"""Outlook Mail persistence and detached planning queries."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from message_ingest.catalog.models.microsoft.outlook.email import (
    AttachmentRecord,
    MailFolderRecord,
    MessageObservation,
    MessageRecord,
    MessageSurface,
)


class OutlookMailStore:
    """Own Outlook Mail catalog state for one logical source."""

    def __init__(self, catalog, *, source_id: str) -> None:
        self.catalog = catalog
        self.source_id = source_id

    def record_message(
        self,
        *,
        run_id: str | None,
        message: dict[str, Any],
        kind: str,
        evidence_id: str | None,
        observed_at: str,
    ) -> bool:
        """Record one message projection and observation transactionally."""
        message_id = message["id"]
        with self.catalog.Session() as session, session.begin():
            record = session.scalar(
                select(MessageRecord).filter_by(
                    source_id=self.source_id,
                    message_id=message_id,
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

            if datetime.fromisoformat(observed_at) >= datetime.fromisoformat(
                record.latest_observed_at
            ):
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

            return self._add_observation(
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
        with self.catalog.Session() as session, session.begin():
            return self._add_observation(
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

    @staticmethod
    def _add_observation(session: Session, observation: MessageObservation) -> bool:
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
                return False
        session.add(observation)
        return True

    def set_surface(
        self,
        *,
        message_id: str,
        surface: str,
        status: str,
        evidence_id: str | None,
        observed_at: str,
        profile_version: str | None = None,
    ) -> None:
        """Upsert one profile surface without letting older evidence win."""
        with self.catalog.Session() as session, session.begin():
            record = session.scalar(
                select(MessageSurface).filter_by(
                    source_id=self.source_id,
                    message_id=message_id,
                    surface=surface,
                )
            )
            if record is None:
                session.add(
                    MessageSurface(
                        source_id=self.source_id,
                        message_id=message_id,
                        surface=surface,
                        status=status,
                        evidence_id=evidence_id,
                        observed_at=observed_at,
                        profile_version=profile_version,
                    )
                )
                return
            if datetime.fromisoformat(observed_at) < datetime.fromisoformat(
                record.observed_at
            ):
                return
            record.status = status
            record.evidence_id = evidence_id
            record.observed_at = observed_at
            record.profile_version = profile_version

    def upsert_attachment(
        self,
        *,
        message_id: str,
        attachment: dict[str, Any],
        evidence_id: str | None,
        observed_at: str,
    ) -> None:
        """Keep newest metadata for one source/message/attachment key."""
        attachment_id = attachment["id"]
        with self.catalog.Session() as session, session.begin():
            record = session.scalar(
                select(AttachmentRecord).filter_by(
                    source_id=self.source_id,
                    message_id=message_id,
                    attachment_id=attachment_id,
                )
            )
            if record is None:
                record = AttachmentRecord(
                    source_id=self.source_id,
                    message_id=message_id,
                    attachment_id=attachment_id,
                    latest_observed_at=observed_at,
                )
                session.add(record)
            if datetime.fromisoformat(observed_at) < datetime.fromisoformat(
                record.latest_observed_at
            ):
                return
            record.attachment_type = attachment.get("@odata.type")
            record.name = attachment.get("name")
            record.content_type = attachment.get("contentType")
            record.size = attachment.get("size")
            record.is_inline = attachment.get("isInline")
            record.latest_observed_at = observed_at
            record.latest_evidence_id = evidence_id

    def get_message_state(self, *, message_id: str) -> dict[str, Any] | None:
        """Return detached message state, or ``None`` for an unknown message."""
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

    def upsert_folder(
        self,
        *,
        folder: dict[str, Any],
        evidence_id: str | None,
        observed_at: str,
    ) -> None:
        """Keep latest folder metadata; discovery does not infer deletion."""
        folder_id = folder["id"]
        with self.catalog.Session() as session, session.begin():
            record = session.scalar(
                select(MailFolderRecord).filter_by(
                    source_id=self.source_id,
                    folder_id=folder_id,
                )
            )
            if record is None:
                record = MailFolderRecord(
                    source_id=self.source_id,
                    folder_id=folder_id,
                    latest_observed_at=observed_at,
                )
                session.add(record)
            if datetime.fromisoformat(observed_at) < datetime.fromisoformat(
                record.latest_observed_at
            ):
                return
            record.display_name = folder.get("displayName")
            record.parent_folder_id = folder.get("parentFolderId")
            record.child_folder_count = folder.get("childFolderCount")
            record.total_item_count = folder.get("totalItemCount")
            record.unread_item_count = folder.get("unreadItemCount")
            record.is_hidden = folder.get("isHidden")
            record.latest_observed_at = observed_at
            record.latest_evidence_id = evidence_id


__all__ = ["OutlookMailStore"]
