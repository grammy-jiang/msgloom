"""Keep durable delivery progress when cancellation interrupts settlement."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import cast

import pytest

from msgloom.contracts import (
    AttemptIdentity,
    ExecutionIdentity,
    ExternalEffectState,
    OperationRequest,
    PhaseCapability,
    ResultRef,
    TerminalStatus,
    VersionRef,
)
from msgloom.delivery import (
    ReportSubmissionHandler,
    ReportSubmissionPlan,
    SubmissionHandlerConfig,
    SubmissionPartPlan,
)
from msgloom.delivery.part import DeliveryProgress
from msgloom.persistence import Phase1Persistence
from msgloom.reporting import SavedReport
from tests.delivery.helpers import RecordingTransport


class SettlementStore:
    """Model durable claim writes with a controlled finite settlement barrier."""

    def __init__(self) -> None:
        self.token = SimpleNamespace(claim_key="settlement-claim")
        self.effect = ExternalEffectState.NOT_STARTED
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.finished = False

    async def acquire_claim(self, *args, **kwargs):
        """Return the owned claim without database or provider access."""
        return self.token

    async def mark_external_effect(self, token, effect):
        """Record the pre-transport durable barrier."""
        self.effect = effect

    async def inspect_claim(self, key):
        """Expose the durable effect for real interrupted-state recovery."""
        return SimpleNamespace(current_token=self.token, current_effect=self.effect)

    async def get_result(self, result_id):
        """Report no saved receipt after the transport failure."""
        return

    async def finish_claim(self, token, status, effect):
        """Commit the recovered effect, then delay write acknowledgement."""
        self.effect = effect
        self.entered.set()
        await self.release.wait()
        self.finished = True


class FailingSettlementStore(SettlementStore):
    """Expose durable recovery evidence, then fail terminal acknowledgement."""

    def __init__(self, recovered_effect: ExternalEffectState) -> None:
        super().__init__()
        self.recovered_effect = recovered_effect

    async def inspect_claim(self, key):
        """Model stronger durable state recovered after transport interruption."""
        return SimpleNamespace(
            current_token=self.token, current_effect=self.recovered_effect
        )

    async def finish_claim(self, token, status, effect):
        """Raise after the controlled terminal write has completed."""
        await super().finish_claim(token, status, effect)
        raise RuntimeError("Phase 1 persistence is closing or closed")


def settlement_handler(monkeypatch, store, *, timeout=30.0):
    """Use real submit, recovery, and outcome logic with in-memory boundaries."""
    part = SubmissionPartPlan(
        part_number=1,
        attempt_result_id="saved-attempt",
        receipt_result_id="missing-receipt",
    )
    plan = ReportSubmissionPlan(
        report_result_ref=ResultRef("report-result", "report", "1"),
        report_ref=VersionRef("report", "report", "1"),
        policy_ref=VersionRef("report-policy", "policy", "1"),
        owner_identity="owner@example.com",
        destination_identity="owner@example.com",
        parts=(part,),
        expected_parameters=(),
    )
    handler = ReportSubmissionHandler(
        plan=plan,
        config=SubmissionHandlerConfig(
            attempt=AttemptIdentity("settlement-attempt"),
            code_version="test",
            timeout_seconds=timeout,
            claim_lease_seconds=60.0,
        ),
        persistence=cast(Phase1Persistence, store),
        transport=RecordingTransport(TimeoutError("transport deadline")),
    )
    request = OperationRequest(
        execution=ExecutionIdentity("settlement-execution"),
        caller="owner",
        capability=PhaseCapability.REPORT_SUBMIT,
        target_inputs=(plan.report_ref, plan.policy_ref),
        authority_ref="trusted-submit",
        parameters=(),
    )
    report = cast(
        SavedReport,
        SimpleNamespace(
            parts=(SimpleNamespace(topic_refs=()),),
            topics=(),
            report_ref=plan.report_ref,
            policy_ref=plan.policy_ref,
        ),
    )

    async def prepare(*args):
        return b"saved-send-bytes", ResultRef("saved-attempt", "report_submission", "1")

    async def load_report():
        return report

    async def existing_effect(part_plan):
        return None

    monkeypatch.setattr(handler._parts, "_prepare_attempt", prepare)
    monkeypatch.setattr(handler._parts, "existing_effect", existing_effect)
    monkeypatch.setattr(handler, "_load_report", load_report)
    return handler, request


def test_total_timeout_preserves_settled_effect_and_refs(monkeypatch) -> None:
    """A deadline during failed-send settlement must retain durable evidence."""

    async def exercise() -> None:
        store = SettlementStore()
        handler, request = settlement_handler(monkeypatch, store)
        deadline = asyncio.timeout(None)
        monkeypatch.setattr(asyncio, "timeout", lambda seconds: deadline)

        async def release_settlement():
            await store.entered.wait()
            # Expire the real total-budget context at the durable write barrier.
            # Schedule release after timeout dispatch, without timing races.
            loop = asyncio.get_running_loop()
            deadline.reschedule(loop.time())
            loop.call_soon(loop.call_soon, store.release.set)

        release_task = asyncio.create_task(release_settlement())
        try:
            outcome = await handler.run(request)
        finally:
            store.release.set()
            await release_task
        if outcome.external_effect is not ExternalEffectState.UNKNOWN:
            pytest.fail("deadline discarded the durable UNKNOWN effect")
        if outcome.result_refs != (
            ResultRef("saved-attempt", "report_submission", "1"),
        ):
            pytest.fail("deadline discarded the saved attempt reference")
        if outcome.status is not TerminalStatus.INCOMPLETE:
            pytest.fail("an interrupted submission must remain incomplete")
        if not store.finished:
            pytest.fail("handler returned before settlement finished")

    asyncio.run(exercise())


def test_repeated_cancellation_drains_settlement_and_retains_progress(monkeypatch):
    """Repeated caller cancellation must not cancel owned settlement writes."""

    async def exercise() -> None:
        store = SettlementStore()
        handler, request = settlement_handler(monkeypatch, store)
        progress = DeliveryProgress()
        task = asyncio.create_task(handler._run_budgeted(request, progress))
        await store.entered.wait()
        task.cancel()
        loop = asyncio.get_running_loop()
        loop.call_soon(task.cancel)
        loop.call_soon(store.release.set)
        with pytest.raises(asyncio.CancelledError):
            await task
        if progress.effects != [ExternalEffectState.UNKNOWN]:
            pytest.fail("repeated cancellation lost the settled effect")
        if progress.refs != [ResultRef("saved-attempt", "report_submission", "1")]:
            pytest.fail("repeated cancellation lost the durable attempt")
        if not store.finished:
            pytest.fail("cancellation returned before settlement finished")

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "effect",
    [
        ExternalEffectState.UNKNOWN,
        ExternalEffectState.ACCEPTED,
        ExternalEffectState.CONFIRMED,
    ],
)
def test_late_settlement_error_preserves_deadline_outcome(monkeypatch, effect):
    """Late cleanup failure cannot erase recovered truth or the attempt prefix."""

    async def exercise() -> None:
        store = FailingSettlementStore(effect)
        handler, request = settlement_handler(monkeypatch, store)
        deadline = asyncio.timeout(None)
        monkeypatch.setattr(asyncio, "timeout", lambda seconds: deadline)

        async def release_settlement():
            await store.entered.wait()
            loop = asyncio.get_running_loop()
            deadline.reschedule(loop.time())
            loop.call_soon(loop.call_soon, store.release.set)

        release_task = asyncio.create_task(release_settlement())
        try:
            outcome = await handler.run(request)
        finally:
            store.release.set()
            await release_task
        if outcome.external_effect is not effect:
            pytest.fail("late settlement failure discarded the recovered effect")
        if outcome.result_refs != (
            ResultRef("saved-attempt", "report_submission", "1"),
        ):
            pytest.fail("late settlement failure discarded the durable prefix")
        if outcome.status is not TerminalStatus.INCOMPLETE:
            pytest.fail("late cleanup must not produce operation success")
        if not store.finished:
            pytest.fail("deadline returned before the terminal write finished")

    asyncio.run(exercise())


def test_late_settlement_error_preserves_original_cancellation(monkeypatch):
    """Repeated cancellation keeps the original stop and recovered progress."""

    async def exercise() -> None:
        store = FailingSettlementStore(ExternalEffectState.UNKNOWN)
        handler, request = settlement_handler(monkeypatch, store)
        progress = DeliveryProgress()
        task = asyncio.create_task(handler._run_budgeted(request, progress))
        await store.entered.wait()
        task.cancel("original stop")
        loop = asyncio.get_running_loop()
        loop.call_soon(task.cancel, "later stop")
        loop.call_soon(store.release.set)
        with pytest.raises(asyncio.CancelledError, match="original stop"):
            await task
        if progress.effects != [ExternalEffectState.UNKNOWN]:
            pytest.fail("late cleanup error lost the durable UNKNOWN effect")
        if progress.refs != [ResultRef("saved-attempt", "report_submission", "1")]:
            pytest.fail("late cleanup error lost the durable attempt prefix")
        if not store.finished:
            pytest.fail("cancellation returned before settlement finished")
        if asyncio.all_tasks() != {asyncio.current_task()}:
            pytest.fail("cancellation left a delivery-owned task running")

    asyncio.run(exercise())
