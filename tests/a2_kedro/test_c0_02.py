"""C0-02: re-verify a frozen source selection against an exact reader."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from msgloom.a2_kedro.contracts.codec import A2ContractError
from msgloom.a2_kedro.contracts.held import HeldReason
from msgloom.a2_kedro.contracts.source import (
    FrozenRoot,
    FrozenSourceSelection,
    evidence_from_released,
    verify_exact_occurrence,
)
from msgloom.a2_kedro.source_resolution import (
    SequenceGap,
    SourceResolution,
    held_reason_for,
    resolve_frozen_selection,
    sequence_gaps,
)
from msgloom.preparation_pipeline.intake_models import (
    IntakeAnchor,
    IntakeSelection,
    PreparationIntakeWorkset,
)
from msgloom.sources.handoff_models import ReleaseEntryRef
from msgloom.sources.models import (
    SourceEvidenceError,
    SourceEvidenceLimitError,
    SourceReaderError,
    SourceReferenceError,
)
from msgloom.sources.release_models import ReleasedInput, ScopedTransition
from tests.a2_kedro.a1_typed import collected, fact, released, selection_of
from tests.a2_kedro.helpers import (
    CODE,
    CONFIG,
    SCOPE,
    WORKSET_REF,
    check,
    entry,
    hexd,
    mutate,
)

BAD = (ValueError, A2ContractError)
SECRET = "/home/secret/mailbox.db BODY-TEXT-7731"


class MapReader:
    """Reader double: one prepared answer or error per entry sequence."""

    def __init__(self, answers: dict[int, Any]) -> None:
        self.answers = answers
        self.calls: list[ReleaseEntryRef] = []

    async def read_entry(self, entry: ReleaseEntryRef) -> Any:
        """Record the call; raise or return the prepared answer."""
        self.calls.append(entry)
        answer = self.answers[entry.release_entry_seq]
        if isinstance(answer, BaseException):
            raise answer
        return answer


def make_workset(
    values: list[ReleasedInput],
    selections: tuple[IntakeSelection, ...],
    *,
    previous: int = 0,
) -> PreparationIntakeWorkset:
    """Build a workset whose entries are the references of ``values``."""
    refs = tuple(v.reference for v in values)
    anchor = IntakeAnchor()
    if previous:
        anchor = IntakeAnchor(
            last_release_entry_seq=previous,
            last_release_entry_digest=hexd("1"),
        )
    return PreparationIntakeWorkset(
        scope=SCOPE,
        previous=anchor,
        cutoff=IntakeAnchor(
            last_release_entry_seq=refs[-1].release_entry_seq,
            last_release_entry_digest=refs[-1].entry_digest,
        ),
        entries=refs,
        selections=selections,
        configuration_version=CONFIG,
        code_version=CODE,
    )


class Case:
    """A consistent workset, proven roots and selection for ``values``."""

    def __init__(self, values: list[ReleasedInput], *, previous: int = 0) -> None:
        self.values = values
        evidence = [evidence_from_released(v) for v in values]
        pairs = [
            (i, o)
            for i, ev in enumerate(evidence)
            for o in range(len(ev.occurrence_sha256))
        ]
        selections = tuple(selection_of(values[i], o) for i, o in pairs)
        self.workset = make_workset(values, selections, previous=previous)
        self.roots = tuple(
            verify_exact_occurrence(
                self.workset,
                self.workset.selections[n],
                evidence[i],
                saved_selection_sha256=evidence[i].occurrence_sha256[o],
            )
            for n, (i, o) in enumerate(pairs)
        )

    def selection(
        self, roots: tuple[FrozenRoot, ...] | None = None
    ) -> FrozenSourceSelection:
        """Return a selection with a freshly computed digest."""
        return FrozenSourceSelection.build(
            WORKSET_REF, SCOPE, incremental_roots=roots or self.roots
        )

    def reader(self) -> MapReader:
        """Return a reader that answers with the original values."""
        return MapReader({v.reference.release_entry_seq: v for v in self.values})

    def resolve(
        self,
        selection: FrozenSourceSelection | None = None,
        reader: MapReader | None = None,
        **options: Any,
    ) -> SourceResolution:
        """Run the async resolution to completion."""
        return asyncio.run(
            resolve_frozen_selection(
                selection or self.selection(),
                self.workset,
                reader or self.reader(),
                **options,
            )
        )


def fail_with(case: Case, selection: FrozenSourceSelection, text: str) -> None:
    """Resolve ``selection`` and require an ``A2ContractError`` with ``text``."""
    with pytest.raises(A2ContractError, match=text):
        case.resolve(selection)


def two_entries() -> Case:
    return Case([released(1, components=1), released(2)])


def test_exact_selection_resolves_every_root_and_reads_each_entry_once() -> None:
    case = two_entries()
    reader = case.reader()
    result = case.resolve(reader=reader)
    check(result.roots == case.roots, "all roots proven in workset order")
    check(len(result.roots) == 3, "three roots")
    check(result.held == () and result.gaps == (), "no held, no gap")
    check(
        [r.role for r in result.roots] == ["primary", "component", "primary"],
        "roles come from the proven ordinals",
    )
    check(
        reader.calls == [case.values[0].reference, case.values[1].reference],
        "one read per entry, in workset order",
    )


def test_duplicate_ordinal_claim_is_rejected_by_structure() -> None:
    case = two_entries()
    forged = mutate(case.roots[1], ordinal=0, role="primary")
    with pytest.raises(BAD, match="duplicate entry ordinal"):
        case.selection((case.roots[0], forged, case.roots[2]))


def test_forged_ordinal_on_a_single_root_is_rejected() -> None:
    case = Case([released(1, components=1)])
    # Keep only the ordinal-1 selection so the forged root is structurally
    # valid. The role stays "component", so only the ordinal is forged.
    forged = mutate(case.roots[1], ordinal=0, workset_index=0)
    check(forged.role == "component", "fixture role")
    workset = make_workset(case.values, (case.workset.selections[1],))
    selection = FrozenSourceSelection.build(
        WORKSET_REF, SCOPE, incremental_roots=(forged,)
    )
    with pytest.raises(A2ContractError, match="root ordinal differs"):
        asyncio.run(resolve_frozen_selection(selection, workset, case.reader()))


def test_swapped_ordinals_are_rejected() -> None:
    case = Case([released(1, primary=False, components=2)])
    first, second = case.roots
    swapped = (mutate(first, ordinal=1), mutate(second, ordinal=0))
    fail_with(case, case.selection(swapped), "root ordinal differs")


def test_forged_role_is_rejected() -> None:
    case = Case([released(1, components=1)])
    forged = mutate(case.roots[1], role="primary")
    with pytest.raises(BAD, match="primary role needs"):
        case.selection((case.roots[0], forged))
    demoted = mutate(case.roots[0], role="component")
    fail_with(case, case.selection((demoted, case.roots[1])), "root role differs")


def test_forged_digest_with_recomputed_selection_digest_is_rejected() -> None:
    case = two_entries()
    forged = mutate(case.roots[0], selection_sha256="2" * 64)
    selection = case.selection((forged, *case.roots[1:]))
    check(
        selection.selection_set_sha256 == selection.content_sha256(),
        "the forger recomputed the set digest, so only A1 can catch it",
    )
    fail_with(case, selection, "saved selection differs from re-read")


def test_changed_reread_bytes_are_rejected() -> None:
    case = two_entries()
    original = case.values[0]
    tampered = ReleasedInput(
        reference=original.reference,
        selection=collected("tampered"),
        components=original.components,
        facts=original.facts,
    )
    reader = MapReader({1: tampered, 2: case.values[1]})
    with pytest.raises(A2ContractError, match="saved selection differs"):
        case.resolve(reader=reader)


def test_root_for_another_selection_is_rejected() -> None:
    case = two_entries()
    other = case.workset.selections[2].result
    proof = other.result_id.split(":", 1)[1]
    swapped = mutate(case.roots[0], selected=other, a1_ordinal_proof=proof)
    fail_with(case, case.selection((swapped, *case.roots[1:])), "differs from")


def test_component_only_roots_are_proven_as_components() -> None:
    case = Case([released(1, primary=False, components=2)])
    result = case.resolve()
    check(
        [(r.role, r.ordinal) for r in result.roots]
        == [("component", 0), ("component", 1)],
        "ordinal 0 is a component when no primary exists",
    )


def test_component_only_root_cannot_claim_primary() -> None:
    case = Case([released(1, primary=False, components=1)])
    forged = mutate(case.roots[0], role="primary")
    fail_with(case, case.selection((forged,)), "root role differs")


def transition_value(seq: int) -> ReleasedInput:
    return ReleasedInput(
        reference=entry(seq),
        selection=None,
        transitions=(
            ScopedTransition(
                fact_id=hexd("c"),
                source_id="src-1",
                stream="outlook_mail",
                resource_kind="mail",
                resource_identity="r-c",
                parent_resource_kind=None,
                parent_resource_identity=None,
                scope_kind="folder",
                scope_identity="inbox",
                reason="deleted",
                authority_revision=None,
                provider_order=None,
                evidence=None,
            ),
        ),
        facts=(fact(0, "transition"),),
    )


def context_value(seq: int) -> ReleasedInput:
    return ReleasedInput(
        reference=entry(seq),
        selection=None,
        contexts=(collected(f"x{seq}"),),
        facts=(fact(0, "context"),),
    )


def empty_value(seq: int) -> ReleasedInput:
    return ReleasedInput(
        reference=entry(seq), selection=None, facts=(fact(0, "proof"),)
    )


def selection_without_evidence(value: ReleasedInput) -> tuple[Case, FrozenRoot]:
    """Build a workset that wrongly selects an occurrence of ``value``."""
    sel = selection_of(value, 0)
    ws = make_workset([value], (sel,))
    case = Case.__new__(Case)
    case.values = [value]
    case.workset = ws
    root = FrozenRoot(
        selected=sel.result,
        workset_index=0,
        role="component",
        selection_sha256=hexd("1"),
        ordinal=0,
        a1_ordinal_proof=sel.result.result_id.split(":", 1)[1],
        entry=sel.entry,
    )
    case.roots = (root,)
    return case, root


@pytest.mark.parametrize(
    ("build", "text"),
    [
        (transition_value, "transition-only"),
        (context_value, "context-only"),
        (empty_value, "no selectable occurrence"),
    ],
)
def test_root_over_entry_without_occurrence_is_rejected(build: Any, text: str) -> None:
    case, root = selection_without_evidence(build(1))
    fail_with(case, case.selection((root,)), text)


def test_hand_built_root_over_component_entry_still_checks_bytes() -> None:
    # Positive control: the same builder over a real component entry works.
    case, root = selection_without_evidence(released(1, primary=False, components=1))
    forged = mutate(root, selection_sha256="3" * 64)
    fail_with(case, case.selection((forged,)), "saved selection differs")


def test_gaps_are_reported_not_rejected_by_default() -> None:
    case = Case([released(1), released(4)])
    result = case.resolve()
    check(result.gaps == (SequenceGap(after_seq=1, before_seq=4),), "gap 1..4")
    check(len(result.roots) == 2, "roots are still proven")
    with pytest.raises(A2ContractError, match="gap"):
        case.resolve(allow_gaps=False)


def test_sequence_gaps_cover_the_previous_anchor() -> None:
    check(sequence_gaps(Case([released(1)]).workset) == (), "genesis, no gap")
    check(sequence_gaps(Case([released(1), released(2)]).workset) == (), "dense")
    late = Case([released(3)])
    check(
        sequence_gaps(late.workset) == (SequenceGap(0, 3),),
        "first entry is not 1",
    )
    after = Case([released(6)], previous=5)
    check(sequence_gaps(after.workset) == (), "follows the previous anchor")
    skipped = Case([released(8)], previous=5)
    check(sequence_gaps(skipped.workset) == (SequenceGap(5, 8),), "gap after")


ERRORS = [
    (SourceReferenceError, HeldReason.SOURCE_EVIDENCE_UNAVAILABLE),
    (SourceEvidenceError, HeldReason.SOURCE_EVIDENCE_UNAVAILABLE),
    (SourceEvidenceLimitError, HeldReason.INPUT_LIMIT),
    (SourceReaderError, HeldReason.SOURCE_EVIDENCE_UNAVAILABLE),
]


@pytest.mark.parametrize(("kind", "reason"), ERRORS)
def test_source_read_error_becomes_a_held_outcome(
    kind: type[SourceReaderError], reason: HeldReason
) -> None:
    case = two_entries()
    reader = MapReader({1: kind(SECRET), 2: case.values[1]})
    result = case.resolve(reader=reader)
    check(held_reason_for(kind(SECRET)) is reason, "mapping function")
    check(len(result.held) == 2, "one held record per root of the entry")
    for record, root in zip(result.held, case.roots[:2], strict=True):
        check(record.reason is reason, "closed reason")
        check(record.repair_class == "operator_repair", "explicit repair class")
        check(record.configuration_version == CONFIG, "config version")
        check(record.code_version == CODE, "code version")
        record.validate_against(root)
    check(result.roots == (case.roots[2],), "other entry stays proven")
    leaked = json.dumps([h.model_dump(mode="json") for h in result.held]) + repr(result)
    for word in ("secret", "mailbox", "BODY-TEXT", "7731"):
        check(word not in leaked, f"held outcome leaks {word}")


def test_every_entry_unreadable_gives_only_held_outcomes() -> None:
    case = two_entries()
    reader = MapReader(
        {1: SourceEvidenceError(SECRET), 2: SourceReferenceError(SECRET)}
    )
    result = case.resolve(reader=reader)
    check(result.roots == (), "nothing proven")
    check([h.workset_index for h in result.held] == [0, 1, 2], "all held")


def test_other_reader_exceptions_are_not_swallowed() -> None:
    case = two_entries()
    reader = MapReader({1: RuntimeError("boom"), 2: case.values[1]})
    with pytest.raises(RuntimeError, match="boom"):
        case.resolve(reader=reader)


def test_reader_cancellation_is_not_swallowed() -> None:
    case = two_entries()
    reader = MapReader({1: asyncio.CancelledError(), 2: case.values[1]})
    with pytest.raises(asyncio.CancelledError):
        case.resolve(reader=reader)
    check(reader.calls[0].release_entry_seq == 1, "cancel hit first read")


def test_wrong_reader_answers_are_contract_errors_without_leaks() -> None:
    case = two_entries()
    for answer in (case.values[1], "not released", None):
        reader = MapReader({1: answer, 2: case.values[1]})
        with pytest.raises(A2ContractError) as info:
            case.resolve(reader=reader)
        text = str(info.value)
        check(entry(1).entry_digest not in text, "message names no digest")
        check("not released" not in text, "message echoes no answer")


def test_baseline_selection_is_not_read_through_a_release_reader() -> None:
    from tests.a2_kedro.test_c0_01 import baseline
    from tests.a2_kedro.test_source import baseline_workset

    reader = MapReader({})
    with pytest.raises(A2ContractError):
        asyncio.run(resolve_frozen_selection(baseline(), baseline_workset(), reader))
    check(reader.calls == [], "no read for a baseline")


def test_stale_selection_fails_before_any_read() -> None:
    case = two_entries()
    other = Case([released(1, components=1), released(2), released(3)])
    reader = case.reader()
    with pytest.raises(A2ContractError):
        asyncio.run(resolve_frozen_selection(case.selection(), other.workset, reader))
    check(reader.calls == [], "workset mismatch is caught without reading")
