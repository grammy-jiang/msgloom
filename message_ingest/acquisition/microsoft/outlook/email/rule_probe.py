"""Internal Outlook Mail acquisition-rule probe result contract."""

from __future__ import annotations

from dataclasses import dataclass

from .rule_evaluation import MailRuleObservation, MailRuleProbeData


@dataclass(frozen=True, slots=True)
class OutlookMailRuleProbeResult:
    """Internal Spider output consumed by the Mail rule middleware."""

    observation: MailRuleObservation
    probe: MailRuleProbeData


__all__ = ["OutlookMailRuleProbeResult"]
