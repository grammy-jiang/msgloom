"""R2 reconciliation replay and receipt-backed history recovery tests."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path

import pytest

from msgloom.contracts import (
    AttemptIdentity,
    ClaimKind,
    ExecutionIdentity,
    ExternalEffectState,
    ResultRef,
    StageResult,
    TerminalStatus,
    VersionRef,
)
from msgloom.delivery import (
    DeliveryReportHistoryResolver,
    ProviderEvidence,
    ReportReconciler,
    ReportReconciliationPlan,
    SubmissionAttempt,
    SubmissionHistory,
    SubmissionReceipt,
    TransportReceipt,
    build_mime,
    submission_claim_key,
)
from msgloom.persistence import Phase1PersistenceError
from msgloom.reporting import PriorReportState, RendererConfig, ReportBuildHandler
from tests.delivery.helpers import (
    RecordingTransport,
    build_report,
    open_store,
    submission_handler,
    submission_plan,
    submission_request,
)
from tests.reporting.helpers import plan as build_selection
from tests.reporting.helpers import policy
from tests.reporting.test_handler import _config as report_config
from tests.reporting.test_handler import _request as report_request


async def _assert_history_suppresses(
    store,
    report,
    history_ref: ResultRef,
    *,
    identity: str,
) -> None:
    resolver = DeliveryReportHistoryResolver(store)
    evidence = await resolver.resolve(await resolver.inspect(history_ref))
    state = PriorReportState(
        policy_ref=evidence.policy_ref,
        assessment_ref=evidence.assessment_ref,
        report_ref=evidence.report_ref,
        reported_at=evidence.reported_at,
        evidence_ref=history_ref,
    )
    selection = build_selection(*report.source_triage_results).model_copy(
        update={"prior_state": (state,)}
    )
    outcome = await ReportBuildHandler(
        policy=policy(),
        selection_plan=selection,
        persistence=store,
        renderer_config=RendererConfig(
            max_part_bytes=100_000,
            max_total_bytes=300_000,
            max_parts=8,
        ),
        config=report_config(identity),
        history_resolver=resolver,
    ).run(report_request(selection, identity=f"{identity}-execution"))
    if outcome.status is not TerminalStatus.FAILED:
        pytest.fail("receipt-backed history did not reach repeat suppression")


async def _seed_unknown_accepted_receipt(
    store, report_ref, report, effect=ExternalEffectState.ACCEPTED
):
    """Persist a target UNKNOWN claim with one exact definite receipt."""
    execution = ExecutionIdentity("seed-unknown-execution")
    attempt_identity = AttemptIdentity("seed-unknown-attempt")
    key = submission_claim_key(
        report.report_ref.identity,
        report.report_ref.version,
        report.policy_ref.identity,
        report.policy_ref.version,
        1,
    )
    claim = await store.acquire_claim(
        key,
        ClaimKind.REPORT_SUBMIT,
        execution,
        attempt_identity,
        required_inputs=(report_ref,),
        lease_seconds=10.0,
    )
    part = report.parts[0]
    assessments = tuple(
        topic.assessment_ref
        for topic in report.topics
        if topic.topic_ref in part.topic_refs
    )
    send_bytes = build_mime(report, part, report.destination.destination_identity)
    attempt = SubmissionAttempt(
        report_ref=report.report_ref,
        policy_ref=report.policy_ref,
        part_number=1,
        owner_identity=report.destination.owner_identity,
        destination_identity=report.destination.destination_identity,
        assessment_refs=assessments,
        send_bytes=send_bytes,
        send_sha256=sha256(send_bytes).hexdigest(),
    )
    attempt_ref = ResultRef("seed-attempt-result", "report_submission", "1")
    attempt_data = store.semantic_reference(
        "data-seed-attempt-result", "report_submission", "1", attempt
    )
    await store.append_result_with_data(
        StageResult(
            result_id=attempt_ref.result_id,
            kind=attempt_ref.kind,
            schema_version=attempt_ref.schema_version,
            execution=execution,
            attempt=attempt_identity,
            input_refs=(report_ref,),
            source_versions=(),
            prepared_versions=(),
            topic_versions=assessments,
            configuration_version=report.policy_ref.version,
            code_version="delivery-test",
            status=TerminalStatus.INCOMPLETE,
            acceptable=True,
            semantic_data_ref=attempt_data,
            exposed_output_ref=report.report_ref,
        ),
        attempt,
        require_new=True,
        claim=claim,
    )
    await store.mark_external_effect(claim, ExternalEffectState.PENDING)

    recorded_at = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)
    receipt = SubmissionReceipt(
        report_ref=report.report_ref,
        policy_ref=report.policy_ref,
        part_number=1,
        assessment_refs=assessments,
        attempt_ref=attempt_ref,
        effect=effect,
        provider_status="202",
        provider_receipt="accepted-proof",
        recorded_at=recorded_at,
    )
    receipt_ref = ResultRef("seed-receipt-result", "report_submission", "1")
    receipt_data = store.semantic_reference(
        "data-seed-receipt-result", "report_submission", "1", receipt
    )
    await store.append_result_with_data(
        StageResult(
            result_id=receipt_ref.result_id,
            kind=receipt_ref.kind,
            schema_version=receipt_ref.schema_version,
            execution=execution,
            attempt=attempt_identity,
            input_refs=(report_ref, attempt_ref),
            source_versions=(),
            prepared_versions=(),
            topic_versions=assessments,
            configuration_version=report.policy_ref.version,
            code_version="delivery-test",
            status=TerminalStatus.COMPLETE,
            acceptable=True,
            semantic_data_ref=receipt_data,
            exposed_output_ref=report.report_ref,
        ),
        receipt,
        require_new=True,
        claim=claim,
    )
    await store.finish_claim(claim, TerminalStatus.FAILED, ExternalEffectState.UNKNOWN)
    return claim, receipt_ref, receipt


def test_history_failure_repairs_on_restart_without_resend(tmp_path: Path) -> None:
    """Accepted receipt history is repaired under a fresh no-send claim."""

    async def exercise() -> None:
        path = tmp_path / "history-repair.sqlite3"
        first = await open_store(path)
        report_ref, report = await build_report(first)
        plan_value = submission_plan(report_ref, report, suffix="history-repair")
        original = first.append_result_with_data
        failed = False

        async def fail_history(result, value, **kwargs):
            nonlocal failed
            if isinstance(value, SubmissionHistory) and not failed:
                failed = True
                raise Phase1PersistenceError("synthetic history failure")
            return await original(result, value, **kwargs)

        first.append_result_with_data = fail_history  # type: ignore[method-assign]
        transport = RecordingTransport(
            TransportReceipt(ExternalEffectState.ACCEPTED, "202", "accepted")
        )
        outcome = await submission_handler(first, plan_value, transport).run(
            submission_request(plan_value)
        )
        if outcome.status is not TerminalStatus.INCOMPLETE:
            pytest.fail("history failure incorrectly reported complete submission")
        if outcome.external_effect is not ExternalEffectState.ACCEPTED:
            pytest.fail("history failure downgraded durable accepted effect")
        if len(transport.calls) != 1:
            pytest.fail("initial accepted submission call count changed")
        await first.close()

        reopened = await open_store(path)
        try:
            no_send = RecordingTransport(RuntimeError("must not send"))
            recovered = await submission_handler(
                reopened,
                plan_value,
                no_send,
                attempt="history-recovery-attempt",
            ).run(submission_request(plan_value, identity="history-recovery"))
            if recovered.status is not TerminalStatus.COMPLETE:
                pytest.fail("restart did not repair accepted report history")
            if no_send.calls:
                pytest.fail("history recovery invoked transport")

            assessment = report.topics[0].assessment_ref
            from msgloom.delivery.records import history_result_id

            history_ref = ResultRef(
                history_result_id(
                    report.report_ref,
                    report.policy_ref,
                    1,
                    assessment,
                ),
                "report_submission",
                "1",
            )
            await _assert_history_suppresses(
                reopened,
                report,
                history_ref,
                identity="history-repair-build",
            )
        finally:
            await reopened.close()

    asyncio.run(exercise())


def test_reconciliation_is_replayable_and_changed_proof_fails(
    tmp_path: Path,
) -> None:
    """Exact recovery replay is idempotent across a post-proof interruption."""

    async def exercise() -> None:
        store = await open_store(tmp_path / "reconcile-replay.sqlite3")
        try:
            report_ref, report = await build_report(store)
            plan_value = submission_plan(report_ref, report, suffix="unknown-proof")
            await submission_handler(
                store,
                plan_value,
                RecordingTransport(TimeoutError()),
            ).run(submission_request(plan_value))
            key = submission_claim_key(
                report.report_ref.identity,
                report.report_ref.version,
                report.policy_ref.identity,
                report.policy_ref.version,
                1,
            )
            target = (await store.inspect_claim(key)).current_token
            if target is None:
                pytest.fail("unknown target claim is missing")
            recovery = ReportReconciliationPlan(
                identity="replayable-recovery",
                target=target,
                report_ref=report.report_ref,
                policy_ref=report.policy_ref,
                part_number=1,
                decision=ExternalEffectState.REJECTED,
                provider_evidence=(
                    ProviderEvidence(
                        provider="synthetic",
                        reference="proof-one",
                        detail="Synthetic provider rejected the exact attempt.",
                    ),
                ),
                recovery_attempt=AttemptIdentity("replayable-recovery-attempt"),
                recovery_result_id="replayable-recovery-proof",
                code_version="delivery-test",
                claim_lease_seconds=10.0,
            )
            reconciler = ReportReconciler(store)
            original = store.reconcile_external_effect
            interrupted = False

            async def fail_once(request):
                nonlocal interrupted
                if not interrupted:
                    interrupted = True
                    raise RuntimeError("synthetic post-proof interruption")
                return await original(request)

            store.reconcile_external_effect = fail_once  # type: ignore[method-assign]
            with pytest.raises(RuntimeError, match="post-proof interruption"):
                await reconciler.reconcile(
                    recovery, execution=ExecutionIdentity("recovery-execution")
                )
            store.reconcile_external_effect = original  # type: ignore[method-assign]
            first = await reconciler.reconcile(
                recovery, execution=ExecutionIdentity("recovery-execution")
            )
            second = await reconciler.reconcile(
                recovery, execution=ExecutionIdentity("recovery-execution")
            )
            if first != second:
                pytest.fail("identical reconciliation retry changed saved result")

            changed = recovery.model_copy(
                update={
                    "provider_evidence": (
                        ProviderEvidence(
                            provider="synthetic",
                            reference="proof-two",
                            detail="Changed synthetic proof must not rewrite identity.",
                        ),
                    )
                }
            )
            with pytest.raises(ValueError, match="changed proof"):
                await reconciler.reconcile(
                    changed, execution=ExecutionIdentity("recovery-execution")
                )
        finally:
            await store.close()

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "effect", [ExternalEffectState.ACCEPTED, ExternalEffectState.CONFIRMED]
)
def test_accepted_reconciliation_requires_receipt_and_build_uses_history(
    tmp_path: Path, effect: ExternalEffectState
) -> None:
    """Accepted reconciliation creates only receipt-backed historical evidence."""

    async def exercise() -> None:
        store = await open_store(tmp_path / "accepted-reconcile.sqlite3")
        try:
            report_ref, report = await build_report(store)
            target, receipt_ref, receipt = await _seed_unknown_accepted_receipt(
                store, report_ref, report, effect
            )
            with pytest.raises(
                ValueError, match="accepted reconciliation requires a durable receipt"
            ):
                ReportReconciliationPlan(
                    identity="missing-receipt",
                    target=target,
                    report_ref=report.report_ref,
                    policy_ref=report.policy_ref,
                    part_number=1,
                    decision=effect,
                    provider_evidence=(
                        ProviderEvidence(
                            provider="synthetic",
                            reference="operator-only",
                            detail="Operator assertion without receipt.",
                        ),
                    ),
                    recovery_attempt=AttemptIdentity("missing-receipt-attempt"),
                    recovery_result_id="missing-receipt-proof",
                    code_version="delivery-test",
                    claim_lease_seconds=10.0,
                )

            recovery = ReportReconciliationPlan(
                identity="accepted-recovery",
                target=target,
                report_ref=report.report_ref,
                policy_ref=report.policy_ref,
                part_number=1,
                decision=effect,
                provider_evidence=(
                    ProviderEvidence(
                        provider="synthetic",
                        reference="accepted-provider-proof",
                        detail="Provider evidence corroborates the durable receipt.",
                    ),
                ),
                receipt_ref=receipt_ref,
                recovery_attempt=AttemptIdentity("accepted-recovery-attempt"),
                recovery_result_id="accepted-recovery-proof",
                code_version="delivery-test",
                claim_lease_seconds=10.0,
            )
            reconciler = ReportReconciler(store)
            result = await reconciler.reconcile(
                recovery, execution=ExecutionIdentity("accepted-recovery-execution")
            )
            if result.decision is not effect:
                pytest.fail("reconciliation lost its definite receipt effect")
            replayed = await reconciler.reconcile(
                recovery, execution=ExecutionIdentity("accepted-recovery-execution")
            )
            if replayed != result:
                pytest.fail("definite reconciliation replay changed saved result")

            from msgloom.delivery.records import history_result_id

            assessment = report.topics[0].assessment_ref
            history_ref = ResultRef(
                history_result_id(
                    report.report_ref,
                    report.policy_ref,
                    1,
                    assessment,
                ),
                "report_submission",
                "1",
            )
            resolver = DeliveryReportHistoryResolver(store)
            history = await resolver.resolve(await resolver.inspect(history_ref))
            if history.reported_at != receipt.recorded_at:
                pytest.fail("reconciliation invented a new report acceptance time")

            forged = SubmissionHistory(
                report_ref=report.report_ref,
                policy_ref=report.policy_ref,
                assessment_ref=assessment,
                receipt_ref=VersionRef(
                    "report-receipt", receipt_ref.result_id, receipt_ref.schema_version
                ),
                effect=ExternalEffectState.ACCEPTED,
                reported_at=receipt.recorded_at + timedelta(seconds=1),
            )
            forged_ref = ResultRef("forged-history", "report_submission", "1")
            forged_data = store.semantic_reference(
                "data-forged-history", "report_submission", "1", forged
            )
            await store.append_result_with_data(
                StageResult(
                    result_id=forged_ref.result_id,
                    kind=forged_ref.kind,
                    schema_version=forged_ref.schema_version,
                    execution=ExecutionIdentity("forged-history-execution"),
                    attempt=AttemptIdentity("forged-history-attempt"),
                    input_refs=(receipt_ref,),
                    source_versions=(),
                    prepared_versions=(),
                    topic_versions=(assessment,),
                    configuration_version=report.policy_ref.version,
                    code_version="delivery-test",
                    status=TerminalStatus.COMPLETE,
                    acceptable=True,
                    semantic_data_ref=forged_data,
                    exposed_output_ref=report.report_ref,
                ),
                forged,
                require_new=True,
            )
            with pytest.raises(ValueError, match="exact receipt lineage"):
                await resolver.resolve(await resolver.inspect(forged_ref))

            await _assert_history_suppresses(
                store,
                report,
                history_ref,
                identity="accepted-reconcile-build",
            )
        finally:
            await store.close()

    asyncio.run(exercise())
