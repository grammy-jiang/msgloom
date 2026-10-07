"""Concrete complete-T2 Microsoft Teams channel discovery spider."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, ClassVar

from scrapy import Request
from twisted.python.failure import Failure

from message_ingest.items.microsoft.teams.coverage import TeamsCoverageItem
from message_ingest.items.microsoft.teams.topology import TeamsChannelItem
from message_ingest.spiders.microsoft.teams._base import MicrosoftTeamsBaseSpider
from microsoft_graph.spiders.teams.channel_composition import (
    MicrosoftTeamsChannelCompositionSpider,
)

from ._channel_content import ChannelContentMixin
from ._channel_messages import ChannelMessagesMixin
from ._channel_profile import CHANNEL_GRAPH_PERMISSIONS
from ._channel_topology import ChannelTopologyMixin


class MicrosoftTeamsChannelDiscoverSpider(
    MicrosoftTeamsChannelCompositionSpider,
    MicrosoftTeamsBaseSpider,
    ChannelTopologyMixin,
    ChannelMessagesMixin,
    ChannelContentMixin,
):
    """
    Discover complete T2 team/channel topology and Graph-visible messages.

    Traversal stays in named application callbacks. Provider helpers own paths
    and parsing, the shared Teams base owns transport/evidence/integrity policy,
    and the Teams pipeline owns durable semantic writes.
    """

    name = "microsoft_teams_channel_discover"
    graph_permissions: ClassVar[tuple[str, ...]] = CHANNEL_GRAPH_PERMISSIONS
    failure_context_keys = (
        "team_id",
        "host_team_id",
        "receiving_team_id",
        "channel_id",
        "root_message_id",
        "hosted_content_id",
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize bounded context guards; JOBDIR resume is rejected by base."""
        super().__init__(*args, **kwargs)
        self._channel_detail_requests: set[tuple[str, str | None]] = set()
        self._hosted_request_keys: set[tuple[str, tuple[str, ...], str]] = set()

    async def start(self):
        """Start from associated-team completeness and direct membership inventory."""
        for path, callback, purpose in (
            (
                self.associated_teams_path(),
                self.parse_associated_teams,
                "teams-associated-teams",
            ),
            (
                self.joined_teams_path(),
                self.parse_joined_teams,
                "teams-joined-teams",
            ),
        ):
            yield self._teams_request(
                path,
                callback=callback,
                purpose=purpose,
            )

    def _teams_request(
        self,
        path: str,
        *,
        callback: Any,
        purpose: str,
        cb_kwargs: dict[str, Any] | None = None,
        prefer: str | None = None,
        errback: Any = None,
        dont_filter: bool = False,
    ) -> Request:
        """Build one fresh provider-path request with explicit failure purpose."""
        request = self.graph_request(
            path,
            callback=callback,
            errback=errback or self.errback,
            operation=purpose,
            cb_kwargs={**(cb_kwargs or {}), "purpose": purpose},
            prefer=prefer,
        )
        if dont_filter:
            return request.replace(dont_filter=True)
        return request

    def _teams_continuation(
        self,
        next_link: str,
        *,
        callback: Any,
        purpose: str,
        cb_kwargs: dict[str, Any] | None = None,
        prefer: str | None = None,
        errback: Any = None,
        dont_filter: bool = False,
    ) -> Request:
        """Replay one opaque continuation with unchanged callback context."""
        request = self.continuation_request(
            next_link,
            callback=callback,
            errback=errback or self.errback,
            operation=purpose,
            cb_kwargs={**(cb_kwargs or {}), "purpose": purpose},
            prefer=prefer,
        )
        if dont_filter:
            return request.replace(dont_filter=True)
        return request

    def _channel_followups(
        self: Any,
        item: TeamsChannelItem,
        *,
        detail_path: str | None,
    ) -> Iterator[Request]:
        detail_purpose = "teams-channel-detail"
        detail = self._teams_request(
            detail_path or self.channel_path(item.host_team_id, item.channel_id),
            callback=self.parse_channel_detail,
            errback=self.hydration_errback,
            purpose=detail_purpose,
            cb_kwargs={
                "host_team_id": item.host_team_id,
                "host_tenant_id": item.host_tenant_id,
                "receiving_team_id": item.receiving_team_id,
                "receiving_tenant_id": item.receiving_tenant_id,
                "channel_id": item.channel_id,
                "original_resource_link": item.original_resource_link,
                "limitation_scope_kind": "channel",
                "limitation_scope": (
                    (item.host_team_id, item.channel_id, item.receiving_team_id)
                    if item.receiving_team_id is not None
                    else (item.host_team_id, item.channel_id)
                ),
            },
            prefer=self.representation_prefer,
        )
        detail_key = (detail.url, item.receiving_team_id)
        if detail_key not in self._channel_detail_requests:
            self._channel_detail_requests.add(detail_key)
            yield detail.replace(dont_filter=True)

        if item.membership_type == "shared":
            yield self._teams_request(
                self.shared_with_teams_path(item.host_team_id, item.channel_id),
                callback=self.parse_shared_with_teams,
                purpose="teams-shared-with-teams",
                cb_kwargs={
                    "host_team_id": item.host_team_id,
                    "host_tenant_id": item.host_tenant_id,
                    "channel_id": item.channel_id,
                },
            )
        yield self._teams_request(
            self.channel_members_path(item.host_team_id, item.channel_id),
            callback=self.parse_channel_members,
            purpose="teams-channel-members",
            cb_kwargs={
                "host_team_id": item.host_team_id,
                "channel_id": item.channel_id,
                "membership_source": "direct",
            },
        )
        yield self._teams_request(
            self.all_channel_members_path(item.host_team_id, item.channel_id),
            callback=self.parse_channel_members,
            purpose="teams-channel-all-members",
            cb_kwargs={
                "host_team_id": item.host_team_id,
                "channel_id": item.channel_id,
                "membership_source": "all",
            },
        )
        purpose = "teams-channel-root-messages"
        yield self.root_messages_request(
            item.host_team_id,
            item.channel_id,
            callback=self.parse_root_messages,
            errback=self.errback,
            cb_kwargs={
                "purpose": purpose,
                "host_team_id": item.host_team_id,
                "channel_id": item.channel_id,
            },
            operation=purpose,
        )

    def _inherited_teams_errback(self, failure: Failure) -> Iterator[Any]:
        """Delegate terminal failure evidence/integrity to the shared Graph base."""
        return MicrosoftTeamsBaseSpider.errback(self, failure)

    def hydration_errback(self, failure: Failure) -> Iterator[Any]:
        """Retain inherited terminal failure evidence plus explicit detail gap."""
        request = self._failure_request(failure)
        outputs = self._inherited_teams_errback(failure)
        evidence = next(outputs)
        yield evidence
        yield from outputs

        scope_kind = request.cb_kwargs.get("limitation_scope_kind")
        scope = request.cb_kwargs.get("limitation_scope")
        if not isinstance(scope_kind, str) or not isinstance(scope, tuple):
            raise TypeError("Teams hydration failure lacks limitation scope")
        if any(not isinstance(value, str) or not value for value in scope):
            raise ValueError("Teams hydration limitation scope must be explicit")
        yield TeamsCoverageItem(
            scope_kind=scope_kind,
            scope=scope,
            fact_kind="detail-hydration",
            status="unavailable",
            history_incomplete=True,
            details={
                "purpose": request.cb_kwargs.get("purpose"),
                "status_code": evidence.response_status,
            },
            **self._teams_provenance(evidence),
        )


__all__ = ["MicrosoftTeamsChannelDiscoverSpider"]
