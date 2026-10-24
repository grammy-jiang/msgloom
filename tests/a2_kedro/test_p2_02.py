"""P2-02 JSON and plain-text parser: positions, null/empty, partial bodies."""

from __future__ import annotations

import pytest

from msgloom.a2_kedro.contracts.codec import A2ContractError, sha256_hex
from msgloom.a2_kedro.contracts.parse import ByteLink, ParsedParts, Part
from msgloom.a2_kedro.parsers import plain_json as pj
from msgloom.a2_kedro.parsers.plain_json import (
    FieldState,
    Limitation,
    Outcome,
    ParseResult,
    PlainJsonInputError,
    parse_json,
    parse_plain_text,
)
from tests.a2_kedro.helpers import check

SECRET = "alice.private@example.invalid"


def limits(result: ParseResult) -> tuple[str, ...]:
    return tuple(item.value for item in result.limitations)


def field_map(result: ParseResult) -> dict[str, tuple[FieldState, str | None]]:
    return {f.pointer: (f.state, f.value) for f in result.fields}


# --- plain text --------------------------------------------------------


def test_plain_text_offsets_for_lf_crlf_cr_are_exact() -> None:
    data = b"one\ntwo\r\nthree\rfour"
    result = parse_plain_text(data)
    check(result.outcome is Outcome.COMPLETE, "plain text is complete")
    got = [
        (line.span.offset, line.span.length, line.ending, line.span.slice(data))
        for line in result.lines
    ]
    want = [
        (0, 3, "lf", b"one"),
        (4, 3, "crlf", b"two"),
        (9, 5, "cr", b"three"),
        (15, 4, "none", b"four"),
    ]
    check(got == want, "line spans and endings are exact")


def test_plain_text_blocks_split_on_blank_lines() -> None:
    data = b"a1\r\na2\r\n\r\n  \t\nb1\n\n\nc1"
    result = parse_plain_text(data)
    spans = [(b.span.slice(data), b.first_line, b.line_count) for b in result.blocks]
    check(
        spans == [(b"a1\r\na2", 0, 2), (b"b1", 4, 1), (b"c1", 7, 1)],
        "blocks hold the exact source bytes",
    )
    check([b.index for b in result.blocks] == [0, 1, 2], "block index ascends")


def test_plain_text_trailing_terminator_makes_no_extra_line() -> None:
    result = parse_plain_text(b"x\n")
    check(len(result.lines) == 1, "no phantom last line")
    check(result.lines[0].ending == "lf", "terminator is kept as ending")


def test_plain_text_bom_is_skipped_but_offsets_count_it() -> None:
    data = b"\xef\xbb\xbfhi\nyo"
    result = parse_plain_text(data)
    check(result.bom, "bom is flagged")
    check(result.outcome is Outcome.COMPLETE, "bom is not a limitation")
    first = result.lines[0].span
    check((first.offset, first.length) == (3, 2), "offset counts the BOM")
    check(first.text(data) == "hi", "text excludes the BOM")


def test_plain_text_invalid_utf8_keeps_byte_offsets_and_flags() -> None:
    data = b"ok\n\xff\xfebad\nend"
    result = parse_plain_text(data)
    check(result.outcome is Outcome.INCOMPLETE, "invalid UTF-8 is incomplete")
    check(limits(result) == ("invalid_utf8",), "limitation is invalid_utf8")
    bad = result.lines[1].span
    check((bad.offset, bad.length) == (3, 5), "offset is in source bytes")
    check(bad.slice(data) == b"\xff\xfebad", "source bytes are exact")
    check(bad.text(data) == "��bad", "text uses replacement")
    check(result.lines[2].span.offset == 9, "later offsets are unshifted")


def test_plain_text_multibyte_offsets_are_bytes_not_characters() -> None:
    data = "café\nnaïve".encode()
    result = parse_plain_text(data)
    check(result.lines[1].span.offset == 6, "offset counts bytes")
    check(result.outcome is Outcome.COMPLETE, "valid UTF-8 is complete")


