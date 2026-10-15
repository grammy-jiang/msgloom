"""Mailbox-level mailFolder delta cursor proof and atomic release promotion."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from message_ingest.catalog import Catalog
from message_ingest.catalog.models.microsoft.outlook.email import (
    MailFolderDeltaCandidateBase,
)
from message_ingest.extensions.catalog import CatalogService
from message_ingest.sync.microsoft.outlook.email._cursor_causality import (
    absent_baseline,
    committed_baseline,
    validate_baseline,
)


class OutlookFolderDeltaCheckpointStore:
    """Persist the one mailbox-level Graph mailFolder delta cursor per source."""

    # Kept distinct from message-delta per-folder tokens and tombstone epochs.
    _FOLDER_DELTA_SCOPE = "mailFolder-delta-cursor-v1"

    def __init__(self, catalog_or_url: Catalog | str, source_id: str) -> None:
        self._owns_catalog = isinstance(catalog_or_url, str)
        self.catalog = (
            Catalog(catalog_or_url)
            if isinstance(catalog_or_url, str)
            else catalog_or_url
        )
        self.source_id = source_id

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            CatalogService.from_crawler(crawler).catalog,
            crawler.settings["MSGLOOM_SOURCE_ID"],
        )

    def close(self) -> None:
        if self._owns_catalog:
            self.catalog.close()

    def _generation(self, checkpoint) -> str:
        if checkpoint is None:
            return absent_baseline(self.source_id, self._FOLDER_DELTA_SCOPE)
        return committed_baseline(
            self.source_id,
            self._FOLDER_DELTA_SCOPE,
            delta_link=checkpoint.delta_link,
            run_id=checkpoint.run_id,
            committed_at=checkpoint.committed_at,
        )

    def get_delta_start(self) -> tuple[str | None, str]:
        """Atomically snapshot the opaque URL and its committed generation."""
        from message_ingest.catalog import FolderDeltaCheckpoint

        with self.catalog.Session() as session:
            checkpoint = session.scalar(
                select(FolderDeltaCheckpoint).filter_by(source_id=self.source_id)
            )
            return (
                None if checkpoint is None else checkpoint.delta_link,
                self._generation(checkpoint),
            )

    def get_delta_link(self) -> str | None:
        return self.get_delta_start()[0]

    def write_candidate(
        self,
        *,
        run_id: str,
        delta_link: str,
        observed_at: str,
        baseline_identity: str | None = None,
        evidence_id: str | None = None,
    ) -> None:
        """Stage the terminal response with immutable first-request evidence."""
        from message_ingest.catalog import FolderDeltaCheckpointCandidate

        identity = validate_baseline(baseline_identity)
        with self.catalog.writer_session() as session:
            proof = session.get(MailFolderDeltaCandidateBase, (self.source_id, run_id))
            candidate = session.scalar(
                select(FolderDeltaCheckpointCandidate).filter_by(
                    source_id=self.source_id, run_id=run_id
                )
            )
            if proof is None and candidate is not None:
                raise RuntimeError(
                    "legacy folder delta candidate lacks causal baseline"
                )
            if proof is None:
                session.add(
                    MailFolderDeltaCandidateBase(
                        source_id=self.source_id,
                        run_id=run_id,
                        baseline_identity=identity,
                    )
                )
            elif proof.baseline_identity != identity:
                raise ValueError("folder delta candidate changed its causal baseline")
            if candidate is None:
                session.add(
                    FolderDeltaCheckpointCandidate(
                        source_id=self.source_id,
                        run_id=run_id,
                        delta_link=delta_link,
                        evidence_id=evidence_id,
                        observed_at=observed_at,
                    )
                )
                return
            if candidate.committed_at is not None:
                if (
                    candidate.delta_link,
                    candidate.evidence_id,
                    candidate.observed_at,
                ) != (delta_link, evidence_id, observed_at):
                    raise RuntimeError("committed folder delta candidate changed")
                return
            candidate.delta_link = delta_link
            candidate.evidence_id = evidence_id
            candidate.observed_at = observed_at

    def get_candidate(self, run_id: str):
        from message_ingest.catalog import FolderDeltaCheckpointCandidate

        with self.catalog.Session() as session:
            return session.scalar(
                select(FolderDeltaCheckpointCandidate).filter_by(
                    source_id=self.source_id, run_id=run_id
                )
            )

    def commit(self, run_id: str) -> None:
        """Commit folder authority only if its original cursor still wins.

        Observation time is recorded for provenance, never for Graph token
        ancestry. Release, lifecycle, and the cursor share one writer lock.
        """
        from message_ingest.catalog import (
            FolderDeltaCheckpoint,
            FolderDeltaCheckpointCandidate,
        )

        from ._authority_decision import input_digest, replay, seal

        with self.catalog.writer_session() as session:
            candidate = session.scalar(
                select(FolderDeltaCheckpointCandidate).filter_by(
                    source_id=self.source_id, run_id=run_id
                )
            )
            if candidate is None:
                raise RuntimeError("folder delta candidate missing")
            proof = session.get(MailFolderDeltaCandidateBase, (self.source_id, run_id))
            if proof is None:
                raise RuntimeError("folder delta candidate lacks causal baseline")
            baseline = validate_baseline(proof.baseline_identity)
            checkpoint = session.scalar(
                select(FolderDeltaCheckpoint).filter_by(source_id=self.source_id)
            )
            if candidate.committed_at is not None:
                if (
                    checkpoint is None
                    or checkpoint.run_id != run_id
                    or checkpoint.delta_link != candidate.delta_link
                    or checkpoint.committed_at != candidate.committed_at
                ):
                    raise RuntimeError("folder delta candidate displaced")
                digest = input_digest(session, self.source_id, run_id, "folder_delta")
                if (
                    replay(session, self.source_id, run_id, "folder_delta", digest)
                    is None
                ):
                    raise RuntimeError(
                        "Legacy Mail authority decision requires reacquisition"
                    )
                return  # exact idempotent replay must not churn generation
            if self._generation(checkpoint) != baseline:
                raise RuntimeError("folder delta candidate displaced")
            digest = input_digest(session, self.source_id, run_id, "folder_delta")
            committed_at = datetime.now(UTC).isoformat()
            if checkpoint is None:
                session.add(
                    FolderDeltaCheckpoint(
                        source_id=self.source_id,
                        delta_link=candidate.delta_link,
                        committed_at=committed_at,
                        run_id=run_id,
                    )
                )
            else:
                checkpoint.delta_link = candidate.delta_link
                checkpoint.committed_at = committed_at
                checkpoint.run_id = run_id
            from message_ingest.catalog.stores.microsoft.outlook._email_apply_authority import (
                apply_mail_observations,
            )
            from message_ingest.catalog.stores.microsoft.outlook.email import (
                OutlookMailStore,
            )

            from ._release import release_mail_authority

            applied = apply_mail_observations(
                OutlookMailStore(self.catalog, source_id=self.source_id),
                session,
                run_id=run_id,
                authority="folder_delta",
                scopes={self.source_id},
            )
            release_mail_authority(
                self.catalog,
                session,
                source_id=self.source_id,
                run_id=run_id,
                committed_at=committed_at,
                subject="folder_delta",
                applied=applied,
            )
            candidate.committed_at = committed_at
            seal(session, self.source_id, run_id, "folder_delta", digest, {}, applied)


__all__ = ["OutlookFolderDeltaCheckpointStore"]
