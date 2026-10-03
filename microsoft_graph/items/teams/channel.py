"""Provider-only Microsoft Teams team and channel topology projections."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Self

from microsoft_graph.protocol import graph_object

TeamRepresentation = Literal["associated", "joined", "detail"]
ChannelRepresentation = Literal["allChannels", "incomingChannels", "detail"]


def _resource(resource: dict[str, Any], context: str) -> dict[str, Any]:
    """Require one provider object with a stable non-empty resource ID."""
    raw = graph_object(resource, context=context)
    resource_id = raw.get("id")
    if not isinstance(resource_id, str) or not resource_id:
        raise ValueError(f"{context} requires a non-empty id")
    return raw


def _context_id(value: str | None, *, name: str, required: bool) -> None:
    """Validate contextual opaque IDs without normalizing provider values."""
    if value is None and not required:
        return
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")


@dataclass(slots=True)
class TeamsTeamItem:
    """
    Team discovery/detail representation with unchanged provider JSON.

    Discovery observations stay explicitly partial until a separate detail
    response is observed. Consumers may replace the default limitation text
    with a concrete provider limitation after a failed hydration attempt.
    """

    team_id: str
    representation: TeamRepresentation
    detail_complete: bool
    detail_limitation: str | None
    raw: dict[str, Any]
    display_name: str | None = field(init=False)
    description: str | None = field(init=False)
    tenant_id: str | None = field(init=False)
    web_url: str | None = field(init=False)
    created_date_time: str | None = field(init=False)

    def __post_init__(self) -> None:
        """Project provider fields while enforcing representation provenance."""
        if self.representation not in {"associated", "joined", "detail"}:
            raise ValueError("Unknown Teams team representation")
        if self.detail_complete:
            if self.representation != "detail" or self.detail_limitation is not None:
                raise ValueError(
                    "Complete team detail must come from a detail response"
                )
        elif not isinstance(self.detail_limitation, str) or not self.detail_limitation:
            raise ValueError("Partial team representations require a detail limitation")
        self.display_name = self.raw.get("displayName")
        self.description = self.raw.get("description")
        self.tenant_id = self.raw.get("tenantId")
        self.web_url = self.raw.get("webUrl")
        self.created_date_time = self.raw.get("createdDateTime")

    @classmethod
    def from_associated(
        cls,
        resource: dict[str, Any],
        *,
        detail_limitation: str = (
            "associatedTeams is discovery-only; full team detail is not observed"
        ),
        **kwargs: Any,
    ) -> Self:
        """Parse an associated-team discovery observation."""
        raw = _resource(resource, "Teams associated-team entry")
        return cls(
            team_id=raw["id"],
            representation="associated",
            detail_complete=False,
            detail_limitation=detail_limitation,
            raw=raw,
            **kwargs,
        )

    @classmethod
    def from_joined(
        cls,
        resource: dict[str, Any],
        *,
        detail_limitation: str = (
            "joinedTeams is discovery-only; full team detail is not observed"
        ),
        **kwargs: Any,
    ) -> Self:
        """Parse a direct-team discovery observation."""
        raw = _resource(resource, "Teams joined-team entry")
        return cls(
            team_id=raw["id"],
            representation="joined",
            detail_complete=False,
            detail_limitation=detail_limitation,
            raw=raw,
            **kwargs,
        )

    @classmethod
    def from_detail(cls, resource: dict[str, Any], **kwargs: Any) -> Self:
        """Parse a separately retrieved full team-detail observation."""
        raw = _resource(resource, "Teams team detail")
        return cls(
            team_id=raw["id"],
            representation="detail",
            detail_complete=True,
            detail_limitation=None,
            raw=raw,
            **kwargs,
        )


@dataclass(slots=True)
class TeamsChannelItem:
    """
    Channel representation with explicit host and receiving-team context.

    The provider never assumes the team used for discovery is the content host.
    Incoming/shared discovery can therefore retain both identities and tenants.
    List projections remain partial even when every selected field is present.
    """

    channel_id: str
    host_team_id: str
    host_tenant_id: str | None
    receiving_team_id: str | None
    receiving_tenant_id: str | None
    representation: ChannelRepresentation
    detail_complete: bool
    detail_limitation: str | None
    original_resource_link: str | None
    raw: dict[str, Any]
    created_date_time: str | None = field(init=False)
    display_name: str | None = field(init=False)
    description: str | None = field(init=False)
    is_archived: bool | None = field(init=False)
    is_favorite_by_default: bool | None = field(init=False)
    layout_type: str | None = field(init=False)
    membership_type: str | None = field(init=False)
    migration_mode: str | None = field(init=False)
    original_created_date_time: str | None = field(init=False)
    tenant_id: str | None = field(init=False)
    web_url: str | None = field(init=False)

    def __post_init__(self) -> None:
        """Validate context and retain projected values without coercion."""
        _context_id(self.host_team_id, name="host team ID", required=True)
        _context_id(self.host_tenant_id, name="host tenant ID", required=False)
        _context_id(self.receiving_team_id, name="receiving team ID", required=False)
        _context_id(
            self.receiving_tenant_id,
            name="receiving tenant ID",
            required=False,
        )
        if self.representation not in {"allChannels", "incomingChannels", "detail"}:
            raise ValueError("Unknown Teams channel representation")
        if self.representation == "incomingChannels" and self.receiving_team_id is None:
            raise ValueError("Incoming channel discovery requires a receiving team")
        if self.detail_complete:
            if self.representation != "detail" or self.detail_limitation is not None:
                raise ValueError(
                    "Complete channel detail must come from detail response"
                )
        elif not isinstance(self.detail_limitation, str) or not self.detail_limitation:
            raise ValueError("Channel discovery requires a detail limitation")
        mapping = {
            "created_date_time": "createdDateTime",
            "display_name": "displayName",
            "description": "description",
            "is_archived": "isArchived",
            "is_favorite_by_default": "isFavoriteByDefault",
            "layout_type": "layoutType",
            "membership_type": "membershipType",
            "migration_mode": "migrationMode",
            "original_created_date_time": "originalCreatedDateTime",
            "tenant_id": "tenantId",
            "web_url": "webUrl",
        }
        for attribute, provider_name in mapping.items():
            setattr(self, attribute, self.raw.get(provider_name))

    @classmethod
    def from_all_channels(
        cls,
        resource: dict[str, Any],
        *,
        host_team_id: str,
        host_tenant_id: str | None = None,
        receiving_team_id: str | None = None,
        receiving_tenant_id: str | None = None,
        detail_limitation: str = (
            "allChannels is a discovery projection; full channel detail is not observed"
        ),
        original_resource_link: str | None = None,
        **kwargs: Any,
    ) -> Self:
        """Parse one allChannels discovery observation."""
        raw = _resource(resource, "Teams allChannels entry")
        link = (
            raw.get("@odata.id")
            if original_resource_link is None
            else original_resource_link
        )
        return cls(
            channel_id=raw["id"],
            host_team_id=host_team_id,
            host_tenant_id=host_tenant_id,
            receiving_team_id=receiving_team_id,
            receiving_tenant_id=receiving_tenant_id,
            representation="allChannels",
            detail_complete=False,
            detail_limitation=detail_limitation,
            original_resource_link=link,
            raw=raw,
            **kwargs,
        )

    @classmethod
    def from_incoming(
        cls,
        resource: dict[str, Any],
        *,
        host_team_id: str,
        receiving_team_id: str,
        host_tenant_id: str | None = None,
        receiving_tenant_id: str | None = None,
        detail_limitation: str = (
            "incomingChannels is a discovery projection; full channel detail is not observed"
        ),
        original_resource_link: str | None = None,
        **kwargs: Any,
    ) -> Self:
        """Parse incoming shared-channel topology without conflating team roles."""
        raw = _resource(resource, "Teams incomingChannels entry")
        link = (
            raw.get("@odata.id")
            if original_resource_link is None
            else original_resource_link
        )
        return cls(
            channel_id=raw["id"],
            host_team_id=host_team_id,
            host_tenant_id=host_tenant_id,
            receiving_team_id=receiving_team_id,
            receiving_tenant_id=receiving_tenant_id,
            representation="incomingChannels",
            detail_complete=False,
            detail_limitation=detail_limitation,
            original_resource_link=link,
            raw=raw,
            **kwargs,
        )

    @classmethod
    def from_detail(
        cls,
        resource: dict[str, Any],
        *,
        host_team_id: str,
        host_tenant_id: str | None = None,
        receiving_team_id: str | None = None,
        receiving_tenant_id: str | None = None,
        original_resource_link: str | None = None,
        **kwargs: Any,
    ) -> Self:
        """Parse separately retrieved channel detail with caller topology context."""
        raw = _resource(resource, "Teams channel detail")
        return cls(
            channel_id=raw["id"],
            host_team_id=host_team_id,
            host_tenant_id=host_tenant_id,
            receiving_team_id=receiving_team_id,
            receiving_tenant_id=receiving_tenant_id,
            representation="detail",
            detail_complete=True,
            detail_limitation=None,
            original_resource_link=original_resource_link,
            raw=raw,
            **kwargs,
        )


@dataclass(slots=True)
class TeamsSharedWithTeamItem:
    """One observed shared-channel relation from host to receiving team."""

    host_team_id: str
    host_tenant_id: str | None
    channel_id: str
    receiving_team_id: str
    raw: dict[str, Any]
    receiving_tenant_id: str | None = field(init=False)
    display_name: str | None = field(init=False)

    def __post_init__(self) -> None:
        """Validate host context and project receiving-team provider fields."""
        _context_id(self.host_team_id, name="host team ID", required=True)
        _context_id(self.host_tenant_id, name="host tenant ID", required=False)
        _context_id(self.channel_id, name="channel ID", required=True)
        self.receiving_tenant_id = self.raw.get("tenantId")
        self.display_name = self.raw.get("displayName")

    @classmethod
    def from_graph(
        cls,
        resource: dict[str, Any],
        *,
        host_team_id: str,
        channel_id: str,
        host_tenant_id: str | None = None,
        **kwargs: Any,
    ) -> Self:
        """Parse one sharedWithTeams relation without team deduplication."""
        raw = _resource(resource, "Teams sharedWithTeams entry")
        return cls(
            host_team_id=host_team_id,
            host_tenant_id=host_tenant_id,
            channel_id=channel_id,
            receiving_team_id=raw["id"],
            raw=raw,
            **kwargs,
        )


__all__ = [
    "ChannelRepresentation",
    "TeamRepresentation",
    "TeamsChannelItem",
    "TeamsSharedWithTeamItem",
    "TeamsTeamItem",
]
