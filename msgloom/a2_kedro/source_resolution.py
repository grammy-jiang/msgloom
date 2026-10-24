"""
Re-verify a ``FrozenSourceSelection`` against an exact release reader (C0-02).

``resolve_frozen_selection`` takes a stored selection, the frozen Intake
workset and an injected :class:`ReleaseReader`. It re-reads every release
entry that owns a root, exactly once. For each root it checks, against the
re-read A1 evidence:

* the ordinal identity (the root ordinal must be the one that reproduces the
  Intake selection identity);
* byte equality (the saved ``selection_sha256`` must equal the digest of the
  re-read value at that ordinal);
* the role, which comes from the proven ordinal and never from the stored
  root.

The proof reuses :func:`verify_exact_occurrence`. A root that differs from
its proof raises :exc:`A2ContractError`. A stored digest that was recomputed
by a forger therefore still fails.

Release shapes. A release with a primary selection has ordinal 0 as
``primary`` and later ordinals as ``component``. A component-only release has
no primary: its ordinal 0 is ``component``. A context-only release and a
transition-only release hold no selectable occurrence. They cannot own a
root. A root that points at one raises :exc:`A2ContractError` with a
distinct message. Such an entry has no occurrence to prove.

Source read errors. A read error is not a contract violation: it means the
evidence cannot be read now. Each :exc:`SourceReaderError` becomes one
:class:`InputDisposition` per root of that entry. The reason mapping is
closed (see :func:`held_reason_for`). The held record copies only root
fields. It never copies the error text, so no path or body text can leak.
Any other exception, and cancellation, propagates unchanged.

Global sequence gaps. A1 publishes one global sequence across streams. A
gap between the previous anchor and the workset entries is therefore legal
for one stream. The function reports every gap as a :class:`SequenceGap`.
With ``allow_gaps=False`` the first gap raises :exc:`A2ContractError`.

Out of scope. Baseline selections hold no release entry. The release reader
cannot read them, so a baseline selection raises :exc:`A2ContractError`.
``selection.verify_against_evidence`` stays the baseline path.

Names introduced here are internal Python names only: ``SequenceGap``,
``SourceResolution``, ``held_reason_for`` and ``resolve_frozen_selection``.
They add no wire field and no schema. The held record uses the existing
``a2_input_disposition@1`` contract unchanged.

CANDIDATE/RESEARCH: the held reason mapping is a decision that needs review.
The stored ``selection_sha256`` of a held root is unproven, because its
evidence could not be read.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from msgloom.a2_kedro.contracts.codec import A2ContractError
from msgloom.a2_kedro.contracts.held import HeldReason, InputDisposition
from msgloom.a2_kedro.contracts.source import (
    FrozenRoot,
    FrozenSourceSelection,
    OccurrenceEvidence,
    ReleaseReader,
    evidence_from_released,
    verify_exact_occurrence,
)
from msgloom.preparation_pipeline.intake_models import PreparationIntakeWorkset
from msgloom.sources.handoff_models import ReleaseEntryRef
from msgloom.sources.models import SourceEvidenceLimitError, SourceReaderError


@dataclass(frozen=True, slots=True)
class SequenceGap:
    """
    Missing global release sequence numbers between two anchors.

    ``after_seq`` is the previous anchor or entry. ``before_seq`` is the next
    workset entry. The missing numbers lie strictly between them.
    """

    after_seq: int
    before_seq: int


@dataclass(frozen=True, slots=True)
class SourceResolution:
    """
    Outcome of one re-verification, in workset order.

    ``roots`` holds the roots that A1 evidence proved. ``held`` holds one
    record per root whose entry could not be read. Together they cover every
    root of the selection exactly once.
    """

    roots: tuple[FrozenRoot, ...]
    held: tuple[InputDisposition, ...]
    gaps: tuple[SequenceGap, ...]


def held_reason_for(error: SourceReaderError) -> HeldReason:
    """
    Map a typed source read error to its closed held reason.

    ``SourceEvidenceLimitError`` maps to ``INPUT_LIMIT``. Every other A1
    reader error maps to ``SOURCE_EVIDENCE_UNAVAILABLE``: a reference
    error, an evidence error or an unknown reader error subclass. The text
    of ``error`` is never read.
    """
    if isinstance(error, SourceEvidenceLimitError):
        return HeldReason.INPUT_LIMIT
    return HeldReason.SOURCE_EVIDENCE_UNAVAILABLE


def sequence_gaps(workset: PreparationIntakeWorkset) -> tuple[SequenceGap, ...]:
    """Return every gap from the previous anchor through the last entry."""
    gaps: list[SequenceGap] = []
    last = workset.previous.last_release_entry_seq
    for ref in workset.entries:
        seq = ref.release_entry_seq
        if seq != last + 1:
            gaps.append(SequenceGap(after_seq=last, before_seq=seq))
        last = seq
    return tuple(gaps)


def _entry_evidence(entry: ReleaseEntryRef, released: Any) -> OccurrenceEvidence:
    """Project the answer and reject an entry that has no occurrence."""
    evidence = evidence_from_released(released)
    if evidence.reference != entry:
        raise A2ContractError("reader answered a different release entry")
    if evidence.occurrence_sha256:
        return evidence
    if released.transitions:
        raise A2ContractError("root entry is transition-only")
    if released.contexts:
        raise A2ContractError("root entry is context-only")
    raise A2ContractError("root entry has no selectable occurrence")


def _prove(
    workset: PreparationIntakeWorkset,
    root: FrozenRoot,
    evidence: OccurrenceEvidence,
) -> FrozenRoot:
    """Rebuild ``root`` from evidence; every proven field must be equal."""
    proven = verify_exact_occurrence(
        workset,
        workset.selections[root.workset_index],
        evidence,
        saved_selection_sha256=root.selection_sha256,
    )
    for name in FrozenRoot.model_fields:
        if getattr(root, name) != getattr(proven, name):
            raise A2ContractError(f"root {name} differs from A1 evidence")
    return proven


async def resolve_frozen_selection(
    selection: FrozenSourceSelection,
    workset: PreparationIntakeWorkset,
    reader: ReleaseReader,
    *,
    allow_gaps: bool = True,
) -> SourceResolution:
    """
    Re-verify ``selection`` against ``workset`` and the exact ``reader``.

    Order: the selection is checked against the workset first, with no read.
    Then each entry that owns a root is read once, in workset order.

    Raise :exc:`A2ContractError` for a selection that differs from the
    workset, a baseline selection, a gap when ``allow_gaps`` is false, a
    reader answer that is not the exact entry, an entry without a
    selectable occurrence, or any root whose ordinal, role, proof, selected
    reference or saved digest differs from the re-read evidence.

    A :exc:`SourceReaderError` does not raise. It becomes a held record for
    each root of that entry. See :func:`held_reason_for`.
    """
    selection.verify_against(workset)
    if selection.incremental_roots is None:
        raise A2ContractError("baseline roots need a baseline reader")
    gaps = sequence_gaps(workset)
    if gaps and not allow_gaps:
        raise A2ContractError("global release sequence has a gap")
    by_entry: dict[ReleaseEntryRef, list[FrozenRoot]] = {}
    for root in selection.incremental_roots:
        if root.entry is None:
            raise A2ContractError("incremental root needs release and ordinal")
        by_entry.setdefault(root.entry, []).append(root)
    proven: list[FrozenRoot] = []
    held: list[InputDisposition] = []
    for entry, roots in by_entry.items():
        try:
            released = await reader.read_entry(entry)
        except SourceReaderError as error:
            reason = held_reason_for(error)
            held.extend(
                InputDisposition.from_root(
                    root,
                    reason,
                    configuration_version=workset.configuration_version,
                    code_version=workset.code_version,
                )
                for root in roots
            )
            continue
        evidence = _entry_evidence(entry, released)
        proven.extend(_prove(workset, root, evidence) for root in roots)
    return SourceResolution(
        roots=tuple(sorted(proven, key=lambda r: r.workset_index)),
        held=tuple(sorted(held, key=lambda h: h.workset_index)),
        gaps=gaps,
    )
