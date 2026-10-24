"""C0-05 NormalizedContent and ContentZones: exact original-span mapping."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from msgloom.a2_kedro.contracts import zones
from msgloom.a2_kedro.contracts.codec import A2ContractError, sha256_hex
from msgloom.a2_kedro.contracts.zones import (
    ContentZones,
    NormalizedContent,
    QuoteOccurrence,
)
from tests.a2_kedro.helpers import check, hexd

SENTINEL = "alice.private@example.invalid"

#: (mode, parsed piece, normalized piece). The parsed text keeps a two byte
#: character and a collapsed run of blanks.
PIECES = (
    ("identity", "Hi", "Hi"),
    ("transformed", "  ", " "),
    ("identity", "thé.\n", "thé.\n"),
    ("identity", "> old\n", "> old\n"),
    ("transformed", "-- \n", "--\n"),
    ("identity", "sig", "sig"),
)


def texts(pieces: Any = PIECES) -> tuple[bytes, bytes, list[dict[str, Any]]]:
    parsed = normalized = b""
    segments: list[dict[str, Any]] = []
    for mode, old, new in pieces:
        old_b, new_b = old.encode(), new.encode()
        segments.append(
            {
                "normalized": {
                    "start": len(normalized),
                    "end": len(normalized) + len(new_b),
                },
                "original_start": len(parsed),
                "original_end": len(parsed) + len(old_b),
                "mode": mode,
            }
        )
        parsed, normalized = parsed + old_b, normalized + new_b
    return parsed, normalized, segments


def binding(parsed: bytes, normalized: bytes) -> dict[str, Any]:
    return {
        "part_id": "p0",
        "parsed_sha256": sha256_hex(parsed),
        "parsed_length": len(parsed),
        "normalized_sha256": sha256_hex(normalized),
        "normalized_length": len(normalized),
    }


def content(**kw: Any) -> NormalizedContent:
    parsed, normalized, segments = texts()
    data = {**binding(parsed, normalized), "segments": tuple(segments), **kw}
    return NormalizedContent.model_validate(data)


def span(start: int, end: int) -> dict[str, int]:
    return {"start": start, "end": end}


def zone(zid: str, kind: str, orig: tuple[int, int], norm: tuple[int, int], **kw):
    return {
        "zone_id": zid,
        "kind": kind,
        "original": span(*orig),
        "normalized": span(*norm),
        **kw,
    }


def good_zones() -> list[dict[str, Any]]:
    # normalized offsets: "Hi" 0-2, " " 2-3, "thé.\n" 3-9, "> old\n" 9-15,
    # "--\n" 15-18, "sig" 18-21. Parsed: 0-2, 2-4, 4-10, 10-16, 16-20, 20-23.
    return [
        zone("z0", "authored", (0, 10), (0, 9)),
        zone(
            "z1",
            "quote",
            (10, 16),
            (9, 15),
            quote_occurrence={"ordinal": 0, "depth": 1},
            quote_author_sha256=hexd("b"),
        ),
        zone("z2", "signature", (16, 23), (15, 21)),
    ]


def make_zones(items: Any = None, **kw: Any) -> ContentZones:
    parsed, normalized, _ = texts()
    data = {
        **binding(parsed, normalized),
        "zones": tuple(items if items is not None else good_zones()),
        **kw,
    }
    return ContentZones.model_validate(data)


def test_round_trip_and_bytes_prove_the_mapping() -> None:
    parsed, normalized, _ = texts()
    norm, marks = content(), make_zones()
    check(NormalizedContent.decode(norm.encode()) == norm, "content round trip")
    check(ContentZones.decode(marks.encode()) == marks, "zones round trip")
    check(norm.header.kind == zones.NORMALIZED_KIND, "content kind")
    check(marks.header.kind == zones.ZONES_KIND, "zones kind")
    norm.verify_bytes(parsed, normalized)
    marks.verify_bytes(parsed, normalized)
    marks.validate_against(norm)
    check(norm.project(3, 9) == (4, 10), "identity run maps exactly")
    check(norm.project(4, 6) == (5, 7), "offset inside identity maps exactly")
    check(norm.project(2, 3) == (2, 4), "whole transformed segment maps")


def test_wire_field_names_are_pinned() -> None:
    parsed = normalized = b"ab"
    seg = {
        "normalized": span(0, 2),
        "original_start": 0,
        "original_end": 2,
        "mode": "identity",
    }
    norm = NormalizedContent.model_validate(
        {**binding(parsed, normalized), "segments": (seg,)}
    )
    marks = ContentZones.model_validate(
        {
            **binding(parsed, normalized),
            "zones": (zone("z", "authored", (0, 2), (0, 2)),),
        }
    )
    sha = sha256_hex(b"ab")
    texts_part = (
        '"normalized_length":2,"normalized_sha256":"' + sha + '",'
        '"parsed_length":2,"parsed_sha256":"' + sha + '","part_id":"p0"'
    )
    head = '{"header":{"kind":"%s","profile":"a2-c0-provisional-1","version":"1"},'
    expected_content = (
        head % "normalized_content"
        + texts_part
        + ',"segments":[{"mode":"identity","normalized":{"end":2,"start":0},'
        '"original_end":2,"original_start":0}]}'
    )
    expected_zones = (
        head % "zones"
        + texts_part
        + ',"zones":[{"kind":"authored","normalized":{"end":2,"start":0},'
        '"original":{"end":2,"start":0},"quote_author_sha256":null,'
        '"quote_occurrence":null,"zone_id":"z"}]}'
    )
    check(norm.encode().decode() == expected_content, "content wire form changed")
    check(marks.encode().decode() == expected_zones, "zones wire form changed")


def test_segment_map_negative_cases() -> None:
    _, _, segs = texts()
    bad: list[tuple[Any, str]] = [
        (segs[:1] + segs[2:], "gap or overlap"),
        (segs[:-1], "do not cover"),
        (
            segs[:1] + [{**segs[1], "original_start": 1}] + segs[2:],
            "overlap or go back",
        ),
        ([{**segs[0], "original_end": 5}] + segs[1:], "changes the length"),
        ([{**segs[0], "original_start": 3, "original_end": 2}] + segs[1:], "reversed"),
        ([{**segs[0], "normalized": span(2, 0)}] + segs[1:], "empty or reversed"),
        ([{**segs[0], "mode": "copy"}] + segs[1:], ""),
        ([{**segs[0], "extra": 1}] + segs[1:], ""),
        ((), "disagree"),
    ]
    for segments, message in bad:
        with pytest.raises(ValueError, match=message or None):
            content(segments=tuple(segments))
    with pytest.raises(ValueError, match="outside the parsed text"):
        content(parsed_length=10)
    with pytest.raises(ValueError, match="disagree"):
        content(normalized_length=0)


def test_dropped_parsed_bytes_are_a_gap_in_original_ranges() -> None:
    pieces = (
        ("identity", "ab", "ab"),
        ("transformed", "", "|"),
        ("identity", "cd", "cd"),
    )
    parsed, normalized, segs = texts(pieces)
    parsed2 = parsed[:2] + b"XX" + parsed[2:]
    segs[2]["original_start"] += 2
    segs[2]["original_end"] += 2
    norm = NormalizedContent.model_validate(
        {**binding(parsed2, normalized), "segments": tuple(segs)}
    )
    norm.verify_bytes(parsed2, normalized)
    check(norm.project(0, 5) == (0, 6), "range spans the dropped bytes")


def test_zone_shape_negative_cases() -> None:
    z = good_zones()
    overlap = [z[0], {**z[1], "original": span(9, 16)}, z[2]]
    reorder = [z[1], z[0], z[2]]
    outside = [z[0], z[1], {**z[2], "normalized": span(15, 22)}]
    bad: list[tuple[Any, str]] = [
        (overlap, "overlap or are not sorted"),
        (reorder, "overlap or are not sorted"),
        (outside, "outside the text"),
        ([z[0], {**z[1], "zone_id": "z0"}, z[2]], "duplicate zone id"),
        ([z[0], {**z[1], "quote_occurrence": None}, z[2]], "needs an occurrence"),
        ([{**z[0], "quote_author_sha256": hexd("b")}, z[1], z[2]], "only a quote"),
        (
            [{**z[0], "quote_occurrence": {"ordinal": 0, "depth": 1}}, z[1], z[2]],
            "only a quote",
        ),
        (
            [z[0], {**z[1], "quote_occurrence": {"ordinal": 1, "depth": 1}}, z[2]],
            "not in order",
        ),
        ([z[0], {**z[1], "quote_occurrence": {"ordinal": 0, "depth": 0}}, z[2]], ""),
        ([{**z[0], "kind": "headline"}], ""),
        ([{**z[0], "original": span(3, 3)}], "empty or reversed"),
        ([{**z[0], "original": span(-1, 3)}], ""),
        ([], "out of bounds"),
    ]
    for items, message in bad:
        with pytest.raises(ValueError, match=message or None):
            make_zones(items)


def test_quote_occurrence_and_author_stay_separate_fields() -> None:
    quote = make_zones().zones[1]
    check(quote.quote_occurrence is not None, "occurrence kept")
    check(quote.quote_author_sha256 == hexd("b"), "author kept")
    anonymous = [good_zones()[0]] + [
        {**good_zones()[1], "quote_author_sha256": None},
        good_zones()[2],
    ]
    check(make_zones(anonymous).zones[1].quote_author_sha256 is None, "no author")
    check(
        make_zones(anonymous).encode() != make_zones().encode(),
        "author digest is part of the bytes",
    )
    check(
        "quote_author" not in QuoteOccurrence.model_fields,
        "occurrence holds no author",
    )


def test_projection_mismatch_is_rejected() -> None:
    norm = content()
    z = good_zones()
    wrong = [{**z[0], "original": span(0, 9)}, z[1], z[2]]
    with pytest.raises(A2ContractError, match="differs from projection"):
        make_zones(wrong).validate_against(norm)
    inside_end = [zone("z", "authored", (10, 17), (9, 16))]
    with pytest.raises(A2ContractError, match="ends inside a transformed"):
        make_zones(inside_end).validate_against(norm)
    inside_start = [zone("z", "authored", (16, 23), (16, 21))]
    with pytest.raises(A2ContractError, match="starts inside a transformed"):
        make_zones(inside_start).validate_against(norm)
    long_seg = (("transformed", "abcd", "xy"),)
    parsed, normalized, segs = texts(long_seg)
    one = NormalizedContent.model_validate(
        {**binding(parsed, normalized), "segments": tuple(segs)}
    )
    with pytest.raises(A2ContractError, match="starts inside a transformed"):
        one.project(1, 2)
    with pytest.raises(A2ContractError, match="outside the text"):
        norm.project(0, 99)
    with pytest.raises(A2ContractError, match="outside the text"):
        norm.project(5, 5)


def test_zones_must_bind_the_same_texts() -> None:
    norm = content()
    for change in (
        {"part_id": "other"},
        {"parsed_sha256": hexd("1")},
        {"parsed_length": 24},
        {"normalized_sha256": hexd("2")},
        {"normalized_length": 22},
    ):
        with pytest.raises(A2ContractError, match="same texts"):
            make_zones(**change).validate_against(norm)


def test_bytes_that_do_not_match_are_rejected() -> None:
    parsed, normalized, _ = texts()
    norm, marks = content(), make_zones()
    for obj in (norm, marks):
        with pytest.raises(A2ContractError, match="saved digest"):
            obj.verify_bytes(parsed + b"x", normalized)
        with pytest.raises(A2ContractError, match="saved digest"):
            obj.verify_bytes(parsed, normalized.replace(b"Hi", b"Ho"))


def test_identity_segment_must_equal_the_original_bytes() -> None:
    parsed, normalized = b"abcd", b"abXd"
    seg = {
        "normalized": span(0, 4),
        "original_start": 0,
        "original_end": 4,
        "mode": "identity",
    }
    norm = NormalizedContent.model_validate(
        {**binding(parsed, normalized), "segments": (seg,)}
    )
    with pytest.raises(A2ContractError, match="does not match the bytes"):
        norm.verify_bytes(parsed, normalized)
    as_rewrite = {**seg, "mode": "transformed"}
    NormalizedContent.model_validate(
        {**binding(parsed, normalized), "segments": (as_rewrite,)}
    ).verify_bytes(parsed, normalized)


def test_spans_must_sit_on_character_boundaries_and_be_utf8() -> None:
    parsed = normalized = "éé".encode()
    halves = tuple(
        {
            "normalized": span(i, i + 1),
            "original_start": i,
            "original_end": i + 1,
            "mode": "identity",
        }
        for i in range(4)
    )
    split = NormalizedContent.model_validate(
        {**binding(parsed, normalized), "segments": halves}
    )
    with pytest.raises(A2ContractError, match="not UTF-8"):
        split.verify_bytes(parsed, normalized)
    split_zone = ContentZones.model_validate(
        {
            **binding(parsed, normalized),
            "zones": (zone("z", "authored", (0, 1), (0, 1)),),
        }
    )
    with pytest.raises(A2ContractError, match="not UTF-8"):
        split_zone.verify_bytes(parsed, normalized)
    bad = b"\xff\xfe"
    broken = ContentZones.model_validate(
        {**binding(bad, bad), "zones": (zone("z", "authored", (0, 2), (0, 2)),)}
    )
    with pytest.raises(A2ContractError, match="not UTF-8"):
        broken.verify_bytes(bad, bad)


def test_models_are_closed_frozen_and_header_checked() -> None:
    with pytest.raises(ValueError):
        make_zones(extra_field=1)
    with pytest.raises(ValueError, match="approved|not zones"):
        make_zones(header={"kind": "parsed_parts", "version": "1"})
    with pytest.raises(ValueError, match="not zones"):
        make_zones(header={"kind": "normalized_content", "version": "1"})
    with pytest.raises(ValueError, match="not normalized_content"):
        content(header={"kind": "zones", "version": "1"})
    with pytest.raises(ValidationError):
        make_zones().part_id = "x"  # type: ignore[misc]
    with pytest.raises(ValueError):
        make_zones(parsed_sha256="A" * 64)


@pytest.mark.parametrize("char", ["\x00", "\n", "\t", "\x7f", "\x85", " "])
def test_control_characters_are_rejected(char: str) -> None:
    with pytest.raises(ValueError):
        make_zones(part_id="p" + char)
    with pytest.raises(ValueError):
        make_zones([{**good_zones()[0], "zone_id": "z" + char}])
    with pytest.raises(ValueError):
        content(part_id="p" + char)


def test_error_text_carries_no_input_values() -> None:
    z = good_zones()
    cases: list[Any] = [
        lambda: make_zones(
            [{**z[0], "zone_id": SENTINEL}, {**z[1], "zone_id": SENTINEL}, z[2]]
        ),
        lambda: make_zones([{**z[0], "zone_id": SENTINEL, "kind": SENTINEL}]),
        lambda: make_zones([{**z[0], "zone_id": SENTINEL + "\n"}]),
        lambda: make_zones(part_id=SENTINEL, parsed_sha256=SENTINEL),
        lambda: make_zones(
            [{**z[0], "zone_id": SENTINEL}, {**z[1], "quote_occurrence": None}, z[2]]
        ),
        lambda: content(part_id=SENTINEL, segments=()),
    ]
    for build in cases:
        with pytest.raises(ValueError) as caught:
            build()
        check(SENTINEL not in str(caught.value), "input value in error text")
    marks = make_zones(part_id=SENTINEL)
    with pytest.raises(A2ContractError) as mismatch:
        marks.validate_against(content())
    check(SENTINEL not in str(mismatch.value), "id in binding error text")


def test_decode_rejects_non_canonical_bytes() -> None:
    data = make_zones().encode()
    with pytest.raises(A2ContractError):
        ContentZones.decode(data.replace(b'"zones"', b' "zones"'))
    with pytest.raises(A2ContractError):
        ContentZones.decode(data.replace(b'"part_id"', b'"part"'))
    with pytest.raises(A2ContractError):
        NormalizedContent.decode(data)
