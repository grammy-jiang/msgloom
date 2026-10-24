"""P2-01 MIME/HTML parser: structure, offsets, limitations and privacy."""

from __future__ import annotations

import base64
import socket
from typing import Any

import pytest

from msgloom.a2_kedro.contracts.codec import A2ContractError
from msgloom.a2_kedro.contracts.extract import ComponentEntry, ExtractedComponents
from msgloom.a2_kedro.contracts.parse import ParsedParts
from msgloom.a2_kedro.parsers import MimeParseResult, MimePart, mime_html, part_bytes
from msgloom.a2_kedro.parsers.mime_html import parse_mime
from msgloom.contracts import TerminalStatus

SENTINEL = "alice.private@example.invalid"
HEAD = b"From: a@example.invalid\r\nSubject: s\r\n"


def entity(headers: str, body: bytes | str) -> bytes:
    raw = body.encode() if isinstance(body, str) else body
    return headers.replace("\n", "\r\n").encode() + b"\r\n\r\n" + raw


def multipart(kind: str, boundary: str, *children: bytes, close: bool = True) -> bytes:
    head = f"Content-Type: multipart/{kind}; boundary={boundary}\r\n".encode()
    out = HEAD + head + b"\r\n"
    for child in children:
        out += b"--" + boundary.encode() + b"\r\n" + child + b"\r\n"
    return out + (b"--" + boundary.encode() + b"--\r\n" if close else b"")


def plain(text: str, charset: str = "utf-8", extra: str = "") -> bytes:
    return entity(f"Content-Type: text/plain; charset={charset}{extra}", text)


def html_part(text: str) -> bytes:
    return entity("Content-Type: text/html; charset=utf-8", text)


def codes(result: MimeParseResult) -> set[str]:
    return {item.code for item in result.limitations}


def by_path(result: MimeParseResult, path: str) -> MimePart:
    for part in result.parts:
        if part.path == path:
            return part
    pytest.fail("part path not found")


def check_windows(data: bytes, result: MimeParseResult) -> None:
    """Every window is inside the input and inside its parent window."""
    paths = {p.path: p for p in result.parts}
    for part in result.parts:
        if not 0 <= part.start <= part.body_start <= part.end <= len(data):
            pytest.fail("window is outside the input")
        parent = paths.get(part.parent or "")
        if parent and not parent.start <= part.start <= part.end <= parent.end:
            pytest.fail("child window is outside its parent")
    if (result.status is TerminalStatus.COMPLETE) == bool(result.limitations):
        pytest.fail("status conflicts with limitations")


# --- positive cases --------------------------------------------------------


def test_single_plain_part_is_complete_and_traceable() -> None:
    data = entity("Content-Type: text/plain; charset=utf-8", "hello world")
    result = parse_mime(data)
    root = by_path(result, "1")
    assert_equal(result.status, TerminalStatus.COMPLETE)
    assert_equal(result.body_status, "present")
    assert_equal((root.start, root.end), (0, len(data)))
    assert_equal(data[root.body_start : root.end], b"hello world")
    assert_equal(root.text, "hello world")
    assert_equal(part_bytes(data, root), data)
    assert_equal(result.input_size, len(data))
    assert_equal(len(result.input_sha256), 64)


def assert_equal(left: Any, right: Any) -> None:
    if left != right:
        pytest.fail(f"{left!r:.200} != {right!r:.200}")


def test_alternative_parts_are_ordered_with_offsets() -> None:
    data = multipart(
        "alternative", "AAA", plain("plain text"), html_part("<p>html</p>")
    )
    result = parse_mime(data)
    assert_equal([p.path for p in result.parts], ["1", "1.1", "1.2"])
    assert_equal([p.role for p in result.parts], ["body", "body", "alternate"])
    assert_equal(
        [p.content_type for p in result.parts][1:], ["text/plain", "text/html"]
    )
    assert_equal(by_path(result, "1.1").charset, "utf-8")
    first, second = by_path(result, "1.1"), by_path(result, "1.2")
    if not first.end < second.start:
        pytest.fail("child windows overlap")
    assert_equal(data[first.body_start : first.end], b"plain text")
    assert_equal(data[second.body_start : second.end], b"<p>html</p>")
    assert_equal(result.status, TerminalStatus.COMPLETE)
    check_windows(data, result)


