"""Application source binding stays outside provider subscription state."""

from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path

import pytest

from message_ingest.spiders.microsoft.teams._notification_intake import (
    NotificationInputError,
    aggregate_coverage_items,
    load_trusted_subscriptions,
)
from microsoft_graph.protocol.teams_notifications import (
    TeamsTrustedSubscription,
    teams_notifications_from_payload,
)
from tests.teams_notification_support import chat_subscription, lifecycle_event


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


@pytest.mark.parametrize(
    ("lifecycles", "expected_gaps", "aggregate_gap"),
    [
        (
            ["reauthorizationRequired"],
            ["reauthorization-required"],
            "reauthorization-required",
        ),
        (["subscriptionRemoved"], ["subscription-removed"], "subscription-removed"),
        (
            ["subscriptionRemoved", "reauthorizationRequired"],
            ["subscription-removed", "reauthorization-required"],
            "notification-gap",
        ),
    ],
)
def test_application_maps_lifecycle_facts_to_durable_gap_details(
    lifecycles: list[str], expected_gaps: list[str], aggregate_gap: str
) -> None:
    record = TeamsTrustedSubscription.from_mapping(chat_subscription())
    events = teams_notifications_from_payload(
        {"value": [lifecycle_event(lifecycle=value) for value in lifecycles]},
        trusted_subscriptions={record.subscription_id: record},
        captured_at="2026-10-04T05:00:00+00:00",
    )
    if any(hasattr(event, "gap_kind") for event in events):
        pytest.fail("Provider lifecycle facts contain application gap semantics")
    items = aggregate_coverage_items(
        events,
        source_id="teams-source",
        observed_at="2026-10-04T05:00:00+00:00",
        evidence_id="a" * 32,
        run_id="run",
    )
    if len(items) != 1:
        pytest.fail("Same-scope lifecycle facts did not aggregate")
    item = items[0]
    if item.gap_kind != aggregate_gap or not item.history_incomplete:
        pytest.fail("Application lifecycle gap aggregation changed")
    details = item.details["events"]
    if [value["gap_kind"] for value in details] != expected_gaps:
        pytest.fail("Stored lifecycle gap details changed")
    if [value["lifecycle_event"] for value in details] != lifecycles:
        pytest.fail("Stored lifecycle facts lost their provider order")
