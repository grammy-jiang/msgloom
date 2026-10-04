"""Custom-folder Contacts delta staging and checkpoint promotion."""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from message_ingest.catalog.models.microsoft.contacts import (
    ContactDeltaCheckpoint,
    ContactDeltaCheckpointCandidate,
    ContactDeltaObservation,
    ContactRecord,
)
from message_ingest.catalog.store import Catalog
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from message_ingest.items.microsoft.contacts import (
    ContactDeltaCheckpointCandidateItem,
    ContactItem,
)

from ._contacts_handoff import stage_contacts_fact
from ._contacts_state import (
    ContactsPromotionOrder,
    ContactStateWriter,
    observation_time,
)


@dataclass(frozen=True, slots=True)
class ContactDeltaCheckpointState:
    """Detached committed cursor state for one custom folder."""

    folder_id: str
    delta_link: str
    revision: int
    run_id: str
    committed_at: str


class ContactsDeltaStore:
    """Own delta staging, ordered application, and opaque cursor promotion."""

    def __init__(self, catalog: Catalog, *, source_id: str) -> None:
        self.catalog = catalog
        self.source_id = source_id
        self.handoff = AcquisitionHandoffStore(catalog)
        self.state = ContactStateWriter(source_id=source_id)
        self.order = ContactsPromotionOrder(catalog, source_id=source_id)

    def begin_run(
        self, *, folder_id: str, run_id: str
    ) -> ContactDeltaCheckpointState | None:
        """Capture shared promotion ownership before any delta request is sent."""
        self.order.begin(run_id=run_id, operation=self._operation(folder_id))
        return self.load_checkpoint(folder_id)

    def persist_observation(self, item: ContactItem) -> None:
        """Stage one ordered custom-folder delta entry without changing current state."""
        if item.observation_kind != "delta" or item.is_default_scope:
            raise ValueError("Contacts delta requires a concrete custom-folder scope")
        folder_id = item.folder_id
        if not isinstance(folder_id, str) or not folder_id.strip():
            raise ValueError("Contacts delta requires a concrete folder ID")
        observation_time(item.observed_at)
        with self.catalog.writer_session() as session:
            ordinal = session.scalar(
                select(func.max(ContactDeltaObservation.ordinal)).filter_by(
                    source_id=self.source_id, folder_id=folder_id, run_id=item.run_id
                )
            )
            ordinal = (ordinal or 0) + 1
            removed = item.removed
            reason = removed.get("reason") if isinstance(removed, dict) else None
            session.add(
                ContactDeltaObservation(
                    source_id=self.source_id,
                    folder_id=folder_id,
                    run_id=item.run_id,
                    ordinal=ordinal,
                    contact_id=item.contact_id,
                    is_removed=removed is not None,
                    removed_reason=reason if isinstance(reason, str) else None,
                    observed_at=item.observed_at,
                    evidence_id=item.evidence_id,
                    raw=item.raw,
                )
            )
            stage_contacts_fact(
                session,
                self.handoff,
                source_id=self.source_id,
                spider_name="microsoft_contacts_delta",
                item=item,
                ordinal=ordinal,
            )

    def stage_candidate(self, item: ContactDeltaCheckpointCandidateItem) -> None:
        """Persist the exact opaque terminal link for later idle-time promotion."""
        if not item.folder_id.strip() or not item.delta_link or not item.evidence_id:
            raise ValueError(
                "Contacts delta candidate requires folder, link, and evidence"
            )
        observation_time(item.observed_at)
        identity = {
            "source_id": self.source_id,
            "folder_id": item.folder_id,
            "run_id": item.run_id,
        }
        with self.catalog.writer_session() as session:
            record = session.get(ContactDeltaCheckpointCandidate, identity)
            values = {
                "base_revision": item.base_revision,
                "delta_link": item.delta_link,
                "observed_at": item.observed_at,
                "evidence_id": item.evidence_id,
            }
            if record is None:
                session.add(ContactDeltaCheckpointCandidate(**identity, **values))
                return
            for name, value in values.items():
                setattr(record, name, value)

    def load_checkpoint(self, folder_id: str) -> ContactDeltaCheckpointState | None:
        """Return the committed opaque cursor for one custom folder."""
        with self.catalog.Session() as session:
            row = session.get(
                ContactDeltaCheckpoint,
                {"source_id": self.source_id, "folder_id": folder_id},
            )
            return self._checkpoint_state(row) if row is not None else None

    def promote(
        self, *, folder_id: str, run_id: str, base_revision: int | None
    ) -> ContactDeltaCheckpointState:
        """Apply staged observations and cursor under shared snapshot/delta CAS."""
        with self.catalog.writer_session() as session:
            generation = self.order.require_base(
                session, run_id=run_id, operation=self._operation(folder_id)
            )
            current = session.get(
                ContactDeltaCheckpoint,
                {"source_id": self.source_id, "folder_id": folder_id},
            )
            revision = current.revision if current is not None else None
            if revision != base_revision:
                raise RuntimeError("Contacts delta base revision is stale")
            candidate = session.get(
                ContactDeltaCheckpointCandidate,
                {
                    "source_id": self.source_id,
                    "folder_id": folder_id,
                    "run_id": run_id,
                },
            )
            if candidate is None or candidate.base_revision != base_revision:
                raise RuntimeError("Contacts delta candidate is missing or stale")
            observations = session.scalars(
                select(ContactDeltaObservation)
                .filter_by(source_id=self.source_id, folder_id=folder_id, run_id=run_id)
                .order_by(ContactDeltaObservation.ordinal)
            ).all()
            for observation in observations:
                self._apply_observation(session, observation)
            committed_at = datetime.now(UTC).isoformat()
            if current is None:
                current = ContactDeltaCheckpoint(
                    source_id=self.source_id,
                    folder_id=folder_id,
                    delta_link=candidate.delta_link,
                    revision=1,
                    run_id=run_id,
                    committed_at=committed_at,
                )
                session.add(current)
            else:
                current.delta_link = candidate.delta_link
                current.revision += 1
                current.run_id = run_id
                current.committed_at = committed_at
            self.order.advance(session, expected=generation)
            session.flush()
            return self._checkpoint_state(current)

    def _apply_observation(
        self, session: Session, observation: ContactDeltaObservation
    ) -> None:
        scope_key = f"folder:{observation.folder_id}"
        identity = {
            "source_id": self.source_id,
            "scope_key": scope_key,
            "contact_id": observation.contact_id,
        }
        if self.state.delta_is_stale(
            session,
            identity=identity,
            run_id=observation.run_id,
            observed_at=observation.observed_at,
        ):
            return
        if observation.is_removed:
            self.state.set_presence(
                session,
                identity=identity,
                is_present=False,
                reason=observation.removed_reason or "delta_removed",
                run_id=observation.run_id,
                observed_at=observation.observed_at,
                evidence_id=observation.evidence_id,
            )
            return
        record = session.get(ContactRecord, identity)
        raw = dict(record.raw) if record is not None else {}
        raw.update(observation.raw)
        if record is None:
            item = ContactItem.from_graph(
                raw,
                folder_id=observation.folder_id,
                is_default_scope=False,
                observation_kind="delta",
                observed_at=observation.observed_at,
                evidence_id=observation.evidence_id,
                run_id=observation.run_id,
                run_started_at=observation.observed_at,
            )
            session.add(self.state.record(item, scope_key=scope_key))
        else:
            self.state.assign(
                record, raw, observation.observed_at, observation.evidence_id
            )
        self.state.set_presence(
            session,
            identity=identity,
            is_present=True,
            reason=None,
            run_id=observation.run_id,
            observed_at=observation.observed_at,
            evidence_id=observation.evidence_id,
        )

    @staticmethod
    def _operation(folder_id: str) -> str:
        return f"delta:{folder_id}"

    @staticmethod
    def _checkpoint_state(row: ContactDeltaCheckpoint) -> ContactDeltaCheckpointState:
        return ContactDeltaCheckpointState(
            folder_id=row.folder_id,
            delta_link=row.delta_link,
            revision=row.revision,
            run_id=row.run_id,
            committed_at=row.committed_at,
        )


__all__ = ["ContactDeltaCheckpointState", "ContactsDeltaStore"]
