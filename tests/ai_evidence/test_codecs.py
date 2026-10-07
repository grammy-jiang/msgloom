"""Closed codec and privacy tests for AI evidence."""

from __future__ import annotations

import warnings

import pytest

from msgloom.ai import AnalysisResponse, AttemptStatus, TraceEvent, TraceKind
from msgloom.ai_evidence import (
    EvidenceCodecError,
    RequestEvidence,
    RequestEvidenceCodec,
    TerminalEvidence,
    TerminalEvidenceCodec,
    TraceEvidence,
    TraceEvidenceCodec,
)
from msgloom.contracts import AttemptIdentity, ResultRef

from .helpers import analysis_attempt, trusted_policy


def test_request_codec_round_trip_retains_exact_public_request_and_policy() -> None:
    request = analysis_attempt()
    value = RequestEvidence.bind(
        request,
        trusted_policy(request),
        (ResultRef("seed-result", "seed", "1"),),
    )
    codec = RequestEvidenceCodec()
    payload = codec.encode(value)
    decoded = codec.decode(payload)
    if decoded.request != request:
        pytest.fail("request evidence changed across canonical round trip")
    if decoded.resolved_model != "synthetic-model":
        pytest.fail("resolved trusted model was not retained")
    if dict(decoded.resolved_schema) != dict(value.resolved_schema):
        pytest.fail("resolved trusted schema was not retained")
    if b"credential" in payload or b"/home/" in payload:
        pytest.fail("request evidence unexpectedly contains runtime secret material")


def test_codecs_revalidate_bypassed_nested_values_without_raw_warning() -> None:
    sensitive = "synthetic-private-marker"
    request = analysis_attempt()
    value = RequestEvidence.bind(
        request,
        trusted_policy(request),
        (ResultRef("seed-result", "seed", "1"),),
    )
    object.__setattr__(request.limits, "max_tokens", sensitive)
    with warnings.catch_warnings(record=True) as emitted:
        warnings.simplefilter("always")
        with pytest.raises(EvidenceCodecError) as raised:
            RequestEvidenceCodec().encode(value)
    if emitted:
        pytest.fail("invalid evidence emitted a warning")
    if sensitive in str(raised.value):
        pytest.fail("codec error leaked invalid nested evidence")

    event = TraceEvent(
        attempt=AttemptIdentity("attempt-ai-1"),
        sequence=0,
        kind=TraceKind.DIAGNOSTIC,
        name="synthetic",
        text="",
    )
    object.__setattr__(event, "kind", sensitive)
    with pytest.raises(EvidenceCodecError):
        TraceEvidenceCodec().encode(
            TraceEvidence(ResultRef("request", "ai_request", "1"), event)
        )


def test_decode_rejects_noncanonical_duplicate_and_unknown_fields() -> None:
    codec = TraceEvidenceCodec()
    bad_payloads = (
        b'{"event":{},"request_ref":{} }',
        b'{"event":{},"event":{},"request_ref":{}}',
        b'{"event":{},"request_ref":{},"extra":1}',
    )
    for payload in bad_payloads:
        with pytest.raises(EvidenceCodecError):
            codec.decode(payload)


def test_fixed_request_ceiling_is_independent_of_runner_limit() -> None:
    text = "x" * (4 * 1024 * 1024)
    request = analysis_attempt(
        input_text=text,
        max_input_bytes=len(text.encode("utf-8")) + 1024,
    )
    value = RequestEvidence.bind(
        request,
        trusted_policy(request),
        (ResultRef("seed-result", "seed", "1"),),
    )
    with pytest.raises(EvidenceCodecError):
        RequestEvidenceCodec().encode(value)


