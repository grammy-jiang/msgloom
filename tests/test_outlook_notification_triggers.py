"""Verify Graph webhook envelopes only produce privacy-safe sync hints."""

from __future__ import annotations

import pytest

from message_ingest.acquisition.microsoft.outlook.notifications import (
    OutlookNotificationAuthenticationError,
    OutlookNotificationError,
    OutlookSyncTrigger,
    sync_triggers_from_notification,
)

SECRET = "opaque-client-state-secret"


def test_basic_changes_coalesce_to_mail_and_calendar_sync_hints() -> None:
    triggers = sync_triggers_from_notification(
        {
            "value": [
                {
                    "subscriptionId": "sub-mail",
                    "changeType": "updated",
                    "resource": "Users/owner/Messages/message-1",
                    "clientState": SECRET,
                },
                {
                    "subscriptionId": "sub-calendar",
                    "changeType": "deleted",
                    "resource": "Users/owner/Events/event-1",
                    "clientState": SECRET,
                },
                {
                    "subscriptionId": "sub-mail",
                    "changeType": "created",
                    "resource": "Users/owner/Messages/message-2",
                    "clientState": SECRET,
                },
            ]
        },
        expected_client_state=SECRET,
    )
    if triggers != (
        OutlookSyncTrigger("mail", "change"),
        OutlookSyncTrigger("calendar", "change"),
    ):
        pytest.fail(f"Unexpected notification sync hints: {triggers!r}")
    if any(trigger.requires_subscription_recovery for trigger in triggers):
        pytest.fail("Ordinary changes must not imply subscription recovery")


def test_lifecycle_event_uses_subscription_resource_mapping_and_strongest_reason() -> (
    None
):
    triggers = sync_triggers_from_notification(
        {
            "value": [
                {
                    "subscriptionId": "mail-sub",
                    "lifecycleEvent": "reauthorizationRequired",
                    "clientState": SECRET,
                },
                {
                    "subscriptionId": "mail-sub",
                    "lifecycleEvent": "missed",
                    "clientState": SECRET,
                },
            ]
        },
        expected_client_state=SECRET,
        subscription_resources={"mail-sub": "/users/owner/messages"},
    )
    if triggers != (OutlookSyncTrigger("mail", "missed"),):
        pytest.fail("Expected missed lifecycle event to dominate Mail trigger")
    if not triggers[0].requires_subscription_recovery:
        pytest.fail("Missed notification must request subscription recovery")


def test_client_state_mismatch_fails_closed() -> None:
    with pytest.raises(OutlookNotificationAuthenticationError):
        sync_triggers_from_notification(
            {
                "value": [
                    {
                        "changeType": "updated",
                        "resource": "/me/messages/m1",
                        "clientState": "wrong",
                    }
                ]
            },
            expected_client_state=SECRET,
        )


def test_unsupported_resource_is_rejected_without_exposing_provider_ids() -> None:
    with pytest.raises(OutlookNotificationError, match="unsupported"):
        sync_triggers_from_notification(
            {
                "value": [
                    {
                        "changeType": "updated",
                        "resource": "/users/owner/contacts/contact-1",
                        "clientState": SECRET,
                    }
                ]
            },
            expected_client_state=SECRET,
        )
