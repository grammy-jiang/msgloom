"""Cross-stage failure and evidence-gap acceptance."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from msgloom.ai import AnalysisResponse, AttemptStatus
from msgloom.contracts import (
    ExecutionIdentity,
    PhaseCapability,
    TerminalStatus,
    VersionRef,
)
from msgloom.preparation import PreparedSourceType
from msgloom.preparation_pipeline import PreparationHandler
from msgloom.reporting import SavedReport
from msgloom.sources import CollectedSourceReader
from msgloom.triage import (
    PredicateKind,
    Priority,
    RuleEffect,
    RuleEffectKind,
    RulePredicate,
    SourceDisposition,
    SourceDispositionKind,
    TopicAllocation,
    TriageCandidate,
    TriageData,
    TriageRule,
    TriageRuleConfig,
)
from msgloom.triage_pipeline import TriageHandler
from msgloom.working_context import MemoryFileSelection, WorkingContextSnapshot
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


class MalformedRunner:
    """Return transport-complete but schema-invalid synthetic output."""

    calls = 0

    async def run(self, attempt, trace_sink):
        """Return an undeclared field without provider or network use."""
        self.calls += 1
        return AnalysisResponse(
            attempt=attempt.attempt,
            status=AttemptStatus.COMPLETE,
            structured_output={"invented": "claim"},
            trace_count=0,
        )


def _allocation(identity: str) -> TopicAllocation:
    return TopicAllocation(
        allocation_key=f"allocation-{identity}",
        topic_ref=VersionRef("topic", identity, "v1"),
        assessment_ref=VersionRef("topic-assessment", identity, "v1"),
    )


def _conflicting_rules(subject: str) -> TriageRuleConfig:
    predicate = RulePredicate(kind=PredicateKind.SUBJECT_EXACT, text_value=subject)
    return TriageRuleConfig(
        version=VersionRef("triage_rule_config", "conflict", "v1"),
        rules=(
            TriageRule(
                rule_ref=VersionRef("triage_rule", "critical", "v1"),
                predicates=(predicate,),
                effects=(
                    RuleEffect(
                        kind=RuleEffectKind.REQUIRED_PRIORITY,
                        priority=Priority.CRITICAL,
                    ),
                ),
            ),
            TriageRule(
                rule_ref=VersionRef("triage_rule", "low", "v1"),
                predicates=(predicate,),
                effects=(
                    RuleEffect(
                        kind=RuleEffectKind.REQUIRED_PRIORITY,
                        priority=Priority.LOW_VALUE,
                    ),
                ),
            ),
        ),
    )


def test_conflict_and_malformed_model_never_create_false_report(
    tmp_path: Path,
) -> None:
    """A3 review/failure states cannot become a false completed A5 report."""

    async def exercise() -> None:
        record = collected_record(
            "conflict",
            subject="Synthetic conflict",
            body="Synthetic conflict needs explicit review.",
        )
        store = await open_store(tmp_path / "conflict.sqlite3")
        preparation = preparation_plan((record.source,), attempt="conflict-prepare")
        prepared = await app_for(
            store,
            PhaseCapability.PREPARE,
            lambda: PreparationHandler(
                store,
                cast(CollectedSourceReader, static_reader(record)),
                preparation,
            ),
        ).run(request(PhaseCapability.PREPARE, "conflict-prepare", (record.source,)))
        require_status(prepared, TerminalStatus.COMPLETE, "A2 conflict setup failed")
        records = await prepared_records(store, prepared.result_refs)
        allocation = _allocation("conflict")

        malformed_config = triage_config(
            records,
            prepared.result_refs,
            preparation,
            (allocation,),
            key="malformed",
        )
        malformed_runner = MalformedRunner()
        malformed = await app_for(
            store,
            PhaseCapability.TRIAGE,
            lambda: TriageHandler(store, malformed_config, malformed_runner),
        ).run(
            request(
                PhaseCapability.TRIAGE,
                "malformed-triage",
                malformed_config.plan.expected_targets,
                parameters=malformed_config.expected_parameters,
            )
        )
        require_status(
            malformed,
            TerminalStatus.INCOMPLETE,
            "malformed model output became accepted analysis",
        )
        if any(ref.kind == "triage" for ref in malformed.result_refs):
            pytest.fail("malformed model output published triage semantics")

        conflict_config = triage_config(
            records,
            prepared.result_refs,
            preparation,
            (allocation,),
            key="rule-conflict",
            rules=_conflicting_rules("Synthetic conflict"),
        )
        conflict_config = replace(
            conflict_config,
            plan=replace(conflict_config.plan, topic_allocations=()),
        )
        disposition = SourceDisposition(
            source_ref=record.source,
            kind=SourceDispositionKind.REVIEW_REQUIRED,
            reason="Conflicting required priorities need explicit review.",
        )
        runner = FakeRunner(
            store,
            [TriageCandidate(topics=(), dispositions=(disposition,))],
        )
        conflict = await app_for(
            store,
            PhaseCapability.TRIAGE,
            lambda: TriageHandler(store, conflict_config, runner),
        ).run(
            request(
                PhaseCapability.TRIAGE,
                "conflict-triage",
                conflict_config.plan.expected_targets,
                parameters=conflict_config.expected_parameters,
            )
        )
        require_status(conflict, TerminalStatus.COMPLETE, "rule review was not saved")
        values = await semantic_values(store, conflict.result_refs, "triage")
        if len(values) != 1 or not isinstance(values[0], TriageData):
            pytest.fail("conflict review omitted canonical triage data")
        data = cast(TriageData, values[0])
        if (
            data.topics
            or data.dispositions[0].kind is not SourceDispositionKind.REVIEW_REQUIRED
        ):
            pytest.fail("rule conflict became a semantic priority fallback")

        report = await run_report(
            store,
            report_plan(*conflict.result_refs),
            identity="conflict-report",
        )
        require_status(
            report,
            TerminalStatus.FAILED,
            "review-only analysis incorrectly produced a completed report",
        )
        for execution in (
            "malformed-triage",
            "conflict-triage",
            "conflict-report-execution",
        ):
            if await store.get_outcome(ExecutionIdentity(execution)) is None:
                pytest.fail(f"terminal outcome was not persisted: {execution}")
        await store.close()

    asyncio.run(exercise())


def test_missing_attachment_and_memory_remain_explicit_in_saved_chain(
    saved_catalog: dict[str, object], tmp_path: Path
) -> None:
    """Missing selected evidence stays visible through A2, A3, and A5."""

    async def exercise() -> None:
        real = saved_reader(saved_catalog)
        versions = await real.list_versions(
            PreparedSourceType.OUTLOOK_EMAIL,
            source_id=cast(str, saved_catalog["source_id"]),
            limit=10,
        )
        source = next(item for item in versions if item.version == "obs-current")
        root = cast(Path, saved_catalog["evidence_root"])

        class RaceReader:
            def __init__(self) -> None:
                self.changed = False

            async def read_selection(self, requested):
                selection = await real.read_selection(requested)
                if not self.changed:
                    saved = selection.record.attachments[0].saved_bytes
                    if saved is None:
                        pytest.fail("fixture attachment omitted saved bytes")
                    (root / f"{saved.sha256}.bin").unlink()
                    self.changed = True
                return selection

            async def load_saved_bytes(self, reference):
                return await real.load_saved_bytes(reference)

        store = await open_store(tmp_path / "missing-evidence.sqlite3")
        preparation = preparation_plan((source,), attempt="missing-evidence")
        prepared = await app_for(
            store,
            PhaseCapability.PREPARE,
            lambda: PreparationHandler(
                store, cast(CollectedSourceReader, RaceReader()), preparation
            ),
        ).run(
            request(
                PhaseCapability.PREPARE,
                "missing-evidence-prepare",
                (source,),
            )
        )
        require_status(
            prepared,
            TerminalStatus.INCOMPLETE,
            "missing attachment was not retained as incomplete",
        )
        records = await prepared_records(store, prepared.result_refs)
        record = records[0]
        if not any(
            item.code == "saved-content-unavailable" for item in record.limitations
        ):
            pytest.fail("prepared record lost the attachment limitation")

        allocation = _allocation("missing-evidence")
        config = triage_config(
            records,
            prepared.result_refs,
            preparation,
            (allocation,),
            key="missing-evidence",
        )
        if config.working_context_config is None:
            pytest.fail("live A3 context configuration is absent")
        context = config.working_context_config.model_copy(
            update={
                "selected_files": (
                    MemoryFileSelection(
                        selection_id="missing-memory",
                        path="/tmp/msgloom-phase1-e2e-missing-memory.txt",
                    ),
                )
            }
        )
        config = replace(config, working_context_config=context)
        from tests.phase1_e2e.test_cross_stage_chain import _candidate

        candidate = TriageCandidate(
            topics=(
                _candidate(
                    allocation,
                    source,
                    "Current body",
                    title="Missing evidence topic",
                    limitation=record.limitations,
                ),
            ),
            dispositions=(),
        )
        runner = FakeRunner(store, [candidate])
        triaged = await app_for(
            store,
            PhaseCapability.TRIAGE,
            lambda: TriageHandler(store, config, runner),
        ).run(
            request(
                PhaseCapability.TRIAGE,
                "missing-evidence-triage",
                config.plan.expected_targets,
                parameters=config.expected_parameters,
            )
        )
        require_status(triaged, TerminalStatus.COMPLETE, "A3 evidence-gap case failed")
        final = await store.get_result(triaged.result_refs[0].result_id)
        if final is None:
            pytest.fail("A3 final result is missing")
        context_ref = next(
            (ref for ref in final.input_refs if ref.kind == "working_context"), None
        )
        if context_ref is None:
            pytest.fail("A3 final result omitted exact working-context lineage")
        context_result = await store.get_result(context_ref.result_id)
        if context_result is None or context_result.semantic_data_ref is None:
            pytest.fail("saved working context is missing")
        snapshot = await store.load_semantic_data(context_result.semantic_data_ref)
        if not isinstance(snapshot, WorkingContextSnapshot):
            pytest.fail("working-context semantic type is invalid")
        if not snapshot.files or not snapshot.files[0].limitations:
            pytest.fail("missing selected memory was not explicit")

        reported = await run_report(
            store,
            report_plan(*triaged.result_refs),
            identity="missing-evidence-report",
        )
        require_status(
            reported,
            TerminalStatus.INCOMPLETE,
            "report hid upstream evidence limitations",
        )
        report = cast(
            SavedReport,
            (await semantic_values(store, reported.result_refs, "report"))[0],
        )
        if not any(
            item.code == "saved-content-unavailable"
            for topic in report.topics
            for item in topic.limitations
        ):
            pytest.fail("report lost the selected attachment limitation")
        await store.close()
        await real.close()

    asyncio.run(exercise())