def test_nested_multipart_and_wire_record_validate() -> None:
    inner = multipart("alternative", "BBB", plain("one"), html_part("<b>two</b>"))
    inner_entity = inner[len(HEAD) :]
    pdf = entity(
        'Content-Type: application/pdf\nContent-Disposition: attachment; filename="a.pdf"\n'
        "Content-Transfer-Encoding: base64",
        base64.b64encode(b"%PDF-1.4 fake"),
    )
    data = multipart("mixed", "AAA", inner_entity, pdf)
    result = parse_mime(data, component_id="msg-1")
    assert_equal([p.path for p in result.parts], ["1", "1.1", "1.1.1", "1.1.2", "1.2"])
    assert_equal(by_path(result, "1.2").role, "attachment")
    assert_equal(by_path(result, "1.1.2").parent, "1.1")
    assert_equal(result.status, TerminalStatus.COMPLETE)
    parsed = result.parsed
    if parsed is None:
        pytest.fail("wire record missing")
    assert_equal([p.part_id for p in parsed.parts], [p.path for p in result.parts])
    assert_equal(parsed.parts[4].detected_format, "pdf")
    assert_equal(parsed.parts[2].parent_part_id, "1.1")
    assert_equal(parsed.receipt.outcome, "complete")
    assert_equal(ParsedParts.decode(parsed.encode()), parsed)
    extracted = ExtractedComponents(
        components=(
            ComponentEntry(
                component_id="msg-1",
                role="primary",
                status="present",
                reference="saved://x",
                sha256=result.input_sha256,
            ),
        )
    )
    parsed.validate_against(extracted)
    check_windows(data, result)


def test_charsets_and_transfer_encodings_decode() -> None:
    qp = entity(
        "Content-Type: text/plain; charset=iso-8859-1\nContent-Transfer-Encoding: quoted-printable",
        "caf=E9 =\r\nok",
    )
    b64 = entity(
        "Content-Type: text/plain; charset=utf-8\nContent-Transfer-Encoding: base64",
        base64.b64encode("naïve".encode()),
    )
    result = parse_mime(multipart("mixed", "M", qp, b64))
    assert_equal(by_path(result, "1.1").text, "café ok")
    assert_equal(by_path(result, "1.2").text, "naïve")
    assert_equal(result.status, TerminalStatus.COMPLETE)


def test_inline_reply_marks_quotes_without_deleting_text() -> None:
    text = "My answer\n> old line\n>> older\nmore\n> again\n"
    result = parse_mime(plain(text))
    part = by_path(result, "1")
    assert_equal(part.text, text)
    marks = [(part.text or "")[r.start : r.end] for r in part.quoted]
    assert_equal(marks, ["> old line\n>> older", "> again"])
    assert_equal([r.depth for r in part.quoted], [2, 1])
    assert_equal({r.kind for r in part.quoted}, {"marker"})


def test_html_is_reduced_without_script_style_or_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(*_args: Any, **_kwargs: Any) -> None:
        pytest.fail("network use")

    monkeypatch.setattr(socket, "socket", refuse)
    source = (
        "<html><head><title>T</title><style>p{color:red}</style></head><body>"
        '<script>evil()</script><img src="http://x.invalid/a.png">'
        '<p>Hi &amp; <a href="http://x.invalid/">bye</a></p>'
        "<blockquote>quoted</blockquote></body></html>"
    )
    result = parse_mime(html_part(source))
    part = by_path(result, "1")
    text = part.text or ""
    assert_equal(text.split(), ["Hi", "&", "bye", "quoted"])
    for dropped in ("evil", "color", "x.invalid", "T\n"):
        if dropped in text:
            pytest.fail("dropped content leaked into text")
    quote = part.quoted[0]
    assert_equal(text[quote.start : quote.end].strip(), "quoted")
    assert_equal(quote.kind, "blockquote")
    # Each mapped span points at the markup that produced it.
    raw = {
        text[s.text_start : s.text_end]: source[s.source_start : s.source_end]
        for s in part.text_map
    }
    assert_equal(raw["&"], "&amp;")
    if any(s.source_end > len(source) for s in part.text_map):
        pytest.fail("map leaves the decoded body")


def test_attached_message_is_embedded() -> None:
    inner = entity("Content-Type: text/plain", "inner body")
    outer = entity("Content-Type: message/rfc822", inner)
    data = multipart("mixed", "O", plain("outer body"), outer)
    result = parse_mime(data)
    assert_equal([p.path for p in result.parts], ["1", "1.1", "1.2", "1.2.1"])
    assert_equal(by_path(result, "1.2").role, "embedded")
    assert_equal(by_path(result, "1.2.1").role, "embedded")
    assert_equal(by_path(result, "1.2.1").text, "inner body")
    assert_equal(result.status, TerminalStatus.COMPLETE)


