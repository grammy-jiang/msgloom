"""Synthetic report fixtures with no provider or private data."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from msgloom.contracts import (
    AttemptIdentity,
    ExecutionIdentity,
    ResultRef,
    ResultSchemaRegistry,
    StageResult,
    TerminalStatus,
    VersionRef,
)
from msgloom.persistence import Phase1Persistence, SemanticDataRegistry
from msgloom.reporting import (
    DueMode,
    ReminderMode,
    RepeatMode,
    ReportDestination,
    ReportPolicy,
    ReportSelectionPlan,
    SourceLink,
)
from msgloom.triage import (
    ActionOwner,
    Deadline,
    Development,
    EvidenceKind,
    OwnerState,
    Priority,
    Risk,
    TopicAssessment,
    TriageAction,
    TriageData,
    TriageEvidence,
)


def ref(kind: str, identity: str, version: str = "1") -> VersionRef:
    """Build an exact synthetic version reference."""
    return VersionRef(kind=kind, identity=identity, version=version)


def evidence(
    source: VersionRef, text: str = "Synthetic <b>evidence</b>"
) -> TriageEvidence:
    """Build labelled synthetic source evidence."""
    return TriageEvidence(
        kind=EvidenceKind.SOURCE_STATEMENT,
        source_ref=source,
        statement=text,
    )


def topic(
    identity: str = "topic-a",
    assessment: str = "assessment-a",
    *,
    source_identity: str = "message-a",
    priority: Priority = Priority.IMPORTANT,
    title: str = "Synthetic <script>alert(1)</script> topic",
) -> TopicAssessment:
    """Build a complete synthetic topic with all essential report fields."""
    source = ref("source-message", source_identity)
    item = evidence(source)
    return TopicAssessment(
        topic_ref=ref("topic", identity),
        assessment_ref=ref("topic-assessment", assessment),
        title=title,
        source_refs=(source,),
        priority=priority,
        reason="Priority reason with Unicode 雪",
        developments=(
            Development(text="Development line\nsecond row | x", evidence=(item,)),
        ),
        actions=(
            TriageAction(
                text="Review synthetic request",
                owner=ActionOwner(state=OwnerState.UNKNOWN),
                evidence=(item,),
            ),
        ),
        deadlines=(
            Deadline(
                original_wording="by Friday EOD",
                interpreted_at=datetime(2026, 9, 30, 17, 0, tzinfo=UTC),
                timezone_basis="UTC",
                ambiguous=True,
                evidence=(item,),
            ),
        ),
        risks=(Risk(text="Synthetic delivery risk", evidence=(item,)),),
        limitations=(),
    )


def triage_data(*topics: TopicAssessment) -> TriageData:
    """Build canonical triage semantic data."""
    return TriageData(topics=topics, dispositions=())


def policy(*, due_mode: DueMode = DueMode.ALL_MATCHING) -> ReportPolicy:
    """Build explicit owner-only synthetic report policy."""
    return ReportPolicy(
        policy_ref=ref("report-policy", "owner-daily", "7"),
        destination=ReportDestination(
            owner_identity="owner-synthetic",
            destination_identity="owner@example.invalid",
        ),
        due_at=datetime(2026, 10, 1, 9, 0, tzinfo=UTC),
        timezone="UTC",
        priorities=(Priority.CRITICAL, Priority.IMPORTANT),
        due_mode=due_mode,
        repeat_mode=RepeatMode.NEVER,
        repeat_after_seconds=None,
        reminder_mode=ReminderMode.DISABLED,
        reminder_after_seconds=None,
    )


def plan(
    *result_refs: ResultRef, source_links: tuple[SourceLink, ...] = ()
) -> ReportSelectionPlan:
    """Build a finite plan bound to exact request and triage references."""
    return ReportSelectionPlan(
        request_targets=(ref("report-target", "owner-daily"),),
        triage_results=result_refs,
        assessment_selections=(),
        prior_state=(),
        pending_warnings=(),
        source_links=source_links,
    )


def semantic_registry() -> SemanticDataRegistry:
    """Use the default report composition in production and restart tests."""
    return SemanticDataRegistry.phase1()


async def open_store(path: Path) -> Phase1Persistence:
    """Open real Phase 1 persistence with the lane-local report codec."""
    return await Phase1Persistence.open(
        f"sqlite+pysqlite:///{path}",
        registry=ResultSchemaRegistry.phase1().with_schema(
            "report_selection", "1", semantic_data_required=True
        ),
        semantic_registry=semantic_registry(),
    )


async def save_triage(
    store: Phase1Persistence,
    data: TriageData,
    *,
    result_id: str = "triage-result",
    acceptable: bool = True,
) -> ResultRef:
    """Persist one accepted synthetic triage@1 result and semantic payload."""
    data_ref = store.semantic_reference(f"data-{result_id}", "triage", "1", data)
    result = StageResult(
        result_id=result_id,
        kind="triage",
        schema_version="1",
        execution=ExecutionIdentity(f"execution-{result_id}"),
        attempt=AttemptIdentity(f"attempt-{result_id}"),
        input_refs=(),
        source_versions=tuple(
            source for item in data.topics for source in item.source_refs
        ),
        prepared_versions=(),
        topic_versions=tuple(item.assessment_ref for item in data.topics),
        configuration_version="triage-config-1",
        code_version="synthetic",
        status=TerminalStatus.COMPLETE,
        acceptable=acceptable,
        semantic_data_ref=data_ref,
    )
    await store.append_result_with_data(result, data)
    return ResultRef(result_id, "triage", "1")
