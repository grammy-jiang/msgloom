"""Prove standalone request, scope, fingerprint, and serialization contracts."""

import hashlib

import pytest
from scrapy import Request
from scrapy.utils.request import fingerprint, request_from_dict
from scrapy.utils.test import get_crawler

from microsoft_graph.scrapy import MicrosoftGraphSpider
from microsoft_graph.scrapy.fingerprints import GraphRequestFingerprinter
from microsoft_graph.scrapy.outlook import OutlookCalendarSpider, OutlookMailSpider
from microsoft_graph.scrapy.request import GRAPH_OPERATION_META_KEY


class ExampleSpider(MicrosoftGraphSpider):
    name = "framework_example"
    graph_permissions = ("User.Read",)

    def parse(self, response, **kwargs):
        return []


def test_request_options_do_not_add_application_context():
    crawler = get_crawler(ExampleSpider)
    spider = ExampleSpider.from_crawler(crawler)
    request = spider.graph_request(
        "/me",
        callback=spider.parse,
        operation="profile",
        cb_kwargs={"page": 1},
        dont_cache=True,
        download_maxsize=4096,
        prefer="custom",
    )
    if request.url != "https://graph.microsoft.com/v1.0/me":
        pytest.fail("Relative Graph endpoints must use the service root")
    if request.cb_kwargs != {"page": 1} or request.headers.get("Prefer") != b"custom":
        pytest.fail("Framework must preserve consumer callback context and headers")
    if request.meta != {
        GRAPH_OPERATION_META_KEY: "profile",
        "dont_cache": True,
        "download_maxsize": 4096,
    }:
        pytest.fail("Expected only explicit transport metadata")
    if crawler.settings.getbool("MS_GRAPH_AUTH_ENABLED") or hasattr(spider, "run_id"):
        pytest.fail("Framework must not force auth or application run identity")
    if crawler.settings.getlist("MS_GRAPH_SCOPES") != ["User.Read"]:
        pytest.fail("Declared scopes must be available to optional auth components")


def test_opaque_continuation_has_named_serializable_callbacks():
    spider = ExampleSpider()
    link = "https://graph.microsoft.com/v1.0/me/contacts?$skiptoken=a%2fb+%2B&x=2&x=1"
    request = spider.continuation_request(link, callback=spider.parse, operation="list")
    saved = request.to_dict(spider=spider)
    restored = request_from_dict(saved, spider=spider)
    if restored.url != link or restored.meta.get("verbatim_url") is not True:
        pytest.fail("Continuation bytes must survive JOBDIR serialization")
    if saved["callback"] != "parse" or saved["errback"] != "errback":
        pytest.fail("Callbacks and errbacks must be stored by name")


def test_service_root_and_consumer_scope_override():
    crawler = get_crawler(
        ExampleSpider,
        settings_dict={
            "MS_GRAPH_SERVICE_ROOT": "https://graph.example/beta",
            "MS_GRAPH_SCOPES": ["consumer"],
        },
    )
    spider = ExampleSpider.from_crawler(crawler)
    if spider.allowed_domains != ["graph.example"]:
        pytest.fail("Allowed domain must follow the service root")
    if spider.graph_request("/me").url != "https://graph.example/beta/me":
        pytest.fail("Service root override must control request construction")
    if crawler.settings.getlist("MS_GRAPH_SCOPES") != ["consumer"]:
        pytest.fail("Explicit consumer scopes must win over declaration defaults")


@pytest.mark.parametrize(
    "base,scopes",
    [
        (OutlookMailSpider, ("Mail.Read", "Mail.Read.Shared")),
        (OutlookCalendarSpider, ("Calendars.Read", "Calendars.Read.Shared")),
    ],
)
@pytest.mark.parametrize("target", ["", "shared/user@example.test"])
def test_mailbox_paths_scopes_and_representation(base, scopes, target):
    class Mailbox(base):
        name = "mailbox"

    crawler = get_crawler(Mailbox, settings_dict={"MS_GRAPH_TARGET_MAILBOX": target})
    spider = Mailbox.from_crawler(crawler)
    expected = "/users/shared%2Fuser%40example.test" if target else "/me"
    if spider._mailbox_path() != expected:
        pytest.fail("Mailbox locator must be encoded as one path segment")
    if crawler.settings.getlist("MS_GRAPH_SCOPES") != [scopes[bool(target)]]:
        pytest.fail("Mailbox declaration must select own/shared scopes")
    request = spider.graph_request(spider._mailbox_url("/messages"))
    expected_prefer = b'IdType="ImmutableId"' if base is OutlookMailSpider else None
    if request.headers.get("Prefer") != expected_prefer:
        pytest.fail("Mail alone defaults to immutable IDs")
    if spider.graph_request("/me", prefer=None).headers.get("Prefer") is not None:
        pytest.fail("Consumer must be able to suppress the default preference")


def test_fingerprints_match_native_header_algorithm_and_msgloom_v1():
    from message_ingest.fingerprints.microsoft_graph import (
        RepresentationAwareRequestFingerprinter,
    )

    request = Request(
        "https://graph.microsoft.com/v1.0/me",
        headers={
            "Accept": "application/json",
            "Prefer": 'IdType="ImmutableId"',
            "Authorization": "Bearer first",
        },
    )
    base = fingerprint(request, include_headers=("Accept", "Prefer"))
    framework = GraphRequestFingerprinter()
    if framework.fingerprint(request) != base:
        pytest.fail("Framework fingerprint must use Scrapy's native helper")
    second = request.replace(
        headers={**dict(request.headers), "Authorization": "other"}
    )
    if framework.fingerprint(second) != base:
        pytest.fail("Authorization must not affect representation identity")
    digest = b"source"
    expected = hashlib.sha256(
        b"msgloom-graph-fingerprint-v1\0" + digest + b"\0" + base
    ).digest()
    if RepresentationAwareRequestFingerprinter(digest).fingerprint(request) != expected:
        pytest.fail("Msgloom fingerprint bytes must remain version 1 compatible")


def test_non_graph_fingerprint_uses_native_identity():
    request = Request("https://example.test/me", headers={"Prefer": "anything"})
    if GraphRequestFingerprinter().fingerprint(request) != fingerprint(request):
        pytest.fail("Other hosts must retain native identity")


def test_msgloom_custom_service_root_preserves_source_and_header_isolation():
    from message_ingest.fingerprints.microsoft_graph import (
        RepresentationAwareRequestFingerprinter,
    )

    def scoped(source):
        crawler = get_crawler(
            ExampleSpider,
            settings_dict={
                "MS_GRAPH_SERVICE_ROOT": "https://graph.example/v1.0",
                "MSGLOOM_SOURCE_ID": source,
                "MSGLOOM_DATABASE_URL": "sqlite:///:memory:",
            },
        )
        return RepresentationAwareRequestFingerprinter.from_crawler(crawler)

    request = Request(
        "https://graph.example/v1.0/me", headers={"Accept": "application/json"}
    )
    source = scoped("first")
    if source.fingerprint(request) == scoped("second").fingerprint(request):
        pytest.fail("Configured Graph roots must preserve source isolation")
    raw = request.replace(headers={"Accept": "message/rfc822"})
    if source.fingerprint(request) == source.fingerprint(raw):
        pytest.fail("Configured Graph roots must preserve representation isolation")
