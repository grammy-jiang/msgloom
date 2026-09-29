"""Closed configuration and replay plans for the finite A2 producer."""

from __future__ import annotations

import math
from enum import StrEnum

from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticSerializationError

from msgloom.contracts import AttemptIdentity, ResultRef, VersionRef
from msgloom.preparation import (
    DocumentFormat,
    ParserConfig,
    ParserIdentity,
    ParserLimits,
)
from msgloom.preparation.filtering import FilterConfig


class PreparationMode(StrEnum):
    """Select current saved A1 versions or replay a captured selection."""

    LIVE = "live"
    REPLAY = "replay"


class _FrozenModel(BaseModel):
    """Reject coercion, mutation, and undeclared producer settings."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")


class ParserProfile(_FrozenModel):
    """Trusted parser identity, profile, and limits for one exact format."""

    format: DocumentFormat
    parser: ParserIdentity
    config: ParserConfig
    limits: ParserLimits


class SelectionPlan(_FrozenModel):
    """Bind one request target to live capture or one exact replay result."""

    source: VersionRef
    replay_result: ResultRef | None = None
    replay_selection: VersionRef | None = None

    @model_validator(mode="after")
    def _replay_pair(self) -> SelectionPlan:
        if (self.replay_result is None) != (self.replay_selection is None):
            raise ValueError("replay result and selection reference must be paired")
        if self.replay_result is not None and (
            self.replay_result.kind != "collected_selection"
            or self.replay_result.schema_version != "1"
        ):
            raise ValueError("replay result must reference collected_selection@1")
        if self.replay_selection is not None and (
            self.replay_selection.kind != "collected_selection"
        ):
            raise ValueError("replay selection reference kind is invalid")
        return self


class PreparationPlan(_FrozenModel):
    """Explicit finite work plan resolved from trusted caller configuration."""

    mode: PreparationMode
    attempt: AttemptIdentity
    selections: tuple[SelectionPlan, ...]
    filter_config: FilterConfig
    parser_profiles: tuple[ParserProfile, ...]
    configuration_version: str
    code_version: str
    execution_timeout_seconds: float = 120.0
    claim_lease_seconds: float = 180.0
    max_records: int = 100
    max_total_selected_bytes: int = 64 * 1024 * 1024
    max_derived_bytes: int = 16 * 1024 * 1024
    max_total_derived_bytes: int = 32 * 1024 * 1024
    max_total_parser_output_bytes: int = 32 * 1024 * 1024

    @field_validator("configuration_version", "code_version")
    @classmethod
    def _nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("producer versions must be non-empty")
        return value

    @field_validator(
        "max_records",
        "max_total_selected_bytes",
        "max_derived_bytes",
        "max_total_derived_bytes",
        "max_total_parser_output_bytes",
    )
    @classmethod
    def _positive_integer(cls, value: int) -> int:
        if isinstance(value, bool) or value < 1:
            raise ValueError("producer integer bounds must be positive")
        return value

    @field_validator("execution_timeout_seconds", "claim_lease_seconds")
    @classmethod
    def _positive_finite(cls, value: float) -> float:
        if not math.isfinite(value) or value <= 0:
            raise ValueError("producer time bounds must be positive and finite")
        return value

    @model_validator(mode="after")
    def _closed_plan(self) -> PreparationPlan:
        if not self.selections or len(self.selections) > self.max_records:
            raise ValueError("selection count is outside configured bounds")
        sources = tuple(item.source for item in self.selections)
        if len(sources) != len(set(sources)):
            raise ValueError("selection plan contains duplicate source versions")
        replay = self.mode is PreparationMode.REPLAY
        if any((item.replay_result is not None) != replay for item in self.selections):
            raise ValueError("selection entries do not match preparation mode")
        formats = tuple(item.format for item in self.parser_profiles)
        if len(formats) != len(set(formats)):
            raise ValueError("parser profiles must have unique formats")
        if self.max_derived_bytes > self.max_total_derived_bytes:
            raise ValueError(
                "per-artifact derived bound exceeds aggregate derived bound"
            )
        if self.claim_lease_seconds <= self.execution_timeout_seconds + 1.0:
            raise ValueError("claim lease must exceed execution budget by one second")
        return self

    def profile_for(self, format_: DocumentFormat) -> ParserProfile | None:
        """Return the trusted profile for a detected format, if configured."""
        return next(
            (item for item in self.parser_profiles if item.format is format_),
            None,
        )


def revalidate_plan(value: PreparationPlan) -> PreparationPlan:
    """Reconstruct every nested trusted-plan value through strict JSON validation."""
    if not isinstance(value, PreparationPlan):
        raise TypeError("preparation plan has the wrong public type")
    try:
        payload = value.model_dump_json(
            round_trip=True,
            warnings="error",
        )
        return PreparationPlan.model_validate_json(payload, strict=True)
    except (PydanticSerializationError, ValidationError, TypeError, ValueError):
        raise ValueError("preparation plan failed closed validation") from None
