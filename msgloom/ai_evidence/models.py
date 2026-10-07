"""Immutable durable envelopes for exposed AI execution evidence."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from msgloom.ai import AnalysisAttempt, AnalysisResponse, TraceEvent, TrustedPolicy
from msgloom.contracts import ResultRef

_MAX_DEPTH = 20


def _freeze_json(value: object, depth: int = 0) -> object:
    """Freeze strict finite JSON so evidence cannot mutate after validation."""
    if depth > _MAX_DEPTH:
        raise ValueError("resolved schema exceeds the nesting bound")
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("resolved schema contains a non-finite number")
        return value
    if isinstance(value, Mapping):
        frozen: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("resolved schema keys must be strings")
            frozen[key] = _freeze_json(item, depth + 1)
        return MappingProxyType(frozen)
    if isinstance(value, (tuple, list)):
        return tuple(_freeze_json(item, depth + 1) for item in value)
    raise TypeError("resolved schema contains a non-JSON value")


@dataclass(frozen=True, slots=True)
class RequestEvidence:
    """Exact public AI request plus explicitly resolved trusted policy values."""

    request: AnalysisAttempt
    resolved_schema: Mapping[str, object]
    resolved_model: str
    required_inputs: tuple[ResultRef, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.request, AnalysisAttempt):
            raise TypeError("request evidence requires AnalysisAttempt")
        if not isinstance(self.resolved_schema, Mapping) or not self.resolved_schema:
            raise ValueError("request evidence requires a resolved schema")
        frozen = _freeze_json(self.resolved_schema)
        if not isinstance(frozen, Mapping):
            raise TypeError("resolved schema must be a JSON object")
        object.__setattr__(self, "resolved_schema", frozen)
        if not isinstance(self.resolved_model, str) or not self.resolved_model.strip():
            raise ValueError("request evidence requires a resolved model")
        if not isinstance(self.required_inputs, tuple) or not self.required_inputs:
            raise ValueError("request evidence requires durable input references")
        if any(not isinstance(item, ResultRef) for item in self.required_inputs):
            raise TypeError("required inputs must be ResultRef values")
        if len(set(self.required_inputs)) != len(self.required_inputs):
            raise ValueError("required inputs must be unique")

    @classmethod
    def bind(
        cls,
        request: AnalysisAttempt,
        policy: TrustedPolicy,
        required_inputs: tuple[ResultRef, ...],
    ) -> RequestEvidence:
        """Bind public request data to supplied trusted schema and model policy."""
        if not isinstance(request, AnalysisAttempt):
            raise TypeError("request evidence requires AnalysisAttempt")
        if not isinstance(policy, TrustedPolicy):
            raise TypeError("request evidence requires TrustedPolicy")
        schema = policy.schema_for(request.schema_ref)
        model = policy.models.get(request.model_ref)
        if schema is None or model is None:
            raise ValueError("trusted policy does not resolve request references")
        return cls(
            request=request,
            resolved_schema=schema,
            resolved_model=model,
            required_inputs=required_inputs,
        )


@dataclass(frozen=True, slots=True)
class TraceEvidence:
    """One exposed trace event bound to its saved request evidence."""

    request_ref: ResultRef
    event: TraceEvent

    def __post_init__(self) -> None:
        if not isinstance(self.request_ref, ResultRef):
            raise TypeError("trace request reference must be ResultRef")
        if not isinstance(self.event, TraceEvent):
            raise TypeError("trace evidence requires TraceEvent")
        if (
            self.request_ref.kind != "ai_request"
            or self.request_ref.schema_version != "1"
        ):
            raise ValueError("trace evidence requires ai_request@1 lineage")


@dataclass(frozen=True, slots=True)
class TerminalEvidence:
    """Transport terminal evidence; semantic triage acceptance remains external."""

    request_ref: ResultRef
    trace_refs: tuple[ResultRef, ...]
    response: AnalysisResponse
    transport_eligible: bool
    triage_semantics_accepted: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.request_ref, ResultRef):
            raise TypeError("terminal request reference must be ResultRef")
        if not isinstance(self.trace_refs, tuple):
            raise TypeError("terminal trace references must be a tuple")
        if any(not isinstance(item, ResultRef) for item in self.trace_refs):
            raise TypeError("terminal trace references must be ResultRef values")
        if not isinstance(self.response, AnalysisResponse):
            raise TypeError("terminal response must be AnalysisResponse")
        if (
            self.request_ref.kind != "ai_request"
            or self.request_ref.schema_version != "1"
        ):
            raise ValueError("terminal evidence requires ai_request@1 lineage")
        if any(
            item.kind != "ai_trace" or item.schema_version != "1"
            for item in self.trace_refs
        ):
            raise ValueError("terminal evidence requires ai_trace@1 references")
        if len(set(self.trace_refs)) != len(self.trace_refs):
            raise ValueError("terminal trace references must be unique")
        if self.response.trace_count != len(self.trace_refs):
            raise ValueError("terminal trace count must match durable references")
        if not isinstance(self.transport_eligible, bool):
            raise TypeError("transport eligibility must be boolean")
        if self.transport_eligible != self.response.acceptable_for_semantic_validation:
            raise ValueError("transport eligibility must match terminal response")
        if self.triage_semantics_accepted is not False:
            raise ValueError("AI evidence cannot accept triage semantics")
