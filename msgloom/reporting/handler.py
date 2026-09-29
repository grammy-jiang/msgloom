"""Finite awaited REPORT_BUILD operation handler."""

from __future__ import annotations

import asyncio
from time import monotonic
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from msgloom.contracts import (
    AttemptIdentity,
    ClaimKind,
    ClaimToken,
    ExternalEffectState,
    Failure,
    OperationOutcome,
    OperationRequest,
    PhaseCapability,
    ResultRef,
    StageResult,
    TerminalStatus,
    VersionRef,
)
from msgloom.persistence import Phase1Persistence, Phase1PersistenceError
from msgloom.triage import TriageData

from .build import (
    ReportBuildError,
    build_overview,
    build_topics,
    report_limitations,
    validate_semantic_coverage,
)
from .codec import REPORT_KIND, REPORT_SCHEMA_VERSION
from .models import ReportPolicy, ReportSelectionPlan, SavedReport
from .renderer import RENDERER_VERSION, RendererConfig, render_report
from .selection import ReportSelectionError, select_topics


class ReportHandlerConfig(BaseModel):
    """Trusted finite identities and budget for one configured build."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    report_ref: VersionRef
    result_id: Annotated[str, Field(min_length=1, max_length=256)]
    semantic_data_id: Annotated[str, Field(min_length=1, max_length=256)]
    attempt: AttemptIdentity
    code_version: Annotated[str, Field(min_length=1, max_length=256)]
    expected_parameters: Annotated[tuple[tuple[str, str], ...], Field(max_length=32)]
    timeout_seconds: Annotated[float, Field(gt=0.0, le=300.0)]
    claim_lease_seconds: Annotated[float, Field(gt=0.0, le=600.0)]

    @model_validator(mode="after")
    def _budget_fits_lease(self) -> ReportHandlerConfig:
        keys = tuple(key for key, _value in self.expected_parameters)
        if len(keys) != len(set(keys)):
            raise ValueError("trusted handler parameters must have unique keys")
        if self.claim_lease_seconds < self.timeout_seconds + 1.0:
            raise ValueError("claim lease must exceed the finite operation budget")
        return self


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
    ) -> None:
        self._policy = policy
        self._plan = selection_plan
        self._persistence = persistence
        self._renderer = renderer_config
        self._config = config

    async def run(self, request: OperationRequest) -> OperationOutcome:
        """Validate request binding, claim policy scope, build, and persist."""
        mismatch = self._request_mismatch(request)
        if mismatch is not None:
            return self._failed(request, "request_binding_invalid", mismatch)
        claim = None
        started = monotonic()
        try:
            claim = await self._persistence.acquire_claim(
                self._claim_key(),
                ClaimKind.REPORT_BUILD,
                request.execution,
                self._config.attempt,
                required_inputs=self._plan.triage_results,
                lease_seconds=self._config.claim_lease_seconds,
            )
            async with asyncio.timeout(self._config.timeout_seconds):
                loaded = await self._load_inputs()
                selected = select_topics(self._policy, self._plan, loaded)
                topics = build_topics(selected, self._plan)
                overview = build_overview(topics)
                validate_semantic_coverage(topics, overview)
                limitations = report_limitations(topics, self._plan)
                parts = render_report(
                    self._config.report_ref,
                    overview,
                    topics,
                    self._plan.pending_warnings,
                    self._renderer,
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
                if monotonic() - started >= self._config.claim_lease_seconds:
                    raise ReportBuildError("report build claim lease expired")
                await self._persistence.append_result_with_data(result, report)
                if monotonic() - started >= self._config.claim_lease_seconds:
                    raise ReportBuildError("report build claim lease expired")
                await self._persistence.finish_claim(
                    claim, status, ExternalEffectState.NONE
                )
                claim = None
                return OperationOutcome(
                    execution=request.execution,
                    capability=request.capability,
                    status=status,
                    result_refs=(
                        ResultRef(
                            result_id=result.result_id,
                            kind=result.kind,
                            schema_version=result.schema_version,
                        ),
                    ),
                    limitations=limitations,
                    external_effect=ExternalEffectState.NONE,
                )
        except asyncio.CancelledError:
            if claim is not None:
                await self._finish_after_interrupt(claim, TerminalStatus.CANCELLED)
            raise
        except TimeoutError:
            if claim is not None:
                await self._finish_after_interrupt(claim, TerminalStatus.FAILED)
            return self._failed(
                request, "report_build_timeout", "Report build timed out"
            )
        except (ReportSelectionError, ReportBuildError, TypeError, ValueError):
            if claim is not None:
                await self._finish_after_interrupt(claim, TerminalStatus.FAILED)
            return self._failed(
                request,
                "report_build_invalid",
                "Report build input or output failed validation",
            )
        except Phase1PersistenceError:
            if claim is not None:
                await self._finish_after_interrupt(claim, TerminalStatus.FAILED)
            return self._failed(
                request,
                "report_build_failed",
                "Report build persistence or ownership failed",
            )

    async def _load_inputs(
        self,
    ) -> tuple[tuple[ResultRef, StageResult, TriageData], ...]:
        loaded = []
        for ref in self._plan.triage_results:
            result = await self._persistence.get_result(ref.result_id)
            if result is None:
                raise ReportSelectionError("selected triage result is missing")
            if (
                result.result_id != ref.result_id
                or result.kind != ref.kind
                or result.schema_version != ref.schema_version
                or result.semantic_data_ref is None
            ):
                raise ReportSelectionError(
                    "selected triage result reference mismatches"
                )
            data = await self._persistence.load_semantic_data(result.semantic_data_ref)
            if not isinstance(data, TriageData):
                raise ReportSelectionError("selected semantic input is not triage@1")
            loaded.append((ref, result, data))
        return tuple(loaded)

    def _stage_result(
        self,
        request: OperationRequest,
        report: SavedReport,
        status: TerminalStatus,
    ) -> StageResult:
        data_ref = self._persistence.semantic_reference(
            self._config.semantic_data_id,
            REPORT_KIND,
            REPORT_SCHEMA_VERSION,
            report,
        )
        source_versions = tuple(
            source for topic in report.topics for source in topic.source_refs
        )
        topic_versions = tuple(topic.assessment_ref for topic in report.topics)
        return StageResult(
            result_id=self._config.result_id,
            kind=REPORT_KIND,
            schema_version=REPORT_SCHEMA_VERSION,
            execution=request.execution,
            attempt=self._config.attempt,
            input_refs=self._plan.triage_results,
            source_versions=source_versions,
            prepared_versions=(),
            topic_versions=topic_versions,
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

    async def _finish_after_interrupt(
        self,
        claim: ClaimToken,
        status: TerminalStatus,
    ) -> None:
        task = asyncio.create_task(
            self._persistence.finish_claim(claim, status, ExternalEffectState.NONE)
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

    @staticmethod
    def _failed(
        request: OperationRequest,
        code: str,
        detail: str,
    ) -> OperationOutcome:
        return OperationOutcome(
            execution=request.execution,
            capability=request.capability,
            status=TerminalStatus.FAILED,
            failures=(Failure(code=code, detail=detail),),
            external_effect=ExternalEffectState.NONE,
        )
