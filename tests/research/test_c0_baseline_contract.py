"""Prototype acceptance for explicitly approved A1 historical baselines."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from msgloom.contracts import TerminalStatus, VersionRef
from msgloom.preparation_pipeline.intake_models import (
    IntakeAnchor,
    IntakeScope,
    PreparationIntakeWorkset,
)
from msgloom.sources.handoff_models import A1CatalogIdentity
from scripts.research.c0_contract_prototype import (
    C0ContractError,
    CompletionReceipt,
    FrozenRoot,
    HeldReason,
    InputDisposition,
    TerminalRoot,
)
from tests.research.test_c0_contract_prototype import _entry, digest, ref


def test_approved_historical_baseline_is_not_fabricated_release_entry() -> None:
    catalog = A1CatalogIdentity(
        catalog_identity="c0-baseline-catalog", schema_version=1
    )
    scope = IntakeScope(
        catalog=catalog,
        source_id="synthetic-baseline-source",
        stream="contacts",
        consumer_id="c0-consumer",
    )
    original_source = VersionRef("contacts", "synthetic-contact", "saved-version-1")
    selection_ref = ref("collected_selection", 41)
    workset = PreparationIntakeWorkset(
        scope=scope,
        previous=IntakeAnchor(),
        cutoff=IntakeAnchor(),
        entries=(),
        selections=(),
        transitions=(),
        held=(),
        configuration_version="c0-config",
        code_version="c0-code",
        baseline_approval="owner-approved-c0",
        baseline_sources=(original_source,),
        baseline_selections=(selection_ref,),
    )
    root_ref = ref("preparation_intake_workset", 992)
    selected = FrozenRoot(
        selected=selection_ref,
        role="baseline",
        occurrence=0,
        baseline_source=original_source,
        baseline_approval="owner-approved-c0",
        selection_sha256=digest("historical-saved-selection"),
    )
    if selected.entry is not None or selected.a1_ordinal_proof is not None:
        pytest.fail("historical baseline fabricated an incremental release")
    completed = TerminalRoot(
        baseline_selection=selection_ref,
        baseline_source=original_source,
        workset_selection_index=0,
        result=ref("prepared", 92, "2"),
        disposition="prepared",
        status=TerminalStatus.COMPLETE,
    )
    receipt = CompletionReceipt(
        workset=root_ref,
        roots=(completed,),
        status=TerminalStatus.COMPLETE,
        policy_version="baseline-c0-v1",
    )
    receipt.validate_against(workset, root_ref)
    with pytest.raises(C0ContractError, match="coverage"):
        receipt.model_copy(
            update={
                "roots": (
                    completed.model_copy(
                        update={
                            "baseline_source": VersionRef(
                                "contacts", "synthetic-contact", "other-version"
                            )
                        }
                    ),
                )
            }
        ).validate_against(workset, root_ref)

    InputDisposition(
        selected=selection_ref,
        baseline_source=original_source,
        baseline_approval="owner-approved-c0",
        occurrence=0,
        reason=HeldReason.SOURCE_EVIDENCE_UNAVAILABLE,
        selection_sha256=digest("historical-saved-selection"),
        configuration_version="c0-config",
        code_version="c0-code",
    )
    with pytest.raises(ValidationError):
        FrozenRoot(
            selected=selection_ref,
            role="baseline",
            occurrence=0,
            selection_sha256=digest("historical-saved-selection"),
            entry=_entry(catalog, 1),
        )
    held = TerminalRoot(
        baseline_selection=selection_ref,
        baseline_source=original_source,
        workset_selection_index=0,
        result=ref("a2_input_disposition", 13),
        disposition="held",
        status=TerminalStatus.INCOMPLETE,
    )
    receipt.model_copy(
        update={"roots": (held,), "status": TerminalStatus.INCOMPLETE}
    ).validate_against(workset, root_ref)
