"""C0 strict prototype contract acceptance; no production A2 mutation."""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

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


def expect(condition: bool, message: str) -> None:
    """Fail with a description of the violated expectation."""
    if not condition:
        pytest.fail(message)


def decode_errors(model: type[BaseModel], payload: object) -> list[str]:
    """Decode JSON-mode ``payload`` strictly; return ``loc: message`` errors.

    JSON decoding avoids a strict dataclass-versus-dict mismatch that would
    mask the predicate under test. An empty list means it was accepted.
    """
    try:
        model.model_validate_json(json.dumps(payload), strict=True)
    except ValidationError as error:
        return [
            ".".join(str(part) for part in item["loc"]) + ": " + item["msg"]
            for item in error.errors()
        ]
    return []


def expect_one_error(model: type[BaseModel], payload: object, fragment: str) -> None:
    """Require exactly one decode error that contains ``fragment``."""
    errors = decode_errors(model, payload)
    expect(
        len(errors) == 1 and fragment in errors[0],
        f"expected one error containing {fragment!r}, got {errors}",
    )


def strict_json[ModelT: BaseModel](model: type[ModelT], payload: object) -> ModelT:
    """Validate a JSON-mode payload, as stored data would be decoded."""
    return model.model_validate_json(json.dumps(payload), strict=True)


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


def frozen_root(workset: PreparationIntakeWorkset) -> FrozenRoot:
    selection = workset.selections[0]
    return FrozenRoot(
        entry=selection.entry,
        selected=selection.result,
        occurrence=0,
        role="primary",
        selection_sha256=digest("canonical-exact-selection"),
        a1_ordinal_proof=digest("a1-intake-identity-revalidated"),
    )


def stage_identity(
    workset: PreparationIntakeWorkset, workset_ref: ResultRef, **changes: Any
) -> StageIdentity:
    """Build a valid prepared@2 message-stage identity with ``changes``."""
    fields = {
        "scope_key": digest(workset.scope.claim_key()),
        "workset": workset_ref,
        "partition_ordinal": 0,
        "selected": (frozen_root(workset),),
        "stage_kind": "prepared",
        "schema_version": "2",
        "upstream": (ref("parsed", 1),),
        "configuration_version": "c0-config-v1",
        "code_version": "c0-code-v1",
        "parser_version": "c0-parser-v1",
        "rule_version": "c0-filter-v1",
        "partition_policy_version": "c0-partition-v1",
    }
    return StageIdentity.model_validate(fields | changes)


def transition_identity(
    workset: PreparationIntakeWorkset, workset_ref: ResultRef, **changes: Any
) -> StageIdentity:
    """Build a valid prepared_transitions@2 identity with ``changes``."""
    defaults = {
        "selected": (),
        "transitions": workset.transitions,
        "stage_kind": "prepared_transitions",
        "upstream": (),
    }
    return stage_identity(workset, workset_ref, **defaults | changes)


def test_acceptance_key_is_input_only_and_binds_role_entry_order_and_versions() -> None:
    workset, workset_ref = fixture_workset()
    original = frozen_root(workset)

    def key_for(*, root=original, config="c0-config-v1", index=0) -> str:
        return stage_identity(
            workset,
            workset_ref,
            selected=(root,),
            configuration_version=config,
            partition_ordinal=index,
        ).logical_acceptance_key()

    base = key_for()
    expect(base == key_for(), "same input parts must give the same key")
    expect(base.startswith("a2-accepted:"), "acceptance key lost its tag")
    other_entry = workset.selections[1].entry
    for name, other in {
        "role": key_for(root=original.model_copy(update={"role": "component"})),
        "release entry": key_for(
            root=original.model_copy(update={"entry": other_entry})
        ),
        "partition ordinal": key_for(index=1),
        "configuration version": key_for(config="c0-config-v2"),
    }.items():
        expect(base != other, f"acceptance key does not bind the {name}")


def test_stage_identity_decodes_from_json_and_forbids_attempt_and_output() -> None:
    workset, workset_ref = fixture_workset()
    identity = stage_identity(workset, workset_ref)
    payload = identity.model_dump(mode="json")
    # Positive control: only the extra field can fail below.
    expect(strict_json(StageIdentity, payload) == identity, "JSON round trip failed")
    for name in ("attempt", "output_digest"):
        expect_one_error(StageIdentity, payload | {name: "x"}, f"{name}: Extra inputs")


