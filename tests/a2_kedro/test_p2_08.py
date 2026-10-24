"""P2-08 content zones: kinds, attribution, tiling, offset map, mutations."""

from __future__ import annotations

import pytest

from msgloom.a2_kedro import zones as zmod
from msgloom.a2_kedro.contracts.codec import A2ContractError, sha256_hex
from msgloom.a2_kedro.contracts.zones import ContentZones, Zone
from msgloom.a2_kedro.normalize import NormalizedContent, normalize_text
from msgloom.a2_kedro.zones import ZoneResult, build_zones
from tests.a2_kedro.helpers import check

AUTHOR = "alice@example.com"


def go(
    raw: str, author: str = AUTHOR, **kw: int
) -> tuple[NormalizedContent, ZoneResult]:
    source = normalize_text(raw)
    return source, build_zones(raw, source, part_id="part-1", author=author, **kw)


def view(source: NormalizedContent, res: ZoneResult) -> list[tuple[str, int, str]]:
    data = source.text.encode("utf-8")
    zones = zs(res) if res.zones else ()
    return [
        (
            z.kind,
            z.quote_occurrence.depth if z.quote_occurrence else 0,
            data[z.normalized.start : z.normalized.end].decode("utf-8"),
        )
        for z in zones
    ]


def zs(res: ZoneResult) -> tuple[Zone, ...]:
    """Return the zones of ``res`` or fail the test when there are none."""
    if res.zones is None:
        pytest.fail("zones expected")
    return res.zones.zones


def kinds(raw: str) -> list[str]:
    return [item[0] for item in view(*go(raw))]


def digest(claim: str) -> str:
    return sha256_hex(claim.encode("utf-8"))


def check_tiling(raw: str, source: NormalizedContent, res: ZoneResult) -> None:
    """Zones plus unknown ranges cover the text with no gap or overlap."""
    data = source.text.encode("utf-8")
    zones = zs(res) if res.zones else ()
    spans = [(z.normalized.start, z.normalized.end) for z in zones]
    spans += [(u.start, u.end) for u in res.unknown]
    cursor = 0
    for start, end in sorted(spans):
        check(start == cursor, "gap or overlap in the zone tiling")
        cursor = end
    check(cursor == len(data), "the tiling does not cover the text")
    if res.zones:
        res.zones.validate_against(res.content)
        res.zones.verify_bytes(raw.encode("utf-8"), data)


def check_quotes_not_authored(source: NormalizedContent, res: ZoneResult) -> None:
    """A line that starts with ``>`` is in a quote zone or unknown."""
    data = source.text.encode("utf-8")
    zones = zs(res) if res.zones else ()
    offset = 0
    for line in data.splitlines(keepends=True):
        if line.startswith(b">"):
            hit = [z for z in zones if z.normalized.start <= offset < z.normalized.end]
            check(
                all(z.kind == "quote" for z in hit),
                "a quoted line is inside a non-quote zone",
            )
        offset += len(line)


def test_plain_text_is_one_authored_zone() -> None:
    raw = "Hello Bob.\nSee you at noon.\n"
    source, res = go(raw)
    check(view(source, res) == [("authored", 0, raw)], "plain text must be authored")
    check(res.unknown == () and res.limitations == (), "nothing unknown expected")
    check_tiling(raw, source, res)


def test_gt_inside_a_line_is_not_a_quote() -> None:
    raw = "a > b is true\n  > indented\nx>y\n"
    check(kinds(raw) == ["authored"], "only a line prefix quotes")


# --- quotes -----------------------------------------------------------


def test_reply_with_wrote_marker() -> None:
    claim = "Mon, Oct 5, 2026 at 9:00 AM Bob Example <bob@example.org>"
    raw = f"Thanks, noted.\n\nOn {claim} wrote:\n> Can we meet?\n> Noon works.\n"
    source, res = go(raw)
    got = view(source, res)
    check([g[:2] for g in got] == [("authored", 0), ("quote", 1)], "kinds differ")
    check(got[0][2] == "Thanks, noted.\n\n", "authored text differs")
    check(got[1][2].startswith("On Mon") and "Noon works." in got[1][2], "quote text")
    quote = zs(res)[1]
    check(quote.quote_author_sha256 == digest(claim.casefold()), "claim digest")
    check_tiling(raw, source, res)


