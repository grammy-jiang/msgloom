"""Validate trusted basic Microsoft Teams change-notification envelopes."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal
from urllib.parse import unquote

from microsoft_graph.protocol.notifications import (
    GraphNotificationAuthenticationError,
    GraphNotificationError,
    notifications_from_payload,
)
from microsoft_graph.protocol.teams import TeamsMessageIdentity

TeamsNotificationScopeKind = Literal["chat-messages", "channel-messages"]

_ENVELOPE_FORBIDDEN_KEYS = frozenset(
    {"encryptedContent", "resourceData", "validationToken", "validationTokens"}
)
_ENTRY_FORBIDDEN_KEYS = frozenset(
    {"encryptedContent", "validationToken", "validationTokens"}
)
_BASIC_RESOURCE_DATA_KEYS = frozenset({"id", "@odata.type", "@odata.id"})
_CHAT_MESSAGE_ODATA_TYPE = "#Microsoft.Graph.chatMessage"


class TeamsNotificationError(ValueError):
    """Report an invalid Teams notification without provider identifier values."""


class TeamsNotificationAuthenticationError(TeamsNotificationError):
    """Report failed Teams clientState authentication."""


def _utc(value: object, *, name: str) -> datetime:
    """Parse one trusted UTC timestamp without returning it in an error."""
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a valid UTC timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ValueError(f"{name} must be UTC")
    return parsed


def _opaque(value: object, *, name: str) -> str:
    """Require one non-empty trusted opaque string without exposing its value."""
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")
    return value


@dataclass(frozen=True, slots=True)
class TeamsTrustedSubscription:
    """Caller-trusted tenant, scope, secret, and validity binding."""

    subscription_id: str
    tenant_id: str
    scope_kind: TeamsNotificationScopeKind
    client_state: str = field(repr=False)
    valid_from: str
    valid_until: str
    chat_id: str | None = None
    host_team_id: str | None = None
    channel_id: str | None = None

    def __post_init__(self) -> None:
        """Require exactly one trusted chat or channel scope and valid window."""
        _opaque(self.subscription_id, name="subscription_id")
        _opaque(self.tenant_id, name="tenant_id")
        _opaque(self.client_state, name="client_state")
        start = _utc(self.valid_from, name="valid_from")
        end = _utc(self.valid_until, name="valid_until")
        if start >= end:
            raise ValueError("trusted subscription validity window must increase")

        if self.scope_kind == "chat-messages":
            _opaque(self.chat_id, name="chat_id")
            if self.host_team_id is not None or self.channel_id is not None:
                raise ValueError("chat subscription cannot contain channel scope")
            return
        if self.scope_kind != "channel-messages":
            raise ValueError("unsupported trusted Teams notification scope")
        _opaque(self.host_team_id, name="host_team_id")
        _opaque(self.channel_id, name="channel_id")
        if self.chat_id is not None:
            raise ValueError("channel subscription cannot contain chat scope")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> TeamsTrustedSubscription:
        """Construct one trusted record from caller-controlled configuration."""
        scope_kind = value.get("scope_kind")
        if scope_kind not in ("chat-messages", "channel-messages"):
            raise ValueError("unsupported trusted Teams notification scope")
        return cls(
            subscription_id=_opaque(
                value.get("subscription_id"), name="subscription_id"
            ),
            tenant_id=_opaque(value.get("tenant_id"), name="tenant_id"),
            scope_kind=scope_kind,
            client_state=_opaque(value.get("client_state"), name="client_state"),
            valid_from=_opaque(value.get("valid_from"), name="valid_from"),
            valid_until=_opaque(value.get("valid_until"), name="valid_until"),
            chat_id=value.get("chat_id"),
            host_team_id=value.get("host_team_id"),
            channel_id=value.get("channel_id"),
        )

    @property
    def scope(self) -> tuple[str, ...]:
        """Return the trusted resource scope independent of envelope bytes."""
        if self.scope_kind == "chat-messages":
            return (self.chat_id or "",)
        return (self.host_team_id or "", self.channel_id or "")

    @property
    def base_resource(self) -> str:
        """Return the trusted subscription resource without a message target."""
        if self.scope_kind == "chat-messages":
            return f"/chats/{self.chat_id}/messages"
        return f"/teams/{self.host_team_id}/channels/{self.channel_id}/messages"


@dataclass(frozen=True, slots=True)
class TeamsNotificationEvent:
    """One authenticated event bound to caller-trusted scope and validity."""

    ordinal: int
    subscription_id: str
    tenant_id: str
    scope_kind: TeamsNotificationScopeKind
    scope: tuple[str, ...]
    valid_from: str
    valid_until: str
    change_type: str | None
    lifecycle_event: str | None
    identity: TeamsMessageIdentity | None


def _odata_key(segment: str, *, collection: str) -> str:
    """Decode one documented OData string-key segment without interpreting the ID."""
    prefix = f"{collection}('"
    if not segment.startswith(prefix) or not segment.endswith("')"):
        raise TeamsNotificationError("Teams notification resource is malformed")
    value = segment[len(prefix) : -2]
    if not value:
        raise TeamsNotificationError("Teams notification resource is malformed")
    return value.replace("''", "'")


def _odata_resource_segments(parts: tuple[str, ...]) -> tuple[str, ...]:
    """Normalize documented Teams OData key paths to ordinary opaque segments."""
    first = parts[0]
    if first.startswith("chats("):
        chat_id = _odata_key(first, collection="chats")
        if len(parts) != 2:
            raise TeamsNotificationError("Teams notification resource is malformed")
        if parts[1] == "messages":
            return ("chats", chat_id, "messages")
        message_id = _odata_key(parts[1], collection="messages")
        return ("chats", chat_id, "messages", message_id)

    if not first.startswith("teams("):
        raise TeamsNotificationError("Teams notification resource is malformed")
    if len(parts) not in {3, 4}:
        raise TeamsNotificationError("Teams notification resource is malformed")
    team_id = _odata_key(first, collection="teams")
    channel_id = _odata_key(parts[1], collection="channels")
    if parts[2] == "messages":
        if len(parts) != 3:
            raise TeamsNotificationError("Teams notification resource is malformed")
        return ("teams", team_id, "channels", channel_id, "messages")

    root_id = _odata_key(parts[2], collection="messages")
    if len(parts) == 3:
        return (
            "teams",
            team_id,
            "channels",
            channel_id,
            "messages",
            root_id,
        )
    reply_id = _odata_key(parts[3], collection="replies")
    return (
        "teams",
        team_id,
        "channels",
        channel_id,
        "messages",
        root_id,
        "replies",
        reply_id,
    )


def _resource_segments(resource: str) -> tuple[str, ...]:
    """Decode one relative slash or documented OData-key Teams resource path."""
    if "://" in resource or "?" in resource or "#" in resource or "\\" in resource:
        raise TeamsNotificationError("Teams notification resource is not trusted")
    text = resource.removeprefix("/")
    if not text:
        raise TeamsNotificationError("Teams notification resource is empty")
    encoded = text.split("/")
    if any(not part for part in encoded):
        raise TeamsNotificationError("Teams notification resource is malformed")
    parts = tuple(unquote(part) for part in encoded)
    if parts[0].startswith(("chats(", "teams(")):
        return _odata_resource_segments(parts)
    return parts


def _identity_from_resource(
    resource: str,
    trusted: TeamsTrustedSubscription,
    *,
    lifecycle: bool,
) -> TeamsMessageIdentity | None:
    """Validate exact trusted scope and return a path-scoped message identity."""
    parts = _resource_segments(resource)
    if trusted.scope_kind == "chat-messages":
        expected = ("chats", trusted.chat_id or "", "messages")
        if lifecycle:
            if parts != expected:
                raise TeamsNotificationError("Teams lifecycle resource scope mismatch")
            return None
        if len(parts) != 4 or parts[:3] != expected or not parts[3]:
            raise TeamsNotificationError("Teams change resource scope mismatch")
        return TeamsMessageIdentity.chat(parts[3], chat_id=trusted.chat_id or "")

    expected = (
        "teams",
        trusted.host_team_id or "",
        "channels",
        trusted.channel_id or "",
        "messages",
    )
    if lifecycle:
        if parts != expected:
            raise TeamsNotificationError("Teams lifecycle resource scope mismatch")
        return None
    if len(parts) == 6 and parts[:5] == expected and parts[5]:
        return TeamsMessageIdentity.channel_root(
            parts[5],
            team_id=trusted.host_team_id or "",
            channel_id=trusted.channel_id or "",
        )
    if (
        len(parts) == 8
        and parts[:5] == expected
        and parts[5]
        and parts[6] == "replies"
        and parts[7]
    ):
        return TeamsMessageIdentity.channel_reply(
            parts[7],
            team_id=trusted.host_team_id or "",
            channel_id=trusted.channel_id or "",
            root_message_id=parts[5],
        )
    raise TeamsNotificationError("Teams change resource scope mismatch")


def _validate_basic_resource_data(
    item: Mapping[str, Any],
    *,
    trusted: TeamsTrustedSubscription,
    identity: TeamsMessageIdentity | None,
) -> None:
    """Accept only identity metadata that agrees with the authenticated target."""
    if "resourceData" not in item:
        return
    metadata = item.get("resourceData")
    if identity is None or not isinstance(metadata, Mapping):
        raise TeamsNotificationError(
            "Teams notification resourceData is not basic identity metadata"
        )
    if set(metadata) != _BASIC_RESOURCE_DATA_KEYS:
        raise TeamsNotificationError(
            "Teams notification resourceData contains unsupported fields"
        )
    metadata_id = metadata.get("id")
    metadata_type = metadata.get("@odata.type")
    metadata_resource = metadata.get("@odata.id")
    if (
        not isinstance(metadata_id, str)
        or not metadata_id
        or metadata_id != identity.message_id
    ):
        raise TeamsNotificationError("Teams notification resourceData ID mismatch")
    if metadata_type != _CHAT_MESSAGE_ODATA_TYPE:
        raise TeamsNotificationError("Teams notification resourceData type mismatch")
    if not isinstance(metadata_resource, str) or not metadata_resource:
        raise TeamsNotificationError(
            "Teams notification resourceData resource is invalid"
        )
    metadata_identity = _identity_from_resource(
        metadata_resource,
        trusted,
        lifecycle=False,
    )
    if metadata_identity != identity:
        raise TeamsNotificationError(
            "Teams notification resourceData resource mismatch"
        )


def _validate_capture(
    captured_at: str,
    trusted: TeamsTrustedSubscription,
) -> None:
    """Require the trusted capture to fall inside the recorded validity window."""
    try:
        captured = _utc(captured_at, name="captured_at")
        start = _utc(trusted.valid_from, name="valid_from")
        end = _utc(trusted.valid_until, name="valid_until")
    except ValueError as exc:
        raise TeamsNotificationError(
            "trusted subscription validity is invalid"
        ) from exc
    if captured < start or captured >= end:
        raise TeamsNotificationError("notification is outside trusted validity window")


def teams_notifications_from_payload(
    payload: Mapping[str, Any],
    *,
    trusted_subscriptions: Mapping[str, TeamsTrustedSubscription],
    captured_at: str,
) -> tuple[TeamsNotificationEvent, ...]:
    """Authenticate and scope every Teams event before returning any of them."""
    if not isinstance(payload, Mapping):
        raise TeamsNotificationError("Teams notification envelope must be an object")
    if _ENVELOPE_FORBIDDEN_KEYS.intersection(payload):
        raise TeamsNotificationError(
            "rich or validation-token envelopes are unsupported"
        )
    values = payload.get("value")
    if not isinstance(values, list):
        raise TeamsNotificationError("Teams notification envelope requires value list")

    events: list[TeamsNotificationEvent] = []
    for ordinal, item in enumerate(values):
        if not isinstance(item, Mapping):
            raise TeamsNotificationError("Teams notification entry must be an object")
        if _ENTRY_FORBIDDEN_KEYS.intersection(item):
            raise TeamsNotificationError("rich Teams notification entry is unsupported")
        subscription_id = item.get("subscriptionId")
        if not isinstance(subscription_id, str) or not subscription_id:
            raise TeamsNotificationError("Teams notification subscription is missing")
        trusted = trusted_subscriptions.get(subscription_id)
        if trusted is None:
            raise TeamsNotificationError("Teams notification subscription is unknown")
        tenant_id = item.get("tenantId")
        if not isinstance(tenant_id, str) or tenant_id != trusted.tenant_id:
            raise TeamsNotificationError("Teams notification tenant scope mismatch")
        _validate_capture(captured_at, trusted)

        try:
            graph_event = notifications_from_payload(
                {"value": [item]},
                expected_client_state=trusted.client_state,
                subscription_resources={subscription_id: trusted.base_resource},
            )[0]
        except GraphNotificationAuthenticationError as exc:
            raise TeamsNotificationAuthenticationError(
                "Teams notification clientState mismatch"
            ) from exc
        except GraphNotificationError as exc:
            raise TeamsNotificationError("invalid basic Graph notification") from exc

        if graph_event.lifecycle_event == "missed":
            raise TeamsNotificationError("unsupported Teams lifecycle event")
        lifecycle = graph_event.lifecycle_event is not None
        identity = _identity_from_resource(
            graph_event.resource,
            trusted,
            lifecycle=lifecycle,
        )
        _validate_basic_resource_data(
            item,
            trusted=trusted,
            identity=identity,
        )
        events.append(
            TeamsNotificationEvent(
                ordinal=ordinal,
                subscription_id=trusted.subscription_id,
                tenant_id=trusted.tenant_id,
                scope_kind=trusted.scope_kind,
                scope=trusted.scope,
                valid_from=trusted.valid_from,
                valid_until=trusted.valid_until,
                change_type=graph_event.change_type,
                lifecycle_event=graph_event.lifecycle_event,
                identity=identity,
            )
        )
    return tuple(events)


__all__ = [
    "TeamsNotificationAuthenticationError",
    "TeamsNotificationError",
    "TeamsNotificationEvent",
    "TeamsNotificationScopeKind",
    "TeamsTrustedSubscription",
    "teams_notifications_from_payload",
]