def test_stage_identity_selected_roots_xor_transition_batch() -> None:
    workset, workset_ref = fixture_workset(include_transition=True)
    message_json = stage_identity(workset, workset_ref).model_dump(mode="json")
    batch_json = transition_identity(workset, workset_ref).model_dump(mode="json")
    for valid in (message_json, batch_json):  # Positive controls decode unchanged.
        errors = decode_errors(StageIdentity, valid)
        expect(errors == [], f"valid {valid['stage_kind']} identity rejected: {errors}")
    roots = message_json["selected"]
    # Each case breaks exactly one predicate and keeps every other field valid.
    for payload, fragment in (
        (batch_json | {"transitions": []}, "selected roots XOR"),
        (batch_json | {"selected": roots}, "selected roots XOR"),
        (message_json | {"stage_kind": "prepared_transitions"}, "exact transition"),
        (batch_json | {"stage_kind": "prepared"}, "cannot become a message"),
    ):
        expect_one_error(StageIdentity, payload, fragment)


def test_stage_identity_kind_and_schema_version_pairing_is_closed() -> None:
    workset, workset_ref = fixture_workset()
    identity = stage_identity(workset, workset_ref)
    payload = identity.model_dump(mode="json")
    expect(decode_errors(StageIdentity, payload) == [], "prepared@2 must be allowed")
    for kind, version in (("prepared", "1"), ("zones", "2")):
        changed = payload | {"stage_kind": kind, "schema_version": version}
        expect_one_error(StageIdentity, changed, "pairing is not approved")
    blank = payload | {"configuration_version": " "}
    expect_one_error(StageIdentity, blank, "empty frozen stage version")


def test_accepted_output_digest_is_not_identity_and_conflicting_bytes_fail_closed() -> (
    None
):
    workset, workset_ref = fixture_workset()
    identity = stage_identity(workset, workset_ref)
    accepted = AcceptedPayload(
        logical_key=identity.logical_acceptance_key(),
        output=ref("prepared", 11, "2"),
        canonical_sha256=digest("accepted-first-output"),
        canonical_byte_count=23,
    )
    expect(append_or_verify(None, accepted) == accepted, "first output not accepted")
    expect(append_or_verify(accepted, accepted) == accepted, "replay not idempotent")
    for update in (
        {"canonical_sha256": digest("different-output")},
        {"output": ref("prepared", 12, "2")},
    ):  # Same logical key, different output digest or substituted result ref.
        with pytest.raises(C0ContractError, match="integrity-conflict"):
            append_or_verify(accepted, accepted.model_copy(update=update))
    payload = accepted.model_dump(mode="json")
    expect(decode_errors(AcceptedPayload, payload) == [], "valid payload rejected")
    bad_key = {"logical_key": "a2-accepted:" + "z" * 64}
    expect_one_error(AcceptedPayload, payload | bad_key, "should match pattern")


def test_completion_receipt_exact_multiple_release_occurrences() -> None:
    workset, workset_ref = fixture_workset(
        selections_per_entry=2, include_transition=True
    )
    sequences = [x.entry.release_entry_seq for x in workset.selections]
    expect(sequences == [3, 3, 7, 7], f"unexpected release occurrences {sequences}")
    expect(len(workset.selection_refs) == 4, "distinct refs must stay distinct")
    receipt = valid_receipt(workset, workset_ref)
    receipt.validate_against(workset, workset_ref)
    expect(receipt_digest(receipt) == receipt_digest(receipt), "digest unstable")

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
    duplicated = receipt.roots[1].model_copy(update={"result": receipt.roots[0].result})
    with pytest.raises(C0ContractError, match="result covers"):
        receipt.model_copy(
            update={"roots": (receipt.roots[0], duplicated, *receipt.roots[2:])}
        ).validate_against(workset, workset_ref)


def test_duplicate_saved_selection_ref_never_collapses_intake_occurrences() -> None:
    """Two entries sharing one ``ResultRef`` still need two terminal results.

    This is a purely defensive case. Real A1 hashes the exact
    ``ReleaseEntryRef`` into every ``intake-selection:`` result ID, so honest
    acquisition cannot produce one ``ResultRef`` at two entries. The Workset
    validator only rejects a repeated ``(entry, result)`` pair, and the
    receipt must not rely on the deduplicated ``selection_refs`` for coverage.
    """
    original, workset_ref = fixture_workset()
    first, second = original.selections
    duplicated = second.model_copy(update={"result": first.result})
    payload = original.model_dump(mode="json") | {
        "selections": [
            first.model_dump(mode="json"),
            duplicated.model_dump(mode="json"),
        ]
    }
    workset = strict_json(PreparationIntakeWorkset, payload)
    expect(
        first.entry != duplicated.entry and first.result == duplicated.result,
        "fixture must repeat one ResultRef at two distinct ReleaseEntry occurrences",
    )
    expect(len(workset.selections) == 2, "both occurrences must stay in the workset")
    expect(workset.selection_refs == (first.result,), "selection_refs must deduplicate")
    receipt = valid_receipt(workset, workset_ref)
    expect(
        len({root.result for root in receipt.roots}) == 2,
        "receipt must carry two distinct results, one per occurrence",
    )
    receipt.validate_against(workset, workset_ref)
    for kept in (receipt.roots[:1], receipt.roots[1:]):  # Either result missing.
        with pytest.raises(C0ContractError, match="missing/overlapping"):
            receipt.model_copy(update={"roots": kept}).validate_against(
                workset, workset_ref
            )


