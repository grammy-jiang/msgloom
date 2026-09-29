"""Real ReportBuildHandler integration with durable delivery history."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from msgloom.contracts import ExternalEffectState, ResultRef, TerminalStatus
from msgloom.delivery import (
    DeliveryReportHistoryResolver,
    TransportReceipt,
)
from msgloom.delivery.records import history_result_id
from msgloom.reporting import (
    PriorReportState,
    RendererConfig,
    ReportBuildHandler,
)
from tests.delivery.helpers import (
    RecordingTransport,
    build_report,
    open_store,
    submission_handler,
    submission_plan,
    submission_request,
)
from tests.reporting.helpers import plan, policy
from tests.reporting.test_handler import _config, _request


def test_accepted_history_is_verified_across_restart_and_attempt_is_not_history(
    tmp_path: Path,
) -> None:
    """Only receipt-backed accepted history may participate in suppression."""

    async def exercise() -> None:
        path = tmp_path / "history.sqlite3"
        first = await open_store(path)
        report_ref, report = await build_report(first)
        submit_plan = submission_plan(report_ref, report, suffix="history")
        outcome = await submission_handler(
            first,
            submit_plan,
            RecordingTransport(TransportReceipt(ExternalEffectState.ACCEPTED, "202")),
        ).run(submission_request(submit_plan))
        if outcome.status is not TerminalStatus.COMPLETE:
            pytest.fail("synthetic accepted report did not complete")

        assessment = report.topics[0].assessment_ref
        history_ref = ResultRef(
            history_result_id(report.report_ref, report.policy_ref, 1, assessment),
            "report_submission",
            "1",
        )
        attempt_ref = ResultRef(
            submit_plan.parts[0].attempt_result_id, "report_submission", "1"
        )
        await first.close()

        second = await open_store(path)
        try:
            resolver = DeliveryReportHistoryResolver(second)
            evidence = await resolver.resolve(await resolver.inspect(history_ref))
            state = PriorReportState(
                policy_ref=evidence.policy_ref,
                assessment_ref=evidence.assessment_ref,
                report_ref=evidence.report_ref,
                reported_at=evidence.reported_at,
                evidence_ref=history_ref,
            )
            selection = plan(*report.source_triage_results).model_copy(
                update={"prior_state": (state,)}
            )
            handler = ReportBuildHandler(
                policy=policy(),
                selection_plan=selection,
                persistence=second,
                renderer_config=RendererConfig(
                    max_part_bytes=100_000,
                    max_total_bytes=300_000,
                    max_parts=8,
                ),
                config=_config("report-after-history"),
                history_resolver=resolver,
            )
            suppressed = await handler.run(
                _request(selection, identity="report-after-history-execution")
            )
            if suppressed.status is not TerminalStatus.FAILED:
                pytest.fail("repeat-never accepted history did not suppress due topic")
            if not any(
                failure.code == "report_build_invalid"
                for failure in suppressed.failures
            ):
                pytest.fail("accepted history did not reach due-topic selection")

            bad_state = state.model_copy(update={"evidence_ref": attempt_ref})
            bad_selection = plan(*report.source_triage_results).model_copy(
                update={"prior_state": (bad_state,)}
            )
            bad_handler = ReportBuildHandler(
                policy=policy(),
                selection_plan=bad_selection,
                persistence=second,
                renderer_config=RendererConfig(
                    max_part_bytes=100_000,
                    max_total_bytes=300_000,
                    max_parts=8,
                ),
                config=_config("report-with-attempt-history"),
                history_resolver=resolver,
            )
            invalid = await bad_handler.run(
                _request(bad_selection, identity="report-with-attempt-execution")
            )
            if invalid.status is not TerminalStatus.FAILED:
                pytest.fail("mere submission attempt qualified as report history")
        finally:
            await second.close()

    asyncio.run(exercise())
