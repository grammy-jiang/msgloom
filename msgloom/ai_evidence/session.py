"""Awaited Phase1Persistence-backed AI evidence session."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine

from msgloom.ai import (
    AnalysisAttempt,
    AnalysisResponse,
    AttemptStatus,
    TraceEvent,
    TrustedPolicy,
)
from msgloom.contracts import (
    ExecutionIdentity,
    ResultRef,
    StageResult,
    TerminalStatus,
)
from msgloom.persistence import Phase1Persistence
from msgloom.persistence.errors import DuplicateResultError

from .codec_common import EvidenceCodecError, canonical
from .codec_common import event as event_payload
from .codec_common import response as response_payload
from .codecs import TERMINAL_MAX_BYTES, TRACE_MAX_BYTES
from .models import RequestEvidence, TerminalEvidence, TraceEvidence


class EvidenceSessionError(RuntimeError):
    """Base privacy-safe evidence session failure."""


class DuplicateAttemptError(EvidenceSessionError):
    """An immutable attempt request already exists."""


class EvidenceStateError(EvidenceSessionError):
    """Evidence order, identity, or durable prerequisites are invalid."""


async def _drain[T](task: asyncio.Task[T]) -> tuple[T, bool]:
    """Await one accepted task through repeated caller cancellation."""
    cancelled = False
    while True:
        try:
            return await asyncio.shield(task), cancelled
        except asyncio.CancelledError:
            cancelled = True
            if task.done():
                return task.result(), cancelled


async def _accepted[T](awaitable: Coroutine[object, object, T]) -> tuple[T, bool]:
    """Own an accepted async operation until it reaches a terminal state."""
    return await _drain(asyncio.create_task(awaitable))


def _request_id(attempt: str) -> str:
    return f"ai-request:{attempt}"


def _trace_id(attempt: str, sequence: int) -> str:
    return f"ai-trace:{attempt}:{sequence}"


def _terminal_id(attempt: str) -> str:
    return f"ai-response:{attempt}"


def _bounded_size(value: object, maximum: int) -> int:
    """Measure canonical evidence and normalize fixed-ceiling rejection."""
    try:
        return len(canonical(value, maximum))
    except EvidenceCodecError:
        raise EvidenceStateError("evidence exceeds fixed codec ceiling") from None


class PersistenceTraceSink:
    """TraceSink facade that persists each event before returning."""

    def __init__(self, session: EvidenceSession) -> None:
        self._session = session

    async def write(self, event: TraceEvent) -> None:
        """Persist exactly the next exposed trace event."""
        await self._session.write(event)


class EvidenceSession:
    """Finite durable evidence state for one AnalysisAttempt identity."""

    def __init__(
        self,
        persistence: Phase1Persistence,
        execution: ExecutionIdentity,
        request: RequestEvidence,
        request_ref: ResultRef,
        configuration_version: str,
        code_version: str,
    ) -> None:
        self._persistence = persistence
        self.execution = execution
        self.request = request
        self.request_ref = request_ref
        self.configuration_version = configuration_version
        self.code_version = code_version
        self._trace_refs: list[ResultRef] = []
        self._terminal_ref: ResultRef | None = None
        self._transition_lock = asyncio.Lock()
        self.trace_sink = PersistenceTraceSink(self)

    @property
    def next_sequence(self) -> int:
        """Return the only trace sequence currently accepted."""
        return len(self._trace_refs)

    @property
    def trace_refs(self) -> tuple[ResultRef, ...]:
        """Return the exact durable trace prefix."""
        return tuple(self._trace_refs)

    @property
    def terminal_ref(self) -> ResultRef | None:
        """Return terminal evidence when explicitly finished."""
        return self._terminal_ref

    @classmethod
    async def begin(
        cls,
        persistence: Phase1Persistence,
        execution: ExecutionIdentity,
        request: AnalysisAttempt,
        *,
        trusted_policy: TrustedPolicy,
        required_inputs: tuple[ResultRef, ...],
        configuration_version: str,
        code_version: str,
    ) -> EvidenceSession:
        """Validate durable inputs and save request evidence before execution."""
        if not isinstance(persistence, Phase1Persistence):
            raise TypeError("evidence session requires Phase1Persistence")
        if not isinstance(execution, ExecutionIdentity):
            raise TypeError("evidence session requires ExecutionIdentity")
        if not isinstance(trusted_policy, TrustedPolicy):
            raise TypeError("evidence session requires TrustedPolicy")
        evidence = RequestEvidence.bind(request, trusted_policy, required_inputs)
        request_id = _request_id(request.attempt.value)
        for reference in required_inputs:
            saved, cancelled = await _accepted(
                persistence.get_result(reference.result_id)
            )
            if cancelled:
                raise asyncio.CancelledError
            if (
                saved is None
                or not saved.acceptable
                or saved.semantic_data_ref is None
                or ResultRef(saved.result_id, saved.kind, saved.schema_version)
                != reference
            ):
                raise EvidenceStateError("required input is not durably acceptable")
            _value, cancelled = await _accepted(
                persistence.load_semantic_data(saved.semantic_data_ref)
            )
            if cancelled:
                raise asyncio.CancelledError

        semantic_ref, cancelled = await _accepted(
            asyncio.to_thread(
                persistence.semantic_reference,
                f"{request_id}:data",
                "ai_request",
                "1",
                evidence,
            )
        )
        if cancelled:
            raise asyncio.CancelledError
        result = StageResult(
            result_id=request_id,
            kind="ai_request",
            schema_version="1",
            execution=execution,
            attempt=request.attempt,
            input_refs=required_inputs,
            source_versions=(),
            prepared_versions=request.input_refs,
            topic_versions=(),
            configuration_version=configuration_version,
            code_version=code_version,
            status=TerminalStatus.COMPLETE,
            acceptable=True,
            prompt_version=request.prompt_ref.version,
            model_identifier=evidence.resolved_model,
            working_context_version=request.context_ref,
            semantic_data_ref=semantic_ref,
        )
        try:
            _none, cancelled = await _accepted(
                persistence.append_result_with_data(
                    result,
                    evidence,
                    require_new=True,
                )
            )
        except DuplicateResultError:
            raise DuplicateAttemptError(
                "analysis attempt evidence already exists"
            ) from None
        session = cls(
            persistence,
            execution,
            evidence,
            ResultRef(request_id, "ai_request", "1"),
            configuration_version,
            code_version,
        )
        if cancelled:
            raise asyncio.CancelledError
        return session

    async def write(self, event: TraceEvent) -> None:
        """Serialize and persist exactly one next trace transition."""
        async with self._transition_lock:
            await self._write(event)

    async def _write(self, event: TraceEvent) -> None:
        """Persist one accepted trace and advance state only after durability."""
        if self._terminal_ref is not None:
            raise EvidenceStateError("terminal evidence already exists")
        if not isinstance(event, TraceEvent):
            raise EvidenceStateError("trace event type is invalid")
        request = self.request.request
        if self.next_sequence >= request.limits.max_trace_events:
            raise EvidenceStateError("trace event count exceeds request limit")
        if event.attempt != request.attempt or event.sequence != self.next_sequence:
            raise EvidenceStateError("trace identity or sequence is invalid")
        event_bytes = _bounded_size(event_payload(event), TRACE_MAX_BYTES)
        if event_bytes > request.limits.max_trace_event_bytes:
            raise EvidenceStateError("trace event exceeds request byte limit")
        evidence = TraceEvidence(self.request_ref, event)
        result_id = _trace_id(request.attempt.value, event.sequence)
        semantic_ref, cancelled = await _accepted(
            asyncio.to_thread(
                self._persistence.semantic_reference,
                f"{result_id}:data",
                "ai_trace",
                "1",
                evidence,
            )
        )
        if cancelled:
            raise asyncio.CancelledError
        lineage = (self.request_ref, *self._trace_refs)
        result = StageResult(
            result_id=result_id,
            kind="ai_trace",
            schema_version="1",
            execution=self.execution,
            attempt=request.attempt,
            input_refs=lineage,
            source_versions=(),
            prepared_versions=request.input_refs,
            topic_versions=(),
            configuration_version=self.configuration_version,
            code_version=self.code_version,
            status=TerminalStatus.COMPLETE,
            acceptable=True,
            prompt_version=request.prompt_ref.version,
            model_identifier=self.request.resolved_model,
            working_context_version=request.context_ref,
            semantic_data_ref=semantic_ref,
        )
        _none, cancelled = await _accepted(
            self._persistence.append_result_with_data(result, evidence)
        )
        self._trace_refs.append(ResultRef(result_id, "ai_trace", "1"))
        if cancelled:
            raise asyncio.CancelledError

    async def finish(self, response: AnalysisResponse) -> ResultRef:
        """Serialize terminal response after the complete durable trace prefix."""
        async with self._transition_lock:
            return await self._finish_response(response)

    async def _finish_response(self, response: AnalysisResponse) -> ResultRef:
        """Validate and save one accepted terminal response transition."""
        request = self.request.request
        if self._terminal_ref is not None:
            raise EvidenceStateError("terminal evidence already exists")
        if not isinstance(response, AnalysisResponse):
            raise EvidenceStateError("terminal response type is invalid")
        if response.attempt != request.attempt:
            raise EvidenceStateError("terminal attempt identity is invalid")
        if response.trace_count != len(self._trace_refs):
            raise EvidenceStateError("terminal trace count does not match evidence")
        response_bytes = _bounded_size(response_payload(response), TERMINAL_MAX_BYTES)
        if response_bytes > request.limits.max_output_bytes:
            raise EvidenceStateError("terminal response exceeds request byte limit")
        eligible = response.acceptable_for_semantic_validation
        status = (
            TerminalStatus.COMPLETE
            if response.status is AttemptStatus.COMPLETE
            else TerminalStatus.FAILED
        )
        return await self._finish(response, status, eligible)

    async def finish_diagnostic(
        self,
        *,
        cancelled: bool,
        failure_code: str,
        failure_detail: str,
    ) -> ResultRef:
        """Serialize one caller-supplied runner diagnostic transition."""
        async with self._transition_lock:
            return await self._finish_diagnostic(
                cancelled=cancelled,
                failure_code=failure_code,
                failure_detail=failure_detail,
            )

    async def _finish_diagnostic(
        self,
        *,
        cancelled: bool,
        failure_code: str,
        failure_detail: str,
    ) -> ResultRef:
        """Save one validated runner failure/cancellation diagnostic."""
        if self._terminal_ref is not None:
            raise EvidenceStateError("terminal evidence already exists")
        if not failure_code or not failure_code.strip():
            raise ValueError("failure code must be non-empty")
        if not failure_detail or not failure_detail.strip():
            raise ValueError("failure detail must be non-empty")
        response = AnalysisResponse(
            attempt=self.request.request.attempt,
            status=AttemptStatus.FAILED,
            structured_output=None,
            trace_count=len(self._trace_refs),
            failure_code=failure_code,
            failure_detail=failure_detail,
        )
        response_bytes = _bounded_size(response_payload(response), TERMINAL_MAX_BYTES)
        if response_bytes > self.request.request.limits.max_output_bytes:
            raise EvidenceStateError("terminal response exceeds request byte limit")
        status = TerminalStatus.CANCELLED if cancelled else TerminalStatus.FAILED
        return await self._finish(response, status, False)

    async def _finish(
        self,
        response: AnalysisResponse,
        status: TerminalStatus,
        eligible: bool,
    ) -> ResultRef:
        evidence = TerminalEvidence(
            request_ref=self.request_ref,
            trace_refs=tuple(self._trace_refs),
            response=response,
            transport_eligible=eligible,
        )
        request = self.request.request
        result_id = _terminal_id(request.attempt.value)
        semantic_ref, cancelled = await _accepted(
            asyncio.to_thread(
                self._persistence.semantic_reference,
                f"{result_id}:data",
                "ai_response",
                "1",
                evidence,
            )
        )
        if cancelled:
            raise asyncio.CancelledError
        result = StageResult(
            result_id=result_id,
            kind="ai_response",
            schema_version="1",
            execution=self.execution,
            attempt=request.attempt,
            input_refs=(self.request_ref, *self._trace_refs),
            source_versions=(),
            prepared_versions=request.input_refs,
            topic_versions=(),
            configuration_version=self.configuration_version,
            code_version=self.code_version,
            status=status,
            acceptable=eligible,
            prompt_version=request.prompt_ref.version,
            model_identifier=self.request.resolved_model,
            working_context_version=request.context_ref,
            semantic_data_ref=semantic_ref,
        )
        _none, cancelled = await _accepted(
            self._persistence.append_result_with_data(result, evidence)
        )
        terminal = ResultRef(result_id, "ai_response", "1")
        self._terminal_ref = terminal
        if cancelled:
            raise asyncio.CancelledError
        return terminal
