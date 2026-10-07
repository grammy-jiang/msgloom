"""Pin Teams membership paths and repeated membership-path fidelity."""

from dataclasses import fields, make_dataclass

import pytest
from itemadapter import ItemAdapter

from microsoft_graph.items.teams.membership import (
    TeamsChannelMembershipItem,
    TeamsTeamMembershipItem,
)
from microsoft_graph.spiders.teams.channel import MicrosoftTeamsChannelSpider


def test_team_and_channel_membership_paths_keep_endpoint_specific_queries():
    spider = MicrosoftTeamsChannelSpider(name="provider")
    cases = {
        spider.team_members_path("team"): "/teams/team/members",
        spider.channel_members_path("team", "channel"): (
            "/teams/team/channels/channel/members"
        ),
        spider.team_members_path("team", page_size=999): (
            "/teams/team/members?%24top=999"
        ),
        spider.channel_members_path("team", "channel", page_size=999): (
            "/teams/team/channels/channel/members?%24top=999"
        ),
        spider.team_members_path("team", page_size=2): "/teams/team/members?%24top=2",
        spider.channel_members_path("team", "channel", page_size=2): (
            "/teams/team/channels/channel/members?%24top=2"
        ),
        spider.all_channel_members_path("team", "channel"): (
            "/teams/team/channels/channel/allMembers"
        ),
    }
    for actual, wanted in cases.items():
        if actual != wanted:
            pytest.fail(f"Membership path changed: {actual!r} != {wanted!r}")
    if "%24top" in spider.all_channel_members_path("team", "channel"):
        pytest.fail("allMembers must not invent unsupported page-size syntax")


def test_team_membership_preserves_provider_values_and_parent_scope():
    raw = {
        "id": "membership",
        "userId": "user",
        "tenantId": "foreign-tenant",
        "displayName": "",
        "email": "",
        "roles": [],
        "visibleHistoryStartDateTime": "",
        "@microsoft.graph.originalSourceMembershipUrl": "",
        "future": {"nested": [0, False, ""]},
    }
    item = TeamsTeamMembershipItem.from_graph(raw, team_id="team")
    if item.raw is not raw or item.membership_id != "membership":
        pytest.fail("Team membership identity or raw provider object changed")
    if item.team_id != "team":
        pytest.fail("Team parent scope was lost")
    if (
        item.user_id,
        item.tenant_id,
        item.display_name,
        item.email,
        item.roles,
        item.visible_history_start_date_time,
        item.original_source_membership_url,
    ) != ("user", "foreign-tenant", "", "", [], "", ""):
        pytest.fail("Falsey or foreign-tenant membership fields were normalized")
    if hasattr(item, "__dict__") or ItemAdapter(item).asdict()["raw"] != raw:
        pytest.fail("Membership items must be slotted adapter-compatible dataclasses")


def test_all_members_keeps_repeated_user_paths_as_distinct_observations():
    first_raw = {
        "id": "membership",
        "userId": "same-user",
        "tenantId": "user-tenant",
        "@microsoft.graph.originalSourceMembershipUrl": (
            "https://graph.microsoft.com/v1.0/teams/source-a/members/member"
        ),
    }
    second_raw = {
        "id": "membership",
        "userId": "same-user",
        "tenantId": "user-tenant",
        "@microsoft.graph.originalSourceMembershipUrl": (
            "https://graph.microsoft.com/v1.0/teams/source-b/members/member"
        ),
    }
    first = TeamsChannelMembershipItem.from_all_members(
        first_raw,
        host_team_id="host-team",
        channel_id="channel",
    )
    second = TeamsChannelMembershipItem.from_all_members(
        second_raw,
        host_team_id="host-team",
        channel_id="channel",
    )
    if first.membership_source != "all" or second.membership_source != "all":
        pytest.fail("allMembers provenance was lost")
    if first.user_id != second.user_id or first.membership_id != second.membership_id:
        pytest.fail("Fixture no longer exercises repeated provider identity")
    if first.original_source_membership_url == second.original_source_membership_url:
        pytest.fail("Repeated user membership paths were collapsed")
    if first.raw is not first_raw or second.raw is not second_raw:
        pytest.fail("Repeated membership provider objects must remain independent")


def test_direct_and_all_membership_sources_remain_distinct():
    raw = {
        "id": "membership",
        "userId": "user",
        "@microsoft.graph.originalSourceMembershipUrl": "source",
    }
    direct = TeamsChannelMembershipItem.from_direct(
        raw,
        host_team_id="host-team",
        channel_id="channel",
    )
    all_member = TeamsChannelMembershipItem.from_all_members(
        raw,
        host_team_id="host-team",
        channel_id="channel",
    )
    if direct.membership_source != "direct" or all_member.membership_source != "all":
        pytest.fail("Direct/allMembers discovery paths were conflated")
    if direct.original_source_membership_url != "source":
        pytest.fail("Direct membership original source URL was lost")


@pytest.mark.parametrize("raw", [None, [], {}, {"id": ""}, {"id": False}])
def test_membership_parsers_reject_unstable_membership_identity(raw):
    with pytest.raises((TypeError, ValueError)):
        TeamsTeamMembershipItem.from_graph(raw, team_id="team")
    with pytest.raises((TypeError, ValueError)):
        TeamsChannelMembershipItem.from_all_members(
            raw,
            host_team_id="team",
            channel_id="channel",
        )


def test_membership_parsers_reject_missing_parent_identity():
    with pytest.raises(ValueError):
        TeamsTeamMembershipItem.from_graph({"id": "member"}, team_id="")
    with pytest.raises(ValueError):
        TeamsChannelMembershipItem.from_direct(
            {"id": "member"},
            host_team_id="",
            channel_id="channel",
        )
    with pytest.raises(ValueError):
        TeamsChannelMembershipItem.from_direct(
            {"id": "member"},
            host_team_id="team",
            channel_id="",
        )


def test_membership_provider_accepts_consumer_subclass_fields():
    consumer = make_dataclass(
        "ObservedMembership",
        [("evidence_id", str), ("run_id", str)],
        bases=(TeamsChannelMembershipItem,),
        slots=True,
    )
    raw = {
        "id": "membership",
        "userId": False,
        "@microsoft.graph.originalSourceMembershipUrl": None,
    }
    item = consumer.from_all_members(
        raw,
        host_team_id="team",
        channel_id="channel",
        evidence_id="evidence",
        run_id="run",
    )
    if item.user_id is not False or item.raw is not raw:
        pytest.fail("Provider values were schema-normalized in consumer subclass")
    if (item.evidence_id, item.run_id) != ("evidence", "run"):
        pytest.fail("Consumer subclass fields were not forwarded")


def test_membership_provider_types_exclude_application_provenance():
    forbidden = {"observed_at", "evidence_id", "run_id", "source_id"}
    for provider in (TeamsTeamMembershipItem, TeamsChannelMembershipItem):
        if forbidden.intersection(field.name for field in fields(provider)):
            pytest.fail("Application provenance leaked into membership provider")
