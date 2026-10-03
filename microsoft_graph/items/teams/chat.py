"""Pure Microsoft Teams chat, member, and pin provider projections."""

from dataclasses import dataclass, field
from typing import Any, Self

from microsoft_graph.protocol import graph_object


def _resource(
    resource: dict[str, Any],
    context: str,
    **parents: str,
) -> dict[str, Any]:
    """Validate only opaque resource and parent identities."""
    raw = graph_object(resource, context=context)
    identities = {"id": raw.get("id"), **parents}
    for name, value in identities.items():
        if not isinstance(value, str) or not value:
            raise ValueError(f"{context} requires a non-empty {name}")
    return raw


@dataclass(slots=True)
class TeamsChatItem:
    """Chat identity and provider fields without application provenance."""

    chat_id: str
    raw: dict[str, Any]
    topic: str | None = field(init=False)
    created_date_time: str | None = field(init=False)
    last_updated_date_time: str | None = field(init=False)
    chat_type: str | None = field(init=False)
    web_url: str | None = field(init=False)
    tenant_id: str | None = field(init=False)
    online_meeting_info: dict[str, Any] | None = field(init=False)
    viewpoint: dict[str, Any] | None = field(init=False)
    is_hidden_for_all_members: bool | None = field(init=False)

    def __post_init__(self) -> None:
        """Project known fields without normalizing falsey or nested values."""
        self.topic = self.raw.get("topic")
        self.created_date_time = self.raw.get("createdDateTime")
        self.last_updated_date_time = self.raw.get("lastUpdatedDateTime")
        self.chat_type = self.raw.get("chatType")
        self.web_url = self.raw.get("webUrl")
        self.tenant_id = self.raw.get("tenantId")
        self.online_meeting_info = self.raw.get("onlineMeetingInfo")
        self.viewpoint = self.raw.get("viewpoint")
        self.is_hidden_for_all_members = self.raw.get("isHiddenForAllMembers")

    @classmethod
    def from_graph(cls, resource: dict[str, Any], **kwargs: Any) -> Self:
        """Map a chat while retaining its original provider dictionary."""
        raw = _resource(resource, "Teams chat")
        return cls(chat_id=raw["id"], raw=raw, **kwargs)


@dataclass(slots=True)
class TeamsChatMemberItem:
    """Explicit member relation with chat-scoped opaque membership identity."""

    chat_id: str
    member_id: str
    raw: dict[str, Any]
    odata_type: str | None = field(init=False)
    display_name: str | None = field(init=False)
    roles: list[str] | None = field(init=False)
    visible_history_start_date_time: str | None = field(init=False)
    email: str | None = field(init=False)
    tenant_id: str | None = field(init=False)
    user_id: str | None = field(init=False)

    def __post_init__(self) -> None:
        """Retain federation/member fields and all unknown values in raw."""
        self.odata_type = self.raw.get("@odata.type")
        self.display_name = self.raw.get("displayName")
        self.roles = self.raw.get("roles")
        self.visible_history_start_date_time = self.raw.get(
            "visibleHistoryStartDateTime"
        )
        self.email = self.raw.get("email")
        self.tenant_id = self.raw.get("tenantId")
        self.user_id = self.raw.get("userId")

    @classmethod
    def from_graph(
        cls,
        resource: dict[str, Any],
        *,
        chat_id: str,
        **kwargs: Any,
    ) -> Self:
        """Map a member without parsing membership or user IDs."""
        raw = _resource(resource, "Teams chat member", chat_id=chat_id)
        return cls(
            chat_id=chat_id,
            member_id=raw["id"],
            raw=raw,
            **kwargs,
        )


@dataclass(slots=True)
class TeamsChatPinItem:
    """Pin relation kept separate from any common chat-message projection."""

    chat_id: str
    message_id: str
    raw: dict[str, Any]
    message: dict[str, Any] | None = field(init=False)

    def __post_init__(self) -> None:
        """Preserve an optional expanded message as raw nested provider data."""
        self.message = self.raw.get("message")

    @classmethod
    def from_graph(
        cls,
        resource: dict[str, Any],
        *,
        chat_id: str,
        **kwargs: Any,
    ) -> Self:
        """Map a pin; Graph defines its resource ID as the chat-message ID."""
        raw = _resource(resource, "Teams chat pin", chat_id=chat_id)
        return cls(
            chat_id=chat_id,
            message_id=raw["id"],
            raw=raw,
            **kwargs,
        )


__all__ = ["TeamsChatItem", "TeamsChatMemberItem", "TeamsChatPinItem"]
