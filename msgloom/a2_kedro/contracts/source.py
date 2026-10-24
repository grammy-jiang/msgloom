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

``FrozenSourceSelection`` is the ``frozen_source_selection@1`` payload (C0-01).
It holds the ordered roots of one workset under one scope. Exactly one of
``incremental_roots`` and ``baseline_roots`` is set. It never mixes them.
The model recomputes ``selection_set_sha256`` from its canonical content.
A supplied value that differs fails validation, so a forged root, role or
index is detected. ``verify_against`` compares the roots with the frozen
Intake workset. Re-reading A1 bytes stays with the adapter below.

PROVISIONAL wire names (not frozen by the plan): ``header``, ``workset``,
``scope``, ``incremental_roots``, ``baseline_roots``,
``selection_set_sha256`` and the digest domain
``a2-frozen-source-selection@1``. See ``docs/notes/a2-v2-contract-c0-01.md``.

CANDIDATE/RESEARCH: the ordinal formula mirrors the one used by
``msgloom.preparation_pipeline.intake`` today. A production verifier must
come from a public A1 API before cutover. If Intake changes the formula,
``verify_exact_occurrence`` rejects every root.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from itertools import pairwise
from typing import Annotated, Any, Literal, Protocol

from pydantic import Field, model_validator

from msgloom.a2_kedro.contracts.codec import (
    A2ContractError,
    A2Model,
    Digest,
    Text,
    canonical_model_bytes,
    decode_model_bytes,
    domain_sha256,
    sha256_hex,
)
from msgloom.a2_kedro.contracts.header import LIMITS, StageHeader
from msgloom.contracts import ResultRef, VersionRef
from msgloom.preparation_pipeline.intake_models import (
    IntakeScope,
    IntakeSelection,
    PreparationIntakeWorkset,
)
from msgloom.sources._snapshot import CollectedSelectionCodec
from msgloom.sources.handoff_models import ReleaseEntryRef
from msgloom.sources.models import CollectedSelection
from msgloom.sources.release_models import ReleasedInput

Index = Annotated[int, Field(ge=0, le=1023)]

KIND = "frozen_source_selection"
VERSION = "1"
SELECTION_DOMAIN = "a2-frozen-source-selection@1"
_PROOF_PREFIX = "intake-selection:"


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


Roots = tuple[FrozenRoot, ...]


def _check_incremental(roots: Roots, scope: IntakeScope) -> None:
    indexes = [root.workset_index for root in roots]
    if any(a >= b for a, b in pairwise(indexes)):
        raise A2ContractError("workset indexes must be unique and ascending")
    seen: set[tuple[ReleaseEntryRef, int]] = set()
    primaries: set[ReleaseEntryRef] = set()
    for root in roots:
        entry, ordinal = root.entry, root.ordinal
        if root.role == "baseline" or entry is None or ordinal is None:
            raise A2ContractError("incremental selection holds a baseline root")
        if entry.catalog != scope.catalog:
            raise A2ContractError("root entry is outside the selection scope")
        if (entry, ordinal) in seen:
            raise A2ContractError("duplicate entry ordinal occurrence")
        seen.add((entry, ordinal))
        if root.role == "primary":
            if ordinal != 0 or entry in primaries:
                raise A2ContractError("primary role needs the only ordinal 0")
            primaries.add(entry)
        proof = root.selected.result_id.removeprefix(_PROOF_PREFIX)
        if not root.selected.result_id.startswith(_PROOF_PREFIX) or (
            proof != root.a1_ordinal_proof
        ):
            raise A2ContractError("ordinal proof differs from selection id")


def _check_baseline(roots: Roots) -> None:
    indexes = [root.workset_index for root in roots]
    if any(a >= b for a, b in pairwise(indexes)):
        raise A2ContractError("workset indexes must be unique and ascending")
    if any(root.role != "baseline" for root in roots):
        raise A2ContractError("baseline selection holds a non-baseline root")
    if len({root.baseline_approval for root in roots}) != 1:
        raise A2ContractError("baseline roots need one approval")


