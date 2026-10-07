"""R3 regressions for structural coverage, history, fencing, and snapshots."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
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
)
from msgloom.persistence import Phase1PersistenceError
from msgloom.reporting import (
    FrozenReportSelection,
    PriorReportState,
    RendererConfig,
    RepeatMode,
    ReportBuildHandler,
    ReportCodec,
    ReportHistoryEvidence,
    ReportHistoryMetadata,
    SavedReport,
    SourceLink,
    render_report,
)
from msgloom.reporting.build import build_overview, build_topics
from tests.reporting.helpers import (
    open_store,
    plan,
    policy,
    ref,
    save_triage,
    topic,
    triage_data,
)
from tests.reporting.test_handler import _config, _request


def _saved_report(*, linked: bool = False, control_text: bool = False) -> SavedReport:
    item = topic(title="DETAILS TOPIC PENDING WORK" if control_text else topic().title)
    links = ()
    if linked:
        links = (
            SourceLink(
                source_ref=item.source_refs[0],
                url="https://example.invalid/exact?x=1&y=2",
            ),
        )
    selection = plan(ResultRef("triage-r3", "triage", "1"), source_links=links)
    built = build_topics((item,), selection)
    overview = build_overview(built)
    parts = render_report(
        ref("report", "r3"),
        overview,
        built,
        (),
        RendererConfig(max_part_bytes=100_000, max_total_bytes=200_000, max_parts=4),
    )
    configured = policy()
    return SavedReport(
        report_ref=ref("report", "r3"),
        policy_ref=configured.policy_ref,
        destination=configured.destination,
        due_at=configured.due_at,
        timezone=configured.timezone,
        source_triage_results=selection.triage_results,
        topics=built,
        overview=overview,
        pending_warnings=(),
        limitations=(),
        renderer_version="r3-test",
        parts=parts,
    )


@pytest.mark.parametrize("mutation", ("overview", "href", "boundary", "number"))
def test_codec_rejects_section_link_boundary_and_part_number_forgery(
    mutation: str,
) -> None:
    """Actual saved structure, not metadata or whole-document text, is authoritative."""
    saved = _saved_report(linked=True, control_text=True)
    part = saved.parts[0]
    if mutation == "overview":
        html = (
            part.html.split("<h2>Overview</h2>", 1)[0]
            + "<h2>Details</h2>"
            + part.html.split("<h2>Details</h2>", 1)[1]
        )
        forged_part = part.model_copy(update={"html": html})
    elif mutation == "href":
        forged_part = part.model_copy(
            update={
                "html": part.html.replace(
                    'href="https://example.invalid/exact?x=1&amp;y=2"',
                    'href="https://example.invalid/wrong"',
                    1,
                )
            }
        )
    elif mutation == "boundary":
        forged_part = part.model_copy(
            update={
                "html": part.html.replace(
                    "</article>",
                    '<article data-topic="topic:hidden@1"></article></article>',
                    1,
                )
            }
        )
    else:
        forged_part = part.model_copy(update={"part_number": 2})
    forged = saved.model_copy(update={"parts": (forged_part,)})
    with pytest.raises(TypeError, match="failed validation"):
        ReportCodec().encode(forged)


class _HistoryResolver:
    def __init__(
        self, metadata: ReportHistoryMetadata, evidence: ReportHistoryEvidence
    ) -> None:
        self.metadata = metadata
        self.evidence = evidence

    async def inspect(self, evidence_ref: ResultRef) -> ReportHistoryMetadata:
        if evidence_ref != self.metadata.evidence_ref:
            pytest.fail("resolver inspected an unexpected history reference")
        return self.metadata

    async def resolve(self, metadata: ReportHistoryMetadata) -> ReportHistoryEvidence:
        if metadata != self.metadata:
            pytest.fail("resolver resolved unexpected history metadata")
        return self.evidence


async def _save_submission(
    store: object, evidence_ref: ResultRef, assessment_ref: object, policy_version: str
) -> None:
    result = StageResult(
        result_id=evidence_ref.result_id,
        kind=evidence_ref.kind,
        schema_version=evidence_ref.schema_version,
        execution=ExecutionIdentity("submission-execution"),
        attempt=AttemptIdentity("submission-attempt"),
        input_refs=(),
        source_versions=(),
        prepared_versions=(),
        topic_versions=(assessment_ref,),  # type: ignore[arg-type]
        configuration_version=policy_version,
        code_version="delivery-test",
        status=TerminalStatus.COMPLETE,
        acceptable=True,
    )
    await store.append_result(result)  # type: ignore[attr-defined]


def test_verified_history_is_frozen_and_forged_timestamp_fails(tmp_path: Path) -> None:
    """Suppression/repeat history comes only from exact verified durable evidence."""

    async def exercise() -> None:
        store = await open_store(tmp_path / "history.sqlite3")
        item = topic()
        triage_ref = await save_triage(store, triage_data(item))
        configured = policy().model_copy(
            update={
                "repeat_mode": RepeatMode.AFTER_INTERVAL,
                "repeat_after_seconds": 60,
            }
        )
        evidence_ref = ResultRef("submission-r3", "report_submission", "1")
        reported_at = datetime(2026, 9, 30, 8, 0, tzinfo=UTC)
        state = PriorReportState(
            policy_ref=configured.policy_ref,
            assessment_ref=item.assessment_ref,
            report_ref=ref("report", "previous"),
            reported_at=reported_at,
            evidence_ref=evidence_ref,
        )
        selection = plan(triage_ref).model_copy(update={"prior_state": (state,)})
        await _save_submission(
            store, evidence_ref, item.assessment_ref, configured.policy_ref.version
        )
        metadata = ReportHistoryMetadata(evidence_ref=evidence_ref)
        evidence = ReportHistoryEvidence(
            evidence_ref=evidence_ref,
            report_ref=state.report_ref,
            policy_ref=state.policy_ref,
            assessment_ref=state.assessment_ref,
            reported_at=state.reported_at,
            receipt_ref=ref("delivery-receipt", "receipt-r3"),
            external_effect=ExternalEffectState.CONFIRMED,
        )
        handler = ReportBuildHandler(
            policy=configured,
            selection_plan=selection,
            persistence=store,
            renderer_config=RendererConfig(
                max_part_bytes=100_000, max_total_bytes=300_000, max_parts=8
            ),
            config=_config("history-report"),
            history_resolver=_HistoryResolver(metadata, evidence),
        )
        outcome = await handler.run(_request(selection, "history-execution"))
        if outcome.status is not TerminalStatus.COMPLETE:
            pytest.fail("verified confirmed history did not permit interval repeat")
        frozen_result = await store.get_result("selection-history-report")
        if frozen_result is None or frozen_result.semantic_data_ref is None:
            pytest.fail("history selection snapshot was not durable")
        frozen = await store.load_semantic_data(frozen_result.semantic_data_ref)
        if not isinstance(frozen, FrozenReportSelection) or not frozen.history:
            pytest.fail("verified history basis was not frozen")
        if frozen.history[0].receipt_ref != evidence.receipt_ref:
            pytest.fail("frozen history lost exact receipt integrity identity")

        forged = evidence.model_copy(
            update={"reported_at": datetime(2026, 9, 29, 8, 0, tzinfo=UTC)}
        )
        bad = ReportBuildHandler(
            policy=configured,
            selection_plan=selection,
            persistence=store,
            renderer_config=RendererConfig(
                max_part_bytes=100_000, max_total_bytes=300_000, max_parts=8
            ),
            config=_config("history-forged"),
            history_resolver=_HistoryResolver(metadata, forged),
        )
        failed = await bad.run(_request(selection, "history-forged-execution"))
        if failed.status is not TerminalStatus.FAILED:
            pytest.fail("caller-forged history timestamp was accepted")
        frozen_ref = frozen_result.semantic_data_ref
        await store.close()

        reopened = await open_store(tmp_path / "history.sqlite3")
        try:
            replay = await reopened.load_semantic_data(frozen_ref)
            if replay != frozen:
                pytest.fail("restart changed frozen selection/history basis")
        finally:
            await reopened.close()

    asyncio.run(exercise())


def test_handler_passes_claim_to_both_semantic_publications(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Selection and final report writes are both fenced by the acquired claim."""

    async def exercise() -> None:
        store = await open_store(tmp_path / "claims.sqlite3")
        triage_ref = await save_triage(store, triage_data(topic()))
        selection = plan(triage_ref)
        original = store.append_result_with_data
        claims = []

        async def observed(result: object, value: object, **kwargs: object) -> None:
            if getattr(result, "kind", None) in {"report_selection", "report"}:
                claims.append(kwargs.get("claim"))
            await original(result, value, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(store, "append_result_with_data", observed)
        outcome = await ReportBuildHandler(
            policy=policy(),
            selection_plan=selection,
            persistence=store,
            renderer_config=RendererConfig(
                max_part_bytes=100_000, max_total_bytes=300_000, max_parts=8
            ),
            config=_config("claim-report"),
        ).run(_request(selection, "claim-execution"))
        if outcome.status is not TerminalStatus.COMPLETE:
            pytest.fail("claim-fenced report fixture did not complete")
        if len(claims) != 2 or any(claim is None for claim in claims):
            pytest.fail("one or more report publications were not claim fenced")
        if claims[0] != claims[1]:
            pytest.fail("report publications did not use the exact same claim token")
        await store.close()

    asyncio.run(exercise())


def test_two_facade_reclaim_rejects_stale_semantic_publication(tmp_path: Path) -> None:
    """A reclaimed claim fences a stale owner's semantic publication atomically."""

    async def exercise() -> None:
        path = tmp_path / "stale.sqlite3"
        first = await open_store(path)
        triage_ref = await save_triage(first, triage_data(topic()))
        second = await open_store(path)
        try:
            old = await first.acquire_claim(
                "r3-stale",
                ClaimKind.REPORT_BUILD,
                ExecutionIdentity("old-execution"),
                AttemptIdentity("old-attempt"),
                required_inputs=(triage_ref,),
                lease_seconds=0.01,
            )
            await asyncio.sleep(0.03)
            await second.acquire_claim(
                "r3-stale",
                ClaimKind.REPORT_BUILD,
                ExecutionIdentity("new-execution"),
                AttemptIdentity("new-attempt"),
                required_inputs=(triage_ref,),
                lease_seconds=1.0,
            )
            data = triage_data(topic("stale-topic", "stale-assessment"))
            data_ref = first.semantic_reference("stale-data", "triage", "1", data)
            stale_result = StageResult(
                result_id="stale-result",
                kind="triage",
                schema_version="1",
                execution=ExecutionIdentity("old-execution"),
                attempt=AttemptIdentity("old-child"),
                input_refs=(),
                source_versions=(),
                prepared_versions=(),
                topic_versions=(),
                configuration_version="synthetic",
                code_version="synthetic",
                status=TerminalStatus.COMPLETE,
                acceptable=True,
                semantic_data_ref=data_ref,
            )
            with pytest.raises(Phase1PersistenceError):
                await first.append_result_with_data(stale_result, data, claim=old)
            if await second.get_result("stale-result") is not None:
                pytest.fail("stale owner published after claim reclaim")
        finally:
            await first.close()
            await second.close()

    asyncio.run(exercise())


def test_history_unknown_effect_and_same_version_other_policy_fail(
    tmp_path: Path,
) -> None:
    """Only accepted/confirmed exact-policy receipt evidence can affect selection."""

    async def exercise() -> None:
        store = await open_store(tmp_path / "history-invalid.sqlite3")
        item = topic()
        triage_ref = await save_triage(store, triage_data(item))
        configured = policy().model_copy(
            update={
                "repeat_mode": RepeatMode.AFTER_INTERVAL,
                "repeat_after_seconds": 60,
            }
        )
        evidence_ref = ResultRef("submission-invalid", "report_submission", "1")
        state = PriorReportState(
            policy_ref=configured.policy_ref,
            assessment_ref=item.assessment_ref,
            report_ref=ref("report", "previous-invalid"),
            reported_at=datetime(2026, 9, 30, 8, 0, tzinfo=UTC),
            evidence_ref=evidence_ref,
        )
        selection = plan(triage_ref).model_copy(update={"prior_state": (state,)})
        await _save_submission(
            store, evidence_ref, item.assessment_ref, configured.policy_ref.version
        )
        metadata = ReportHistoryMetadata(evidence_ref=evidence_ref)
        valid = ReportHistoryEvidence(
            evidence_ref=evidence_ref,
            report_ref=state.report_ref,
            policy_ref=state.policy_ref,
            assessment_ref=state.assessment_ref,
            reported_at=state.reported_at,
            receipt_ref=ref("delivery-receipt", "invalid-cases"),
            external_effect=ExternalEffectState.ACCEPTED,
        )
        for identity, forged in (
            (
                "unknown",
                valid.model_copy(
                    update={"external_effect": ExternalEffectState.UNKNOWN}
                ),
            ),
            (
                "other-policy",
                valid.model_copy(
                    update={
                        "policy_ref": ref(
                            "report-policy", "different-owner", state.policy_ref.version
                        )
                    }
                ),
            ),
        ):
            handler = ReportBuildHandler(
                policy=configured,
                selection_plan=selection,
                persistence=store,
                renderer_config=RendererConfig(
                    max_part_bytes=100_000, max_total_bytes=300_000, max_parts=8
                ),
                config=_config(f"history-{identity}"),
                history_resolver=_HistoryResolver(metadata, forged),
            )
            outcome = await handler.run(
                _request(selection, f"history-{identity}-execution")
            )
            if outcome.status is not TerminalStatus.FAILED:
                pytest.fail(f"invalid history evidence was accepted: {identity}")
        await store.close()

    asyncio.run(exercise())


def test_selection_codec_rejects_forged_renderer_snapshot(tmp_path: Path) -> None:
    """Frozen selection codec revalidates nested renderer bounds after model_copy."""

    async def exercise() -> None:
        from msgloom.reporting import ReportSelectionCodec

        store = await open_store(tmp_path / "selection-codec.sqlite3")
        triage_ref = await save_triage(store, triage_data(topic()))
        selection = plan(triage_ref)
        outcome = await ReportBuildHandler(
            policy=policy(),
            selection_plan=selection,
            persistence=store,
            renderer_config=RendererConfig(
                max_part_bytes=100_000, max_total_bytes=300_000, max_parts=8
            ),
            config=_config("selection-codec-report"),
        ).run(_request(selection, "selection-codec-execution"))
        if outcome.status is not TerminalStatus.COMPLETE:
            pytest.fail("selection codec fixture did not complete")
        saved = await store.get_result("selection-selection-codec-report")
        if saved is None or saved.semantic_data_ref is None:
            pytest.fail("selection codec fixture did not persist selection")
        frozen = await store.load_semantic_data(saved.semantic_data_ref)
        if not isinstance(frozen, FrozenReportSelection):
            pytest.fail("selection codec fixture loaded wrong type")
        forged = frozen.model_copy(
            update={"renderer": frozen.renderer.model_copy(update={"max_parts": 0})}
        )
        with pytest.raises(TypeError, match="failed validation"):
            ReportSelectionCodec().encode(forged)
        await store.close()

    asyncio.run(exercise())
