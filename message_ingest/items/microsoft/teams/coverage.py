"""Evidence-backed Teams visibility, retention, subscription, and gap facts."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class TeamsCoverageItem:
    """One additive coverage fact for a concrete visible provider scope."""

    source_id: str
    scope_kind: str
    scope: tuple[str, ...]
    fact_kind: str
    status: str
    history_incomplete: bool
    observed_at: str
    evidence_id: str | None
    run_id: str
    visible_scope: dict[str, Any] | None = None
    retention_limitations: list[str] = field(default_factory=list)
    subscription_id: str | None = None
    subscription_valid_from: str | None = None
    subscription_valid_until: str | None = None
    gap_kind: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Require explicit scope labels without inferring completeness."""
        if not self.scope_kind:
            raise ValueError("Teams coverage requires scope_kind")
        if not self.scope or any(not value for value in self.scope):
            raise ValueError("Teams coverage requires a non-empty opaque scope")
        if not self.fact_kind or not self.status:
            raise ValueError("Teams coverage requires fact_kind and status")


__all__ = ["TeamsCoverageItem"]
