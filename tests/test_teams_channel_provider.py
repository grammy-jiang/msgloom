"""Pin complete-T2 Teams channel paths and topology projections."""

import subprocess
import sys
from dataclasses import fields

import pytest
from itemadapter import ItemAdapter
from scrapy.settings import Settings

from microsoft_graph.items.teams.channel import (
    TeamsChannelItem,
    TeamsSharedWithTeamItem,
    TeamsTeamItem,
)
from microsoft_graph.spiders.teams.channel import MicrosoftTeamsChannelSpider
from microsoft_graph.spiders.teams.channel_paths import (
    CHANNEL_SELECT_FIELDS,
    resolve_trusted_channel_resource_link,
)

SCOPES = (
    "Team.ReadBasic.All",
    "Channel.ReadBasic.All",
    "ChannelMessage.Read.All",
    "TeamMember.Read.All",
    "ChannelMember.Read.All",
)
SELECT_QUERY = (
    "?%24select=id%2CcreatedDateTime%2CdisplayName%2Cdescription%2CisArchived"
    "%2CisFavoriteByDefault%2ClayoutType%2CmembershipType%2CmigrationMode"
    "%2CoriginalCreatedDateTime%2CtenantId%2CwebUrl"
)


def test_complete_t2_scope_and_frozen_team_channel_paths():
    spider = MicrosoftTeamsChannelSpider(name="provider")
    settings = Settings()
    spider.update_settings(settings)
    if spider.required_graph_permissions(settings) != SCOPES:
        pytest.fail("Complete T2 scope declaration changed")
    if settings.getlist("MS_GRAPH_SCOPES") != list(SCOPES):
        pytest.fail("Complete T2 defaults must request exactly the frozen scopes")
    if spider.associated_teams_path() != "/me/teamwork/associatedTeams":
        pytest.fail("Associated teams must remain the discovery root")
    if spider.joined_teams_path() != "/me/joinedTeams":
        pytest.fail("Direct teams must remain a separate inventory")
    if spider.team_path("team") != "/teams/team":
        pytest.fail("Team detail path changed")
    expected = {
        spider.all_channels_path("team"): "/teams/team/allChannels" + SELECT_QUERY,
        spider.incoming_channels_path("team"): (
            "/teams/team/incomingChannels" + SELECT_QUERY
        ),
        spider.channel_path("team", "channel"): (
            "/teams/team/channels/channel" + SELECT_QUERY
        ),
        spider.shared_with_teams_path("team", "channel"): (
            "/teams/team/channels/channel/sharedWithTeams"
        ),
        spider.team_members_path("team"): "/teams/team/members?%24top=999",
        spider.channel_members_path("team", "channel"): (
            "/teams/team/channels/channel/members?%24top=999"
        ),
        spider.all_channel_members_path("team", "channel"): (
            "/teams/team/channels/channel/allMembers"
        ),
        spider.root_messages_path("team", "channel"): (
            "/teams/team/channels/channel/messages?%24top=50"
        ),
        spider.root_message_path("team", "channel", "root"): (
            "/teams/team/channels/channel/messages/root"
        ),
        spider.replies_path("team", "channel", "root"): (
            "/teams/team/channels/channel/messages/root/replies?%24top=50"
        ),
        spider.reply_message_path("team", "channel", "root", "reply"): (
            "/teams/team/channels/channel/messages/root/replies/reply"
        ),
    }
    for actual, wanted in expected.items():
        if actual != wanted:
            pytest.fail(f"Frozen Teams path changed: {actual!r} != {wanted!r}")
    if CHANNEL_SELECT_FIELDS != (
        "id",
        "createdDateTime",
        "displayName",
        "description",
        "isArchived",
        "isFavoriteByDefault",
        "layoutType",
        "membershipType",
        "migrationMode",
        "originalCreatedDateTime",
        "tenantId",
        "webUrl",
    ):
        pytest.fail("Channel projection must exactly match the P0-C freeze")
    if spider.representation_prefer != "include-unknown-enum-members":
        pytest.fail("Unknown enum retention preference changed")


