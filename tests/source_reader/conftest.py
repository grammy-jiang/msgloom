"""Authentic A1-schema fixtures containing only synthetic Graph evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from message_ingest.catalog import Catalog
from message_ingest.catalog.models.acquisition import RawHttpEvidence, SourceBinding
from message_ingest.catalog.models.microsoft.contacts import (
    ContactDeltaObservation,
    ContactSighting,
)
from message_ingest.catalog.models.microsoft.onedrive import (
    OneDriveContentCapture,
    OneDriveItemRecord,
)
from message_ingest.catalog.models.microsoft.outlook.email import (
    AttachmentRecord,
    MessageObservation,
    MessageRecord,
    MessageSurface,
)
from message_ingest.catalog.models.microsoft.todo import TodoTaskSighting

SOURCE = "synthetic-source"
OBSERVED_OLD = "2026-09-28T00:00:00+00:00"
OBSERVED_NEW = "2026-09-29T00:00:00+00:00"


def _evidence(
    session: Session,
    root: Path,
    evidence_id: str,
    body: object,
    *,
    purpose: str,
    observed_at: str,
) -> RawHttpEvidence:
    data = (
        body
        if isinstance(body, bytes)
        else json.dumps(body, separators=(",", ":")).encode()
    )
    digest = hashlib.sha256(data).hexdigest()
    path = root / f"{digest}.bin"
    path.write_bytes(data)
    row = RawHttpEvidence(
        evidence_id=evidence_id,
        source_id=SOURCE,
        run_id="synthetic-run",
        purpose=purpose,
        observed_at=observed_at,
        origin="network",
        request_fingerprint="f" * 64,
        request_url="https://graph.example.invalid/redacted",
        request_method="GET",
        request_headers={},
        request_body_sha256=hashlib.sha256(b"").hexdigest(),
        request_body_path=str(root / "empty.bin"),
        request_body_bytes=0,
        response_url=None,
        response_status=200,
        response_headers={},
        response_body_sha256=digest,
        response_body_path=str(path),
        response_body_bytes=len(data),
        response_flags=[],
        error_type=None,
        error_message=None,
    )
    session.add(row)
    return row


@pytest.fixture
def saved_catalog(tmp_path: Path) -> dict[str, object]:
    """Build the real A1 tables with old/current synthetic source versions."""
    database = tmp_path / "catalog.sqlite3"
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    (evidence_root / "empty.bin").write_bytes(b"")
    engine = create_engine(f"sqlite:///{database}")
    # Install the same immutable guards as acquisition before ORM seeding.
    catalog = Catalog(f"sqlite:///{database}")
    catalog.close()

    with Session(engine) as session, session.begin():
        session.add(
            SourceBinding(
                source_id=SOURCE,
                provider="microsoft",
                key_scheme="synthetic",
                account_key_sha256="a" * 64,
                binding_method="test",
                bound_at="2026-09-01T00:00:00+00:00",
            )
        )
        parent = {
            "id": "parent",
            "subject": "Parent",
            "internetMessageId": "<parent@example.test>",
            "receivedDateTime": "2026-09-27T00:00:00Z",
            "body": {"contentType": "text", "content": "Parent body"},
        }
        old = {
            "id": "message",
            "subject": "Old subject",
            "internetMessageId": "<message@example.test>",
            "conversationId": "conversation-1",
            "parentFolderId": "folder-old",
            "receivedDateTime": "2026-09-28T00:00:00Z",
            "lastModifiedDateTime": "2026-09-28T00:00:00Z",
            "body": {"contentType": "text", "content": "Old body"},
            "hasAttachments": True,
        }
        current = {
            **old,
            "subject": "Current subject",
            "parentFolderId": "folder-new",
            "lastModifiedDateTime": "2026-09-29T00:00:00Z",
            "body": {"contentType": "html", "content": "<p>Current body</p>"},
            "internetMessageHeaders": [
                {"name": "In-Reply-To", "value": "<parent@example.test>"}
            ],
        }
        _evidence(
            session,
            evidence_root,
            "ev-parent",
            parent,
            purpose="message-detail",
            observed_at="2026-09-27T00:00:00+00:00",
        )
        _evidence(
            session,
            evidence_root,
            "ev-old",
            old,
            purpose="message-detail",
            observed_at=OBSERVED_OLD,
        )
        _evidence(
            session,
            evidence_root,
            "ev-current",
            current,
            purpose="message-detail",
            observed_at=OBSERVED_NEW,
        )
        _evidence(
            session,
            evidence_root,
            "ev-attachment",
            b"synthetic attachment",
            purpose="attachment-raw",
            observed_at=OBSERVED_NEW,
        )
        _evidence(
            session,
            evidence_root,
            "ev-mime",
            b"From: sender@example.test\r\n\r\nMIME body",
            purpose="message-mime",
            observed_at=OBSERVED_NEW,
        )
        session.add_all(
            [
                MessageRecord(
                    source_id=SOURCE,
                    message_id="parent",
                    subject="Parent",
                    internet_message_id="<parent@example.test>",
                    received_date_time="2026-09-27T00:00:00Z",
                    is_removed=False,
                    latest_observed_at="2026-09-27T00:00:00+00:00",
                    latest_evidence_id="ev-parent",
                ),
                MessageRecord(
                    source_id=SOURCE,
                    message_id="message",
                    subject="Current subject",
                    internet_message_id="<message@example.test>",
                    conversation_id="conversation-1",
                    parent_folder_id="folder-new",
                    received_date_time="2026-09-28T00:00:00Z",
                    last_modified_date_time="2026-09-29T00:00:00Z",
                    has_attachments=True,
                    is_removed=False,
                    latest_observed_at=OBSERVED_NEW,
                    latest_evidence_id="ev-current",
                ),
                MessageObservation(
                    observation_id="obs-parent",
                    source_id=SOURCE,
                    message_id="parent",
                    run_id="run-parent",
                    kind="detail",
                    evidence_id="ev-parent",
                    observed_at="2026-09-27T00:00:00+00:00",
                ),
                MessageObservation(
                    observation_id="obs-old",
                    source_id=SOURCE,
                    message_id="message",
                    run_id="run-old",
                    kind="detail",
                    evidence_id="ev-old",
                    observed_at=OBSERVED_OLD,
                    parent_folder_id="folder-old",
                ),
                MessageObservation(
                    observation_id="obs-current",
                    source_id=SOURCE,
                    message_id="message",
                    run_id="run-current",
                    kind="detail",
                    evidence_id="ev-current",
                    observed_at=OBSERVED_NEW,
                    parent_folder_id="folder-new",
                ),
                AttachmentRecord(
                    source_id=SOURCE,
                    message_id="message",
                    attachment_id="attachment-1",
                    attachment_type="#microsoft.graph.fileAttachment",
                    name="note.txt",
                    content_type="text/plain",
                    size=len(b"synthetic attachment"),
                    is_inline=False,
                    latest_observed_at=OBSERVED_NEW,
                    latest_evidence_id="ev-current",
                ),
                MessageSurface(
                    source_id=SOURCE,
                    message_id="message",
                    surface="mime",
                    status="acquired",
                    evidence_id="ev-mime",
                    observed_at=OBSERVED_NEW,
                    profile_version="full-v1",
                ),
                MessageSurface(
                    source_id=SOURCE,
                    message_id="message",
                    surface="attachments",
                    status="acquired",
                    evidence_id="ev-current",
                    observed_at=OBSERVED_NEW,
                    profile_version="full-v1",
                ),
                MessageSurface(
                    source_id=SOURCE,
                    message_id="message",
                    surface="attachment_raw:attachment-1",
                    status="acquired",
                    evidence_id="ev-attachment",
                    observed_at=OBSERVED_NEW,
                    profile_version="full-v1",
                ),
            ]
        )

        todo_old = {
            "value": [
                {
                    "id": "task",
                    "title": "Old task",
                    "lastModifiedDateTime": "2026-09-28T00:00:00Z",
                    "body": {"contentType": "html", "content": "<b>old</b>"},
                    "status": "notStarted",
                }
            ]
        }
        todo_new = {
            "value": [
                {
                    "id": "task",
                    "title": "Current task",
                    "lastModifiedDateTime": "2026-09-29T00:00:00Z",
                    "body": {"contentType": "text", "content": "current"},
                    "status": "inProgress",
                }
            ]
        }
        _evidence(
            session,
            evidence_root,
            "ev-todo-old",
            todo_old,
            purpose="todo-tasks-page",
            observed_at=OBSERVED_OLD,
        )
        _evidence(
            session,
            evidence_root,
            "ev-todo-new",
            todo_new,
            purpose="todo-tasks-page",
            observed_at=OBSERVED_NEW,
        )
        session.add_all(
            [
                TodoTaskSighting(
                    source_id=SOURCE,
                    run_id="todo-old",
                    list_id="list",
                    task_id="task",
                    observed_at=OBSERVED_OLD,
                    evidence_id="ev-todo-old",
                ),
                TodoTaskSighting(
                    source_id=SOURCE,
                    run_id="todo-new",
                    list_id="list",
                    task_id="task",
                    observed_at=OBSERVED_NEW,
                    evidence_id="ev-todo-new",
                ),
            ]
        )

        contact = {
            "value": [
                {
                    "id": "contact",
                    "displayName": "Synthetic Contact",
                    "companyName": "Example",
                    "lastModifiedDateTime": "2026-09-29T00:00:00Z",
                }
            ]
        }
        _evidence(
            session,
            evidence_root,
            "ev-contact",
            contact,
            purpose="contacts-default-page",
            observed_at=OBSERVED_NEW,
        )
        session.add(
            ContactSighting(
                source_id=SOURCE,
                run_id="contacts-run",
                scope_key="default",
                contact_id="contact",
                observed_at=OBSERVED_NEW,
                evidence_id="ev-contact",
                run_started_at=OBSERVED_NEW,
            )
        )
        contact_delta = {
            "value": [
                {
                    "id": "contact-delta",
                    "displayName": "Delta Contact",
                    "companyName": "Earlier Example",
                    "lastModifiedDateTime": "2026-09-28T00:00:00Z",
                }
            ]
        }
        _evidence(
            session,
            evidence_root,
            "ev-contact-delta",
            contact_delta,
            purpose="contacts-delta-page",
            observed_at=OBSERVED_OLD,
        )
        session.add(
            ContactDeltaObservation(
                source_id=SOURCE,
                folder_id="folder-1",
                run_id="contacts-delta-run",
                ordinal=0,
                contact_id="contact-delta",
                is_removed=False,
                removed_reason=None,
                observed_at=OBSERVED_OLD,
                evidence_id="ev-contact-delta",
                raw=contact_delta["value"][0],
            )
        )

        drive = {
            "value": [
                {
                    "id": "file",
                    "name": "report.txt",
                    "size": 7,
                    "lastModifiedDateTime": "2026-09-29T00:00:00Z",
                    "webUrl": "https://provider.example.invalid/file",
                    "eTag": "etag-1",
                    "cTag": "ctag-1",
                    "file": {"mimeType": "text/plain"},
                }
            ]
        }
        _evidence(
            session,
            evidence_root,
            "ev-drive",
            drive,
            purpose="onedrive-root-children-page",
            observed_at=OBSERVED_NEW,
        )
        content = _evidence(
            session,
            evidence_root,
            "ev-drive-content",
            b"content",
            purpose="onedrive-content",
            observed_at=OBSERVED_NEW,
        )
        session.add(
            OneDriveItemRecord(
                source_id=SOURCE,
                item_id="file",
                name="report.txt",
                size=7,
                last_modified_date_time="2026-09-29T00:00:00Z",
                web_url="https://provider.example.invalid/file",
                e_tag="etag-1",
                c_tag="ctag-1",
                file={"mimeType": "text/plain"},
                is_deleted=False,
                raw=drive["value"][0],
                latest_observed_at=OBSERVED_NEW,
                latest_evidence_id="ev-drive",
                latest_run_id="drive-run",
            )
        )
        session.add(
            OneDriveContentCapture(
                source_id=SOURCE,
                evidence_id="ev-drive-content",
                item_id="file",
                content_sha256=content.response_body_sha256,
                content_bytes=content.response_body_bytes,
                planned_metadata_observed_at=OBSERVED_NEW,
                planned_metadata_evidence_id="ev-drive",
                planned_e_tag="etag-1",
                planned_c_tag="ctag-1",
                response_e_tag="etag-1",
                observed_at=OBSERVED_NEW,
                run_id="drive-content-run",
            )
        )
    engine.dispose()
    return {
        "database": database,
        "evidence_root": evidence_root,
        "source_id": SOURCE,
    }
