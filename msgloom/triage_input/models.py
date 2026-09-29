"""Immutable contracts for bounded Phase 1 triage input."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from msgloom.contracts import ResultRef, SemanticDataRef, VersionRef
from msgloom.preparation.filtering import FilterConfig, FilterResult
from msgloom.preparation.grouping import GroupResult
from msgloom.preparation.records import PreparedRecord
from msgloom.triage.rules import TriageRuleEvaluation

MAX_SELECTED_SOURCES = 256
MAX_UNITS = 256
MAX_PARTS_PER_UNIT = 512
MAX_FRAGMENT_PATH = 32
MAX_OCCURRENCES_PER_UNIT = 100_000
MAX_TOTAL_OCCURRENCES = 200_000
MAX_TOTAL_PARTS = MAX_UNITS * MAX_PARTS_PER_UNIT


class _FrozenModel(BaseModel):
    """Reject coercion, mutation, and unknown fields at the input boundary."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")


class SourceRole(StrEnum):
    """Caller-selected temporal role for one exact prepared source."""

    EARLIER_CONTEXT = "earlier-context"
    NEW_SOURCE = "new-source"


class HeldReason(StrEnum):
    """Mechanical reason a source is retained but withheld from ordinary AI input."""

    FILTER_EXCLUDED = "filter-excluded"
    FILTER_CONFLICT = "filter-conflict"
    RULE_EXCLUDED = "rule-excluded"
    RULE_CONFLICT = "rule-conflict"


class FragmentKind(StrEnum):
    """Typed structural fragment; source strings always remain data."""

    CONTAINER = "container"
    SCALAR = "scalar"
    TEXT = "text"
    REPETITION = "repetition"


class ContainerKind(StrEnum):
    """JSON-compatible container shape retained without flattening."""

    OBJECT = "object"
    ARRAY = "array"


class PartState(StrEnum):
    """Handler-facing execution state for one exact saved part."""

    PENDING = "pending"
    COMPLETE = "complete"
    FAILED = "failed"


PathSegment = str | int
ScalarValue = str | int | float | bool | None


class SavedPreparedBinding(_FrozenModel):
    """Bind an exact saved prepared result/data reference to its reloaded value."""

    result_ref: ResultRef
    data_ref: SemanticDataRef
    record: PreparedRecord


class SavedFilterBinding(_FrozenModel):
    """Bind an exact saved filter result/data reference to its reloaded value."""

    result_ref: ResultRef
    data_ref: SemanticDataRef
    result: FilterResult


class SavedGroupBinding(_FrozenModel):
    """Bind an exact saved grouping result/data reference to its reloaded value."""

    result_ref: ResultRef
    data_ref: SemanticDataRef
    result: GroupResult


class SavedRuleBinding(_FrozenModel):
    """Bind exact saved deterministic A3 evaluation to its reloaded value."""

    result_ref: ResultRef
    data_ref: SemanticDataRef
    evaluation: TriageRuleEvaluation


class SourceRoleBinding(_FrozenModel):
    """Select the earlier-context/new-source role for one exact source."""

    source_ref: VersionRef
    role: SourceRole


class TrustedInputVersions(_FrozenModel):
    """Trusted versions affecting AI input semantics and interpretation."""

    prompt: VersionRef
    model: VersionRef
    output_schema: VersionRef
    configuration: VersionRef


class RepetitionPolicy(_FrozenModel):
    """Explicitly authorize only exact text repetition removal."""

    remove_exact_text_repetitions: bool = False


class SplitBudget(_FrozenModel):
    """Finite serialized-byte and part-count bounds for each semantic unit."""

    max_part_bytes: Annotated[int, Field(ge=512, le=4 * 1024 * 1024)]
    max_parts_per_unit: Annotated[int, Field(ge=1, le=MAX_PARTS_PER_UNIT)]