def test_targeted_and_hosted_paths_keep_root_reply_context_separate():
    spider = MicrosoftTeamsChannelSpider(name="provider")
    root_base = "/teams/team/channels/channel/messages/root"
    reply_base = root_base + "/replies/reply"
    cases = {
        spider.hosted_contents_path("team", "channel", "root"): (
            root_base + "/hostedContents"
        ),
        spider.hosted_content_path("team", "channel", "root", "hosted"): (
            root_base + "/hostedContents/hosted"
        ),
        spider.hosted_content_bytes_path("team", "channel", "root", "hosted"): (
            root_base + "/hostedContents/hosted/$value"
        ),
        spider.hosted_contents_path(
            "team", "channel", "root", reply_id="reply"
        ): reply_base + "/hostedContents",
        spider.hosted_content_path(
            "team",
            "channel",
            "root",
            "hosted",
            reply_id="reply",
        ): reply_base + "/hostedContents/hosted",
        spider.hosted_content_bytes_path(
            "team",
            "channel",
            "root",
            "hosted",
            reply_id="reply",
        ): reply_base + "/hostedContents/hosted/$value",
    }
    for actual, wanted in cases.items():
        if actual != wanted:
            pytest.fail(f"Hosted-content context changed: {actual!r} != {wanted!r}")
    if spider.hosted_consistency_level != "eventual":
        pytest.fail("Hosted item/byte consistency policy changed")
    if spider.hosted_bytes_accept != "application/octet-stream":
        pytest.fail("Hosted byte representation policy changed")


def test_opaque_ids_are_encoded_once_and_page_bounds_are_enforced():
    spider = MicrosoftTeamsChannelSpider(name="provider")
    team_id = "T/A+=%2f ?é"
    channel_id = "C/+%2F=#"
    root_id = "R/+%2f"
    expected = (
        "/teams/T%2FA%2B%3D%252f%20%3F%C3%A9/channels/"
        "C%2F%2B%252F%3D%23/messages/R%2F%2B%252f"
    )
    if spider.root_message_path(team_id, channel_id, root_id) != expected:
        pytest.fail("Opaque Teams IDs were not encoded exactly once")
    if spider.team_members_path("team", page_size=1) != "/teams/team/members?%24top=1":
        pytest.fail("Minimum team-member page size must be accepted")
    if spider.channel_members_path("team", "channel", page_size=999) != (
        "/teams/team/channels/channel/members?%24top=999"
    ):
        pytest.fail("Maximum channel-member page size must be accepted")
    if spider.root_messages_path("team", "channel", page_size=1) != (
        "/teams/team/channels/channel/messages?%24top=1"
    ):
        pytest.fail("Minimum message page size must be accepted")
    if spider.replies_path("team", "channel", "root", page_size=50) != (
        "/teams/team/channels/channel/messages/root/replies?%24top=50"
    ):
        pytest.fail("Maximum reply page size must be accepted")
    bad_calls = (
        lambda: spider.team_members_path("team", page_size=0),
        lambda: spider.team_members_path("team", page_size=1000),
        lambda: spider.channel_members_path("team", "channel", page_size=0),
        lambda: spider.root_messages_path("team", "channel", page_size=51),
        lambda: spider.replies_path("team", "channel", "root", page_size=0),
        lambda: spider.root_messages_path("team", "channel", page_size=True),
    )
    for call in bad_calls:
        with pytest.raises((TypeError, ValueError)):
            call()


