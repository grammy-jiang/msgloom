"""Frozen roots proven by real A1 typed evidence, with no look-alike stubs."""

from __future__ import annotations

import asyncio
from dataclasses import asdict, replace

import pytest
from pydantic import ValidationError

from msgloom.a2_kedro.contracts.codec import A2ContractError, sha256_hex
from msgloom.a2_kedro.contracts.source import (
    OccurrenceEvidence,
    ReadOnlyOccurrenceAdapter,
    evidence_from_released,
    verify_baseline_selection,
    verify_exact_occurrence,
)
from msgloom.contracts import ResultRef
from msgloom.preparation_pipeline.intake import _identity
from msgloom.preparation_pipeline.intake_models import (
    IntakeAnchor,
    PreparationIntakeWorkset,
)
from msgloom.sources._snapshot import CollectedSelectionCodec
from msgloom.sources.handoff_models import A1CatalogIdentity, ReleaseEntryRef
from tests.a2_kedro.a1_typed import (
    TypedReader,
    collected,
    fact,
    released,
    selection_of,
    workset_of,
)
from tests.a2_kedro.helpers import CODE, CONFIG, SCOPE, check, entry, mutate


def digest_of(value: object) -> str:
    """Return the digest of ``value`` under the real A1 codec."""
    return sha256_hex(CollectedSelectionCodec().encode(value))


def read(value: object, seq: int = 1):
    """Read ``value`` through the adapter and return its evidence."""
    return asyncio.run(
        ReadOnlyOccurrenceAdapter(TypedReader(value)).evidence(entry(seq))
    )


def test_primary_from_real_released_input() -> None:
    value = released(1, components=1)
    ws = workset_of(value, (selection_of(value, 0),))
    root = verify_exact_occurrence(
        ws,
        ws.selections[0],
        read(value),
        saved_selection_sha256=digest_of(value.selection),
    )
    check(root.role == "primary" and root.ordinal == 0, "primary ordinal")
    check(root.entry == value.reference, "real entry reference bound")


def test_component_from_real_released_input() -> None:
    value = released(1, components=2)
    ws = workset_of(value, (selection_of(value, 2),))
    root = verify_exact_occurrence(
        ws,
        ws.selections[0],
        read(value),
        saved_selection_sha256=digest_of(value.components[1]),
    )
    check(root.role == "component" and root.ordinal == 2, "component ordinal")


def test_component_only_release_has_no_primary() -> None:
    value = released(1, components=1, primary=False)
    ws = workset_of(value, (selection_of(value, 0),))
    root = verify_exact_occurrence(
        ws,
        ws.selections[0],
        read(value),
        saved_selection_sha256=digest_of(value.components[0]),
    )
    check(root.role == "component" and root.ordinal == 0, "no primary role")


def test_baseline_from_real_collected_selection() -> None:
    value = collected("base-1")
    ref = ResultRef(
        _identity(
            "baseline-selection",
            [SCOPE.claim_key(), asdict(value.selection), CONFIG, CODE],
        ),
        "collected_selection",
        "1",
    )
    ws = PreparationIntakeWorkset(
        scope=SCOPE,
        previous=IntakeAnchor(),
        cutoff=IntakeAnchor(),
        entries=(),
        configuration_version=CONFIG,
        code_version=CODE,
        baseline_approval="approval-1",
        baseline_sources=(value.source,),
        baseline_selections=(ref,),
    )
    root = verify_baseline_selection(ws, 0, value)
    check(root.role == "baseline" and root.entry is None, "baseline shape")
    check(root.selection_sha256 == digest_of(value), "digest from real codec")
    with pytest.raises(A2ContractError, match="another source"):
        verify_baseline_selection(ws, 0, collected("other"))
    with pytest.raises(A2ContractError, match="not a CollectedSelection"):
        verify_baseline_selection(ws, 0, value.model_dump())  # type: ignore[arg-type]


def test_invalid_ordinal_rejected() -> None:
    value = released(1, components=1)
    ws = workset_of(value, (selection_of(value, 5),))
    with pytest.raises(A2ContractError, match="one role"):
        verify_exact_occurrence(
            ws, ws.selections[0], read(value), saved_selection_sha256="1" * 64
        )


def test_invalid_role_rejected() -> None:
    with pytest.raises(ValidationError):
        fact(0, "owner")  # type: ignore[arg-type]
    value = released(1)
    ws = workset_of(value, (selection_of(value, 0),))
    root = verify_exact_occurrence(
        ws,
        ws.selections[0],
        read(value),
        saved_selection_sha256=digest_of(value.selection),
    )
    with pytest.raises(ValueError):
        mutate(root, role="context")


def test_invalid_member_role_rejected_by_verifier() -> None:
    value = released(1)
    ws = workset_of(value, (selection_of(value, 0),))
    evidence = read(value)
    forged = replace(
        evidence, members=((evidence.members[0][0], "owner"), *evidence.members[1:])
    )
    with pytest.raises(A2ContractError, match="one role"):
        verify_exact_occurrence(
            ws,
            ws.selections[0],
            forged,
            saved_selection_sha256=digest_of(value.selection),
        )


