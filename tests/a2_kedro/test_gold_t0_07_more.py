"""Mutation tests for the T0-07 crash, restart, late-write and cancel oracle.

Every outcome, every snapshot and several timeline inputs of every case are
changed one at a time. The checker must report each change. Extra tests pin
the terminal-workset rules (duplicate finalize, late write) and the public
scheduled outcome rule of blueprint 8.2. The checker lives in
``test_gold_t0_07.py``. This module never imports ``msgloom`` code.
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from test_gold_t0_07 import SCHEDULED, STATES, VOCAB, _case, _ids, check_case

Case = dict[str, Any]


def _outcome_mutants(case: Case) -> Iterator[tuple[str, Case]]:
    timeline = case["input"]["timeline"]
    for i, out in enumerate(case["expected"]["event_outcomes"]):
        if out is None:
            continue
        for other in VOCAB[timeline[i]["op"]]:
            if other != out["outcome"]:
                mutant = copy.deepcopy(case)
                mutant["expected"]["event_outcomes"][i]["outcome"] = other
                yield f"event {i} -> {other}", mutant


def _snapshot_mutants(case: Case) -> Iterator[tuple[str, Case]]:
    """Change every field of every snapshot, not only the last one."""
    for k, snap in enumerate(case["expected"]["snapshots"]):
        edits: dict[str, Any] = {
            "replayable": [*snap["replayable"], 9],
            "workset_state": "x",
            "accepted": {snap["active_config"]: [0, 7]},
            "active_config": "cfg-other",
        }
        edits |= {f"state {s}": s for s in STATES if s != snap["workset_state"]}
        for label, value in edits.items():
            mutant = copy.deepcopy(case)
            target = mutant["expected"]["snapshots"][k]
            target["workset_state" if label.startswith("state ") else label] = value
            yield f"snapshot {k} {label}", mutant


def _scheduled_mutants(case: Case) -> Iterator[tuple[str, Case]]:
    """Drop, swap or add scheduled_outcome on every snapshot."""
    for k, snap in enumerate(case["expected"]["snapshots"]):
        have = snap.get("scheduled_outcome")
        if have is not None:
            mutant = copy.deepcopy(case)
            del mutant["expected"]["snapshots"][k]["scheduled_outcome"]
            yield f"snapshot {k} drops scheduled_outcome", mutant
        for other in SCHEDULED:
            if other != have:
                mutant = copy.deepcopy(case)
                mutant["expected"]["snapshots"][k]["scheduled_outcome"] = other
                yield f"snapshot {k} scheduled_outcome {other['status']}", mutant


def _timeline_mutants(case: Case) -> Iterator[tuple[str, Case]]:
    """Change the input of writes whose effect the answers depend on."""
    size = len(case["input"]["workset"]["occurrences"])
    outs = case["expected"]["event_outcomes"]
    for i, event in enumerate(case["input"]["timeline"]):
        if event["op"] != "write" or outs[i]["outcome"] not in ("accepted", "reused"):
            continue
        edits: dict[str, Callable[[dict[str, Any]], None]] = {
            "shifts occ": lambda e: e.update(occ=(e["occ"] + 1) % size),
            "unknown claim": lambda e: e.update(claim="claim-ZZ"),
        }
        if outs[i]["outcome"] == "accepted":
            edits["toggles limited"] = lambda e: e.update(
                limited=not e.get("limited", False)
            )
        for label, edit in edits.items():
            mutant = copy.deepcopy(case)
            edit(mutant["input"]["timeline"][i])
            yield f"timeline {i} {label}", mutant


def _result_mutants(case: Case) -> Iterator[tuple[str, Case]]:
    extra = {"config": "cfg-1", "occurrence": 0, "result_id": "res-late"}
    extra["limited"] = False
    for label, edit in {
        "extra survivor": lambda r: r.append(extra),
        "dropped survivor": lambda r: r.pop(),
        "changed id": lambda r: r[0].update(result_id="res-other"),
    }.items():
        mutant = copy.deepcopy(case)
        edit(mutant["expected"]["surviving_results"])
        yield label, mutant
    mutant = copy.deepcopy(case)
    mutant["expected"]["half_accepted_results"] = [{"occurrence": 0}]
    yield "half result listed", mutant


def _mutants(case: Case) -> Iterator[tuple[str, Case]]:
    yield from _outcome_mutants(case)
    yield from _snapshot_mutants(case)
    yield from _scheduled_mutants(case)
    yield from _timeline_mutants(case)
    yield from _result_mutants(case)


@pytest.mark.parametrize("case_id", _ids())
def test_every_mutation_is_detected(case_id: str) -> None:
    count = 0
    for label, mutant in _mutants(_case(case_id)):
        count += 1
        if not check_case(mutant):
            pytest.fail(f"{case_id}: mutation {label!r} went unnoticed")
    if count < 20:
        pytest.fail(f"{case_id}: only {count} mutations were tried")


def _problems(case_id: str, edit: Callable[[Case], None]) -> str:
    case = _case(case_id)
    edit(case)
    return "; ".join(check_case(case))


def _set_outcome(
    index: int, outcome: str, rid: str | None = None
) -> Callable[[Case], None]:
    def edit(case: Case) -> None:
        case["expected"]["event_outcomes"][index] = {
            "outcome": outcome,
            "result_id": rid,
        }

    return edit


def test_terminal_rules_fire() -> None:
    """A second finalize and any later write must name the terminal rule."""
    want = "the rules give rejected_already_terminal"
    tries = {
        "duplicate finalize accepted": ("N04", _set_outcome(5, "terminal_complete")),
        "restarted finalize accepted": ("N04", _set_outcome(8, "terminal_complete")),
        "duplicate finalize on INCOMPLETE": (
            "N05",
            _set_outcome(4, "terminal_complete"),
        ),
        "late live write reused": ("N07", _set_outcome(4, "reused", "res-cfg1-1")),
    }
    for label, (cid, edit) in tries.items():
        if want not in _problems(f"T0-07-{cid}", edit):
            pytest.fail(f"{label}: the terminal rule did not fire")
    stale = _problems("T0-07-N06", _set_outcome(9, "rejected_already_terminal"))
    if "the rules give rejected_stale_claim" not in stale:
        pytest.fail("a stale late write must give rejected_stale_claim")
    late = _problems("T0-07-N06", _set_outcome(9, "accepted", "res-late"))
    if "the rules give rejected_stale_claim" not in late:
        pytest.fail("a stale late write must not be accepted")


def test_stale_finalize_after_terminal_is_not_a_valid_timeline() -> None:
    """Blueprint 4.3 does not order the claim check and the terminal check."""

    def edit(case: Case) -> None:
        case["input"]["timeline"].append({"op": "finalize", "claim": "claim-A"})
        case["expected"]["event_outcomes"].append(
            {"outcome": "rejected_stale_claim", "result_id": None}
        )
        last = copy.deepcopy(case["expected"]["snapshots"][-1])
        last["after_event"] += 1
        case["expected"]["snapshots"].append(last)

    if "check order is undefined" not in _problems("T0-07-N06", edit):
        pytest.fail("a stale finalize on a terminal workset was accepted as input")


def test_terminal_snapshot_does_not_change_after_late_operations() -> None:
    for cid, first in (("N04", 0), ("N05", 0), ("N06", 0), ("N07", 0)):
        snaps = _case(f"T0-07-{cid}")["expected"]["snapshots"]
        base = {k: v for k, v in snaps[first].items() if k != "after_event"}
        for later in snaps[first + 1 :]:
            if {k: v for k, v in later.items() if k != "after_event"} != base:
                pytest.fail(f"T0-07-{cid}: a late operation changed the snapshot")


def test_scheduled_outcome_is_required_after_cancel_or_stale_claim() -> None:
    for cid, status in (("P05", "CANCELLED"), ("P06", "CANCELLED"), ("N01", "FAILED")):
        case = _case(f"T0-07-{cid}")
        first = case["expected"]["snapshots"][0]
        if first.get("scheduled_outcome", {}).get("status") != status:
            pytest.fail(f"T0-07-{cid}: first snapshot lacks {status}")
        del first["scheduled_outcome"]
        if not any("scheduled_outcome is missing" in p for p in check_case(case)):
            pytest.fail(f"T0-07-{cid}: a missing scheduled_outcome went unnoticed")
    for cid in ("P08", "N05"):
        case = _case(f"T0-07-{cid}")
        del case["expected"]["snapshots"][-1]["scheduled_outcome"]
        if not any("scheduled_outcome is missing" in p for p in check_case(case)):
            pytest.fail(f"T0-07-{cid}: INCOMPLETE without scheduled_outcome passed")
