"""P2-01 review fixes: late parts, defects, skipped HTML elements."""

from __future__ import annotations

import pytest

from msgloom.a2_kedro.parsers import part_bytes
from msgloom.a2_kedro.parsers.mime_html import parse_mime
from msgloom.contracts import TerminalStatus
from tests.a2_kedro.test_p2_01 import (
    assert_equal,
    by_path,
    check_windows,
    codes,
    html_part,
    multipart,
    plain,
)

# --- review fixes ----------------------------------------------------------


def test_part_after_close_delimiter_is_kept_and_flagged() -> None:
    first, lost = plain("first"), plain("LOST")
    data = multipart("mixed", "B", first)
    data += b"--B\r\n" + lost + b"\r\n--B--\r\n"
    result = parse_mime(data)
    assert_equal(result.status, TerminalStatus.INCOMPLETE)
    if "multipart_malformed" not in codes(result):
        pytest.fail("part after close is not flagged")
    assert_equal([p.path for p in result.parts], ["1", "1.1", "1.2"])
    if b"LOST" not in part_bytes(data, by_path(result, "1.2")):
        pytest.fail("late part bytes were dropped")
    check_windows(data, result)


def test_second_close_delimiter_is_flagged() -> None:
    data = multipart("mixed", "B", plain("only")) + b"--B--\r\n"
    result = parse_mime(data)
    assert_equal(result.status, TerminalStatus.INCOMPLETE)
    if "multipart_malformed" not in codes(result):
        pytest.fail("second close is not flagged")
    assert_equal(len(result.parts), 2)


@pytest.mark.parametrize(
    "epilogue",
    [b"", b"\r\nepilogue text\r\n", b"-- B\r\n--Bx\r\nsig\r\n", b"x--B--\r\n"],
)
def test_epilogue_after_close_stays_complete(epilogue: bytes) -> None:
    data = multipart("mixed", "B", plain("one"), plain("two")) + epilogue
    result = parse_mime(data)
    assert_equal(result.status, TerminalStatus.COMPLETE)
    assert_equal(len(result.parts), 3)
    assert_equal(result.limitations, ())


def test_content_defect_keeps_receipt_tied_to_resource_limits() -> None:
    # C0-04 allows outcome "partial" only with a limit_hit; a content
    # defect is reported by the limitation list and the result status.
    data = plain("QUJD$$$", extra="\nContent-Transfer-Encoding: base64")
    result = parse_mime(data)
    assert_equal(result.status, TerminalStatus.INCOMPLETE)
    if result.parsed is None:
        pytest.fail("wire record missing")
    assert_equal(
        (result.parsed.receipt.outcome, result.parsed.receipt.limit_hit),
        ("complete", "none"),
    )
    if "base64_corrupt" not in codes(result):
        pytest.fail("corrupt base64 is not flagged")


@pytest.mark.parametrize(
    "source",
    [
        "<p>seen</p><script>hidden()",
        "<p>seen</p><style>p{}",
        "<p>seen</p><title>hidden",
        "<p>seen</p><template><b>hidden</b>",
        "<p>seen</p><template><template>x</template>hidden",
    ],
)
def test_unclosed_skipped_element_is_flagged(source: str) -> None:
    result = parse_mime(html_part(source))
    assert_equal(result.status, TerminalStatus.INCOMPLETE)
    if "html_parse_error" not in codes(result):
        pytest.fail("unclosed skipped element is not flagged")
    text = by_path(result, "1").text or ""
    assert_equal(text.split(), ["seen"])


def test_nested_template_does_not_leak_and_closed_stays_complete() -> None:
    source = "<p>a</p><template>x<template>y</template>z</template><p>b</p>"
    result = parse_mime(html_part(source))
    assert_equal(result.status, TerminalStatus.COMPLETE)
    assert_equal((by_path(result, "1").text or "").split(), ["a", "b"])
    plain_close = "<title>T</title><script>s()</script><p>ok</p>"
    result = parse_mime(html_part(plain_close))
    assert_equal(result.status, TerminalStatus.COMPLETE)
