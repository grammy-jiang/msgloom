"""Synthetic real-persistence fixtures for the A3 producer."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from msgloom.ai import AnalysisResponse, AttemptLimits, AttemptStatus, TrustedPolicy
from msgloom.ai_evidence import AI_EVIDENCE_CODECS
from msgloom.contracts import (
    AttemptIdentity,
    ExecutionIdentity,
    ResultSchemaRegistry,
    StageResult,
    TerminalStatus,
    VersionRef,
)
from msgloom.persistence import Phase1Persistence, SemanticDataRegistry
from msgloom.preparation.codec import PreparedDataCodec
from msgloom.preparation.filtering import FilterResultCodec
from msgloom.preparation.grouping import GroupResultCodec
from msgloom.sources import CollectedSelectionCodec
from msgloom.triage import (
    Development,
    EvidenceKind,
    Priority,
    TopicAllocation,
    TopicCandidate,
    TriageCandidate,
    TriageDataCodec,
    TriageEvidence,
    TriageRuleEvaluationCodec,
)
from msgloom.triage_input import (
    TriageInputCodec,
    TrustedInputVersions,
)
from msgloom.triage_pipeline import (
    TRIAGE_PIPELINE_CODECS,
    TriageHandler,
    TriageMode,
    TriageProducerConfig,
    TriageReplayPlan,
)
from msgloom.working_context import (
    CaptureTimePolicy,
    StalePolicy,
    WorkingContextCodec,
    WorkingContextConfig,
)
from tests.triage_input.helpers import config as input_config
from tests.triage_input.helpers import record, selection


def registries():
    """Return explicit opt-in registries without changing product defaults."""
    result = ResultSchemaRegistry.phase1()
    for codec in TRIAGE_PIPELINE_CODECS:
        result = result.with_schema(
            codec.kind, codec.schema_version, semantic_data_required=True
        )
    semantic = SemanticDataRegistry(
        (
            CollectedSelectionCodec(),
            PreparedDataCodec(),
            FilterResultCodec(),
            GroupResultCodec(),
            WorkingContextCodec(),
            TriageRuleEvaluationCodec(),
            TriageInputCodec(),
            TriageDataCodec(),
            *AI_EVIDENCE_CODECS,
            *TRIAGE_PIPELINE_CODECS,
        )
    )
    return result, semantic


async def open_store(path: Path) -> Phase1Persistence:
    """Open real SQLite persistence with explicit A3 producer codecs."""
    result, semantic = registries()
    return await Phase1Persistence.open(
        f"sqlite:///{path}", registry=result, semantic_registry=semantic
    )


def stage(
    result_ref,
    data_ref,
    source_refs: tuple[VersionRef, ...],
    prepared_refs: tuple[VersionRef, ...],
) -> StageResult:
    """Build one acceptable synthetic upstream result with prepared lineage."""
    return StageResult(
        result_id=result_ref.result_id,
        kind=result_ref.kind,
        schema_version=result_ref.schema_version,
        execution=ExecutionIdentity("upstream-exec"),
        attempt=AttemptIdentity(f"attempt-{result_ref.result_id}"),
        input_refs=(),
        source_versions=source_refs,
        prepared_versions=prepared_refs,
        topic_versions=(),
        configuration_version="upstream-config",
        code_version="upstream-code",
        status=TerminalStatus.COMPLETE,
        acceptable=True,
        semantic_data_ref=data_ref,
    )


async def save_selection(store: Phase1Persistence, selected) -> None:
    """Persist exact prepared/filter/group values named by a pure selection."""
    prepared = {
        binding.record.source: VersionRef(
            "prepared",
            binding.result_ref.result_id,
            binding.data_ref.sha256,
        )
        for binding in selected.prepared
    }
    for binding in selected.prepared:
        await store.append_result_with_data(
            stage(
                binding.result_ref,
                binding.data_ref,
                (binding.record.source,),
                (prepared[binding.record.source],),
            ),
            binding.record,
        )
    for binding in selected.filters:
        await store.append_result_with_data(
            stage(
                binding.result_ref,
                binding.data_ref,
                (binding.result.input,),
                (prepared[binding.result.input],),
            ),
            binding.result,
        )
    all_sources = tuple(prepared)
    all_prepared = tuple(prepared[source] for source in all_sources)
    for binding in selected.groups:
        await store.append_result_with_data(
            stage(binding.result_ref, binding.data_ref, all_sources, all_prepared),
            binding.result,
        )


class FakeRunner:
    """Deterministic runner proving request evidence exists before execution."""

    def __init__(self, store, candidates):
        self.store = store
        self.candidates = list(candidates)
        self.calls = 0
        self.request_was_saved = []
        self.attempts = []

    async def run(self, attempt, trace_sink):
        """Return the next synthetic structured candidate without provider use."""
        self.attempts.append(attempt)
        saved = await self.store.get_result(f"ai-request:{attempt.attempt.value}")
        self.request_was_saved.append(saved is not None and saved.acceptable)
        candidate = self.candidates[self.calls]
        self.calls += 1
        return AnalysisResponse(
            attempt=attempt.attempt,
            status=AttemptStatus.COMPLETE,
            structured_output=candidate.model_dump(mode="json"),
            trace_count=0,
        )


def setup(*, allocations=1, prompt_version="v1"):
    """Return one-source exact selection, config, plan, and candidates."""
    source = record("source-1", body="Synthetic approval is requested.")
    selected = selection((source,))
    versions = TrustedInputVersions(
        prompt=VersionRef("prompt", "triage", prompt_version),
        model=VersionRef("model", "synthetic", "v1"),
        output_schema=VersionRef("schema", "triage-candidate", "v1"),
        configuration=VersionRef("triage_input_config", "synthetic", "v1"),
    )
    chosen = selected.model_copy(update={"versions": versions})
    topic_allocations = tuple(
        TopicAllocation(
            allocation_key=f"allocation-{index}",
            topic_ref=VersionRef("topic", f"topic-{index}", "v1"),
            assessment_ref=VersionRef(
                "topic-assessment",
                f"topic-{index}",
                f"{prompt_version}-{index}",
            ),
        )
        for index in range(allocations)
    )
    topics = tuple(
        TopicCandidate(
            allocation_key=item.allocation_key,
            title=f"Synthetic topic {index}",
            source_refs=(source.source,),
            priority=Priority.NORMAL,
            reason="Synthetic grounded triage reason",
            developments=(
                Development(
                    text="Synthetic approval is requested.",
                    evidence=(
                        TriageEvidence(
                            kind=EvidenceKind.SOURCE_STATEMENT,
                            source_ref=source.source,
                            statement="Synthetic approval is requested.",
                        ),
                    ),
                ),
            ),
        )
        for index, item in enumerate(topic_allocations)
    )
    candidate = TriageCandidate(topics=topics, dispositions=())
    plan = TriageReplayPlan(
        expected_targets=(source.source,),
        prepared_results=tuple(item.result_ref for item in chosen.prepared),
        filter_results=tuple(item.result_ref for item in chosen.filters),
        group_results=tuple(item.result_ref for item in chosen.groups),
        prior_triage_results=(),
        roles=chosen.roles,
        topic_allocations=topic_allocations,
        mode=TriageMode.LIVE,
    )
    schema = versions.output_schema
    model = versions.model
    producer = TriageProducerConfig(
        plan=plan,
        filter_config=chosen.filter_config,
        rule_config=chosen.rules.evaluation.config,
        input_config=input_config(max_part_bytes=4 * 1024 * 1024),
        versions=versions,
        working_context_config=WorkingContextConfig(
            selected_files=(),
            allowed_roots=("/tmp",),
            time_policy=CaptureTimePolicy(timezone="Australia/Sydney"),
            stale_policy=StalePolicy.CAPTURE,
            stale_after_seconds=3600.0,
            max_files=1,
            max_bytes_per_file=4096,
            max_total_bytes=4096,
            max_capture_seconds=5.0,
        ),
        capture_time=datetime(2026, 9, 29, 12, 0, tzinfo=ZoneInfo("Australia/Sydney")),
        prompt_text="Return only the declared synthetic triage candidate.",
        trusted_policy=TrustedPolicy(
            schemas={schema: {"type": "object"}},
            models={model: "synthetic-model"},
        ),
        attempt_limits=AttemptLimits(
            timeout_seconds=2.0,
            max_input_bytes=4 * 1024 * 1024,
            max_context_bytes=4096,
            max_prompt_bytes=4096,
            max_output_bytes=4 * 1024 * 1024,
            max_trace_events=8,
            max_trace_event_bytes=4096,
            max_turns=2,
            max_tokens=1024,
        ),
        expected_parameters=(("mode", "synthetic"),),
        claim_key=f"triage:source-1:{prompt_version}",
        configuration_version=f"producer-{prompt_version}",
        code_version="test-build",
        lease_seconds=60.0,
        operation_timeout_seconds=45.0,
        cleanup_margin_seconds=5.0,
        max_upstream_results=16,
        max_upstream_bytes=64 * 1024 * 1024,
        max_parts=4,
    )
    return chosen, producer, candidate


def handler(store, producer, candidate):
    """Return a handler and its deterministic fake runner."""
    runner = FakeRunner(store, [candidate] * producer.max_parts)
    return TriageHandler(store, producer, runner), runner
