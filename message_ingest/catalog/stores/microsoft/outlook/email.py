"""Outlook Mail persistence and detached planning queries."""

from __future__ import annotations

from dataclasses import replace
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from message_ingest.acquisition.handoff import AcquisitionFactKind as Kind
from message_ingest.catalog.models.microsoft.outlook.email import (
    AttachmentRecord,
    MessageObservation,
    MessagePresence,
    MessageRecord,
    MessageSurface,
)

from ._email_components import OutlookMailComponentStore
from ._email_handoff import (
    MailPersistenceOutcome,
    is_stale,
    previous_primary_key,
    primary_projection,
    semantic_digest,
)


class OutlookMailStore(OutlookMailComponentStore):
    """Own Outlook Mail catalog state for one logical source."""

    def record_message(
        self,
        *,
        run_id: str | None,
        message: dict[str, Any],
        kind: str,
        evidence_id: str | None,
        observed_at: str,
    ) -> MailPersistenceOutcome:
        """Commit projection, observation, and exact primary fact together."""
        message_id = message["id"]
        with self.catalog.writer_session() as session:
            record = session.scalar(
                select(MessageRecord).filter_by(
                    source_id=self.source_id,
                    message_id=message_id,
                )
            )
            stale = is_stale(
                observed_at,
                record.latest_observed_at if record else None,
            )
            projection = primary_projection(message)
            prior_key = previous_primary_key(
                session,
                self.source_id,
                record.latest_evidence_id if record else None,
                message_id,
            )
            equivalent = bool(
                record
                and (
                    prior_key == semantic_digest(projection)
                    or (
                        evidence_id is not None
                        and record.latest_evidence_id == evidence_id
                    )
                )
            )
            if record is None:
                record = MessageRecord(
                    source_id=self.source_id,
                    message_id=message_id,
                    latest_observed_at=observed_at,
                    is_removed=False,
                )
                session.add(record)

            if not stale:
                record.subject = message.get("subject", record.subject)
                record.internet_message_id = message.get(
                    "internetMessageId", record.internet_message_id
                )
                record.conversation_id = message.get(
                    "conversationId", record.conversation_id
                )
                record.parent_folder_id = message.get(
                    "parentFolderId", record.parent_folder_id
                )
                record.received_date_time = message.get(
                    "receivedDateTime", record.received_date_time
                )
                record.last_modified_date_time = message.get(
                    "lastModifiedDateTime", record.last_modified_date_time
                )
                if "isRead" in message:
                    record.is_read = message.get("isRead")
                if "hasAttachments" in message:
                    record.has_attachments = message.get("hasAttachments")
                record.is_removed = False
                record.latest_observed_at = observed_at
                record.latest_evidence_id = evidence_id

            self.mark_message_present_in_session(
                session,
                message_id=message_id,
                run_id=run_id,
                observed_at=observed_at,
                evidence_id=evidence_id,
            )

            observation, created = self._add_observation(
                session,
                MessageObservation(
                    observation_id=uuid4().hex,
                    source_id=self.source_id,
                    message_id=message_id,
                    run_id=run_id,
                    kind=kind,
                    evidence_id=evidence_id,
                    observed_at=observed_at,
                    parent_folder_id=message.get("parentFolderId"),
                    last_modified_date_time=message.get("lastModifiedDateTime"),
                    removed_reason=None,
                ),
            )
            outcome = self._facts().stage(
                session,
                run_id=run_id,
                resource_id=message_id,
                state=projection,
                evidence_id=evidence_id,
                observed_at=observed_at,
                observation_id=observation.observation_id,
                resource_version=message.get("changeKey") or None,
                stale=stale,
                equivalent=equivalent,
            )
            return replace(outcome, observation_created=created)

    def record_folder_removal(
        self,
        *,
        run_id: str | None,
        message_id: str,
        folder_id: str,
        removed_reason: str | None,
        evidence_id: str | None,
        observed_at: str,
    ) -> bool:
        """Record removal from one folder without inferring global deletion."""
        with self.catalog.writer_session() as session:
            observation, created = self._add_observation(
                session,
                MessageObservation(
                    observation_id=uuid4().hex,
                    source_id=self.source_id,
                    message_id=message_id,
                    run_id=run_id,
                    kind="folder_removed",
                    evidence_id=evidence_id,
                    observed_at=observed_at,
                    parent_folder_id=folder_id,
                    last_modified_date_time=None,
                    removed_reason=removed_reason,
                ),
            )
            self._facts().stage(
                session,
                run_id=run_id,
                resource_id=message_id,
                kind=Kind.SCOPED_STATE_TRANSITION,
                component="folder_membership",
                scope_id=folder_id,
                state={"is_member": False},
                evidence_id=evidence_id,
                observed_at=observed_at,
                observation_id=observation.observation_id,
                authority=True,
                reason="folder_membership_removed",
            )
            return created

    @staticmethod
    def _add_observation(
        session: Session,
        observation: MessageObservation,
    ) -> tuple[MessageObservation, bool]:
        """Deduplicate one source/message/kind/evidence observation."""
        if observation.evidence_id is not None:
            existing = session.scalar(
                select(MessageObservation).filter_by(
                    source_id=observation.source_id,
                    message_id=observation.message_id,
                    kind=observation.kind,
                    evidence_id=observation.evidence_id,
                )
            )
            if existing is not None:
                return existing, False
        session.add(observation)
        return observation, True

    def list_message_ids(
        self,
        *,
        run_ids=None,
        observation_kinds=None,
    ) -> list[str]:
        """Return current message IDs, optionally scoped to observations."""
        with self.catalog.Session() as session:
            stmt = (
                select(MessageRecord.message_id)
                .outerjoin(
                    MessagePresence,
                    (MessagePresence.source_id == MessageRecord.source_id)
                    & (MessagePresence.message_id == MessageRecord.message_id),
                )
                .where(
                    MessageRecord.source_id == self.source_id,
                    MessageRecord.is_removed.is_(False),
                    self.active_message_filter(),
                )
            )
            normalized_runs = tuple(dict.fromkeys(run_ids or ()))
            normalized_kinds = tuple(dict.fromkeys(observation_kinds or ()))
            if normalized_runs or normalized_kinds:
                stmt = stmt.join(
                    MessageObservation,
                    (MessageObservation.source_id == MessageRecord.source_id)
                    & (MessageObservation.message_id == MessageRecord.message_id),
                )
                if normalized_runs:
                    stmt = stmt.where(MessageObservation.run_id.in_(normalized_runs))
                if normalized_kinds:
                    stmt = stmt.where(MessageObservation.kind.in_(normalized_kinds))
                stmt = stmt.distinct()
            stmt = stmt.order_by(
                MessageRecord.latest_observed_at.desc(),
                MessageRecord.message_id,
            )
            return list(session.scalars(stmt).all())

    def get_message_state(self, *, message_id: str) -> dict[str, Any] | None:
        """Return detached state, or ``None`` for an unknown message."""
        with self.catalog.Session() as session:
            row = session.scalar(
                select(MessageRecord).filter_by(
                    source_id=self.source_id,
                    message_id=message_id,
                )
            )
            if row is None:
                return None
            return {
                "message_id": row.message_id,
                "has_attachments": row.has_attachments,
                "is_removed": row.is_removed,
                "latest_observed_at": row.latest_observed_at,
                "latest_evidence_id": row.latest_evidence_id,
            }

    def get_surfaces(self, *, message_id: str) -> dict[str, dict[str, Any]]:
        """Return detached surface state for enrichment planning."""
        with self.catalog.Session() as session:
            rows = session.scalars(
                select(MessageSurface).filter_by(
                    source_id=self.source_id,
                    message_id=message_id,
                )
            ).all()
            return {
                row.surface: {
                    "status": row.status,
                    "evidence_id": row.evidence_id,
                    "observed_at": row.observed_at,
                    "profile_version": row.profile_version,
                }
                for row in rows
            }

    def get_attachments(self, *, message_id: str) -> list[dict[str, Any]]:
        """Return detached attachment metadata for child-surface planning."""
        with self.catalog.Session() as session:
            rows = session.scalars(
                select(AttachmentRecord).filter_by(
                    source_id=self.source_id,
                    message_id=message_id,
                )
            ).all()
            return [
                {
                    "attachment_id": row.attachment_id,
                    "attachment_type": row.attachment_type,
                    "name": row.name,
                    "content_type": row.content_type,
                    "size": row.size,
                    "is_inline": row.is_inline,
                    "latest_observed_at": row.latest_observed_at,
                    "latest_evidence_id": row.latest_evidence_id,
                }
                for row in rows
            ]


__all__ = ["OutlookMailStore"]
