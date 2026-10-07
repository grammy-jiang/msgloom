"""Qualify basic Teams notifications against documented provider forms."""

from __future__ import annotations

import pytest

from microsoft_graph.protocol.teams_notifications import (
    TeamsNotificationError,
    TeamsTrustedSubscription,
    teams_notifications_from_payload,
)


def _trusted(location: str) -> TeamsTrustedSubscription:
    return TeamsTrustedSubscription(
        subscription_id="sub",
        tenant_id="tenant",
        scope_kind="chat-messages" if location == "chat" else "channel-messages",
        client_state="synthetic-secret",
        valid_from="2026-10-04T00:00:00Z",
        valid_until="2026-10-05T00:00:00Z",
        chat_id="chat" if location == "chat" else None,
        host_team_id=None if location == "chat" else "team",
        channel_id=None if location == "chat" else "channel",
    )


def _resource(location: str, form: str) -> str:
    paths = {
        "chat": (("chats", "chat"), ("messages", "message")),
        "channel-root": (
            ("teams", "team"),
            ("channels", "channel"),
            ("messages", "message"),
        ),
        "channel-reply": (
            ("teams", "team"),
            ("channels", "channel"),
            ("messages", "root"),
            ("replies", "message"),
        ),
    }
    if form == "odata":
        return "/".join(f"{kind}('{identity}')" for kind, identity in paths[location])
    return "/".join(part for pair in paths[location] for part in pair)


def _entry(resource: str) -> dict:
    return {
        "subscriptionId": "sub",
        "tenantId": "tenant",
        "clientState": "synthetic-secret",
        "changeType": "created",
        "resource": resource,
    }


def _parse(entry: dict, trusted: TeamsTrustedSubscription):
    return teams_notifications_from_payload(
        {"value": [entry]},
        trusted_subscriptions={"sub": trusted},
        captured_at="2026-10-04T01:00:00Z",
    )


@pytest.mark.parametrize("location", ("chat", "channel-root", "channel-reply"))
@pytest.mark.parametrize(
    "form,metadata", (("slash", True), ("odata", False), ("odata", True))
)
def test_documented_basic_identity_metadata_and_key_paths(location, form, metadata):
    """Basic resourceData identifies a target and is not an encrypted body."""
    resource = _resource(location, form)
    entry = _entry(resource)
    if metadata:
        entry["resourceData"] = {
            "id": "message",
            "@odata.type": "#Microsoft.Graph.chatMessage",
            "@odata.id": resource,
        }
    events = _parse(entry, _trusted(location))
    if len(events) != 1 or events[0].identity is None:
        pytest.fail("Documented basic notification did not resolve one target")
    identity = events[0].identity
    if identity.message_id != "message" or identity.location != location:
        pytest.fail("Basic resource routing changed scoped provider identity")
    if location == "channel-reply" and identity.root_message_id != "root":
        pytest.fail("Reply notification lost its root identity")


@pytest.mark.parametrize(
    "field,value",
    (
        ("id", "different-message"),
        ("@odata.type", "#Microsoft.Graph.user"),
        ("@odata.id", "chats/another/messages/message"),
        ("@odata.id", "https://attacker.invalid/messages/message"),
        ("body", {"content": "unverified message body"}),
    ),
)
def test_basic_metadata_cannot_override_scope_or_supply_message_body(field, value):
    """Conflicting identity metadata and full message data fail closed."""
    resource = _resource("chat", "odata")
    entry = _entry(resource)
    entry["resourceData"] = {
        "id": "message",
        "@odata.type": "#Microsoft.Graph.chatMessage",
        "@odata.id": resource,
        field: value,
    }
    with pytest.raises(TeamsNotificationError):
        _parse(entry, _trusted("chat"))
