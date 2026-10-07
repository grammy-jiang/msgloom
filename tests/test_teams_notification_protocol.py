"""Pure Teams notification trust, scope, and lifecycle validation tests."""

from __future__ import annotations

import traceback
from collections.abc import Mapping

import pytest

from microsoft_graph.protocol.teams import TeamsMessageIdentity
from microsoft_graph.protocol.teams_notifications import (
    TeamsNotificationAuthenticationError,
    TeamsNotificationError,
    TeamsNotificationScopeKind,
    TeamsTrustedSubscription,
    teams_notifications_from_payload,
)

CAPTURED = "2026-10-04T05:00:00+00:00"
SECRET = "client-state-secret-must-not-leak"


def _trusted(
    *,
    subscription_id: str = "sub-chat",
    scope_kind: TeamsNotificationScopeKind = "chat-messages",
    tenant_id: str = "tenant-a",
    chat_id: str | None = "same",
    host_team_id: str | None = None,
    channel_id: str | None = None,
) -> TeamsTrustedSubscription:
    return TeamsTrustedSubscription(
        subscription_id=subscription_id,
        tenant_id=tenant_id,
        scope_kind=scope_kind,
        client_state=SECRET,
        valid_from="2026-10-04T04:00:00+00:00",
        valid_until="2026-10-04T06:00:00+00:00",
        chat_id=chat_id,
        host_team_id=host_team_id,
        channel_id=channel_id,
    )


def _entry(
    *,
    subscription_id: str = "sub-chat",
    resource: str = "/chats/same/messages/same",
    change_type: str = "updated",
    tenant_id: str = "tenant-a",
    client_state: str = SECRET,
    **extra: object,
) -> dict[str, object]:
    return {
        "subscriptionId": subscription_id,
        "resource": resource,
        "changeType": change_type,
        "tenantId": tenant_id,
        "clientState": client_state,
        **extra,
    }


def _parse(
    *entries: Mapping[str, object],
    subscriptions: tuple[TeamsTrustedSubscription, ...] | None = None,
    captured_at: str = CAPTURED,
):
    trusted = subscriptions or (_trusted(),)
    return teams_notifications_from_payload(
        {"value": list(entries)},
        trusted_subscriptions={record.subscription_id: record for record in trusted},
        captured_at=captured_at,
    )


def test_chat_and_channel_reply_resources_keep_opaque_scope() -> None:
    channel = _trusted(
        subscription_id="sub-channel",
        scope_kind="channel-messages",
        chat_id=None,
        host_team_id="same",
        channel_id="same",
    )
    events = _parse(
        _entry(),
        _entry(
            subscription_id="sub-channel",
            resource="/teams/same/channels/same/messages/root/replies/same",
        ),
        subscriptions=(_trusted(), channel),
    )
    if events[0].identity != TeamsMessageIdentity.chat("same", chat_id="same"):
        pytest.fail("Chat notification identity lost its chat scope")
    expected = TeamsMessageIdentity.channel_reply(
        "same",
        team_id="same",
        channel_id="same",
        root_message_id="root",
    )
    if events[1].identity != expected:
        pytest.fail("Channel reply notification identity lost its root scope")
    if events[0].scope == events[1].scope:
        pytest.fail("Equal opaque IDs across scopes must not alias")


@pytest.mark.parametrize(
    ("mutator", "error"),
    [
        (
            lambda value: value.update(clientState="wrong"),
            TeamsNotificationAuthenticationError,
        ),
        (lambda value: value.update(subscriptionId="unknown"), TeamsNotificationError),
        (lambda value: value.update(tenantId="tenant-b"), TeamsNotificationError),
        (
            lambda value: value.update(resource="/chats/other/messages/same"),
            TeamsNotificationError,
        ),
        (
            lambda value: value.update(
                resource="https://evil.invalid/chats/same/messages/same"
            ),
            TeamsNotificationError,
        ),
        (
            lambda value: value.update(resourceData={"id": "same"}),
            TeamsNotificationError,
        ),
        (
            lambda value: value.update(encryptedContent={"data": "ciphertext"}),
            TeamsNotificationError,
        ),
    ],
)
def test_untrusted_boundary_fails_atomically_without_secret_leak(
    mutator,
    error: type[Exception],
) -> None:
    good = _entry(resource="/chats/same/messages/first")
    bad = _entry(resource="/chats/same/messages/second")
    mutator(bad)
    with pytest.raises(error) as caught:
        _parse(good, bad)
    rendered = "".join(traceback.format_exception(caught.value))
    if SECRET in rendered or "second" in rendered:
        pytest.fail("Notification validation error leaked secret/provider values")


@pytest.mark.parametrize(
    "payload",
    [
        {"value": [_entry()], "validationTokens": ["jwt"]},
        {"value": [_entry()], "validationToken": "handshake"},
        {"value": [_entry()], "encryptedContent": {"data": "ciphertext"}},
    ],
)
def test_rich_or_validation_token_envelopes_are_rejected(payload) -> None:
    with pytest.raises(TeamsNotificationError):
        teams_notifications_from_payload(
            payload,
            trusted_subscriptions={"sub-chat": _trusted()},
            captured_at=CAPTURED,
        )


@pytest.mark.parametrize(
    "captured_at",
    [
        "2026-10-04T03:59:59+00:00",
        "2026-10-04T06:00:01+00:00",
    ],
)
def test_capture_must_fall_inside_trusted_subscription_window(captured_at: str) -> None:
    with pytest.raises(TeamsNotificationError, match="validity"):
        _parse(_entry(), captured_at=captured_at)


