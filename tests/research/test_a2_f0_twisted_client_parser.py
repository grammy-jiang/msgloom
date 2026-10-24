"""Loopback tests: Scrapy downloads use Twisted's HTTP client parser.

The tests separate two Twisted classes. ``HTTPClientParser`` parses
responses and is used by the Scrapy download path. ``HTTPChannel`` is the
server-side request receiver named by GHSA-q7qq-6mhp-9rc4. A Scrapy download
must not build it.

Each crawl runs in a fresh interpreter, because the Twisted reactor cannot
restart. The server listens on ``127.0.0.1`` with an ephemeral port. No
external host and no Graph service is involved.
"""

from __future__ import annotations

import inspect
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "scripts" / "research" / "a2_f0_twisted_client_probe.py"


def _run_probe(mode: str) -> dict[str, Any]:
    """Run the probe in a fresh interpreter and return its JSON facts."""
    result = subprocess.run(
        [sys.executable, "-B", str(PROBE), "--mode", mode],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=ROOT,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(f"probe exit {result.returncode}: {result.stderr[-400:]}")
    return json.loads(result.stdout)


@pytest.fixture(scope="module")
def plain() -> dict[str, Any]:
    """Facts from a crawl with a well-formed response."""
    return _run_probe("plain")


@pytest.fixture(scope="module")
def bare_lf() -> dict[str, Any]:
    """Facts from a crawl whose response header holds a bare LF."""
    return _run_probe("bare-lf")


def test_download_completes_over_loopback(plain: dict[str, Any]) -> None:
    if plain.get("status") != 200 or plain.get("body") != "ok":
        pytest.fail(f"crawl did not complete: {plain}")


def test_http_scheme_uses_http11_download_handler(plain: dict[str, Any]) -> None:
    if plain.get("handler") != "HTTP11DownloadHandler":
        pytest.fail(f"unexpected handler: {plain.get('handler')}")


def test_download_builds_twisted_client_parser(plain: dict[str, Any]) -> None:
    if plain["parser_built"] < 1:
        pytest.fail("HTTPClientParser was never built")


def test_download_feeds_scrapy_subclass_of_client_parser(
    plain: dict[str, Any],
) -> None:
    # Scrapy swaps the parser class after Twisted builds it.
    if plain["parser_receivers"] != ["_LenientHTTPClientParser"]:
        pytest.fail(f"unexpected receivers: {plain['parser_receivers']}")


def test_download_never_builds_server_side_http_channel(
    plain: dict[str, Any], bare_lf: dict[str, Any]
) -> None:
    if plain["http_channels"] != 0 or bare_lf["http_channels"] != 0:
        pytest.fail("a download built twisted.web.http.HTTPChannel")


def test_client_parser_splits_header_lines_on_bare_lf(
    bare_lf: dict[str, Any],
) -> None:
    # Observation, not a safety claim: the client parser delimiter is LF.
    # The advisory mechanism needs a CRLF-only line split, as in HTTPChannel.
    headers = bare_lf["headers"]
    if headers.get("X-Fold") != ["a"] or headers.get("X-Hidden") != ["b"]:
        pytest.fail(f"unexpected header split: {headers}")


def test_installed_sources_keep_the_claimed_structure() -> None:
    from scrapy.core.downloader.handlers import http11
    from twisted.web import _newclient
    from twisted.web import http as twisted_http

    if not issubclass(http11._LenientHTTPClientParser, _newclient.HTTPClientParser):
        pytest.fail("Scrapy parser no longer extends HTTPClientParser")
    if _newclient.HTTPParser.delimiter != b"\n":
        pytest.fail("client parser delimiter changed")
    if twisted_http.HTTPChannel.delimiter != b"\r\n":
        pytest.fail("server channel delimiter changed")
    source = inspect.getsource(http11)
    if "HTTPChannel" in source:
        pytest.fail("Scrapy HTTP/1.1 handler now references HTTPChannel")