class TriageInputConfig(_FrozenModel):
    """Trusted bounded input configuration with no business-policy defaults."""

    version: VersionRef
    repetition: RepetitionPolicy
    split: SplitBudget
    max_snapshot_bytes: Annotated[int, Field(ge=4096, le=64 * 1024 * 1024)]


class TriageSelection(_FrozenModel):
    """Exact saved A2/A3 bindings selected for one pure input build."""

    prepared: Annotated[
        tuple[SavedPreparedBinding, ...],
        Field(min_length=1, max_length=MAX_SELECTED_SOURCES),
    ]
    filter_config: FilterConfig
    filters: Annotated[
        tuple[SavedFilterBinding, ...],
        Field(min_length=1, max_length=MAX_SELECTED_SOURCES),
    ]
    groups: Annotated[
        tuple[SavedGroupBinding, ...],
        Field(min_length=1, max_length=MAX_SELECTED_SOURCES),
    ]
    rules: SavedRuleBinding
    roles: Annotated[
        tuple[SourceRoleBinding, ...],
        Field(min_length=1, max_length=MAX_SELECTED_SOURCES),
    ]
    working_context_ref: VersionRef
    versions: TrustedInputVersions

    @model_validator(mode="after")
    def _unique_surface_references(self) -> TriageSelection:
        prepared = tuple(item.record.source for item in self.prepared)
        filters = tuple(item.result.input for item in self.filters)
        roles = tuple(item.source_ref for item in self.roles)
        for values in (prepared, filters, roles):
            if len(values) != len(set(values)):
                raise ValueError("triage selection source bindings must be unique")
        return self


class HeldSource(_FrozenModel):
    """Retain a selected source withheld from ordinary semantic input."""

    source_ref: VersionRef
    role: SourceRole
    reasons: Annotated[tuple[HeldReason, ...], Field(min_length=1, max_length=4)]
    filter_ref: SemanticDataRef
    rule_ref: SemanticDataRef


class RepetitionTarget(_FrozenModel):
    """Point a removed exact occurrence to the retained source/path occurrence."""

    source_ref: VersionRef
    namespace: str
    path: Annotated[tuple[PathSegment, ...], Field(max_length=MAX_FRAGMENT_PATH)]


class SemanticFragment(_FrozenModel):
    """One structured, path-addressed source-data fragment."""

    occurrence_id: str
    source_ref: VersionRef
    role: SourceRole
    namespace: str
    path: Annotated[tuple[PathSegment, ...], Field(max_length=MAX_FRAGMENT_PATH)]
    kind: FragmentKind
    value: ScalarValue = None
    container_kind: ContainerKind | None = None
    container_length: int | None = None
    text_start: int | None = None
    text_end: int | None = None
    repetition_of: RepetitionTarget | None = None

    @model_validator(mode="after")
    def _shape_matches_kind(self) -> SemanticFragment:
        if self.kind is FragmentKind.CONTAINER:
            if self.container_kind is None or self.container_length is None:
                raise ValueError("container fragment requires shape metadata")
            if self.container_length < 0:
                raise ValueError("container length must be non-negative")
            if any(
                value is not None
                for value in (
                    self.value,
                    self.text_start,
                    self.text_end,
                    self.repetition_of,
                )
            ):
                raise ValueError("container fragment carries only shape metadata")
            return self
        if self.kind is FragmentKind.TEXT:
            if not isinstance(self.value, str):
                raise ValueError("text fragment requires string data")
            if self.text_start is None or self.text_end is None:
                raise ValueError("text fragment requires exact character range")
            if self.text_start < 0 or self.text_end < self.text_start:
                raise ValueError("text fragment range must be ordered")
            if len(self.value) != self.text_end - self.text_start:
                raise ValueError("text fragment range must match text length")
            if self.container_kind is not None or self.repetition_of is not None:
                raise ValueError("text fragment cannot carry container/repetition data")
            return self
        if self.kind is FragmentKind.REPETITION:
            if self.repetition_of is None:
                raise ValueError("repetition fragment requires retained target")
            if any(
                value is not None
                for value in (
                    self.value,
                    self.container_kind,
                    self.container_length,
                    self.text_start,
                    self.text_end,
                )
            ):
                raise ValueError("repetition fragment carries only its target")
            return self
        if isinstance(self.value, str):
            raise TypeError("string scalar data must use a text fragment")
        if any(
            value is not None
            for value in (
                self.container_kind,
                self.container_length,
                self.text_start,
                self.text_end,
                self.repetition_of,
            )
        ):
            raise ValueError("scalar fragment cannot carry other fragment metadata")
        return self