def test_invalid_trusted_window_is_rejected() -> None:
    with pytest.raises(ValueError, match="valid"):
        TeamsTrustedSubscription(
            subscription_id="sub",
            tenant_id="tenant",
            scope_kind="chat-messages",
            client_state=SECRET,
            valid_from="2026-10-04T06:00:00+00:00",
            valid_until="2026-10-04T04:00:00+00:00",
            chat_id="chat",
        )


@pytest.mark.parametrize(
    "lifecycle",
    ["reauthorizationRequired", "subscriptionRemoved"],
)
def test_supported_lifecycle_event_uses_trusted_scope(
    lifecycle: str,
) -> None:
    entry = {
        "subscriptionId": "sub-chat",
        "tenantId": "tenant-a",
        "clientState": SECRET,
        "lifecycleEvent": lifecycle,
    }
    event = _parse(entry)[0]
    if event.identity is not None or event.lifecycle_event != lifecycle:
        pytest.fail("Lifecycle notification lost its provider lifecycle fact")
    if event.scope != ("same",):
        pytest.fail("Lifecycle notification lost its trusted resource scope")


def test_generic_missed_lifecycle_is_not_claimed_for_teams() -> None:
    entry = {
        "subscriptionId": "sub-chat",
        "tenantId": "tenant-a",
        "clientState": SECRET,
        "lifecycleEvent": "missed",
    }
    with pytest.raises(TeamsNotificationError, match="lifecycle"):
        _parse(entry)


def _documented_resource(location: str, *, odata: bool) -> str:
    paths = {
        "chat": (("chats", "chat-a"), ("messages", "message-a")),
        "channel-root": (
            ("teams", "team-a"),
            ("channels", "channel-a"),
            ("messages", "message-a"),
        ),
        "channel-reply": (
            ("teams", "team-a"),
            ("channels", "channel-a"),
            ("messages", "root-a"),
            ("replies", "message-a"),
        ),
    }
    selected = paths[location]
    if odata:
        return "/".join(f"{kind}('{identity}')" for kind, identity in selected)
    return "/" + "/".join(part for pair in selected for part in pair)


def _documented_subscription(location: str) -> TeamsTrustedSubscription:
    if location == "chat":
        return _trusted(chat_id="chat-a")
    return _trusted(
        subscription_id="sub-channel",
        scope_kind="channel-messages",
        chat_id=None,
        host_team_id="team-a",
        channel_id="channel-a",
    )


@pytest.mark.parametrize("location", ["chat", "channel-root", "channel-reply"])
@pytest.mark.parametrize(
    ("odata", "metadata"),
    [(False, True), (True, False), (True, True)],
)
def test_documented_basic_identity_metadata_and_odata_key_paths(
    location: str,
    odata: bool,
    metadata: bool,
) -> None:
    """Accept documented basic identity metadata without treating it as a body."""
    resource = _documented_resource(location, odata=odata)
    subscription = _documented_subscription(location)
    entry = _entry(
        subscription_id=subscription.subscription_id,
        resource=resource,
    )
    if metadata:
        entry["resourceData"] = {
            "id": "message-a",
            "@odata.type": "#Microsoft.Graph.chatMessage",
            "@odata.id": resource,
        }

    events = _parse(entry, subscriptions=(subscription,))
    if len(events) != 1 or events[0].identity is None:
        pytest.fail("Documented basic notification did not resolve one target")
    identity = events[0].identity
    if identity.message_id != "message-a" or identity.location.value != location:
        pytest.fail("Documented basic notification changed scoped message identity")
    if location == "channel-reply" and identity.root_message_id != "root-a":
        pytest.fail("Documented reply notification lost its root identity")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", "different-message"),
        ("@odata.type", "#Microsoft.Graph.user"),
        ("@odata.id", "chats('other-chat')/messages('message-a')"),
        ("@odata.id", "https://attacker.invalid/messages/message-a"),
        ("body", {"content": "unverified message body"}),
    ],
)
def test_basic_resource_data_cannot_forge_identity_or_supply_message_body(
    field: str,
    value: object,
) -> None:
    """Reject metadata that disagrees with the authenticated resource target."""
    resource = _documented_resource("chat", odata=True)
    metadata: dict[str, object] = {
        "id": "message-a",
        "@odata.type": "#Microsoft.Graph.chatMessage",
        "@odata.id": resource,
    }
    metadata[field] = value
    entry = _entry(resource=resource, resourceData=metadata)
    with pytest.raises(TeamsNotificationError):
        _parse(entry, subscriptions=(_documented_subscription("chat"),))


def test_odata_key_form_preserves_percent_encoded_opaque_ids() -> None:
    """Decode one path segment without losing opaque ID boundaries."""
    trusted = _trusted(chat_id="chat/opaque")
    resource = "chats('chat%2Fopaque')/messages('message%2Fopaque')"
    event = _parse(
        _entry(resource=resource),
        subscriptions=(trusted,),
    )[0]
    expected = TeamsMessageIdentity.chat(
        "message/opaque",
        chat_id="chat/opaque",
    )
    if event.identity != expected:
        pytest.fail("OData key resource decoding changed opaque Teams IDs")


def test_odata_key_form_scope_mismatch_fails_closed() -> None:
    """OData syntax must not bypass caller-trusted scope binding."""
    with pytest.raises(TeamsNotificationError, match="scope"):
        _parse(
            _entry(resource="chats('other')/messages('message-a')"),
            subscriptions=(_trusted(chat_id="chat-a"),),
        )


def test_client_state_is_hidden_from_trusted_subscription_repr() -> None:
    if SECRET in repr(_trusted()):
        pytest.fail("Trusted subscription repr exposed clientState")
