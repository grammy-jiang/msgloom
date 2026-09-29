"""Finite awaited REPORT_BUILD operation handler."""

from __future__ import annotations

import asyncio
from time import monotonic

from pydantic import ValidationError
from pydantic_core import PydanticSerializationError

from msgloom.contracts import (
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
from msgloom.persistence import Phase1Persistence, Phase1PersistenceError
from msgloom.triage import TopicAssessment, TriageData

from .build import (
    ReportBuildError,
    build_overview,
    build_topics,
    report_limitations,
    validate_semantic_coverage,
)
from .codec import REPORT_KIND, REPORT_SCHEMA_VERSION
from .config import ReportHandlerConfig
from .history import ReportHistoryEvidence, ReportHistoryMetadata, ReportHistoryResolver
from .lifecycle import finish_quietly
from .models import (
    AssessmentSelection,
    FrozenRendererConfig,
    FrozenReportHistory,
    FrozenReportInput,
    FrozenReportSelection,
    ReportOverviewItem,
    ReportPart,
    ReportPolicy,
    ReportSelectionPlan,
    ReportTopic,
    SavedReport,
)
from .renderer import RENDERER_VERSION, RendererConfig, render_report
from .selection import ReportSelectionError, select_topics
from .selection_codec import REPORT_SELECTION_KIND, REPORT_SELECTION_SCHEMA_VERSION


class ReportBuildHandler:
    """Build one immutable report from exact already-admitted saved inputs."""

    def __init__(
        self,
        *,
        policy: ReportPolicy,
        selection_plan: ReportSelectionPlan,
        persistence: Phase1Persistence,
        renderer_config: RendererConfig,
        config: ReportHandlerConfig,
        history_resolver: ReportHistoryResolver | None = None,
    ) -> None:
        try:
            self._policy = ReportPolicy.model_validate_json(
                policy.model_dump_json(warnings="error"), strict=True
            )
            self._plan = ReportSelectionPlan.model_validate_json(
                selection_plan.model_dump_json(warnings="error"), strict=True
            )
            self._renderer = RendererConfig.model_validate_json(
                renderer_config.model_dump_json(warnings="error"), strict=True
            )
            self._config = ReportHandlerConfig.model_validate_json(
                config.model_dump_json(warnings="error"), strict=True
            )
        except (PydanticSerializationError, ValidationError, TypeError, ValueError):
            raise ValueError("report build configuration failed validation") from None
        if self._plan.prior_state and history_resolver is None:
            raise ValueError("prior report history requires a durable history resolver")
        self._persistence = persistence
        self._history_resolver = history_resolver

    async def run(self, request: OperationRequest) -> OperationOutcome:
        """Validate, admit metadata, claim, build, and publish within one deadline."""
        mismatch = self._request_mismatch(request)
        if mismatch is not None:
            return self._failed(request, "request_binding_invalid", mismatch)
        claim: ClaimToken | None = None
        durable_refs: list[ResultRef] = []
        deadline = monotonic() + self._config.timeout_seconds
        try:
            async with asyncio.timeout_at(deadline):
                _admitted, history_meta = await self._inspect_inputs()
                self._check_deadline(deadline)
                required = self._plan.triage_results + tuple(
                    item.evidence_ref for item in history_meta
                )
                claim = await self._persistence.acquire_claim(
                    self._claim_key(),
                    ClaimKind.REPORT_BUILD,
                    request.execution,
                    self._config.attempt,
                    required_inputs=required,
                    lease_seconds=self._config.claim_lease_seconds,
                )
                loaded = await self._load_inputs()
                history = await self._resolve_history(history_meta)
                selected = select_topics(self._policy, self._plan, loaded)
                snapshot = self._selection_snapshot(loaded, selected, history)
                selection_result = self._selection_stage_result(request, snapshot)
                self._check_deadline(deadline)
                await self._persistence.append_result_with_data(
                    selection_result, snapshot, claim=claim
                )
                selection_ref = ResultRef(
                    selection_result.result_id,
                    selection_result.kind,
                    selection_result.schema_version,
                )
                durable_refs.append(selection_ref)
                topics = build_topics(selected, self._plan)
                overview = build_overview(topics)
                validate_semantic_coverage(topics, overview)
                upstream = tuple(
                    limitation
                    for _ref, result, _data in loaded
                    for limitation in result.limitations
                )
                limitations = report_limitations(topics, self._plan, upstream)
                parts = await self._render_owned(
                    overview, topics, limitations, deadline
                )
                report = SavedReport(
                    report_ref=self._config.report_ref,
                    policy_ref=self._policy.policy_ref,
                    destination=self._policy.destination,
                    due_at=self._policy.due_at,
                    timezone=self._policy.timezone,
                    source_triage_results=self._plan.triage_results,
                    topics=topics,
                    overview=overview,
                    pending_warnings=self._plan.pending_warnings,
                    limitations=limitations,
                    renderer_version=RENDERER_VERSION,
                    parts=parts,
                )
                status = (
                    TerminalStatus.INCOMPLETE
                    if limitations
                    else TerminalStatus.COMPLETE
                )
                result = self._stage_result(request, report, status)
                self._check_deadline(deadline)
                await self._persistence.append_result_with_data(
                    result, report, claim=claim
                )
                report_result_ref = ResultRef(
                    result.result_id, result.kind, result.schema_version
                )
                durable_refs.append(report_result_ref)
                self._check_deadline(deadline)
                await self._persistence.finish_claim(
                    claim, status, ExternalEffectState.NONE
                )
                claim = None
                return OperationOutcome(
                    execution=request.execution,
                    capability=request.capability,
                    status=status,
                    result_refs=(report_result_ref,),
                    limitations=limitations,
                    external_effect=ExternalEffectState.NONE,
                )
        except asyncio.CancelledError:
            if claim is not None:
                await finish_quietly(self._persistence, claim, TerminalStatus.CANCELLED)
            raise
        except TimeoutError:
            if claim is not None:
                await finish_quietly(self._persistence, claim, TerminalStatus.FAILED)
            return self._failed(
                request,
                "report_build_timeout",
                "Report build timed out",
                tuple(durable_refs),
            )
        except (ReportSelectionError, ReportBuildError, TypeError, ValueError):
            if claim is not None:
                await finish_quietly(self._persistence, claim, TerminalStatus.FAILED)
            return self._failed(
                request,
                "report_build_invalid",
                "Report build input or output failed validation",
                tuple(durable_refs),
            )
        except Phase1PersistenceError:
            if claim is not None:
                await finish_quietly(self._persistence, claim, TerminalStatus.FAILED)
            return self._failed(
                request,
                "report_build_failed",
                "Report build persistence or ownership failed",
                tuple(durable_refs),
            )

    async def _inspect_inputs(
        self,
    ) -> tuple[
        tuple[tuple[ResultRef, StageResult], ...],
        tuple[ReportHistoryMetadata, ...],
    ]:
        """Inspect and sum all declared metadata before claim acquisition."""
        admitted: list[tuple[ResultRef, StageResult]] = []
        total = 0
        for ref in self._plan.triage_results:
            result = await self._persistence.get_result(ref.result_id)
            if result is None or result.semantic_data_ref is None:
                raise ReportSelectionError("selected triage result is missing")
            if (
                result.result_id != ref.result_id
                or result.kind != "triage"
                or result.schema_version != "1"
            ):
                raise ReportSelectionError(
                    "selected triage result reference mismatches"
                )
            total += result.semantic_data_ref.byte_count
            if total > self._config.max_input_bytes:
                raise ReportSelectionError("selected semantic inputs exceed byte limit")
            admitted.append((ref, result))
        history: list[ReportHistoryMetadata] = []
        resolver = self._history_resolver
        for state in self._plan.prior_state:
            if resolver is None or state.evidence_ref is None:
                raise ReportSelectionError(
                    "prior report history resolver is unavailable"
                )
            metadata = await resolver.inspect(state.evidence_ref)
            metadata = ReportHistoryMetadata.model_validate_json(
                metadata.model_dump_json(warnings="error"), strict=True
            )
            result = await self._persistence.get_result(state.evidence_ref.result_id)
            if (
                result is None
                or result.result_id != state.evidence_ref.result_id
                or result.kind != "report_submission"
                or result.schema_version != "1"
                or not result.acceptable
                or result.status
                not in {TerminalStatus.COMPLETE, TerminalStatus.INCOMPLETE}
                or metadata.evidence_ref != state.evidence_ref
                or metadata.semantic_data_ref != result.semantic_data_ref
            ):
                raise ReportSelectionError("prior report history metadata mismatches")
            if result.semantic_data_ref is not None:
                total += result.semantic_data_ref.byte_count
                if total > self._config.max_input_bytes:
                    raise ReportSelectionError(
                        "selected semantic inputs exceed byte limit"
                    )
            history.append(metadata)
        return tuple(admitted), tuple(history)

    async def _load_inputs(
        self,
    ) -> tuple[tuple[ResultRef, StageResult, TriageData], ...]:
        """Reload bounded metadata after claim, then resolve admitted semantic data."""
        admitted, _history = await self._inspect_inputs()
        return await self._load_admitted(admitted)

    async def _load_admitted(
        self, admitted: tuple[tuple[ResultRef, StageResult], ...]
    ) -> tuple[tuple[ResultRef, StageResult, TriageData], ...]:
        loaded = []
        for ref, result in admitted:
            data_ref = result.semantic_data_ref
            if data_ref is None:
                raise ReportSelectionError("selected triage semantic data is missing")
            data = await self._persistence.load_semantic_data(data_ref)
            if not isinstance(data, TriageData):
                raise ReportSelectionError("selected semantic input is not triage@1")
            loaded.append((ref, result, data))
        return tuple(loaded)

    async def _resolve_history(
        self, metadata: tuple[ReportHistoryMetadata, ...]
    ) -> tuple[ReportHistoryEvidence, ...]:
        resolver = self._history_resolver
        if metadata and resolver is None:
            raise ReportSelectionError("prior report history resolver is unavailable")
        resolved = []
        for state, meta in zip(self._plan.prior_state, metadata, strict=True):
            if resolver is None:
                raise ReportSelectionError(
                    "prior report history resolver is unavailable"
                )
            evidence = await resolver.resolve(meta)
            evidence = ReportHistoryEvidence.model_validate_json(
                evidence.model_dump_json(warnings="error"), strict=True
            )
            if (
                evidence.evidence_ref != state.evidence_ref
                or evidence.report_ref != state.report_ref
                or evidence.policy_ref != state.policy_ref
                or evidence.assessment_ref != state.assessment_ref
                or evidence.reported_at != state.reported_at
                or evidence.semantic_data_ref != meta.semantic_data_ref
            ):
                raise ReportSelectionError("prior report evidence does not match state")
            resolved.append(evidence)
        return tuple(resolved)

    def _selection_snapshot(
        self,
        loaded: tuple[tuple[ResultRef, StageResult, TriageData], ...],
        selected: tuple[TopicAssessment, ...],
        history: tuple[ReportHistoryEvidence, ...],
    ) -> FrozenReportSelection:
        inputs = tuple(
            FrozenReportInput(
                result_ref=ref, semantic_data_ref=result.semantic_data_ref
            )
            for ref, result, _data in loaded
            if result.semantic_data_ref is not None
        )
        choices = tuple(
            AssessmentSelection(
                topic_ref=item.topic_ref, assessment_ref=item.assessment_ref
            )
            for item in selected
        )
        frozen_history = tuple(
            FrozenReportHistory(
                evidence_ref=item.evidence_ref,
                report_ref=item.report_ref,
                policy_ref=item.policy_ref,
                assessment_ref=item.assessment_ref,
                reported_at=item.reported_at,
                receipt_ref=item.receipt_ref,
                semantic_data_ref=item.semantic_data_ref,
            )
            for item in history
        )
        return FrozenReportSelection(
            report_ref=self._config.report_ref,
            policy=self._policy,
            plan=self._plan,
            renderer=FrozenRendererConfig(
                max_part_bytes=self._renderer.max_part_bytes,
                max_total_bytes=self._renderer.max_total_bytes,
                max_parts=self._renderer.max_parts,
            ),
            code_version=self._config.code_version,
            expected_parameters=self._config.expected_parameters,
            inputs=inputs,
            selected=choices,
            history=frozen_history,
        )

    def _selection_stage_result(
        self, request: OperationRequest, snapshot: FrozenReportSelection
    ) -> StageResult:
        data_ref = self._persistence.semantic_reference(
            self._config.selection_semantic_data_id,
            REPORT_SELECTION_KIND,
            REPORT_SELECTION_SCHEMA_VERSION,
            snapshot,
        )
        return StageResult(
            result_id=self._config.selection_result_id,
            kind=REPORT_SELECTION_KIND,
            schema_version=REPORT_SELECTION_SCHEMA_VERSION,
            execution=request.execution,
            attempt=self._config.attempt,
            input_refs=self._plan.triage_results
            + tuple(x.evidence_ref for x in snapshot.history),
            source_versions=(),
            prepared_versions=(),
            topic_versions=tuple(x.assessment_ref for x in snapshot.selected),
            configuration_version=self._policy.policy_ref.version,
            code_version=self._config.code_version,
            status=TerminalStatus.COMPLETE,
            acceptable=True,
            semantic_data_ref=data_ref,
        )

    async def _render_owned(
        self,
        overview: tuple[ReportOverviewItem, ...],
        topics: tuple[ReportTopic, ...],
        limitations: tuple[Limitation, ...],
        deadline: float,
    ) -> tuple[ReportPart, ...]:
        task = asyncio.create_task(
            asyncio.to_thread(
                render_report,
                self._config.report_ref,
                overview,
                topics,
                self._plan.pending_warnings,
                self._renderer,
                limitations,
            )
        )
        cancelled = False
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                cancelled = True
        error = task.exception()
        if error is not None:
            raise error
        if cancelled:
            raise asyncio.CancelledError
        self._check_deadline(deadline)
        return task.result()

    def _stage_result(
        self, request: OperationRequest, report: SavedReport, status: TerminalStatus
    ) -> StageResult:
        data_ref = self._persistence.semantic_reference(
            self._config.semantic_data_id, REPORT_KIND, REPORT_SCHEMA_VERSION, report
        )
        return StageResult(
            result_id=self._config.result_id,
            kind=REPORT_KIND,
            schema_version=REPORT_SCHEMA_VERSION,
            execution=request.execution,
            attempt=self._config.attempt,
            input_refs=(
                ResultRef(
                    self._config.selection_result_id,
                    REPORT_SELECTION_KIND,
                    REPORT_SELECTION_SCHEMA_VERSION,
                ),
            ),
            source_versions=tuple(
                source for topic in report.topics for source in topic.source_refs
            ),
            prepared_versions=(),
            topic_versions=tuple(topic.assessment_ref for topic in report.topics),
            configuration_version=self._policy.policy_ref.version,
            code_version=self._config.code_version,
            status=status,
            acceptable=True,
            semantic_data_ref=data_ref,
            limitations=report.limitations,
        )

    def _request_mismatch(self, request: OperationRequest) -> str | None:
        if request.capability is not PhaseCapability.REPORT_BUILD:
            return "handler only accepts REPORT_BUILD"
        if request.target_inputs != self._plan.request_targets:
            return "request target references do not match trusted selection"
        if request.parameters != self._config.expected_parameters:
            return "request parameters do not match trusted configuration"
        keys = tuple(key for key, _value in request.parameters)
        if len(keys) != len(set(keys)):
            return "request contains duplicate parameters"
        return None

    def _claim_key(self) -> str:
        ref = self._policy.policy_ref
        return f"report-build:{ref.kind}:{ref.identity}:{ref.version}"

    @staticmethod
    def _check_deadline(deadline: float) -> None:
        if monotonic() >= deadline:
            raise TimeoutError

    @staticmethod
    def _failed(
        request: OperationRequest,
        code: str,
        detail: str,
        result_refs: tuple[ResultRef, ...] = (),
    ) -> OperationOutcome:
        return OperationOutcome(
            execution=request.execution,
            capability=request.capability,
            status=TerminalStatus.FAILED,
            result_refs=result_refs,
            failures=(Failure(code=code, detail=detail),),
            external_effect=ExternalEffectState.NONE,
        )
