"""Multipart partial acceptance and safe restart retry."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from msgloom.contracts import ExternalEffectState, ResultRef, TerminalStatus
from msgloom.delivery import TransportReceipt
from msgloom.reporting import RendererConfig, ReportBuildHandler, SavedReport
from tests.delivery.helpers import (
    RecordingTransport,
    open_store,
    submission_handler,
    submission_plan,
    submission_request,
)
from tests.reporting.helpers import plan, policy, save_triage, topic, triage_data
from tests.reporting.test_handler import _config, _request


async def _build_multipart(store) -> tuple[ResultRef, SavedReport]:
    """Build two actual rendered parts through the report producer."""
    first = topic("topic-one", "assessment-one", source_identity="source-one")
    second = topic("topic-two", "assessment-two", source_identity="source-two")
    triage_ref = await save_triage(store, triage_data(first, second))
    selection = plan(triage_ref)
    outcome = await ReportBuildHandler(
        policy=policy(),
        selection_plan=selection,
        persistence=store,
        renderer_config=RendererConfig(
            max_part_bytes=4_000,
            max_total_bytes=30_000,
            max_parts=8,
        ),
        config=_config("multipart-report"),
    ).run(_request(selection, identity="multipart-build"))
    if outcome.status is not TerminalStatus.COMPLETE:
        raise RuntimeError("multipart synthetic report build failed")
    ref = outcome.result_refs[0]
    result = await store.get_result(ref.result_id)
    if result is None or result.semantic_data_ref is None:
        raise RuntimeError("multipart report result is missing")
    value = await store.load_semantic_data(result.semantic_data_ref)
    if not isinstance(value, SavedReport) or len(value.parts) != 2:
        raise RuntimeError("report producer did not create two saved parts")
    return ref, value


def test_partial_acceptance_is_not_full_and_retry_skips_accepted_part(
    tmp_path: Path,
) -> None:
    """Restart retry sends only the proven rejected part using saved bytes."""

    async def exercise() -> None:
        path = tmp_path / "multipart.sqlite3"
        first = await open_store(path)
        report_ref, report = await _build_multipart(first)
        initial = submission_plan(report_ref, report, suffix="multipart-first")
        transport = RecordingTransport(
            TransportReceipt(ExternalEffectState.ACCEPTED, "202"),
            TransportReceipt(ExternalEffectState.REJECTED, "400"),
        )
        outcome = await submission_handler(first, initial, transport, timeout=30.0).run(
            submission_request(initial)
        )
        if outcome.status is not TerminalStatus.INCOMPLETE:
            pytest.fail("partial acceptance was reported as full submission")
        if outcome.external_effect is not ExternalEffectState.ACCEPTED:
            pytest.fail("partial accepted report lost its known accepted effect")
        if len(transport.calls) != 2:
            pytest.fail("multipart report did not submit each initial part once")
        second_attempt = ResultRef(
            initial.parts[1].attempt_result_id, "report_submission", "1"
        )
        await first.close()

        reopened = await open_store(path)
        try:
            retry = submission_plan(
                report_ref,
                report,
                suffix="multipart-retry",
            )
            retry = retry.model_copy(
                update={
                    "parts": (
                        retry.parts[0],
                        retry.parts[1].model_copy(
                            update={"replay_attempt_ref": second_attempt}
                        ),
                    )
                }
            )
            retry_transport = RecordingTransport(
                TransportReceipt(ExternalEffectState.ACCEPTED, "202")
            )
            completed = await submission_handler(
                reopened,
                retry,
                retry_transport,
                attempt="multipart-retry-attempt",
                timeout=30.0,
            ).run(submission_request(retry, identity="multipart-retry"))
            if completed.status is not TerminalStatus.COMPLETE:
                pytest.fail("safe rejected part retry did not complete report")
            if retry_transport.calls != [transport.calls[1]]:
                pytest.fail("accepted part resent or rejected part bytes changed")
        finally:
            await reopened.close()

    asyncio.run(exercise())
