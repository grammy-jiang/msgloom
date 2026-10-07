"""Verify provider attachment mechanics without app completeness policy."""

from urllib.parse import parse_qs, urlsplit

import pytest
from scrapy.utils.request import request_from_dict

from microsoft_graph.protocol.attachments import (
    attachment_list_path,
    attachment_raw_path,
    attachment_type_name,
    item_attachment_path,
)
from microsoft_graph.spiders.outlook import OutlookMailSpider


class AttachmentSpider(OutlookMailSpider):
    name = "attachment_example"

    def parse(self, response, **kwargs):
        return []


@pytest.mark.parametrize(
    "kind,expected",
    [
        (None, "unknown"),
        ("#microsoft.graph.fileAttachment", "fileAttachment"),
        ("microsoft.graph.itemAttachment", "itemAttachment"),
        ("referenceAttachment", "referenceAttachment"),
        ("futureType", "futureType"),
    ],
)
def test_attachment_type_normalization(kind, expected):
    if attachment_type_name(kind) != expected:
        pytest.fail("Normalization must preserve unknown provider types")


def test_attachment_requests_preserve_provider_paths_and_callback_context():
    spider = AttachmentSpider()
    parent = "/users/shared%40example.test/messages/message%2Fone"
    request = spider.graph_request(
        attachment_list_path(parent, page_size=10, fields=("id", "contentBytes")),
        callback=spider.parse,
        cb_kwargs={"id": "message/one"},
    )
    query = parse_qs(urlsplit(request.url).query)
    if query != {"$top": ["10"], "$select": ["id,contentBytes"]}:
        pytest.fail("Provider must honor caller-selected fields and page size")
    raw = spider.graph_request(
        attachment_raw_path(parent, "attachment/one"),
        callback=spider.parse,
        accept="*/*",
    )
    if not raw.url.endswith("/attachments/attachment%2Fone/$value"):
        pytest.fail("Raw attachment ID must be encoded as one path segment")
    if raw.headers.get("Accept") != b"*/*":
        pytest.fail("Raw content must request its byte representation")
    detail = spider.graph_request(
        item_attachment_path(parent, "attachment/one"), callback=spider.parse
    )
    if parse_qs(urlsplit(detail.url).query).get("$expand") != [
        "microsoft.graph.itemattachment/item"
    ]:
        pytest.fail("Item attachment must use Graph's expansion path")
    restored = request_from_dict(request.to_dict(spider=spider), spider=spider)
    if restored.cb_kwargs != {"id": "message/one"}:
        pytest.fail("Consumer traversal context must remain serializable")


def test_attachment_pagination_preserves_opaque_url():
    spider = AttachmentSpider()
    url = "https://graph.microsoft.com/v1.0/next?$skiptoken=a%2fb+%2B"
    request = spider.continuation_request(url, callback=spider.parse)
    if request.url != url or not request.meta.get("verbatim_url"):
        pytest.fail("Attachment next links must remain opaque")


@pytest.mark.parametrize(
    "page_size,expected",
    [(None, "/me/events/e/attachments"), (10, "/me/events/e/attachments?%24top=10")],
)
def test_attachment_list_has_no_implicit_projection(page_size, expected):
    if attachment_list_path("/me/events/e", page_size=page_size) != expected:
        pytest.fail("Provider attachment paths must not select an application profile")
