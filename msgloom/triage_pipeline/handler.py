"""Finite awaited A3 handler with evidence-before-semantics ordering."""

from __future__ import annotations

import asyncio
from functools import partial
from typing import Protocol

from msgloom.ai import AnalysisAttempt, AnalysisResponse, TraceSink
from msgloom.contracts import (
    AttemptIdentity,
    ClaimKind,
    ClaimToken,
    ExternalEffectState,
    Failure,
    Limitation,
    OperationOutcome,
    OperationRequest,
    PhaseCapability,
    ResultRef,
    StageResult,
    TerminalStatus,
)
from msgloom.persistence import Phase1Persistence, StaleClaimError
from msgloom.preparation import PreparedRecord
from msgloom.preparation.filtering import FilterResult
from msgloom.preparation.grouping import GroupResult
from msgloom.triage import (
    TriageCandidate,
    TriageReconciliationError,
    evaluate_rule_set,
    reconcile_triage,
)
from msgloom.triage_input import (
    PartExecution,
    PartState,
    build_triage_input,
    saved_part_payloads,
    validate_parent_part_states,
)

from .codecs import (
    TriagePartState,
)
from .models import TriageProducerConfig
from .part_state_mixin import _TriagePartStateMixin


class TriageRunner(Protocol):
    """Narrow runner boundary implemented by AIRunner and test emitters."""

    async def run(
        self, attempt: AnalysisAttempt, trace_sink: TraceSink
    ) -> AnalysisResponse:
        """Run one already-admitted bounded analysis attempt."""
        ...


from .common import (
    RUN_STATE,
    RunState,
    cpu_bound,
    drain,
    durable_prefix,
    result_ref,
    stable_id,
)
from .finalize_mixin import _TriageFinalizeMixin
from .io_mixin import _TriageIOMixin