def test_terminal_codec_never_accepts_triage_semantics() -> None:
    response = AnalysisResponse(
        attempt=AttemptIdentity("attempt-ai-1"),
        status=AttemptStatus.COMPLETE,
        structured_output={"result": "synthetic"},
        trace_count=0,
    )
    value = TerminalEvidence(
        request_ref=ResultRef("request", "ai_request", "1"),
        trace_refs=(),
        response=response,
        transport_eligible=True,
    )
    codec = TerminalEvidenceCodec()
    decoded = codec.decode(codec.encode(value))
    if decoded.triage_semantics_accepted:
        pytest.fail("transport evidence was converted to triage acceptance")

    object.__setattr__(response, "trace_count", True)
    with pytest.raises(EvidenceCodecError):
        codec.encode(value)


def test_request_codec_rejects_bypassed_empty_and_duplicate_inputs() -> None:
    request = analysis_attempt()
    seed = ResultRef("seed-result", "seed", "1")
    codec = RequestEvidenceCodec()

    empty = RequestEvidence.bind(request, trusted_policy(request), (seed,))
    object.__setattr__(empty, "required_inputs", ())
    with pytest.raises(EvidenceCodecError):
        codec.encode(empty)

    duplicate = RequestEvidence.bind(request, trusted_policy(request), (seed,))
    object.__setattr__(duplicate, "required_inputs", (seed, seed))
    with pytest.raises(EvidenceCodecError):
        codec.encode(duplicate)


def test_trace_and_terminal_codecs_reject_bypassed_lineage_invariants() -> None:
    attempt = AttemptIdentity("attempt-ai-1")
    event = TraceEvent(
        attempt=attempt,
        sequence=0,
        kind=TraceKind.DIAGNOSTIC,
        name="synthetic",
        text="",
    )
    trace = TraceEvidence(ResultRef("request", "ai_request", "1"), event)
    object.__setattr__(
        trace,
        "request_ref",
        ResultRef("request", "wrong-request-kind", "1"),
    )
    with pytest.raises(EvidenceCodecError):
        TraceEvidenceCodec().encode(trace)

    response = AnalysisResponse(
        attempt=attempt,
        status=AttemptStatus.FAILED,
        structured_output=None,
        trace_count=0,
        failure_code="synthetic",
        failure_detail="synthetic",
    )
    terminal = TerminalEvidence(
        request_ref=ResultRef("request", "ai_request", "1"),
        trace_refs=(),
        response=response,
        transport_eligible=False,
    )
    object.__setattr__(terminal, "transport_eligible", True)
    object.__setattr__(response, "trace_count", 9)
    with pytest.raises(EvidenceCodecError):
        TerminalEvidenceCodec().encode(terminal)


def test_terminal_decode_rejects_wrong_ref_kinds_counts_and_eligibility() -> None:
    response = AnalysisResponse(
        attempt=AttemptIdentity("attempt-ai-1"),
        status=AttemptStatus.COMPLETE,
        structured_output={"result": "synthetic"},
        trace_count=1,
    )
    terminal = TerminalEvidence(
        request_ref=ResultRef("request", "ai_request", "1"),
        trace_refs=(ResultRef("trace", "ai_trace", "1"),),
        response=response,
        transport_eligible=True,
    )
    codec = TerminalEvidenceCodec()
    payload = codec.encode(terminal)

    import json

    body = json.loads(payload)
    variants = []

    wrong_request = dict(body)
    wrong_request["request_ref"] = dict(wrong_request["request_ref"])
    wrong_request["request_ref"]["kind"] = "wrong"
    variants.append(wrong_request)

    wrong_trace = dict(body)
    wrong_trace["trace_refs"] = [dict(wrong_trace["trace_refs"][0])]
    wrong_trace["trace_refs"][0]["schema_version"] = "2"
    variants.append(wrong_trace)

    wrong_count = dict(body)
    wrong_count["response"] = dict(wrong_count["response"])
    wrong_count["response"]["trace_count"] = 0
    variants.append(wrong_count)

    wrong_eligibility = dict(body)
    wrong_eligibility["transport_eligible"] = False
    variants.append(wrong_eligibility)

    for variant in variants:
        invalid = json.dumps(
            variant,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        with pytest.raises(EvidenceCodecError):
            codec.decode(invalid)
