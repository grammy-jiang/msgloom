"""Validate basic Graph change and lifecycle notification envelopes."""

from __future__ import annotations

import hmac
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

ChangeType = Literal["created", "updated", "deleted"]
LifecycleEvent = Literal["reauthorizationRequired", "subscriptionRemoved", "missed"]

_LIFECYCLE_EVENTS: dict[str, LifecycleEvent] = {
    "reauthorizationrequired": "reauthorizationRequired",
    "subscriptionremoved": "subscriptionRemoved",
    "missed": "missed",
}


class GraphNotificationError(ValueError):
    """Report an invalid envelope without including provider identifiers."""


class GraphNotificationAuthenticationError(GraphNotificationError):
    """Report a failed basic-notification ``clientState`` check."""


@dataclass(frozen=True, slots=True)
class GraphNotification:
    """
    Retain a resolved resource and one provider event, in envelope order.

    The resource can contain private identifiers and is omitted from repr.
    Lifecycle events take precedence over changeType when both are supplied.
    No scheduling, resource classification, or recovery policy is applied.
    """

    resource: str = field(repr=False)
    change_type: ChangeType | None = None
    lifecycle_event: LifecycleEvent | None = None


def notifications_from_payload(
    payload: Mapping[str, Any],
    *,
    expected_client_state: str,
    subscription_resources: Mapping[str, str] | None = None,
) -> tuple[GraphNotification, ...]:
    """
    Authenticate and validate a complete basic webhook envelope atomically.

    A nonempty resource wins over the subscription-to-resource fallback.
    The caller owns that mapping. Errors contain no values from the envelope.
    This does not validate rich notifications or decrypt resource data.
    """
    if not isinstance(expected_client_state, str) or not expected_client_state:
        raise ValueError("expected_client_state must not be empty")
    values = payload.get("value") if isinstance(payload, Mapping) else None
    if not isinstance(values, list):
        raise GraphNotificationError("notification payload must contain a value list")

    notifications = []
    resource_map = subscription_resources or {}
    for item in values:
        if not isinstance(item, Mapping):
            raise GraphNotificationError("notification entries must be objects")
        client_state = item.get("clientState")
        if not isinstance(client_state, str) or not hmac.compare_digest(
            client_state.encode("utf-8"), expected_client_state.encode("utf-8")
        ):
            raise GraphNotificationAuthenticationError(
                "Microsoft Graph notification clientState mismatch"
            )
        resource = item.get("resource")
        if not isinstance(resource, str) or not resource:
            subscription_id = item.get("subscriptionId")
            if isinstance(subscription_id, str):
                resource = resource_map.get(subscription_id)
        if not isinstance(resource, str) or not resource:
            raise GraphNotificationError(
                "notification resource is missing and subscription mapping is unavailable"
            )
        notifications.append(_notification(resource, item))
    return tuple(notifications)


def _notification(resource: str, item: Mapping[str, Any]) -> GraphNotification:
    lifecycle = item.get("lifecycleEvent")
    if lifecycle is None:
        change_type = item.get("changeType")
        if not isinstance(change_type, str) or change_type not in (
            "created",
            "updated",
            "deleted",
        ):
            raise GraphNotificationError("unsupported Graph changeType")
        return GraphNotification(resource, change_type=change_type)
    if not isinstance(lifecycle, str):
        raise GraphNotificationError("lifecycleEvent must be a string")
    event = _LIFECYCLE_EVENTS.get(lifecycle.replace("_", "").lower())
    if event is None:
        raise GraphNotificationError("unsupported Graph lifecycleEvent")
    return GraphNotification(resource, lifecycle_event=event)


__all__ = [
    "ChangeType",
    "GraphNotification",
    "GraphNotificationAuthenticationError",
    "GraphNotificationError",
    "LifecycleEvent",
    "notifications_from_payload",
]
