"""Persistence, context, and per-part execution helpers for A3."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from hashlib import sha256
from typing import Any

from msgloom.ai import AnalysisAttempt
from msgloom.ai_evidence import EvidenceSession, PersistenceTraceSink
from msgloom.contracts import (
    AttemptIdentity,
    ResultRef,
    StageResult,
    VersionRef,
)
from msgloom.persistence import Phase1Persistence, StaleClaimError
from msgloom.triage import (
    PriorTopicAssessment,
    TriageCandidate,
    TriageData,
    validate_triage_candidate,
)
from msgloom.triage_input import (
    PART_KIND,
    PART_SCHEMA_VERSION,
    PartState,
    SavedFilterBinding,
    SavedGroupBinding,
    SavedPreparedBinding,
    SavedRuleBinding,
    TriageSelection,
    encode_part,
)
from msgloom.working_context import (
    WORKING_CONTEXT_KIND,
    WORKING_CONTEXT_SCHEMA_VERSION,
    WorkingContextSnapshot,
    capture,
    snapshot_ref,
)

from .common import (
    cpu_bound,
    drain,
    ensure_acceptance_time,
    record_result,
    result_ref,
    stable_id,
)
from .models import TriageMode, TriageProducerConfig


def _validated_candidate(output: object, part) -> TriageCandidate:
    """Validate bounded model output and exact per-part source coverage."""
    payload = json.dumps(
        output,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    candidate = validate_triage_candidate(payload)
    allowed = {item.source_ref for item in part.fragments}
    used = {source for topic in candidate.topics for source in topic.source_refs} | {
        item.source_ref for item in candidate.dispositions
    }
    if not used <= allowed:
        raise ValueError("candidate references a source outside its part")
    if not allowed <= used:
        raise ValueError("candidate does not cover every required part source")
    return candidate


class _TriageIOMixin:
    """Implement exact semantic loads and claim-fenced intermediate saves."""

    _persistence: Phase1Persistence
    _config: TriageProducerConfig
    _runner: Any
    _stage: Callable[..., StageResult]
    _part_attempt: Callable[..., AttemptIdentity]
    _context_text: Callable[..., str]
    _save_part_state: Callable[..., Any]

    async def _semantic_ref(self, *args: Any):
        """Encode and hash one semantic value off the caller event loop."""
        return await cpu_bound(self._persistence.semantic_reference, *args)

    async def _record_terminal_prefix(self, terminal: ResultRef) -> None:
        """Record request/traces before the exact durable terminal response."""
        saved = await self._persistence.get_result(terminal.result_id)
        if saved is None:
            raise ValueError("durable AI terminal result is missing")
        for reference in saved.input_refs:
            record_result(reference)
        record_result(terminal)

    async def _load_values[T](
        self,
        refs: tuple[ResultRef, ...],
        by_id: dict[str, StageResult],
        expected: type[T],
    ) -> tuple[T, ...]:
        values: list[T] = []
        for ref in refs:
            semantic = by_id[ref.result_id].semantic_data_ref
            if semantic is None:
                raise ValueError("upstream semantic reference is missing")
            value = await self._persistence.load_semantic_data(semantic)
            if not isinstance(value, expected):
                raise TypeError("upstream semantic value has unexpected type")
            values.append(value)
        return tuple(values)

    async def _load_priors(
        self, by_id: dict[str, StageResult]
    ) -> tuple[PriorTopicAssessment, ...]:
        priors: list[PriorTopicAssessment] = []
        for ref in self._config.plan.prior_triage_results:
            saved = by_id[ref.result_id]
            semantic = saved.semantic_data_ref
            if semantic is None:
                raise ValueError("prior triage semantic reference is missing")
            value = await self._persistence.load_semantic_data(semantic)
            if not isinstance(value, TriageData):
                raise TypeError("prior triage result has unexpected semantic type")
            for topic in value.topics:
                evidence = []
                for development in topic.developments:
                    evidence.extend(development.evidence)
                for action in topic.actions:
                    evidence.extend(action.evidence)
                for deadline in topic.deadlines:
                    evidence.extend(deadline.evidence)
                for risk in topic.risks:
                    evidence.extend(risk.evidence)
                unique_evidence = []
                for item in evidence:
                    if item not in unique_evidence:
                        unique_evidence.append(item)
                priors.append(
                    PriorTopicAssessment(
                        topic_ref=topic.topic_ref,
                        assessment_ref=topic.assessment_ref,
                        source_refs=topic.source_refs,
                        evidence=tuple(unique_evidence),
                    )
                )
        return tuple(priors)

    async def _save_rules(self, request, attempt, claim, rules, upstream) -> ResultRef:
        result_id = stable_id(
            "triage-rules",
            request.execution.value,
            self._config.rule_config.version.version,
            self._config.semantic_fingerprint(),
        )
        semantic = await self._semantic_ref(
            f"{result_id}:data", "triage_rules", "1", rules
        )
        result = self._stage(
            request,
            attempt,
            result_id,
            "triage_rules",
            tuple(result_ref(item) for item in upstream),
            tuple(item.source_ref for item in rules.outcomes),
            semantic=semantic,
        )
        ensure_acceptance_time()
        await self._persistence.append_result_with_data(result, rules, claim=claim)
        return record_result(result_ref(result))

    async def _context(self, request, attempt, claim, by_id):
        plan = self._config.plan
        if plan.mode is TriageMode.REPLAY:
            ref = plan.replay_context_result
            if ref is None:
                raise ValueError("replay context is missing")
            saved = by_id[ref.result_id]
            semantic = saved.semantic_data_ref
            if semantic is None:
                raise ValueError("saved context semantic reference is missing")
            value = await self._persistence.load_semantic_data(semantic)
            if not isinstance(value, WorkingContextSnapshot):
                raise TypeError("saved context has unexpected semantic type")
            return value, ref

        config = self._config.working_context_config
        capture_time = self._config.capture_time
        if config is None or capture_time is None:
            raise ValueError("live context capture is not configured")
        value = await capture(config, capture_time)
        version = snapshot_ref(value)
        result_id = stable_id(
            "working-context", request.execution.value, version.version
        )
        semantic = await self._semantic_ref(
            f"{result_id}:data",
            WORKING_CONTEXT_KIND,
            WORKING_CONTEXT_SCHEMA_VERSION,
            value,
        )
        result = self._stage(
            request,
            attempt,
            result_id,
            WORKING_CONTEXT_KIND,
            (),
            (),
            semantic=semantic,
            working_context=version,
        )
        ensure_acceptance_time()
        await self._persistence.append_result_with_data(result, value, claim=claim)
        return value, record_result(result_ref(result))

    def _selection(
        self, prepared, filters, groups, rules, rule_ref, context, by_id
    ) -> TriageSelection:
        prepared_bindings = []
        for ref, value in zip(
            self._config.plan.prepared_results, prepared, strict=True
        ):
            semantic = by_id[ref.result_id].semantic_data_ref
            if semantic is None:
                raise ValueError("prepared semantic reference is missing")
            prepared_bindings.append(
                SavedPreparedBinding(result_ref=ref, data_ref=semantic, record=value)
            )
        filter_bindings = []
        for ref, value in zip(self._config.plan.filter_results, filters, strict=True):
            semantic = by_id[ref.result_id].semantic_data_ref
            if semantic is None:
                raise ValueError("filter semantic reference is missing")
            filter_bindings.append(
                SavedFilterBinding(result_ref=ref, data_ref=semantic, result=value)
            )
        group_bindings = []
        for ref, value in zip(self._config.plan.group_results, groups, strict=True):
            semantic = by_id[ref.result_id].semantic_data_ref
            if semantic is None:
                raise ValueError("group semantic reference is missing")
            group_bindings.append(
                SavedGroupBinding(result_ref=ref, data_ref=semantic, result=value)
            )
        saved_rule = self._persistence.semantic_reference(
            f"{rule_ref.result_id}:data", "triage_rules", "1", rules
        )
        return TriageSelection(
            prepared=tuple(prepared_bindings),
            filter_config=self._config.filter_config,
            filters=tuple(filter_bindings),
            groups=tuple(group_bindings),
            rules=SavedRuleBinding(
                result_ref=rule_ref, data_ref=saved_rule, evaluation=rules
            ),
            roles=self._config.plan.roles,
            working_context_ref=snapshot_ref(context),
            versions=self._config.versions,
        )

    async def _save_snapshot(
        self, request, attempt, claim, snapshot, rule_ref, context_ref
    ) -> ResultRef:
        result_id = stable_id(
            "triage-input", request.execution.value, snapshot.snapshot_hash
        )
        semantic = await self._semantic_ref(
            f"{result_id}:data", "triage_input", "1", snapshot
        )
        upstream = (
            *self._config.plan.prepared_results,
            *self._config.plan.filter_results,
            *self._config.plan.group_results,
            rule_ref,
            context_ref,
        )
        result = self._stage(
            request,
            attempt,
            result_id,
            "triage_input",
            upstream,
            tuple(item.source_ref for item in snapshot.selected_sources),
            semantic=semantic,
            working_context=snapshot.working_context_ref,
        )
        ensure_acceptance_time()
        await self._persistence.append_result_with_data(result, snapshot, claim=claim)
        return record_result(result_ref(result))

    async def _save_part(
        self, request, attempt, claim, part, payload, input_result
    ) -> ResultRef:
        encoded_part = await cpu_bound(encode_part, part)
        if encoded_part != payload:
            raise ValueError("saved part payload does not match canonical part bytes")
        semantic = await self._semantic_ref(
            stable_id(
                "triage-part-data",
                request.execution.value,
                part.part_id,
                part.versions.prompt.version,
                self._config.semantic_fingerprint(),
            ),
            PART_KIND,
            PART_SCHEMA_VERSION,
            part,
        )
        if semantic.sha256 != sha256(payload).hexdigest():
            raise ValueError("saved part digest does not match snapshot")
        result = self._stage(
            request,
            attempt,
            stable_id(
                "triage-part",
                request.execution.value,
                part.part_id,
                self._config.semantic_fingerprint(),
            ),
            PART_KIND,
            (input_result,),
            tuple(
                sorted(
                    {item.source_ref for item in part.fragments},
                    key=lambda ref: (ref.kind, ref.identity, ref.version),
                )
            ),
            semantic=semantic,
            working_context=part.working_context_ref,
        )
        ensure_acceptance_time()
        await self._persistence.append_result_with_data(result, part, claim=claim)
        return record_result(result_ref(result))

    async def _run_part(
        self, request, claim, part, part_result, input_result, context_result, context
    ):
        attempt_id = self._part_attempt(request, part.part_id)
        context_text = await cpu_bound(self._context_text, context)
        part_payload = await cpu_bound(encode_part, part)
        analysis = AnalysisAttempt(
            attempt=attempt_id,
            input_refs=(
                VersionRef(
                    PART_KIND,
                    stable_id(
                        "triage-part-data",
                        request.execution.value,
                        part.part_id,
                        part.versions.prompt.version,
                        self._config.semantic_fingerprint(),
                    ),
                    sha256(part_payload).hexdigest(),
                ),
            ),
            context_ref=snapshot_ref(context),
            prompt_ref=self._config.versions.prompt,
            schema_ref=self._config.versions.output_schema,
            model_ref=self._config.versions.model,
            input_text=part_payload.decode(),
            context_text=context_text,
            prompt_text=self._config.prompt_text,
            limits=self._config.attempt_limits,
        )
        ensure_acceptance_time()
        session = await EvidenceSession.begin(
            self._persistence,
            request.execution,
            analysis,
            trusted_policy=self._config.trusted_policy,
            required_inputs=(part_result, input_result, context_result),
            configuration_version=self._config.configuration_version,
            code_version=self._config.code_version,
            claim=claim,
        )
        record_result(session.request_ref)
        sink = PersistenceTraceSink(session)
        try:
            loop = asyncio.get_running_loop()
            timeout = min(
                self._config.attempt_limits.timeout_seconds,
                ensure_acceptance_time(),
            )
            attempt_deadline = loop.time() + timeout
            async with asyncio.timeout_at(attempt_deadline):
                response = await self._runner.run(analysis, sink)
            if loop.time() >= attempt_deadline:
                raise TimeoutError("AI attempt deadline expired")
            ensure_acceptance_time()
        except TimeoutError:
            terminal, cancelled = await drain(
                session.finish_diagnostic(
                    cancelled=False,
                    failure_code="attempt_deadline",
                    failure_detail="AI attempt deadline expired",
                )
            )
            await self._record_terminal_prefix(terminal)
            if cancelled:
                raise asyncio.CancelledError
            state_ref = await self._save_part_state(
                request,
                claim,
                part,
                attempt_id,
                PartState.FAILED,
                terminal,
                "attempt_deadline",
                (part_result, input_result, context_result),
            )
            return None, state_ref, terminal
        except asyncio.CancelledError:
            try:
                _ref, _cancelled = await drain(
                    session.finish_diagnostic(
                        cancelled=True,
                        failure_code="runner_cancelled",
                        failure_detail="AI runner was cancelled",
                    )
                )
            except StaleClaimError:
                pass
            raise
        except Exception:  # noqa: BLE001
            terminal, cancelled = await drain(
                session.finish_diagnostic(
                    cancelled=False,
                    failure_code="runner_failed",
                    failure_detail="AI runner failed",
                )
            )
            await self._record_terminal_prefix(terminal)
            if cancelled:
                raise asyncio.CancelledError
            state_ref = await self._save_part_state(
                request,
                claim,
                part,
                attempt_id,
                PartState.FAILED,
                terminal,
                "runner_failed",
                (part_result, input_result, context_result),
            )
            return None, state_ref, terminal

        terminal, cancelled = await drain(session.finish(response))
        await self._record_terminal_prefix(terminal)
        if cancelled:
            raise asyncio.CancelledError
        if not response.acceptable_for_semantic_validation:
            state_ref = await self._save_part_state(
                request,
                claim,
                part,
                attempt_id,
                PartState.FAILED,
                terminal,
                response.failure_code or "runner_incomplete",
                (part_result, input_result, context_result),
            )
            return None, state_ref, terminal
        try:
            candidate = await cpu_bound(
                _validated_candidate,
                response.structured_output,
                part,
            )
        except (TypeError, ValueError):
            state_ref = await self._save_part_state(
                request,
                claim,
                part,
                attempt_id,
                PartState.FAILED,
                terminal,
                "invalid_candidate",
                (part_result, input_result, context_result),
            )
            return None, state_ref, terminal

        state_ref = await self._save_part_state(
            request,
            claim,
            part,
            attempt_id,
            PartState.COMPLETE,
            terminal,
            None,
            (part_result, input_result, context_result),
        )
        return candidate, state_ref, terminal
