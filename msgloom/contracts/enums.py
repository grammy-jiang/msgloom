"""Provider-neutral Phase 1 enum contracts."""

from enum import StrEnum


class PhaseCapability(StrEnum):
    """Capabilities admitted through the shared Application boundary."""

    PREPARE = "a2_prepare"
    TRIAGE = "a3_triage"
    REPORT_BUILD = "a5_report_build"
    REPORT_SUBMIT = "a5_report_submit"
    INVESTIGATE = "a4_investigate"
    PROPOSE_ACTION = "a6_propose_action"
    EXECUTE_ACTION = "a7_execute_action"


class TerminalStatus(StrEnum):
    """Saved terminal status for an operation or stage attempt."""

    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class ExternalEffectState(StrEnum):
    """Observable state of an operation that can affect an external system."""

    NONE = "none"
    NOT_STARTED = "not_started"
    PENDING = "pending"
    ACCEPTED = "accepted"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


class ClaimKind(StrEnum):
    """Durable Phase 1 work scopes that exclude duplicate execution."""

    PREPARE = "prepare"
    TRIAGE = "triage"
    REPORT_BUILD = "report_build"
    REPORT_SUBMIT = "report_submit"