class FrozenSourceSelection(A2Model):
    """
    ``frozen_source_selection@1``: the ordered roots of one frozen workset.

    Exactly one of ``incremental_roots`` and ``baseline_roots`` is set and
    non-empty. Use :meth:`build` to compute ``selection_set_sha256``.
    """

    header: StageHeader = Field(
        default_factory=lambda: StageHeader(kind=KIND, version=VERSION)
    )
    workset: ResultRef
    scope: IntakeScope
    incremental_roots: Roots | None = None
    baseline_roots: Roots | None = None
    selection_set_sha256: Digest

    @model_validator(mode="after")
    def _closed(self) -> FrozenSourceSelection:
        if (self.header.kind, self.header.version) != (KIND, VERSION):
            raise A2ContractError("header is not frozen_source_selection@1")
        if (self.workset.kind, self.workset.schema_version) != (
            "preparation_intake_workset",
            "1",
        ):
            raise A2ContractError("selection workset schema mismatch")
        chosen = [r for r in (self.incremental_roots, self.baseline_roots) if r]
        both = self.incremental_roots is not None and self.baseline_roots is not None
        if both or len(chosen) != 1:
            raise A2ContractError("need exactly one non-empty root set")
        if len(chosen[0]) > LIMITS["max_roots"]:
            raise A2ContractError("root count exceeds the workset bound")
        if self.incremental_roots:
            _check_incremental(self.incremental_roots, self.scope)
        elif self.baseline_roots:
            _check_baseline(self.baseline_roots)
        if self.selection_set_sha256 != self.content_sha256():
            raise A2ContractError("selection digest does not match content")
        return self

    def content_sha256(self) -> str:
        """Return the digest of every field except the stored digest."""
        content = self.model_dump(mode="json", exclude={"selection_set_sha256"})
        return domain_sha256(SELECTION_DOMAIN, content)

    @classmethod
    def build(
        cls,
        workset: ResultRef,
        scope: IntakeScope,
        *,
        incremental_roots: Roots | None = None,
        baseline_roots: Roots | None = None,
    ) -> FrozenSourceSelection:
        """Build a selection and compute its digest; never accept one."""
        values = {
            "workset": workset,
            "scope": scope,
            "incremental_roots": incremental_roots,
            "baseline_roots": baseline_roots,
        }
        draft = cls.model_construct(
            header=StageHeader(kind=KIND, version=VERSION),
            selection_set_sha256="0" * 64,
            **values,
        )
        digest = draft.content_sha256()
        return cls(selection_set_sha256=digest, **values)

    def roots(self) -> Roots:
        """Return the set roots in workset order."""
        return self.incremental_roots or self.baseline_roots or ()

    def verify_against(self, workset: PreparationIntakeWorkset) -> None:
        """
        Prove that every root equals the frozen Intake workset content.

        Raise :exc:`A2ContractError` for another scope, a baseline
        mismatch, or a root that is not the workset item at its index.
        """
        if workset.scope != self.scope:
            raise A2ContractError("selection scope differs from workset")
        if (workset.baseline_approval is not None) != bool(self.baseline_roots):
            raise A2ContractError("selection mode differs from workset")
        for root in self.roots():
            index = root.workset_index
            if root.role == "baseline":
                same = (
                    index < len(workset.baseline_sources)
                    and workset.baseline_selections[index] == root.selected
                    and workset.baseline_sources[index] == root.baseline_source
                    and workset.baseline_approval == root.baseline_approval
                )
            else:
                same = (
                    index < len(workset.selections)
                    and workset.selections[index].result == root.selected
                    and workset.selections[index].entry == root.entry
                )
            if not same:
                raise A2ContractError("root differs from the frozen workset")

    def encode(self) -> bytes:
        """Return the bounded canonical bytes of this record."""
        return canonical_model_bytes(self)

    @classmethod
    def decode(cls, data: bytes) -> FrozenSourceSelection:
        """Strictly decode canonical bytes; reject anything else."""
        return decode_model_bytes(cls, data)


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


def evidence_from_released(released: ReleasedInput) -> OccurrenceEvidence:
    """
    Project a real :class:`ReleasedInput` into :class:`OccurrenceEvidence`.

    The projection always uses the A1 ``CollectedSelectionCodec``. A caller
    cannot supply an encoder, so a caller cannot choose the bytes that are
    hashed. A value that is not a ``ReleasedInput`` raises
    :exc:`A2ContractError`. Two equal occurrence digests are ambiguous and
    also raise. The function mutates nothing.
    """
    if not isinstance(released, ReleasedInput):
        raise A2ContractError("released input is not an A1 ReleasedInput")
    codec = CollectedSelectionCodec()
    values = tuple(
        value
        for value in (released.selection, *released.components)
        if value is not None
    )
    digests = tuple(sha256_hex(codec.encode(value)) for value in values)
    if len(set(digests)) != len(digests):
        raise A2ContractError("release repeats one selection occurrence")
    return OccurrenceEvidence(
        reference=released.reference,
        members=tuple((fact.fact_id, fact.role) for fact in released.facts),
        occurrence_sha256=digests,
        has_primary=released.selection is not None,
    )


class ReadOnlyOccurrenceAdapter:
    """Read exact occurrence evidence through an injected A1 reader."""

    def __init__(self, reader: ReleaseReader) -> None:
        self._reader = reader

    async def evidence(self, entry: ReleaseEntryRef) -> OccurrenceEvidence:
        """
        Re-read ``entry`` and return its evidence snapshot.

        The reader must return a real ``ReleasedInput`` whose reference
        equals ``entry``. Any other answer raises :exc:`A2ContractError`.

        CANDIDATE/RESEARCH: read-only, not production-ready.
        """
        released = await self._reader.read_entry(entry)
        evidence = evidence_from_released(released)
        if evidence.reference != entry:
            raise A2ContractError("reader answered a different release entry")
        return evidence


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


def verify_baseline_selection(
    workset: PreparationIntakeWorkset, index: int, value: CollectedSelection
) -> FrozenRoot:
    """
    Build a baseline root only from a real :class:`CollectedSelection`.

    The digest comes from the A1 ``CollectedSelectionCodec``, never from the
    caller. The value must name the approved source at ``index`` and must
    reproduce the saved baseline selection identity.

    CANDIDATE/RESEARCH: the identity formula mirrors the historical
    baseline admission code. A public A1 verifier is still missing.
    """
    if not isinstance(value, CollectedSelection):
        raise A2ContractError("baseline value is not a CollectedSelection")
    if workset.baseline_approval is None:
        raise A2ContractError("workset is not an approved baseline")
    if not 0 <= index < len(workset.baseline_sources):
        raise A2ContractError("baseline index is outside the frozen scope")
    if value.source != workset.baseline_sources[index]:
        raise A2ContractError("baseline selection names another source")
    expected = "intake-baseline-selection:" + _plain_digest(
        [
            workset.scope.claim_key(),
            asdict(value.selection),
            workset.configuration_version,
            workset.code_version,
        ]
    )
    if workset.baseline_selections[index].result_id != expected:
        raise A2ContractError("baseline selection identity does not match")
    return baseline_root(
        workset,
        index,
        selection_sha256=sha256_hex(CollectedSelectionCodec().encode(value)),
    )