def test_transition_batch_identity_binds_every_scoped_fact_and_order() -> None:
    workset, workset_ref = fixture_workset(include_transition=True)
    first = workset.transitions[0]
    second = first.model_copy(update={"fact_id": digest("another-scoped-fact")})
    a = transition_identity(workset, workset_ref, transitions=(first, second))
    b = transition_identity(workset, workset_ref, transitions=(second, first))
    expect(
        a.logical_acceptance_key() != b.logical_acceptance_key(),
        "transition batch key lost exact ordering",
    )
    duplicate = a.model_dump(mode="json") | {
        "transitions": [first.model_dump(mode="json")] * 2
    }
    expect_one_error(StageIdentity, duplicate, "duplicate exact transition")


def test_a2_held_is_explicit_and_never_claims_complete() -> None:
    workset, workset_ref = fixture_workset()
    outcome = valid_roots(workset)[0]
    selection = outcome.selection
    if selection is None:
        pytest.fail("Incremental prepared root lacked exact IntakeSelection")
    a2_held = TerminalRoot(
        selection=selection,
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
        selected=selection.result,
        entry=selection.entry,
        occurrence=0,
        reason=HeldReason.ROLE_UNVERIFIABLE,
        selection_sha256=digest("saved-original-selection"),
        configuration_version="v1",
        code_version="v1",
    )
    with pytest.raises(ValidationError, match="wrong kind/version"):
        TerminalRoot(
            selection=selection,
            workset_selection_index=0,
            result=ref("prepared", 1, "2"),
            disposition="held",
            status=TerminalStatus.INCOMPLETE,
        )


def test_intake_held_only_needs_incomplete_receipt_without_fake_prepared() -> None:
    workset, workset_ref = fixture_workset(held_only=True)
    expect(not workset.selections, "held-only fixture must have no selections")
    receipt = valid_receipt(workset, workset_ref, status=TerminalStatus.INCOMPLETE)
    receipt.validate_against(workset, workset_ref)
    with pytest.raises(C0ContractError, match="status"):
        valid_receipt(workset, workset_ref).validate_against(workset, workset_ref)


def test_transitions_have_one_exact_scoped_batch_not_fabricated_message() -> None:
    workset, workset_ref = fixture_workset(include_transition=True)
    receipt = valid_receipt(workset, workset_ref)
    receipt.validate_against(workset, workset_ref)
    original_batch = receipt.transition_batch
    if original_batch is None:
        pytest.fail("Expected an exact scoped transition batch")
    changed = original_batch.model_copy(update={"transitions": ()})
    with pytest.raises(C0ContractError, match="altered scoped"):
        receipt.model_copy(update={"transition_batch": changed}).validate_against(
            workset, workset_ref
        )


def test_receipt_policy_version_is_frozen_non_blank_and_bounded() -> None:
    workset, workset_ref = fixture_workset()
    payload = valid_receipt(workset, workset_ref).model_dump(mode="json")
    for good in ("c0-policy-v1", "p" * 2048):  # Positive controls.
        errors = decode_errors(CompletionReceipt, payload | {"policy_version": good})
        expect(errors == [], f"valid policy of {len(good)} bytes rejected: {errors}")
    for bad in ("", "   ", "p" * 2049):
        changed = payload | {"policy_version": bad}
        expect_one_error(CompletionReceipt, changed, "frozen receipt policy")


def test_pydantic_frozen_strict_schema_and_roundtrip() -> None:
    workset, workset_ref = fixture_workset(selections_per_entry=2)
    receipt = valid_receipt(workset, workset_ref)
    payload = receipt.model_dump(mode="json")
    restored = strict_json(CompletionReceipt, payload)
    expect(restored == receipt, "receipt changed in a strict JSON round trip")
    restored.validate_against(workset, workset_ref)
    expect_one_error(CompletionReceipt, payload | {"extra": 1}, "extra: Extra inputs")
    with pytest.raises(ValidationError, match="frozen"):
        restored.policy_version = "mutated"
