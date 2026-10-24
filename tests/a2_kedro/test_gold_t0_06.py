"""Validate the hand-written T0-06 coverage oracle (no missing, no overlap).

A language model annotated every expected answer in ``golden/t0_06.json``
from the A2 Kedro v2 blueprint. The small pure-Python checker below only
tests that the answers agree with these rules: each frozen item has exactly
one valid terminal (prepared@2, A2-held disposition, transition batch or
frozen intake-held entry); a receipt row must point at an accepted store
record of the right kind that covers the item; A2 never rewrites
intake-held; held or partial results allow only INCOMPLETE. The module never
imports ``msgloom``.
Every rule can be switched off by name so tests can prove a mutant dies.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pytest

GOLDEN = Path(__file__).resolve().parent / "golden"
FIXTURE = GOLDEN / "t0_06.json"
MANIFEST = GOLDEN / "MANIFEST.sha256"
NOTE = Path(__file__).resolve().parents[2] / "docs/notes/a2-v2-golden-t0-06.md"

Case = dict[str, Any]
KIND = {
    "prepared": "prepared@2",
    "a2_held": "a2_input_disposition@1",
    "transition_batch": "prepared_transitions@2",
}
TERMINAL = ("prepared", "a2_held")
ALLOWED = {
    "occurrence": TERMINAL,
    "baseline": TERMINAL,
    "transition": ("transition_batch",),
    "intake_held": ("intake_held",),
}
SCOPE_KEYS = (
    ("selections", "occurrence"),
    ("baseline_roots", "baseline"),
    ("transitions", "transition"),
    ("intake_held", "intake_held"),
)
DUPLICATE = {
    "a2_held": "duplicate_held",
    "prepared": "duplicate_prepared",
    "transition_batch": "duplicate_batch",
}
CODES = (
    "missing", "overlap", "unlisted_terminal", "duplicate_held",
    "duplicate_prepared", "duplicate_batch", "fabricated_ref", "unaccepted_ref",
    "kind_mismatch", "wrong_cover", "wrong_origin", "wrong_disposition",
    "batch_mismatch", "rewrote_intake_held", "unknown_item",
)  # fmt: skip
CEILING_RULES = (
    "ceiling_problems", "ceiling_a2_held", "ceiling_intake_held", "ceiling_status",
)  # fmt: skip
RULES = (*CODES, *CEILING_RULES)
CEILINGS = ("NOT_FINALIZABLE", "INCOMPLETE_ONLY", "COMPLETE_ALLOWED")
COVERAGE_VALUES = (*KIND, "intake_held", "missing", "overlap")
# Hand-written: the cases that must change when one rule is switched off.
RULE_CASES = {
    "missing": ("N01", "N06", "N20"),
    "overlap": ("N02",),
    "unlisted_terminal": ("N03",),
    "duplicate_held": ("N04",),
    "duplicate_prepared": ("N05",),
    "duplicate_batch": ("N18",),
    "fabricated_ref": ("N09",),
    "unaccepted_ref": ("N07", "N10"),
    "kind_mismatch": ("N11",),
    "wrong_cover": ("N12",),
    "wrong_origin": ("N13",),
    "wrong_disposition": ("N08", "N15"),
    "batch_mismatch": ("N16", "N17"),
    "rewrote_intake_held": ("N14",),
    "unknown_item": ("N19",),
    "ceiling_problems": ("N20",),
    "ceiling_a2_held": ("P03",),
    "ceiling_intake_held": ("P05", "P06"),
    "ceiling_status": ("P02",),
}
COVERAGE_IDS = [f"T0-06-P{n:02d}" for n in range(1, 12)]
COVERAGE_IDS += [f"T0-06-N{n:02d}" for n in range(1, 21)]


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    if len({key for key, _ in pairs}) != len(pairs):
        raise ValueError("duplicate JSON key")
    return dict(pairs)


def load_strict(path: Path) -> Any:
    """Load JSON and reject duplicate object keys."""
    with path.open(encoding="utf-8") as handle:
        return json.load(handle, object_pairs_hook=_no_duplicates)


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


# ---------------------------------------------------------------- schema ----


def _keys(obj: Any, want: set[str], label: str) -> list[str]:
    if not isinstance(obj, dict):
        return [f"{label} must be an object"]
    got = set(obj)
    return [f"{label} keys differ: missing {sorted(want - got)} extra {sorted(got - want)}"] * (got != want)  # fmt: skip


def _list_of(obj: Any, key: str, want: set[str], label: str) -> list[str]:
    rows = obj.get(key) if isinstance(obj, dict) else None
    if not isinstance(rows, list):
        return [f"{label}.{key} must be a list"]
    bad = [p for i, r in enumerate(rows) for p in _keys(r, want, f"{label}.{key}[{i}]")]
    if bad:
        return bad
    return [f"{label}.{key} has a non-text field" for r in rows if not all(_text(v) for k, v in r.items() if k not in ("accepted", "covers", "ref"))]  # fmt: skip


def _workset_problems(ws: Any) -> list[str]:
    bad = _keys(ws, {"workset_id", *(k for k, _ in SCOPE_KEYS)}, "workset")
    if bad:
        return bad
    shapes = {
        "selections": {"item", "role", "source_ref"},
        "baseline_roots": {"item", "source_ref"},
        "transitions": {"item", "fact_id"},
        "intake_held": {"item"},
    }
    for key, want in shapes.items():
        bad += _list_of(ws, key, want, "workset")
    if bad:
        return bad
    items = [e["item"] for key, _ in SCOPE_KEYS for e in ws[key]]
    roles = [e["role"] for e in ws["selections"]]
    bad += ["scope item ids must be unique"] * (len(set(items)) != len(items))
    bad += ["bad selection role"] * (not set(roles) <= {"primary", "component"})
    return bad + ([] if _text(ws["workset_id"]) else ["workset_id is empty"])


def _store_problems(store: Any) -> list[str]:
    if not isinstance(store, list):
        return ["store must be a list"]
    bad: list[str] = []
    for i, rec in enumerate(store):
        kind = rec.get("kind") if isinstance(rec, dict) else None
        base = {"ref", "kind", "accepted", "status", "covers"}
        bad += _keys(rec, base | ({"origin"} if kind == KIND["a2_held"] else set()), f"store[{i}]")  # fmt: skip
        if bad:
            return bad
        ok = (
            _text(rec["ref"])
            and kind in KIND.values()
            and isinstance(rec["accepted"], bool)
            and rec["status"] in ("COMPLETE", "INCOMPLETE")
            and isinstance(rec["covers"], list)
            and bool(rec["covers"])
            and all(map(_text, rec["covers"]))
            and rec.get("origin", "a2_held") in ("a2_held", "intake_held")
        )
        bad += [] if ok else [f"store[{i}] has an invalid value"]
    refs = [r.get("ref") for r in store if isinstance(r, dict)]
    return bad + ["store refs must be unique"] * (len(set(refs)) != len(refs))


def _receipt_problems(rows: Any) -> list[str]:
    if not isinstance(rows, list):
        return ["receipt must be a list"]
    bad = [p for i, r in enumerate(rows) for p in _keys(r, {"item", "disposition", "ref"}, f"receipt[{i}]")]  # fmt: skip
    if bad:
        return bad
    ok = all(
        _text(r["item"])
        and r["disposition"] in (*KIND, "intake_held")
        and (r["ref"] is None or _text(r["ref"]))
        for r in rows
    )
    return [] if ok else ["receipt has an invalid value"]


def _expected_problems(exp: Any, items: list[str]) -> list[str]:
    bad = _keys(exp, {"coverage", "problems", "ceiling"}, "expected")
    if bad:
        return bad
    cov, probs = exp["coverage"], exp["problems"]
    if not isinstance(cov, dict) or sorted(cov) != sorted(items):
        bad.append("coverage keys differ from the scope items")
    elif not set(cov.values()) <= set(COVERAGE_VALUES):
        bad.append("coverage has an unknown value")
    if not isinstance(probs, list):
        return [*bad, "problems must be a list"]
    shape = [p for i, r in enumerate(probs) for p in _keys(r, {"subject", "code"}, f"problems[{i}]")]  # fmt: skip
    if shape:
        return [*bad, *shape]
    pairs = [(p["subject"], p["code"]) for p in probs]
    bad += ["problems must be sorted and unique"] * (pairs != sorted(set(pairs)))
    bad += ["unknown problem code"] * (not {c for _, c in pairs} <= set(CODES))
    return bad + ["bad ceiling"] * (exp["ceiling"] not in CEILINGS)


def schema_problems(case: Any) -> list[str]:
    """Return shape problems of one case. An empty list means the shape is valid."""
    want = {"case_id", "polarity", "title", "rationale", "input", "expected"}
    bad = _keys(case, want, "case")
    if bad:
        return bad
    bad += [f"{k} is empty" for k in ("case_id", "title", "rationale") if not _text(case[k])]  # fmt: skip
    bad += ["bad polarity"] * (case["polarity"] not in ("positive", "negative"))
    inp = case["input"]
    bad += _keys(inp, {"workset", "store", "receipt"}, "input")
    if bad:
        return bad
    bad += _workset_problems(inp["workset"]) + _store_problems(inp["store"])
    bad += _receipt_problems(inp["receipt"])
    if bad:
        return bad
    items = [e["item"] for key, _ in SCOPE_KEYS for e in inp["workset"][key]]
    return _expected_problems(case["expected"], items)


# --------------------------------------------------------------- checker ----


def _first(checks: list[tuple[str, bool]], off: frozenset[str]) -> str | None:
    for code, bad in checks:
        if bad and code not in off:
            return code
    return None


def _row_code(
    row: Case, kind: str | None, rec: Case | None, trans: list[str], off: frozenset[str]
) -> str | None:
    """Return the first failing rule of one receipt row, or None when it is valid."""
    disp = row["disposition"]
    head = [
        ("unknown_item", kind is None),
        ("wrong_disposition", kind is not None and disp not in ALLOWED[kind]),
    ]
    code = _first(head, off)
    if code or kind == "intake_held":
        return code  # the frozen workset entry is the intake-held record
    want = trans if kind == "transition" else [row["item"]]
    off_cover = rec is not None and rec["covers"] != want
    forged = rec is not None and rec["kind"] == KIND["a2_held"]
    tail = [
        ("fabricated_ref", rec is None),
        ("unaccepted_ref", rec is not None and not rec["accepted"]),
        ("kind_mismatch", rec is not None and rec["kind"] != KIND.get(disp)),
        ("batch_mismatch", off_cover and kind == "transition"),
        ("wrong_cover", off_cover and kind != "transition"),
        ("wrong_origin", forged and rec is not None and rec["origin"] != "a2_held"),
    ]
    return _first(tail, off)


def _classify(
    item: str, kind: str, got: list[Case], store: list[Case], off: frozenset[str]
) -> tuple[str, str | None]:
    """Return the coverage label and the problem code of one scope item."""
    if not got:
        return "missing", "missing"
    listed = {r["ref"] for r in got}
    hidden = (
        kind in TERMINAL_KINDS
        and len(got) == 1
        and any(
            r["accepted"]
            and r["kind"] != KIND["transition_batch"]
            and item in r["covers"]
            and r["ref"] not in listed
            for r in store
        )
    )
    if len(got) == 1 and not hidden:
        return got[0]["disposition"], None
    seen = {r["disposition"] for r in got}
    if hidden:
        return "overlap", "unlisted_terminal"
    if len(seen) == 1:
        return "overlap", DUPLICATE.get(next(iter(seen)), "overlap")
    return "overlap", "overlap"


TERMINAL_KINDS = ("occurrence", "baseline")


def _ceiling(good: list[Case], by_ref: dict[str, Case], bad: bool, off: frozenset[str]) -> str:  # fmt: skip
    if bad and "ceiling_problems" not in off:
        return "NOT_FINALIZABLE"
    disp = {r["disposition"] for r in good}
    partial = any(
        by_ref.get(r["ref"], {}).get("status") != "COMPLETE"
        for r in good
        if r["disposition"] in ("prepared", "transition_batch")
    )
    flags = [
        ("ceiling_a2_held", "a2_held" in disp),
        ("ceiling_intake_held", "intake_held" in disp),
        ("ceiling_status", partial),
    ]
    return "INCOMPLETE_ONLY" if _first(flags, off) else "COMPLETE_ALLOWED"


def evaluate(case: Case, off: frozenset[str] = frozenset()) -> Case:
    """Derive coverage, problems and ceiling. ``off`` switches rules off."""
    ws, store, rows = case["input"]["workset"], case["input"]["store"], case["input"]["receipt"]  # fmt: skip
    kinds = {e["item"]: kind for key, kind in SCOPE_KEYS for e in ws[key]}
    trans = [e["item"] for e in ws["transitions"]]
    by_ref = {r["ref"]: r for r in store}
    problems: set[tuple[str, str]] = set()
    good: dict[str, list[Case]] = {item: [] for item in kinds}
    for row in rows:
        item = row["item"]
        code = _row_code(row, kinds.get(item), by_ref.get(row["ref"]), trans, off)
        if code:
            problems.add((item, code))
        elif item in good:
            good[item].append(row)
    for rec in store:
        for item in rec["covers"]:
            rewrote = rec["accepted"] and kinds.get(item) == "intake_held"
            if rewrote and "rewrote_intake_held" not in off:
                problems.add((item, "rewrote_intake_held"))
    coverage: dict[str, str] = {}
    for item, kind in kinds.items():
        label, code = _classify(item, kind, good[item], store, off)
        coverage[item] = label
        if code and code not in off:
            problems.add((item, code))
    flat = [r for rows_ in good.values() for r in rows_]
    return {
        "coverage": coverage,
        "problems": [{"subject": s, "code": c} for s, c in sorted(problems)],
        "ceiling": _ceiling(flat, by_ref, bool(problems), off),
    }


def check_case(case: Any) -> list[str]:
    """Return all problems of one case. An empty list means it is consistent."""
    bad = schema_problems(case)
    if bad:
        return bad
    got, want = evaluate(case), case["expected"]
    return [f"{k}: checker gives {got[k]}, fixture says {want[k]}" for k in want if got[k] != want[k]]  # fmt: skip


# ----------------------------------------------------------------- tests ----


def _cases() -> list[Case]:
    return load_strict(FIXTURE)["cases"]


def _ids() -> list[str]:
    return [case["case_id"] for case in _cases()]


def _case(case_id: str) -> Case:
    found = [c for c in _cases() if c["case_id"] == case_id]
    if len(found) != 1:
        pytest.fail(f"missing case {case_id}")
    return copy.deepcopy(found[0])


def test_header_coverage_and_no_policy_marks() -> None:
    data = load_strict(FIXTURE)
    if data["schema"] != "a2-golden-case-file@1" or data["task_id"] != "T0-06":
        pytest.fail("bad schema or task_id")
    for field in ("title", "annotator", "independence_statement"):
        if not _text(data[field]):
            pytest.fail(f"field {field} is empty")
    if not data["provenance"]["sources"] or not isinstance(data["model"], dict):
        pytest.fail("provenance.sources or model is missing")
    if sorted(_ids()) != sorted(COVERAGE_IDS):
        pytest.fail(f"cases {_ids()} differ from the required coverage")
    polarity = [c["polarity"] for c in _cases()]
    if polarity != sorted(polarity, reverse=True) or set(polarity) != {"positive", "negative"}:  # fmt: skip
        pytest.fail("need positive cases first, then negative cases")
    # Every verdict follows the blueprint text, so no case needs policy_status.
    if any("policy_status" in c for c in _cases()):
        pytest.fail("T0-06 has no decision case; policy_status must be absent")


def test_note_exists_and_prose_is_short() -> None:
    text = NOTE.read_text(encoding="utf-8")
    for needle in ("T0-06-P11", "COMPLETE_ALLOWED", "Modeling limits"):
        if needle not in text:
            pytest.fail(f"{NOTE.name} lacks {needle}")
    prose = [ln for ln in text.splitlines() if not ln.startswith(("|", "#"))]
    if any(len(ln) > 79 for ln in prose):
        pytest.fail(f"{NOTE.name} has a prose line longer than 79 columns")


def test_fixture_is_synthetic_and_portable() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    if "@" in re.sub(r"\w+@\d", "", text) or re.search(r"[A-Za-z]:\\|/home/|/tmp/", text):  # fmt: skip
        pytest.fail("fixture has an email-like token or an absolute path")


def manifest_matches(manifest_text: str, name: str, data: bytes) -> bool:
    """Return True when exactly one manifest line for name holds SHA-256 of data."""
    lines = [ln for ln in manifest_text.splitlines() if ln.endswith("  " + name)]
    return lines == [f"{hashlib.sha256(data).hexdigest()}  {name}"]


def test_manifest_line_matches_file_bytes() -> None:
    text, data = MANIFEST.read_text(encoding="utf-8"), FIXTURE.read_bytes()
    if not manifest_matches(text, FIXTURE.name, data):
        pytest.fail("MANIFEST.sha256 line for t0_06.json does not match the file")
    if manifest_matches(text, FIXTURE.name, data + b"\n") or manifest_matches("", FIXTURE.name, data):  # fmt: skip
        pytest.fail("the manifest check accepted changed bytes or a missing line")


@pytest.mark.parametrize("case_id", _ids())
def test_case_is_valid_and_consistent(case_id: str) -> None:
    bad = check_case(_case(case_id))
    if bad:
        pytest.fail(f"{case_id}: {bad}")


def test_loader_rejects_duplicate_keys(tmp_path: Path) -> None:
    bad = tmp_path / "dup.json"
    bad.write_text('{"a": 1, "a": 2}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON key"):
        load_strict(bad)
