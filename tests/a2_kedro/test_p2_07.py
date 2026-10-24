"""P2-07 normalized content: strict offset map, duplicates, marker bound."""

from __future__ import annotations

import unicodedata
from dataclasses import replace

import pytest

from msgloom.a2_kedro.normalize import (
    STRIP_CHARS,
    IrreversibleMarker,
    NormalizedContent,
    NormalizeError,
    Segment,
    Span,
    normalize_text,
    validate_offset_map,
)
from tests.a2_kedro.helpers import check

ZWSP = "\u200b"
RLO = "\u202e"

CORPUS = (
    "",
    "plain ascii",
    "one\r\ntwo\rthree\nfour",
    "cafe\u0301 and caf\u00e9",
    "\u0958 \u1100\u1161\u11a8 x",
    "a" + ZWSP + "b" + RLO + "c" + ZWSP * 3,
    "wide    gap\t\t\tand\n\n\n\n\nblank",
    "e" + ZWSP + "\u0301 joined",
    "a \u200b \u200b b",
    "\n\n\n",
    ZWSP,
    "tail\r",
    "Same line\r\n" * 3,
)


def seg_tuples(content: NormalizedContent) -> list[tuple[int, int, int, int, str]]:
    return [
        (
            s.normalized.start,
            s.normalized.end,
            s.original_start,
            s.original_end,
            s.mode,
        )
        for s in content.segments
    ]


def expect_error(content: NormalizedContent, raw: str) -> None:
    with pytest.raises(NormalizeError):
        validate_offset_map(content, raw)


# --- transforms ---------------------------------------------------------


def test_empty_string_gives_empty_map() -> None:
    content = normalize_text("")
    check(content.text == "" and content.segments == (), "empty text and map")
    check(content.irreversible_count == 0, "no markers")
    validate_offset_map(content, "")


def test_plain_ascii_is_one_identity_segment() -> None:
    content = normalize_text("plain ascii")
    check(seg_tuples(content) == [(0, 11, 0, 11, "identity")], "one segment")
    validate_offset_map(content, "plain ascii")


def test_line_ends_fold_to_lf_and_stay_reversible() -> None:
    raw = "one\r\ntwo\rthree\nfour"
    content = normalize_text(raw)
    check(content.text == "one\ntwo\nthree\nfour", "line ends folded")
    check(content.markers == (), "line end fold is reversible")
    check((3, 4, 3, 5, "transformed") in seg_tuples(content), "CRLF maps 2 to 1")
    check((7, 8, 8, 9, "transformed") in seg_tuples(content), "CR maps 1 to 1")
    validate_offset_map(content, raw)


def test_nfc_can_shrink_and_grow_the_text() -> None:
    shrink = "e\u0301"
    content = normalize_text(shrink)
    check(content.text == "\u00e9", "composed")
    check(seg_tuples(content) == [(0, 1, 0, 2, "transformed")], "2 to 1")
    grow = "\u0958"
    content = normalize_text(grow)
    check(content.text == unicodedata.normalize("NFC", grow), "decomposed")
    check(seg_tuples(content) == [(0, 2, 0, 1, "transformed")], "1 to 2")
    hangul = "\u1100\u1161\u11a8"
    content = normalize_text(hangul)
    check(content.text == "\uac01", "jamo composed")
    check(seg_tuples(content) == [(0, 1, 0, 3, "transformed")], "3 to 1")
    for raw in (shrink, grow, hangul):
        validate_offset_map(normalize_text(raw), raw)


def test_nfc_text_matches_the_standard_library() -> None:
    for raw in CORPUS:
        expected = unicodedata.normalize("NFC", raw)
        for char in STRIP_CHARS:
            expected = expected.replace(char, "")
        folded = expected.replace("\r\n", "\n").replace("\r", "\n")
        content = normalize_text(raw)
        check(unicodedata.is_normalized("NFC", content.text), "text is NFC")
        plain = " " not in raw and "\t" not in raw and "\n\n\n" not in raw
        if plain and (ZWSP not in raw or "\u0301" not in raw):
            check(content.text == folded, "matches stdlib pipeline")