def test_plain_text_nul_bytes_are_flagged_and_kept() -> None:
    data = b"a\x00b\nc"
    result = parse_plain_text(data)
    check(limits(result) == ("nul_bytes",), "NUL is flagged")
    check(result.outcome is Outcome.INCOMPLETE, "NUL is incomplete")
    check(result.lines[0].span.slice(data) == b"a\x00b", "NUL stays in place")


def test_plain_text_nul_only_line_is_not_blank() -> None:
    result = parse_plain_text(b"\x00\n\nx")
    check(len(result.blocks) == 2, "NUL line is content, not blank")


def test_plain_text_line_bound_gives_limitation(monkeypatch) -> None:
    monkeypatch.setattr(pj, "MAX_LINES", 3)
    result = parse_plain_text(b"a\nb\nc\nd\ne\n")
    check(len(result.lines) == 3, "lines stop at the bound")
    check(limits(result) == ("line_limit",), "bound is a limitation")
    check(result.outcome is Outcome.INCOMPLETE, "bound is incomplete")
    tail = parse_plain_text(b"a\nb\nc\nd")
    check(limits(tail) == ("line_limit",), "unterminated last line is bounded")


def test_plain_text_size_bound_gives_limitation(monkeypatch) -> None:
    monkeypatch.setattr(pj, "MAX_BODY_BYTES", 8)
    result = parse_plain_text(b"0123456789")
    check(limits(result) == ("size_limit",), "size bound is a limitation")
    check(result.outcome is Outcome.INCOMPLETE and not result.lines, "no parse")
    check(result.input_bytes == 10, "size is still reported")


def test_utf16_bom_is_unsupported_not_garbled() -> None:
    for data in (b"\xff\xfeh\x00i\x00", b"\xfe\xff\x00h\x00i"):
        for parse in (parse_plain_text, parse_json):
            result = parse(data)
            check(limits(result) == ("unsupported_encoding",), "wide BOM flagged")
            check(result.outcome is Outcome.INCOMPLETE, "wide BOM is incomplete")


# --- empty bodies ------------------------------------------------------


@pytest.mark.parametrize("data", [b"", b"\xef\xbb\xbf", b" \r\n\t\n"])
@pytest.mark.parametrize("parse", [parse_plain_text, parse_json])
def test_empty_body_is_missing_never_complete(data, parse) -> None:
    result = parse(data)
    check(result.outcome is Outcome.MISSING, "empty body is MISSING")
    check(limits(result) == ("empty_body",), "empty body is explained")
    check(not result.lines and not result.fields, "nothing is invented")
    check(result.to_receipt("1") is None, "no receipt for a missing body")


def test_zero_byte_digest_is_the_empty_digest() -> None:
    check(parse_json(b"").input_sha256 == sha256_hex(b""), "digest is exact")


# --- JSON fields -------------------------------------------------------

DOC = (
    b'{"subject": "Hi", "body": {"content": "", "type": null},'
    b' "to": ["a", "", null, 3, true], "a/b": "x", "m~n": "y", "n": 1.5}'
)


def test_json_pointers_and_states_in_document_order() -> None:
    result = parse_json(DOC)
    check(result.outcome is Outcome.COMPLETE, "valid JSON is complete")
    got = [(f.pointer, f.state.value, f.value) for f in result.fields]
    want = [
        ("/subject", "text", "Hi"),
        ("/body/content", "empty", ""),
        ("/body/type", "null", None),
        ("/to/0", "text", "a"),
        ("/to/1", "empty", ""),
        ("/to/2", "null", None),
        ("/a~1b", "text", "x"),
        ("/m~0n", "text", "y"),
    ]
    check(got == want, "pointers, states and values are exact")


def test_null_empty_and_missing_are_three_outcomes() -> None:
    result = parse_json(DOC)
    null = result.lookup("/body/type")
    empty = result.lookup("/body/content")
    missing = result.lookup("/body/nope")
    check(null.state is FieldState.NULL and null.value is None, "null")
    check(empty.state is FieldState.EMPTY and empty.value == "", "empty")
    check(missing.state is FieldState.MISSING and missing.value is None, "missing")
    check(len({null.state, empty.state, missing.state}) == 3, "three states")
    check(result.lookup("/subject").value == "Hi", "text value")
    check(result.lookup("/to/3").state is FieldState.OTHER, "number is other")
    check(result.lookup("/to/9").state is FieldState.MISSING, "index past end")
    check(result.lookup("/to/01").state is FieldState.MISSING, "leading zero")
    check(result.lookup("/a~1b").value == "x", "escaped slash")
    check(result.lookup("/m~0n").value == "y", "escaped tilde")
    check(result.lookup("").state is FieldState.OTHER, "root is a container")


