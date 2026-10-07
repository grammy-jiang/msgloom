"""Keep hydration completeness in application topology items."""

from dataclasses import asdict, fields, replace

import pytest

from message_ingest.items.microsoft.teams.topology import (
    TeamsChannelItem,
    TeamsTeamItem,
)
from microsoft_graph.items.teams.channel import (
    TeamsChannelItem as ProviderChannel,
)
from microsoft_graph.items.teams.channel import TeamsTeamItem as ProviderTeam

PROVENANCE = {
    "source_id": "source",
    "observed_at": "2026-10-08T00:00:00+00:00",
    "evidence_id": "evidence",
    "run_id": "run",
}


@pytest.mark.parametrize("item_type", [ProviderTeam, ProviderChannel])
def test_provider_topology_has_no_completeness_state(item_type) -> None:
    names = {field.name for field in fields(item_type)}
    if names.intersection({"detail_complete", "detail_limitation"}):
        pytest.fail("Provider topology contains application completeness state")


@pytest.mark.parametrize("factory", ["from_associated", "from_joined"])
def test_team_discovery_retains_application_completeness(factory: str) -> None:
    item = getattr(TeamsTeamItem, factory)({"id": "team"}, **PROVENANCE)
    if item.detail_complete or not item.detail_limitation:
        pytest.fail("Team discovery lost partial-detail policy")
    limited = getattr(TeamsTeamItem, factory)(
        {"id": "team"}, detail_limitation="detail GET denied", **PROVENANCE
    )
    if limited.detail_limitation != "detail GET denied":
        pytest.fail("Explicit team hydration limitation changed")
    with pytest.raises(ValueError, match="limitation"):
        getattr(TeamsTeamItem, factory)(
            {"id": "team"}, detail_limitation="", **PROVENANCE
        )


@pytest.mark.parametrize("factory", ["from_all_channels", "from_incoming"])
def test_channel_discovery_retains_application_completeness(factory: str) -> None:
    context = {"host_team_id": "host", "receiving_team_id": "receiver"}
    item = getattr(TeamsChannelItem, factory)(
        {"id": "channel"}, **context, **PROVENANCE
    )
    if item.detail_complete or not item.detail_limitation:
        pytest.fail("Channel discovery lost partial-detail policy")
    limited = getattr(TeamsChannelItem, factory)(
        {"id": "channel"},
        detail_limitation="detail GET denied",
        **context,
        **PROVENANCE,
    )
    if limited.detail_limitation != "detail GET denied":
        pytest.fail("Explicit channel hydration limitation changed")
    with pytest.raises(ValueError, match="limitation"):
        getattr(TeamsChannelItem, factory)(
            {"id": "channel"}, detail_limitation="", **context, **PROVENANCE
        )


@pytest.mark.parametrize(
    ("item_type", "provider_type", "context"),
    [
        (TeamsTeamItem, ProviderTeam, {}),
        (TeamsChannelItem, ProviderChannel, {"host_team_id": "host"}),
    ],
)
def test_detail_application_fields_preserve_provider_projection(
    item_type, provider_type, context
) -> None:
    raw = {"id": "resource", "displayName": "Observed"}
    item = item_type.from_detail(raw, **context, **PROVENANCE)
    provider = provider_type.from_detail(raw, **context)
    values = asdict(item)
    if not item.detail_complete or item.detail_limitation is not None:
        pytest.fail("Application detail completion changed")
    for key, value in asdict(provider).items():
        if values[key] != value:
            pytest.fail(f"Application changed provider projection field {key}")


@pytest.mark.parametrize(
    "item",
    [
        TeamsTeamItem.from_associated({"id": "team"}, **PROVENANCE),
        TeamsChannelItem.from_all_channels(
            {"id": "channel"}, host_team_id="host", **PROVENANCE
        ),
    ],
)
def test_application_rejects_complete_discovery(item) -> None:
    with pytest.raises(ValueError, match="Complete"):
        replace(item, detail_complete=True, detail_limitation=None)
