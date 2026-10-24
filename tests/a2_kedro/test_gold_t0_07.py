"""Validate the hand-written T0-07 crash, restart, late-write and cancel oracle.

A Claude language-model worker wrote every expected outcome in
``golden/t0_07.json`` from the A2 Kedro v2 blueprint. No human has reviewed it
yet. A small pure-Python reference checker only tests that the answers agree
with each other and with these invariants: the accepted set is a contiguous
prefix; a stale claim leaves no result; no half result exists;
replayable == frozen minus accepted; replay keeps the same result id; a
terminal workset rejects a second finalize and any later write and does not
change. The module never imports ``msgloom`` code. Mutation tests are in
``test_gold_t0_07_more.py``.
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
FIXTURE = GOLDEN / "t0_07.json"
MANIFEST = GOLDEN / "MANIFEST.sha256"
NOTE = Path(__file__).resolve().parents[2] / "docs/notes/a2-v2-golden-t0-07.md"

WRITE_OUT = ("accepted", "reused", "rejected_stale_claim", "rejected_bridge_closed")
WRITE_OUT += ("rolled_back", "rejected_already_terminal")
FINAL_OUT = ("terminal_complete", "terminal_incomplete", "rejected_stale_claim")
FINAL_OUT += ("rejected_missing_accepted", "rejected_already_terminal")
VOCAB = {"write": WRITE_OUT, "finalize": FINAL_OUT}
FLAGS = {"limited", "in_flight_at_cancel", "caller_cancelled_after_commit"}
FIELDS = {
    "claim": {"claim", "config"},
    "crash": set(),
    "cancel": set(),
    "finalize": {"claim"},
    "write": {"claim", "occ", "interrupted"} | FLAGS,
}
SNAP_KEYS = {"after_event", "active_config", "accepted", "replayable", "workset_state"}
STATES = ("pending", "terminal_complete", "terminal_incomplete")
# Pairs from blueprint section 8.2, written by hand.
SCHEDULED = [
    {"status": "CANCELLED", "code": "scheduled-cancelled"},
    {"status": "FAILED", "code": "scheduled-claim-lost"},
    {"status": "INCOMPLETE", "code": "scheduled-preparation-incomplete"},
]
POLICY = {
    "T0-07-P05": "task_goal_decision",
    "T0-07-P10": "proposed_owner_signoff_needed",
    "T0-07-N07": "proposed_owner_signoff_needed",
}
# Required case ids, in the order of the task list: crash before first accept,
# mid-batch, inside a write, before the finalizer; cancel in flight and after
# COMMIT; double restart; limited result; duplicate source; config change;
# stale claim; cancel with rollback; finalizer refusal; duplicate finalize;
# late write after terminal (stale claim N06, live claim N07).
COVERAGE = [f"T0-07-P{n:02d}" for n in range(1, 11)]
COVERAGE += [f"T0-07-N{n:02d}" for n in range(1, 8)]


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


def _ordinals(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(v, int) and not isinstance(v, bool) for v in value
    )


# ---------------------------------------------------------------- schema ----


def _event_problems(i: int, event: Any, size: int) -> list[str]:
    if not isinstance(event, dict) or event.get("op") not in FIELDS:
        return [f"event {i}: bad op"]
    op = event["op"]
    bad = [f"event {i}: unknown field {k}" for k in set(event) - FIELDS[op] - {"op"}]
    bad += [
        f"event {i}: {k} must be text"
        for k in ("claim", "config")
        if k in FIELDS[op] and not _text(event.get(k))
    ]
    if op == "write":
        occ = event.get("occ")
        if not (isinstance(occ, int) and not isinstance(occ, bool) and 0 <= occ < size):
            bad.append(f"event {i}: occ is not a frozen ordinal")
        if event.get("interrupted", "before_commit") != "before_commit":
            bad.append(f"event {i}: bad interrupted value")
        bad += [
            f"event {i}: {f} must be boolean"
            for f in FLAGS
            if not isinstance(event.get(f, False), bool)
        ]
    return bad


def _outcome_problems(i: int, op: str, out: Any) -> list[str]:
    if op not in VOCAB:
        return [f"event {i}: {op} has no outcome"] if out is not None else []
    ok = (
        isinstance(out, dict)
        and set(out) == {"outcome", "result_id"}
        and out["outcome"] in VOCAB[op]
        and (out["result_id"] is None or _text(out["result_id"]))
    )
    return [] if ok else [f"event {i}: bad outcome object"]


def _snapshot_shape(snap: Any, events: int) -> list[str]:
    if not isinstance(snap, dict) or not SNAP_KEYS <= set(snap):
        return ["snapshot lacks required fields"]
    after, accepted = snap["after_event"], snap["accepted"]
    checks = {
        "unknown fields": not set(snap) - SNAP_KEYS - {"scheduled_outcome"},
        "after_event": isinstance(after, int) and 0 <= after < events,
        "active_config": _text(snap["active_config"]),
        "accepted": isinstance(accepted, dict)
        and all(map(_ordinals, accepted.values())),
        "replayable": _ordinals(snap["replayable"]),
        "workset_state": snap["workset_state"] in STATES,
        "scheduled_outcome": snap.get("scheduled_outcome", SCHEDULED[0]) in SCHEDULED,
    }
    return [
        f"snapshot field {name} is invalid" for name, ok in checks.items() if not ok
    ]


def schema_problems(case: Any) -> list[str]:
    """Return shape problems of one case. An empty list means the shape is valid."""
    inp = case.get("input") if isinstance(case, dict) else None
    exp = case.get("expected") if isinstance(case, dict) else None
    if not isinstance(inp, dict) or not isinstance(exp, dict):
        return ["input and expected must be objects"]
    ws, timeline = inp.get("workset"), inp.get("timeline")
    occs = ws.get("occurrences") if isinstance(ws, dict) else None
    if (
        not isinstance(occs, list)
        or not occs
        or not all(
            isinstance(o, dict)
            and _text(o.get("occurrence_id"))
            and _text(o.get("source_ref"))
            for o in occs
        )
    ):
        return ["workset.occurrences needs occurrence_id and source_ref"]
    if not isinstance(timeline, list) or not timeline:
        return ["timeline must be a non-empty list"]
    bad: list[str] = []
    for i, event in enumerate(timeline):
        bad += _event_problems(i, event, len(occs))
    outs, snaps = exp.get("event_outcomes"), exp.get("snapshots")
    if not isinstance(outs, list) or len(outs) != len(timeline):
        bad.append("event_outcomes must align with the timeline")
    elif not bad:
        for i, (event, out) in enumerate(zip(timeline, outs, strict=True)):
            bad += _outcome_problems(i, event["op"], out)
    if not isinstance(snaps, list) or not snaps:
        bad.append("snapshots must be a non-empty list")
    else:
        bad += [p for snap in snaps for p in _snapshot_shape(snap, len(timeline))]
    for key in ("surviving_results", "half_accepted_results"):
        if not isinstance(exp.get(key), list):
            bad.append(f"{key} must be a list")
    return bad


# --------------------------------------------------------------- checker ----


class _Run:
    """Reference state. It only checks hand-written answers."""

    def __init__(self, size: int) -> None:
        self.size = size
        self.live: str | None = None
        self.config_of: dict[str, str] = {}
        self.done: dict[str, dict[int, tuple[str, bool]]] = {}
        self.closed = self.crashed = self.cancel_seen = self.stale_seen = False
        self.state = "pending"

    def derive(self, event: dict[str, Any]) -> str:
        """Blueprint order: live claim, bridge flag, COMMIT, accepted key."""
        done = self.done[self.config_of[event["claim"]]]
        if event["claim"] != self.live:
            self.stale_seen = self.stale_seen or self.state == "pending"
            return "rejected_stale_claim"
        if self.state != "pending":  # blueprint 4.3 steps 4 and 5
            return "rejected_already_terminal"
        if event["op"] == "finalize":
            if set(done) != set(range(self.size)):
                return "rejected_missing_accepted"
            limited = any(flag for _, flag in done.values())
            return "terminal_incomplete" if limited else "terminal_complete"
        if self.closed and not event.get("in_flight_at_cancel", False):
            return "rejected_bridge_closed"
        if event.get("interrupted") == "before_commit":
            return "rolled_back"
        return "reused" if event["occ"] in done else "accepted"


def _write_effect(run: _Run, event: dict[str, Any], out: dict[str, Any]) -> list[str]:
    done = run.done[run.config_of[event["claim"]]]
    kind, rid = out["outcome"], out["result_id"]
    if kind == "accepted":
        if event["occ"] != len(done):
            return ["accept breaks the prefix property"]
        if not rid:
            return ["accepted write has no result id"]
        done[event["occ"]] = (rid, bool(event.get("limited")))
    elif kind == "reused" and rid != done[event["occ"]][0]:
        return ["replay changed the result id"]
    elif kind not in ("accepted", "reused") and rid is not None:
        return [f"{kind} must not carry a result id"]
    if event.get("caller_cancelled_after_commit") and kind != "accepted":
        return ["cancel-after-commit needs an accepted write"]
    return []


def _step(run: _Run, event: dict[str, Any], out: dict[str, Any] | None) -> list[str]:
    op = event["op"]
    if op == "claim":
        if event["claim"] in run.config_of:
            return ["claim token reused"]
        run.live = event["claim"]
        run.config_of[event["claim"]] = event["config"]
        run.done.setdefault(event["config"], {})
        run.closed = run.crashed = run.cancel_seen = False
        return []
    if op == "crash":
        run.crashed = True
        return []
    if op == "cancel":
        run.closed = run.cancel_seen = True
        return []
    if run.crashed:
        return [f"{op} runs in a dead process"]
    if event["claim"] not in run.config_of or out is None:
        return ["unknown claim token"]
    if event.get("in_flight_at_cancel") and not run.closed:
        return ["in_flight_at_cancel before any cancel"]
    if op == "finalize" and run.state != "pending" and event["claim"] != run.live:
        return ["stale finalize after terminal: the check order is undefined"]
    derived = run.derive(event)
    if out["outcome"] != derived:
        return [f"outcome {out['outcome']} but the rules give {derived}"]
    if op == "write":
        return _write_effect(run, event, out)
    run.state = derived if derived.startswith("terminal") else run.state
    return []


def _snapshot_problems(run: _Run, snap: dict[str, Any], n: int) -> list[str]:
    """Check one snapshot by its own invariants, then against the reference."""
    acc, active = snap["accepted"], snap["active_config"]
    bad = [
        f"{c} accepted set is not a prefix"
        for c, o in acc.items()
        if o != list(range(len(o)))
    ]
    if active not in acc:
        return [*bad, "active_config has no accepted entry"]
    if snap["replayable"] != sorted(set(range(n)) - set(acc[active])):
        bad.append("replayable is not frozen minus accepted")
    if snap["workset_state"] != "pending" and snap["replayable"]:
        bad.append("terminal workset still has replayable work")
    if active != run.config_of.get(run.live or ""):
        bad.append("active_config differs from the live claim config")
    if acc != {c: sorted(d) for c, d in run.done.items()}:
        bad.append("accepted differs from the timeline result")
    if snap["workset_state"] != run.state:
        bad.append("workset_state differs from the finalizer outcomes")
    return bad + _scheduled_problems(run, snap)


def _scheduled_problems(run: _Run, snap: dict[str, Any]) -> list[str]:
    """Blueprint 8.2: the public outcome must be present exactly when it applies."""
    allowed = {
        "pending": [
            s
            for s, seen in (("CANCELLED", run.cancel_seen), ("FAILED", run.stale_seen))
            if seen
        ],
        "terminal_incomplete": ["INCOMPLETE"],
        "terminal_complete": [],
    }[snap["workset_state"]]
    status = snap.get("scheduled_outcome", {}).get("status")
    if status is None:
        return (
            [f"scheduled_outcome is missing, one of {allowed} applies"]
            if allowed
            else []
        )
    return [] if status in allowed else [f"scheduled_outcome {status} does not apply"]


def _survivor_problems(run: _Run, exp: dict[str, Any]) -> list[str]:
    keys = {"config", "occurrence", "result_id", "limited"}
    got = exp["surviving_results"]
    if not all(isinstance(r, dict) and set(r) == keys for r in got):
        return ["surviving_results entries have the wrong shape"]
    want = sorted((c, o, r, f) for c, d in run.done.items() for o, (r, f) in d.items())
    bad = []
    if (
        sorted(
            (r["config"], r["occurrence"], r["result_id"], r["limited"]) for r in got
        )
        != want
    ):
        bad.append("surviving_results differ from the accepted events")
    if len({r["result_id"] for r in got}) != len(got):
        bad.append("two occurrences share one result id")
    if exp["half_accepted_results"] != []:
        bad.append("a half accepted result is listed")
    return bad


def check_case(case: Any) -> list[str]:
    """Return all problems of one case. An empty list means it is consistent."""
    bad = schema_problems(case)
    if bad:
        return bad
    exp, timeline = case["expected"], case["input"]["timeline"]
    n = len(case["input"]["workset"]["occurrences"])
    snaps = {s["after_event"]: s for s in exp["snapshots"]}
    if len(snaps) != len(exp["snapshots"]) or len(timeline) - 1 not in snaps:
        bad.append("snapshots must be unique and include the last event")
    run = _Run(n)
    for i, (event, out) in enumerate(zip(timeline, exp["event_outcomes"], strict=True)):
        bad += [f"event {i}: {p}" for p in _step(run, event, out)]
        if i in snaps:
            bad += [f"snapshot {i}: {p}" for p in _snapshot_problems(run, snaps[i], n)]
    return bad + _survivor_problems(run, exp)


# ----------------------------------------------------------------- tests ----


def _cases() -> list[dict[str, Any]]:
    return load_strict(FIXTURE)["cases"]


def _ids() -> list[str]:
    return [case["case_id"] for case in _cases()]


def _case(case_id: str) -> dict[str, Any]:
    found = [c for c in _cases() if c["case_id"] == case_id]
    if len(found) != 1:
        pytest.fail(f"missing case {case_id}")
    return copy.deepcopy(found[0])


def test_header_coverage_and_policy_marks() -> None:
    data = load_strict(FIXTURE)
    if data["schema"] != "a2-golden-case-file@1" or data["task_id"] != "T0-07":
        pytest.fail("bad schema or task_id")
    for field in ("title", "annotator", "independence_statement", "canary"):
        if not _text(data[field]):
            pytest.fail(f"field {field} is empty")
    if not data["provenance"]["sources"]:
        pytest.fail("provenance.sources is empty")
    ids = _ids()
    if sorted(ids) != sorted(COVERAGE) or len(ids) < 8:
        pytest.fail(f"cases {ids} differ from the required coverage")
    polarity = [c["polarity"] for c in _cases()]
    if set(polarity) != {"positive", "negative"} or polarity != sorted(
        polarity, reverse=True
    ):
        pytest.fail("need positive cases first, then negative cases")
    marks = {c["case_id"]: c["policy_status"] for c in _cases() if "policy_status" in c}
    if marks != POLICY:
        pytest.fail(f"policy_status mismatch: {marks}")


def test_note_records_each_decision_case() -> None:
    text = NOTE.read_text(encoding="utf-8")
    for case_id, status in POLICY.items():
        if case_id not in text or status not in text:
            pytest.fail(f"{NOTE.name} lacks {case_id} or {status}")
    prose = [ln for ln in text.splitlines() if not ln.startswith(("|", "#"))]
    if any(len(ln) > 79 for ln in prose):
        pytest.fail(f"{NOTE.name} has a prose line longer than 79 columns")


def test_fixture_is_synthetic_and_portable() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    if "@" in re.sub(r"\w+@\d", "", text) or re.search(
        r"[A-Za-z]:\\|/home/|/tmp/", text
    ):
        pytest.fail("fixture has an email-like token or an absolute path")


def manifest_matches(manifest_text: str, name: str, data: bytes) -> bool:
    """Return True when exactly one manifest line for name holds SHA-256 of data."""
    lines = [ln for ln in manifest_text.splitlines() if ln.endswith("  " + name)]
    return lines == [f"{hashlib.sha256(data).hexdigest()}  {name}"]


def test_manifest_line_matches_file_bytes() -> None:
    text, data = MANIFEST.read_text(encoding="utf-8"), FIXTURE.read_bytes()
    if not manifest_matches(text, FIXTURE.name, data):
        pytest.fail("MANIFEST.sha256 line for t0_07.json does not match the file")
    if manifest_matches(text, FIXTURE.name, data + b"\n") or manifest_matches(
        "", FIXTURE.name, data
    ):
        pytest.fail("the manifest check accepted changed bytes or a missing line")


@pytest.mark.parametrize("case_id", _ids())
def test_case_is_valid_and_consistent(case_id: str) -> None:
    bad = check_case(_case(case_id))
    if bad:
        pytest.fail(f"{case_id}: {bad}")


# ------------------------------------------------------- negative tests ----


def test_named_violations_are_detected() -> None:
    names = {"stale": "N01", "hole": "P01", "replay": "P04", "dead": "P01"}
    names |= {"op": "P01", "field": "P01"}
    cases = {label: _case(f"T0-07-{cid}") for label, cid in names.items()}
    cases["stale"]["expected"]["event_outcomes"][5]["outcome"] = "accepted"
    cases["hole"]["input"]["timeline"][3]["occ"] = 1  # skips occurrence 0
    cases["replay"]["expected"]["event_outcomes"][6]["result_id"] = "res-new"
    cases["dead"]["input"]["timeline"].insert(
        2, {"op": "write", "claim": "claim-A", "occ": 0}
    )
    cases["dead"]["expected"]["event_outcomes"].insert(
        2, {"outcome": "accepted", "result_id": "r"}
    )
    cases["op"]["input"]["timeline"][1] = {"op": "reboot"}
    cases["field"]["input"]["timeline"][3]["surprise"] = True
    for label, case in cases.items():
        if not check_case(case):
            pytest.fail(f"{label} violation went unnoticed")
    if not any("dead process" in p for p in check_case(cases["dead"])):
        pytest.fail("the dead-process rule did not fire")


def test_loader_rejects_duplicate_keys(tmp_path: Path) -> None:
    bad = tmp_path / "dup.json"
    bad.write_text('{"a": 1, "a": 2}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON key"):
        load_strict(bad)