def test_zero_width_and_bidi_are_irreversible_markers() -> None:
    raw = "a" + ZWSP + "b" + RLO + "c" + ZWSP * 3
    content = normalize_text(raw)
    check(content.text == "abc", "controls removed")
    got = [(m.kind, m.original_start, m.original_end, m.count) for m in content.markers]
    check(
        got == [("strip", 1, 2, 1), ("strip", 3, 4, 1), ("strip", 5, 8, 3)],
        "one marker per contiguous run with a count",
    )
    check(len(content.segments) == 3, "each kept run is its own segment")
    check(content.segments[1].original_start == 2, "gap is not in a segment")
    validate_offset_map(content, raw)


def test_bidi_override_is_stripped_not_kept() -> None:
    raw = "safe" + RLO + "txt.exe"
    content = normalize_text(raw)
    check(content.text == "safetxt.exe", "override removed")
    check(content.irreversible_count == 1, "one marker")
    validate_offset_map(content, raw)


def test_collapse_runs_are_marked_and_absorb_inner_strips() -> None:
    raw = "a" + " " * 4 + "b\n\n\n\n\nc"
    content = normalize_text(raw)
    check(content.text == "a b\n\nc", "runs collapsed")
    kinds = [(m.kind, m.count) for m in content.markers]
    check(kinds == [("collapse_space", 3), ("collapse_blank_lines", 3)], "markers")
    absorbed = "a \u200b \u200b b"
    content = normalize_text(absorbed)
    check(content.text == "a b", "space run collapsed through strips")
    check(content.irreversible_count == 1, "inner strips are absorbed")
    validate_offset_map(content, absorbed)


def test_strip_inside_a_nfc_cluster_is_marked_and_composes() -> None:
    raw = "e" + ZWSP + "\u0301!"
    content = normalize_text(raw)
    check(content.text == "\u00e9!", "stripped mark composes")
    check(content.irreversible_count == 1, "strip is counted")
    check(not content.is_reversible(0), "marked cluster is not reversible")
    check(content.is_reversible(1), "plain tail is reversible")
    check(seg_tuples(content)[0] == (0, 1, 0, 3, "transformed"), "cluster range")
    validate_offset_map(content, raw)


# --- bounds and hostile input -------------------------------------------


def test_lone_surrogate_fails_closed() -> None:
    for raw in ("\ud800", "ok\udc00ok", "a\ud83d"):
        with pytest.raises(NormalizeError):
            normalize_text(raw)


def test_input_just_over_the_bound_fails_and_at_the_bound_passes() -> None:
    normalize_text("x" * 100, max_chars=100)
    with pytest.raises(NormalizeError):
        normalize_text("x" * 101, max_chars=100)


def test_many_tiny_segments_fail_closed() -> None:
    raw = "a\r\n" * 10_000
    with pytest.raises(NormalizeError):
        normalize_text(raw)
    content = normalize_text(raw, max_segments=20_000)
    check(len(content.segments) == 20_000, "alternating segments")
    validate_offset_map(content, raw)


def test_segment_bound_is_exact() -> None:
    raw = "a\r\n" * 3  # identity, transformed, identity, ... = 6 segments
    normalize_text(raw, max_segments=6)
    with pytest.raises(NormalizeError):
        normalize_text(raw, max_segments=5)


def test_marker_bound_is_exact_and_never_truncates() -> None:
    raw = ("a" + ZWSP) * 5
    content = normalize_text(raw, max_irreversible_markers=5)
    check(content.irreversible_count == 5, "five markers at the cap")
    with pytest.raises(NormalizeError):
        normalize_text(raw, max_irreversible_markers=4)


