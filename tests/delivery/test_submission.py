"""Integrated saved-report submission lifecycle regressions."""

from __future__ import annotations

import asyncio
from hashlib import sha256
from pathlib import Path

import pytest

from msgloom.contracts import (
    ExternalEffectState,
    ResultRef,
    TerminalStatus,
)
from msgloom.delivery import (
    DeliveryReportHistoryResolver,
    SubmissionAttempt,
    SubmissionReceipt,
    TransportReceipt,
)
from msgloom.persistence import Phase1PersistenceError
from tests.delivery.helpers import (
    RecordingTransport,
    build_report,
    open_store,
    submission_handler,
    submission_plan,
    submission_request,
)


def test_owner_only_binding_and_injection_rejected_before_transport(
    tmp_path: Path,
) -> None:
    """Saved destination mismatch and recipient injection never reach transport."""

    async def exercise() -> None:
        store = await open_store(tmp_path / "owner.sqlite3")
        try:
            report_ref, report = await build_report(store)
            transport = RecordingTransport()
            with pytest.raises(ValueError, match="extra recipients"):
                submission_handler(
                    store,
                    submission_plan(
                        report_ref,
                        report,
                        destination="owner@example.invalid,other@example.invalid",
                    ),
                    transport,
                )
            wrong = submission_plan(
                report_ref, report, destination="other@example.invalid"
            )
            outcome = await submission_handler(store, wrong, transport).run(
                submission_request(wrong)
            )
            if outcome.status is not TerminalStatus.FAILED:
                pytest.fail("mismatched saved destination was not rejected")
            if transport.calls:
                pytest.fail("destination mismatch reached external transport")
        finally:
            await store.close()

    asyncio.run(exercise())


@pytest.mark.parametrize(
    ("receipt", "status", "effect", "acceptable"),
    [
        (
            TransportReceipt(ExternalEffectState.ACCEPTED, "202", "request-a"),
            TerminalStatus.COMPLETE,
            ExternalEffectState.ACCEPTED,
            True,
        ),
        (
            TransportReceipt(ExternalEffectState.CONFIRMED, "confirmed", "proof-a"),
            TerminalStatus.COMPLETE,
            ExternalEffectState.CONFIRMED,
            True,
        ),
        (
            TransportReceipt(ExternalEffectState.REJECTED, "400", "request-r"),
            TerminalStatus.INCOMPLETE,
            ExternalEffectState.REJECTED,
            False,
        ),
    ],
)
def test_definite_receipts_persist_before_effect_and_survive_restart(
    tmp_path: Path,
    receipt: TransportReceipt,
    status: TerminalStatus,
    effect: ExternalEffectState,
    acceptable: bool,
) -> None:
    """Accepted, confirmed, and rejected provider responses remain distinct."""

    async def exercise() -> None:
        path = tmp_path / f"{receipt.effect.value}.sqlite3"
        first = await open_store(path)
        report_ref, report = await build_report(first)
        plan_value = submission_plan(report_ref, report, suffix=receipt.effect.value)
        transport = RecordingTransport(receipt)
        outcome = await submission_handler(first, plan_value, transport).run(
            submission_request(plan_value)
        )
        if outcome.status is not status or outcome.external_effect is not effect:
            pytest.fail("submission outcome classification changed")
        receipt_ref = ResultRef(
            plan_value.parts[0].receipt_result_id, "report_submission", "1"
        )
        stored = await first.get_result(receipt_ref.result_id)
        if stored is None or stored.acceptable is not acceptable:
            pytest.fail("provider receipt acceptability is wrong")
        await first.close()

        second = await open_store(path)
        try:
            stored = await second.get_result(receipt_ref.result_id)
            if stored is None or stored.semantic_data_ref is None:
                pytest.fail("provider receipt did not survive restart")
            payload = await second.load_semantic_data(stored.semantic_data_ref)
            if not isinstance(payload, SubmissionReceipt):
                pytest.fail("stored receipt has the wrong semantic type")
            if payload.effect is not receipt.effect:
                pytest.fail("stored receipt lost exact provider effect")
            if acceptable:
                resolver = DeliveryReportHistoryResolver(second)
                history_ids = [
                    ref
                    for ref in outcome.result_refs
                    if ref.result_id.startswith("report-history-")
                ]
                if history_ids:
                    pytest.fail("history refs must not be exposed as send receipts")
                assessment = report.topics[0].assessment_ref
                digest = sha256(
                    (
                        f"{plan_value.parts[0].receipt_result_id}:"
                        f"{assessment.identity}:{assessment.version}"
                    ).encode()
                ).hexdigest()[:32]
                evidence_ref = ResultRef(
                    f"report-history-{digest}", "report_submission", "1"
                )
                resolved = await resolver.resolve(await resolver.inspect(evidence_ref))
                if resolved.assessment_ref != report.topics[0].assessment_ref:
                    pytest.fail("history evidence lost assessment identity")
        finally:
            await second.close()

    asyncio.run(exercise())


