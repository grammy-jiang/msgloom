"""R3 regressions for durable effect truth and exact replay evidence."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from msgloom.contracts import (
    AttemptIdentity,
    ExecutionIdentity,
    ExternalEffectState,
    ResultRef,
    StageResult,
    TerminalStatus,
    VersionRef,
)
from msgloom.delivery import (
    SubmissionAttempt,
    TransportReceipt,
    build_mime,
    submission_claim_key,
)
from msgloom.delivery.records import load_attempt_record
from tests.delivery.helpers import (
    RecordingTransport,
    build_report,
    open_store,
    submission_handler,
    submission_plan,
    submission_request,
)


def test_cancel_after_pending_commit_preserves_uncertain_gate(tmp_path: Path) -> None:
    """Cancellation between durable PENDING and local state cannot release retry."""

    async def exercise() -> None:
        store = await open_store(tmp_path / "pending-cancel.sqlite3")
        try:
            report_ref, report = await build_report(store)
            plan = submission_plan(report_ref, report, suffix="pending-cancel")
            committed = asyncio.Event()
            original = store.mark_external_effect

            async def pause_after_commit(token, effect):
                await original(token, effect)
                if effect is ExternalEffectState.PENDING:
                    committed.set()
                    await asyncio.Event().wait()

            store.mark_external_effect = pause_after_commit  # type: ignore[method-assign]
            transport = RecordingTransport()
            task = asyncio.create_task(
                submission_handler(store, plan, transport).run(submission_request(plan))
            )
            await committed.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            if transport.calls:
                pytest.fail("transport started before the PENDING barrier released")
            key = submission_claim_key(
                report.report_ref.identity,
                report.report_ref.version,
                report.policy_ref.identity,
                report.policy_ref.version,
                1,
            )
            snapshot = await store.inspect_claim(key)
            if snapshot.current_effect is not ExternalEffectState.UNKNOWN:
                pytest.fail("durable PENDING was downgraded during cancellation")
        finally:
            await store.close()

    asyncio.run(exercise())


def test_transport_value_error_retains_unknown_gate(tmp_path: Path) -> None:
    """An ordinary post-PENDING transport ValueError cannot authorize retry."""

    async def exercise() -> None:
        store = await open_store(tmp_path / "transport-value-error.sqlite3")
        try:
            report_ref, report = await build_report(store)
            plan = submission_plan(report_ref, report, suffix="transport-value")
            transport = RecordingTransport(ValueError("synthetic private detail"))
            outcome = await submission_handler(store, plan, transport).run(
                submission_request(plan)
            )
            if outcome.external_effect is not ExternalEffectState.UNKNOWN:
                pytest.fail("transport ValueError released the uncertain send gate")
            retry = submission_plan(report_ref, report, suffix="transport-retry")
            retry_transport = RecordingTransport()
            blocked = await submission_handler(
                store, retry, retry_transport, attempt="transport-retry-attempt"
            ).run(submission_request(retry, identity="transport-retry-execution"))
            if blocked.external_effect is not ExternalEffectState.UNKNOWN:
                pytest.fail("uncertain transport failure became retry-safe")
            if retry_transport.calls:
                pytest.fail("uncertain transport failure allowed a duplicate call")
        finally:
            await store.close()

    asyncio.run(exercise())


def test_rejected_restart_replays_exact_saved_bytes(tmp_path: Path) -> None:
    """A rejected retry after reopen sends only the exact prior attempt bytes."""

    async def exercise() -> None:
        path = tmp_path / "rejected-replay.sqlite3"
        first = await open_store(path)
        report_ref, report = await build_report(first)
        initial = submission_plan(report_ref, report, suffix="rejected-original")
        rejected = RecordingTransport(
            TransportReceipt(ExternalEffectState.REJECTED, "400")
        )
        outcome = await submission_handler(first, initial, rejected).run(
            submission_request(initial)
        )
        attempt_ref = next(
            ref
            for ref in outcome.result_refs
            if ref.result_id == initial.parts[0].attempt_result_id
        )
        result = await first.get_result(attempt_ref.result_id)
        if result is None or result.semantic_data_ref is None:
            pytest.fail("rejected attempt evidence is missing")
        attempt = await first.load_semantic_data(result.semantic_data_ref)
        if not isinstance(attempt, SubmissionAttempt):
            pytest.fail("rejected attempt evidence changed type")
        exact_bytes = attempt.send_bytes
        await first.close()

        reopened = await open_store(path)
        try:
            replay = submission_plan(
                report_ref,
                report,
                suffix="rejected-retry",
                replay=attempt_ref,
            )
            transport = RecordingTransport(
                TransportReceipt(ExternalEffectState.ACCEPTED, "202")
            )
            retried = await submission_handler(
                reopened,
                replay,
                transport,
                attempt="rejected-retry-attempt",
            ).run(submission_request(replay, identity="rejected-retry-execution"))
            if retried.status is not TerminalStatus.COMPLETE:
                pytest.fail("exact rejected replay did not complete")
            if transport.calls != [exact_bytes]:
                pytest.fail("rejected retry did not reuse exact saved send bytes")
        finally:
            await reopened.close()

    asyncio.run(exercise())


def test_attempt_loader_rejects_fabricated_stage_lineage(tmp_path: Path) -> None:
    """Receipt/history verification cannot trust a mismatched attempt wrapper."""

    async def exercise() -> None:
        store = await open_store(tmp_path / "attempt-lineage.sqlite3")
        try:
            report_ref, report = await build_report(store)
            plan = submission_plan(report_ref, report, suffix="lineage-source")
            outcome = await submission_handler(
                store,
                plan,
                RecordingTransport(
                    TransportReceipt(ExternalEffectState.REJECTED, "400")
                ),
            ).run(submission_request(plan))
            source_ref = next(
                ref
                for ref in outcome.result_refs
                if ref.result_id == plan.parts[0].attempt_result_id
            )
            source_result = await store.get_result(source_ref.result_id)
            if source_result is None or source_result.semantic_data_ref is None:
                pytest.fail("source attempt is missing")
            attempt = await store.load_semantic_data(source_result.semantic_data_ref)
            if not isinstance(attempt, SubmissionAttempt):
                pytest.fail("source attempt has the wrong type")

            forged_ref = ResultRef("forged-attempt-lineage", "report_submission", "1")
            forged_data = store.semantic_reference(
                "data-forged-attempt-lineage", "report_submission", "1", attempt
            )
            await store.append_result_with_data(
                StageResult(
                    result_id=forged_ref.result_id,
                    kind=forged_ref.kind,
                    schema_version=forged_ref.schema_version,
                    execution=ExecutionIdentity("forged-attempt-execution"),
                    attempt=AttemptIdentity("forged-attempt"),
                    input_refs=(report_ref,),
                    source_versions=(),
                    prepared_versions=(),
                    topic_versions=attempt.assessment_refs,
                    configuration_version=attempt.policy_ref.version,
                    code_version="delivery-test",
                    status=TerminalStatus.INCOMPLETE,
                    acceptable=True,
                    semantic_data_ref=forged_data,
                    exposed_output_ref=VersionRef("report", "wrong-report", "v1"),
                ),
                attempt,
                require_new=True,
            )
            with pytest.raises(ValueError, match="stage lineage mismatches"):
                await load_attempt_record(store, forged_ref)
        finally:
            await store.close()

    asyncio.run(exercise())


def test_mime_rejects_subject_control_characters(tmp_path: Path) -> None:
    """Subject source text cannot contain non-newline ASCII controls."""

    async def exercise() -> None:
        store = await open_store(tmp_path / "mime-controls.sqlite3")
        try:
            _report_ref, report = await build_report(store)
            bad = report.model_copy(
                update={"report_ref": VersionRef("report", "bad\x00identity", "v1")}
            )
            with pytest.raises(ValueError, match="header controls"):
                build_mime(bad, bad.parts[0], bad.destination.destination_identity)
        finally:
            await store.close()

    asyncio.run(exercise())
