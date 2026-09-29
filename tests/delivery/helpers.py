"""Synthetic real-SQLite helpers for report delivery tests."""

from __future__ import annotations

import asyncio
from collections import deque
from pathlib import Path

from msgloom.contracts import (
    AttemptIdentity,
    ExecutionIdentity,
    ExternalEffectState,
    OperationRequest,
    PhaseCapability,
    ResultRef,
    ResultSchemaRegistry,
    TerminalStatus,
)
from msgloom.delivery import (
    ReportSubmissionCodec,
    ReportSubmissionHandler,
    ReportSubmissionPlan,
    ReportTransport,
    SubmissionHandlerConfig,
    SubmissionPartPlan,
    TransportReceipt,
)
from msgloom.persistence import Phase1Persistence, SemanticDataRegistry
from msgloom.reporting import ReportCodec, ReportSelectionCodec, SavedReport
from msgloom.triage import TriageDataCodec
from tests.reporting.helpers import plan, save_triage, topic, triage_data
from tests.reporting.test_handler import _handler as build_handler
from tests.reporting.test_handler import _request as build_request


class RecordingTransport:
    """Deterministic fake transport with no provider or network access."""

    def __init__(self, *responses: object) -> None:
        self.responses = deque(responses)
        self.calls: list[bytes] = []
        self.entered = asyncio.Event()
        self.release: asyncio.Event | None = None

    async def submit(
        self, send_bytes: bytes, *, timeout_seconds: float
    ) -> TransportReceipt:
        """Record exact bytes and return or raise the configured response."""
        self.calls.append(send_bytes)
        self.entered.set()
        if self.release is not None:
            await self.release.wait()
        if not self.responses:
            return TransportReceipt(ExternalEffectState.ACCEPTED, "202")
        response = self.responses.popleft()
        if isinstance(response, BaseException):
            raise response
        if not isinstance(response, TransportReceipt):
            raise TypeError("synthetic response is invalid")
        return response


def semantic_registry() -> SemanticDataRegistry:
    """Compose only codecs needed by the integrated report delivery tests."""
    return SemanticDataRegistry(
        (
            TriageDataCodec(),
            ReportSelectionCodec(),
            ReportCodec(),
            ReportSubmissionCodec(),
        )
    )


async def open_store(path: Path) -> Phase1Persistence:
    """Open real SQLite with lane-local delivery semantic data enabled."""
    return await Phase1Persistence.open(
        f"sqlite:///{path}",
        registry=ResultSchemaRegistry.phase1(),
        semantic_registry=semantic_registry(),
    )


async def build_report(store: Phase1Persistence) -> tuple[ResultRef, SavedReport]:
    """Build an actual report through ReportBuildHandler and reload it."""
    triage_ref = await save_triage(store, triage_data(topic()))
    selection = plan(triage_ref)
    outcome = await build_handler(store, selection).run(build_request(selection))
    if outcome.status is not TerminalStatus.COMPLETE:
        raise RuntimeError("synthetic report build failed")
    ref = outcome.result_refs[0]
    result = await store.get_result(ref.result_id)
    if result is None or result.semantic_data_ref is None:
        raise RuntimeError("synthetic report result is missing")
    value = await store.load_semantic_data(result.semantic_data_ref)
    if not isinstance(value, SavedReport):
        raise TypeError("synthetic report payload has the wrong type")
    return ref, value


def submission_plan(
    report_ref: ResultRef,
    report: SavedReport,
    *,
    suffix: str = "one",
    destination: str | None = None,
    replay: ResultRef | None = None,
) -> ReportSubmissionPlan:
    """Build one trusted submission plan for every saved report part."""
    parts = tuple(
        SubmissionPartPlan(
            part_number=part.part_number,
            attempt_result_id=f"submit-attempt-{suffix}-{part.part_number}",
            receipt_result_id=f"submit-receipt-{suffix}-{part.part_number}",
            replay_attempt_ref=replay if part.part_number == 1 else None,
        )
        for part in report.parts
    )
    return ReportSubmissionPlan(
        report_result_ref=report_ref,
        report_ref=report.report_ref,
        policy_ref=report.policy_ref,
        owner_identity=report.destination.owner_identity,
        destination_identity=destination or report.destination.destination_identity,
        parts=parts,
        expected_parameters=(("mode", "scheduled"),),
    )


def submission_request(
    plan_value: ReportSubmissionPlan, *, identity: str = "submit-execution"
) -> OperationRequest:
    """Build the exact Application-facing REPORT_SUBMIT request."""
    return OperationRequest(
        execution=ExecutionIdentity(identity),
        caller="synthetic-owner",
        capability=PhaseCapability.REPORT_SUBMIT,
        target_inputs=(plan_value.report_ref, plan_value.policy_ref),
        authority_ref="trusted-report-submit",
        parameters=plan_value.expected_parameters,
    )


def submission_handler(
    store: Phase1Persistence,
    plan_value: ReportSubmissionPlan,
    transport: ReportTransport,
    *,
    attempt: str = "submit-attempt",
    timeout: float = 30.0,
) -> ReportSubmissionHandler:
    """Build a finite handler with explicit synthetic transport."""
    return ReportSubmissionHandler(
        plan=plan_value,
        config=SubmissionHandlerConfig(
            attempt=AttemptIdentity(attempt),
            code_version="delivery-test",
            timeout_seconds=timeout,
            claim_lease_seconds=max(3.0, timeout + 1.0),
        ),
        persistence=store,
        transport=transport,
    )
