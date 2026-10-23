"""Receipt coverage rejects a terminal root that is not in the workset."""

from __future__ import annotations

import pytest

from msgloom.preparation_pipeline.intake_models import IntakeSelection
from scripts.research.c0_contract_prototype import C0ContractError, TerminalRoot
from tests.research.test_c0_contract_prototype import (
    _entry,
    fixture_workset,
    ref,
    valid_receipt,
)


def test_receipt_rejects_foreign_selected_roots_with_positive_control() -> None:
    """
    Foreign roots fail; the same receipt with workset roots passes.

    Two cases replace the first root's ``IntakeSelection``. They keep the
    root count and every other field valid, so only the coverage check
    rejects them. The third case appends a root. It changes the count, so
    the generic count check rejects it, not a foreign-root check.
    """
    workset, workset_ref = fixture_workset()
    receipt = valid_receipt(workset, workset_ref)
    receipt.validate_against(workset, workset_ref)  # Positive control.
    first = receipt.roots[0]
    known = workset.selections[0]
    catalog = workset.scope.catalog
    foreign_selections = (
        # A release entry that is not in the workset.
        IntakeSelection(
            entry=_entry(catalog, 99), result=ref("collected_selection", 99)
        ),
        # A workset entry with a saved selection that is not in the workset.
        IntakeSelection(entry=known.entry, result=ref("collected_selection", 98)),
    )
    for selection in foreign_selections:
        foreign = first.model_copy(update={"selection": selection})
        changed = receipt.model_copy(update={"roots": (foreign, *receipt.roots[1:])})
        with pytest.raises(C0ContractError, match="coverage differs"):
            changed.validate_against(workset, workset_ref)
    extra = TerminalRoot(
        selection=foreign_selections[0],
        workset_selection_index=len(receipt.roots),
        result=ref("prepared", 97, "2"),
        disposition="prepared",
        status=first.status,
    )
    appended = receipt.model_copy(update={"roots": (*receipt.roots, extra)})
    with pytest.raises(C0ContractError, match="missing/overlapping"):
        appended.validate_against(workset, workset_ref)