def test_gt_prefix_without_marker_has_no_claim() -> None:
    raw = "Fine.\n> quoted a\n> quoted b\nAfter.\n"
    source, res = go(raw)
    check(
        view(source, res)
        == [
            ("authored", 0, "Fine.\n"),
            ("quote", 1, "> quoted a\n> quoted b\n"),
            ("authored", 0, "After.\n"),
        ],
        "gt quote zones differ",
    )
    check(zs(res)[1].quote_author_sha256 is None, "no claim expected")


def test_body_that_is_only_quoted_text() -> None:
    raw = "> a\n> b\n"
    source, res = go(raw)
    check(view(source, res) == [("quote", 1, raw)], "only a quote zone expected")
    check("authored" not in kinds("On Tue, Bob wrote:\n> a\n"), "no authored zone")


BLOCK = "> > level two\n> > > level three\n"
FIRST = f"Hi.\nOn Tue, Bob wrote:\n> level one\n> On Mon, Carol wrote:\n{BLOCK}"


def test_nested_depth_three_repeated_twice() -> None:
    raw = FIRST + f">\n> level one again\n{BLOCK}"
    source, res = go(raw)
    got = view(source, res)
    check(
        [g[:2] for g in got]
        == [("authored", 0), ("quote", 1), ("quote", 2), ("quote", 3)]
        + [("quote", 1), ("quote", 2), ("quote", 3)],
        "nested zone kinds and depths differ",
    )
    check(got[2][2] == got[5][2] and got[3][2] == got[6][2], "repeat text differs")
    zones = zs(res)
    check(zones[2].original.start != zones[5].original.start, "repeat shares an offset")
    check(
        [z.quote_occurrence.ordinal for z in zones[1:] if z.quote_occurrence]
        == list(range(6)),
        "ordinals",
    )
    check(zones[1].quote_author_sha256 == digest("tue, bob"), "outer claim")
    check(zones[2].quote_author_sha256 == digest("mon, carol"), "nested claim")
    check(zones[5].quote_author_sha256 is None, "a repeat must not copy a claim")
    check_tiling(raw, source, res)
    check_quotes_not_authored(source, res)


def test_repeated_block_zones_are_independent() -> None:
    once_src, once = go(FIRST)
    twice_raw = FIRST + f"> level one again\n{BLOCK}"
    twice_src, twice = go(twice_raw)
    head = view(once_src, once)
    check(view(twice_src, twice)[: len(head) - 1] == head[:-1], "first copy changed")
    check(zs(twice)[: len(head) - 1] == zs(once)[:-1], "first spans")
    check(len(zs(twice)) > len(zs(once)), "second copy is missing")
    # Editing the second copy must not move or relabel the first copy.
    other_raw = FIRST + "> level one again\n> > changed\n"
    other_src, other = go(other_raw)
    check(zs(other)[:3] == zs(once)[:3], "first copy not independent")
    check_tiling(other_raw, other_src, other)


def test_depth_over_sixteen_is_unknown_with_limitation() -> None:
    raw = "Top.\n" + "> " * 17 + "x\n"
    source, res = go(raw)
    check(kinds(raw) == ["authored"], "over-deep line must not be a zone")
    check(res.limitations == ("quote_depth_limit",), "limitation expected")
    check(len(res.unknown) == 1, "the line must be unknown")
    check_tiling(raw, source, res)
    check(kinds("> " * 16 + "x\n") == ["quote"], "depth 16 is allowed")


# --- attribution --------------------------------------------------------


@pytest.mark.parametrize("author", [AUTHOR, "ALICE@Example.COM", "alice@example"])
def test_quote_is_never_attributed_to_the_author(author: str) -> None:
    raw = "On Mon, Alice <alice@example.com> wrote:\n> mine\n"
    _, res = go(raw, author=author)
    check(zs(res)[0].quote_author_sha256 is None, "self attribution")


