"""Application source binding stays outside provider subscription state."""

from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path

import pytest

from message_ingest.spiders.microsoft.teams._notification_intake import (
    NotificationInputError,
    load_trusted_subscriptions,
)
from microsoft_graph.protocol.teams_notifications import TeamsTrustedSubscription
from tests.teams_notification_support import chat_subscription


def test_provider_subscription_needs_no_application_identity() -> None:
    value = chat_subscription()
    value.pop("source_id")
    record = TeamsTrustedSubscription.from_mapping(value)
    if record.subscription_id != value["subscription_id"]:
        pytest.fail("Provider subscription lost its trusted identity")
    if "source_id" in {field.name for field in fields(record)}:
        pytest.fail("Provider subscription contains application source identity")


@pytest.mark.parametrize("bound_source", [None, "", 1, "other-source"])
def test_application_rejects_invalid_source_binding(
    tmp_path: Path, bound_source: object
) -> None:
    value = chat_subscription()
    value["source_id"] = bound_source
    path = tmp_path / "subscriptions.json"
    path.write_text(json.dumps({"subscriptions": [value]}))
    with pytest.raises(NotificationInputError):
        load_trusted_subscriptions(str(path), source_id="teams-source")


def test_application_preserves_source_binding_without_provider_state(
    tmp_path: Path,
) -> None:
    value = chat_subscription()
    path = tmp_path / "subscriptions.json"
    path.write_text(json.dumps({"subscriptions": [value]}))
    records = load_trusted_subscriptions(str(path), source_id=value["source_id"])
    record = records[value["subscription_id"]]
    if record.chat_id != value["chat_id"]:
        pytest.fail("Source validation changed the provider subscription scope")
    if hasattr(record, "source_id"):
        pytest.fail("Application source binding escaped into provider state")