def test_bad_arguments_fail() -> None:
    with pytest.raises(NormalizeError):
        normalize_text(b"bytes")  # type: ignore[arg-type]
    for name in ("max_chars", "max_segments", "max_irreversible_markers"):
        for bad in (0, -1, True, 1.5, None):
            with pytest.raises(NormalizeError):
                normalize_text("x", **{name: bad})  # type: ignore[arg-type]


def test_repr_and_errors_hide_content() -> None:
    secret = "alice.private@example.invalid"
    content = normalize_text(secret)
    check(secret not in repr(content), "repr has no text")
    try:
        normalize_text(secret + "\ud800")
    except NormalizeError as error:
        check(secret not in str(error), "error has no text")
    else:
        pytest.fail("lone surrogate must raise")


def test_same_input_gives_equal_result() -> None:
    for raw in CORPUS:
        check(normalize_text(raw) == normalize_text(raw), "deterministic")


# --- duplicates ---------------------------------------------------------


def test_repeated_paragraph_keeps_distinct_source_offsets() -> None:
    para = "Same line\r\n"
    raw = para * 3
    content = normalize_text(raw)
    check(content.text == "Same line\n" * 3, "text repeats")
    identity = [s for s in content.segments if s.mode == "identity"]
    check(len(identity) == 3, "three identity segments")
    starts = [s.original_start for s in identity]
    check(starts == [0, len(para), 2 * len(para)], "own source offsets")
    check(len({s.normalized.start for s in identity}) == 3, "own normalized spans")
    for index, seg in enumerate(identity):
        piece = raw[seg.original_start : seg.original_end]
        check(piece == "Same line", "slice matches")
        check(seg.normalized.start == index * 10, "normalized offset")
    validate_offset_map(content, raw)


def test_repeated_blocks_swapped_offsets_are_rejected() -> None:
    raw = "dup\r\n" * 3
    content = normalize_text(raw)
    first, second = content.segments[0], content.segments[2]
    swapped = list(content.segments)
    swapped[0] = replace(
        first, original_start=second.original_start, original_end=second.original_end
    )
    swapped[2] = replace(
        second, original_start=first.original_start, original_end=first.original_end
    )
    expect_error(replace(content, segments=tuple(swapped)), raw)


# --- tampered maps ------------------------------------------------------


def tamper_cases(
    content: NormalizedContent,
) -> dict[str, NormalizedContent]:
    segs = list(content.segments)

    def with_seg(index: int, **changes: object) -> NormalizedContent:
        out = list(segs)
        out[index] = replace(out[index], **changes)  # type: ignore[arg-type]
        return replace(content, segments=tuple(out))

    def with_span(index: int, start: int, end: int) -> NormalizedContent:
        return with_seg(index, normalized=Span(start, end))

    s1, s2 = segs[1].normalized, segs[2].normalized
    return {
        "normalized overlap": with_span(2, s2.start - 1, s2.end),
        "normalized gap": with_span(2, s2.start + 1, s2.end),
        "normalized reversed": with_span(1, s1.end, s1.start),
        "normalized empty": with_span(1, s1.start, s1.start),
        "normalized past text": with_span(
            len(segs) - 1, segs[-1].normalized.start, 10**6
        ),
        "source out of range": with_seg(1, original_end=10**6),
        "source reversed": with_seg(
            1, original_start=segs[1].original_end, original_end=segs[1].original_start
        ),
        "source negative": with_seg(0, original_start=-1),
        "source non monotonic": with_seg(
            2, original_start=0, original_end=segs[2].original_end
        ),
        "source overlap": with_seg(2, original_start=segs[1].original_end - 1),
        "mode lies identity": with_seg(1, mode="identity"),
        "mode lies transformed": with_seg(0, mode="transformed"),
        "mode unknown": with_seg(0, mode="other"),
        "float offset": with_seg(0, original_start=0.0),
        "entry type": replace(content, segments=(*segs[:1], "x", *segs[2:])),  # type: ignore[arg-type]
        "dropped last": replace(content, segments=tuple(segs[:-1])),
        "dropped first": replace(content, segments=tuple(segs[1:])),
        "dropped all": replace(content, segments=()),
        "wrong length": replace(content, source_length=content.source_length + 1),
        "text changed": replace(content, text=content.text + "x"),
        "text swapped": replace(content, text=content.text[::-1]),
    }