def test_attribution_table_never_names_the_author() -> None:
    raws = (
        "On Mon, Alice <alice@example.com> wrote:\n> a\n",
        "On A, Bob wrote:\n> On Mon, Alice <alice@example.com> wrote:\n> > old\n",
        "x\nFrom: Alice <alice@example.com>\nSent: s\nTo: t\nSubject: u\n\nbody\n",
        "On Mon, Bob wrote:\n> b\n",
    )
    own = {digest(AUTHOR), digest("alice <alice@example.com>")}
    for raw in raws:
        source, res = go(raw)
        quotes = [z for z in (zs(res) if res.zones else ()) if z.kind == "quote"]
        check(bool(quotes), "a quote zone is expected")
        for z in quotes:
            check(z.quote_author_sha256 not in own, "quote names the author")
        check_quotes_not_authored(source, res)
    _, nested = go(raws[1])
    got = [z.quote_author_sha256 for z in zs(nested)]
    check(got == [digest("a, bob"), None], "nested self claim must drop")


# --- forward header -----------------------------------------------------

HEADER = (
    "From: Bob Example <bob@example.org>\nSent: Monday, October 5, 2026 9:00 AM\n"
    "To: Alice <alice@example.com>\nSubject: Plan\n"
)


def test_outlook_forward_header() -> None:
    raw = f"FYI below.\n\n{HEADER}\nBody one.\nBody two.\n"
    source, res = go(raw)
    got = view(source, res)
    check(
        [g[:2] for g in got] == [("authored", 0), ("forward_header", 0), ("quote", 1)],
        "forward kinds differ",
    )
    check(got[1][2] == HEADER + "\n", "header zone differs")
    check(got[2][2] == "Body one.\nBody two.\n", "forwarded body differs")
    want = digest("bob example <bob@example.org>")
    check(zs(res)[2].quote_author_sha256 == want, "forward claim")
    check_tiling(raw, source, res)


def test_forward_with_separator_and_cc() -> None:
    cc = HEADER.replace("Subject", "Cc: Dan\nSubject")
    raw = f"-----Original Message-----\n{cc}\nOld text.\n"
    source, res = go(raw)
    check([g[0] for g in view(source, res)] == ["forward_header", "quote"], "kinds")
    check(view(source, res)[0][2].startswith("-----Original"), "separator joins")


@pytest.mark.parametrize(
    "raw",
    [
        "Note.\nFrom: Bob\nSubject: Plan\nbody\n",
        "Note.\nFrom: Bob\nTo: A\nSent: s\nSubject: Plan\nbody\n",
        "Note.\nFrom: Bob\nSent: s\nTo: A\nSubject: Plan\nFrom: C\nbody\n",
    ],
)
def test_malformed_forward_header_is_unknown(raw: str) -> None:
    source, res = go(raw)
    check(kinds(raw) == ["authored"], "a bad header must not be a zone")
    check(len(res.unknown) == 1 and res.unknown[0].start == 6, "tail unknown")
    check_tiling(raw, source, res)


def test_lone_from_line_is_plain_text() -> None:
    check(kinds("From: the start\nthen more\n") == ["authored"], "lone From:")


# --- signature -----------------------------------------------------------


def test_signature_delimiter() -> None:
    raw = "Regards text.\n-- \nAlice Example\nExample Corp\n"
    source, res = go(raw)
    check(
        view(source, res)
        == [
            ("authored", 0, "Regards text.\n"),
            ("signature", 0, "-- \nAlice Example\nExample Corp\n"),
        ],
        "signature zone differs",
    )
    check_tiling(raw, source, res)
    top = kinds("Top.\n-- \nAlice\nOn Tue, Bob wrote:\n> q\n")
    check(top == ["authored", "signature", "quote"], "signature stops at a quote")


@pytest.mark.parametrize("line", ["--", "---", "--flag", "-- x", " -- ", "- -"])
def test_dashes_line_is_not_a_signature(line: str) -> None:
    check("signature" not in kinds(f"Intro\n{line}\nmore\n"), "false positive")


