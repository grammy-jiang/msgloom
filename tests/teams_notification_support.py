"""Shared fixtures for local Teams notification reconciliation tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from message_ingest.catalog.store import Catalog
from tests.teams_support import GraphFixture, crawl, json_reply

SOURCE = "teams-fixture"
SECRET = "notification-client-state-secret"
CAPTURED = "2026-10-04T05:00:00+00:00"
VALID_FROM = "2026-10-04T04:00:00+00:00"
VALID_UNTIL = "2026-10-04T06:00:00+00:00"
DELIVERY_URL = "https://trusted.local/teams/webhook"
DEFAULT_EVIDENCE_ID = "a" * 32


def chat_subscription(
    *,
    subscription_id: str = "sub-chat",
    chat_id: str = "chat-a",
) -> dict[str, Any]:
    """Return one caller-trusted delegated chat subscription record."""
    return {
        "subscription_id": subscription_id,
        "source_id": SOURCE,
        "tenant_id": "tenant-a",
        "scope_kind": "chat-messages",
        "client_state": SECRET,
        "valid_from": VALID_FROM,
        "valid_until": VALID_UNTIL,
        "chat_id": chat_id,
    }


def channel_subscription(
    *,
    subscription_id: str = "sub-channel",
    team_id: str = "team-a",
    channel_id: str = "channel-a",
) -> dict[str, Any]:
    """Return one caller-trusted delegated channel subscription record."""
    return {
        "subscription_id": subscription_id,
        "source_id": SOURCE,
        "tenant_id": "tenant-a",
        "scope_kind": "channel-messages",
        "client_state": SECRET,
        "valid_from": VALID_FROM,
        "valid_until": VALID_UNTIL,
        "host_team_id": team_id,
        "channel_id": channel_id,
    }


def change_event(
    *,
    subscription_id: str = "sub-chat",
    resource: str = "/chats/chat-a/messages/message-a",
    change_type: str = "updated",
    tenant_id: str = "tenant-a",
    client_state: str = SECRET,
    **extra: object,
) -> dict[str, object]:
    """Return one basic notification entry with explicit provider metadata."""
    return {
        "subscriptionId": subscription_id,
        "resource": resource,
        "changeType": change_type,
        "tenantId": tenant_id,
        "clientState": client_state,
        **extra,
    }


def lifecycle_event(
    *,
    subscription_id: str = "sub-chat",
    lifecycle: str = "reauthorizationRequired",
    tenant_id: str = "tenant-a",
    client_state: str = SECRET,
) -> dict[str, object]:
    """Return one lifecycle entry that relies on the trusted resource mapping."""
    return {
        "subscriptionId": subscription_id,
        "tenantId": tenant_id,
        "clientState": client_state,
        "lifecycleEvent": lifecycle,
    }


def encode_envelope(entries: list[dict[str, object]]) -> bytes:
    """Encode deterministic but non-prettified bytes for exact-body assertions."""
    return json.dumps(
        {"value": entries},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def write_notification_inputs(
    tmp_path: Path,
    *,
    body: bytes,
    subscriptions: list[dict[str, Any]],
    evidence_id: str = DEFAULT_EVIDENCE_ID,
    captured_at: str = CAPTURED,
    delivery_url: str = DELIVERY_URL,
    local_gap: dict[str, Any] | None = None,
) -> list[str]:
    """Write caller-controlled local files and return explicit spider arguments."""
    envelope_path = tmp_path / "notification-envelope.json"
    trusted_path = tmp_path / "trusted-subscriptions.json"
    envelope_path.write_bytes(body)
    trusted_path.write_text(
        json.dumps({"subscriptions": subscriptions}, ensure_ascii=False),
        encoding="utf-8",
    )
    arguments = [
        "-a",
        f"envelope_path={envelope_path}",
        "-a",
        f"trusted_subscriptions_path={trusted_path}",
        "-a",
        f"envelope_id={evidence_id}",
        "-a",
        f"captured_at={captured_at}",
        "-a",
        f"delivery_url={delivery_url}",
    ]
    if local_gap is not None:
        gap_path = tmp_path / "local-gap.json"
        gap_path.write_text(json.dumps(local_gap, ensure_ascii=False), encoding="utf-8")
        arguments.extend(["-a", f"local_gap_path={gap_path}"])
    return arguments


def crawl_notification(
    tmp_path: Path,
    fixture: GraphFixture,
    *,
    body: bytes,
    subscriptions: list[dict[str, Any]],
    evidence_id: str = DEFAULT_EVIDENCE_ID,
    captured_at: str = CAPTURED,
    delivery_url: str = DELIVERY_URL,
    local_gap: dict[str, Any] | None = None,
    extra_settings: dict[str, object] | None = None,
):
    """Run the private spider directly without requiring coordinator registration."""
    arguments = [
        "crawl",
        "microsoft_teams_notification_reconcile",
        *write_notification_inputs(
            tmp_path,
            body=body,
            subscriptions=subscriptions,
            evidence_id=evidence_id,
            captured_at=captured_at,
            delivery_url=delivery_url,
            local_gap=local_gap,
        ),
    ]
    settings: dict[str, object] = {
        "SPIDER_MODULES": "message_ingest.spiders.microsoft.teams.notifications",
        "RETRY_TIMES": 0,
    }
    settings.update(extra_settings or {})
    return crawl(
        tmp_path,
        fixture,
        arguments,
        extra_settings=settings,
    )


def open_catalog(tmp_path: Path) -> Catalog:
    """Open the notification test catalog created by a real crawl."""
    return Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")


__all__ = [
    "CAPTURED",
    "DEFAULT_EVIDENCE_ID",
    "DELIVERY_URL",
    "SECRET",
    "SOURCE",
    "VALID_FROM",
    "VALID_UNTIL",
    "GraphFixture",
    "change_event",
    "channel_subscription",
    "chat_subscription",
    "crawl_notification",
    "encode_envelope",
    "json_reply",
    "lifecycle_event",
    "open_catalog",
    "write_notification_inputs",
]
