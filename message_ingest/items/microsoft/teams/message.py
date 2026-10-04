"""Application Teams message items with durable acquisition provenance."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Self

from microsoft_graph.items.teams.message import (
    TeamsMessageItem as GraphTeamsMessageItem,
)
from microsoft_graph.protocol.teams import TeamsMessageIdentity


@dataclass(slots=True)
class TeamsMessageItem(GraphTeamsMessageItem):
    """One pre-parsed provider message linked to one raw HTTP capture."""

    source_id: str
    observed_at: str
    evidence_id: str | None
    run_id: str


@dataclass(frozen=True, slots=True)
class TeamsMessageTrigger:
    """
    Pickle-safe reference to the exact message observation that caused a fetch.

    Callbacks may carry this value in cb_kwargs. Before persistence,
    TeamsPipeline resolves its provisional evidence ID and time through the
    crawler evidence alias map, so a cache-canonicalized capture still
    identifies the same committed message observation.
    """

    source_id: str
    identity: TeamsMessageIdentity
    observed_at: str
    evidence_id: str

    @classmethod
    def from_message(cls, item: TeamsMessageItem) -> Self:
        """Build a trigger from a message item before follow-up scheduling."""
        if not isinstance(item.evidence_id, str) or not item.evidence_id:
            raise ValueError("Teams message trigger requires evidence_id")
        return cls(
            source_id=item.source_id,
            identity=item.identity,
            observed_at=item.observed_at,
            evidence_id=item.evidence_id,
        )


DeletionKind = Literal["direct", "notification"]
ReadbackState = Literal["not-attempted", "failed", "succeeded"]


@dataclass(slots=True)
class TeamsMessageDeletionItem:
    """Explicit provider deletion fact; ordinary list absence emits no item."""

    source_id: str
    identity: TeamsMessageIdentity
    deletion_kind: DeletionKind
    declared_deleted_at: Any
    observed_at: str
    evidence_id: str | None
    run_id: str
    readback_state: ReadbackState
    readback_evidence_id: str | None = None
    readback_observed_at: str | None = None

    def __post_init__(self) -> None:
        """Validate only application semantics, never provider ID syntax."""
        if self.deletion_kind not in {"direct", "notification"}:
            raise ValueError("Unknown Teams deletion kind")
        if self.readback_state not in {"not-attempted", "failed", "succeeded"}:
            raise ValueError("Unknown Teams deletion readback state")
        supplied = (
            self.readback_evidence_id is not None,
            self.readback_observed_at is not None,
        )
        if supplied[0] != supplied[1]:
            raise ValueError(
                "Teams deletion readback evidence and observation time "
                "must be supplied together"
            )


__all__ = [
    "DeletionKind",
    "ReadbackState",
    "TeamsMessageDeletionItem",
    "TeamsMessageItem",
    "TeamsMessageTrigger",
]