def test_signature_size_boundary_and_mid_body_delimiter() -> None:
    check(kinds("a\n-- \n" + "s\n" * 11) == ["authored", "signature"], "12 lines")
    raw = "a\n-- \n" + "s\n" * 12
    source, res = go(raw)
    check(kinds(raw) == ["authored"], "13 lines must be unknown")
    check(len(res.unknown) == 1, "the long region is one unknown range")
    check_tiling(raw, source, res)


def test_empty_and_blank_input_have_no_zones() -> None:
    _, empty = go("")
    check(empty.zones is None and empty.unknown == (), "empty input")
    check(empty.content.normalized_length == 0, "empty content")
    raw = "\n\n \n"
    source, blank = go(raw)
    check(blank.zones is None and len(blank.unknown) == 1, "blank input")
    check_tiling(raw, source, blank)


@pytest.mark.parametrize(
    "raw",
    [
        "In.\nOn Tue, Bob wrote:\nplain follow\n",
        "In.\nOn Tue, Bob wrote:\n",
        "In.\nOn wrote:\n> q\n",
        "In.\nOn Tue, Bob wrote:\n> > deeper\n",
        "In.\nOn Tue, Bob wrote:\n\n> q\n",
    ],
)
def test_ambiguous_marker_is_unknown(raw: str) -> None:
    source, res = go(raw)
    check(kinds(raw) == ["authored"], "an ambiguous marker made a zone")
    check(res.unknown[0].start == 4, "unknown must start at the marker")
    check_tiling(raw, source, res)


def test_non_markers_are_plain() -> None:
    check(kinds("bob wrote:\nnext\n") == ["authored"], "needs the On prefix")
    long_marker = "On " + "x " * 400 + "wrote:\n> q\n"
    source, res = go(long_marker)
    got = view(source, res)
    check([g[:2] for g in got] == [("authored", 0), ("quote", 1)], "long marker")
    check(zs(res)[1].quote_author_sha256 is None, "no claim from long line")


# --- invariants and offset map ----------------------------------------------

TABLE = (
    "",
    "x",
    "\n",
    "> a",
    "-- ",
    "-- \n",
    "On x wrote:",
    "From: a\nSent: b\nTo: c\nSubject: d",
    "> " * 20 + "deep",
    "Gr\u00fc\u00dfe\n> \u4f60\u597d\n-- \nAlic\u00e9\n",
    "a\r\n> b\r\n",
    "z\u200bw\n\n\n\n> q\n",
    FIRST,
    FIRST + "> again\n" + BLOCK + "-- \nSig\n",
    "a\n> b\n" * 10,
    "On Tue, Bob wrote:\n> q\n\n\n\nafter\n-- \ns\n",
    f"top\n{HEADER}\n> inner\n> inner\n",
    "-----\n" + HEADER + "\n",
    "  \n> a\n  \n",
    "cafe\u0301\n> q\n\u0344 x\n",
)


def test_tiling_invariant_over_table() -> None:
    check(len(TABLE) >= 15, "the table is too small")
    for raw in TABLE:
        source, res = go(raw)
        check_tiling(raw, source, res)
        check_quotes_not_authored(source, res)
        if res.zones:
            check(ContentZones.decode(res.zones.encode()) == res.zones, "wire form")


def test_offset_map_round_trip() -> None:
    raw = (
        "Hi\u200b all,\r\n\r\n\r\n\r\nSee   below.\r\n> quoted\u200b text\r\n> more\r\n"
    )
    source, res = go(raw)
    data = raw.encode("utf-8")
    for z in zs(res):
        lo, hi = res.content.project(z.normalized.start, z.normalized.end)
        check((lo, hi) == (z.original.start, z.original.end), "projection differs")
        old = data[z.original.start : z.original.end].decode("utf-8")
        new = source.text.encode("utf-8")[z.normalized.start : z.normalized.end]
        check(normalize_text(old).text.encode("utf-8") == new, "slice round trip")
    check(zs(res)[0].original.start == 0, "first zone starts at zero")


