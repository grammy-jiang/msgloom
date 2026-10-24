"""Validate the hand-written T0-08 historical reader oracle.

A language model annotated every decision in ``golden/t0_08.json`` from the
A2 Kedro v2 blueprint, the frozen v1 contract and the A1 fixtures. The small
reference reader below only checks that the answers agree with each other. Each rule of
the reader has a name and can be switched off, so that the mutation tests in
``test_gold_t0_08_mutants.py`` can prove that the oracle needs the rule. This
module never imports ``msgloom``.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from test_gold_t0_08_reader import (
    V1_FIELDS,
    V2_FIELDS,
    Case,
    evaluate,
    materialize,
)

GOLDEN = Path(__file__).resolve().parent / "golden"
FIXTURE = GOLDEN / "t0_08.json"
MANIFEST = GOLDEN / "MANIFEST.sha256"
NOTE = Path(__file__).resolve().parents[2] / "docs/notes/a2-v2-golden-t0-08.md"

RULE_CASES = {
    "label_kind_exact": ("N05", "N07"),
    "label_version_exact": ("N01", "N02", "N03", "N04", "N06", "N38"),
    "v1_codec_strict": ("N08",),
    "unexpected_fields": ("N08", "N09", "N10", "N11", "N29"),
    "missing_fields": ("N12", "N22", "N23", "N33"),
    "canonical_defaults": ("N13",),
    "enum_and_text": ("N15", "N20", "N21", "N27", "N30", "N32"),
    "aware_time": ("N14",),
    "pending_no_rule": ("N16",),
    "parsed_refs_unique": ("N18",),
    "parsed_refs_dangling": ("N17",),
    "mapping_range": ("N19",),
    "v2_selection_valid": ("N31",),
    "v2_lineage_kinds": ("N26",),
    "v2_zone_range": ("N28",),
    "v2_status_consistency": ("N25",),
    "status_counts_all_sources": ("N24",),
    "projection_forbidden": ("N34", "N35"),
    "binding_line": ("N36", "N37"),
    "preserve_all_fields": ("P08",),
    "no_invented_fields": ("P01", "P02"),
    "limitations_all_sources": ("P01", "P04", "P08", "P10", "P11"),
    "limitation_order": ("P08",),
    "limitation_no_dedupe": ("P08",),
    "text_verbatim": ("P05",),
}  # fmt: skip
CODES = (
    "unknown_version", "unexpected_field", "missing_field", "not_canonical",
    "bad_value", "naive_time", "pending_with_rule", "dangling_parsed_ref",
    "duplicate_parsed_ref", "bad_range", "status_limitation_mismatch",
    "lineage_kind_mismatch", "lossy_projection_forbidden",
    "ref_version_not_allowed",
)  # fmt: skip
PROPOSED = "proposed_owner_signoff_needed"
PROPOSED_CASE = "T0-08-N37"
OPERATIONS = ("read", "force_v1_codec", "project_to_v1", "bind_triage_input")
TOPICS = (
    "historical_v1", "historical_unchanged", "v2_mapping", "limitations",
    "lossy_projection", "version_rejection", "tamper", "missing_field",
    "binding",
)  # fmt: skip
SOURCES = (
    "BP-2", "BP-4", "BP-4.1", "BP-4.2", "BP-8.1", "PLAN-C0-17", "V1-RECORDS",
    "V1-CODEC", "V1-TRIAGE-CODEC", "A1-FIXTURE",
)  # fmt: skip
COVERAGE = [f"T0-08-P{n:02d}" for n in range(1, 14)]
COVERAGE += [f"T0-08-N{n:02d}" for n in range(1, 39)]
PINNED = ("T0-08-P01", "T0-08-P02")
LINKED = ("T0-08-P06",)


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    if len({key for key, _ in pairs}) != len(pairs):
        raise ValueError("duplicate JSON key")
    return dict(pairs)


def load_strict(path: Path) -> Any:
    """Load JSON and reject duplicate object keys."""
    with path.open(encoding="utf-8") as handle:
        return json.load(handle, object_pairs_hook=_no_duplicates)


def _doc() -> dict[str, Any]:
    return load_strict(FIXTURE)


def _cases() -> list[Case]:
    return _doc()["cases"]


def _case(case_id: str) -> Case:
    for case in _cases():
        if case["case_id"].endswith(case_id):
            return case
    raise KeyError(case_id)


def _ids() -> list[str]:
    return [c["case_id"] for c in _cases()]


# ---------------------------------------------------------------- checker ----


def _canonical(payload: Any) -> bytes:
    text = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return text.encode("utf-8")


def check_case(case: Case, doc: dict[str, Any], all_cases: list[Case]) -> list[str]:
    """Return the problems of one case. An empty list means the case is sound."""
    try:
        return _problems(case, doc, all_cases)
    except (KeyError, TypeError, AttributeError, ValueError, IndexError) as error:
        return [f"malformed case: {type(error).__name__} {error}"]


def _problems(case: Case, doc: dict[str, Any], all_cases: list[Case]) -> list[str]:
    bad: list[str] = []
    top = {"case_id", "polarity", "topic", "title", "input", "expected", "rationale", "source"}  # fmt: skip
    extra = {"links", "pinned", "policy_status"}
    if not top <= set(case) <= top | extra:
        return [f"case keys {sorted(set(case) ^ top)}"]
    # Only N37 is a proposed policy; it needs the marker, no other case may carry it.
    want_status = PROPOSED if case["case_id"] == PROPOSED_CASE else None
    if case.get("policy_status") != want_status:
        return [f"policy_status {case.get('policy_status')!r}, want {want_status!r}"]
    inp, exp = case["input"], case["expected"]
    stored = inp["stored"]
    want = {"operation", "stored"} | ({"target"} if inp["operation"] == "bind_triage_input" else set())  # fmt: skip
    if set(inp) != want or inp["operation"] not in OPERATIONS:
        bad.append("bad input keys or operation")
    if set(stored) != {"kind", "schema_version", "base", "edits"}:
        bad.append("bad stored keys")
    if stored["base"] not in doc["bases"]:
        return [*bad, "unknown base"]
    for edit in stored["edits"]:
        keys = {"set": {"op", "path", "value"}, "delete": {"op", "path"}, "copy": {"op", "path", "from"}}  # fmt: skip
        if set(edit) != keys.get(edit.get("op")):
            bad.append(f"bad edit {edit}")
    if inp["operation"] == "project_to_v1" and stored["schema_version"] != "2":
        bad.append("project_to_v1 needs a version 2 record")
    if case["polarity"] not in ("positive", "negative") or case["topic"] not in TOPICS:
        bad.append("bad polarity or topic")
    if (case["polarity"] == "positive") != (exp["decision"] == "accept"):
        bad.append("polarity does not match decision")
    if exp.get("code") is not None and exp["code"] not in CODES:
        bad.append("unknown reason code")
    for field in ("title", "rationale"):
        if not isinstance(case[field], str) or not case[field].strip():
            bad.append(f"empty {field}")
    if not case["source"] or any(s not in SOURCES for s in case["source"]):
        bad.append("bad source list")
    if evaluate(case, doc["bases"]) != exp:
        bad.append("reference reader disagrees with expected")
    bad += _link_problems(case, all_cases)
    bad += _pin_problems(case, doc)
    return bad


def _link_problems(case: Case, all_cases: list[Case]) -> list[str]:
    link = case.get("links")
    if (link is None) != (case["case_id"] not in LINKED):
        return ["a link must exist exactly on the linked cases"]
    if link is None:
        return []
    other = [c for c in all_cases if c["case_id"] == link.get("same_view_as")]
    if len(other) != 1 or other[0]["expected"] != case["expected"]:
        return ["linked case is missing or has a different view"]
    return []


def _pin_problems(case: Case, doc: dict[str, Any]) -> list[str]:
    pin = case.get("pinned")
    if (pin is None) != (case["case_id"] not in PINNED):
        return ["pin must exist exactly on the pinned cases"]
    if pin is None:
        return []
    data = _canonical(materialize(case["input"]["stored"], doc["bases"]))
    ok = pin == {"canonical_sha256": hashlib.sha256(data).hexdigest(), "canonical_byte_count": len(data)}  # fmt: skip
    return [] if ok else ["pinned digest differs from the canonical bytes"]


# ------------------------------------------------------------------ tests ----


def test_file_header_and_coverage() -> None:
    doc = _doc()
    if doc["task_id"] != "T0-08" or doc["schema"] != "a2-golden-case-file@1":
        pytest.fail("bad header")
    if _ids() != COVERAGE:
        pytest.fail(f"case ids differ from coverage list: {_ids()}")
    if set(doc["bases"]) != {"v1_full", "v1_min", "v2_min", "v2_full"}:
        pytest.fail("bases changed")
    if {c["topic"] for c in _cases()} != set(TOPICS):
        pytest.fail("not every topic is covered")
    if {c["polarity"] for c in _cases() if c["topic"] == "lossy_projection"} != {"negative"}:  # fmt: skip
        pytest.fail("lossy projection cases must be negative")
    if not {"model", "provenance"} <= set(doc):
        pytest.fail("model and provenance are required")


@pytest.mark.parametrize("case_id", _ids())
def test_case_is_sound(case_id: str) -> None:
    doc, cases = _doc(), _cases()
    problems = check_case(_case(case_id), doc, cases)
    if problems:
        pytest.fail(f"{case_id}: {problems}")


def test_v1_and_v2_field_sets_match_the_contract() -> None:
    bases = _doc()["bases"]
    if set(bases["v1_full"]) != set(V1_FIELDS) or len(V1_FIELDS) != 14:
        pytest.fail("v1 base does not have the 14 frozen fields")
    if set(bases["v2_full"]) != set(V2_FIELDS) or len(V2_FIELDS) != 19:
        pytest.fail("v2 base does not have the 19 oracle fields")
    if "filtering" in bases["v2_full"]:
        pytest.fail("a v2 record has no inline filtering")
    body = bases["v2_full"]["body"]
    if len(body) != 62 or len(bases["v2_min"]["body"]) != 20:
        pytest.fail("zone ranges assume body lengths 62 and 20")


def test_all_codes_and_both_readers_are_used() -> None:
    cases = _cases()
    used = {c["expected"].get("code") for c in cases} - {None}
    if used != set(CODES):
        pytest.fail(f"reason codes differ: {sorted(used ^ set(CODES))}")
    readers = {c["expected"].get("reader") for c in cases} - {None}
    if readers != {"v1_historical", "v2"}:
        pytest.fail(f"readers used: {readers}")
    if {c["input"]["operation"] for c in cases} != set(OPERATIONS):
        pytest.fail("not every operation is used")


def test_manifest_lists_the_file() -> None:
    lines = MANIFEST.read_text(encoding="utf-8").splitlines()
    digest = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    if f"{digest}  t0_08.json" not in lines:
        pytest.fail("MANIFEST.sha256 lacks the current digest of t0_08.json")


def test_note_names_every_case() -> None:
    text = NOTE.read_text(encoding="utf-8")
    for case_id in _ids():
        if case_id not in text:
            pytest.fail(f"{NOTE.name} does not name {case_id}")