def test_every_tampered_map_is_rejected() -> None:
    raw = "ab\r\ncd\r\nef\r\ngh"
    content = normalize_text(raw)
    validate_offset_map(content, raw)
    check(len(content.segments) >= 4, "fixture has enough segments")
    for name, bad in tamper_cases(content).items():
        try:
            validate_offset_map(bad, raw)
        except NormalizeError:
            continue
        pytest.fail(f"tampered map accepted: {name}")


def test_tampered_markers_are_rejected() -> None:
    raw = "a" + ZWSP + "b" + ZWSP
    content = normalize_text(raw)
    first = content.markers[0]
    for markers in (
        (),
        content.markers[:1],
        content.markers + content.markers[:1],
        (replace(first, original_end=first.original_end + 1), content.markers[1]),
        (replace(first, kind="bogus"), content.markers[1]),  # type: ignore[arg-type]
        (replace(first, count=9), content.markers[1]),
        ("x", content.markers[1]),  # type: ignore[arg-type]
    ):
        expect_error(replace(content, markers=markers), raw)


def test_source_gap_with_real_text_is_rejected() -> None:
    raw = "abcdef"
    content = normalize_text(raw)
    seg = content.segments[0]
    expect_error(
        replace(
            content,
            text="abef",
            segments=(
                Segment(Span(0, 2), 0, 2, "identity"),
                Segment(Span(2, 4), 4, 6, "identity"),
            ),
        ),
        raw,
    )
    check(seg.original_end == 6, "fixture sanity")


def test_validator_rejects_wrong_argument_types() -> None:
    content = normalize_text("x")
    expect_error("x", "x")  # type: ignore[arg-type]
    expect_error(content, b"x")  # type: ignore[arg-type]
    expect_error(replace(content, segments=[]), "x")  # type: ignore[arg-type]
    expect_error(replace(content, markers=[]), "x")  # type: ignore[arg-type]


# --- round trip ---------------------------------------------------------


def test_every_corpus_map_validates_and_covers_the_text() -> None:
    for raw in CORPUS:
        content = normalize_text(raw)
        validate_offset_map(content, raw)
        cursor = last = 0
        for seg in content.segments:
            check(seg.normalized.start == cursor, "no gap on the normalized side")
            check(seg.normalized.end > seg.normalized.start, "non-empty")
            check(seg.original_start >= last, "source ascends")
            check(seg.original_end <= len(raw), "source in bounds")
            cursor, last = seg.normalized.end, seg.original_end
        check(cursor == len(content.text), "covers the whole text")


def test_reversible_entries_round_trip_through_a_second_run() -> None:
    reversible = 0
    for raw in CORPUS:
        content = normalize_text(raw)
        for index, seg in enumerate(content.segments):
            if not content.is_reversible(index):
                continue
            reversible += 1
            piece = raw[seg.original_start : seg.original_end]
            again = normalize_text(piece)
            target = content.text[seg.normalized.start : seg.normalized.end]
            check(again.text == target, "source slice normalizes to the slice")
            check(again.markers == (), "reversible slice has no marker")
    check(reversible > 10, "corpus exercises reversible entries")


def test_normalizing_normalized_text_is_a_fixed_point() -> None:
    for raw in CORPUS:
        once = normalize_text(raw)
        twice = normalize_text(once.text)
        check(twice.text == once.text, "idempotent text")
        check(twice.markers == (), "second run loses nothing")


def test_marker_type_is_frozen() -> None:
    marker = IrreversibleMarker("strip", 0, 1, 1)
    with pytest.raises(AttributeError):
        marker.count = 2  # type: ignore[misc]