def test_non_ascii_and_shrinking_normalization() -> None:
    raw = "cafe\u0301 ok\n> \u4f60\u597d \u00fc\n"
    source, res = go(raw)
    first, second = zs(res)
    check(first.normalized.end - first.normalized.start == 9, "NFC length")
    check(first.original.end - first.original.start == 10, "original length")
    check(second.original.start == 10 and second.normalized.start == 9, "shift")
    check_tiling(raw, source, res)


def test_edge_inside_a_rewrite_becomes_unknown() -> None:
    raw = "> q\n\u0344 text"
    source, res = go(raw)
    check(res.limitations == ("unmapped_boundary",), "limitation expected")
    check(
        view(source, res) == [("quote", 1, "> q"), ("authored", 0, " text")],
        "zones must shrink to the segment edge",
    )
    data = source.text.encode("utf-8")
    gap = data[res.unknown[0].start : res.unknown[0].end]
    check(gap == "\n\u0308\u0301".encode(), "the rewrite must be unknown")
    check_tiling(raw, source, res)


def test_zone_cap_gives_typed_limitation() -> None:
    raw = "a\n> b\n" * 50
    source, res = go(raw, max_zones=5)
    check(res.zones is not None and len(zs(res)) == 5, "cap not applied")
    check(res.limitations == ("zone_limit",), "limitation expected")
    check_tiling(raw, source, res)
    big_raw = "a\n> b\n" * 600
    big_source, big = go(big_raw)
    check(big.zones is not None and len(zs(big)) == 1024, "contract cap")
    check(big.limitations == ("zone_limit",), "contract cap limitation")
    check_tiling(big_raw, big_source, big)


@pytest.mark.parametrize("bad", [0, 1025, True])
def test_bad_max_zones_is_refused(bad: int) -> None:
    source = normalize_text("x")
    with pytest.raises(A2ContractError):
        build_zones("x", source, part_id="p", author=AUTHOR, max_zones=bad)


def test_bad_arguments_and_no_text_in_messages() -> None:
    raw = "SECRETWORD body\n> SECRETWORD\n"
    source = normalize_text(raw)
    for kw in ({"part_id": "", "author": "a"}, {"part_id": "p", "author": "  "}):
        with pytest.raises(A2ContractError) as info:
            build_zones(raw, source, **kw)  # type: ignore[arg-type]
        check("SECRETWORD" not in str(info.value), "message carries text")
    with pytest.raises(A2ContractError) as info:
        build_zones(raw + "x", source, part_id="p", author=AUTHOR)
    check("SECRETWORD" not in str(info.value), "message carries text")
    with pytest.raises(A2ContractError):
        build_zones(raw, "text", part_id="p", author=AUTHOR)  # type: ignore[arg-type]
    check("SECRETWORD" not in repr(go(raw)[1]), "repr carries text")


# --- mutation checks ---------------------------------------------------------


def conformance() -> list[str]:
    """Return the names of the rules that the current rule set breaks."""
    bad: list[str] = []
    for line in ("--", "---", "--flag", "-- x"):
        if "signature" in kinds(f"Intro\n{line}\nmore\n"):
            bad.append("signature_false_positive")
    if kinds("Intro\n-- \nAlice\n") != ["authored", "signature"]:
        bad.append("signature_missed")
    if kinds("> a\n> b\n") != ["quote"]:
        bad.append("quote_read_as_authored")
    _, res = go("On Mon, Alice <alice@example.com> wrote:\n> mine\n")
    if res.zones is None or zs(res)[0].quote_author_sha256 is not None:
        bad.append("quote_attributed_to_author")
    return bad


def test_conformance_holds_for_the_real_rules() -> None:
    check(conformance() == [], "the real rules must pass the conformance set")


def test_mutation_signature_prefix_match_is_caught(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        zmod, "_is_signature_delimiter", lambda line: line.startswith("--")
    )
    check("signature_false_positive" in conformance(), "mutation not caught")


def test_mutation_quote_depth_ignored_is_caught(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(zmod, "_quote_depth", lambda text, start, end: (0, 0))
    check("quote_read_as_authored" in conformance(), "mutation not caught")


def test_mutation_author_check_removed_is_caught(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(zmod, "_names_author", lambda claim, author: False)
    check("quote_attributed_to_author" in conformance(), "mutation not caught")
