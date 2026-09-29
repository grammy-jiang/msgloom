"""Strict bounded parent-side IPC decoding for the isolated AI worker."""

from __future__ import annotations

import asyncio
import json
import math
from collections.abc import Awaitable, Callable
from typing import Any

from msgloom.ai.models import AnalysisAttempt, TraceEvent, TraceKind, TraceSink

_FAILURE_CODES = frozenset(
    {
        "worker-failure",
        "sdk-result-error",
        "missing-structured-output",
        "incomplete-sdk-stream",
        "disabled-tool-event",
    }
)


class IPCFailure(ValueError):
    """Carry the durable trace count at an invalid worker boundary."""

    def __init__(self, trace_count: int) -> None:
        super().__init__("invalid or oversized AI worker IPC")
        self.trace_count = trace_count


class TracePersistenceFailure(RuntimeError):
    """Carry the exact count saved before the trace sink failed."""

    def __init__(self, trace_count: int) -> None:
        super().__init__("AI trace persistence failed")
        self.trace_count = trace_count


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object field")
        result[key] = value
    return result


def _constant(_value: str) -> object:
    raise ValueError("non-finite JSON number")


def _validate_json(value: object, *, depth: int = 0) -> None:
    if depth > 16:
        raise ValueError("IPC JSON nesting exceeded")
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("IPC JSON number is not finite")
        return
    if isinstance(value, list):
        for item in value:
            _validate_json(item, depth=depth + 1)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("IPC JSON object key is not text")
            _validate_json(item, depth=depth + 1)
        return
    raise TypeError("IPC contains a non-JSON value")


def decode_event(line: bytes) -> dict[str, Any]:
    """Decode one exact worker protocol object."""
    try:
        event = json.loads(
            line,
            object_pairs_hook=_pairs,
            parse_constant=_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError("AI worker emitted malformed IPC") from exc
    if not isinstance(event, dict):
        raise TypeError("AI worker IPC must be an object")
    _validate_json(event)
    event_type = event.get("type")
    if event_type == "trace":
        expected = {"type", "kind", "name", "text", "data"}
        if set(event) != expected:
            raise ValueError("AI worker trace fields are not exact")
        try:
            TraceKind(event["kind"])
        except (TypeError, ValueError) as exc:
            raise ValueError("AI worker trace kind is unknown") from exc
        if not isinstance(event["name"], str) or not event["name"].strip():
            raise ValueError("AI worker trace name is invalid")
        if not isinstance(event["text"], str) or not isinstance(event["data"], dict):
            raise ValueError("AI worker trace value has the wrong type")
        return event
    if event_type != "final" or not isinstance(event.get("ok"), bool):
        raise ValueError("AI worker emitted an unknown IPC event")
    if event["ok"]:
        if set(event) != {"type", "ok", "structured_output"}:
            raise ValueError("AI worker success fields are not exact")
        if not isinstance(event["structured_output"], dict):
            raise ValueError("AI worker structured output is not an object")
        return event
    if set(event) != {"type", "ok", "code", "detail"}:
        raise ValueError("AI worker failure fields are not exact")
    if event["code"] not in _FAILURE_CODES:
        raise ValueError("AI worker failure code is unknown")
    if not isinstance(event["detail"], str):
        raise TypeError("AI worker failure detail has the wrong type")
    return event


async def consume_stdout(
    stream: Any,
    attempt: AnalysisAttempt,
    sink: TraceSink,
    persist: Callable[[TraceSink, TraceEvent], Awaitable[None]],
) -> tuple[int, dict[str, Any] | None]:
    """Persist a strictly ordered worker stream and return its terminal event."""
    count = 0
    final: dict[str, Any] | None = None
    while True:
        try:
            line = await stream.readline()
        except ValueError as exc:
            raise IPCFailure(count) from exc
        if not line:
            break
        maximum = (
            attempt.limits.max_output_bytes
            if final is None and b'"type":"final"' in line
            else attempt.limits.max_trace_event_bytes
        )
        if len(line) > maximum:
            raise IPCFailure(count)
        try:
            event = decode_event(line)
        except (TypeError, ValueError) as exc:
            raise IPCFailure(count) from exc
        if final is not None:
            raise IPCFailure(count)
        if event["type"] == "final":
            if len(line) > attempt.limits.max_output_bytes:
                raise IPCFailure(count)
            final = event
            continue
        if count >= attempt.limits.max_trace_events:
            raise IPCFailure(count)
        if len(line) > attempt.limits.max_trace_event_bytes:
            raise IPCFailure(count)
        trace = TraceEvent(
            attempt.attempt,
            count,
            TraceKind(event["kind"]),
            event["name"],
            event["text"],
            event["data"],
        )
        try:
            await persist(sink, trace)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            raise TracePersistenceFailure(count) from exc
        count += 1
    return count, final


async def count_stderr(stream: Any, maximum: int) -> int:
    """Drain stderr while retaining only a bounded byte count."""
    total = 0
    while chunk := await stream.read(min(4096, maximum + 1)):
        total += len(chunk)
        if total > maximum:
            raise ValueError("AI child stderr limit exceeded")
    return total
