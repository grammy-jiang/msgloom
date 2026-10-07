"""Keep selected Mail fields in msgloom without changing request bytes."""

from urllib.parse import urlencode

import pytest
from scrapy.utils.test import get_crawler

from message_ingest.spiders.microsoft.outlook.email.discover import (
    OutlookDiscoverSpider as ApplicationMail,
)
from microsoft_graph.spiders.outlook.mail import OutlookMailSpider as ProviderMail

DISCOVERY_FIELDS = (
    "id",
    "subject",
    "from",
    "sender",
    "toRecipients",
    "ccRecipients",
    "bccRecipients",
    "replyTo",
    "receivedDateTime",
    "sentDateTime",
    "createdDateTime",
    "lastModifiedDateTime",
    "changeKey",
    "importance",
    "isRead",
    "isDraft",
    "hasAttachments",
    "conversationId",
    "conversationIndex",
    "inferenceClassification",
    "flag",
    "categories",
    "bodyPreview",
    "parentFolderId",
    "webLink",
    "internetMessageId",
)
FULL_FIELDS = DISCOVERY_FIELDS + (
    "body",
    "internetMessageHeaders",
    "isDeliveryReceiptRequested",
    "isReadReceiptRequested",
    "uniqueBody",
)
FOLDER_FIELDS = (
    "id",
    "displayName",
    "parentFolderId",
    "childFolderCount",
    "totalItemCount",
    "unreadItemCount",
    "isHidden",
)


def test_provider_does_not_select_a_mail_acquisition_profile():
    for name in ("discovery_fields", "full_fields", "folder_fields"):
        if hasattr(ProviderMail, name):
            pytest.fail(f"Provider owns selected application profile: {name}")


def test_application_profile_preserves_selected_fields_and_wire_queries():
    crawler = get_crawler(ApplicationMail)
    mail = ApplicationMail.from_crawler(crawler, name="profile")
    cases = (
        (mail.discovery_fields, DISCOVERY_FIELDS, mail.messages_path),
        (mail.full_fields, FULL_FIELDS, lambda **kw: mail.message_path("m", **kw)),
        (mail.folder_fields, FOLDER_FIELDS, mail.mail_folder_delta_path),
    )
    for actual, expected, path in cases:
        if actual != expected:
            pytest.fail("Selected Mail profile fields or order changed")
        expected_query = urlencode({"$select": ",".join(expected)})
        if not path(fields=actual).endswith("?" + expected_query):
            pytest.fail("Selected Mail request query bytes changed")