def test_json_root_scalars() -> None:
    check(parse_json(b'"x"').lookup("").state is FieldState.TEXT, "root text")
    check(parse_json(b'""').lookup("").state is FieldState.EMPTY, "root empty")
    root_null = parse_json(b" null ")
    check(root_null.outcome is Outcome.COMPLETE, "root null is a value")
    check(root_null.lookup("").state is FieldState.NULL, "root null")
    check(root_null.lookup("/a").state is FieldState.MISSING, "below null")


def test_json_bom_is_skipped() -> None:
    result = parse_json(b'\xef\xbb\xbf{"a": "b"}')
    check(result.bom and result.outcome is Outcome.COMPLETE, "BOM tolerated")
    check(field_map(result) == {"/a": (FieldState.TEXT, "b")}, "field found")


def test_lookup_needs_a_document_and_a_valid_pointer() -> None:
    with pytest.raises(PlainJsonInputError):
        parse_json(b"").lookup("/a")
    with pytest.raises(PlainJsonInputError):
        parse_json(b'{"a": ').lookup("/a")
    with pytest.raises(PlainJsonInputError):
        parse_plain_text(b"x").lookup("/a")
    with pytest.raises(PlainJsonInputError):
        parse_json(b"{}").lookup("a")


def test_json_lone_surrogate_is_flagged_and_replaced() -> None:
    result = parse_json(b'{"a": "x\\ud800y"}')
    check(limits(result) == ("lone_surrogate",), "surrogate flagged")
    check(result.fields[0].value == "x?y", "value is encodable")
    clean = parse_json('{"a": "café"}'.encode())
    check(clean.outcome is Outcome.COMPLETE, "valid non-ASCII is complete")


def test_json_invalid_utf8_is_flagged() -> None:
    result = parse_json(b'{"a": "\xff"}')
    check(limits(result) == ("invalid_utf8",), "invalid UTF-8 flagged")
    check(result.outcome is Outcome.INCOMPLETE, "incomplete")


def test_json_field_bound_gives_limitation(monkeypatch) -> None:
    monkeypatch.setattr(pj, "MAX_JSON_FIELDS", 2)
    result = parse_json(b'["a", "b", "c"]')
    check(len(result.fields) == 2, "fields stop at the bound")
    check(limits(result) == ("field_limit",), "bound is a limitation")
    check(result.outcome is Outcome.INCOMPLETE, "bound is incomplete")


def test_json_size_bound_gives_limitation(monkeypatch) -> None:
    monkeypatch.setattr(pj, "MAX_BODY_BYTES", 4)
    result = parse_json(b'{"a": "b"}')
    check(limits(result) == ("size_limit",), "size bound")
    check(result.outcome is Outcome.INCOMPLETE and not result.fields, "no parse")


# --- partial and invalid JSON -----------------------------------------


@pytest.mark.parametrize(
    "data",
    [
        b'{"value": [{"a": "b"}, {"a"',
        b'{"value": [{"a": "b"}',
        b'{"a": "unterminated',
        b'{"a": ',
        b"[1, 2,",
        b'{"a": "b"',
    ],
)
def test_truncated_json_is_incomplete(data) -> None:
    result = parse_json(data)
    check(result.outcome is Outcome.INCOMPLETE, "truncated is never COMPLETE")
    check(limits(result) == ("truncated_json",), "truncation is explained")
    check(not result.fields and not result.parsed, "no partial document")


def test_every_prefix_of_a_valid_body_is_not_complete() -> None:
    body = b'{"value": [{"s": "x", "n": null}], "k": ""}'
    for cut in range(1, len(body)):
        result = parse_json(body[:cut])
        if result.outcome is Outcome.COMPLETE:
            pytest.fail("a truncated prefix parsed as COMPLETE")
    check(parse_json(body).outcome is Outcome.COMPLETE, "full body is complete")


