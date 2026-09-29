"""Deterministic finite selection of accepted saved triage assessments."""

from __future__ import annotations

from datetime import UTC, timedelta

from msgloom.contracts import ResultRef, StageResult, TerminalStatus
from msgloom.triage import TopicAssessment, TriageData

from .models import DueMode, ReminderMode, RepeatMode, ReportPolicy, ReportSelectionPlan


class ReportSelectionError(ValueError):
    """Classify fail-closed report selection without source data leakage."""


def select_topics(
    policy: ReportPolicy,
    plan: ReportSelectionPlan,
    loaded: tuple[tuple[ResultRef, StageResult, TriageData], ...],
) -> tuple[TopicAssessment, ...]:
    """Freeze exact accepted assessments selected by one trusted policy."""
    expected = set(plan.triage_results)
    if {item[0] for item in loaded} != expected or len(loaded) != len(expected):
        raise ReportSelectionError("loaded triage inputs do not match selection plan")
    candidates: dict[tuple[str, str], list[TopicAssessment]] = {}
    for ref, result, data in loaded:
        if (
            result.result_id != ref.result_id
            or result.kind != "triage"
            or result.schema_version != "1"
            or not result.acceptable
            or result.status not in {TerminalStatus.COMPLETE, TerminalStatus.INCOMPLETE}
        ):
            raise ReportSelectionError(
                "selected input is not an accepted triage result"
            )
        for topic in data.topics:
            key = (topic.topic_ref.kind, topic.topic_ref.identity)
            candidates.setdefault(key, []).append(topic)

    choices = {
        (item.topic_ref.kind, item.topic_ref.identity): item.assessment_ref
        for item in plan.assessment_selections
    }
    for key, wanted in choices.items():
        if key not in candidates or not any(
            item.assessment_ref == wanted for item in candidates[key]
        ):
            raise ReportSelectionError("assessment selection does not match input")
    selected: list[TopicAssessment] = []
    for topic_key in sorted(candidates):
        versions = candidates[topic_key]
        if len(versions) == 1:
            chosen = versions[0]
        else:
            wanted = choices.get(topic_key)
            matches = [item for item in versions if item.assessment_ref == wanted]
            if len(matches) != 1:
                raise ReportSelectionError(
                    "conflicting topic assessments require one explicit selection"
                )
            chosen = matches[0]
        if _is_due(policy, plan, chosen):
            selected.append(chosen)

    if not selected:
        raise ReportSelectionError("selection contains no due topic assessments")
    selected_refs = {(x.topic_ref, x.assessment_ref) for x in selected}
    for warning in plan.pending_warnings:
        if (warning.topic_ref, warning.selected_assessment_ref) not in selected_refs:
            raise ReportSelectionError(
                "pending warning does not bind a selected assessment"
            )
        if warning.pending_ref == warning.selected_assessment_ref:
            raise ReportSelectionError(
                "pending warning must reference newer distinct work"
            )
    return tuple(selected)


def _is_due(
    policy: ReportPolicy,
    plan: ReportSelectionPlan,
    topic: TopicAssessment,
) -> bool:
    if topic.priority not in policy.priorities:
        return False
    if policy.due_mode is DueMode.DEADLINE_BY:
        interpreted = tuple(
            item.interpreted_at
            for item in topic.deadlines
            if item.interpreted_at is not None
        )
        if not interpreted or min(interpreted) > policy.due_at:
            return False
    states = [
        item
        for item in plan.prior_state
        if item.policy_ref == policy.policy_ref
        and item.assessment_ref == topic.assessment_ref
    ]
    if not states:
        return True
    latest = max(item.reported_at for item in states)
    if policy.reminder_mode is ReminderMode.AFTER_INTERVAL:
        interval = policy.reminder_after_seconds
        if interval is not None and latest.astimezone(UTC) + timedelta(
            seconds=interval
        ) <= policy.due_at.astimezone(UTC):
            return True
    if policy.repeat_mode is RepeatMode.AFTER_INTERVAL:
        interval = policy.repeat_after_seconds
        if interval is not None and latest.astimezone(UTC) + timedelta(
            seconds=interval
        ) <= policy.due_at.astimezone(UTC):
            return True
    return False
