"""Canonical fixed-ceiling semantic codecs for AI evidence."""

from __future__ import annotations

import warnings
from collections.abc import Callable

from .codec_common import (
    EvidenceCodecError,
    attempt,
    canonical,
    decode_attempt,
    decode_event,
    decode_response,
    decode_result_ref,
    event,
    exact,
    fail,
    json_value,
    load,
    response,
    result_ref,
)
from .models import RequestEvidence, TerminalEvidence, TraceEvidence

REQUEST_MAX_BYTES = 4 * 1024 * 1024
TRACE_MAX_BYTES = 1024 * 1024
TERMINAL_MAX_BYTES = 4 * 1024 * 1024


def _safe[T](operation: Callable[[], T]) -> T:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            return operation()
        except EvidenceCodecError:
            raise
        except (AttributeError, KeyError, TypeError, UnicodeError, ValueError):
            raise fail() from None


class RequestEvidenceCodec:
    """Encode exact request evidence without credentials or runtime paths."""

    kind = "ai_request"
    schema_version = "1"
    max_bytes = REQUEST_MAX_BYTES

    def encode(self, value: object) -> bytes:
        """Revalidate and canonically encode request evidence."""

        def operation() -> bytes:
            if not isinstance(value, RequestEvidence):
                raise fail()
            schema = json_value(value.resolved_schema)
            if not isinstance(schema, dict):
                raise fail()
            rebuilt = RequestEvidence(
                request=decode_attempt(attempt(value.request)),
                resolved_schema=schema,
                resolved_model=value.resolved_model,
                required_inputs=tuple(
                    decode_result_ref(result_ref(item))
                    for item in value.required_inputs
                ),
            )
            body = {
                "request": attempt(rebuilt.request),
                "resolved_schema": json_value(rebuilt.resolved_schema),
                "resolved_model": rebuilt.resolved_model,
                "required_inputs": [
                    result_ref(item) for item in rebuilt.required_inputs
                ],
            }
            return canonical(body, self.max_bytes)

        return _safe(operation)

    def decode(self, payload: bytes) -> RequestEvidence:
        """Decode and fully reconstruct request evidence."""

        def operation() -> RequestEvidence:
            body = load(payload, self.max_bytes)
            exact(
                body,
                ("request", "resolved_schema", "resolved_model", "required_inputs"),
            )
            schema = body["resolved_schema"]
            inputs = body["required_inputs"]
            model = body["resolved_model"]
            if not isinstance(schema, dict) or not isinstance(inputs, list):
                raise fail()
            if not isinstance(model, str) or not model.strip():
                raise fail()
            return RequestEvidence(
                request=decode_attempt(body["request"]),
                resolved_schema=schema,
                resolved_model=model,
                required_inputs=tuple(decode_result_ref(item) for item in inputs),
            )

        return _safe(operation)


class TraceEvidenceCodec:
    """Encode one exact exposed trace event and request lineage."""

    kind = "ai_trace"
    schema_version = "1"
    max_bytes = TRACE_MAX_BYTES

    def encode(self, value: object) -> bytes:
        """Revalidate and canonically encode trace evidence."""

        def operation() -> bytes:
            if not isinstance(value, TraceEvidence):
                raise fail()
            rebuilt = TraceEvidence(
                request_ref=decode_result_ref(result_ref(value.request_ref)),
                event=decode_event(event(value.event)),
            )
            return canonical(
                {
                    "request_ref": result_ref(rebuilt.request_ref),
                    "event": event(rebuilt.event),
                },
                self.max_bytes,
            )

        return _safe(operation)

    def decode(self, payload: bytes) -> TraceEvidence:
        """Decode one exact trace evidence value."""

        def operation() -> TraceEvidence:
            body = load(payload, self.max_bytes)
            exact(body, ("request_ref", "event"))
            return TraceEvidence(
                request_ref=decode_result_ref(body["request_ref"]),
                event=decode_event(body["event"]),
            )

        return _safe(operation)


class TerminalEvidenceCodec:
    """Encode transport completion separately from triage semantic acceptance."""

    kind = "ai_response"
    schema_version = "1"
    max_bytes = TERMINAL_MAX_BYTES

    def encode(self, value: object) -> bytes:
        """Revalidate and canonically encode terminal evidence."""

        def operation() -> bytes:
            if not isinstance(value, TerminalEvidence):
                raise fail()
            rebuilt = TerminalEvidence(
                request_ref=decode_result_ref(result_ref(value.request_ref)),
                trace_refs=tuple(
                    decode_result_ref(result_ref(item)) for item in value.trace_refs
                ),
                response=decode_response(response(value.response)),
                transport_eligible=value.transport_eligible,
                triage_semantics_accepted=value.triage_semantics_accepted,
            )
            return canonical(
                {
                    "request_ref": result_ref(rebuilt.request_ref),
                    "trace_refs": [result_ref(item) for item in rebuilt.trace_refs],
                    "response": response(rebuilt.response),
                    "transport_eligible": rebuilt.transport_eligible,
                    "triage_semantics_accepted": rebuilt.triage_semantics_accepted,
                },
                self.max_bytes,
            )

        return _safe(operation)

    def decode(self, payload: bytes) -> TerminalEvidence:
        """Decode terminal evidence and reject semantic-acceptance forgery."""

        def operation() -> TerminalEvidence:
            body = load(payload, self.max_bytes)
            exact(
                body,
                (
                    "request_ref",
                    "trace_refs",
                    "response",
                    "transport_eligible",
                    "triage_semantics_accepted",
                ),
            )
            refs = body["trace_refs"]
            eligible = body["transport_eligible"]
            accepted = body["triage_semantics_accepted"]
            if not isinstance(refs, list) or not isinstance(eligible, bool):
                raise fail()
            if accepted is not False:
                raise fail()
            return TerminalEvidence(
                request_ref=decode_result_ref(body["request_ref"]),
                trace_refs=tuple(decode_result_ref(item) for item in refs),
                response=decode_response(body["response"]),
                transport_eligible=eligible,
                triage_semantics_accepted=False,
            )

        return _safe(operation)


AI_EVIDENCE_CODECS = (
    RequestEvidenceCodec(),
    TraceEvidenceCodec(),
    TerminalEvidenceCodec(),
)
AI_EVIDENCE_SCHEMAS = frozenset(
    (codec.kind, codec.schema_version) for codec in AI_EVIDENCE_CODECS
)