def test_same_bytes_give_same_result() -> None:
    data = multipart("alternative", "AAA", plain("a\n> b"), html_part("<p>x</p>"))
    assert_equal(parse_mime(data), parse_mime(data))


# --- negative cases: limitation, never silent loss -------------------------


def test_missing_boundary_parameter_is_flagged_and_kept() -> None:
    data = HEAD + b"Content-Type: multipart/mixed\r\n\r\n--X\r\nhello\r\n--X--\r\n"
    result = parse_mime(data)
    assert_equal(result.status, TerminalStatus.INCOMPLETE)
    if "multipart_malformed" not in codes(result):
        pytest.fail("malformed boundary is not flagged")
    assert_equal(len(result.parts), 1)
    assert_equal(result.body_status, "missing")
    check_windows(data, result)


def test_boundary_absent_from_body_is_flagged() -> None:
    data = HEAD + b"Content-Type: multipart/mixed; boundary=ZZ\r\n\r\nno delimiters\r\n"
    result = parse_mime(data)
    if not {"multipart_malformed", "body_absent"} <= codes(result):
        pytest.fail("missing delimiter is not flagged")
    assert_equal(result.status, TerminalStatus.INCOMPLETE)


def test_truncated_multipart_keeps_last_part_and_flags() -> None:
    data = multipart("alternative", "T", plain("first"), plain("cut off"), close=False)
    data = data[: data.index(b"cut off") + 3]
    result = parse_mime(data)
    assert_equal(result.status, TerminalStatus.INCOMPLETE)
    if "multipart_truncated" not in codes(result):
        pytest.fail("truncation is not flagged")
    assert_equal(len(result.parts), 3)
    assert_equal(by_path(result, "1.2").end, len(data))
    assert_equal(result.body_status, "present")
    check_windows(data, result)


@pytest.mark.parametrize("charset", ["x-no-such-charset", "hex", "base64"])
def test_unknown_or_non_text_charset_is_flagged(charset: str) -> None:
    result = parse_mime(plain("café", charset=charset))
    assert_equal(result.status, TerminalStatus.INCOMPLETE)
    if "charset_unknown" not in codes(result):
        pytest.fail("charset is not flagged")
    assert_equal(by_path(result, "1").text, "café")


def test_undecodable_bytes_are_replaced_and_flagged() -> None:
    result = parse_mime(
        entity("Content-Type: text/plain; charset=utf-8", b"ok \xff\xfe")
    )
    assert_equal(result.status, TerminalStatus.INCOMPLETE)
    if "charset_decode_error" not in codes(result):
        pytest.fail("decode error is not flagged")
    assert_equal((by_path(result, "1").text or "")[:3], "ok ")


def test_bad_base64_is_flagged_and_part_is_kept() -> None:
    good = base64.b64encode(b"hello there world")
    body = good[:8] + b"!!!" + good[8:]
    part = entity(
        "Content-Type: text/plain; charset=utf-8\nContent-Transfer-Encoding: base64",
        body,
    )
    result = parse_mime(part)
    if "base64_corrupt" not in codes(result):
        pytest.fail("bad base64 is not flagged")
    assert_equal(result.status, TerminalStatus.INCOMPLETE)
    assert_equal(len(result.parts), 1)
    assert_equal((by_path(result, "1").text or "")[:5], "hello")


def test_bad_quoted_printable_and_unknown_encoding_are_flagged() -> None:
    qp = entity(
        "Content-Type: text/plain\nContent-Transfer-Encoding: quoted-printable", "a=ZZb"
    )
    odd = entity("Content-Type: text/plain\nContent-Transfer-Encoding: x-odd", "body")
    assert_equal(codes(parse_mime(qp)), {"qp_corrupt"})
    assert_equal(codes(parse_mime(odd)), {"cte_unknown"})


def test_zero_byte_input_is_missing_not_complete() -> None:
    result = parse_mime(b"")
    assert_equal(result.status, TerminalStatus.INCOMPLETE)
    assert_equal(result.body_status, "missing")
    assert_equal(result.parts, ())
    assert_equal(result.parsed, None)
    assert_equal(codes(result), {"input_empty", "body_absent"})


@pytest.mark.parametrize(
    "data",
    [
        HEAD,
        entity("Content-Type: text/plain", "  \r\n \r\n"),
        multipart("mixed", "M", entity("Content-Type: image/png", b"\x89PNG")),
    ],
)
def test_message_without_body_is_missing(data: bytes) -> None:
    result = parse_mime(data)
    assert_equal(result.body_status, "missing")
    assert_equal(result.status, TerminalStatus.INCOMPLETE)
    if "body_absent" not in codes(result):
        pytest.fail("missing body is not named")