@pytest.mark.parametrize("data", [b'{"a": 1} x', b"{'a': 1}", b'{"a" 1}', b"nul"])
def test_invalid_json_is_incomplete_with_its_own_limitation(data) -> None:
    result = parse_json(data)
    check(result.outcome is Outcome.INCOMPLETE, "invalid is incomplete")
    check(limits(result) == ("invalid_json",), "invalid is not truncated")


def test_paging_marker_makes_a_valid_page_incomplete() -> None:
    page = b'{"value": [{"s": "x"}], "@odata.nextLink": "https://h.invalid/n"}'
    result = parse_json(page)
    check(result.outcome is Outcome.INCOMPLETE, "page is incomplete")
    check(limits(result) == ("paging_marker",), "marker is explained")
    check(result.lookup("/value/0/s").value == "x", "page data is kept")
    last = parse_json(b'{"value": [], "@odata.nextLink": null}')
    check(last.outcome is Outcome.COMPLETE, "null nextLink is the last page")
    blank = parse_json(b'{"@odata.nextLink": ""}')
    check(blank.outcome is Outcome.COMPLETE, "empty nextLink is no marker")
    token = parse_json(b'{"nextPageToken": "t"}')
    check(limits(token) == ("paging_marker",), "nextPageToken is a marker")
    flag = parse_json(b'{"truncated": true, "value": []}')
    check(limits(flag) == ("paging_marker",), "truncated flag is a marker")
    nested = parse_json(b'{"x": {"@odata.nextLink": "u"}}')
    check(nested.outcome is Outcome.COMPLETE, "only the root counts")


# --- duplicates, numbers, depth ----------------------------------------


def test_duplicate_keys_are_detected_at_any_depth() -> None:
    for data in (b'{"a": 1, "a": 2}', b'{"x": [{"k": "1", "k": "2"}]}'):
        result = parse_json(data)
        check(limits(result) == ("duplicate_key",), "duplicate flagged")
        check(result.outcome is Outcome.INCOMPLETE and not result.fields, "no fields")
    same = parse_json(b'{"a": {"k": 1}, "b": {"k": 2}}')
    check(same.outcome is Outcome.COMPLETE, "same key in two objects is fine")


@pytest.mark.parametrize(
    "data", [b'{"a": NaN}', b"[Infinity]", b"[-Infinity]", b'{"a": 1e999}']
)
def test_non_finite_numbers_are_rejected(data) -> None:
    result = parse_json(data)
    check(limits(result) == ("non_finite_number",), "non-finite flagged")
    check(result.outcome is Outcome.INCOMPLETE and not result.fields, "no fields")


def test_huge_integer_is_bounded_and_does_not_crash() -> None:
    big = b"9" * 5000
    result = parse_json(b'{"id": ' + big + b', "s": "ok"}')
    check(limits(result) == ("huge_integer",), "huge integer flagged")
    check(result.outcome is Outcome.INCOMPLETE, "huge integer is incomplete")
    check(result.lookup("/s").value == "ok", "text is still read")
    check(result.lookup("/id").state is FieldState.OTHER, "number is not text")
    ok = parse_json(b'{"id": ' + b"9" * pj.MAX_INT_DIGITS + b"}")
    check(ok.outcome is Outcome.COMPLETE, "integer at the bound is fine")


def test_deep_nesting_gives_limitation_not_a_crash() -> None:
    depth = 100_000
    result = parse_json(b"[" * depth + b"]" * depth)
    check(limits(result) == ("depth_limit",), "depth flagged")
    check(result.outcome is Outcome.INCOMPLETE and not result.fields, "no fields")
    objects = parse_json(b'{"a":' * 5000 + b"1" + b"}" * 5000)
    check(limits(objects) == ("depth_limit",), "deep objects flagged")


def test_depth_at_the_bound_is_parsed_and_brackets_in_strings_ignored() -> None:
    n = pj.MAX_JSON_DEPTH
    ok = parse_json(b"[" * n + b'"x"' + b"]" * n)
    check(ok.outcome is Outcome.COMPLETE, "depth at the bound is parsed")
    check(ok.fields[0].pointer == "/0" * n, "deep pointer is exact")
    over = parse_json(b"[" * (n + 1) + b"]" * (n + 1))
    check(limits(over) == ("depth_limit",), "one past the bound")
    text = parse_json(b'{"a": "[[[[[[[[[[' + b"[" * 200 + b'\\"[[["}')
    check(text.outcome is Outcome.COMPLETE, "brackets in strings do not count")