def test_trusted_tenant_resource_link_rewrite_is_exact_and_query_preserving():
    link = (
        "https://graph.microsoft.com/v1.0/tenants/tenant%2fA/teams/"
        "team%2FB/channels/channel%2fc?x=a%2fb+%20&x=2"
    )
    resolved = resolve_trusted_channel_resource_link(link)
    if resolved is None:
        pytest.fail("Frozen trusted resource-link shape was rejected")
    if resolved.raw != link:
        pytest.fail("Original resource link must be retained unchanged")
    if resolved.request_path != (
        "/teams/team%2FB/channels/channel%2fc?x=a%2fb+%20&x=2"
    ):
        pytest.fail("Resource rewrite changed encoded path/query bytes")
    if (
        resolved.tenant_path_segment,
        resolved.team_path_segment,
        resolved.channel_path_segment,
    ) != ("tenant%2fA", "team%2FB", "channel%2fc"):
        pytest.fail("Trusted path segments were decoded or normalized")

    rejected = (
        "http://graph.microsoft.com/v1.0/tenants/t/teams/a/channels/c",
        "https://evil.example/v1.0/tenants/t/teams/a/channels/c",
        "https://user@graph.microsoft.com/v1.0/tenants/t/teams/a/channels/c",
        "https://graph.microsoft.com:443/v1.0/tenants/t/teams/a/channels/c",
        "https://graph.microsoft.com/v1.0/tenants/t/teams/a/channels/c#fragment",
        "https://graph.microsoft.com/beta/tenants/t/teams/a/channels/c",
        "https://graph.microsoft.com/v1.0/teams/a/channels/c",
        "https://graph.microsoft.com/v1.0/tenants/t/teams/a/channels/c/messages",
        "https://graph.microsoft.com/v1.0/tenants//teams/a/channels/c",
        "https://[invalid]/v1.0/tenants/t/teams/a/channels/c",
    )
    for value in rejected:
        if resolve_trusted_channel_resource_link(value) is not None:
            pytest.fail(f"Untrusted resource link was accepted: {value!r}")


def test_opaque_next_link_uses_existing_continuation_primitive_only():
    spider = MicrosoftTeamsChannelSpider(name="provider")
    next_link = (
        "https://graph.microsoft.com/v1.0/teams/t/allChannels?"
        "%24skiptoken=a%2fb+%20&x=1&x=2"
    )
    request = spider.continuation_request(
        next_link,
        callback=spider.parse,
        prefer=spider.representation_prefer,
    )
    if request.url != next_link:
        pytest.fail("Continuation URL was normalized instead of replayed verbatim")
    if request.meta.get("verbatim_url") is not True:
        pytest.fail("Continuation request must retain the Graph verbatim marker")
    if resolve_trusted_channel_resource_link(next_link) is not None:
        pytest.fail("Resource-link workaround must never accept continuation URLs")


def test_team_representations_keep_discovery_and_detail_observations_distinct():
    raw = {
        "id": "team",
        "displayName": "",
        "description": False,
        "tenantId": "",
        "webUrl": "",
        "createdDateTime": None,
        "future": {"flags": [0, False, ""]},
    }
    associated = TeamsTeamItem.from_associated(
        raw, detail_limitation="detail GET denied for this observation"
    )
    joined = TeamsTeamItem.from_joined(raw)
    detail = TeamsTeamItem.from_detail(raw)
    if associated.raw is not raw or detail.raw is not raw:
        pytest.fail("Team parser copied or replaced provider JSON")
    if associated.detail_complete or joined.detail_complete:
        pytest.fail("Discovery team representations must remain explicitly partial")
    if associated.detail_limitation != "detail GET denied for this observation":
        pytest.fail("Concrete partial-detail limitation was not preserved")
    if not detail.detail_complete or detail.detail_limitation is not None:
        pytest.fail("Full team detail state was not preserved separately")
    if (associated.display_name, associated.description, associated.tenant_id) != (
        "",
        False,
        "",
    ):
        pytest.fail("Falsey team provider fields were normalized")


def test_channel_topology_preserves_host_receiving_tenants_and_resource_link():
    resource_link = (
        "https://graph.microsoft.com/v1.0/tenants/host-tenant/"
        "teams/host-team/channels/channel"
    )
    raw = {
        "id": "channel",
        "@odata.id": resource_link,
        "createdDateTime": "",
        "displayName": "",
        "description": False,
        "isArchived": False,
        "isFavoriteByDefault": False,
        "layoutType": None,
        "membershipType": "shared",
        "migrationMode": "",
        "originalCreatedDateTime": None,
        "tenantId": "host-tenant",
        "webUrl": "",
        "future": [],
    }
    incoming = TeamsChannelItem.from_incoming(
        raw,
        host_team_id="host-team",
        host_tenant_id="host-tenant",
        receiving_team_id="receiving-team",
        receiving_tenant_id="receiving-tenant",
    )
    detail = TeamsChannelItem.from_detail(
        raw,
        host_team_id="host-team",
        host_tenant_id="host-tenant",
        receiving_team_id="receiving-team",
        receiving_tenant_id="receiving-tenant",
        original_resource_link=resource_link,
    )
    if incoming.raw is not raw or incoming.original_resource_link != resource_link:
        pytest.fail("Incoming channel resource link/raw representation was lost")
    if (
        incoming.host_team_id,
        incoming.host_tenant_id,
        incoming.receiving_team_id,
        incoming.receiving_tenant_id,
    ) != ("host-team", "host-tenant", "receiving-team", "receiving-tenant"):
        pytest.fail("Host and receiving topology contexts were conflated")
    if incoming.detail_complete or incoming.layout_type is not None:
        pytest.fail("Discovery projection must not masquerade as full detail")
    if not detail.detail_complete or detail.original_resource_link != resource_link:
        pytest.fail("Detail hydration must remain a separate observation")
    if (
        incoming.display_name,
        incoming.description,
        incoming.is_archived,
        incoming.migration_mode,
        incoming.web_url,
    ) != ("", False, False, "", ""):
        pytest.fail("Falsey channel fields were normalized")
    if hasattr(incoming, "__dict__") or ItemAdapter(incoming).asdict()["raw"] != raw:
        pytest.fail("Channel items must be slotted adapter-compatible dataclasses")