class OccurrenceManifest(_FrozenModel):
    """Expected identity and coverage for one pre-split semantic occurrence."""

    occurrence_id: str
    source_ref: VersionRef
    role: SourceRole
    namespace: str
    path: Annotated[tuple[PathSegment, ...], Field(max_length=MAX_FRAGMENT_PATH)]
    kind: FragmentKind
    text_length: int | None = None


class UnitManifest(_FrozenModel):
    """Stable unit authority and verifiable retained-content commitment."""

    unit_id: str
    unit_hash: str
    commitment: Literal["complete-content", "retained-prefix"]
    source_refs: Annotated[
        tuple[VersionRef, ...], Field(min_length=1, max_length=MAX_SELECTED_SOURCES)
    ]
    group_ref: SemanticDataRef | None
    occurrences: Annotated[
        tuple[OccurrenceManifest, ...],
        Field(min_length=1, max_length=MAX_OCCURRENCES_PER_UNIT),
    ]

    @model_validator(mode="after")
    def _unique_occurrences(self) -> UnitManifest:
        identities = tuple(item.occurrence_id for item in self.occurrences)
        if len(identities) != len(set(identities)):
            raise ValueError("unit occurrence identities must be unique")
        return self


class InputPart(_FrozenModel):
    """One self-describing bounded structured AI-input part."""

    part_id: str
    unit_id: str
    unit_hash: str
    part_index: int
    working_context_ref: VersionRef
    versions: TrustedInputVersions
    fragments: Annotated[
        tuple[SemanticFragment, ...], Field(min_length=1, max_length=20_000)
    ]


class InputPartReference(_FrozenModel):
    """Integrity reference and exact typed value for canonical saved part bytes."""

    reference: SemanticDataRef
    part: InputPart
    state: PartState = PartState.PENDING


class CoverageFailure(_FrozenModel):
    """Bounded explicit coverage left unsent because a unit cannot fit."""

    unit_id: str
    reason: Literal["part-count-exceeded", "irreducible-fragment"]
    first_occurrence: int
    first_text_offset: int | None = None
    remaining_occurrences: int
    remaining_digest: str


class TriageInputSnapshot(_FrozenModel):
    """Persistable deterministic triage-input snapshot and part manifest."""

    schema_version: Literal["1"] = "1"
    selection_hash: str
    selection_binding_hash: str
    configuration_hash: str
    snapshot_hash: str
    configuration: TriageInputConfig
    working_context_ref: VersionRef
    versions: TrustedInputVersions
    prepared_refs: tuple[SemanticDataRef, ...]
    filter_refs: tuple[SemanticDataRef, ...]
    group_refs: tuple[SemanticDataRef, ...]
    rule_ref: SemanticDataRef
    held: tuple[HeldSource, ...]
    units: Annotated[tuple[UnitManifest, ...], Field(max_length=MAX_UNITS)]
    selected_sources: Annotated[
        tuple[SourceRoleBinding, ...],
        Field(min_length=1, max_length=MAX_SELECTED_SOURCES),
    ]
    parts: Annotated[tuple[InputPartReference, ...], Field(max_length=MAX_TOTAL_PARTS)]
    complete: bool
    failures: tuple[CoverageFailure, ...]
