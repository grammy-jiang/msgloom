"""
Gold access for the V0-05 acceptance test.

The gold files are read only. This module loads the relation cases of
``t0_02.json`` (Mail), ``t0_03.json`` (Teams) and ``t0_04.json`` (Calendar,
To Do, OneDrive, Contacts) and keeps the registry that maps a gold case to
one check function. It holds no expected value. Digests come from
``golden/MANIFEST.sha256`` through the V0-04 helpers.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from tests.a2_kedro.acceptance.v0_04_gold import (
    CANARY,
    Cmp,
    file_digest,
    load_cases,
    manifest_digests,
)

__all__ = [
    "CANARY",
    "CASES",
    "CHECKS",
    "GOLD_FILES",
    "Cmp",
    "file_digest",
    "gold",
    "manifest_digests",
    "run",
]

GOLD_FILES = ("t0_02.json", "t0_03.json", "t0_04.json")
#: Mail cases that belong to V0-04 (parsers). V0-05 checks the others.
_MAIL_RELATION_IDS = frozenset(
    {
        "T0-02-P02",
        "T0-02-P03",
        "T0-02-P04",
        "T0-02-N01",
        "T0-02-N02",
        "T0-02-N03",
        "T0-02-N05",
        "T0-02-N06",
    }
)


def _cases() -> dict[str, dict[str, Any]]:
    cases: dict[str, dict[str, Any]] = {}
    for name in GOLD_FILES:
        for case_id, case in load_cases(name).items():
            if name != "t0_02.json" or case_id in _MAIL_RELATION_IDS:
                cases[case_id] = case
    return cases


CASES = _cases()
CHECKS: dict[str, Callable[[Cmp], None]] = {}


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
