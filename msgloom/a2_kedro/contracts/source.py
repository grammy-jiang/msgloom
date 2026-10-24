"""
Frozen source roots and the read-only A1 occurrence adapter.

A ``FrozenRoot`` names one selected occurrence of a frozen Intake workset.
For an incremental workset it binds the exact A1 release entry, the
per-entry ordinal and an ordinal proof. For an approved historical
baseline it binds the approved source version instead and never fabricates
a release entry.

The adapter only reads. It calls ``read_entry`` on an injected reader and
never writes A1 ledgers, Intake rows or cursors. Ordering: evidence is
read first, then the proof is computed, then the root is built.

Failure handling: any mismatch raises :exc:`A2ContractError`. The messages
never carry source bytes or provider identifiers.

CANDIDATE/RESEARCH: the ordinal formula mirrors the one used by
``msgloom.preparation_pipeline.intake`` today. A production verifier must
come from a public A1 API before cutover. If Intake changes the formula,
``verify_exact_occurrence`` rejects every root.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Any, Literal, Protocol

from pydantic import Field, model_validator

from msgloom.a2_kedro.contracts.codec import (
    A2ContractError,
    A2Model,
    Digest,
    Text,
    sha256_hex,
)
from msgloom.contracts import ResultRef, VersionRef
from msgloom.preparation_pipeline.intake_models import (
    IntakeSelection,
    PreparationIntakeWorkset,
)
from msgloom.sources.handoff_models import ReleaseEntryRef

Index = Annotated[int, Field(ge=0, le=1023)]


def _is_selection(ref: ResultRef) -> bool:
    return (ref.kind, ref.schema_version) == ("collected_selection", "1")


class FrozenRoot(A2Model):
    """One selected occurrence, incremental or approved baseline."""

    selected: ResultRef
    workset_index: Index
    role: Literal["primary", "component", "baseline"]
    selection_sha256: Digest
    ordinal: Index | None = None
    a1_ordinal_proof: Digest | None = None
    entry: ReleaseEntryRef | None = None
    baseline_source: VersionRef | None = None
    baseline_approval: Text | None = None

    @model_validator(mode="after")
    def _exclusive_source(self) -> FrozenRoot:
        if not _is_selection(self.selected):
            raise A2ContractError("frozen root is not collected_selection@1")
        incremental = (self.entry, self.ordinal, self.a1_ordinal_proof)
        baseline = (self.baseline_source, self.baseline_approval)
        if self.role == "baseline":
            if any(v is not None for v in incremental):
                raise A2ContractError("baseline cannot carry release proof")
            if any(v is None for v in baseline):
                raise A2ContractError("baseline needs approval and source")
            return self
        if any(v is None for v in incremental):
            raise A2ContractError("incremental root needs release and ordinal")
        if any(v is not None for v in baseline):
            raise A2ContractError("incremental root cannot carry baseline")
        return self


@dataclass(frozen=True, slots=True)
class OccurrenceEvidence:
    """
    Bounded read-only snapshot of one exactly re-read A1 release entry.

    ``occurrence_sha256`` holds the digest of each candidate selection in
    ordinal order (primary selection first, when present, then components).
    ``members`` holds ``(fact_id, role)`` pairs in release order.
    """

    reference: ReleaseEntryRef
    members: tuple[tuple[str, str], ...]
    occurrence_sha256: tuple[str, ...]
    has_primary: bool


class ReleaseReader(Protocol):
    """Subset of the A1 release reader that A2 uses: read-only."""

    async def read_entry(self, entry: ReleaseEntryRef) -> Any:
        """Return the exact released input for one release entry."""
        ...


def evidence_from_released(
    released: Any, encode: Callable[[Any], bytes]
) -> OccurrenceEvidence:
    """
    Project a released input into :class:`OccurrenceEvidence`.

    ``released`` needs ``reference``, ``facts`` (with ``fact_id`` and
    ``role``), ``selection`` and ``components``. ``encode`` is the
    canonical selection encoder, for example
    ``CollectedSelectionCodec().encode``. The function mutates nothing.
    """
    values = tuple(
        value
        for value in (released.selection, *released.components)
        if value is not None
    )
    return OccurrenceEvidence(
        reference=released.reference,
        members=tuple((fact.fact_id, fact.role) for fact in released.facts),
        occurrence_sha256=tuple(sha256_hex(encode(value)) for value in values),
        has_primary=released.selection is not None,
    )


class ReadOnlyOccurrenceAdapter:
    """Read exact occurrence evidence through an injected A1 reader."""

    def __init__(self, reader: ReleaseReader, encode: Callable[[Any], bytes]) -> None:
        self._reader = reader
        self._encode = encode

    async def evidence(self, entry: ReleaseEntryRef) -> OccurrenceEvidence:
        """
        Re-read ``entry`` and return its evidence snapshot.

        CANDIDATE/RESEARCH: read-only, not production-ready.
        """
        released = await self._reader.read_entry(entry)
        return evidence_from_released(released, self._encode)


def _ordinal_identity(
    workset: PreparationIntakeWorkset,
    entry: ReleaseEntryRef,
    members: tuple[tuple[str, str], ...],
    ordinal: int,
) -> str:
    return "intake-selection:" + _plain_digest(
        [
            workset.scope.claim_key(),
            entry.model_dump(mode="json"),
            [list(member) for member in members],
            workset.configuration_version,
            workset.code_version,
            ordinal,
        ]
    )


def _plain_digest(parts: list[Any]) -> str:
    """Hash without a domain: it must equal the Intake identity bytes."""
    data = json.dumps(parts, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(data.encode()).hexdigest()


def verify_exact_occurrence(
    workset: PreparationIntakeWorkset,
    selection: IntakeSelection,
    evidence: OccurrenceEvidence,
    *,
    saved_selection_sha256: str,
) -> FrozenRoot:
    """
    Build a :class:`FrozenRoot` only when A1 evidence proves the ordinal.

    CANDIDATE/RESEARCH: proof-dependent, not production-ready.

    The saved selection digest must equal the digest of the re-read value
    at the proven ordinal. Role comes from the proven ordinal, never from
    caller input. Exactly one ordinal may match the selection identity.
    """
    if workset.baseline_approval is not None:
        raise A2ContractError("baseline cannot impersonate a release entry")
    if selection not in workset.selections:
        raise A2ContractError("selection is not part of the frozen workset")
    if (
        selection.entry not in workset.entries
        or selection.entry != evidence.reference
        or selection.entry.catalog != workset.scope.catalog
    ):
        raise A2ContractError("frozen workset does not match exact release")
    matches = [
        ordinal
        for ordinal in range(len(evidence.occurrence_sha256))
        if selection.result.result_id
        == _ordinal_identity(workset, selection.entry, evidence.members, ordinal)
    ]
    if len(matches) != 1:
        raise A2ContractError("ordinal identity cannot establish one role")
    ordinal = matches[0]
    if evidence.occurrence_sha256[ordinal] != saved_selection_sha256:
        raise A2ContractError("saved selection differs from re-read release")
    return FrozenRoot(
        selected=selection.result,
        workset_index=workset.selections.index(selection),
        role="primary" if evidence.has_primary and ordinal == 0 else "component",
        selection_sha256=saved_selection_sha256,
        ordinal=ordinal,
        a1_ordinal_proof=selection.result.result_id.split(":", 1)[1],
        entry=selection.entry,
    )


def baseline_root(
    workset: PreparationIntakeWorkset, index: int, *, selection_sha256: str
) -> FrozenRoot:
    """
    Build the root for one approved baseline pair at ``index``.

    CANDIDATE/RESEARCH: the caller must supply a digest it verified.
    """
    approval = workset.baseline_approval
    if approval is None:
        raise A2ContractError("workset is not an approved baseline")
    if not 0 <= index < len(workset.baseline_sources):
        raise A2ContractError("baseline index is outside the frozen scope")
    return FrozenRoot(
        selected=workset.baseline_selections[index],
        workset_index=index,
        role="baseline",
        selection_sha256=selection_sha256,
        baseline_source=workset.baseline_sources[index],
        baseline_approval=approval,
    )
