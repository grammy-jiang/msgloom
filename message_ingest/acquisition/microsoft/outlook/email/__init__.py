"""Outlook Mail acquisition policies."""

from .planner import pending_full_v1_message_ids
from .profile import (
    FULL_V1,
    TERMINAL_SURFACE_STATUSES,
    attachment_required_surfaces,
    attachment_type_name,
    surface_is_complete,
)
from .rule_evaluation import (
    MailRuleDecisionOutcome,
    MailRuleEvaluation,
    MailRuleEvaluationState,
    MailRuleEvaluator,
    MailRuleObservation,
    MailRuleProbeData,
    MailRuleProbeStatus,
    MailRuleRequiredData,
    mail_rule_observation_from_item,
)
from .rule_probe import OutlookMailRuleProbeResult

__all__ = [
    "FULL_V1",
    "TERMINAL_SURFACE_STATUSES",
    "MailRuleDecisionOutcome",
    "MailRuleEvaluation",
    "MailRuleEvaluationState",
    "MailRuleEvaluator",
    "MailRuleObservation",
    "MailRuleProbeData",
    "MailRuleProbeStatus",
    "MailRuleRequiredData",
    "OutlookMailRuleProbeResult",
    "attachment_required_surfaces",
    "attachment_type_name",
    "mail_rule_observation_from_item",
    "pending_full_v1_message_ids",
    "surface_is_complete",
]
