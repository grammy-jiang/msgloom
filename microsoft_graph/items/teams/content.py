"""Teams embedded attachment and hosted-content provider projections."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Self

from microsoft_graph.protocol import GraphObjectTypeError, graph_object
from microsoft_graph.protocol.teams import (
    TeamsAttachmentKind,
    TeamsMessageIdentity,
    classify_teams_attachment,
)


def _embedded_objects(value: Any, *, context: str) -> tuple[dict[str, Any], ...]:
    """Validate a present embedded collection without changing its objects."""
    if value is None:
        return ()
    if not isinstance(value, list):
        raise GraphObjectTypeError(f"{context} must be a JSON array")
    return tuple(graph_object(entry, context=f"{context} entry") for entry in value)


@dataclass(slots=True)
class TeamsMessageAttachmentItem:
    """
    Preserve one embedded chatMessageAttachment under a scoped message.

    contentUrl and thumbnailUrl remain provider references only. This model
    exposes no fetch operation and does not reuse Outlook attachment endpoints.
    """

    message_identity: TeamsMessageIdentity
    raw: dict[str, Any]
    attachment_id: Any = field(init=False)
    content_type: Any = field(init=False)
    content_url: Any = field(init=False)
    content: Any = field(init=False)
    name: Any = field(init=False)
    thumbnail_url: Any = field(init=False)
    teams_app_id: Any = field(init=False)
    kind: TeamsAttachmentKind = field(init=False)

    def __post_init__(self) -> None:
        """Project known metadata while retaining falsey and unknown values."""
        self.attachment_id = self.raw.get("id")
        self.content_type = self.raw.get("contentType")
        self.content_url = self.raw.get("contentUrl")
        self.content = self.raw.get("content")
        self.name = self.raw.get("name")
        self.thumbnail_url = self.raw.get("thumbnailUrl")
        self.teams_app_id = self.raw.get("teamsAppId")
        self.kind = classify_teams_attachment(self.content_type)

    @classmethod
    def from_graph(
        cls,
        resource: Any,
        *,
        message_identity: TeamsMessageIdentity,
        **kwargs: Any,
    ) -> Self:
        """Map embedded attachment JSON without inventing resolution state."""
        raw = graph_object(resource, context="Teams message attachment")
        return cls(message_identity=message_identity, raw=raw, **kwargs)


@dataclass(slots=True)
class TeamsHostedContentItem:
    """
    Preserve chatMessageHostedContent metadata under one message observation.

    The provider API addresses hosted content by current message and content
    IDs, not by a historical message etag. This item therefore carries no
    message-version claim. contentBytes is retained only when Graph supplied it
    in the JSON representation; binary retrieval remains a separate response.
    """

    message_identity: TeamsMessageIdentity
    hosted_content_id: str
    raw: dict[str, Any]
    content_type: Any = field(init=False)
    content_bytes: Any = field(init=False)

    def __post_init__(self) -> None:
        """Project metadata without interpreting encoding or byte ownership."""
        self.content_type = self.raw.get("contentType")
        self.content_bytes = self.raw.get("contentBytes")

    @classmethod
    def from_graph(
        cls,
        resource: Any,
        *,
        message_identity: TeamsMessageIdentity,
        **kwargs: Any,
    ) -> Self:
        """Map hosted metadata and require only its opaque provider ID."""
        raw = graph_object(resource, context="Teams hosted content")
        hosted_content_id = raw.get("id")
        if not isinstance(hosted_content_id, str) or not hosted_content_id:
            raise ValueError("Teams hosted content requires a non-empty id")
        return cls(
            message_identity=message_identity,
            hosted_content_id=hosted_content_id,
            raw=raw,
            **kwargs,
        )


def parse_message_attachments(
    value: Any,
    *,
    message_identity: TeamsMessageIdentity,
) -> tuple[TeamsMessageAttachmentItem, ...]:
    """Parse an embedded attachment list while preserving each raw object."""
    return tuple(
        TeamsMessageAttachmentItem.from_graph(
            raw,
            message_identity=message_identity,
        )
        for raw in _embedded_objects(value, context="Teams message attachments")
    )


def parse_hosted_contents(
    value: Any,
    *,
    message_identity: TeamsMessageIdentity,
) -> tuple[TeamsHostedContentItem, ...]:
    """Parse hosted-content metadata returned by a Graph collection."""
    return tuple(
        TeamsHostedContentItem.from_graph(
            raw,
            message_identity=message_identity,
        )
        for raw in _embedded_objects(value, context="Teams hosted contents")
    )


__all__ = [
    "TeamsHostedContentItem",
    "TeamsMessageAttachmentItem",
    "parse_hosted_contents",
    "parse_message_attachments",
]
