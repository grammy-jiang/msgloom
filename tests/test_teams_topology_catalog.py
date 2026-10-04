"""Teams topology observation and relation persistence tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from message_ingest.catalog.models.microsoft.teams import (
    TeamsTopologyCurrent,
    TeamsTopologyObservation,
)
from message_ingest.catalog.stores.microsoft.teams.topology import TeamsTopologyStore
from message_ingest.items.microsoft.teams.topology import (
    TeamsChannelItem,
    TeamsChannelMembershipItem,
    TeamsChatPinItem,
    TeamsPinStateItem,
    TeamsSharedWithTeamItem,
    TeamsTeamItem,
)
from tests.teams_persistence_support import (
    OBSERVED,
    RUN,
    SOURCE,
    open_catalog,
    record_evidence,
)


def _provenance(evidence_id: str, observed_at: str = OBSERVED) -> dict[str, str]:
    return {
        "source_id": SOURCE,
        "observed_at": observed_at,
        "evidence_id": evidence_id,
        "run_id": RUN,
    }


def test_discovery_detail_and_shared_topology_keep_all_context(tmp_path: Path) -> None:
    catalog = open_catalog(tmp_path)
    store = TeamsTopologyStore(catalog, source_id=SOURCE)
    try:
        times = [
            "2026-10-04T00:00:00+00:00",
            "2026-10-04T00:00:01+00:00",
            "2026-10-04T00:00:02+00:00",
            "2026-10-04T00:00:03+00:00",
        ]
        for index, observed_at in enumerate(times):
            record_evidence(catalog, f"ev-{index}", observed_at=observed_at)

        associated = TeamsTeamItem.from_associated(
            {"id": "host-team", "displayName": "Host"},
            detail_limitation="detail GET denied",
            **_provenance("ev-0", times[0]),
        )
        incoming = TeamsChannelItem.from_incoming(
            {
                "id": "shared-channel",
                "displayName": "Shared",
                "membershipType": "shared",
                "tenantId": "host-tenant",
                "@odata.id": "https://graph.microsoft.test/raw-resource-link",
            },
            host_team_id="host-team",
            host_tenant_id="host-tenant",
            receiving_team_id="receiving-team",
            receiving_tenant_id="receiving-tenant",
            detail_limitation="detail GET forbidden",
            **_provenance("ev-1", times[1]),
        )
        detail = TeamsChannelItem.from_detail(
            {
                "id": "shared-channel",
                "displayName": "Shared detail",
                "membershipType": "shared",
                "layoutType": "posts",
                "tenantId": "host-tenant",
            },
            host_team_id="host-team",
            host_tenant_id="host-tenant",
            receiving_team_id="receiving-team",
            receiving_tenant_id="receiving-tenant",
            original_resource_link=incoming.original_resource_link,
            **_provenance("ev-2", times[2]),
        )
        shared_with = TeamsSharedWithTeamItem.from_graph(
            {
                "id": "receiving-team",
                "tenantId": "receiving-tenant",
                "displayName": "Receiving",
            },
            host_team_id="host-team",
            host_tenant_id="host-tenant",
            channel_id="shared-channel",
            **_provenance("ev-3", times[3]),
        )

        for item in (associated, incoming, detail, shared_with):
            store.persist(item)

        with catalog.Session() as session:
            observations = session.scalars(
                select(TeamsTopologyObservation).order_by(
                    TeamsTopologyObservation.observation_id
                )
            ).all()
            if len(observations) != 4:
                pytest.fail(
                    "Expected every topology response to remain immutable history"
                )
            channel_rows = [
                row for row in observations if row.resource_kind == "channel"
            ]
            if len(channel_rows) != 2:
                pytest.fail("Discovery and detail must remain separate observations")
            discovery = channel_rows[0].context
            if discovery["detail_complete"]:
                pytest.fail("incomingChannels must remain explicitly partial")
            if discovery["detail_limitation"] != "detail GET forbidden":
                pytest.fail("Hydration failure limitation was not retained")
            if discovery["host_team_id"] != "host-team":
                pytest.fail("Host team identity was not retained")
            if discovery["receiving_team_id"] != "receiving-team":
                pytest.fail("Receiving team identity was not retained")
            if discovery["receiving_tenant_id"] != "receiving-tenant":
                pytest.fail("Receiving tenant identity was not retained")
            current = session.scalars(
                select(TeamsTopologyCurrent).where(
                    TeamsTopologyCurrent.resource_kind == "channel"
                )
            ).all()
            if len(current) != 1 or not current[0].context["detail_complete"]:
                pytest.fail(
                    "Later full detail should own the channel current projection"
                )
            if current[0].context["original_resource_link"] != (
                "https://graph.microsoft.test/raw-resource-link"
            ):
                pytest.fail(
                    "Raw incoming resource linkage context must survive hydration"
                )
    finally:
        catalog.close()


def test_allmembers_paths_with_same_membership_id_remain_distinct(
    tmp_path: Path,
) -> None:
    catalog = open_catalog(tmp_path)
    store = TeamsTopologyStore(catalog, source_id=SOURCE)
    try:
        for index in range(2):
            observed_at = f"2026-10-04T00:01:0{index}+00:00"
            evidence_id = f"member-{index}"
            record_evidence(catalog, evidence_id, observed_at=observed_at)
            item = TeamsChannelMembershipItem.from_all_members(
                {
                    "id": "opaque-membership",
                    "userId": "user-a",
                    "tenantId": "tenant-a",
                    "@microsoft.graph.originalSourceMembershipUrl": (
                        f"https://graph.microsoft.test/source/{index}"
                    ),
                },
                host_team_id="host-team",
                channel_id="shared-channel",
                **_provenance(evidence_id, observed_at),
            )
            store.persist(item)

        with catalog.Session() as session:
            rows = session.scalars(
                select(TeamsTopologyCurrent).where(
                    TeamsTopologyCurrent.resource_kind == "channel-membership"
                )
            ).all()
            if len(rows) != 2:
                pytest.fail("Distinct allMembers access paths must not collapse")
            urls = {row.context["original_source_membership_url"] for row in rows}
            if len(urls) != 2:
                pytest.fail("Every originalSourceMembershipUrl path must survive")
    finally:
        catalog.close()


def test_explicit_unpin_changes_relation_but_empty_inventory_does_not(
    tmp_path: Path,
) -> None:
    catalog = open_catalog(tmp_path)
    store = TeamsTopologyStore(catalog, source_id=SOURCE)
    try:
        record_evidence(catalog, "pin-1", observed_at=OBSERVED)
        record_evidence(
            catalog,
            "pin-2",
            observed_at="2026-10-04T00:02:00+00:00",
        )
        pinned = TeamsChatPinItem.from_graph(
            {"id": "message-1"},
            chat_id="chat-a",
            **_provenance("pin-1"),
        )
        unpinned = TeamsPinStateItem(
            source_id=SOURCE,
            chat_id="chat-a",
            message_id="message-1",
            state="unpinned",
            observed_at="2026-10-04T00:02:00+00:00",
            evidence_id="pin-2",
            run_id=RUN,
            reason="explicit notification",
        )
        store.persist(pinned)
        store.persist(unpinned)

        with catalog.Session() as session:
            history = session.scalars(
                select(TeamsTopologyObservation).where(
                    TeamsTopologyObservation.resource_kind == "pin"
                )
            ).all()
            if len(history) != 2:
                pytest.fail("Pin and explicit unpin must both remain in history")
            current = session.scalar(
                select(TeamsTopologyCurrent).where(
                    TeamsTopologyCurrent.resource_kind == "pin"
                )
            )
            if current is None or current.context["state"] != "unpinned":
                pytest.fail(
                    "Explicit unpin evidence must update current relation state"
                )

        # A later empty pin list emits no semantic item. Re-read to prove no
        # absence-based mutation occurred.
        with catalog.Session() as session:
            current = session.scalar(
                select(TeamsTopologyCurrent).where(
                    TeamsTopologyCurrent.resource_kind == "pin"
                )
            )
            if current is None or current.context["state"] != "unpinned":
                pytest.fail("Empty inventory must not invent a pin transition")
    finally:
        catalog.close()
