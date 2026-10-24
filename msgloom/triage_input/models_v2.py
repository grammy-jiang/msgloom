"""
Strict ``triage_input@2`` models for the A3 snapshot over A2 v2 results.

``triage_input@2`` is a new, explicit contract. It does not extend
``triage_input@1``. The v1 models, codec and fixtures stay unchanged and
remain the only readers of v1 data. A v2 payload carries a required
``header`` and no ``schema_version`` field, and every model forbids extra
fields, so v1 code cannot read a v2 payload and v2 code cannot read v1.

All models derive from
:class:`~msgloom.a2_kedro.contracts.codec.A2Model`: frozen, strict,
``extra="forbid"``, exact text, no control characters, and pydantic error
text that hides input values.

What changed from v1:

* **Refs.** A3 binds only accepted ``prepared@2``, ``filter_result@2`` and
  ``group_result@2`` results. Each binding pairs the accepted
  :class:`~msgloom.contracts.ResultRef` with its
  :class:`~msgloom.contracts.SemanticDataRef`.
* **Selected roles.** :class:`SelectedRole` adds ``baseline-context``.
  Sources sort by accepted prepared key.
* **Held reasons.** :class:`HeldReason` adds ``filter-unknown`` for the
  ``unknown`` filter verdict.
* **Binding and snapshot digests.** The snapshot stores
  ``binding_sha256``, ``configuration_sha256`` and ``snapshot_sha256``.
  :mod:`~msgloom.triage_input.codec_v2` computes and verifies them under
  v2 digest domains.
* **Part state.** :class:`PartState` has ``pending``, ``complete`` and
  ``failed``. A saved snapshot holds only ``pending`` parts. The codec
  enforces this.
* **Limitations.** The snapshot keeps upstream limitations as a sorted
  set. It is complete if and only if there is no limitation. A
  coverage failure needs the limitation code ``coverage_incomplete``.

Units keep a count and a digest of their occurrences, not the occurrence
list. Occurrence-level coverage proof belongs to the later A3 reader.

Failure handling: a violation raises :exc:`A2ContractError` or a pydantic
``ValueError`` with fixed text. No message carries a value.

CANDIDATE/RESEARCH, PROVISIONAL: all names, limits and the
``triage_rules@2`` and ``triage_input_part@2`` schema IDs are not frozen.
See ``docs/notes/a2-v2-a3-triage-input-v2.md``.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, ClassVar, Literal

from pydantic import Field, model_validator

from msgloom.a2_kedro.contracts.codec import (
    MAX_CANONICAL_BYTES,
    A2ContractError,
    A2Model,
    Digest,
)
from msgloom.a2_kedro.contracts.header import StageHeader
from msgloom.a2_kedro.contracts.result_base import (
    check_limitations,
    sorted_unique,
)
from msgloom.a2_kedro.contracts.schema_ids import STAGE_SCHEMAS, is_accepted_key
from msgloom.contracts import (
    Limitation,
    ResultRef,
    SemanticDataRef,
    TerminalStatus,
    VersionRef,
)

TRIAGE_INPUT_V2_KIND = "triage_input"
TRIAGE_INPUT_V2_VERSION = "2"
#: PROVISIONAL: A3 rules over ``prepared@2`` need their own version.
RULE_KIND, RULE_VERSION = "triage_rules", "2"
#: PROVISIONAL: part payloads carry ``prepared@2`` content.
PART_KIND, PART_VERSION = "triage_input_part", "2"

#: Provisional bounds. They are wire decisions, not production limits.
MAX_SOURCES = 256
MAX_UNITS = 256
MAX_PARTS_PER_UNIT = 64
MAX_TOTAL_PARTS = 4096
MAX_OCCURRENCES_PER_UNIT = 100_000
MAX_HELD_REASONS = 5


class SelectedRole(StrEnum):
    """Caller-selected temporal role for one exact prepared source."""

    EARLIER_CONTEXT = "earlier-context"
    NEW_SOURCE = "new-source"
    BASELINE_CONTEXT = "baseline-context"


class HeldReason(StrEnum):
    """Mechanical reason a source is kept but withheld from AI input."""

    FILTER_EXCLUDED = "filter-excluded"
    FILTER_CONFLICT = "filter-conflict"
    FILTER_UNKNOWN = "filter-unknown"
    RULE_EXCLUDED = "rule-excluded"
    RULE_CONFLICT = "rule-conflict"


class PartState(StrEnum):
    """Handler-facing execution state for one exact saved part."""

    PENDING = "pending"
    COMPLETE = "complete"
    FAILED = "failed"


def _accepted(ref: ResultRef, kind: str) -> ResultRef:
    pair = (ref.kind, ref.schema_version)
    if pair != (kind, STAGE_SCHEMAS[kind]) or not is_accepted_key(ref.result_id):
        raise A2ContractError("reference is not an accepted result of its kind")
    return ref


def _data_matches(data: SemanticDataRef, kind: str, version: str) -> None:
    if (data.kind, data.schema_version) != (kind, version):
        raise A2ContractError("data reference has wrong kind or version")


class _Binding(A2Model):
    """Pair an accepted result ref with its saved semantic data ref."""

    KIND: ClassVar[str] = ""
    result: ResultRef
    data: SemanticDataRef

    @model_validator(mode="after")
    def _kind_matches(self) -> _Binding:
        _accepted(self.result, self.KIND)
        _data_matches(self.data, self.KIND, STAGE_SCHEMAS[self.KIND])
        return self


class PreparedBinding(_Binding):
    """Bind one accepted ``prepared@2`` result."""

    KIND: ClassVar[str] = "prepared"


class FilterBinding(_Binding):
    """Bind one accepted ``filter_result@2`` result."""

    KIND: ClassVar[str] = "filter_result"


class GroupBinding(_Binding):
    """Bind one accepted ``group_result@2`` result."""

    KIND: ClassVar[str] = "group_result"


class SelectedSource(A2Model):
    """Select the role of one exact accepted ``prepared@2`` source."""

    prepared: ResultRef
    role: SelectedRole

    @model_validator(mode="after")
    def _is_prepared(self) -> SelectedSource:
        _accepted(self.prepared, "prepared")
        return self


class TrustedVersions(A2Model):
    """Trusted versions that affect AI input semantics."""

    prompt: VersionRef
    model: VersionRef
    output_schema: VersionRef
    configuration: VersionRef


class SelectionBinding(A2Model):
    """Exact saved refs and roles selected for one input build."""

    prepared: Annotated[
        tuple[PreparedBinding, ...], Field(min_length=1, max_length=MAX_SOURCES)
    ]
    filters: Annotated[
        tuple[FilterBinding, ...], Field(min_length=1, max_length=MAX_SOURCES)
    ]
    groups: Annotated[
        tuple[GroupBinding, ...], Field(min_length=1, max_length=MAX_SOURCES)
    ]
    rule: SemanticDataRef
    roles: Annotated[
        tuple[SelectedSource, ...], Field(min_length=1, max_length=MAX_SOURCES)
    ]
    working_context: VersionRef
    versions: TrustedVersions

    @model_validator(mode="after")
    def _closed(self) -> SelectionBinding:
        _data_matches(self.rule, RULE_KIND, RULE_VERSION)
        sorted_unique([b.result.result_id for b in self.prepared], "prepared")
        sorted_unique([b.result.result_id for b in self.filters], "filter")
        sorted_unique([b.result.result_id for b in self.groups], "group")
        sorted_unique([s.prepared.result_id for s in self.roles], "role")
        wanted = {b.result for b in self.prepared}
        if {s.prepared for s in self.roles} != wanted:
            raise A2ContractError("roles differ from the prepared bindings")
        return self


class SnapshotConfig(A2Model):
    """Trusted bounded configuration with no business-policy default."""

    version: VersionRef
    remove_exact_text_repetitions: bool
    max_part_bytes: Annotated[int, Field(ge=512, le=4 * 1024 * 1024)]
    max_parts_per_unit: Annotated[int, Field(ge=1, le=MAX_PARTS_PER_UNIT)]
    max_snapshot_bytes: Annotated[int, Field(ge=4096, le=MAX_CANONICAL_BYTES)]


class HeldSource(A2Model):
    """A selected source that is kept but withheld from AI input."""

    prepared: ResultRef
    role: SelectedRole
    reasons: Annotated[
        tuple[HeldReason, ...], Field(min_length=1, max_length=MAX_HELD_REASONS)
    ]
    filter: ResultRef
    rule: SemanticDataRef

    @model_validator(mode="after")
    def _closed(self) -> HeldSource:
        _accepted(self.prepared, "prepared")
        _accepted(self.filter, "filter_result")
        _data_matches(self.rule, RULE_KIND, RULE_VERSION)
        sorted_unique([r.value for r in self.reasons], "reason")
        return self


class UnitEntry(A2Model):
    """Stable unit identity and a commitment to its occurrences."""

    unit_id: Digest
    unit_sha256: Digest
    commitment: Literal["complete-content", "retained-prefix"]
    prepared: Annotated[
        tuple[ResultRef, ...], Field(min_length=1, max_length=MAX_SOURCES)
    ]
    group: ResultRef | None = None
    occurrence_count: Annotated[int, Field(ge=1, le=MAX_OCCURRENCES_PER_UNIT)]
    occurrences_sha256: Digest

    @model_validator(mode="after")
    def _closed(self) -> UnitEntry:
        for ref in self.prepared:
            _accepted(ref, "prepared")
        if self.group is not None:
            _accepted(self.group, "group_result")
        sorted_unique([r.result_id for r in self.prepared], "unit source")
        return self


class PartEntry(A2Model):
    """Integrity reference and state of one saved bounded input part."""

    part_id: Digest
    unit_id: Digest
    unit_sha256: Digest
    part_index: Annotated[int, Field(ge=0, lt=MAX_PARTS_PER_UNIT)]
    data: SemanticDataRef
    state: PartState = PartState.PENDING

    @model_validator(mode="after")
    def _closed(self) -> PartEntry:
        _data_matches(self.data, PART_KIND, PART_VERSION)
        if self.data.data_id != self.part_id:
            raise A2ContractError("part data identity differs from part id")
        return self


class CoverageFailure(A2Model):
    """Explicit coverage left unsent because a unit cannot fit."""

    unit_id: Digest
    reason: Literal["part-count-exceeded", "irreducible-fragment"]
    first_occurrence: Annotated[int, Field(ge=0, lt=MAX_OCCURRENCES_PER_UNIT)]
    first_text_offset: Annotated[int, Field(ge=1)] | None = None
    remaining_occurrences: Annotated[int, Field(ge=1, le=MAX_OCCURRENCES_PER_UNIT)]
    remaining_sha256: Digest


class TriageInputSnapshot(A2Model):
    """Persistable ``triage_input@2`` snapshot and part manifest."""

    header: StageHeader
    binding: SelectionBinding
    binding_sha256: Digest
    configuration: SnapshotConfig
    configuration_sha256: Digest
    held: tuple[HeldSource, ...] = ()
    units: Annotated[tuple[UnitEntry, ...], Field(max_length=MAX_UNITS)] = ()
    parts: Annotated[tuple[PartEntry, ...], Field(max_length=MAX_TOTAL_PARTS)] = ()
    failures: tuple[CoverageFailure, ...] = ()
    limitations: tuple[Limitation, ...] = ()
    complete: bool
    snapshot_sha256: Digest

    @model_validator(mode="after")
    def _closed(self) -> TriageInputSnapshot:
        pair = (self.header.kind, self.header.version)
        if pair != (TRIAGE_INPUT_V2_KIND, TRIAGE_INPUT_V2_VERSION):
            raise A2ContractError("header is not triage_input@2")
        if self.configuration.version != self.binding.versions.configuration:
            raise A2ContractError("configuration version binding mismatch")
        status = TerminalStatus.COMPLETE if self.complete else TerminalStatus.INCOMPLETE
        needed = {"coverage_incomplete"} if self.failures else set()
        check_limitations(status, self.limitations, needed)
        self._check_sources()
        self._check_parts()
        return self

    def _check_sources(self) -> None:
        roles = {s.prepared: s.role for s in self.binding.roles}
        filters = {b.result for b in self.binding.filters}
        groups = {b.result for b in self.binding.groups}
        sorted_unique([h.prepared.result_id for h in self.held], "held")
        held = {h.prepared for h in self.held}
        for item in self.held:
            if roles.get(item.prepared) is not item.role:
                raise A2ContractError("held source role is invalid")
            if item.filter not in filters or item.rule != self.binding.rule:
                raise A2ContractError("held source binding is invalid")
        sorted_unique([u.unit_id for u in self.units], "unit")
        active: list[ResultRef] = []
        for unit in self.units:
            if unit.group is not None and unit.group not in groups:
                raise A2ContractError("unit group is not bound")
            active.extend(unit.prepared)
        if len(active) != len(set(active)) or set(active) & held:
            raise A2ContractError("source is active more than once or held")
        if set(active) | held != set(roles):
            raise A2ContractError("selected source coverage is incomplete")

    def _check_parts(self) -> None:
        units = {u.unit_id: u for u in self.units}
        keys = [(p.unit_id, p.part_index) for p in self.parts]
        sorted_unique(keys, "part")
        sorted_unique(sorted(p.part_id for p in self.parts), "part id")
        by_unit: dict[str, list[int]] = {}
        for part in self.parts:
            unit = units.get(part.unit_id)
            if unit is None or part.unit_sha256 != unit.unit_sha256:
                raise A2ContractError("part unit binding is invalid")
            if part.data.byte_count > self.configuration.max_part_bytes:
                raise A2ContractError("part exceeds configured byte limit")
            by_unit.setdefault(part.unit_id, []).append(part.part_index)
        limit = self.configuration.max_parts_per_unit
        for indexes in by_unit.values():
            if indexes != list(range(len(indexes))) or len(indexes) > limit:
                raise A2ContractError("part indexes are not contiguous or bounded")
        sorted_unique([f.unit_id for f in self.failures], "failure")
        for failure in self.failures:
            unit = units.get(failure.unit_id)
            if unit is None or unit.commitment != "retained-prefix":
                raise A2ContractError("failure names no incomplete unit")
            count = unit.occurrence_count
            if failure.remaining_occurrences != count - failure.first_occurrence:
                raise A2ContractError("failure remaining count is invalid")
        incomplete = {
            u.unit_id for u in self.units if u.commitment != "complete-content"
        }
        if incomplete != {f.unit_id for f in self.failures}:
            raise A2ContractError("incomplete units need exactly one failure")
