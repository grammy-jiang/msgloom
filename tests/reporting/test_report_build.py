"""Selection, semantic coverage, codec, and rendering tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from msgloom.contracts import Limitation, ResultRef, StageResult, TerminalStatus
from msgloom.reporting import (
    AssessmentSelection,
    DueMode,
    PendingAssessmentWarning,
    PriorReportState,
    ReminderMode,
    RendererConfig,
    RepeatMode,
    ReportBuildError,
    ReportCodec,
    ReportSelectionError,
    SourceLink,
    render_report,
    select_topics,
    validate_semantic_coverage,
)
from msgloom.reporting.build import build_overview, build_topics
from msgloom.triage import Priority
from tests.reporting.helpers import plan, policy, ref, topic, triage_data


def _loaded(
    result_ref: ResultRef,
    data: object,
) -> tuple[tuple[ResultRef, StageResult, object], ...]:
    result = StageResult(
        result_id=result_ref.result_id,
        kind="triage",
        schema_version="1",
        execution=__import__(
            "msgloom.contracts", fromlist=["ExecutionIdentity"]
        ).ExecutionIdentity("e"),
        attempt=__import__(
            "msgloom.contracts", fromlist=["AttemptIdentity"]
        ).AttemptIdentity("a"),
        input_refs=(),
        source_versions=(),
        prepared_versions=(),
        topic_versions=(),
        configuration_version="c",
        code_version="c",
        status=TerminalStatus.COMPLETE,
        acceptable=True,
    )
    return ((result_ref, result, data),)


def test_policy_prior_state_repeat_and_reminder_are_assessment_scoped() -> None:
    """Prior reporting suppresses only the exact policy plus assessment pair."""
    item = topic()
    result_ref = ResultRef("r", "triage", "1")
    base = plan(result_ref)
    reported = PriorReportState(
        policy_ref=policy().policy_ref,
        assessment_ref=item.assessment_ref,
        report_ref=ref("report", "old"),
        reported_at=datetime(2026, 10, 1, 8, 30, tzinfo=UTC),
    )
    suppressed = base.model_copy(update={"prior_state": (reported,)})
    with pytest.raises(ReportSelectionError):
        select_topics(policy(), suppressed, _loaded(result_ref, triage_data(item)))  # type: ignore[arg-type]

    reminder_policy = policy().model_copy(
        update={
            "reminder_mode": ReminderMode.AFTER_INTERVAL,
            "reminder_after_seconds": 60,
        }
    )
    selected = select_topics(
        reminder_policy,
        suppressed,
        _loaded(result_ref, triage_data(item)),  # type: ignore[arg-type]
    )
    if selected != (item,):
        pytest.fail("explicit reminder policy did not reselect the assessment")

    repeat_policy = policy().model_copy(
        update={
            "repeat_mode": RepeatMode.AFTER_INTERVAL,
            "repeat_after_seconds": 60,
        }
    )
    selected = select_topics(
        repeat_policy,
        suppressed,
        _loaded(result_ref, triage_data(item)),  # type: ignore[arg-type]
    )
    if selected != (item,):
        pytest.fail("explicit repeat policy did not reselect the assessment")


def test_conflicting_versions_require_explicit_trusted_choice() -> None:
    """Out-of-order assessments never select a version by tuple ordering."""
    old = topic(assessment="assessment-old")
    new = topic(assessment="assessment-new").model_copy(
        update={"topic_ref": ref("topic", "topic-a", "2")}
    )
    r1 = ResultRef("old-result", "triage", "1")
    r2 = ResultRef("new-result", "triage", "1")
    selection = plan(r1, r2)
    loaded = (
        _loaded(r2, triage_data(new))[0],
        _loaded(r1, triage_data(old))[0],
    )
    with pytest.raises(ReportSelectionError):
        select_topics(policy(), selection, loaded)  # type: ignore[arg-type]
    explicit = selection.model_copy(
        update={
            "assessment_selections": (
                AssessmentSelection(
                    topic_ref=old.topic_ref,
                    assessment_ref=new.assessment_ref,
                ),
            )
        }
    )
    if select_topics(policy(), explicit, loaded) != (new,):  # type: ignore[arg-type]
        pytest.fail("explicit assessment selection was not honored")


def test_pending_newer_warning_must_bind_selected_assessment() -> None:
    """Pending work cannot silently describe a different selected topic."""
    item = topic()
    result_ref = ResultRef("r", "triage", "1")
    warning = PendingAssessmentWarning(
        topic_ref=item.topic_ref,
        selected_assessment_ref=item.assessment_ref,
        pending_ref=ref("topic-assessment", "pending-newer"),
        detail="New source version is awaiting triage.",
    )
    selection = plan(result_ref).model_copy(update={"pending_warnings": (warning,)})
    selected = select_topics(
        policy(),
        selection,
        _loaded(result_ref, triage_data(item)),  # type: ignore[arg-type]
    )
    if selected != (item,):
        pytest.fail("valid pending-newer warning changed selected assessment")


def test_equal_count_wrong_identity_and_dropped_action_fail_coverage() -> None:
    """Coverage checks identities and essential fields rather than counts."""
    first = build_topics((topic("topic-a"),), plan(ResultRef("r", "triage", "1")))
    overview = build_overview(first)
    wrong = overview[0].model_copy(update={"topic_ref": ref("topic", "wrong")})
    with pytest.raises(ReportBuildError):
        validate_semantic_coverage(first, (wrong,))
    dropped = overview[0].model_copy(update={"actions": ()})
    with pytest.raises(ReportBuildError):
        validate_semantic_coverage(first, (dropped,))


def test_render_escapes_html_preserves_unicode_multiline_and_source_labels() -> None:
    """Source text remains data in HTML and exact content in plain text."""
    item = topic()
    link = SourceLink(
        source_ref=item.source_refs[0],
        url="https://example.invalid/message?id=1&view=full",
    )
    built = build_topics(
        (item,),
        plan(ResultRef("r", "triage", "1"), source_links=(link,)),
    )
    overview = build_overview(built)
    parts = render_report(
        ref("report", "report-a"),
        overview,
        built,
        (),
        RendererConfig(
            max_part_bytes=100_000,
            max_total_bytes=200_000,
            max_parts=4,
        ),
    )
    part = parts[0]
    if "<script>alert(1)</script>" in part.html:
        pytest.fail("active source HTML was not escaped")
    if "&lt;script&gt;alert(1)&lt;/script&gt;" not in part.html:
        pytest.fail("escaped source HTML is missing")
    for value in ("Unicode 雪", "second row | x", "source-statement"):
        if value not in part.plain_text:
            pytest.fail(f"rendered plain text lost required value: {value}")


def test_unsafe_source_link_and_oversized_complete_topic_fail_closed() -> None:
    """Unsafe links and topics that cannot fit are rejected, never trimmed."""
    item = topic()
    bad = SourceLink(source_ref=item.source_refs[0], url="javascript:alert(1)")
    with pytest.raises(ReportBuildError):
        build_topics(
            (item,),
            plan(ResultRef("r", "triage", "1"), source_links=(bad,)),
        )

    huge = item.model_copy(
        update={"reason": "x" * 7_900},
    )
    built = build_topics((huge,), plan(ResultRef("r", "triage", "1")))
    with pytest.raises(ReportBuildError):
        render_report(
            ref("report", "large"),
            build_overview(built),
            built,
            (),
            RendererConfig(
                max_part_bytes=1_024,
                max_total_bytes=2_048,
                max_parts=2,
            ),
        )


def test_report_codec_revalidates_nested_models_and_is_canonical() -> None:
    """Canonical codec rejects nested mutation and preserves finite report JSON."""
    item = topic()
    built = build_topics((item,), plan(ResultRef("r", "triage", "1")))
    overview = build_overview(built)
    parts = render_report(
        ref("report", "codec"),
        overview,
        built,
        (),
        RendererConfig(
            max_part_bytes=100_000,
            max_total_bytes=200_000,
            max_parts=2,
        ),
    )
    from msgloom.reporting.models import SavedReport

    saved = SavedReport(
        report_ref=ref("report", "codec"),
        policy_ref=policy().policy_ref,
        destination=policy().destination,
        due_at=policy().due_at,
        timezone=policy().timezone,
        source_triage_results=(ResultRef("r", "triage", "1"),),
        topics=built,
        overview=overview,
        pending_warnings=(),
        limitations=(Limitation(code="synthetic", detail="Visible limitation"),),
        renderer_version="test-renderer",
        parts=parts,
    )
    codec = ReportCodec()
    payload = codec.encode(saved)
    if codec.decode(payload) != saved:
        pytest.fail("report codec did not round-trip exact semantic content")
    malformed = saved.model_copy(
        update={"topics": (built[0].model_copy(update={"priority": "important"}),)}
    )
    with pytest.raises(TypeError, match="failed validation"):
        codec.encode(malformed)


def test_multipart_keeps_one_identity_and_exact_topic_mapping() -> None:
    """A bounded split retains every topic exactly once under one report."""
    first = topic("topic-a", source_identity="message-a")
    second = topic("topic-b", "assessment-b", source_identity="message-b")
    built = build_topics(
        (first, second),
        plan(ResultRef("r", "triage", "1")),
    )
    overview = build_overview(built)
    large = render_report(
        ref("report", "multipart"),
        overview,
        built,
        (),
        RendererConfig(
            max_part_bytes=100_000,
            max_total_bytes=300_000,
            max_parts=4,
        ),
    )
    full_size = len(large[0].plain_text.encode()) + len(large[0].html.encode())
    parts = render_report(
        ref("report", "multipart"),
        overview,
        built,
        (),
        RendererConfig(
            max_part_bytes=full_size - 1,
            max_total_bytes=300_000,
            max_parts=4,
        ),
    )
    if len(parts) != 2:
        pytest.fail("bounded report did not split deterministically by topic")
    mapped = tuple(ref for part in parts for ref in part.topic_refs)
    if mapped != (first.topic_ref, second.topic_ref):
        pytest.fail("multipart output lost or reordered a topic identity")


def test_priority_and_deadline_due_criteria_are_explicit() -> None:
    """Priority and deadline modes select only topics satisfying configured policy."""
    result_ref = ResultRef("due-result", "triage", "1")
    normal = topic(priority=Priority.NORMAL)
    with pytest.raises(ReportSelectionError):
        select_topics(
            policy(),
            plan(result_ref),
            _loaded(result_ref, triage_data(normal)),  # type: ignore[arg-type]
        )

    important = topic()
    future_deadline = important.deadlines[0].model_copy(
        update={"interpreted_at": datetime(2026, 10, 2, 17, 0, tzinfo=UTC)}
    )
    future = important.model_copy(update={"deadlines": (future_deadline,)})
    with pytest.raises(ReportSelectionError):
        select_topics(
            policy(due_mode=DueMode.DEADLINE_BY),
            plan(result_ref),
            _loaded(result_ref, triage_data(future)),  # type: ignore[arg-type]
        )
