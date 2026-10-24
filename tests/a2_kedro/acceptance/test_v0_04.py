"""
V0-04 acceptance: the real P2 parsers against the independent gold files.

Oracle: ``golden/t0_02.json`` (Mail/MIME) and ``golden/t0_05.json`` (PDF,
Word, Excel, malformed, large and partial input), checked against
``golden/MANIFEST.sha256`` at test start. The gold files are read only.

Method: for each gold case the test builds synthetic input bytes by hand
from the case ``input`` or ``description`` (``v0_04_fixtures``), runs the
real parser that ``parsers/registry.py`` names for it, and compares observed
facts with the gold ``expected`` block (``v0_04_gold``). No expected value
comes from the implementation. A disagreement is marked
``xfail(strict=True)`` and pinned by a second test that names the exact
fields that differ.

Other text types:

* HTML: the only gold HTML is the text/html leaf of ``T0-02-P01``. The bare
  ``html`` key has no parser in the registry (P2-11). P2-01 reads HTML inside
  a message.
* JSON: no case of ``t0_02`` or ``t0_05`` uses JSON. The JSON tests are
  structural only (a parse error is never complete, limitations hold no
  content, spans slice the source). They state no invented expected answer.

Mapping decisions: implementation ``INCOMPLETE`` is oracle ``partial``. Gold
``contributed_text`` is the text of the P2-08 ``authored`` zones. Gold
``quoted_text`` is the ``>`` lines of the ``quote`` zones. Grouping fields
belong to the P3 relation lane, which this branch does not contain.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from functools import lru_cache
from typing import Any

import pytest

from msgloom.a2_kedro.parsers.failure_policy import (
    FailureDecision,
    FailureOutcome,
    FailureReason,
    check_formats,
    classify_exception,
)
from msgloom.a2_kedro.parsers.mime_html import MimeParseResult
from msgloom.a2_kedro.parsers.plain_json import Outcome as JsonOutcome
from msgloom.a2_kedro.parsers.plain_json import ParseResult
from msgloom.a2_kedro.parsers.registry import ParserRefusal, parser_for, resolve
from msgloom.contracts import TerminalStatus
from tests.a2_kedro.acceptance import v0_04_fixtures as fx
from tests.a2_kedro.acceptance.v0_04_gold import (
    CANARY,
    GOLD_FILES,
    Cmp,
    all_cases,
    file_digest,
    leaks,
    manifest_digests,
    observe,
    parse_msg,
    parse_text,
    region_quote,
    span_problems,
    text_parts,
    zone_facts,
)
from tests.a2_kedro.helpers import check

CASES = all_cases()
CHECKS: dict[str, Callable[[Cmp], None]] = {}
AUTHOR = "reply.writer@example.invalid"
SHORT = "grouping, ancestors and references belong to the P3 relation lane"

#: Gold cases that no P2 API can answer. Each entry names the reason.
NOT_MAPPABLE: dict[str, str] = {
    "T0-02-N01": f"duplicate Message-ID: {SHORT}, absent here",
    "T0-02-N02": f"ambiguous duplicate parent: {SHORT}, absent here",
    "T0-02-N03": f"equal subjects never group: {SHORT}, absent here",
    "T0-02-N05": f"parent cycle: {SHORT}, absent here",
    "T0-02-N06": f"shared conversation ID: {SHORT}, absent here",
}
_REL = ("ancestors", "missing_references", "grouping_status", "group_confirmed")
_NOFIELD = "no result field states equivalence or preference; roles follow order"
#: Gold keys of a covered case that no P2 API can answer.
UNMAPPED: dict[str, dict[str, str]] = {
    "T0-02-P01": {
        "alternatives_equivalence_inferred": _NOFIELD,
        "preferred_alternative_inferred": _NOFIELD,
        "ancestors": SHORT,
        "missing_references": SHORT,
    },
    "T0-02-P02": {k: SHORT for k in _REL},
    "T0-02-P03": {k: SHORT for k in (*_REL, "ancestor_order")},
    "T0-02-P04": {k: SHORT for k in _REL},
    "T0-05-P06": {"a1_error_class": "a FAILED result is returned, no A1 class"},
}

#: Implementation vs gold disagreements: reason and the pinned bad fields.
DISAGREEMENTS: dict[str, tuple[str, frozenset[str]]] = {
    "T0-02-P01": (
        (
            "no alternatives limitation (COMPLETE, limitations empty) and "
            "text_by_part[1.2] keeps a trailing newline from </p>"
        ),
        frozenset({"alternatives_limitation_present", "text_by_part[1.2]"}),
    ),
    "T0-05-P05": (
        (
            "legacy .doc gives FAILED encrypted_or_ole, gold status unsupported "
            "with limitation unsupported"
        ),
        frozenset({"status", "limitations"}),
    ),
    "T0-05-N03": (
        "ZIP size bomb gives INCOMPLETE zip_limit, gold status failed",
        frozenset({"status"}),
    ),
    "T0-05-N04": (
        (
            "5000-page PDF gives INCOMPLETE page_limit (500 pages kept), "
            "gold status failed"
        ),
        frozenset({"status"}),
    ),
}


def gold(*case_ids: str) -> Callable[[Callable[[Cmp], None]], Callable[[Cmp], None]]:
    """Register one check function for the given gold cases."""

    def register(fn: Callable[[Cmp], None]) -> Callable[[Cmp], None]:
        CHECKS.update(dict.fromkeys(case_ids, fn))
        return fn

    return register


def run(case_id: str) -> Cmp:
    """Run the check of one gold case and return the comparison record."""
    cm = Cmp(CASES[case_id])
    CHECKS[case_id](cm)
    return cm


def message(case: Mapping[str, Any]) -> tuple[bytes, MimeParseResult]:
    """Build the message of a gold case with ``parts`` and parse it."""
    inp = case["input"]
    sender = inp.get("from", "a@example.invalid")
    data = fx.build_mime(inp["parts"], inp["message_id"], sender)
    return data, parse_msg(data)


# --- t0_02: Mail/MIME -------------------------------------------------------


@gold("T0-02-P02", "T0-02-P03", "T0-02-P04", "T0-02-N04")
def reply_text(cm: Cmp) -> None:
    inp = cm.case["input"]
    res = parse_msg(fx.plain_message(inp["text"], inp["message_id"]))
    own, quoted, attribution = zone_facts(text_parts(res, ("body",))["1"], AUTHOR)
    cm.eq("contributed_text", own)
    if cm.has("quoted_text"):
        cm.eq("quoted_text", quoted)
        cm.flag("quoted_text[mime_regions]", region_quote(res) == quoted)
    if cm.has("attribution_line"):
        cm.eq("attribution_line", attribution)
    if cm.has("canary_in_contributed_text"):
        cm.eq("canary_in_contributed_text", CANARY in own)


@gold("T0-02-P01")
def alternatives(cm: Cmp) -> None:
    _, res = message(cm.case)
    got = text_parts(res, ("body", "alternate"))
    cm.eq("extracted_part_refs", sorted(got))
    cm.eq_map("text_by_part", got)
    cm.eq("alternatives_limitation_present", bool(res.limitations))


@gold("T0-02-P05")
def attachment(cm: Cmp) -> None:
    _, res = message(cm.case)
    cm.eq("contributed_text", "\n".join(text_parts(res, ("body",)).values()))
    cm.eq("attachment_parts", [p.path for p in res.parts if p.role == "attachment"])
    merged = any(p.text for p in res.parts if p.role == "attachment")
    cm.eq("attachment_text_merged_into_body", merged)


@gold("T0-02-P06", "T0-02-P07")
def transfer_decoded(cm: Cmp) -> None:
    _, res = message(cm.case)
    got = text_parts(res, ("body", "alternate"))
    cm.eq("extracted_part_refs", sorted(got))
    cm.eq_map("text_by_part", got)
    raw = cm.case["input"]["parts"][0]["raw"]
    cm.eq("raw_encoded_text_kept", any(raw in t for t in got.values()))


@gold("T0-02-P08")
def empty_body(cm: Cmp) -> None:
    _, res = message(cm.case)
    got = text_parts(res, ("body",))
    cm.eq("contributed_text", "\n".join(got.values()))
    cm.eq("message_record_kept", bool(res.parts) and res.parts[0].path == "1")
    cm.eq("placeholder_text_invented", any(t.strip() for t in got.values()))
    cm.eq("parse_failed", res.status is TerminalStatus.FAILED)


@gold("T0-02-P09")
def forwarded_message(cm: Cmp) -> None:
    _, res = message(cm.case)
    body = text_parts(res, ("body",))
    cm.eq("contributed_text", "\n".join(body.values()))
    cm.eq(
        "attachment_parts", [p.path for p in res.parts if p.disposition == "attachment"]
    )
    meta = [p.path for p in res.parts if p.role in ("attachment", "embedded")]
    cm.eq("metadata_only_parts", meta)
    cm.eq("inner_text_in_body", any("Inner message" in t for t in body.values()))
    cm.eq("canary_in_contributed_text", any(CANARY in t for t in body.values()))


@gold("T0-02-N07", "T0-02-N08")
def defect_is_generic_limitation(cm: Cmp) -> None:
    inp = cm.case["input"]
    try:
        if "content_type" in inp:
            head = f"Message-ID: {inp['message_id']}\r\nContent-Type: "
            data = (head + inp["content_type"] + "\r\n\r\n" + inp["raw"]).encode()
            res = parse_msg(data)
        else:
            res = message(cm.case)[1]
    except Exception:  # noqa: BLE001 - the case asks whether anything is raised
        cm.eq("exception_raised", True)
        return
    cm.eq("exception_raised", False)
    codes = {lim.code for lim in res.limitations}
    if cm.has("structural_limitation_present"):
        found = codes & {"multipart_truncated", "multipart_malformed"}
        cm.eq("structural_limitation_present", bool(found))
        lines = [x for x in inp["raw"].splitlines() if x and x[:2] != "--"]
        lines = [x for x in lines if not x.startswith("Content-")]
        cm.eq("limitation_detail_contains_body_text", leaks(res, lines))
    else:
        found = codes & {"base64_corrupt", "qp_corrupt", "cte_unknown"}
        cm.eq("transfer_limitation_present", bool(found))
    cm.eq("limitation_detail_contains_canary", CANARY in repr(res.limitations))
    cm.eq("reported_as_clean_complete", res.status is TerminalStatus.COMPLETE)


# --- t0_05: documents -------------------------------------------------------


@lru_cache(maxsize=1)
def zip_bomb() -> bytes:
    return fx.zip_with_large_member(70 * 1024 * 1024)


@lru_cache(maxsize=1)
def big_pdf() -> bytes:
    return fx.pdf_5000_pages()


def two_page_pdf() -> bytes:
    return fx.build_pdf([b"Quarterly summary", b"Totals follow"])[0]


def locked_pdf() -> bytes:
    return fx.build_pdf([b"secret page"], password=b"pw")[0]


def bad_central_directory() -> bytes:
    return fx.damaged_central_directory(fx.notes_docx())


DOC_INPUTS: dict[str, tuple[str, Callable[[], bytes]]] = {
    "T0-05-P01": ("pdf", two_page_pdf),
    "T0-05-P02": ("docx", fx.notes_docx),
    "T0-05-P03": ("xlsx", fx.items_xlsx),
    "T0-05-P04": ("pdf", lambda: fx.build_pdf([fx.IMAGE])[0]),
    "T0-05-P05": ("docx", fx.legacy_doc),
    "T0-05-P06": ("pdf", locked_pdf),
    "T0-05-P07": ("xlsx", lambda: fx.items_xlsx(chart=True)),
    "T0-05-N01": ("pdf", fx.pdf_cut_in_xref),
    "T0-05-N02": ("docx", bad_central_directory),
    "T0-05-N03": ("xlsx", zip_bomb),
    "T0-05-N04": ("pdf", big_pdf),
    "T0-05-N07": ("docx", fx.docx_with_ole),
}


@gold(*DOC_INPUTS)
def document(cm: Cmp) -> None:
    key, make = DOC_INPUTS[cm.case["case_id"]]
    seen = observe(key, make())
    # P04: the empty read (no_text) is the stated consequence of a scanned page.
    cm.common(seen, ("missing",) if cm.case["case_id"] == "T0-05-P04" else ())
    if cm.has("ocr_attempted"):
        cm.eq("ocr_attempted", any(t.strip() for t in seen.texts))
    if cm.has("limitation_subject"):
        cm.flag("limitation_subject", "charts" in seen.codes)
    if cm.has("worksheet_cells_still_present"):
        cm.eq("worksheet_cells_still_present", bool(seen.cells))


DECISION_STATUS = {
    FailureOutcome.UNKNOWN: "failed",
    FailureOutcome.MIME_MISMATCH: "failed",
    FailureOutcome.PARTIAL: "partial",
    FailureOutcome.UNSUPPORTED: "unsupported",
}


def decision_facts(cm: Cmp, decision: FailureDecision | None) -> FailureDecision:
    if decision is None:
        pytest.fail("a failure decision must exist")
    cm.eq("status", DECISION_STATUS[decision.outcome])
    cm.eq("status_is_complete", decision.is_complete)
    return decision


@gold("T0-05-N05")
def worker_crash(cm: Cmp) -> None:
    decision = classify_exception(RuntimeError("worker exited without output"))
    decision_facts(cm, decision)
    cm.eq("empty_text_reported_as_complete", decision.is_complete)


@gold("T0-05-N06")
def wrong_format(cm: Cmp) -> None:
    note = ("A plain text note. " + CANARY).encode("ascii")
    # Declared pdf; the bytes are text, so the detected format is plain_text.
    decision = decision_facts(cm, check_formats("pdf", "plain_text"))
    parsed = observe("pdf", note)
    cm.flag("status[pdf parser]", parsed.status == "failed")
    cm.eq("error_visible", bool(parsed.codes))
    cm.flag("reason", decision.reason is FailureReason.DETECTED_FORMAT_DIFFERS)


# --- tests: oracle, scan guard, gold cases ----------------------------------


def test_gold_digests_match_manifest() -> None:
    table = manifest_digests()
    for name in GOLD_FILES:
        check(name in table, f"{name} is listed in MANIFEST.sha256")
        check(file_digest(name) == table[name], f"{name} digest differs")


def test_scan_guard_every_gold_case_is_covered_or_listed() -> None:
    check(len(CASES) == 31, "t0_02 (17 cases) and t0_05 (14 cases) were loaded")
    check(set(CHECKS).isdisjoint(NOT_MAPPABLE), "a case is checked or not mappable")
    check(set(CHECKS) | set(NOT_MAPPABLE) == set(CASES), "every gold id is accounted")
    check(set(DISAGREEMENTS) <= set(CHECKS), "a disagreement is a checked case")
    check(all(NOT_MAPPABLE.values()), "every not-mappable case names a reason")
    check(all(why for why, _ in DISAGREEMENTS.values()), "every xfail has a reason")


@pytest.mark.parametrize("case_id", sorted(CHECKS))
def test_every_expected_key_is_checked_or_declared_unmapped(case_id: str) -> None:
    cm = run(case_id)
    keys = set(cm.expected)
    seen = {k.split("[")[0] for k in cm.checked}
    unmapped = set(UNMAPPED.get(case_id, {}))
    check(not seen & unmapped, f"{case_id}: an unmapped key was also checked")
    check(keys - seen == unmapped, f"{case_id}: unchecked {sorted(keys - seen)}")


def _param(case_id: str) -> Any:
    marks = []
    if case_id in DISAGREEMENTS:
        reason = f"V0-04 DISAGREEMENT {case_id}: {DISAGREEMENTS[case_id][0]}"
        marks.append(pytest.mark.xfail(strict=True, reason=reason))
    return pytest.param(case_id, marks=marks, id=case_id)


@pytest.mark.parametrize("case_id", [_param(c) for c in sorted(CHECKS)])
def test_gold_case(case_id: str) -> None:
    cm = run(case_id)
    check(not cm.bad, f"{case_id} differs from gold in {sorted(cm.bad)}")


@pytest.mark.parametrize("case_id", sorted(DISAGREEMENTS))
def test_disagreement_is_pinned_to_the_named_fields(case_id: str) -> None:
    """The xfail may hide only the documented fields, nothing else."""
    check(set(run(case_id).bad) == DISAGREEMENTS[case_id][1], f"{case_id} drifted")


# --- tests: invariants that the gold implies --------------------------------


def test_alternatives_are_extracted_separately_and_not_merged() -> None:
    want = CASES["T0-02-P01"]["expected"]["text_by_part"]
    got = text_parts(message(CASES["T0-02-P01"])[1], ("body", "alternate"))
    check(sorted(got) == ["1.1", "1.2"], "two leaves and no merged third text")
    check(got["1.1"] == want["1.1"], "plain alternative text")
    check(got["1.2"].strip() == want["1.2"], "html alternative text up to newline")


def test_disagreement_inputs_are_never_complete_and_publish_no_full_content() -> None:
    inputs = (("pdf", big_pdf()), ("xlsx", zip_bomb()), ("docx", fx.legacy_doc()))
    for key, data in inputs:
        seen = observe(key, data)
        check(seen.status != "complete", f"{key} input must not be complete")
        check(bool(seen.codes), f"{key} input shows a visible limitation")
        check(not seen.cells, f"{key} input publishes no cell")
    check(0 < observe("pdf", big_pdf()).pages < 5000, "not all 5000 pages published")
    check(not any(observe("docx", fx.legacy_doc()).texts), "legacy .doc has no text")


def test_text_and_html_spans_map_back_to_the_decoded_body() -> None:
    case = CASES["T0-02-P01"]
    data, res = message(case)
    for ref in ("1.1", "1.2"):
        leaf = next(p for p in case["input"]["parts"] if p["ref"] == ref)
        check(not span_problems(res, ref, leaf["text"]), f"spans of {ref}")
        part = next(p for p in res.parts if p.path == ref)
        check(leaf["text"].encode() in data[part.start : part.end], f"{ref} window")
    for cid in ("T0-02-P06", "T0-02-P07"):
        decoded = CASES[cid]["expected"]["text_by_part"]["1"]
        check(not span_problems(message(CASES[cid])[1], "1", decoded), f"{cid} spans")


def test_unclosed_html_script_is_never_clean() -> None:
    head = b"Content-Type: text/html; charset=utf-8\r\n\r\n"
    res = parse_msg(head + b"<p>kept text</p><script>var x = 1;")
    check(res.status is TerminalStatus.INCOMPLETE, "a parse defect is not complete")
    check("html_parse_error" in {lim.code for lim in res.limitations}, "limitation")
    check("var x" not in repr(res.limitations), "no content in limitations")


def test_json_parse_error_is_never_complete_and_leaks_nothing() -> None:
    def parse(data: bytes) -> ParseResult:
        return parse_text("json", data)

    good = parse(b'{"note": "x", "list": ["a", null]}')
    check(good.outcome is JsonOutcome.COMPLETE and not good.limitations, "valid")
    check([f.pointer for f in good.fields] == ["/note", "/list/0", "/list/1"], "ptrs")
    for text in (f'{{"note": "{CANARY} cut', f'{{"note": {CANARY}}}'):
        bad = parse(text.encode())
        check(bad.outcome is not JsonOutcome.COMPLETE, "a parse error is not complete")
        check(bool(bad.limitations), "a limitation is visible")
        check(CANARY not in repr(bad) + repr(bad.limitations), "no content in result")
    cut = parse(b'{"note": "abc')
    check([str(x) for x in cut.limitations] == ["truncated_json"], "cut JSON")


def test_plain_text_spans_slice_the_source_bytes() -> None:
    source = b"line one\r\nline two\n\nsecond block"
    res = parse_text("plain_text", source)
    check(not res.limitations, "clean text has no limitation")
    lines = [ln.span.slice(source) for ln in res.lines]
    check(lines[:2] == [b"line one", b"line two"], "line spans")
    ends = [ln.span.offset + ln.span.length for ln in res.lines]
    starts = [ln.span.offset for ln in res.lines]
    check(all(a <= b for a, b in zip(ends, starts[1:], strict=False)), "ordered")
    check(res.blocks[-1].span.slice(source) == b"second block", "last block")


def test_registry_routes_and_refusals() -> None:
    for key in ("rfc822", "plain_text", "json", "pdf", "docx", "xlsx"):
        check(parser_for(key).key == key, f"{key} is registered")
    for key, code in (("html", "format_unsupported"), ("doc", "format_unknown")):
        refusal = resolve(key)
        if not isinstance(refusal, ParserRefusal):
            pytest.fail(f"{key} must be refused")
        check(refusal.status is TerminalStatus.FAILED, f"{key} refusal is failed")
        check(refusal.limitation.code == code, f"{key} refusal code")