def test_adapter_reads_once_and_never_writes() -> None:
    value = released(1)
    reader = TypedReader(value)
    adapter = ReadOnlyOccurrenceAdapter(reader)
    asyncio.run(adapter.evidence(entry(1)))
    check(reader.calls == [entry(1)], "exactly one read_entry call")
    public = [name for name in dir(adapter) if not name.startswith("_")]
    check(public == ["evidence"], f"adapter public surface is read-only: {public}")


def test_invalid_saved_sha_rejected() -> None:
    value = released(1)
    ws = workset_of(value, (selection_of(value, 0),))
    for bad in ("2" * 64, "not-a-digest", ""):
        with pytest.raises(A2ContractError, match="differs from re-read"):
            verify_exact_occurrence(
                ws, ws.selections[0], read(value), saved_selection_sha256=bad
            )


def test_duplicate_occurrence_rejected() -> None:
    twin = collected("twin")
    value = released(1).model_copy(update={"components": (twin,), "selection": twin})
    with pytest.raises(A2ContractError, match="repeats one selection"):
        evidence_from_released(value)
    ws = workset_of(released(1), (selection_of(released(1), 0),))
    data = ws.model_dump(mode="json")
    data["selections"] = [data["selections"][0]] * 2
    with pytest.raises(ValueError):
        PreparationIntakeWorkset.model_validate(data)


def test_cross_catalog_rejected() -> None:
    other = ReleaseEntryRef(
        catalog=A1CatalogIdentity(catalog_identity="cat-2", schema_version=1),
        release_entry_seq=1,
        entry_digest=entry(1).entry_digest,
    )
    foreign = released(1, reference=other)
    with pytest.raises(A2ContractError, match="different release entry"):
        read(foreign)
    ws = workset_of(released(1), (selection_of(released(1), 0),))
    with pytest.raises(A2ContractError, match="does not match exact release"):
        verify_exact_occurrence(
            ws,
            ws.selections[0],
            evidence_from_released(foreign),
            saved_selection_sha256=digest_of(foreign.selection),
        )


def test_adapter_rejects_look_alike_values() -> None:
    class Imitation:
        reference = entry(1)
        facts = ()
        selection = None
        components = ()

    with pytest.raises(A2ContractError, match="not an A1 ReleasedInput"):
        read(Imitation())


def test_adapter_has_no_caller_chosen_encoder() -> None:
    with pytest.raises(TypeError):
        ReadOnlyOccurrenceAdapter(TypedReader(released(1)), lambda v: b"x")  # type: ignore[call-arg]
    value = released(1)
    evidence = read(value)
    check(
        evidence.occurrence_sha256 == (digest_of(value.selection),),
        "bytes come from the A1 codec",
    )


def test_source_and_role_are_not_forgeable() -> None:
    value = released(1, components=1)
    ws = workset_of(value, (selection_of(value, 1),))
    # A caller claims the component digest belongs to the primary slot.
    forged = replace(
        read(value),
        occurrence_sha256=(digest_of(value.components[0]),) * 2,
    )
    root = verify_exact_occurrence(
        ws,
        ws.selections[0],
        forged,
        saved_selection_sha256=digest_of(value.components[0]),
    )
    # The role still follows the proven ordinal, not caller input.
    check(root.role == "component" and root.ordinal == 1, "role from ordinal")
    # A caller cannot swap the member list to shift the proof.
    swapped = replace(read(value), members=(("e" * 64, "primary"),))
    with pytest.raises(A2ContractError, match="one role"):
        verify_exact_occurrence(
            ws,
            ws.selections[0],
            swapped,
            saved_selection_sha256=digest_of(value.components[0]),
        )
    # A caller cannot change which source the saved digest names.
    other = collected("elsewhere")
    with pytest.raises(A2ContractError, match="differs from re-read"):
        verify_exact_occurrence(
            ws,
            ws.selections[0],
            read(value),
            saved_selection_sha256=digest_of(other),
        )


def test_gap_evidence_object_is_caller_constructible() -> None:
    """
    Show the missing public bridge: evidence is not bound to a real read.

    A caller can build ``OccurrenceEvidence`` by hand. The verifier checks
    it against the workset only. The binding to a real A1 read depends on
    the caller using the adapter. A1 offers no public API that signs or
    verifies an occurrence, so this stays a documented gap.
    """
    value = released(1)
    ws = workset_of(value, (selection_of(value, 0),))
    hand_made = OccurrenceEvidence(
        reference=value.reference,
        members=tuple((f.fact_id, f.role) for f in value.facts),
        occurrence_sha256=("a" * 64,),
        has_primary=True,
    )
    root = verify_exact_occurrence(
        ws, ws.selections[0], hand_made, saved_selection_sha256="a" * 64
    )
    check(root.selection_sha256 == "a" * 64, "gap: unread digest was accepted")


def test_gap_formula_change_fails_closed() -> None:
    """A changed Intake formula rejects every root; nothing passes silently."""
    value = released(1, components=1)
    drifted = workset_of(value, (selection_of(value, 0, config="config-2"),))
    for current in (value.selection, value.components[0]):
        with pytest.raises(A2ContractError, match="one role"):
            verify_exact_occurrence(
                drifted,
                drifted.selections[0],
                read(value),
                saved_selection_sha256=digest_of(current),
            )
