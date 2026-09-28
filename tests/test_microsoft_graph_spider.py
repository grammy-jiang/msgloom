"""Verify Microsoft Graph provider behavior stays resource-neutral."""

from __future__ import annotations

import pytest
from scrapy.http import Request
from scrapy.utils.test import get_crawler
from twisted.python.failure import Failure

from message_ingest.items import AcquisitionFailureItem, RawHttpEvidenceItem
from message_ingest.providers.microsoft_graph import GRAPH_HOST, GRAPH_ROOT
from message_ingest.providers.microsoft_graph.spider import MicrosoftGraphSpider
from message_ingest.spiders.microsoft.outlook.email.discover import (
    OutlookDiscoverSpider,
)


class FixtureGraphSpider(MicrosoftGraphSpider):
    """Minimal non-Mail Graph resource fixture."""

    name = "graph_fixture"

    async def start(self):
        """Keep the native async-generator contract without scheduling work."""
        if False:
            yield None


def _graph_spider() -> FixtureGraphSpider:
    crawler = get_crawler(FixtureGraphSpider)
    return FixtureGraphSpider.from_crawler(crawler)


def _mail_spider() -> OutlookDiscoverSpider:
    crawler = get_crawler(OutlookDiscoverSpider)
    return OutlookDiscoverSpider.from_crawler(crawler)


def test_graph_spider_owns_provider_host_root_and_auth_enablement() -> None:
    spider = _graph_spider()

    if spider.allowed_domains != [GRAPH_HOST]:
        pytest.fail("Expected: spider.allowed_domains == [GRAPH_HOST]")
    if spider.graph_root != GRAPH_ROOT:
        pytest.fail("Expected: spider.graph_root == GRAPH_ROOT")
    if spider.crawler.settings.getbool("MS_GRAPH_AUTH_ENABLED") is not True:
        pytest.fail("Expected Graph Spider to enable Microsoft Graph auth")
    if spider.crawler.settings.getlist("MS_GRAPH_SCOPES") != []:
        pytest.fail("Expected provider base to remain resource-scope neutral")


def test_graph_request_has_no_outlook_prefer_default() -> None:
    spider = _graph_spider()
    request = spider._request(
        f"{spider.graph_root}/me",
        callback=spider.parse,
        purpose="profile",
        cb_kwargs={},
    )

    if not isinstance(request, Request):
        pytest.fail("Expected: isinstance(request, Request)")
    if request.headers.get("Accept") != b"application/json":
        pytest.fail('Expected: request.headers.get("Accept") == b"application/json"')
    if request.headers.get("Prefer") is not None:
        pytest.fail('Expected: request.headers.get("Prefer") is None')
    if request.cb_kwargs != {"purpose": "profile"}:
        pytest.fail('Expected: request.cb_kwargs == {"purpose": "profile"}')


def test_outlook_request_keeps_immutable_id_preference() -> None:
    spider = _mail_spider()
    request = spider._request(
        f"{spider.graph_root}/me/messages",
        callback=spider.parse,
        purpose="message-list",
        cb_kwargs={},
    )

    if request.headers.get("Prefer") != b'IdType="ImmutableId"':
        pytest.fail(
            'Expected: request.headers.get("Prefer") == b\'IdType="ImmutableId"\''
        )


def test_mail_failure_context_uses_only_resource_allowlist() -> None:
    spider = _mail_spider()
    request = spider._request(
        f"{spider.graph_root}/me/messages/m1",
        callback=spider.parse,
        purpose="message-detail",
        cb_kwargs={
            "message_id": "m1",
            "folder_id": "f1",
            "unrelated": "must-not-enter-context",
        },
    )
    failure = Failure(RuntimeError("transport failed"))
    failure.__dict__["request"] = request

    output = list(spider.errback(failure))
    if not isinstance(output[0], RawHttpEvidenceItem):
        pytest.fail("Expected raw evidence before failure item")
    failure_item = next(
        value for value in output if isinstance(value, AcquisitionFailureItem)
    )
    if failure_item.context != {
        "message_id": "m1",
        "folder_id": "f1",
    }:
        pytest.fail(
            "Expected failure context to contain only allowlisted Mail identifiers"
        )
    if "unrelated" in failure_item.context:
        pytest.fail('Expected: "unrelated" not in failure_item.context')


def test_failure_context_rejects_non_string_allowlisted_values() -> None:
    spider = _mail_spider()
    request = spider._request(
        f"{spider.graph_root}/me/messages/m1",
        callback=spider.parse,
        purpose="message-detail",
        cb_kwargs={
            "message_id": {"private": "payload"},
            "folder_id": None,
            "attachment_id": "a1",
        },
    )
    failure = Failure(RuntimeError("transport failed"))
    failure.__dict__["request"] = request

    failure_item = next(
        value
        for value in spider.errback(failure)
        if isinstance(value, AcquisitionFailureItem)
    )
    if failure_item.context != {"attachment_id": "a1"}:
        pytest.fail("Expected only non-empty string identifiers in failure context")


def test_failure_context_is_independent_per_failure_item() -> None:
    spider = _mail_spider()

    def build(message_id: str) -> AcquisitionFailureItem:
        request = spider._request(
            f"{spider.graph_root}/me/messages/{message_id}",
            callback=spider.parse,
            purpose="message-detail",
            cb_kwargs={"message_id": message_id},
        )
        failure = Failure(RuntimeError("transport failed"))
        failure.__dict__["request"] = request
        return next(
            value
            for value in spider.errback(failure)
            if isinstance(value, AcquisitionFailureItem)
        )

    first = build("m1")
    second = build("m2")
    first.context["message_id"] = "changed"

    if second.context != {"message_id": "m2"}:
        pytest.fail("Expected failure context dictionaries to be independent")


def test_inherited_graph_request_callbacks_round_trip_on_fresh_spider() -> None:
    import pickle

    from scrapy.utils.request import request_from_dict

    source = _mail_spider()
    request = source._request(
        f"{source.graph_root}/me/messages",
        callback=source.parse,
        purpose="message-list",
        cb_kwargs={"page_number": 2},
        verbatim_url=True,
    )
    wire = pickle.loads(pickle.dumps(request.to_dict(spider=source)))

    fresh = _mail_spider()
    restored = request_from_dict(wire, spider=fresh)

    if restored.callback != fresh.parse:
        pytest.fail("Expected callback to restore by name on the fresh spider")
    if restored.errback != fresh.errback:
        pytest.fail("Expected inherited Graph errback to restore on the fresh spider")
    if restored.cb_kwargs != {
        "page_number": 2,
        "purpose": "message-list",
    }:
        pytest.fail("Expected callback kwargs to survive request serialization")
    if restored.meta.get("verbatim_url") is not True:
        pytest.fail("Expected provider request metadata to survive serialization")
    if restored.headers.get("Prefer") != b'IdType="ImmutableId"':
        pytest.fail("Expected Mail representation header to survive serialization")
