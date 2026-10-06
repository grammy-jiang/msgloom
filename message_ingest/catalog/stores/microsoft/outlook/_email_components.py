"""Atomic Mail component and folder-context persistence."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from message_ingest.acquisition.handoff import AcquisitionFactKind as Kind
from message_ingest.catalog.models.microsoft.outlook.email import (
    AttachmentRecord,
    MailFolderPresence,
    MailFolderRecord,
    MessageSurface,
)

from ._email_associations import DeferredMailCapture, MailAssociations, projection
from ._email_handoff import (
    MailFactWriter,
    MailPersistenceOutcome,
    is_stale,
    surface_reason,
    verified_digest,
)
from ._email_lifecycle import OutlookMailLifecycleStore


class OutlookMailComponentStore(OutlookMailLifecycleStore):
    """Keep each component advancement and fact in one strong transaction."""

    def _facts(self) -> MailFactWriter:
        return MailFactWriter(self.catalog, self.source_id, self.spider_name)

    def set_surface(
        self,
        *,
        run_id: str | None,
        message_id: str,
        surface: str,
        status: str,
        evidence_id: str | None,
        observed_at: str,
        profile_version: str | None = None,
        resource_version: str | None = None,
        primary_observed_at: str | None = None,
        selection_id: str | None = None,
        parent_evidence_id: str | None = None,
        capture_id: str | None = None,
    ) -> MailPersistenceOutcome | DeferredMailCapture:
        """
        Persist one surface with logical provenance and semantic component key.

        Byte components use verified saved bytes. Every component key includes
        status, profile, and the exact selected primary association; no run or
        evidence identity participates. A callback pin is independent of item
        completion order. Neither component can overwrite newer observed state.
        """
        with self.catalog.writer_session() as session:
            if selection_id is not None:
                return MailAssociations(self).retain(
                    session,
                    message_id=message_id,
                    selection_id=selection_id,
                    resource_version=resource_version,
                    parent_evidence_id=parent_evidence_id,
                    component=surface,
                    resource_id=message_id,
                    status=status,
                    profile_version=profile_version,
                    evidence_id=evidence_id,
                    observed_at=observed_at,
                    run_id=run_id,
                    capture_id=capture_id,
                )
            record = session.scalar(
                select(MessageSurface).filter_by(
                    source_id=self.source_id,
                    message_id=message_id,
                    surface=surface,
                )
            )
            writer = self._facts()
            stale = is_stale(
                observed_at, record.observed_at if record else None
            ) or writer.parent_is_stale(
                session, message_id, resource_version, primary_observed_at
            )
            version = resource_version or writer.run_primary_version(
                session,
                run_id,
                message_id,
            )
            state: dict[str, Any] = {
                "surface": surface,
                "status": status,
                "profile": profile_version,
                "resource_version": version,
            }
            if status == "acquired":
                # Equal bytes only revalidate the same exact parent binding.
                if surface == "discovery" and version:
                    state["representation"] = version
                else:
                    state["content_sha256"] = verified_digest(
                        session,
                        self.source_id,
                        evidence_id,
                    )
            equivalent = bool(
                record
                and record.status == status
                and record.profile_version == profile_version
                and record.evidence_id == evidence_id
            )
            if not stale:
                if record is None:
                    record = MessageSurface(
                        source_id=self.source_id,
                        message_id=message_id,
                        surface=surface,
                    )
                    session.add(record)
                record.status = status
                record.evidence_id = evidence_id
                record.observed_at = observed_at
                record.profile_version = profile_version
            return writer.stage(
                session,
                run_id=run_id,
                resource_id=message_id,
                state=state,
                evidence_id=evidence_id,
                observed_at=observed_at,
                kind=Kind.COMPONENT_OBSERVATION,
                resource_kind="message_surface",
                component=surface,
                parent_id=message_id,
                resource_version=version,
                reason=surface_reason(status, profile_version),
                stale=stale,
                equivalent=equivalent,
            )

    def upsert_attachment(
        self,
        *,
        run_id: str | None,
        message_id: str,
        attachment: dict[str, Any],
        evidence_id: str | None,
        observed_at: str,
        resource_version: str | None = None,
        primary_observed_at: str | None = None,
        profile_version: str | None = None,
        selection_id: str | None = None,
        parent_evidence_id: str | None = None,
        capture_id: str | None = None,
    ) -> MailPersistenceOutcome | DeferredMailCapture:
        """
        Stage retained metadata separately from raw and expanded detail.

        Expanded item bodies belong to the item-detail surface. Adding those
        fields to an inventory response must not reversion metadata.
        """
        attachment_id = attachment["id"]
        fields = {
            "attachment_type": attachment.get("@odata.type"),
            "name": attachment.get("name"),
            "content_type": attachment.get("contentType"),
            "size": attachment.get("size"),
            "is_inline": attachment.get("isInline"),
        }
        with self.catalog.writer_session() as session:
            if selection_id is not None:
                return MailAssociations(self).retain(
                    session,
                    message_id=message_id,
                    selection_id=selection_id,
                    resource_version=resource_version,
                    parent_evidence_id=parent_evidence_id,
                    component="attachment_metadata",
                    resource_id=attachment_id,
                    status="acquired",
                    profile_version=profile_version,
                    evidence_id=evidence_id,
                    observed_at=observed_at,
                    run_id=run_id,
                    capture_id=capture_id,
                    metadata=projection(attachment),
                )
            record = session.scalar(
                select(AttachmentRecord).filter_by(
                    source_id=self.source_id,
                    message_id=message_id,
                    attachment_id=attachment_id,
                )
            )
            stale = is_stale(
                observed_at, record.latest_observed_at if record else None
            ) or self._facts().parent_is_stale(
                session, message_id, resource_version, primary_observed_at
            )
            equivalent = bool(
                record
                and all(getattr(record, k) == v for k, v in fields.items())
                and record.latest_evidence_id == evidence_id
            )
            if not stale:
                if record is None:
                    record = AttachmentRecord(
                        source_id=self.source_id,
                        message_id=message_id,
                        attachment_id=attachment_id,
                    )
                    session.add(record)
                for name, value in fields.items():
                    setattr(record, name, value)
                record.latest_observed_at = observed_at
                record.latest_evidence_id = evidence_id
            return self._facts().stage(
                session,
                run_id=run_id,
                resource_id=attachment_id,
                resource_kind="attachment",
                state={
                    "id": attachment_id,
                    **fields,
                    "resource_version": resource_version,
                    "status": "acquired",
                    "profile_version": profile_version,
                },
                kind=Kind.COMPONENT_OBSERVATION,
                component="attachment_metadata",
                parent_id=message_id,
                resource_version=resource_version,
                reason=surface_reason("acquired", profile_version),
                evidence_id=evidence_id,
                observed_at=observed_at,
                stale=stale,
                equivalent=equivalent,
            )

    def record_inventory_page(self, item):
        """Commit an immutable page and all eligible applications."""
        from ._email_inventory import record_page

        with self.catalog.writer_session() as session:
            return record_page(self, session, item)

    def upsert_folder(
        self,
        *,
        folder: dict[str, Any],
        evidence_id: str | None,
        observed_at: str,
        run_id: str | None = None,
    ) -> MailPersistenceOutcome:
        """Persist folder context atomically; delta awaits authority."""
        folder_id = folder["id"]
        fields = {
            "display_name": folder.get("displayName"),
            "parent_folder_id": folder.get("parentFolderId"),
            "child_folder_count": folder.get("childFolderCount"),
            "total_item_count": folder.get("totalItemCount"),
            "unread_item_count": folder.get("unreadItemCount"),
            "is_hidden": folder.get("isHidden"),
        }
        with self.catalog.writer_session() as session:
            record = session.scalar(
                select(MailFolderRecord).filter_by(
                    source_id=self.source_id,
                    folder_id=folder_id,
                )
            )
            presence = session.scalar(
                select(MailFolderPresence).filter_by(
                    source_id=self.source_id,
                    folder_id=folder_id,
                )
            )
            stale = is_stale(
                observed_at,
                record.latest_observed_at if record else None,
            ) or is_stale(
                observed_at,
                presence.latest_observed_at if presence else None,
            )
            equivalent = bool(
                record
                and all(getattr(record, k) == v for k, v in fields.items())
                and (presence is None or presence.is_present)
            )
            if not stale:
                if record is None:
                    record = MailFolderRecord(
                        source_id=self.source_id,
                        folder_id=folder_id,
                    )
                    session.add(record)
                for name, value in fields.items():
                    setattr(record, name, value)
                record.latest_observed_at = observed_at
                record.latest_evidence_id = evidence_id
                self.mark_folder_present_in_session(
                    session,
                    folder_id=folder_id,
                    run_id=run_id,
                    observed_at=observed_at,
                    evidence_id=evidence_id,
                )
            return self._facts().stage(
                session,
                run_id=run_id,
                resource_id=folder_id,
                resource_kind="mail_folder",
                kind=Kind.CONTROL_CONTEXT,
                state={"folder": folder, "is_present": True},
                evidence_id=evidence_id,
                observed_at=observed_at,
                stale=stale,
                equivalent=equivalent,
                authority=self.spider_name == "outlook_folder_delta",
            )
