"""Evidence-first Teams channel topology traversal callbacks."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Literal

from scrapy import Request
from scrapy.http import TextResponse

from message_ingest.items.microsoft.teams.coverage import TeamsCoverageItem
from message_ingest.items.microsoft.teams.topology import (
    TeamsChannelItem,
    TeamsChannelMembershipItem,
    TeamsSharedWithTeamItem,
    TeamsTeamItem,
    TeamsTeamMembershipItem,
)
from microsoft_graph.protocol import GraphCollectionPage, graph_object

from ._channel_profile import CHANNEL_SELECT_FIELDS, TEAM_MEMBER_PAGE_SIZE

ChannelInventoryKind = Literal["allChannels", "incomingChannels"]
MembershipSource = Literal["direct", "all"]


class ChannelTopologyMixin:
    """Compose provider topology parsers with application evidence and traversal."""

    def parse_associated_teams(
        self: Any,
        response: TextResponse,
        *,
        purpose: str,
    ) -> Iterator[Any]:
        """Persist associated-team inventory and schedule bounded hydration."""
        yield from self._parse_team_inventory(
            response,
            purpose=purpose,
            representation="associated",
            callback=self.parse_associated_teams,
        )

    def parse_joined_teams(
        self: Any,
        response: TextResponse,
        *,
        purpose: str,
    ) -> Iterator[Any]:
        """Persist direct-team inventory separately from associated discovery."""
        yield from self._parse_team_inventory(
            response,
            purpose=purpose,
            representation="joined",
            callback=self.parse_joined_teams,
        )

    def _parse_team_inventory(
        self: Any,
        response: TextResponse,
        *,
        purpose: str,
        representation: Literal["associated", "joined"],
        callback: Any,
    ) -> Iterator[Any]:
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        page = GraphCollectionPage.from_payload(
            response.json(),
            context=f"Teams {representation} team collection",
            validate_links=False,
        )
        provenance = self._teams_provenance(evidence)
        for resource in page.values:
            if representation == "associated":
                item = TeamsTeamItem.from_associated(resource, **provenance)
            else:
                item = TeamsTeamItem.from_joined(resource, **provenance)
            yield item
            yield from self._team_followups(item)

        if next_link := page.next_link:
            yield self._teams_continuation(
                next_link,
                callback=callback,
                purpose=purpose,
            )

    def _team_followups(self: Any, item: TeamsTeamItem) -> Iterator[Request]:
        team_id = item.team_id
        detail_purpose = "teams-team-detail"
        yield self._teams_request(
            self.team_path(team_id),
            callback=self.parse_team_detail,
            errback=self.hydration_errback,
            purpose=detail_purpose,
            cb_kwargs={
                "team_id": team_id,
                "limitation_scope_kind": "team",
                "limitation_scope": (team_id,),
            },
        )
        yield self._teams_request(
            self.all_channels_path(team_id, fields=CHANNEL_SELECT_FIELDS),
            callback=self.parse_all_channels,
            purpose="teams-all-channels",
            cb_kwargs={
                "inventory_team_id": team_id,
                "receiving_tenant_id": item.tenant_id,
            },
            prefer=self.representation_prefer,
        )
        yield self._teams_request(
            self.incoming_channels_path(team_id, fields=CHANNEL_SELECT_FIELDS),
            callback=self.parse_incoming_channels,
            purpose="teams-incoming-channels",
            cb_kwargs={
                "inventory_team_id": team_id,
                "receiving_tenant_id": item.tenant_id,
            },
            prefer=self.representation_prefer,
        )
        yield self._teams_request(
            self.team_members_path(team_id, page_size=TEAM_MEMBER_PAGE_SIZE),
            callback=self.parse_team_members,
            purpose="teams-team-members",
            cb_kwargs={"team_id": team_id},
        )

    def parse_team_detail(
        self: Any,
        response: TextResponse,
        *,
        purpose: str,
        team_id: str,
        **_context: Any,
    ) -> Iterator[Any]:
        """Persist a separate full team-detail observation."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        item = TeamsTeamItem.from_detail(
            response.json(),
            **self._teams_provenance(evidence),
        )
        if item.team_id != team_id:
            raise ValueError("Teams team detail ID differs from traversal scope")
        yield item

    def parse_team_members(
        self: Any,
        response: TextResponse,
        *,
        purpose: str,
        team_id: str,
    ) -> Iterator[Any]:
        """Persist every explicit team-membership page."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        page = GraphCollectionPage.from_payload(
            response.json(),
            context="Teams team members collection",
            validate_links=False,
        )
        provenance = self._teams_provenance(evidence)
        for resource in page.values:
            yield TeamsTeamMembershipItem.from_graph(
                resource,
                team_id=team_id,
                **provenance,
            )
        if next_link := page.next_link:
            yield self._teams_continuation(
                next_link,
                callback=self.parse_team_members,
                purpose=purpose,
                cb_kwargs={"team_id": team_id},
            )

    def parse_all_channels(
        self: Any,
        response: TextResponse,
        *,
        purpose: str,
        inventory_team_id: str,
        receiving_tenant_id: str | None,
    ) -> Iterator[Any]:
        """Persist allChannels entries, including incoming shared topology."""
        yield from self._parse_channel_inventory(
            response,
            purpose=purpose,
            inventory_kind="allChannels",
            inventory_team_id=inventory_team_id,
            receiving_tenant_id=receiving_tenant_id,
            callback=self.parse_all_channels,
        )

    def parse_incoming_channels(
        self: Any,
        response: TextResponse,
        *,
        purpose: str,
        inventory_team_id: str,
        receiving_tenant_id: str | None,
    ) -> Iterator[Any]:
        """Resolve only trusted incoming resource links before host traversal."""
        yield from self._parse_channel_inventory(
            response,
            purpose=purpose,
            inventory_kind="incomingChannels",
            inventory_team_id=inventory_team_id,
            receiving_tenant_id=receiving_tenant_id,
            callback=self.parse_incoming_channels,
        )

    def _parse_channel_inventory(
        self: Any,
        response: TextResponse,
        *,
        purpose: str,
        inventory_kind: ChannelInventoryKind,
        inventory_team_id: str,
        receiving_tenant_id: str | None,
        callback: Any,
    ) -> Iterator[Any]:
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        page = GraphCollectionPage.from_payload(
            response.json(),
            context=f"Teams {inventory_kind} collection",
            validate_links=False,
        )
        provenance = self._teams_provenance(evidence)
        for resource in page.values:
            raw = graph_object(resource, context=f"Teams {inventory_kind} entry")
            resource_link = raw.get("@odata.id")
            resolved = (
                self.resolve_trusted_channel_resource_link(resource_link)
                if isinstance(resource_link, str)
                else None
            )
            if inventory_kind == "incomingChannels" and resolved is None:
                channel_id = raw.get("id")
                if not isinstance(channel_id, str) or not channel_id:
                    raise ValueError("Teams incoming channel requires a non-empty id")
                yield TeamsCoverageItem(
                    scope_kind="channel-resource-link",
                    scope=(inventory_team_id, channel_id),
                    fact_kind="resource-link-resolution",
                    status="unresolved",
                    history_incomplete=True,
                    details={
                        "inventory_kind": inventory_kind,
                        "original_resource_link": resource_link,
                    },
                    **provenance,
                )
                continue

            if resolved is not None:
                if resolved.channel_id != raw.get("id"):
                    raise ValueError("Teams channel resource-link identity mismatch")
                host_team_id = resolved.team_id
                host_tenant_id = resolved.tenant_id
                receiving_team_id = inventory_team_id
                original_resource_link = resolved.raw
                detail_path = resolved.request_path
            else:
                host_team_id = inventory_team_id
                tenant_value = raw.get("tenantId")
                host_tenant_id = (
                    tenant_value
                    if isinstance(tenant_value, str)
                    else receiving_tenant_id
                )
                receiving_team_id = None
                original_resource_link = (
                    resource_link if isinstance(resource_link, str) else None
                )
                detail_path = None

            if inventory_kind == "incomingChannels":
                item = TeamsChannelItem.from_incoming(
                    raw,
                    host_team_id=host_team_id,
                    host_tenant_id=host_tenant_id,
                    receiving_team_id=inventory_team_id,
                    receiving_tenant_id=receiving_tenant_id,
                    original_resource_link=original_resource_link,
                    **provenance,
                )
            else:
                item = TeamsChannelItem.from_all_channels(
                    raw,
                    host_team_id=host_team_id,
                    host_tenant_id=host_tenant_id,
                    receiving_team_id=receiving_team_id,
                    receiving_tenant_id=receiving_tenant_id,
                    original_resource_link=original_resource_link,
                    **provenance,
                )
            yield item
            yield from self._channel_followups(item, detail_path=detail_path)

        if next_link := page.next_link:
            yield self._teams_continuation(
                next_link,
                callback=callback,
                purpose=purpose,
                cb_kwargs={
                    "inventory_team_id": inventory_team_id,
                    "receiving_tenant_id": receiving_tenant_id,
                },
                prefer=self.representation_prefer,
            )

    def parse_channel_detail(
        self: Any,
        response: TextResponse,
        *,
        purpose: str,
        host_team_id: str,
        host_tenant_id: str | None,
        receiving_team_id: str | None,
        receiving_tenant_id: str | None,
        channel_id: str,
        original_resource_link: str | None,
        **_context: Any,
    ) -> Iterator[Any]:
        """Persist hydrated channel detail under its exact receiving context."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        item = TeamsChannelItem.from_detail(
            response.json(),
            host_team_id=host_team_id,
            host_tenant_id=host_tenant_id,
            receiving_team_id=receiving_team_id,
            receiving_tenant_id=receiving_tenant_id,
            original_resource_link=original_resource_link,
            **self._teams_provenance(evidence),
        )
        if item.channel_id != channel_id:
            raise ValueError("Teams channel detail ID differs from traversal scope")
        yield item

    def parse_shared_with_teams(
        self: Any,
        response: TextResponse,
        *,
        purpose: str,
        host_team_id: str,
        host_tenant_id: str | None,
        channel_id: str,
    ) -> Iterator[Any]:
        """Persist every sharedWithTeams relation page."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        page = GraphCollectionPage.from_payload(
            response.json(),
            context="Teams sharedWithTeams collection",
            validate_links=False,
        )
        provenance = self._teams_provenance(evidence)
        for resource in page.values:
            yield TeamsSharedWithTeamItem.from_graph(
                resource,
                host_team_id=host_team_id,
                host_tenant_id=host_tenant_id,
                channel_id=channel_id,
                **provenance,
            )
        if next_link := page.next_link:
            yield self._teams_continuation(
                next_link,
                callback=self.parse_shared_with_teams,
                purpose=purpose,
                cb_kwargs={
                    "host_team_id": host_team_id,
                    "host_tenant_id": host_tenant_id,
                    "channel_id": channel_id,
                },
            )

    def parse_channel_members(
        self: Any,
        response: TextResponse,
        *,
        purpose: str,
        host_team_id: str,
        channel_id: str,
        membership_source: MembershipSource,
    ) -> Iterator[Any]:
        """Persist direct and allMembers paths without cross-path deduplication."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        page = GraphCollectionPage.from_payload(
            response.json(),
            context="Teams channel members collection",
            validate_links=False,
        )
        provenance = self._teams_provenance(evidence)
        for resource in page.values:
            if membership_source == "direct":
                item = TeamsChannelMembershipItem.from_direct(
                    resource,
                    host_team_id=host_team_id,
                    channel_id=channel_id,
                    **provenance,
                )
            elif membership_source == "all":
                item = TeamsChannelMembershipItem.from_all_members(
                    resource,
                    host_team_id=host_team_id,
                    channel_id=channel_id,
                    **provenance,
                )
            else:
                raise ValueError("Unknown Teams channel membership traversal source")
            yield item
        if next_link := page.next_link:
            yield self._teams_continuation(
                next_link,
                callback=self.parse_channel_members,
                purpose=purpose,
                cb_kwargs={
                    "host_team_id": host_team_id,
                    "channel_id": channel_id,
                    "membership_source": membership_source,
                },
            )