def test_shared_with_relation_preserves_host_and_receiving_tenant_identity():
    raw = {
        "id": "receiving-team",
        "tenantId": "receiving-tenant",
        "displayName": "",
        "future": {"unknown": False},
    }
    item = TeamsSharedWithTeamItem.from_graph(
        raw,
        host_team_id="host-team",
        host_tenant_id="host-tenant",
        channel_id="channel",
    )
    if item.raw is not raw:
        pytest.fail("sharedWithTeams raw relation was copied")
    if (
        item.host_team_id,
        item.host_tenant_id,
        item.channel_id,
        item.receiving_team_id,
        item.receiving_tenant_id,
        item.display_name,
    ) != (
        "host-team",
        "host-tenant",
        "channel",
        "receiving-team",
        "receiving-tenant",
        "",
    ):
        pytest.fail("Shared-channel relation identity or falsey values changed")


@pytest.mark.parametrize(
    "factory,args",
    [
        (TeamsTeamItem.from_associated, ({},)),
        (TeamsTeamItem.from_detail, ({"id": ""},)),
    ],
)
def test_team_parser_rejects_unstable_identity(factory, args):
    with pytest.raises((TypeError, ValueError)):
        factory(*args)


def test_channel_parser_requires_explicit_topology_context():
    with pytest.raises(ValueError):
        TeamsChannelItem.from_incoming(
            {"id": "channel"},
            host_team_id="host",
            receiving_team_id="",
        )
    with pytest.raises(ValueError):
        TeamsChannelItem.from_all_channels({"id": "channel"}, host_team_id="")


def test_provider_modules_import_without_application_or_database_layers():
    code = """
import importlib.abc
import sys
class ForbidApplication(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"message_ingest", "msgloom", "sqlalchemy"}:
            raise ImportError(f"Forbidden dependency: {fullname}")
sys.meta_path.insert(0, ForbidApplication())
from microsoft_graph.items.teams.channel import TeamsChannelItem, TeamsTeamItem
from microsoft_graph.items.teams.membership import (
    TeamsChannelMembershipItem, TeamsTeamMembershipItem,
)
from microsoft_graph.spiders.teams.channel import MicrosoftTeamsChannelSpider
spider = MicrosoftTeamsChannelSpider(name="standalone")
spider.graph_request(spider.associated_teams_path())
TeamsTeamItem.from_associated({"id": "team"})
TeamsChannelItem.from_all_channels({"id": "channel"}, host_team_id="team")
TeamsTeamMembershipItem.from_graph({"id": "member"}, team_id="team")
TeamsChannelMembershipItem.from_all_members(
    {"id": "member"}, host_team_id="team", channel_id="channel"
)
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if result.returncode:
        pytest.fail(result.stderr)


def test_provider_dataclasses_do_not_embed_application_provenance():
    forbidden = {"observed_at", "evidence_id", "run_id", "source_id"}
    for provider in (TeamsTeamItem, TeamsChannelItem, TeamsSharedWithTeamItem):
        if forbidden.intersection(field.name for field in fields(provider)):
            pytest.fail("Application provenance leaked into Teams provider items")