# --- determinism, receipt, PII ----------------------------------------


def test_same_bytes_give_equal_results() -> None:
    for parse, data in ((parse_json, DOC), (parse_plain_text, b"a\r\nb\n\nc")):
        first, second = parse(data), parse(bytes(data))
        check(first == second, "results are equal")
        check(first.limitations == second.limitations, "limitations are equal")
        check(first.input_sha256 == sha256_hex(data), "digest is the input digest")
    wide = parse_json(bytearray(DOC))  # type: ignore[arg-type]
    check(wide == parse_json(DOC), "bytearray is accepted")


def test_limitations_are_unique_and_ordered() -> None:
    result = parse_plain_text(b"\xff\x00\n")
    order = [item for item in Limitation if item in result.limitations]
    check(list(result.limitations) == order, "declaration order")
    check(limits(result) == ("invalid_utf8", "nul_bytes"), "two limitations")


def test_receipt_maps_outcome_to_the_existing_contract() -> None:
    done = parse_plain_text(b"hello").to_receipt("v1")
    partial = parse_json(b'{"a": ').to_receipt("v1")
    if done is None or partial is None:
        pytest.fail("receipt expected")
    check(done.outcome == "complete" and done.limit_hit == "none", "complete")
    check(partial.outcome == "partial" and partial.limit_hit == "bytes", "partial")
    check(done.input_bytes == 5 and done.part_count == 1, "receipt counts")
    link = ByteLink(
        component_id="c0",
        component_sha256=sha256_hex(b"hello"),
        component_size=5,
        offset=0,
        length=5,
    )
    part = Part(
        part_id="p0",
        role="body",
        declared_format="plain_text",
        detected_format="plain_text",
        link=link,
    )
    parts = ParsedParts(parts=(part,), receipt=done)
    check(ParsedParts.decode(parts.encode()) == parts, "receipt fits ParsedParts")


@pytest.mark.parametrize("bad", ["text", None, 5, ["x"]])
def test_non_bytes_input_raises_a_fixed_contract_error(bad) -> None:
    for parse in (parse_json, parse_plain_text):
        with pytest.raises(PlainJsonInputError) as info:
            parse(bad)
        check(isinstance(info.value, A2ContractError), "contract error type")
        check(str(info.value) == "body must be bytes", "fixed message")


def test_nothing_echoes_body_text() -> None:
    bodies = [
        f'{{"a": "{SECRET}", "{SECRET}": null}}'.encode(),
        f'{{"{SECRET}": "x", "{SECRET}": "y"}}'.encode(),
        f'{{"a": "{SECRET}'.encode(),
        f"{{'{SECRET}': 1}}".encode(),
        f'{{"{SECRET}": NaN}}'.encode(),
        f"{SECRET}\n\n{SECRET}\x00\xff".encode(),
        b"[" * 500 + SECRET.encode() + b"]" * 500,
    ]
    for body in bodies:
        for parse in (parse_json, parse_plain_text):
            result = parse(body)
            shown = repr(result) + str(result) + repr(result.limitations)
            for item in (*result.fields, *result.lines, *result.blocks):
                shown += repr(item)
            check(SECRET not in shown, "repr must not echo body text")
    ok = parse_json(f'{{"{SECRET}": "{SECRET}"}}'.encode())
    check(SECRET not in repr(ok.lookup(f"/{SECRET}")), "lookup repr is clean")
    check(ok.lookup(f"/{SECRET}").value == SECRET, "value is available")
    for parse in (parse_json, parse_plain_text):
        with pytest.raises(PlainJsonInputError) as info:
            parse(SECRET)  # type: ignore[arg-type]
        check(SECRET not in str(info.value) + repr(info.value), "no echo")
    with pytest.raises(PlainJsonInputError) as info:
        ok.lookup(SECRET)
    check(SECRET not in str(info.value) + repr(info.value), "pointer not echoed")
