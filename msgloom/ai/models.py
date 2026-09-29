"""Immutable contracts for one bounded AI analysis attempt."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Protocol

from msgloom.contracts import AttemptIdentity, VersionRef


def _text(value: object, field: str, *, empty: bool = False) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    if not empty and (not value or not value.strip()):
        raise ValueError(f"{field} must be non-empty")


def _positive_finite(value: object, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field} must be a number")
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{field} must be finite and positive")


def _freeze_json(value: object, *, depth: int = 0) -> object:
    """Freeze already bounded IPC JSON without accepting arbitrary objects."""
    if depth > 16:
        raise ValueError("trace data nesting exceeds the closed bound")
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("trace data contains a non-finite number")
        return value
    if isinstance(value, Mapping):
        frozen: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("trace data object keys must be strings")
            frozen[key] = _freeze_json(item, depth=depth + 1)
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item, depth=depth + 1) for item in value)
    raise TypeError("trace data contains a non-JSON value")


@dataclass(frozen=True, slots=True)
class AttemptLimits:
    """Measured limits enforced around one AI attempt."""

    timeout_seconds: float
    max_input_bytes: int
    max_context_bytes: int
    max_prompt_bytes: int
    max_output_bytes: int
    max_trace_events: int
    max_trace_event_bytes: int
    max_turns: int
    max_tokens: int

    def __post_init__(self) -> None:
        _positive_finite(self.timeout_seconds, "timeout")
        values = (
            ("input bytes", self.max_input_bytes),
            ("context bytes", self.max_context_bytes),
            ("prompt bytes", self.max_prompt_bytes),
            ("output bytes", self.max_output_bytes),
            ("trace events", self.max_trace_events),
            ("trace event bytes", self.max_trace_event_bytes),
            ("turns", self.max_turns),
            ("tokens", self.max_tokens),
        )
        for name, value in values:
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"maximum {name} must be a positive integer")


@dataclass(frozen=True, slots=True)
class AnalysisAttempt:
    """Bind exact saved references to supplied bounded analysis material."""

    attempt: AttemptIdentity
    input_refs: tuple[VersionRef, ...]
    context_ref: VersionRef
    prompt_ref: VersionRef
    schema_ref: VersionRef
    model_ref: VersionRef
    input_text: str
    context_text: str
    prompt_text: str
    limits: AttemptLimits

    def __post_init__(self) -> None:
        if not isinstance(self.attempt, AttemptIdentity):
            raise TypeError("attempt must be an AttemptIdentity")
        if not isinstance(self.input_refs, tuple) or not self.input_refs:
            raise ValueError("an AI attempt requires a tuple of input references")
        refs = (
            *self.input_refs,
            self.context_ref,
            self.prompt_ref,
            self.schema_ref,
            self.model_ref,
        )
        if any(not isinstance(ref, VersionRef) for ref in refs):
            raise TypeError("AI attempt references must be VersionRef values")
        if not isinstance(self.limits, AttemptLimits):
            raise TypeError("limits must be AttemptLimits")
        _text(self.input_text, "input text")
        _text(self.context_text, "context text", empty=True)
        _text(self.prompt_text, "prompt text")
        bounded = (
            (self.input_text, self.limits.max_input_bytes, "input"),
            (self.context_text, self.limits.max_context_bytes, "context"),
            (self.prompt_text, self.limits.max_prompt_bytes, "prompt"),
        )
        for value, maximum, field in bounded:
            if len(value.encode("utf-8")) > maximum:
                raise ValueError(f"{field} exceeds configured byte limit")


class TraceKind(StrEnum):
    """Closed exposed SDK and runner diagnostic event kinds."""

    ASSISTANT_TEXT = "assistant_text"
    ASSISTANT_THINKING = "assistant_thinking"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
    SYSTEM = "system"
    RESULT = "result"
    DIAGNOSTIC = "diagnostic"


@dataclass(frozen=True, slots=True)
class TraceEvent:
    """One closed, validated SDK message fragment or runner diagnostic."""

    attempt: AttemptIdentity
    sequence: int
    kind: TraceKind
    name: str
    text: str
    data: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.attempt, AttemptIdentity):
            raise TypeError("trace attempt must be an AttemptIdentity")
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int):
            raise TypeError("trace sequence must be an integer")
        if self.sequence < 0:
            raise ValueError("trace sequence must be non-negative")
        if not isinstance(self.kind, TraceKind):
            raise TypeError("trace kind must be TraceKind")
        _text(self.name, "trace name")
        _text(self.text, "trace text", empty=True)
        if self.data is not None:
            frozen = _freeze_json(self.data)
            if not isinstance(frozen, Mapping):
                raise TypeError("trace data must be a JSON object")
            object.__setattr__(self, "data", frozen)


class TraceSink(Protocol):
    """Durably save exposed trace data before semantic output is accepted."""

    async def write(self, event: TraceEvent) -> None:
        """Persist one immutable trace event."""
        ...


class AttemptStatus(StrEnum):
    """Transport-level state before parent semantic validation."""

    COMPLETE = "complete"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


@dataclass(frozen=True, slots=True)
class AnalysisResponse:
    """Bounded structured model output awaiting semantic validation."""

    attempt: AttemptIdentity
    status: AttemptStatus
    structured_output: object | None
    trace_count: int
    failure_code: str | None = None
    failure_detail: str | None = None

    @property
    def acceptable_for_semantic_validation(self) -> bool:
        """Return whether a complete structured object is available."""
        return (
            self.status is AttemptStatus.COMPLETE
            and isinstance(self.structured_output, dict)
            and self.failure_code is None
        )
