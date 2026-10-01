"""Outlook Mail folder and whole-mailbox presence lifecycle state."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, or_, select

from message_ingest.catalog.models.microsoft.outlook.email import (
    DeltaCheckpoint,
    DeltaCheckpointCandidate,
    MailFolderPresence,
    MailFolderRecord,
    MailFolderSighting,
    MailFolderSnapshotCandidate,
    MessagePresence,
    MessagePresenceCandidate,
    MessagePresenceSighting,
    MessageRecord,
)


class OutlookMailLifecycleStore:
    """Own presence sightings and idle-time snapshot promotion."""

    def __init__(self, catalog, *, source_id: str) -> None:
        self.catalog = catalog
        self.source_id = source_id

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    def mark_message_present_in_session(
        self,
        session,
        *,
        message_id: str,
        run_id: str | None,
        observed_at: str,
        evidence_id: str | None,
        reason: str = "observed",
    ) -> None:
        """Record positive mailbox presence without erasing message history."""
        record = session.scalar(
            select(MessagePresence).filter_by(
                source_id=self.source_id,
                message_id=message_id,
            )
        )
        if record is None:
            session.add(
                MessagePresence(
                    source_id=self.source_id,
                    message_id=message_id,
                    is_present=True,
                    reason=reason,
                    latest_run_id=run_id,
                    latest_observed_at=observed_at,
                    latest_evidence_id=evidence_id,
                )
            )
            return
        if observed_at < record.latest_observed_at:
            return
        record.is_present = True
        record.reason = reason
        record.latest_run_id = run_id
        record.latest_observed_at = observed_at
        record.latest_evidence_id = evidence_id

    def mark_folder_present_in_session(
        self,
        session,
        *,
        folder_id: str,
        run_id: str | None,
        observed_at: str,
        evidence_id: str | None,
    ) -> None:
        """Record folder presence and this run's inventory sighting."""
        presence = session.scalar(
            select(MailFolderPresence).filter_by(
                source_id=self.source_id,
                folder_id=folder_id,
            )
        )
        if presence is None:
            session.add(
                MailFolderPresence(
                    source_id=self.source_id,
                    folder_id=folder_id,
                    is_present=True,
                    removed_reason=None,
                    latest_run_id=run_id,
                    latest_observed_at=observed_at,
                    latest_evidence_id=evidence_id,
                )
            )
        elif observed_at >= presence.latest_observed_at:
            presence.is_present = True
            presence.removed_reason = None
            presence.latest_run_id = run_id
            presence.latest_observed_at = observed_at
            presence.latest_evidence_id = evidence_id
        if run_id:
            existing = session.scalar(
                select(MailFolderSighting.id).filter_by(
                    source_id=self.source_id,
                    run_id=run_id,
                    folder_id=folder_id,
                )
            )
            if existing is None:
                session.add(
                    MailFolderSighting(
                        source_id=self.source_id,
                        run_id=run_id,
                        folder_id=folder_id,
                        observed_at=observed_at,
                        evidence_id=evidence_id,
                    )
                )

    def mark_folder_removed(
        self,
        *,
        folder_id: str,
        run_id: str | None,
        observed_at: str,
        evidence_id: str | None,
        reason: str | None,
    ) -> None:
        """Apply an explicit folder-delta tombstone and discard stale message cursors."""
        with self.catalog.Session() as session, session.begin():
            self._set_folder_presence(
                session,
                folder_id=folder_id,
                is_present=False,
                reason=reason or "folder_delta_removed",
                run_id=run_id or "",
                observed_at=observed_at,
                evidence_id=evidence_id,
            )
            session.execute(
                delete(DeltaCheckpoint).where(
                    DeltaCheckpoint.source_id == self.source_id,
                    DeltaCheckpoint.folder_id == folder_id,
                )
            )
            session.execute(
                delete(DeltaCheckpointCandidate).where(
                    DeltaCheckpointCandidate.source_id == self.source_id,
                    DeltaCheckpointCandidate.folder_id == folder_id,
                )
            )

    def record_message_sighting(
        self,
        *,
        run_id: str,
        message_id: str,
        observed_at: str,
        evidence_id: str | None,
    ) -> None:
        """Stage one lightweight whole-mailbox reconciliation sighting."""
        with self.catalog.Session() as session, session.begin():
            existing = session.scalar(
                select(MessagePresenceSighting.id).filter_by(
                    source_id=self.source_id,
                    run_id=run_id,
                    message_id=message_id,
                )
            )
            if existing is None:
                session.add(
                    MessagePresenceSighting(
                        source_id=self.source_id,
                        run_id=run_id,
                        message_id=message_id,
                        observed_at=observed_at,
                        evidence_id=evidence_id,
                    )
                )

    def write_folder_snapshot_candidate(
        self,
        *,
        run_id: str,
        observed_at: str,
        evidence_id: str | None,
    ) -> None:
        """Stage completion of one recursive folder inventory."""
        self._write_candidate(
            MailFolderSnapshotCandidate,
            run_id=run_id,
            observed_at=observed_at,
            evidence_id=evidence_id,
        )

    def write_message_presence_candidate(
        self,
        *,
        run_id: str,
        observed_at: str,
        evidence_id: str | None,
    ) -> None:
        """Stage completion of one whole-mailbox message reconciliation."""
        self._write_candidate(
            MessagePresenceCandidate,
            run_id=run_id,
            observed_at=observed_at,
            evidence_id=evidence_id,
        )

    def _write_candidate(self, model, *, run_id: str, observed_at: str, evidence_id):
        with self.catalog.Session() as session, session.begin():
            record = session.scalar(
                select(model).filter_by(source_id=self.source_id, run_id=run_id)
            )
            if record is None:
                session.add(
                    model(
                        source_id=self.source_id,
                        run_id=run_id,
                        observed_at=observed_at,
                        evidence_id=evidence_id,
                    )
                )
                return
            record.observed_at = observed_at
            record.evidence_id = evidence_id

    def commit_delta_lifecycle(
        self,
        run_id: str,
        *,
        expected_folder_ids: set[str],
        reconcile_messages: bool,
    ) -> dict[str, int]:
        """Promote lifecycle through the shared session-scoped implementation."""
        from message_ingest.sync.microsoft.outlook.email.promotion import (
            ValidatedMailDeltaRun,
        )

        validated = ValidatedMailDeltaRun(
            run_id=run_id,
            expected_folder_ids=frozenset(expected_folder_ids),
            reconcile_messages=reconcile_messages,
            candidate_folder_ids=frozenset(expected_folder_ids),
        )
        committed_at = self._now()
        with self.catalog.Session() as session, session.begin():
            return self.commit_delta_lifecycle_in_session(
                session,
                validated,
                committed_at=committed_at,
            )

    def commit_delta_lifecycle_in_session(
        self,
        session,
        validated,
        *,
        committed_at: str,
    ) -> dict[str, int]:
        """Apply lifecycle promotion inside the caller-owned transaction."""
        run_id = validated.run_id
        expected_folder_ids = set(validated.expected_folder_ids)
        reconcile_messages = validated.reconcile_messages
        folder_candidate = session.scalar(
            select(MailFolderSnapshotCandidate).filter_by(
                source_id=self.source_id,
                run_id=run_id,
            )
        )
        if folder_candidate is None:
            raise RuntimeError("complete delta run has no folder snapshot candidate")
        folder_ids = set(
            session.scalars(
                select(MailFolderSighting.folder_id).filter_by(
                    source_id=self.source_id,
                    run_id=run_id,
                )
            ).all()
        )
        if folder_ids != expected_folder_ids:
            raise RuntimeError(
                "folder snapshot sightings do not match completed delta folders"
            )
        known_folders = set(
            session.scalars(
                select(MailFolderRecord.folder_id).filter_by(source_id=self.source_id)
            ).all()
        )
        removed_folders = known_folders - folder_ids
        for folder_id in folder_ids:
            self._set_folder_presence(
                session,
                folder_id=folder_id,
                is_present=True,
                reason=None,
                run_id=run_id,
                observed_at=folder_candidate.observed_at,
                evidence_id=folder_candidate.evidence_id,
            )
        for folder_id in removed_folders:
            self._set_folder_presence(
                session,
                folder_id=folder_id,
                is_present=False,
                reason="not_in_complete_inventory",
                run_id=run_id,
                observed_at=folder_candidate.observed_at,
                evidence_id=folder_candidate.evidence_id,
            )
        if removed_folders:
            session.execute(
                delete(DeltaCheckpoint).where(
                    DeltaCheckpoint.source_id == self.source_id,
                    DeltaCheckpoint.folder_id.in_(removed_folders),
                )
            )
            session.execute(
                delete(DeltaCheckpointCandidate).where(
                    DeltaCheckpointCandidate.source_id == self.source_id,
                    DeltaCheckpointCandidate.folder_id.in_(removed_folders),
                )
            )
        folder_candidate.committed_at = committed_at

        present_count = absent_count = 0
        if reconcile_messages:
            message_candidate = session.scalar(
                select(MessagePresenceCandidate).filter_by(
                    source_id=self.source_id,
                    run_id=run_id,
                )
            )
            if message_candidate is None:
                raise RuntimeError(
                    "complete reconciled delta run has no message presence candidate"
                )
            seen_messages = set(
                session.scalars(
                    select(MessagePresenceSighting.message_id).filter_by(
                        source_id=self.source_id,
                        run_id=run_id,
                    )
                ).all()
            )
            known_messages = set(
                session.scalars(
                    select(MessageRecord.message_id).filter_by(source_id=self.source_id)
                ).all()
            )
            for message_id in seen_messages:
                self._set_message_presence(
                    session,
                    message_id=message_id,
                    is_present=True,
                    reason="reconciliation_seen",
                    run_id=run_id,
                    observed_at=message_candidate.observed_at,
                    evidence_id=message_candidate.evidence_id,
                )
            for message_id in known_messages - seen_messages:
                self._set_message_presence(
                    session,
                    message_id=message_id,
                    is_present=False,
                    reason="not_in_complete_reconciliation",
                    run_id=run_id,
                    observed_at=message_candidate.observed_at,
                    evidence_id=message_candidate.evidence_id,
                )
            message_candidate.committed_at = committed_at
            present_count = len(seen_messages)
            absent_count = len(known_messages - seen_messages)

        return {
            "folders_present": len(folder_ids),
            "folders_absent": len(removed_folders),
            "messages_present": present_count,
            "messages_absent": absent_count,
        }

    def _set_folder_presence(
        self,
        session,
        *,
        folder_id: str,
        is_present: bool,
        reason: str | None,
        run_id: str,
        observed_at: str,
        evidence_id: str | None,
    ) -> None:
        record = session.scalar(
            select(MailFolderPresence).filter_by(
                source_id=self.source_id,
                folder_id=folder_id,
            )
        )
        if record is None:
            session.add(
                MailFolderPresence(
                    source_id=self.source_id,
                    folder_id=folder_id,
                    is_present=is_present,
                    removed_reason=reason,
                    latest_run_id=run_id,
                    latest_observed_at=observed_at,
                    latest_evidence_id=evidence_id,
                )
            )
            return
        record.is_present = is_present
        record.removed_reason = reason
        record.latest_run_id = run_id
        record.latest_observed_at = observed_at
        record.latest_evidence_id = evidence_id

    def _set_message_presence(
        self,
        session,
        *,
        message_id: str,
        is_present: bool,
        reason: str,
        run_id: str,
        observed_at: str,
        evidence_id: str | None,
    ) -> None:
        record = session.scalar(
            select(MessagePresence).filter_by(
                source_id=self.source_id,
                message_id=message_id,
            )
        )
        if record is None:
            session.add(
                MessagePresence(
                    source_id=self.source_id,
                    message_id=message_id,
                    is_present=is_present,
                    reason=reason,
                    latest_run_id=run_id,
                    latest_observed_at=observed_at,
                    latest_evidence_id=evidence_id,
                )
            )
            return
        record.is_present = is_present
        record.reason = reason
        record.latest_run_id = run_id
        record.latest_observed_at = observed_at
        record.latest_evidence_id = evidence_id

    def folder_presence(self, *, folder_id: str) -> bool | None:
        """Return confirmed recursive-inventory presence for one folder."""
        with self.catalog.Session() as session:
            return session.scalar(
                select(MailFolderPresence.is_present).filter_by(
                    source_id=self.source_id,
                    folder_id=folder_id,
                )
            )

    def message_presence(self, *, message_id: str) -> bool | None:
        """Return confirmed mailbox presence, or ``None`` when never reconciled."""
        with self.catalog.Session() as session:
            return session.scalar(
                select(MessagePresence.is_present).filter_by(
                    source_id=self.source_id,
                    message_id=message_id,
                )
            )

    def active_message_filter(self):
        """SQL predicate that keeps legacy/unknown presence and confirmed present."""
        return or_(MessagePresence.id.is_(None), MessagePresence.is_present.is_(True))


__all__ = ["OutlookMailLifecycleStore"]
