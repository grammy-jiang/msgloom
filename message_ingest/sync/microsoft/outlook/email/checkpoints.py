"""
Stage per-folder delta links and atomically promote a validated run.

Candidates are durable pending state. Only the idle extension may promote them
after every folder, reconciliation request, and pipeline write has completed.
An interrupted or failed crawl must retain the last committed links.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from message_ingest.catalog import Catalog, DeltaCheckpoint, DeltaCheckpointCandidate
from message_ingest.catalog.models.microsoft.outlook.email import (
    MailDeltaAbsenceGeneration,
    MailDeltaCandidateBase,
)
from message_ingest.extensions.catalog import CatalogService
from message_ingest.sync.microsoft.outlook.email._cursor_causality import (
    absent_baseline,
    current_baseline,
    validate_baseline,
)


class OutlookDeltaCheckpointStore:
    """
    Checkpoint queries scoped to one source and the shared catalog engine.
    """

    def __init__(self, catalog_or_url: Catalog | str, source_id: str) -> None:
        """
        Borrow a crawler catalog, or own an engine for standalone inspection.
        """
        self._owns_catalog = isinstance(catalog_or_url, str)
        self.catalog = (
            Catalog(catalog_or_url)
            if isinstance(catalog_or_url, str)
            else catalog_or_url
        )
        self.source_id = source_id

    @classmethod
    def from_crawler(cls, crawler):
        """Use the engine that the catalog extension closes after the crawl."""
        return cls(
            CatalogService.from_crawler(crawler).catalog,
            crawler.settings["MSGLOOM_SOURCE_ID"],
        )

    def close(self) -> None:
        """
        Release only engines created by this store, never a borrowed engine.
        """
        if not self._owns_catalog:
            return
        self.catalog.close()

    def get_delta_link(self, folder_id: str) -> str | None:
        """
        Read a committed link; pending candidates are never resume points.
        """
        with self.catalog.Session() as session:
            return session.scalar(
                select(DeltaCheckpoint.delta_link).filter_by(
                    source_id=self.source_id,
                    folder_id=folder_id,
                )
            )

    def get_delta_links(self) -> dict[str, str]:
        """Load committed links once at startup to avoid a query per folder."""
        with self.catalog.Session() as session:
            rows = session.execute(
                select(DeltaCheckpoint.folder_id, DeltaCheckpoint.delta_link).filter_by(
                    source_id=self.source_id
                )
            ).all()
            return {folder_id: delta_link for folder_id, delta_link in rows}

    def get_delta_starts(self) -> dict[str, tuple[str | None, str]]:
        """Snapshot committed Graph cursors and durable absence generations."""
        with self.catalog.Session() as session:
            epochs = session.scalars(
                select(MailDeltaAbsenceGeneration).filter_by(source_id=self.source_id)
            ).all()
            starts: dict[str, tuple[str | None, str]] = {
                row.folder_id: (
                    None,
                    absent_baseline(
                        self.source_id, row.folder_id, generation=row.generation
                    ),
                )
                for row in epochs
            }
            rows = session.scalars(
                select(DeltaCheckpoint).filter_by(source_id=self.source_id)
            ).all()
            starts.update(
                {
                    row.folder_id: (
                        row.delta_link,
                        current_baseline(self.source_id, row.folder_id, row),
                    )
                    for row in rows
                }
            )
            return starts

    def get_delta_start(self, folder_id: str) -> tuple[str | None, str]:
        """Capture one folder's effective generation at request creation."""
        with self.catalog.Session() as session:
            checkpoint = session.scalar(
                select(DeltaCheckpoint).filter_by(
                    source_id=self.source_id, folder_id=folder_id
                )
            )
            if checkpoint is not None:
                return checkpoint.delta_link, current_baseline(
                    self.source_id, folder_id, checkpoint
                )
            epoch = session.get(MailDeltaAbsenceGeneration, (self.source_id, folder_id))
            return None, absent_baseline(
                self.source_id,
                folder_id,
                generation=0 if epoch is None else epoch.generation,
            )

    def write_candidate(
        self,
        *,
        run_id: str,
        folder_id: str,
        delta_link: str,
        observed_at: str,
        baseline_identity: str | None = None,
        evidence_id: str | None = None,
    ) -> None:
        """Persist the final cursor and its original immutable causal proof.

        A missing or invalid baseline is never treated as an initial cursor.
        Exact replay may be accepted but cannot change a committed candidate.
        The new table preserves legacy candidate history without inventing it.
        """
        baseline = validate_baseline(baseline_identity)
        with self.catalog.writer_session() as session:
            key = (self.source_id, run_id, folder_id)
            proof = session.get(MailDeltaCandidateBase, key)
            record = session.scalar(
                select(DeltaCheckpointCandidate).filter_by(
                    run_id=run_id,
                    source_id=self.source_id,
                    folder_id=folder_id,
                )
            )
            # A legacy pending candidate is unknown, not a proof of absence.
            # Never attach a newly inferred digest to an existing legacy row.
            if proof is None and record is not None:
                raise RuntimeError("legacy Mail delta candidate lacks causal baseline")
            if proof is None:
                session.add(
                    MailDeltaCandidateBase(
                        source_id=self.source_id,
                        run_id=run_id,
                        folder_id=folder_id,
                        baseline_identity=baseline,
                    )
                )
            elif proof.baseline_identity != baseline:
                raise ValueError("Mail delta candidate changed its causal baseline")
            if record is None:
                session.add(
                    DeltaCheckpointCandidate(
                        run_id=run_id,
                        source_id=self.source_id,
                        folder_id=folder_id,
                        delta_link=delta_link,
                        evidence_id=evidence_id,
                        observed_at=observed_at,
                    )
                )
                return
            if record.committed_at is not None:
                if (record.delta_link, record.evidence_id, record.observed_at) != (
                    delta_link,
                    evidence_id,
                    observed_at,
                ):
                    raise RuntimeError("committed Mail delta candidate changed")
                return
            record.delta_link = delta_link
            record.evidence_id = evidence_id
            record.observed_at = observed_at

    def load_candidates(self, run_id: str) -> dict[str, DeltaCheckpointCandidate]:
        """
        Return this run's candidates for exact folder-set validation at idle.
        """
        with self.catalog.Session() as session:
            rows = session.scalars(
                select(DeltaCheckpointCandidate).filter_by(
                    run_id=run_id,
                    source_id=self.source_id,
                )
            ).all()
            return {row.folder_id: row for row in rows}

    def commit(self, run_id: str) -> int:
        """Promote one run through the shared session-scoped implementation."""
        from message_ingest.sync.microsoft.outlook.email.promotion import (
            ValidatedMailDeltaRun,
        )

        candidates = self.load_candidates(run_id)
        validated = ValidatedMailDeltaRun(
            run_id=run_id,
            expected_folder_ids=frozenset(candidates),
            reconcile_messages=False,
            candidate_folder_ids=frozenset(candidates),
        )
        committed_at = datetime.now(UTC).isoformat()
        with self.catalog.writer_session() as session:
            return self.commit_in_session(
                session,
                validated,
                committed_at=committed_at,
            )

    def commit_in_session(
        self,
        session,
        validated,
        *,
        committed_at: str,
    ) -> int:
        """CAS all folder candidates against their first-request baseline.

        Caller owns a SQLite BEGIN IMMEDIATE writer transaction shared with
        lifecycle and release publication. No response timestamp determines
        provider-cursor ancestry. One mismatched folder rejects the full run.
        """
        run_id = validated.run_id
        candidates = session.scalars(
            select(DeltaCheckpointCandidate).filter_by(
                run_id=run_id,
                source_id=self.source_id,
            )
        ).all()
        if {row.folder_id for row in candidates} != validated.candidate_folder_ids:
            raise RuntimeError("mail delta candidate folder set changed")
        updates = []
        for candidate in candidates:
            proof = session.get(
                MailDeltaCandidateBase, (self.source_id, run_id, candidate.folder_id)
            )
            if proof is None:
                raise RuntimeError("mail delta candidate lacks causal baseline")
            baseline = validate_baseline(proof.baseline_identity)
            checkpoint = session.scalar(
                select(DeltaCheckpoint).filter_by(
                    source_id=self.source_id,
                    folder_id=candidate.folder_id,
                )
            )
            if candidate.committed_at is not None:
                if (
                    checkpoint is None
                    or checkpoint.run_id != run_id
                    or checkpoint.delta_link != candidate.delta_link
                    or checkpoint.committed_at != candidate.committed_at
                ):
                    raise RuntimeError("mail delta candidate displaced")
                # Committed replay is read-only. Do not refresh committed_at: a
                # later run might already have captured this exact generation.
                continue
            epoch = (
                session.get(
                    MailDeltaAbsenceGeneration, (self.source_id, candidate.folder_id)
                )
                if checkpoint is None
                else None
            )
            if (
                current_baseline(
                    self.source_id,
                    candidate.folder_id,
                    checkpoint,
                    absence_generation=0 if epoch is None else epoch.generation,
                )
                != baseline
            ):
                raise RuntimeError("mail delta candidate displaced")
            updates.append((candidate, checkpoint))
        for candidate, checkpoint in updates:
            if checkpoint is None:
                session.add(
                    DeltaCheckpoint(
                        source_id=self.source_id,
                        folder_id=candidate.folder_id,
                        delta_link=candidate.delta_link,
                        committed_at=committed_at,
                        run_id=run_id,
                    )
                )
            else:
                checkpoint.delta_link = candidate.delta_link
                checkpoint.committed_at = committed_at
                checkpoint.run_id = run_id
            candidate.committed_at = committed_at
        return len(candidates)


from ._folder_delta_checkpoints import OutlookFolderDeltaCheckpointStore

__all__ = [
    "OutlookDeltaCheckpointStore",
    "OutlookFolderDeltaCheckpointStore",
]
