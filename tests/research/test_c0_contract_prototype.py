"""C0 strict prototype contract acceptance; no production A2 mutation."""

from __future__ import annotations

from hashlib import sha256

import pytest
from pydantic import ValidationError

from msgloom.contracts import ResultRef, TerminalStatus
from msgloom.preparation_pipeline.intake_models import (
    HeldIntakeEntry,
    IntakeAnchor,
    IntakeScope,
    IntakeSelection,
    IntakeTransition,
    PreparationIntakeWorkset,
)
from msgloom.sources.handoff_models import A1CatalogIdentity, ReleaseEntryRef
from scripts.research.c0_contract_prototype import (
    AcceptedPayload,
    C0ContractError,
    CompletionReceipt,
    FrozenRoot,
    HeldReason,
    InputDisposition,
    StageIdentity,
    TerminalRoot,
    TransitionBatch,
    append_or_verify,
    receipt_digest,
)


def digest(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def ref(kind: str, number: int, version: str = "1") -> ResultRef:
    return ResultRef(f"c0-result-{number}:{kind}@{version}", kind, version)


def _entry(catalog: A1CatalogIdentity, seq: int) -> ReleaseEntryRef:
    return ReleaseEntryRef(
        catalog=catalog, release_entry_seq=seq, entry_digest=digest(f"entry-{seq}")
    )


def fixture_workset(
    *,
    selections_per_entry: int = 1,
    include_transition: bool = False,
    held_only: bool = False,
) -> tuple[PreparationIntakeWorkset, ResultRef]:
    catalog = A1CatalogIdentity(
        catalog_identity="synthetic-a1-catalog", schema_version=1
    )
    scope = IntakeScope(
        catalog=catalog,
        source_id="synthetic-source",
        stream="outlook_mail",
        consumer_id="c0-consumer",
    )
    entries = (
        (_entry(catalog, 3), _entry(catalog, 7))
        if not held_only
        else (_entry(catalog, 3),)
    )
    selections = (
        tuple(
            IntakeSelection(entry=entry, result=ref("collected_selection", i * 3 + j))
            for i, entry in enumerate(entries)
            for j in range(selections_per_entry)
        )
        if not held_only
        else ()
    )
    transitions = (
        (
            IntakeTransition(
                entry=entries[-1],
                fact_id=digest("scoped-fact"),
                transition_kind="membership_removal",
                resource_kind="message",
                resource_identity="synthetic-scope-message",
                scope_kind="mail_folder",
                scope_identity="synthetic-folder",
            ),
        )
        if include_transition
        else ()
    )
    held = (
        (HeldIntakeEntry(entry=entries[0], reason="byte_limit"),) if held_only else ()
    )
    workset = PreparationIntakeWorkset(
        scope=scope,
        previous=IntakeAnchor(),
        cutoff=IntakeAnchor(
            last_release_entry_seq=entries[-1].release_entry_seq,
            last_release_entry_digest=entries[-1].entry_digest,
        ),
        entries=entries,
        selections=selections,
        transitions=transitions,
        held=held,
        configuration_version="c0-config-v1",
        code_version="c0-code-v1",
    )
    return workset, ref("preparation_intake_workset", 990)


def valid_roots(workset: PreparationIntakeWorkset) -> tuple[TerminalRoot, ...]:
    return tuple(
        TerminalRoot(
            selection=selection,
            workset_selection_index=index,
            result=ref("prepared", index, "2"),
            disposition="prepared",
            status=TerminalStatus.COMPLETE,
        )
        for index, selection in enumerate(workset.selections)
    )


def valid_receipt(
    workset: PreparationIntakeWorkset,
    workset_ref: ResultRef,
    *,
    status: TerminalStatus = TerminalStatus.COMPLETE,
) -> CompletionReceipt:
    batch = (
        TransitionBatch(
            transitions=workset.transitions,
            result=ref("prepared_transitions", 1, "2"),
            status=TerminalStatus.COMPLETE,
        )
        if workset.transitions
        else None
    )
    return CompletionReceipt(
        workset=workset_ref,
        roots=valid_roots(workset),
        transition_batch=batch,
        status=status,
        policy_version="c0-policy-v1",
    )


def test_acceptance_key_is_input_only_and_binds_role_entry_order_and_versions() -> None:
    workset, workset_ref = fixture_workset()
    original = FrozenRoot(
        entry=workset.selections[0].entry,
        selected=workset.selections[0].result,
        occurrence=0,
        role="primary",
        selection_sha256=digest("canonical-exact-selection"),
        a1_ordinal_proof=digest("a1-intake-identity-revalidated"),
    )

    def key_for(*, root=original, config="c0-config-v1", index=0) -> StageIdentity:
        return StageIdentity(
            scope_key=digest(workset.scope.claim_key()),
            workset=workset_ref,
            partition_ordinal=index,
            selected=(root,),
            stage_kind="prepared",
            schema_version="2",
            upstream=(ref("parsed", 1),),
            configuration_version=config,
            code_version="c0-code-v1",
            parser_version="c0-parser-v1",
            rule_version="c0-filter-v1",
            partition_policy_version="c0-partition-v1",
        )

    base = key_for()
    if base.logical_acceptance_key() != key_for().logical_acceptance_key():
        pytest.fail("Expected C0 test condition at line 178")
    if (
        base.logical_acceptance_key()
        == key_for(
            root=original.model_copy(update={"role": "component"})
        ).logical_acceptance_key()
    ):
        pytest.fail("Expected C0 test condition at line 179")
    if (
        base.logical_acceptance_key()
        == key_for(
            root=original.model_copy(update={"entry": workset.selections[1].entry})
        ).logical_acceptance_key()
    ):
        pytest.fail("Expected C0 test condition at line 185")
    if base.logical_acceptance_key() == key_for(index=1).logical_acceptance_key():
        pytest.fail("Expected C0 test condition at line 191")
    if (
        base.logical_acceptance_key()
        == key_for(config="c0-config-v2").logical_acceptance_key()
    ):
        pytest.fail("Expected C0 test condition at line 192")
    if not (base.logical_acceptance_key().startswith("a2-accepted:")):
        pytest.fail("Expected C0 test condition at line 196")

    with pytest.raises(ValidationError):
        StageIdentity.model_validate(
            {**base.model_dump(), "attempt": "not-allowed"}, strict=True
        )
    with pytest.raises(ValidationError):
        StageIdentity.model_validate(
            {**base.model_dump(), "output_digest": digest("bytes")}, strict=True
        )


def test_accepted_output_digest_is_not_identity_and_conflicting_bytes_fail_closed() -> (
    None
):
    workset, workset_ref = fixture_workset()
    root = FrozenRoot(
        entry=workset.selections[0].entry,
        selected=workset.selections[0].result,
        occurrence=0,
        role="primary",
        selection_sha256=digest("frozen-source"),
        a1_ordinal_proof=digest("ordinal-proof"),
    )
    id_ = StageIdentity(
        scope_key=digest(workset.scope.claim_key()),
        workset=workset_ref,
        partition_ordinal=0,
        selected=(root,),
        stage_kind="prepared",
        schema_version="2",
        upstream=(),
        configuration_version="a",
        code_version="b",
        parser_version="c",
        rule_version="d",
        partition_policy_version="e",
    )
    key = id_.logical_acceptance_key()
    accepted = AcceptedPayload(
        logical_key=key,
        output=ref("prepared", 11, "2"),
        canonical_sha256=digest("accepted-first-output"),
        canonical_byte_count=23,
    )
    if append_or_verify(None, accepted) != accepted:
        pytest.fail("Expected C0 test condition at line 241")
    if append_or_verify(accepted, accepted) != accepted:
        pytest.fail("Expected C0 test condition at line 242")
    with pytest.raises(C0ContractError, match="integrity-conflict"):
        append_or_verify(
            accepted,
            accepted.model_copy(
                update={"canonical_sha256": digest("different-output")}
            ),
        )
    with pytest.raises(C0ContractError, match="integrity-conflict"):
        append_or_verify(
            accepted,
            accepted.model_copy(update={"output": ref("prepared", 12, "2")}),
        )


def test_completion_receipt_exact_multiple_release_occurrences() -> None:
    workset, workset_ref = fixture_workset(
        selections_per_entry=2, include_transition=True
    )
    if [x.entry.release_entry_seq for x in workset.selections] != [3, 3, 7, 7]:
        pytest.fail("Expected C0 test condition at line 261")
    if workset.selection_refs == ():
        pytest.fail("Expected C0 test condition at line 262")
    receipt = valid_receipt(workset, workset_ref)
    receipt.validate_against(workset, workset_ref)
    if receipt_digest(receipt) != receipt_digest(receipt):
        pytest.fail("Expected C0 test condition at line 265")

    with pytest.raises(C0ContractError, match="missing/overlapping"):
        receipt.model_copy(update={"roots": receipt.roots[:-1]}).validate_against(
            workset, workset_ref
        )
    with pytest.raises(C0ContractError, match="coverage"):
        receipt.model_copy(
            update={"roots": tuple(reversed(receipt.roots))}
        ).validate_against(workset, workset_ref)
    with pytest.raises(C0ContractError, match="different immutable workset"):
        receipt.validate_against(workset, ref("preparation_intake_workset", 991))
    with pytest.raises(C0ContractError, match="transition"):
        receipt.model_copy(update={"transition_batch": None}).validate_against(
            workset, workset_ref
        )
    with pytest.raises(C0ContractError, match="result covers"):
        duplicated = receipt.roots[1].model_copy(
            update={"result": receipt.roots[0].result}
        )
        receipt.model_copy(
            update={"roots": (receipt.roots[0], duplicated, *receipt.roots[2:])}
        ).validate_against(workset, workset_ref)


def test_a2_held_is_explicit_and_never_claims_complete() -> None:
    workset, workset_ref = fixture_workset()
    outcome = valid_roots(workset)[0]
    a2_held = TerminalRoot(
        selection=outcome.selection,
        workset_selection_index=0,
        result=ref("a2_input_disposition", 1),
        disposition="held",
        status=TerminalStatus.INCOMPLETE,
    )
    receipt = valid_receipt(workset, workset_ref).model_copy(
        update={
            "roots": (a2_held, valid_roots(workset)[1]),
            "status": TerminalStatus.INCOMPLETE,
        }
    )
    receipt.validate_against(workset, workset_ref)
    with pytest.raises(C0ContractError, match="status"):
        receipt.model_copy(update={"status": TerminalStatus.COMPLETE}).validate_against(
            workset, workset_ref
        )
    InputDisposition(
        selected=outcome.selection.result,
        entry=outcome.selection.entry,
        occurrence=0,
        reason=HeldReason.ROLE_UNVERIFIABLE,
        selection_sha256=digest("saved-original-selection"),
        configuration_version="v1",
        code_version="v1",
    )
    with pytest.raises(ValidationError):
        TerminalRoot(
            selection=outcome.selection,
            workset_selection_index=0,
            result=ref("prepared", 1, "2"),
            disposition="held",
            status=TerminalStatus.INCOMPLETE,
        )


def test_intake_held_only_needs_incomplete_receipt_without_fake_prepared() -> None:
    workset, workset_ref = fixture_workset(held_only=True)
    if workset.selections:
        pytest.fail("Expected C0 test condition at line 332")
    receipt = valid_receipt(workset, workset_ref, status=TerminalStatus.INCOMPLETE)
    receipt.validate_against(workset, workset_ref)
    with pytest.raises(C0ContractError, match="status"):
        valid_receipt(workset, workset_ref).validate_against(workset, workset_ref)


def test_transitions_have_one_exact_scoped_batch_not_fabricated_message() -> None:
    workset, workset_ref = fixture_workset(include_transition=True)
    receipt = valid_receipt(workset, workset_ref)
    receipt.validate_against(workset, workset_ref)
    changed = receipt.transition_batch.model_copy(update={"transitions": ()})
    with pytest.raises(C0ContractError, match="altered scoped"):
        receipt.model_copy(update={"transition_batch": changed}).validate_against(
            workset, workset_ref
        )


def test_stage_key_cannot_confuse_transition_and_selected_message() -> None:
    workset, workset_ref = fixture_workset(include_transition=True)
    scope_key = digest(workset.scope.claim_key())
    transition_key = StageIdentity(
        scope_key=scope_key,
        workset=workset_ref,
        partition_ordinal=0,
        transition=workset.transitions[0],
        stage_kind="prepared_transitions",
        schema_version="2",
        configuration_version="v1",
        code_version="v1",
        parser_version="not-required",
        rule_version="v1",
        partition_policy_version="v1",
    )
    if not (transition_key.logical_acceptance_key()):
        pytest.fail("Expected C0 test condition at line 366")
    with pytest.raises(ValidationError):
        transition_key.model_copy(update={"transition": None}).model_validate(
            transition_key.model_dump()
        )


def test_pydantic_frozen_strict_schema_and_roundtrip() -> None:
    workset, workset_ref = fixture_workset(selections_per_entry=2)
    receipt = valid_receipt(workset, workset_ref)
    restored = CompletionReceipt.model_validate_json(
        receipt.model_dump_json(), strict=True
    )
    if restored != receipt:
        pytest.fail("Expected C0 test condition at line 379")
    restored.validate_against(workset, workset_ref)

    with pytest.raises(ValidationError):
        CompletionReceipt.model_validate(
            {**receipt.model_dump(), "extra": "forbidden"}, strict=True
        )
    with pytest.raises(ValidationError):
        CompletionReceipt.model_validate(
            {**receipt.model_dump(), "policy_version": ""}, strict=True
        )
