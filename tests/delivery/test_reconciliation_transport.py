"""Reconciliation, Graph semantics, and concurrent ownership tests."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import cast

import pytest

from msgloom.contracts import (
    AttemptIdentity,
    ExecutionIdentity,
    ExternalEffectState,
    ResultRef,
    TerminalStatus,
)
from msgloom.delivery import (
    GraphSendMailTransport,
    HttpResponse,
    ProviderEvidence,
    ReportReconciler,
    ReportReconciliationPlan,
    TransportReceipt,
)
from tests.delivery.helpers import (
    RecordingTransport,
    build_report,
    open_store,
    submission_handler,
    submission_plan,
    submission_request,
)


class RecordingHttp:
    """One-shot fake HTTP boundary for Graph adapter tests."""

    def __init__(self, response: HttpResponse) -> None:
        self.response = response
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def post(self, url: str, **kwargs: object) -> HttpResponse:
        """Record the exact one-shot controls and return a synthetic response."""
        self.calls.append((url, kwargs))
        return self.response


def test_graph_202_is_accepted_only_and_http_is_one_shot() -> None:
    """Graph 202 is accepted submission, never confirmed delivery."""

    async def exercise() -> None:
        http = RecordingHttp(HttpResponse(202, "synthetic-request"))
        transport = GraphSendMailTransport(
            mailbox="owner@example.invalid",
            bearer_token="synthetic-secret",
            http=http,
        )
        receipt = await transport.submit(b"exact-mime", timeout_seconds=1.0)
        if receipt.effect is not ExternalEffectState.ACCEPTED:
            pytest.fail("Graph 202 was treated as confirmed delivery")
        if len(http.calls) != 1:
            pytest.fail("Graph adapter retried a one-shot request")
        _url, kwargs = http.calls[0]
        if kwargs["allow_redirects"] is not False or kwargs["retries"] != 0:
            pytest.fail("Graph adapter enabled redirects or retries")
        headers = dict(cast(tuple[tuple[str, str], ...], kwargs["headers"]))
        if headers["Content-Type"] != "text/plain":
            pytest.fail("Graph MIME request content type changed")

    asyncio.run(exercise())


def test_concurrent_claim_holder_cannot_duplicate_send(tmp_path: Path) -> None:
    """A second process-equivalent handler cannot bypass the live part claim."""

    async def exercise() -> None:
        store = await open_store(tmp_path / "concurrent.sqlite3")
        try:
            report_ref, report = await build_report(store)
            plan_value = submission_plan(report_ref, report, suffix="concurrent")
            first_transport = RecordingTransport(
                TransportReceipt(ExternalEffectState.ACCEPTED, "202")
            )
            first_transport.release = asyncio.Event()
            first = asyncio.create_task(
                submission_handler(store, plan_value, first_transport, timeout=5.0).run(
                    submission_request(plan_value, identity="first")
                )
            )
            await first_transport.entered.wait()

            second_transport = RecordingTransport()
            second = await submission_handler(
                store,
                submission_plan(report_ref, report, suffix="second"),
                second_transport,
                attempt="second-attempt",
            ).run(
                submission_request(
                    submission_plan(report_ref, report, suffix="second"),
                    identity="second",
                )
            )
            if second_transport.calls:
                pytest.fail("concurrent holder reached transport")
            if second.status is TerminalStatus.COMPLETE:
                pytest.fail("concurrent blocked holder reported completion")
            first_transport.release.set()
            completed = await first
            if completed.status is not TerminalStatus.COMPLETE:
                pytest.fail("original claim holder did not complete")
        finally:
            await store.close()

    asyncio.run(exercise())


def test_unknown_reconciliation_requires_proof_and_rejected_releases_retry(
    tmp_path: Path,
) -> None:
    """Recovery proof is durable and only proven rejection reopens the part."""

    async def exercise() -> None:
        path = tmp_path / "reconcile.sqlite3"
        first = await open_store(path)
        report_ref, report = await build_report(first)
        plan_value = submission_plan(report_ref, report, suffix="unknown")
        transport = RecordingTransport(TimeoutError())
        outcome = await submission_handler(first, plan_value, transport).run(
            submission_request(plan_value)
        )
        if outcome.external_effect is not ExternalEffectState.UNKNOWN:
            pytest.fail("synthetic uncertain call did not remain unknown")
        key = (
            f"report-submit:{report.report_ref.identity}:{report.report_ref.version}:"
            f"{report.policy_ref.identity}:{report.policy_ref.version}:1"
        )
        snapshot = await first.inspect_claim(key)
        target = snapshot.current_token
        if target is None:
            pytest.fail("unknown submission did not retain its claim token")
        await first.close()

        second = await open_store(path)
        try:
            reconciler = ReportReconciler(second)
            inconclusive = ReportReconciliationPlan(
                identity="reconcile-inconclusive",
                target=target,
                report_ref=report.report_ref,
                policy_ref=report.policy_ref,
                part_number=1,
                decision=ExternalEffectState.UNKNOWN,
                provider_evidence=(),
                recovery_attempt=AttemptIdentity("recovery-inconclusive"),
                recovery_result_id="recovery-inconclusive",
                code_version="delivery-test",
                claim_lease_seconds=10.0,
            )
            result = await reconciler.reconcile(
                inconclusive, execution=ExecutionIdentity("recovery-one")
            )
            if result.decision is not ExternalEffectState.UNKNOWN:
                pytest.fail("inconclusive evidence changed unknown effect")

            definite = ReportReconciliationPlan(
                identity="reconcile-rejected",
                target=target,
                report_ref=report.report_ref,
                policy_ref=report.policy_ref,
                part_number=1,
                decision=ExternalEffectState.REJECTED,
                provider_evidence=(
                    ProviderEvidence(
                        provider="synthetic",
                        reference="provider-proof-1",
                        detail="Synthetic provider proves no message was accepted.",
                    ),
                ),
                recovery_attempt=AttemptIdentity("recovery-rejected"),
                recovery_result_id="recovery-rejected",
                code_version="delivery-test",
                claim_lease_seconds=10.0,
            )
            result = await reconciler.reconcile(
                definite, execution=ExecutionIdentity("recovery-two")
            )
            if result.decision is not ExternalEffectState.REJECTED:
                pytest.fail("definitive rejection was not persisted")

            attempt_ref = ResultRef(
                plan_value.parts[0].attempt_result_id,
                "report_submission",
                "1",
            )
            retry_plan = submission_plan(
                report_ref,
                report,
                suffix="after-reconcile",
                replay=attempt_ref,
            )
            retry_transport = RecordingTransport(
                TransportReceipt(ExternalEffectState.ACCEPTED, "202")
            )
            retry = await submission_handler(
                second,
                retry_plan,
                retry_transport,
                attempt="after-reconcile-attempt",
            ).run(submission_request(retry_plan, identity="after-reconcile"))
            if retry.status is not TerminalStatus.COMPLETE:
                pytest.fail("proven rejected part did not reopen for exact replay")
            if retry_transport.calls != transport.calls:
                pytest.fail("reconciled retry changed the original persisted bytes")
        finally:
            await second.close()

    asyncio.run(exercise())