class TriageHandler(_TriagePartStateMixin, _TriageIOMixin, _TriageFinalizeMixin):
    """Produce one bounded saved A3 result from exact durable A2 inputs."""

    def __init__(
        self,
        persistence: Phase1Persistence,
        config: TriageProducerConfig,
        runner: TriageRunner,
    ) -> None:
        self._persistence = persistence
        self._config = config
        self._trusted_fingerprint = config.validated().semantic_fingerprint()
        self._runner = runner

    async def run(self, request: OperationRequest) -> OperationOutcome:
        """Validate, claim, produce, and return one finite TRIAGE outcome."""
        try:
            checked = self._config.validated()
            if checked.semantic_fingerprint() != self._trusted_fingerprint:
                raise ValueError("trusted triage configuration changed")
            self._config = checked
        except (TypeError, ValueError) as error:
            return self._outcome(
                request,
                TerminalStatus.FAILED,
                failure=Failure("triage_config_invalid", type(error).__name__),
            )
        failure = self._validate_request(request)
        if failure is not None:
            return self._outcome(request, TerminalStatus.FAILED, failure=failure)

        loop = asyncio.get_running_loop()
        state = RunState(
            acceptance_deadline=(
                loop.time()
                + self._config.operation_timeout_seconds
                - self._config.cleanup_margin_seconds
            )
        )
        token = RUN_STATE.set(state)
        claim = None
        try:
            try:
                async with asyncio.timeout_at(state.acceptance_deadline):
                    loaded = await self._preflight_upstream()
            except TimeoutError:
                return self._deadline_outcome(request)
            except Exception as error:  # noqa: BLE001
                return self._outcome(
                    request,
                    TerminalStatus.FAILED,
                    refs=durable_prefix(),
                    failure=Failure("triage_input_invalid", type(error).__name__),
                )

            prepared_versions = []
            for _reference, saved in loaded:
                for version in saved.prepared_versions:
                    if version.kind != "prepared":
                        raise ValueError("upstream prepared lineage kind is invalid")
                    if version not in prepared_versions:
                        prepared_versions.append(version)
            if not prepared_versions:
                return self._outcome(
                    request,
                    TerminalStatus.FAILED,
                    failure=Failure(
                        "triage_lineage_invalid",
                        "upstream prepared lineage is missing",
                    ),
                )
            state.prepared_versions = tuple(prepared_versions)

            attempt = AttemptIdentity(
                stable_id(
                    "triage-attempt",
                    request.execution.value,
                    self._config.configuration_version,
                    self._config.rule_config.version.version,
                    self._config.versions.configuration.version,
                    self._config.versions.prompt.version,
                    self._config.versions.model.version,
                    self._config.versions.output_schema.version,
                    self._config.semantic_fingerprint(),
                )
            )
            required = tuple(item[0] for item in loaded)
            try:
                claim = await self._persistence.acquire_claim(
                    self._config.claim_key,
                    ClaimKind.TRIAGE,
                    request.execution,
                    attempt,
                    required_inputs=required,
                    lease_seconds=self._config.lease_seconds,
                )
            except Exception as error:  # noqa: BLE001
                return self._outcome(
                    request,
                    TerminalStatus.FAILED,
                    refs=durable_prefix(),
                    failure=Failure("triage_claim_unavailable", type(error).__name__),
                )

            try:
                async with asyncio.timeout_at(state.acceptance_deadline):
                    outcome = await self._produce(request, attempt, claim, loaded)
            except TimeoutError:
                outcome = self._deadline_outcome(request)
            except asyncio.CancelledError:
                await self._cancel_claim(claim)
                raise
            except StaleClaimError:
                return self._stale(request, durable_prefix())
            except Exception as error:  # noqa: BLE001
                outcome = self._outcome(
                    request,
                    TerminalStatus.FAILED,
                    refs=durable_prefix(),
                    failure=Failure("triage_failed", type(error).__name__),
                )
            try:
                _none, cancelled = await drain(
                    self._persistence.finish_claim(
                        claim, outcome.status, ExternalEffectState.NONE
                    )
                )
            except StaleClaimError:
                return self._stale(request, durable_prefix())
            if cancelled:
                raise asyncio.CancelledError
            return outcome
        finally:
            RUN_STATE.reset(token)

    def _deadline_outcome(self, request: OperationRequest) -> OperationOutcome:
        return self._outcome(
            request,
            TerminalStatus.INCOMPLETE,
            refs=durable_prefix(),
            limitation=Limitation(
                "triage_operation_deadline",
                "Finite triage acceptance deadline expired",
            ),
        )

    def _validate_request(self, request: OperationRequest) -> Failure | None:
        if request.capability is not PhaseCapability.TRIAGE:
            return Failure("wrong_capability", "handler accepts only TRIAGE")
        if request.target_inputs != self._config.plan.expected_targets:
            return Failure("target_mismatch", "request targets do not match plan")
        keys = tuple(key for key, _value in request.parameters)
        if len(keys) != len(set(keys)):
            return Failure("duplicate_parameter", "request has duplicate parameters")
        if request.parameters != self._config.expected_parameters:
            return Failure("parameter_mismatch", "request parameters do not match plan")
        return None

    async def _preflight_upstream(
        self,
    ) -> tuple[tuple[ResultRef, StageResult], ...]:
        plan = self._config.plan
        refs = (
            *plan.prepared_results,
            *plan.filter_results,
            *plan.group_results,
            *plan.prior_triage_results,
        )
        if plan.replay_context_result is not None:
            refs = (*refs, plan.replay_context_result)
        if len(refs) > self._config.max_upstream_results:
            raise ValueError("upstream result count exceeds configured budget")
        loaded: list[tuple[ResultRef, StageResult]] = []
        total = 0
        for reference in refs:
            saved = await self._persistence.get_result(reference.result_id)
            if (
                saved is None
                or not saved.acceptable
                or saved.semantic_data_ref is None
                or result_ref(saved) != reference
            ):
                raise ValueError("required upstream result is not acceptable")
            total += saved.semantic_data_ref.byte_count
            if total > self._config.max_upstream_bytes:
                raise ValueError("upstream semantic bytes exceed configured budget")
            loaded.append((reference, saved))
        return tuple(loaded)

    async def _produce(
        self,
        request: OperationRequest,
        attempt: AttemptIdentity,
        claim: ClaimToken,
        loaded: tuple[tuple[ResultRef, StageResult], ...],
    ) -> OperationOutcome:
        by_id = {ref.result_id: saved for ref, saved in loaded}
        prepared = await self._load_values(
            self._config.plan.prepared_results, by_id, PreparedRecord
        )
        filters = await self._load_values(
            self._config.plan.filter_results, by_id, FilterResult
        )
        groups = await self._load_values(
            self._config.plan.group_results, by_id, GroupResult
        )
        priors = await self._load_priors(by_id)
        rules = await cpu_bound(evaluate_rule_set, prepared, self._config.rule_config)
        rule_ref = await self._save_rules(
            request, attempt, claim, rules, tuple(by_id.values())
        )
        context, context_result = await self._context(request, attempt, claim, by_id)
        selection = await cpu_bound(
            self._selection,
            prepared,
            filters,
            groups,
            rules,
            rule_ref,
            context,
            by_id,
        )
        snapshot = await cpu_bound(
            build_triage_input, selection, self._config.input_config
        )
        input_result = await self._save_snapshot(
            request, attempt, claim, snapshot, rule_ref, context_result
        )
        if len(snapshot.parts) > self._config.max_parts:
            raise ValueError("triage part count exceeds configured budget")

        candidates: list[TriageCandidate] = []
        states: list[TriagePartState] = []
        evidence_refs: list[ResultRef] = []
        saved_payload_values = await cpu_bound(saved_part_payloads, snapshot)
        for envelope, saved_payload in zip(
            snapshot.parts, saved_payload_values, strict=True
        ):
            part_result = await self._save_part(
                request,
                attempt,
                claim,
                envelope.part,
                saved_payload.payload,
                input_result,
            )
            candidate, state_ref, terminal_ref = await self._run_part(
                request,
                claim,
                envelope.part,
                part_result,
                input_result,
                context_result,
                context,
            )
            state = TriagePartState(
                part_ref=envelope.reference,
                attempt=self._part_attempt(request, envelope.part.part_id),
                state=(
                    PartState.COMPLETE if candidate is not None else PartState.FAILED
                ),
                ai_response_ref=terminal_ref,
                failure_code=None if candidate is not None else "part_failed",
            )
            states.append(state)
            evidence_refs.extend((state_ref, terminal_ref))
            if candidate is None:
                return self._outcome(
                    request,
                    TerminalStatus.INCOMPLETE,
                    refs=durable_prefix(),
                    limitation=Limitation(
                        "triage_part_incomplete",
                        "At least one required semantic part did not complete",
                    ),
                )
            candidates.append(candidate)

        parent_states = tuple(
            PartExecution(
                reference=item.part_ref,
                state=item.state,
                failure_code=item.failure_code,
            )
            for item in states
        )
        all_held = len(snapshot.held) == len(snapshot.selected_sources)
        if snapshot.parts:
            if not await cpu_bound(
                validate_parent_part_states, snapshot, parent_states
            ):
                return self._outcome(
                    request,
                    TerminalStatus.INCOMPLETE,
                    refs=durable_prefix(),
                    limitation=Limitation(
                        "triage_input_incomplete", "Saved input coverage is incomplete"
                    ),
                )
        elif not all_held:
            return self._outcome(
                request,
                TerminalStatus.INCOMPLETE,
                refs=durable_prefix(),
                limitation=Limitation(
                    "triage_input_missing_parts",
                    "Required semantic input has no executable parts",
                ),
            )

        combined = await cpu_bound(self._combine_candidates, candidates, snapshot)
        try:
            data = await cpu_bound(
                partial(
                    reconcile_triage,
                    combined,
                    selected_records=prepared,
                    filter_config=self._config.filter_config,
                    filter_results=filters,
                    rule_evaluation=rules,
                    topic_allocations=self._config.plan.topic_allocations,
                    prior_assessments=priors,
                )
            )
        except TriageReconciliationError as error:
            return self._outcome(
                request,
                TerminalStatus.INCOMPLETE,
                refs=durable_prefix(),
                limitation=Limitation("triage_rejected", error.code),
            )
        final_ref = await self._save_triage(
            request,
            attempt,
            claim,
            data,
            tuple(by_id.values()),
            rule_ref,
            context_result,
            input_result,
            tuple(evidence_refs),
            context,
        )
        return self._outcome(request, TerminalStatus.COMPLETE, refs=(final_ref,))
