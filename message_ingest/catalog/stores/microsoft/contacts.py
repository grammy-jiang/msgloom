"""Contacts snapshot lifecycle and custom-folder delta persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import select

from message_ingest.catalog.models.microsoft.contacts import (
    ContactCollectionCompletion,
    ContactFolderPresence,
    ContactFolderRecord,
    ContactFolderSighting,
    ContactPresence,
    ContactRecord,
    ContactSighting,
    ContactsSnapshotState,
)
from message_ingest.catalog.store import Catalog
from message_ingest.items.microsoft.contacts import (
    ContactCollectionCompleteItem,
    ContactDeltaCheckpointCandidateItem,
    ContactFolderItem,
    ContactItem,
)

type Outcome = Literal["created", "changed", "unchanged", "stale"]


from ._contacts_delta import ContactDeltaCheckpointState, ContactsDeltaStore
from ._contacts_state import (
    ContactsPromotionOrder,
    ContactStateWriter,
    observation_time,
)


class ContactsStore:
    """Persist additive provider state and promote only complete clean runs."""

    def __init__(self, catalog: Catalog, *, source_id: str) -> None:
        self.catalog = catalog
        self.source_id = source_id
        self.state = ContactStateWriter(source_id=source_id)
        self.order = ContactsPromotionOrder(catalog, source_id=source_id)
        self.delta = ContactsDeltaStore(catalog, source_id=source_id)

    @staticmethod
    def scope_key(*, folder_id: str | None, is_default_scope: bool) -> str:
        """Return an internal scope key without inventing a provider default ID."""
        if is_default_scope:
            if folder_id is not None:
                raise ValueError("Default Contacts scope cannot have a folder ID")
            return "default"
        if not isinstance(folder_id, str) or not folder_id.strip():
            raise ValueError("Custom Contacts scope requires a folder ID")
        return f"folder:{folder_id}"

    @staticmethod
    def _time(value: str) -> datetime:
        return observation_time(value)

    def begin_snapshot_run(self, run_id: str) -> int:
        """Capture shared authority ownership before snapshot traversal starts."""
        return self.order.begin(run_id=run_id, operation="snapshot")

    def begin_delta_run(
        self, *, folder_id: str, run_id: str
    ) -> ContactDeltaCheckpointState | None:
        """Capture shared authority ownership before delta traversal starts."""
        return self.delta.begin_run(folder_id=folder_id, run_id=run_id)

    def persist_delta_observation(self, item: ContactItem) -> None:
        """Stage one delta observation without publishing current state."""
        self.delta.persist_observation(item)

    def stage_delta_candidate(self, item: ContactDeltaCheckpointCandidateItem) -> None:
        """Stage one terminal opaque delta cursor."""
        self.delta.stage_candidate(item)

    def load_delta_checkpoint(
        self, folder_id: str
    ) -> ContactDeltaCheckpointState | None:
        """Load one committed custom-folder delta cursor."""
        return self.delta.load_checkpoint(folder_id)

    def promote_delta(
        self, *, folder_id: str, run_id: str, base_revision: int | None
    ) -> ContactDeltaCheckpointState:
        """Promote one clean delta under shared snapshot/delta authority CAS."""
        return self.delta.promote(
            folder_id=folder_id, run_id=run_id, base_revision=base_revision
        )

    def persist_folder(self, item: ContactFolderItem) -> Outcome:
        """Upsert folder metadata and record this run's positive sighting."""
        observed = self._time(item.observed_at)
        self._time(item.run_started_at)
        with self.catalog.writer_session() as session:
            record = session.get(
                ContactFolderRecord,
                {"source_id": self.source_id, "folder_id": item.folder_id},
            )
            outcome: Outcome
            if record is None:
                session.add(
                    ContactFolderRecord(
                        source_id=self.source_id,
                        folder_id=item.folder_id,
                        display_name=item.display_name,
                        parent_folder_id=item.parent_folder_id,
                        latest_observed_at=item.observed_at,
                        latest_evidence_id=item.evidence_id,
                        raw=item.raw,
                    )
                )
                outcome = "created"
            elif observed < self._time(record.latest_observed_at):
                outcome = "stale"
            elif observed == self._time(record.latest_observed_at):
                outcome = "unchanged" if record.raw == item.raw else "stale"
            else:
                outcome = "unchanged" if record.raw == item.raw else "changed"
                self._assign_folder(record, item)
            self._record_folder_sighting(session, item)
            return outcome

    def persist_contact(self, item: ContactItem) -> Outcome:
        """Upsert one snapshot contact; delta observations use explicit staging."""
        if item.observation_kind != "snapshot":
            raise ValueError("Delta contacts must be staged before promotion")
        observed = self._time(item.observed_at)
        self._time(item.run_started_at)
        scope_key = self.scope_key(
            folder_id=item.folder_id, is_default_scope=item.is_default_scope
        )
        identity = {
            "source_id": self.source_id,
            "scope_key": scope_key,
            "contact_id": item.contact_id,
        }
        with self.catalog.writer_session() as session:
            record = session.get(ContactRecord, identity)
            if record is None:
                session.add(self.state.record(item, scope_key=scope_key))
                outcome: Outcome = "created"
            elif observed < self._time(record.latest_observed_at):
                outcome = "stale"
            elif observed == self._time(record.latest_observed_at):
                outcome = "unchanged" if record.raw == item.raw else "stale"
            else:
                outcome = "unchanged" if record.raw == item.raw else "changed"
                self.state.assign(record, item.raw, item.observed_at, item.evidence_id)
            self._record_contact_sighting(session, item, scope_key=scope_key)
            return outcome

    def persist_completion(self, item: ContactCollectionCompleteItem) -> None:
        """Record one terminal collection page for later idle-time validation."""
        self._time(item.observed_at)
        self._time(item.run_started_at)
        scope_key = self._completion_scope(item)
        identity = {
            "source_id": self.source_id,
            "run_id": item.run_id,
            "collection_kind": item.collection_kind,
            "scope_key": scope_key,
        }
        with self.catalog.writer_session() as session:
            record = session.get(ContactCollectionCompletion, identity)
            values = {
                "folder_id": item.folder_id,
                "is_default_scope": item.is_default_scope,
                "observed_at": item.observed_at,
                "evidence_id": item.evidence_id,
                "run_started_at": item.run_started_at,
            }
            if record is None:
                session.add(ContactCollectionCompletion(**identity, **values))
                return
            for name, value in values.items():
                setattr(record, name, value)

    def promote_snapshot(self, run_id: str) -> dict[str, int]:
        """Atomically publish presence after durable traversal-completion checks."""
        committed_at = datetime.now(UTC).isoformat()
        with self.catalog.writer_session() as session:
            completions = session.scalars(
                select(ContactCollectionCompletion).filter_by(
                    source_id=self.source_id, run_id=run_id
                )
            ).all()
            by_key = {(row.collection_kind, row.scope_key): row for row in completions}
            root = by_key.get(("folder_inventory", "root"))
            default = by_key.get(("contacts", "default"))
            if root is None or default is None:
                raise RuntimeError("Contacts snapshot is incomplete")
            started = root.run_started_at
            if default.run_started_at != started:
                raise RuntimeError("Contacts snapshot has inconsistent run identity")
            folder_sightings = {
                row.folder_id: row
                for row in session.scalars(
                    select(ContactFolderSighting).filter_by(
                        source_id=self.source_id, run_id=run_id
                    )
                ).all()
            }
            folders = set(folder_sightings)
            for folder_id in folders:
                scope = f"folder:{folder_id}"
                child = by_key.get(("child_folders", scope))
                contacts = by_key.get(("contacts", scope))
                if child is None or contacts is None:
                    raise RuntimeError("Contacts snapshot is incomplete")
                if (
                    child.run_started_at != started
                    or contacts.run_started_at != started
                ):
                    raise RuntimeError(
                        "Contacts snapshot has inconsistent run identity"
                    )
            current = session.get(ContactsSnapshotState, self.source_id)
            if current is not None:
                if run_id == current.latest_run_id:
                    return self._presence_counts(session)
                if self._time(started) <= self._time(current.latest_run_started_at):
                    raise RuntimeError("Contacts snapshot run is stale")
            generation = self.order.require_base(
                session, run_id=run_id, operation="snapshot"
            )
            contact_sightings = {
                (row.scope_key, row.contact_id): row
                for row in session.scalars(
                    select(ContactSighting).filter_by(
                        source_id=self.source_id, run_id=run_id
                    )
                ).all()
            }
            folder_counts = self._promote_folder_presence(
                session, folder_sightings, run_id, root
            )
            contact_counts = self._promote_contact_presence(
                session, contact_sightings, run_id, by_key, root
            )
            if current is None:
                session.add(
                    ContactsSnapshotState(
                        source_id=self.source_id,
                        latest_run_id=run_id,
                        latest_run_started_at=started,
                        committed_at=committed_at,
                    )
                )
            else:
                current.latest_run_id = run_id
                current.latest_run_started_at = started
                current.committed_at = committed_at
            self.order.advance(session, expected=generation)
            return {**folder_counts, **contact_counts}

    def _promote_folder_presence(
        self, session, seen: dict[str, ContactFolderSighting], run_id: str, root
    ) -> dict[str, int]:
        known = set(
            session.scalars(
                select(ContactFolderRecord.folder_id).filter_by(
                    source_id=self.source_id
                )
            ).all()
        )
        for folder_id in known:
            identity = {"source_id": self.source_id, "folder_id": folder_id}
            record = session.get(ContactFolderPresence, identity)
            sighting = seen.get(folder_id)
            present = sighting is not None
            values = {
                "is_present": present,
                "removed_reason": None if present else "not_in_complete_inventory",
                "latest_run_id": run_id,
                "latest_observed_at": (
                    sighting.observed_at if sighting is not None else root.observed_at
                ),
                "latest_evidence_id": (
                    sighting.evidence_id if sighting is not None else root.evidence_id
                ),
            }
            if record is None:
                session.add(ContactFolderPresence(**identity, **values))
            else:
                for name, value in values.items():
                    setattr(record, name, value)
        return {
            "folders_present": len(seen),
            "folders_absent": len(known - set(seen)),
        }

    def _promote_contact_presence(
        self,
        session,
        seen: dict[tuple[str, str], ContactSighting],
        run_id: str,
        completions: dict[tuple[str, str], ContactCollectionCompletion],
        root,
    ) -> dict[str, int]:
        known = set(
            session.execute(
                select(ContactRecord.scope_key, ContactRecord.contact_id).filter_by(
                    source_id=self.source_id
                )
            ).all()
        )
        for scope_key, contact_id in known | set(seen):
            identity = {
                "source_id": self.source_id,
                "scope_key": scope_key,
                "contact_id": contact_id,
            }
            sighting = seen.get((scope_key, contact_id))
            present = sighting is not None
            completion = completions.get(("contacts", scope_key))
            provenance = sighting or completion or root
            self.state.set_presence(
                session,
                identity=identity,
                is_present=present,
                reason=None if present else "not_in_complete_snapshot",
                run_id=run_id,
                observed_at=provenance.observed_at,
                evidence_id=provenance.evidence_id,
            )
        return {
            "contacts_present": len(seen),
            "contacts_absent": len(known - set(seen)),
        }

    def _record_folder_sighting(self, session, item: ContactFolderItem) -> None:
        identity = {
            "source_id": self.source_id,
            "run_id": item.run_id,
            "folder_id": item.folder_id,
        }
        if session.get(ContactFolderSighting, identity) is None:
            session.add(
                ContactFolderSighting(
                    **identity,
                    observed_at=item.observed_at,
                    evidence_id=item.evidence_id,
                    run_started_at=item.run_started_at,
                )
            )

    def _record_contact_sighting(
        self, session, item: ContactItem, *, scope_key: str
    ) -> None:
        identity = {
            "source_id": self.source_id,
            "run_id": item.run_id,
            "scope_key": scope_key,
            "contact_id": item.contact_id,
        }
        if session.get(ContactSighting, identity) is None:
            session.add(
                ContactSighting(
                    **identity,
                    observed_at=item.observed_at,
                    evidence_id=item.evidence_id,
                    run_started_at=item.run_started_at,
                )
            )

    @staticmethod
    def _assign_folder(record: ContactFolderRecord, item: ContactFolderItem) -> None:
        record.display_name = item.display_name
        record.parent_folder_id = item.parent_folder_id
        record.latest_observed_at = item.observed_at
        record.latest_evidence_id = item.evidence_id
        record.raw = item.raw

    @staticmethod
    def _completion_scope(item: ContactCollectionCompleteItem) -> str:
        if item.collection_kind == "folder_inventory":
            if item.folder_id is not None or item.is_default_scope:
                raise ValueError("Folder inventory completion must use root scope")
            return "root"
        if item.collection_kind == "contacts":
            return ContactsStore.scope_key(
                folder_id=item.folder_id, is_default_scope=item.is_default_scope
            )
        if item.collection_kind == "child_folders":
            if item.is_default_scope:
                raise ValueError("Child-folder completion cannot use default scope")
            return ContactsStore.scope_key(
                folder_id=item.folder_id, is_default_scope=False
            )
        raise ValueError("Unsupported Contacts completion kind")

    def _presence_counts(self, session) -> dict[str, int]:
        folders = session.scalars(
            select(ContactFolderPresence).filter_by(source_id=self.source_id)
        ).all()
        contacts = session.scalars(
            select(ContactPresence).filter_by(source_id=self.source_id)
        ).all()
        return {
            "folders_present": sum(row.is_present for row in folders),
            "folders_absent": sum(not row.is_present for row in folders),
            "contacts_present": sum(row.is_present for row in contacts),
            "contacts_absent": sum(not row.is_present for row in contacts),
        }


__all__ = ["ContactDeltaCheckpointState", "ContactsStore", "Outcome"]
