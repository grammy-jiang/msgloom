"""Qualify exact-target fixture transport before Teams semantic crawls."""

import json
from http.client import HTTPConnection
from urllib.parse import urlsplit

import pytest
from teams_support import FixtureReply, json_reply, serve_graph


def test_exact_targets_binary_headers_and_scripted_failures():
    """Keep opaque target distinctions and exact response bytes observable."""
    first = "/v1.0/opaque?$skiptoken=a%2fb%2F&x=+&x=%20"
    different = first.replace("%2f", "%2F")
    body = b"\x00\xffimage\r\n"
    with serve_graph() as fixture:
        fixture.add(
            first,
            json_reply(
                {"error": {"code": "TooManyRequests"}},
                status=429,
                headers=(("Retry-After", "0"),),
            ),
            FixtureReply(200, body, (("X-Fixture", "a"), ("X-Fixture", "b"))),
        )
        address = urlsplit(fixture.origin)
        connection = HTTPConnection("127.0.0.1", address.port, timeout=5)
        try:
            for status in (429, 200, 200):
                connection.request("GET", first, headers={"Accept": "image/*"})
                response = connection.getresponse()
                content = response.read()
                if response.status != status:
                    pytest.fail("Scripted response sequence changed")
                if status == 200 and content != body:
                    pytest.fail("Binary fixture bytes changed")
                if status == 200 and response.getheader("X-Fixture") != "a, b":
                    pytest.fail("Repeated response headers were lost")
            connection.request("GET", different)
            response = connection.getresponse()
            payload = json.loads(response.read())
            if (
                response.status != 404
                or payload["error"]["code"] != "FixtureRouteMissing"
            ):
                pytest.fail("Fixture normalized a distinct opaque target")
        finally:
            connection.close()
        seen = fixture.seen
        if [request.target for request in seen] != [first, first, first, different]:
            pytest.fail("Arrival targets changed")
        if seen[0].header("accept") != ("image/*",):
            pytest.fail("Request headers were lost")
        if seen[0].header("Authorization"):
            pytest.fail("Fixture unexpectedly received authorization")


def test_route_replacement_and_payload_links_are_literal():
    """Repeat acquisition can change a response without rewriting its links."""
    with serve_graph() as fixture:
        target = "/v1.0/messages"
        opaque = fixture.url("/next?b=2&a=%2f")
        fixture.add(target, json_reply({"@odata.nextLink": opaque, "value": []}))
        address = urlsplit(fixture.origin)
        connection = HTTPConnection("127.0.0.1", address.port, timeout=5)
        try:
            connection.request("GET", target)
            response = connection.getresponse()
            if json.loads(response.read())["@odata.nextLink"] != opaque:
                pytest.fail("Fixture rewrote a nextLink")
            fixture.add(target, FixtureReply(410, b"gone"))
            connection.request("GET", target)
            response = connection.getresponse()
            if response.status != 410 or response.read() != b"gone":
                pytest.fail("Route replacement retained old state")
        finally:
            connection.close()


@pytest.mark.parametrize("retry_status", [429, 503])
def test_native_graph_crawl_retries_and_replays_opaque_links(tmp_path, retry_status):
    """Qualify shared transport using the existing To Do application spider.

    This test proves only the harness and established Graph transport. Teams
    semantic acceptance still requires its dedicated chat/channel crawls.
    """
    from sqlalchemy import select
    from teams_support import crawl

    from message_ingest.catalog import Catalog
    from message_ingest.catalog.models.acquisition import RawHttpEvidence

    target = "/v1.0/me/todo/lists?%24top=2"
    next_target = "/v1.0/opaque?$skiptoken=a%2fb%2F&x=+&x=%20"
    with serve_graph() as fixture:
        fixture.add(
            target,
            json_reply(
                {"error": {"code": "ServiceUnavailable"}},
                status=retry_status,
                headers=(("Retry-After", "0"),),
            ),
            json_reply({"value": [], "@odata.nextLink": fixture.url(next_target)}),
        )
        fixture.add(next_target, json_reply({"value": []}))
        result = crawl(
            tmp_path,
            fixture,
            ["microsoft", "todo", "discover", "--page-size", "2"],
            extra_settings={"MSGLOOM_TODO_SOURCE_ID": "teams-harness-probe"},
        )
        if result.returncode or "ERROR" in result.stderr:
            pytest.fail(result.stderr[-6000:])
        if [request.target for request in fixture.seen] != [
            target,
            target,
            next_target,
        ]:
            pytest.fail("Native retry/pagination did not preserve exact targets")
        if any(request.header("Authorization") for request in fixture.seen):
            pytest.fail("Auth-disabled fixture received credentials")
        for component in (
            "MicrosoftGraphErrorMiddleware",
            "PrivacySafeRetryMiddleware",
            "RepresentationAwareRequestFingerprinter",
            "MicrosoftGraphIntegrityExtension",
        ):
            if component not in result.stderr:
                pytest.fail(f"Native component missing: {component}")
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            rows = session.scalars(select(RawHttpEvidence)).all()
            if len(rows) != 2 or any(row.response_status != 200 for row in rows):
                pytest.fail("Evidence must retain the two final visible responses")
            if any(row.source_id != "teams-harness-probe" for row in rows):
                pytest.fail("Evidence escaped its fixture source")
            if {row.request_url for row in rows} != {
                fixture.url(target),
                fixture.url(next_target),
            }:
                pytest.fail("Persisted evidence changed opaque request URLs")
    finally:
        catalog.close()
