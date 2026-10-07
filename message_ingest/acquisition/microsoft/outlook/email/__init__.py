"""Outlook Mail acquisition policies."""

from .planner import pending_full_v1_message_ids
from .profile import (
    DISCOVERY_V1,
    FULL_V1,
    TERMINAL_SURFACE_STATUSES,
    attachment_required_surfaces,
    attachment_type_name,
    surface_is_complete,
)
from .rule_config import (
    MAIL_RULE_POLICY_FAMILY,
    MailRuleDefinition,
    MailRulePolicy,
    MailRulePredicates,
    MailRuleProfile,
    effective_mail_policy_digest,
    internal_mail_profile,
    mail_policy_inspection,
    parse_mail_rule_policy,
)
from .rule_engine import DeterministicMailRuleEvaluator
from .rule_evaluation import (
    MailRecipientFact,
    MailRuleDecisionOutcome,
    MailRuleEvaluation,
    MailRuleEvaluationState,
    MailRuleEvaluator,
    MailRuleFact,
    MailRuleFacts,
    MailRuleObservation,
    MailRuleProbeData,
    MailRuleProbeFailure,
    MailRuleProbeStatus,
    MailRuleRequiredData,
    mail_rule_observation_from_item,
)
from .rule_probe import OutlookMailRuleProbeResult

__all__ = [
    "DISCOVERY_V1",
    "FULL_V1",
    "MAIL_RULE_POLICY_FAMILY",
    "TERMINAL_SURFACE_STATUSES",
    "DeterministicMailRuleEvaluator",
    "MailRecipientFact",
    "MailRuleDecisionOutcome",
    "MailRuleDefinition",
    "MailRuleEvaluation",
    "MailRuleEvaluationState",
    "MailRuleEvaluator",
    "MailRuleFact",
    "MailRuleFacts",
    "MailRuleObservation",
    "MailRulePolicy",
    "MailRulePredicates",
    "MailRuleProbeData",
    "MailRuleProbeFailure",
    "MailRuleProbeStatus",
    "MailRuleProfile",
    "MailRuleRequiredData",
    "OutlookMailRuleProbeResult",
    "attachment_required_surfaces",
    "attachment_type_name",
    "effective_mail_policy_digest",
    "internal_mail_profile",
    "mail_policy_inspection",
    "mail_rule_observation_from_item",
    "parse_mail_rule_policy",
    "pending_full_v1_message_ids",
    "surface_is_complete",
]
