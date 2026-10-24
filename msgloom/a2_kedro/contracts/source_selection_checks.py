"""
Structural rules for the roots of one ``FrozenSourceSelection`` (C0-01).

The rules live here to keep ``source.py`` below the module size limit. They
read only the roots and the scope. They never read A1 bytes. A1 evidence is
checked later by ``FrozenSourceSelection.verify_against_evidence``.

Failure handling: any broken rule raises :exc:`A2ContractError`. A message
names the rule and never carries source bytes or provider identifiers.

Plan basis for the duplicate rules: the Intake workset itself rejects a
repeated ``baseline_sources`` or ``baseline_selections`` item, so a baseline
selection that repeats one is never a faithful copy. The plan allows one
``ResultRef`` under two release entries (a defensive case), so the
incremental rules never reject a repeated ``selected`` reference.
"""

from __future__ import annotations

from itertools import pairwise
from typing import TYPE_CHECKING

from msgloom.a2_kedro.contracts.codec import A2ContractError
from msgloom.preparation_pipeline.intake_models import IntakeScope
from msgloom.sources.handoff_models import ReleaseEntryRef

if TYPE_CHECKING:
    from msgloom.a2_kedro.contracts.source import FrozenRoot

PROOF_PREFIX = "intake-selection:"


def _check_indexes(roots: tuple[FrozenRoot, ...]) -> None:
    indexes = [root.workset_index for root in roots]
    if any(a >= b for a, b in pairwise(indexes)):
        raise A2ContractError("workset indexes must be unique and ascending")


def check_incremental(roots: tuple[FrozenRoot, ...], scope: IntakeScope) -> None:
    """Check ordering, scope, role and proof rules of incremental roots."""
    _check_indexes(roots)
    seen: set[tuple[ReleaseEntryRef, int]] = set()
    primaries: set[ReleaseEntryRef] = set()
    for root in roots:
        if root.role == "baseline":
            raise A2ContractError("incremental selection mixes a baseline root")
        entry, ordinal = root.entry, root.ordinal
        if entry is None or ordinal is None:
            raise A2ContractError("incremental root needs release and ordinal")
        if entry.catalog != scope.catalog:
            raise A2ContractError("root entry is outside the selection scope")
        if (entry, ordinal) in seen:
            raise A2ContractError("duplicate entry ordinal occurrence")
        seen.add((entry, ordinal))
        if root.role == "primary":
            if ordinal != 0 or entry in primaries:
                raise A2ContractError("primary role needs the only ordinal 0")
            primaries.add(entry)
        proof = root.selected.result_id.removeprefix(PROOF_PREFIX)
        if not root.selected.result_id.startswith(PROOF_PREFIX) or (
            proof != root.a1_ordinal_proof
        ):
            raise A2ContractError("ordinal proof differs from selection id")


def check_baseline(roots: tuple[FrozenRoot, ...]) -> None:
    """Check ordering, approval and uniqueness rules of baseline roots."""
    _check_indexes(roots)
    if any(root.role != "baseline" for root in roots):
        raise A2ContractError("baseline selection mixes an incremental root")
    if len({root.baseline_approval for root in roots}) != 1:
        raise A2ContractError("baseline roots need one approval")
    if len({root.baseline_source for root in roots}) != len(roots):
        raise A2ContractError("baseline source repeats at another index")
    if len({root.selected for root in roots}) != len(roots):
        raise A2ContractError("baseline selection repeats at another index")