def test_timeout_and_cancellation_after_pending_are_unknown_and_block_retry(
    tmp_path: Path,
) -> None:
    """Once the call can have started, timeout/cancellation cannot auto-resend."""

    async def timeout_case(path: Path) -> None:
        store = await open_store(path)
        try:
            report_ref, report = await build_report(store)
            plan_value = submission_plan(report_ref, report, suffix="timeout")
            transport = RecordingTransport(TimeoutError())
            outcome = await submission_handler(
                store, plan_value, transport, timeout=2.0
            ).run(submission_request(plan_value))
            if outcome.external_effect is not ExternalEffectState.UNKNOWN:
                pytest.fail("timed-out submission did not remain unknown")
            retry_plan = submission_plan(report_ref, report, suffix="retry")
            retry_transport = RecordingTransport()
            retry = await submission_handler(store, retry_plan, retry_transport).run(
                submission_request(retry_plan)
            )
            if retry.status is TerminalStatus.COMPLETE:
                pytest.fail("unknown claim reported a completed resend")
            if retry_transport.calls:
                pytest.fail("unknown claim allowed an automatic resend")
        finally:
            await store.close()

    async def cancellation_case(path: Path) -> None:
        store = await open_store(path)
        try:
            report_ref, report = await build_report(store)
            plan_value = submission_plan(report_ref, report, suffix="cancel")
            transport = RecordingTransport()
            transport.release = asyncio.Event()
            task = asyncio.create_task(
                submission_handler(store, plan_value, transport).run(
                    submission_request(plan_value)
                )
            )
            await transport.entered.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            snapshot = await store.inspect_claim(
                f"report-submit:{report.report_ref.identity}:"
                f"{report.report_ref.version}:{report.policy_ref.identity}:"
                f"{report.policy_ref.version}:1"
            )
            if snapshot.current_effect is not ExternalEffectState.UNKNOWN:
                pytest.fail("cancelled in-flight submission did not remain unknown")
        finally:
            await store.close()

    asyncio.run(timeout_case(tmp_path / "timeout.sqlite3"))
    asyncio.run(cancellation_case(tmp_path / "cancel.sqlite3"))


def test_rejected_retry_replays_exact_saved_bytes_after_restart(
    tmp_path: Path,
) -> None:
    """Only a proven rejected part may replay its persisted attempt bytes."""

    async def exercise() -> None:
        path = tmp_path / "retry.sqlite3"
        first = await open_store(path)
        report_ref, report = await build_report(first)
        first_plan = submission_plan(report_ref, report, suffix="first")
        first_transport = RecordingTransport(
            TransportReceipt(ExternalEffectState.REJECTED, "400")
        )
        await submission_handler(first, first_plan, first_transport).run(
            submission_request(first_plan)
        )
        attempt_ref = ResultRef(
            first_plan.parts[0].attempt_result_id, "report_submission", "1"
        )
        await first.close()

        second = await open_store(path)
        try:
            retry_plan = submission_plan(
                report_ref,
                report,
                suffix="retry",
                replay=attempt_ref,
            )
            retry_transport = RecordingTransport(
                TransportReceipt(ExternalEffectState.ACCEPTED, "202")
            )
            outcome = await submission_handler(
                second, retry_plan, retry_transport, attempt="retry-attempt"
            ).run(submission_request(retry_plan, identity="retry-execution"))
            if outcome.status is not TerminalStatus.COMPLETE:
                pytest.fail("safe rejected replay did not complete")
            if retry_transport.calls != first_transport.calls:
                pytest.fail("eligible retry changed persisted send bytes")
        finally:
            await second.close()

    asyncio.run(exercise())


def test_receipt_write_failure_after_call_remains_unknown(tmp_path: Path) -> None:
    """A response without durable receipt must not silently become accepted."""

    async def exercise() -> None:
        store = await open_store(tmp_path / "receipt-failure.sqlite3")
        try:
            report_ref, report = await build_report(store)
            plan_value = submission_plan(report_ref, report, suffix="write-fail")
            original = store.append_result_with_data

            async def fail_receipt(result, value, **kwargs):
                if isinstance(value, SubmissionReceipt):
                    raise Phase1PersistenceError("synthetic receipt failure")
                return await original(result, value, **kwargs)

            store.append_result_with_data = fail_receipt  # type: ignore[method-assign]
            outcome = await submission_handler(
                store,
                plan_value,
                RecordingTransport(
                    TransportReceipt(ExternalEffectState.ACCEPTED, "202")
                ),
            ).run(submission_request(plan_value))
            if outcome.external_effect is not ExternalEffectState.UNKNOWN:
                pytest.fail("receipt write failure became accepted")
            attempt_result = await store.get_result(
                plan_value.parts[0].attempt_result_id
            )
            if attempt_result is None or attempt_result.semantic_data_ref is None:
                pytest.fail("pre-effect attempt evidence was not durable")
            attempt = await store.load_semantic_data(attempt_result.semantic_data_ref)
            if not isinstance(attempt, SubmissionAttempt):
                pytest.fail("attempt evidence semantic type changed")
        finally:
            await store.close()

    asyncio.run(exercise())
