"""
Separate Graph representations while retaining native identity for other hosts.
"""

from __future__ import annotations

import pytest
from scrapy import Request
from scrapy.utils.test import get_crawler

from message_ingest.fingerprints.microsoft_graph import (
    RepresentationAwareRequestFingerprinter,
)
from message_ingest.spiders.microsoft.outlook.email.discover import (
    OutlookDiscoverSpider,
)


def _fingerprinter() -> RepresentationAwareRequestFingerprinter:
    crawler = get_crawler(
        OutlookDiscoverSpider,
        settings_dict={
            "MSGLOOM_SOURCE_ID": "fingerprint-test-source",
            "MSGLOOM_DATABASE_URL": "sqlite:///:memory:",
        },
    )
    return RepresentationAwareRequestFingerprinter.from_crawler(crawler)


def test_graph_accept_header_changes_request_identity() -> None:
    fingerprinter = _fingerprinter()
    json_request = Request(
        "https://graph.microsoft.com/v1.0/me/messages/1/$value",
        headers={"Accept": "application/json"},
    )
    mime_request = Request(
        "https://graph.microsoft.com/v1.0/me/messages/1/$value",
        headers={"Accept": "message/rfc822"},
    )
    if fingerprinter.fingerprint(json_request) == fingerprinter.fingerprint(
        mime_request
    ):
        pytest.fail(
            "Expected: fingerprinter.fingerprint(json_request) != fingerprinter.fingerprint(mime_request)"
        )


def test_graph_prefer_header_changes_request_identity() -> None:
    fingerprinter = _fingerprinter()
    ordinary = Request("https://graph.microsoft.com/v1.0/me/messages")
    immutable = Request(
        "https://graph.microsoft.com/v1.0/me/messages",
        headers={"Prefer": 'IdType="ImmutableId"'},
    )
    if fingerprinter.fingerprint(ordinary) == fingerprinter.fingerprint(immutable):
        pytest.fail(
            "Expected: fingerprinter.fingerprint(ordinary) != fingerprinter.fingerprint(immutable)"
        )


def test_authorization_token_does_not_change_request_identity() -> None:
    fingerprinter = _fingerprinter()
    one = Request(
        "https://graph.microsoft.com/v1.0/me/messages",
        headers={"Accept": "application/json", "Authorization": "Bearer one"},
    )
    two = Request(
        "https://graph.microsoft.com/v1.0/me/messages",
        headers={"Accept": "application/json", "Authorization": "Bearer two"},
    )
    if fingerprinter.fingerprint(one) != fingerprinter.fingerprint(two):
        pytest.fail(
            "Expected: fingerprinter.fingerprint(one) == fingerprinter.fingerprint(two)"
        )


def test_direct_fingerprinter_construction_requires_source_context() -> None:
    with pytest.raises(ValueError, match="requires source context"):
        RepresentationAwareRequestFingerprinter(b"")
