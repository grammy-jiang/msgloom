"""Strict JSON helpers for AI evidence codecs."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import fields

from msgloom.ai import (
    AnalysisAttempt,
    AnalysisResponse,
    AttemptLimits,
    AttemptStatus,
    TraceEvent,
    TraceKind,
)
from msgloom.contracts import AttemptIdentity, ResultRef, VersionRef

_MAX_DEPTH = 20


class EvidenceCodecError(ValueError):
    """Public opaque codec failure without embedded evidence bytes."""


def fail() -> EvidenceCodecError:
    """Return the uniform privacy-safe codec error."""
    return EvidenceCodecError("invalid AI evidence payload")


def json_value(value: object, depth: int = 0) -> object:
    """Copy strict finite JSON while enforcing a fixed nesting bound."""
    if depth > _MAX_DEPTH:
        raise fail()
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise fail()
        return value
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str) or key in result:
                raise fail()
            result[key] = json_value(item, depth + 1)
        return result
    if isinstance(value, (tuple, list)):
        return [json_value(item, depth + 1) for item in value]
    raise fail()


def canonical(value: object, maximum: int) -> bytes:
    """Encode canonical UTF-8 JSON under one fixed codec ceiling."""
    try:
        payload = json.dumps(
            json_value(value),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError):
        raise fail() from None
    if not payload or len(payload) > maximum:
        raise fail()
    return payload


def _pairs(items: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in items:
        if key in result:
            raise fail()
        result[key] = value
    return result


def load(payload: bytes, maximum: int) -> dict[str, object]:
    """Decode only canonical JSON objects with no duplicate keys."""
    if not isinstance(payload, bytes) or not payload or len(payload) > maximum:
        raise fail()
    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=lambda _value: (_ for _ in ()).throw(fail()),
        )
    except (EvidenceCodecError, UnicodeError, json.JSONDecodeError):
        raise fail() from None
    if not isinstance(value, dict) or canonical(value, maximum) != payload:
        raise fail()
    return value


def exact(value: Mapping[str, object], names: tuple[str, ...]) -> None:
    """Require an exact closed object shape."""
    if set(value) != set(names):
        raise fail()


def version_ref(value: object) -> dict[str, str]:
    """Revalidate and encode one exact version reference."""
    if not isinstance(value, VersionRef):
        raise fail()
    try:
        rebuilt = VersionRef(value.kind, value.identity, value.version)
    except (AttributeError, TypeError, ValueError):
        raise fail() from None
    return {
        "kind": rebuilt.kind,
        "identity": rebuilt.identity,
        "version": rebuilt.version,
    }


def decode_version_ref(value: object) -> VersionRef:
    """Decode one closed version reference."""
    if not isinstance(value, dict):
        raise fail()
    exact(value, ("kind", "identity", "version"))
    try:
        return VersionRef(value["kind"], value["identity"], value["version"])  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise fail() from None


def result_ref(value: object) -> dict[str, str]:
    """Revalidate and encode one stage-result reference."""
    if not isinstance(value, ResultRef):
        raise fail()
    try:
        rebuilt = ResultRef(value.result_id, value.kind, value.schema_version)
    except (AttributeError, TypeError, ValueError):
        raise fail() from None
    return {
        "result_id": rebuilt.result_id,
        "kind": rebuilt.kind,
        "schema_version": rebuilt.schema_version,
    }


def decode_result_ref(value: object) -> ResultRef:
    """Decode one closed stage-result reference."""
    if not isinstance(value, dict):
        raise fail()
    exact(value, ("result_id", "kind", "schema_version"))
    try:
        return ResultRef(
            value["result_id"],
            value["kind"],
            value["schema_version"],  # type: ignore[arg-type]
        )
    except (TypeError, ValueError):
        raise fail() from None


def limits(value: object) -> dict[str, object]:
    """Revalidate and encode attempt limits."""
    if not isinstance(value, AttemptLimits):
        raise fail()
    try:
        rebuilt = AttemptLimits(
            **{
                field.name: getattr(value, field.name)
                for field in fields(AttemptLimits)
            }
        )
    except (AttributeError, TypeError, ValueError):
        raise fail() from None
    return {field.name: getattr(rebuilt, field.name) for field in fields(AttemptLimits)}


def decode_limits(value: object) -> AttemptLimits:
    """Decode strict attempt limits."""
    if not isinstance(value, dict):
        raise fail()
    names = tuple(field.name for field in fields(AttemptLimits))
    exact(value, names)
    try:
        return AttemptLimits(**value)
    except (TypeError, ValueError):
        raise fail() from None


def attempt(value: object) -> dict[str, object]:
    """Reconstruct an AnalysisAttempt so bypassed nested values are rejected."""
    if not isinstance(value, AnalysisAttempt):
        raise fail()
    try:
        rebuilt = AnalysisAttempt(
            attempt=AttemptIdentity(value.attempt.value),
            input_refs=tuple(
                VersionRef(item.kind, item.identity, item.version)
                for item in value.input_refs
            ),
            context_ref=VersionRef(
                value.context_ref.kind,
                value.context_ref.identity,
                value.context_ref.version,
            ),
            prompt_ref=VersionRef(
                value.prompt_ref.kind,
                value.prompt_ref.identity,
                value.prompt_ref.version,
            ),
            schema_ref=VersionRef(
                value.schema_ref.kind,
                value.schema_ref.identity,
                value.schema_ref.version,
            ),
            model_ref=VersionRef(
                value.model_ref.kind, value.model_ref.identity, value.model_ref.version
            ),
            input_text=value.input_text,
            context_text=value.context_text,
            prompt_text=value.prompt_text,
            limits=AttemptLimits(
                **{
                    field.name: getattr(value.limits, field.name)
                    for field in fields(AttemptLimits)
                }
            ),
        )
    except (AttributeError, TypeError, ValueError):
        raise fail() from None
    return {
        "attempt": rebuilt.attempt.value,
        "input_refs": [version_ref(item) for item in rebuilt.input_refs],
        "context_ref": version_ref(rebuilt.context_ref),
        "prompt_ref": version_ref(rebuilt.prompt_ref),
        "schema_ref": version_ref(rebuilt.schema_ref),
        "model_ref": version_ref(rebuilt.model_ref),
        "input_text": rebuilt.input_text,
        "context_text": rebuilt.context_text,
        "prompt_text": rebuilt.prompt_text,
        "limits": limits(rebuilt.limits),
    }


def decode_attempt(value: object) -> AnalysisAttempt:
    """Decode one exact public AnalysisAttempt."""
    if not isinstance(value, dict):
        raise fail()
    names = (
        "attempt",
        "input_refs",
        "context_ref",
        "prompt_ref",
        "schema_ref",
        "model_ref",
        "input_text",
        "context_text",
        "prompt_text",
        "limits",
    )
    exact(value, names)
    refs = value["input_refs"]
    if not isinstance(refs, list):
        raise fail()
    try:
        return AnalysisAttempt(
            attempt=AttemptIdentity(value["attempt"]),  # type: ignore[arg-type]
            input_refs=tuple(decode_version_ref(item) for item in refs),
            context_ref=decode_version_ref(value["context_ref"]),
            prompt_ref=decode_version_ref(value["prompt_ref"]),
            schema_ref=decode_version_ref(value["schema_ref"]),
            model_ref=decode_version_ref(value["model_ref"]),
            input_text=value["input_text"],  # type: ignore[arg-type]
            context_text=value["context_text"],  # type: ignore[arg-type]
            prompt_text=value["prompt_text"],  # type: ignore[arg-type]
            limits=decode_limits(value["limits"]),
        )
    except (TypeError, ValueError):
        raise fail() from None


def event(value: object) -> dict[str, object]:
    """Reconstruct and encode one exposed trace event."""
    if not isinstance(value, TraceEvent):
        raise fail()
    try:
        rebuilt = TraceEvent(
            attempt=AttemptIdentity(value.attempt.value),
            sequence=value.sequence,
            kind=TraceKind(value.kind),
            name=value.name,
            text=value.text,
            data=None if value.data is None else dict(value.data),
        )
    except (AttributeError, TypeError, ValueError):
        raise fail() from None
    return {
        "attempt": rebuilt.attempt.value,
        "sequence": rebuilt.sequence,
        "kind": rebuilt.kind.value,
        "name": rebuilt.name,
        "text": rebuilt.text,
        "data": json_value(rebuilt.data),
    }


def decode_event(value: object) -> TraceEvent:
    """Decode one closed trace event."""
    if not isinstance(value, dict):
        raise fail()
    exact(value, ("attempt", "sequence", "kind", "name", "text", "data"))
    data = value["data"]
    if data is not None and not isinstance(data, dict):
        raise fail()
    try:
        return TraceEvent(
            attempt=AttemptIdentity(value["attempt"]),  # type: ignore[arg-type]
            sequence=value["sequence"],  # type: ignore[arg-type]
            kind=TraceKind(value["kind"]),  # type: ignore[arg-type]
            name=value["name"],  # type: ignore[arg-type]
            text=value["text"],  # type: ignore[arg-type]
            data=data,
        )
    except (TypeError, ValueError):
        raise fail() from None


def response(value: object) -> dict[str, object]:
    """Reconstruct and encode one terminal public AnalysisResponse."""
    if not isinstance(value, AnalysisResponse):
        raise fail()
    try:
        if (
            isinstance(value.trace_count, bool)
            or not isinstance(value.trace_count, int)
            or value.trace_count < 0
        ):
            raise fail()
        for item in (value.failure_code, value.failure_detail):
            if item is not None and (
                not isinstance(item, str) or not item or not item.strip()
            ):
                raise fail()
        rebuilt = AnalysisResponse(
            attempt=AttemptIdentity(value.attempt.value),
            status=AttemptStatus(value.status),
            structured_output=json_value(value.structured_output),
            trace_count=value.trace_count,
            failure_code=value.failure_code,
            failure_detail=value.failure_detail,
        )
    except (AttributeError, TypeError, ValueError):
        raise fail() from None
    return {
        "attempt": rebuilt.attempt.value,
        "status": rebuilt.status.value,
        "structured_output": json_value(rebuilt.structured_output),
        "trace_count": rebuilt.trace_count,
        "failure_code": rebuilt.failure_code,
        "failure_detail": rebuilt.failure_detail,
    }


def decode_response(value: object) -> AnalysisResponse:
    """Decode one exact AnalysisResponse."""
    if not isinstance(value, dict):
        raise fail()
    names = (
        "attempt",
        "status",
        "structured_output",
        "trace_count",
        "failure_code",
        "failure_detail",
    )
    exact(value, names)
    try:
        rebuilt = AnalysisResponse(
            attempt=AttemptIdentity(value["attempt"]),  # type: ignore[arg-type]
            status=AttemptStatus(value["status"]),  # type: ignore[arg-type]
            structured_output=json_value(value["structured_output"]),
            trace_count=value["trace_count"],  # type: ignore[arg-type]
            failure_code=value["failure_code"],  # type: ignore[arg-type]
            failure_detail=value["failure_detail"],  # type: ignore[arg-type]
        )
        response(rebuilt)
        return rebuilt
    except (TypeError, ValueError):
        raise fail() from None
