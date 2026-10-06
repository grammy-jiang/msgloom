"""Pin optional provider mappings and existing consumer dataclass schemas."""

from dataclasses import fields

import pytest
from itemadapter import ItemAdapter

from message_ingest.items.microsoft.outlook import calendar, email
from microsoft_graph.items.outlook import (
    OutlookAttachmentItem,
    OutlookCalendarAttachmentItem,
    OutlookCalendarItem,
    OutlookEventItem,
    OutlookMailFolderItem,
    OutlookMessageItem,
)

BASELINE_FIELDS = {
    "OutlookMailItem": (
        "message_id",
        "subject",
        "sender_address",
        "from_address",
        "received_date_time",
        "internet_message_id",
        "conversation_id",
        "parent_folder_id",
        "importance",
        "inference_classification",
        "is_read",
        "has_attachments",
        "body_preview",
        "raw",
        "source_response_url",
        "observed_at",
        "observation_kind",
        "evidence_id",
        "run_id",
    ),
    "OutlookMailDetailItem": (
        "message_id",
        "raw",
        "source_response_url",
        "observed_at",
        "evidence_id",
        "run_id",
        "selection_id",
    ),
    "OutlookAttachmentItem": (
        "message_id",
        "attachment_id",
        "attachment_type",
        "raw",
        "source_response_url",
        "observed_at",
        "evidence_id",
        "run_id",
        "resource_version",
        "primary_observed_at",
        "selection_id",
        "parent_evidence_id",
        "capture_id",
    ),
    "OutlookMailFolderItem": (
        "folder_id",
        "display_name",
        "parent_folder_id",
        "child_folder_count",
        "total_item_count",
        "unread_item_count",
        "is_hidden",
        "raw",
        "source_response_url",
        "observed_at",
        "evidence_id",
        "run_id",
    ),
    "OutlookCalendarItem": (
        "calendar_id",
        "raw",
        "observed_at",
        "evidence_id",
        "run_id",
    ),
    "OutlookCalendarEventItem": (
        "event_id",
        "raw",
        "observed_at",
        "evidence_id",
        "run_id",
        "calendar_id",
        "observation_kind",
    ),
    "OutlookCalendarAttachmentItem": (
        "event_id",
        "attachment_id",
        "attachment_type",
        "raw",
        "observed_at",
        "evidence_id",
        "run_id",
        "calendar_id",
        "content_bytes_present",
        "resource_version",
    ),
}


def test_consumer_item_fields_and_order_are_unchanged():
    for name, expected in BASELINE_FIELDS.items():
        cls = getattr(email, name, None) or getattr(calendar, name)
        actual = tuple(field.name for field in fields(cls))
        if actual != expected:
            pytest.fail(f"Consumer schema changed for {name}: {actual!r}")


@pytest.mark.parametrize(
    "provider,consumer,context,reuse_strategy",
    [
        (OutlookMessageItem, email.OutlookMailItem, {}, "inheritance"),
        (OutlookMailFolderItem, email.OutlookMailFolderItem, {}, "inheritance"),
        (
            OutlookAttachmentItem,
            email.OutlookAttachmentItem,
            {"message_id": "message"},
            "inheritance",
        ),
        (OutlookCalendarItem, calendar.OutlookCalendarItem, {}, "composition"),
        (OutlookEventItem, calendar.OutlookCalendarEventItem, {}, "composition"),
        (
            OutlookCalendarAttachmentItem,
            calendar.OutlookCalendarAttachmentItem,
            {"event_id": "event"},
            "composition",
        ),
    ],
)
def test_provider_items_work_without_application_fields(
    provider, consumer, context, reuse_strategy
):
    """Check inheritance here; test_graph_calendar_items checks composition."""
    raw = {"id": "resource", "subject": "Subject", "unknown": {"retained": True}}
    item = provider.from_graph(raw, **context)
    if reuse_strategy not in {"inheritance", "composition"}:
        pytest.fail(f"Unknown provider reuse strategy: {reuse_strategy}")
    if reuse_strategy == "inheritance" and not issubclass(consumer, provider):
        pytest.fail("Consumer must reuse the provider item contract")
    if item.raw is not raw or ItemAdapter(item).asdict()["raw"] != raw:
        pytest.fail("Provider item must retain the complete resource")
    forbidden = {
        "run_id",
        "evidence_id",
        "observed_at",
        "source_response_url",
        "observation_kind",
        "profile",
        "surface",
        "checkpoint",
    }
    if forbidden.intersection(field.name for field in fields(provider)):
        pytest.fail("Provider defaults must not contain consumer workflow fields")


def test_mail_mapping_preserves_nested_address_and_falsey_values():
    raw = {
        "id": "message",
        "subject": "",
        "isRead": False,
        "sender": {"emailAddress": {"address": "sender@example.com"}},
        "from": {"emailAddress": None},
    }
    item = OutlookMessageItem.from_graph(raw)
    if (item.subject, item.is_read, item.sender_address, item.from_address) != (
        "",
        False,
        "sender@example.com",
        None,
    ):
        pytest.fail("Mail mapper changed falsey or nested address semantics")
    consumer = email.OutlookMailItem.from_graph(
        raw,
        source_response_url="url",
        observed_at="now",
        observation_kind="discovery",
        evidence_id="evidence",
        run_id="run",
    )
    if consumer.raw is not raw or consumer.run_id != "run":
        pytest.fail("Inherited mapper must accept consumer provenance fields")


def test_folder_and_attachment_mapping_preserves_provider_fields():
    folder = OutlookMailFolderItem.from_graph(
        {
            "id": "folder",
            "displayName": "Inbox",
            "childFolderCount": 0,
            "totalItemCount": 12,
            "unreadItemCount": 0,
            "isHidden": False,
        }
    )
    if (folder.child_folder_count, folder.unread_item_count, folder.is_hidden) != (
        0,
        0,
        False,
    ):
        pytest.fail("Folder mapper must preserve zero and false values")
    raw = {
        "id": "attachment",
        "@odata.type": "#microsoft.graph.fileAttachment",
        "contentBytes": "AAAA",
    }
    item = OutlookAttachmentItem.from_graph(raw, message_id="message")
    if item.attachment_type != raw["@odata.type"] or item.raw is not raw:
        pytest.fail("Provider attachment mapper must not apply storage policy")


def test_added_mail_provenance_preserves_legacy_constructor_arguments():
    """Original positional fields still construct with absent optional pins."""
    detail = email.OutlookMailDetailItem("message", {}, "url", "time", None, "run")
    attachment = email.OutlookAttachmentItem(
        "message", "attachment", "type", {}, "url", "time", None, "run"
    )
    if detail.selection_id is not None:
        pytest.fail("Optional detail selection changed its legacy default")
    for name in (
        "resource_version",
        "primary_observed_at",
        "selection_id",
        "parent_evidence_id",
        "capture_id",
    ):
        if getattr(attachment, name) is not None:
            pytest.fail("Optional attachment binding changed legacy defaults")
