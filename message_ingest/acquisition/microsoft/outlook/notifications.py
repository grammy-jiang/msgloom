"""Validate basic Graph notifications and reduce them to privacy-safe sync hints."""

from __future__ import annotations

import hmac
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

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
    "reauthorizationrequired": "reauthorization_required",
    "subscriptionremoved": "subscription_removed",
    "missed": "missed",
}


class OutlookNotificationError(ValueError):
    """Base error for untrusted or unsupported notification envelopes."""


class OutlookNotificationAuthenticationError(OutlookNotificationError):
    """A notification failed the configured basic-notification clientState check."""


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
    if not expected_client_state:
        raise ValueError("expected_client_state must not be empty")
    values = payload.get("value")
    if not isinstance(values, list):
        raise OutlookNotificationError("notification payload must contain a value list")

    strongest: dict[ResourceKind, TriggerReason] = {}
    resource_map = subscription_resources or {}
    for item in values:
        if not isinstance(item, Mapping):
            raise OutlookNotificationError("notification entries must be objects")
        client_state = item.get("clientState")
        if not isinstance(client_state, str) or not hmac.compare_digest(
            client_state, expected_client_state
        ):
            raise OutlookNotificationAuthenticationError(
                "Microsoft Graph notification clientState mismatch"
            )

        resource = item.get("resource")
        if not isinstance(resource, str) or not resource:
            subscription_id = item.get("subscriptionId")
            if isinstance(subscription_id, str):
                resource = resource_map.get(subscription_id)
        if not isinstance(resource, str) or not resource:
            raise OutlookNotificationError(
                "notification resource is missing and subscription mapping is unavailable"
            )
        kind = _resource_kind(resource)
        reason = _reason(item)
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


def _reason(item: Mapping[str, Any]) -> TriggerReason:
    lifecycle = item.get("lifecycleEvent")
    if lifecycle is None:
        change_type = item.get("changeType")
        if change_type not in {"created", "updated", "deleted"}:
            raise OutlookNotificationError("unsupported Outlook changeType")
        return "change"
    if not isinstance(lifecycle, str):
        raise OutlookNotificationError("lifecycleEvent must be a string")
    try:
        return _LIFECYCLE_REASON[lifecycle.replace("_", "").lower()]
    except KeyError as exc:
        raise OutlookNotificationError("unsupported Outlook lifecycleEvent") from exc


__all__ = [
    "OutlookNotificationAuthenticationError",
    "OutlookNotificationError",
    "OutlookSyncTrigger",
    "sync_triggers_from_notification",
]
