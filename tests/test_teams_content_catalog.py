"""Teams attachment, reference-resolution, and hosted-content persistence tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from message_ingest.catalog.models.microsoft.teams import (
    TeamsHostedContentObservation,
    TeamsMessageAttachmentObservation,
    TeamsMessageCurrent,
    TeamsReferenceResolutionCurrent,
    TeamsReferenceResolutionObservation,
)
from message_ingest.catalog.stores.microsoft.teams.content import TeamsContentStore
from message_ingest.catalog.stores.microsoft.teams.message import TeamsMessageStore
from message_ingest.items.microsoft.teams.content import (
    TeamsHostedContentBytesItem,
    TeamsHostedContentFailureItem,
    TeamsHostedContentItem,
    TeamsReferenceResolutionItem,
)
from message_ingest.items.microsoft.teams.message import TeamsMessageTrigger
from tests.teams_persistence_support import (
    OBSERVED,
    RUN,
    SOURCE,
    chat_message,
    open_catalog,
    record_evidence,
)


def test_attachment_ordinals_repeat_ids_unknown_cards_and_relations_survive(
    tmp_path: Path,
) -> None:
    catalog = open_catalog(tmp_path)
    store = TeamsMessageStore(catalog, source_id=SOURCE)
    attachments = [
        {
            "id": "dup",
            "contentType": "reference",
            "contentUrl": "https://sharepoint.invalid/reference",
            "name": "file",
        },
        {
            "id": "dup",
            "contentType": "messageReference",
            "content": {"messageId": "other"},
        },
        {
            "contentType": "forwardedMessageReference",
            "content": {"chatId": "foreign-chat"},
        },
        {
            "id": "meeting",
            "contentType": "meetingReference",
            "content": {"eventId": "event-opaque"},
        },
        {
            "id": "tab",
            "contentType": "tabReference",
            "content": {"tabId": "tab-opaque"},
        },
        {
            "contentType": "application/vnd.contoso.future-card",
            "teamsAppId": "app-x",
            "futureMetadata": {"preserve": True},
        },
    ]
    try:
        record_evidence(catalog, "message-evidence")
        item = chat_message(
            evidence_id="message-evidence",
            attachments=attachments,
        )
        store.persist_message(item)

        with catalog.Session() as session:
            rows = session.scalars(
                select(TeamsMessageAttachmentObservation).order_by(
                    TeamsMessageAttachmentObservation.ordinal
                )
            ).all()
            if [row.ordinal for row in rows] != list(range(6)):
                pytest.fail(
                    "Attachment order/context must survive missing or repeated IDs"
                )
            if rows[0].attachment_id != "dup" or rows[1].attachment_id != "dup":
                pytest.fail("Repeated provider attachment IDs must not collapse")
            if rows[2].attachment_id is not None:
                pytest.fail("Missing provider attachment IDs must remain missing")
            kinds = [row.kind for row in rows]
            expected = [
                "reference",
                "message-reference",
                "forwarded-message-reference",
                "meeting-reference",
                "tab-reference",
                "unknown",
            ]
            if kinds != expected:
                pytest.fail(f"Unexpected retained attachment relation kinds: {kinds!r}")
            if rows[-1].raw["futureMetadata"] != {"preserve": True}:
                pytest.fail("Unknown card metadata must remain lossless")
    finally:
        catalog.close()


def test_reference_resolution_states_are_explicit_and_not_attempted_is_valid(
    tmp_path: Path,
) -> None:
    catalog = open_catalog(tmp_path)
    messages = TeamsMessageStore(catalog, source_id=SOURCE)
    content = TeamsContentStore(catalog, source_id=SOURCE)
    try:
        record_evidence(catalog, "message-evidence")
        message = chat_message(
            evidence_id="message-evidence",
            attachments=[{"contentType": "reference", "name": "file"}],
        )
        messages.persist_message(message)
        trigger = TeamsMessageTrigger.from_message(message)

        not_attempted = TeamsReferenceResolutionItem(
            source_id=SOURCE,
            trigger=trigger,
            attachment_ordinal=0,
            state="not-attempted",
            observed_at=OBSERVED,
            evidence_id="message-evidence",
            run_id=RUN,
            details={"profile": "core-unselected"},
        )
        content.persist_reference(not_attempted)

        denied_at = "2026-10-04T00:03:00+00:00"
        record_evidence(catalog, "reference-denied", observed_at=denied_at)
        denied = TeamsReferenceResolutionItem(
            source_id=SOURCE,
            trigger=trigger,
            attachment_ordinal=0,
            state="denied",
            observed_at=denied_at,
            evidence_id="reference-denied",
            run_id=RUN,
            details={"provider_status": 403},
        )
        content.persist_reference(denied)

        with catalog.Session() as session:
            rows = session.scalars(
                select(TeamsReferenceResolutionObservation).order_by(
                    TeamsReferenceResolutionObservation.observation_id
                )
            ).all()
            if [row.state for row in rows] != ["not-attempted", "denied"]:
                pytest.fail("Reference history must retain explicit resolution states")
            current = session.scalar(select(TeamsReferenceResolutionCurrent))
            if current is None or current.state != "denied":
                pytest.fail(
                    "Later explicit resolution state should own current relation"
                )
    finally:
        catalog.close()


def test_hosted_retrieval_links_exact_trigger_across_later_message_edit(
    tmp_path: Path,
) -> None:
    catalog = open_catalog(tmp_path)
    messages = TeamsMessageStore(catalog, source_id=SOURCE)
    content = TeamsContentStore(catalog, source_id=SOURCE)
    try:
        first_at = "2026-10-04T00:04:00+00:00"
        edit_at = "2026-10-04T00:05:00+00:00"
        hosted_at = "2026-10-04T00:06:00+00:00"
        bytes_at = "2026-10-04T00:07:00+00:00"
        fail_at = "2026-10-04T00:08:00+00:00"
        for evidence_id, observed_at in (
            ("message-v1", first_at),
            ("message-v2", edit_at),
            ("hosted-meta", hosted_at),
            ("hosted-bytes", bytes_at),
            ("hosted-failure", fail_at),
        ):
            record_evidence(catalog, evidence_id, observed_at=observed_at)

        first = chat_message(
            evidence_id="message-v1",
            observed_at=first_at,
            etag="etag-1",
            body="before edit",
        )
        messages.persist_message(first)
        trigger = TeamsMessageTrigger.from_message(first)

        edited = chat_message(
            evidence_id="message-v2",
            observed_at=edit_at,
            etag="etag-2",
            body="after edit",
        )
        messages.persist_message(edited)

        metadata = TeamsHostedContentItem.from_graph(
            {"id": "hosted-1", "contentType": "image/png"},
            message_identity=first.identity,
            source_id=SOURCE,
            trigger=trigger,
            observed_at=hosted_at,
            evidence_id="hosted-meta",
            run_id=RUN,
        )
        content.persist_hosted_metadata(metadata)
        binary = TeamsHostedContentBytesItem.from_bytes(
            source_id=SOURCE,
            message_identity=first.identity,
            hosted_content_id="hosted-1",
            trigger=trigger,
            body=b"PNG",
            content_type="image/png",
            observed_at=bytes_at,
            evidence_id="hosted-bytes",
            run_id=RUN,
        )
        content.persist_hosted_bytes(binary)
        failure = TeamsHostedContentFailureItem(
            source_id=SOURCE,
            message_identity=first.identity,
            hosted_content_id="hosted-2",
            trigger=trigger,
            failure_kind="deleted-thread",
            observed_at=fail_at,
            evidence_id="hosted-failure",
            run_id=RUN,
            status_code=410,
            details={"provider_limitation": "deleted thread"},
        )
        content.persist_hosted_failure(failure)

        with catalog.Session() as session:
            current = session.scalar(select(TeamsMessageCurrent))
            if current is None or current.latest_evidence_id != "message-v2":
                pytest.fail("Later edit should own mutable message current projection")
            hosted = session.scalars(
                select(TeamsHostedContentObservation).order_by(
                    TeamsHostedContentObservation.observation_id
                )
            ).all()
            if len(hosted) != 3:
                pytest.fail(
                    "Metadata, bytes, and failure must each remain observations"
                )
            if {row.trigger_evidence_id for row in hosted} != {"message-v1"}:
                pytest.fail("Hosted retrieval must link exact triggering observation")
            if any(row.provider_version_bound for row in hosted):
                pytest.fail(
                    "Hosted retrieval must never claim provider-version binding"
                )
            kinds = {row.observation_kind for row in hosted}
            if kinds != {"metadata", "bytes", "failure"}:
                pytest.fail(f"Unexpected hosted observation kinds: {kinds!r}")
    finally:
        catalog.close()


def test_reference_resolution_supports_every_explicit_state(tmp_path: Path) -> None:
    catalog = open_catalog(tmp_path)
    messages = TeamsMessageStore(catalog, source_id=SOURCE)
    content = TeamsContentStore(catalog, source_id=SOURCE)
    try:
        message_at = "2026-10-04T00:20:00+00:00"
        record_evidence(catalog, "reference-message", observed_at=message_at)
        message = chat_message(
            evidence_id="reference-message",
            observed_at=message_at,
            attachments=[{"contentType": "reference", "name": "file"}],
        )
        messages.persist_message(message)
        trigger = TeamsMessageTrigger.from_message(message)
        states = ("not-attempted", "denied", "missing", "stale", "resolved")
        for index, state in enumerate(states):
            observed_at = f"2026-10-04T00:20:0{index}+00:00"
            evidence_id = f"reference-{state}"
            if index == 0:
                evidence_id = "reference-message"
                observed_at = message_at
            else:
                record_evidence(catalog, evidence_id, observed_at=observed_at)
            content.persist_reference(
                TeamsReferenceResolutionItem(
                    source_id=SOURCE,
                    trigger=trigger,
                    attachment_ordinal=0,
                    state=state,
                    observed_at=observed_at,
                    evidence_id=evidence_id,
                    run_id=RUN,
                    details={"state": state},
                )
            )

        with catalog.Session() as session:
            rows = session.scalars(
                select(TeamsReferenceResolutionObservation).order_by(
                    TeamsReferenceResolutionObservation.observation_id
                )
            ).all()
            if [row.state for row in rows] != list(states):
                pytest.fail("Every explicit reference resolution state must persist")
            current = session.scalar(select(TeamsReferenceResolutionCurrent))
            if current is None or current.state != "resolved":
                pytest.fail("Latest explicit resolution state should be current")
    finally:
        catalog.close()
