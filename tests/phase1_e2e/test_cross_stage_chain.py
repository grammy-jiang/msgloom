"""Cross-stage acceptance over actual Phase 1 producers and persistence."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import cast

import pytest

from msgloom.contracts import (
    ExecutionIdentity,
    PhaseCapability,
    TerminalStatus,
    VersionRef,
)
from msgloom.preparation import PreparedSourceType
from msgloom.preparation.grouping import GroupResult, GroupStatus
from msgloom.preparation_pipeline import PreparationHandler
from msgloom.reporting import SavedReport
from msgloom.sources import CollectedSourceReader
from msgloom.triage import (
    ActionOwner,
    Deadline,
    Development,
    EvidenceKind,
    OwnerState,
    Priority,
    Risk,
    TopicAllocation,
    TopicCandidate,
    TriageAction,
    TriageCandidate,
    TriageData,
    TriageEvidence,
)
from msgloom.triage_pipeline import TriageHandler
from tests.reporting.helpers import plan as report_plan
from tests.triage_pipeline.helpers import FakeRunner

from .helpers import (
    app_for,
    collected_record,
    open_store,
    preparation_plan,
    prepared_records,
    request,
    require_status,
    run_report,
    saved_reader,
    semantic_values,
    static_reader,
    triage_config,
)


def _allocation(identity: str, version: str = "v1") -> TopicAllocation:
    return TopicAllocation(
        allocation_key=f"allocation-{identity}",
        topic_ref=VersionRef("topic", identity, "v1"),
        assessment_ref=VersionRef("topic-assessment", identity, version),
    )


def _candidate(
    allocation: TopicAllocation,
    source: VersionRef,
    statement: str,
    *,
    title: str,
    limitation=(),
) -> TopicCandidate:
    evidence = TriageEvidence(
        kind=EvidenceKind.SOURCE_STATEMENT,
        source_ref=source,
        statement=statement,
    )
    return TopicCandidate(
        allocation_key=allocation.allocation_key,
        title=title,
        source_refs=(source,),
        priority=Priority.IMPORTANT,
        reason="Synthetic important work retained across stage boundaries.",
        developments=(Development(text=statement, evidence=(evidence,)),),
        actions=(
            TriageAction(
                text=f"Act on {title}",
                owner=ActionOwner(state=OwnerState.UNKNOWN),
                evidence=(evidence,),
            ),
        ),
        deadlines=(
            Deadline(
                original_wording="by synthetic Friday",
                interpreted_at=None,
                timezone_basis=None,
                ambiguous=True,
                evidence=(evidence,),
            ),
        ),
        risks=(Risk(text=f"Risk for {title}", evidence=(evidence,)),),
        limitations=limitation,
    )


def test_saved_a1_chain_survives_restart_with_exact_lineage_and_order(
    saved_catalog: dict[str, object], tmp_path: Path
) -> None:
    """Saved A1 evidence flows through A2, A3, and A5 without shortcuts."""

    async def exercise() -> None:
        database = tmp_path / "phase1-chain.sqlite3"
        reader = saved_reader(saved_catalog)
        store = await open_store(database)
        versions = await reader.list_versions(
            PreparedSourceType.OUTLOOK_EMAIL,
            source_id=cast(str, saved_catalog["source_id"]),
            limit=10,
        )
        current = next(item for item in versions if item.version == "obs-current")
        parent = next(item for item in versions if item.version == "obs-parent")
        sources = (parent, current)
        preparation = preparation_plan(sources, attempt="acceptance-prepare")
        prepare_handler = PreparationHandler(store, reader, preparation)
        prepared = await app_for(
            store, PhaseCapability.PREPARE, lambda: prepare_handler
        ).run(request(PhaseCapability.PREPARE, "acceptance-prepare", sources))
        if prepared.status not in {TerminalStatus.COMPLETE, TerminalStatus.INCOMPLETE}:
            pytest.fail(f"saved A1 preparation failed: {prepared}")

        records = await prepared_records(store, prepared.result_refs)
        groups = await semantic_values(store, prepared.result_refs, "group_result")
        if not any(
            isinstance(item, GroupResult) and item.status is GroupStatus.CONFIRMED
            for item in groups
        ):
            pytest.fail(
                "source-native reply evidence did not produce a confirmed group"
            )

        allocations = (_allocation("parent"), _allocation("current"))
        config = triage_config(
            records,
            prepared.result_refs,
            preparation,
            allocations,
            key="saved-a1",
        )
        statements = {
            record.source: record.body for record in records if record.body is not None
        }
        topics = tuple(
            _candidate(
                allocation,
                source,
                statements[source],
                title=f"Synthetic topic {index}",
            )
            for index, (allocation, source) in enumerate(
                zip(allocations, sources, strict=True), start=1
            )
        )
        runner = FakeRunner(store, [TriageCandidate(topics=topics, dispositions=())])
        triage_handler = TriageHandler(store, config, runner)
        triaged = await app_for(
            store, PhaseCapability.TRIAGE, lambda: triage_handler
        ).run(
            request(
                PhaseCapability.TRIAGE,
                "acceptance-triage",
                config.plan.expected_targets,
                parameters=config.expected_parameters,
            )
        )
        require_status(triaged, TerminalStatus.COMPLETE, "A3 did not complete")
        if runner.calls != 1 or runner.request_was_saved != [True]:
            pytest.fail("fake model boundary bypassed durable AI request evidence")

        report_selection = report_plan(*triaged.result_refs)
        reported = await run_report(
            store, report_selection, identity="acceptance-report"
        )
        require_status(reported, TerminalStatus.COMPLETE, "A5 did not complete")
        report_values = await semantic_values(store, reported.result_refs, "report")
        if len(report_values) != 1 or not isinstance(report_values[0], SavedReport):
            pytest.fail("A5 did not persist one canonical SavedReport")
        report = cast(SavedReport, report_values[0])
        if {topic.topic_ref for topic in report.topics} != {
            item.topic_ref for item in allocations
        }:
            pytest.fail("report lost exact topic identities")
        rendered = "\n".join(f"{part.plain_text}\n{part.html}" for part in report.parts)
        for text in ("Parent body", "Current body", "Act on", "synthetic Friday"):
            if text not in rendered:
                pytest.fail(f"report lost required cross-stage content: {text}")

        triage_saved = await store.get_result(triaged.result_refs[0].result_id)
        report_saved = await store.get_result(reported.result_refs[0].result_id)
        if triage_saved is None or set(triage_saved.source_versions) != set(sources):
            pytest.fail("A3 source lineage does not match exact A1 versions")
        if not triage_saved.prepared_versions:
            pytest.fail("A3 omitted prepared lineage")
        if (
            report_saved is None
            or report_saved.input_refs[0].kind != "report_selection"
        ):
            pytest.fail("A5 did not depend on its durable frozen selection")
        for execution in (
            "acceptance-prepare",
            "acceptance-triage",
            "acceptance-report-execution",
        ):
            if await store.get_outcome(ExecutionIdentity(execution)) is None:
                pytest.fail(
                    f"Application outcome was not awaited and saved: {execution}"
                )

        snapshot = {
            ref: await store.get_result(ref.result_id)
            for ref in (
                *prepared.result_refs,
                *triaged.result_refs,
                *reported.result_refs,
            )
        }
        await store.close()

        reopened = await open_store(database)
        try:
            for ref, expected in snapshot.items():
                if await reopened.get_result(ref.result_id) != expected:
                    pytest.fail("restart changed immutable cross-stage result lineage")
        finally:
            await reopened.close()
            await reader.close()

    asyncio.run(exercise())


def test_same_subject_independent_work_stays_separate_through_report(
    tmp_path: Path,
) -> None:
    """Display-title equality never becomes a cross-source semantic join."""

    async def exercise() -> None:
        first = collected_record(
            "work-a", subject="Weekly review", body="Synthetic work A needs approval."
        )
        second = collected_record(
            "work-b", subject="Weekly review", body="Synthetic work B needs renewal."
        )
        sources = (first.source, second.source)
        store = await open_store(tmp_path / "same-subject.sqlite3")
        preparation = preparation_plan(sources, attempt="same-subject")
        handler = PreparationHandler(
            store,
            cast(CollectedSourceReader, static_reader(first, second)),
            preparation,
        )
        prepared = await app_for(store, PhaseCapability.PREPARE, lambda: handler).run(
            request(PhaseCapability.PREPARE, "same-subject-prepare", sources)
        )
        require_status(prepared, TerminalStatus.COMPLETE, "A2 same-subject case failed")
        groups = await semantic_values(store, prepared.result_refs, "group_result")
        if len(groups) != 2 or any(
            not isinstance(item, GroupResult) or item.status is not GroupStatus.NONE
            for item in groups
        ):
            pytest.fail("same subject caused unsupported grouping")

        records = await prepared_records(store, prepared.result_refs)
        allocations = (_allocation("work-a"), _allocation("work-b"))
        config = triage_config(
            records,
            prepared.result_refs,
            preparation,
            allocations,
            key="same-subject",
        )
        candidates = [
            TriageCandidate(
                topics=(
                    _candidate(
                        allocation,
                        record.source,
                        record.body or "",
                        title="Weekly review",
                    ),
                ),
                dispositions=(),
            )
            for allocation, record in zip(allocations, records, strict=True)
        ]
        runner = FakeRunner(store, candidates)
        triaged = await app_for(
            store,
            PhaseCapability.TRIAGE,
            lambda: TriageHandler(store, config, runner),
        ).run(
            request(
                PhaseCapability.TRIAGE,
                "same-subject-triage",
                config.plan.expected_targets,
                parameters=config.expected_parameters,
            )
        )
        require_status(triaged, TerminalStatus.COMPLETE, "A3 same-subject case failed")
        values = await semantic_values(store, triaged.result_refs, "triage")
        if len(values) != 1 or not isinstance(values[0], TriageData):
            pytest.fail("A3 omitted canonical triage data")
        data = cast(TriageData, values[0])
        if (
            len(data.topics) != 2
            or data.topics[0].topic_ref == data.topics[1].topic_ref
        ):
            pytest.fail("independent same-subject work was merged")

        reported = await run_report(
            store,
            report_plan(*triaged.result_refs),
            identity="same-subject-report",
        )
        require_status(reported, TerminalStatus.COMPLETE, "A5 same-subject case failed")
        report = cast(
            SavedReport,
            (await semantic_values(store, reported.result_refs, "report"))[0],
        )
        if len(report.topics) != 2:
            pytest.fail("report collapsed independent same-subject work")
        await store.close()

    asyncio.run(exercise())


def test_many_important_topics_keep_actions_deadlines_and_report_coverage(
    tmp_path: Path,
) -> None:
    """Multipart rendering retains every important topic and essential detail."""

    async def exercise() -> None:
        record = collected_record(
            "many-topics",
            subject="Synthetic portfolio",
            body="Synthetic portfolio needs coordinated review.",
        )
        store = await open_store(tmp_path / "many-topics.sqlite3")
        preparation = preparation_plan((record.source,), attempt="many-topics")
        prepared = await app_for(
            store,
            PhaseCapability.PREPARE,
            lambda: PreparationHandler(
                store,
                cast(CollectedSourceReader, static_reader(record)),
                preparation,
            ),
        ).run(
            request(
                PhaseCapability.PREPARE,
                "many-topics-prepare",
                (record.source,),
            )
        )
        require_status(prepared, TerminalStatus.COMPLETE, "A2 many-topics case failed")
        records = await prepared_records(store, prepared.result_refs)
        allocations = tuple(_allocation(f"important-{index}") for index in range(12))
        config = triage_config(
            records,
            prepared.result_refs,
            preparation,
            allocations,
            key="many-topics",
        )
        topics = tuple(
            _candidate(
                allocation,
                record.source,
                "Synthetic portfolio needs coordinated review.",
                title=f"Important synthetic topic {index}",
            )
            for index, allocation in enumerate(allocations)
        )
        triaged, runner = await _run_candidate(
            store,
            config,
            TriageCandidate(topics=topics, dispositions=()),
            "many-topics-triage",
        )
        require_status(triaged, TerminalStatus.COMPLETE, "A3 many-topics case failed")
        if runner.request_was_saved != [True]:
            pytest.fail("many-topics model request was not evidence-first")

        reported = await run_report(
            store,
            report_plan(*triaged.result_refs),
            identity="many-topics-report",
            max_part_bytes=16_384,
        )
        require_status(reported, TerminalStatus.COMPLETE, "A5 many-topics case failed")
        report = cast(
            SavedReport,
            (await semantic_values(store, reported.result_refs, "report"))[0],
        )
        if len(report.topics) != 12 or len(report.overview) != 12:
            pytest.fail("report coverage omitted important topics")
        if len(report.parts) < 2:
            pytest.fail("acceptance fixture did not exercise multipart rendering")
        for topic in report.topics:
            if not topic.actions or not topic.deadlines or not topic.risks:
                pytest.fail("report lost an action, deadline, or risk")
        rendered = "\n".join(part.plain_text + part.html for part in report.parts)
        for index in range(12):
            if f"Important synthetic topic {index}" not in rendered:
                pytest.fail(f"rendered variants lost topic {index}")
        await store.close()

    asyncio.run(exercise())


async def _run_candidate(store, config, candidate, execution):
    runner = FakeRunner(store, [candidate] * config.max_parts)
    outcome = await app_for(
        store,
        PhaseCapability.TRIAGE,
        lambda: TriageHandler(store, config, runner),
    ).run(
        request(
            PhaseCapability.TRIAGE,
            execution,
            config.plan.expected_targets,
            parameters=config.expected_parameters,
        )
    )
    return outcome, runner
