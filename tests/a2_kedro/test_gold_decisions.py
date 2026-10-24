"""Check that non-A1 golden decisions carry a machine-readable marker.

The marker is the case field ``policy_status``. The expected map below is
written by hand from ``docs/notes/a2-v2-golden-decisions.md``. This module
never imports ``msgloom.a2_kedro`` and never computes an expected value.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"
DECISIONS_NOTE = (
    Path(__file__).resolve().parents[2] / "docs" / "notes" / "a2-v2-golden-decisions.md"
)
PROPOSED = "proposed_owner_signoff_needed"
TASK_GOAL = "task_goal_decision"
EXPECTED_STATUS = {
    "T0-10-P01": PROPOSED,
    "T0-10-P05": PROPOSED,
    **{f"T0-10-N{n:02d}": PROPOSED for n in range(1, 11)},
    "T0-09-N08": PROPOSED,
    "T0-08-N37": PROPOSED,
    "T0-07-P05": TASK_GOAL,
    "T0-07-P10": PROPOSED,
    "T0-04-P04": TASK_GOAL,
    "T0-04-P05": TASK_GOAL,
    "T0-04-N03": TASK_GOAL,
    "T0-02-P02": TASK_GOAL,
    "T0-02-P03": TASK_GOAL,
    "T0-02-N04": TASK_GOAL,
}


def _status_by_case() -> dict[str, Any]:
    found: dict[str, Any] = {}
    for path in sorted(GOLDEN_DIR.glob("t0_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for case in data["cases"]:
            found[case["case_id"]] = case.get("policy_status")
    return found


def test_policy_status_marks_exactly_the_decision_cases() -> None:
    found = _status_by_case()
    marked = {cid: v for cid, v in found.items() if v is not None}
    if marked != EXPECTED_STATUS:
        missing = sorted(set(EXPECTED_STATUS) - set(marked))
        extra = sorted(set(marked) - set(EXPECTED_STATUS))
        wrong = sorted(c for c in marked if marked[c] != EXPECTED_STATUS.get(c))
        pytest.fail(
            f"policy_status mismatch: missing {missing}, extra {extra}, "
            f"wrong value {wrong}"
        )


def test_decisions_note_names_every_marked_case() -> None:
    text = DECISIONS_NOTE.read_text(encoding="utf-8")
    for case_id in EXPECTED_STATUS:
        if case_id not in text:
            pytest.fail(f"{DECISIONS_NOTE.name} does not name {case_id}")
    for status in (PROPOSED, TASK_GOAL):
        if status not in text:
            pytest.fail(f"{DECISIONS_NOTE.name} does not define {status}")
    if "PROPOSED, owner sign-off needed" not in text:
        pytest.fail("decisions note lacks the PROPOSED heading text")


def test_corpus_directory_is_golden() -> None:
    # Decision 5: the manifest says gold/, the allowlist says golden/.
    if GOLDEN_DIR.name != "golden" or not GOLDEN_DIR.is_dir():
        pytest.fail("corpus directory must be tests/a2_kedro/golden")
    if "`golden/` instead of `gold/`" not in DECISIONS_NOTE.read_text("utf-8"):
        pytest.fail("decisions note lacks the golden/ versus gold/ decision")
