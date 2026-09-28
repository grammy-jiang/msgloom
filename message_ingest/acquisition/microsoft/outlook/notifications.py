"""Reduce validated Graph notifications to privacy-safe Outlook sync hints."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from microsoft_graph.protocol.notifications import (
    GraphNotificationAuthenticationError as OutlookNotificationAuthenticationError,
)
from microsoft_graph.protocol.notifications import (
    GraphNotificationError as OutlookNotificationError,
)
from microsoft_graph.protocol.notifications import notifications_from_payload

ResourceKind = Literal["mail", "calendar"]
TriggerReason = Literal[
    "change",
    "reauthorization_required",
    "subscription_removed",
    "missed",
]

_REASON_PRIORITY: dict[TriggerReason, int] = {
    "change": 0,
    "reauthorization_required": 1,
    "subscription_removed": 2,
    "missed": 3,
}
_LIFECYCLE_REASON: dict[str, TriggerReason] = {
    "reauthorizationRequired": "reauthorization_required",
    "subscriptionRemoved": "subscription_removed",
    "missed": "missed",
}


@dataclass(frozen=True, slots=True)
class OutlookSyncTrigger:
    """Privacy-safe hint for the external scheduler to launch normal sync."""

    resource: ResourceKind
    reason: TriggerReason

    @property
    def requires_subscription_recovery(self) -> bool:
        return self.reason in {
            "reauthorization_required",
            "subscription_removed",
            "missed",
        }


def sync_triggers_from_notification(
    payload: Mapping[str, Any],
    *,
    expected_client_state: str,
    subscription_resources: Mapping[str, str] | None = None,
) -> tuple[OutlookSyncTrigger, ...]:
    """Validate one basic webhook envelope and coalesce it by resource type.

    The returned values contain no subscription IDs, user IDs, message IDs,
    event IDs, or mailbox locators. They are only scheduling hints; delta/sync
    remains the correctness mechanism.
    """
    strongest: dict[ResourceKind, TriggerReason] = {}
    for item in notifications_from_payload(
        payload,
        expected_client_state=expected_client_state,
        subscription_resources=subscription_resources,
    ):
        kind = _resource_kind(item.resource)
        reason: TriggerReason = (
            _LIFECYCLE_REASON[item.lifecycle_event]
            if item.lifecycle_event is not None
            else "change"
        )
        current = strongest.get(kind)
        if current is None or _REASON_PRIORITY[reason] > _REASON_PRIORITY[current]:
            strongest[kind] = reason

    return tuple(
        OutlookSyncTrigger(resource=kind, reason=strongest[kind])
        for kind in ("mail", "calendar")
        if kind in strongest
    )


def _resource_kind(resource: str) -> ResourceKind:
    normalized = "/" + resource.strip().strip("/").lower()
    if "/messages" in normalized:
        return "mail"
    if "/events" in normalized:
        return "calendar"
    raise OutlookNotificationError("unsupported Outlook notification resource")


__all__ = [
    "OutlookNotificationAuthenticationError",
    "OutlookNotificationError",
    "OutlookSyncTrigger",
    "sync_triggers_from_notification",
]
