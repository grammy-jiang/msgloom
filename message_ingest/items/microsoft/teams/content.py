"""Teams content retrieval and reference-resolution application items."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Literal, Self

from microsoft_graph.items.teams.content import (
    TeamsHostedContentItem as GraphTeamsHostedContentItem,
)
from microsoft_graph.protocol.teams import TeamsMessageIdentity

from .message import TeamsMessageTrigger

ResolutionState = Literal[
    "not-attempted",
    "resolved",
    "denied",
    "missing",
    "stale",
]


@dataclass(slots=True)
class TeamsReferenceResolutionItem:
    """One explicit attachment/reference resolution fact."""

    source_id: str
    trigger: TeamsMessageTrigger
    attachment_ordinal: int
    state: ResolutionState
    observed_at: str
    evidence_id: str | None
    run_id: str
    details: dict[str, Any]

    def __post_init__(self) -> None:
        """Validate bounded state and ordinal without interpreting URLs."""
        if self.state not in {
            "not-attempted",
            "resolved",
            "denied",
            "missing",
            "stale",
        }:
            raise ValueError("Unknown Teams reference resolution state")
        if self.attachment_ordinal < 0:
            raise ValueError("Teams attachment ordinal cannot be negative")


@dataclass(slots=True)
class TeamsHostedContentItem(GraphTeamsHostedContentItem):
    """Provider hosted-content metadata linked to its triggering observation."""

    source_id: str
    trigger: TeamsMessageTrigger
    observed_at: str
    evidence_id: str | None
    run_id: str


@dataclass(slots=True)
class TeamsHostedContentBytesItem:
    """One hosted-content byte response represented by digest metadata."""

    source_id: str
    message_identity: TeamsMessageIdentity
    hosted_content_id: str
    trigger: TeamsMessageTrigger
    content_sha256: str
    content_bytes: int
    content_type: str | None
    observed_at: str
    evidence_id: str | None
    run_id: str

    @classmethod
    def from_bytes(
        cls,
        *,
        body: bytes,
        **kwargs: Any,
    ) -> Self:
        """Project response bytes to digest metadata; raw bytes stay in evidence."""
        return cls(
            content_sha256=hashlib.sha256(body).hexdigest(),
            content_bytes=len(body),
            **kwargs,
        )


@dataclass(slots=True)
class TeamsHostedContentFailureItem:
    """Explicit hosted retrieval failure or provider limitation."""

    source_id: str
    message_identity: TeamsMessageIdentity
    hosted_content_id: str
    trigger: TeamsMessageTrigger
    failure_kind: str
    observed_at: str
    evidence_id: str | None
    run_id: str
    status_code: int | None
    details: dict[str, Any]


__all__ = [
    "ResolutionState",
    "TeamsHostedContentBytesItem",
    "TeamsHostedContentFailureItem",
    "TeamsHostedContentItem",
    "TeamsReferenceResolutionItem",
]