def test_unrepresentable_part_is_listed_and_flagged() -> None:
    blob = entity("Content-Type: application/zip", b"PK\x03\x04")
    data = multipart("mixed", "M", plain("hi"), blob)
    result = parse_mime(data)
    assert_equal(by_path(result, "1.2").format, None)
    if "attachment_unsupported" not in codes(result):
        pytest.fail("unsupported part is not flagged")
    if result.parsed is None or "1.2" in {p.part_id for p in result.parsed.parts}:
        pytest.fail("unsupported part reached the wire record")


def test_part_over_size_limit_is_flagged_not_decoded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(mime_html, "MAX_PART_BYTES", 16)
    result = parse_mime(plain("x" * 100))
    assert_equal(by_path(result, "1").text, None)
    assert_equal(result.body_status, "partial")
    assert_equal(result.status, TerminalStatus.INCOMPLETE)
    if result.parsed is None:
        pytest.fail("wire record missing")
    assert_equal(
        (result.parsed.receipt.outcome, result.parsed.receipt.limit_hit),
        ("partial", "bytes"),
    )


def test_input_over_size_limit_lists_root_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mime_html, "MAX_INPUT_BYTES", 32)
    data = plain("y" * 100)
    result = parse_mime(data)
    assert_equal([p.path for p in result.parts], ["1"])
    assert_equal(codes(result), {"input_too_large"})
    assert_equal(result.body_status, "partial")
    assert_equal((by_path(result, "1").start, by_path(result, "1").end), (0, len(data)))


def test_part_count_and_depth_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    many = multipart("mixed", "M", *[plain(f"p{i}") for i in range(6)])
    monkeypatch.setattr(mime_html, "MAX_PARTS", 3)
    result = parse_mime(many)
    assert_equal(len(result.parts), 3)
    if "part_limit" not in codes(result):
        pytest.fail("part limit is not flagged")
    monkeypatch.setattr(mime_html, "MAX_PARTS", 256)
    monkeypatch.setattr(mime_html, "MAX_DEPTH", 1)
    deep = multipart(
        "mixed",
        "A",
        multipart("mixed", "B", multipart("mixed", "C", plain("x")))[len(HEAD) :],
    )
    result = parse_mime(deep)
    if "depth_limit" not in codes(result):
        pytest.fail("depth limit is not flagged")
    assert_equal(result.status, TerminalStatus.INCOMPLETE)


def test_every_prefix_and_byte_flip_parses_without_error() -> None:
    sample = multipart(
        "mixed",
        "B1",
        multipart("alternative", "B2", plain("a\n> b"), html_part("<p>&#x41;<i>"))[
            len(HEAD) :
        ],
        entity(
            "Content-Type: application/pdf\nContent-Transfer-Encoding: base64", b"QUJD"
        ),
    )
    for size in range(len(sample) + 1):
        check_windows(sample[:size], parse_mime(sample[:size]))
    for index in range(0, len(sample), 3):
        mutated = sample[:index] + b"\xff\x00=" + sample[index + 1 :]
        check_windows(mutated, parse_mime(mutated))


# --- argument errors and privacy -------------------------------------------


def test_bad_arguments_raise_fixed_messages_without_echo() -> None:
    with pytest.raises(A2ContractError) as first:
        parse_mime(SENTINEL)  # type: ignore[arg-type]
    with pytest.raises(A2ContractError) as second:
        parse_mime(b"x", component_id="")
    for error in (first, second):
        if SENTINEL in str(error.value) or SENTINEL in repr(error.value):
            pytest.fail("exception echoed input")


def test_repr_and_limitations_do_not_echo_body_text() -> None:
    bad = entity(
        "Content-Type: text/plain; charset=x-no-such-charset\nContent-Transfer-Encoding: quoted-printable",
        f"{SENTINEL} =ZZ\n> {SENTINEL}",
    )
    html_bad = html_part(f"<p>{SENTINEL}</p>")
    data = multipart("mixed", "P", bad, html_bad)
    result = parse_mime(data)
    if not result.limitations:
        pytest.fail("expected limitations")
    if SENTINEL not in (by_path(result, "1.2").text or ""):
        pytest.fail("text should stay available in memory")
    shown = [repr(result), str(result), repr(result.parts), repr(result.limitations)]
    shown += [repr(result.parsed), str(result.parsed)]
    if result.parsed is not None:
        shown.append(repr(result.parsed.encode()))
    for value in shown:
        if SENTINEL in value or "alice" in value:
            pytest.fail("body text leaked into a representation")


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
