"""Compose Teams channel topology with common scoped message/content helpers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from scrapy import Request

from microsoft_graph.items.teams.content import (
    TeamsHostedContentItem,
    parse_hosted_contents,
)
from microsoft_graph.items.teams.message import TeamsMessageItem
from microsoft_graph.protocol import GraphObjectTypeError
from microsoft_graph.protocol.teams import TeamsMessageIdentity, TeamsMessageLocation

from .channel import MicrosoftTeamsChannelSpider

Callback = Callable[..., Any]


def _channel_message_parts(
    identity: TeamsMessageIdentity,
) -> tuple[str, str, str, str | None]:
    """Return host-team/channel/root/reply path parts for a channel identity."""
    if not isinstance(identity, TeamsMessageIdentity):
        raise TypeError("message_identity must be a TeamsMessageIdentity")
    if identity.location is TeamsMessageLocation.CHAT:
        raise ValueError("Channel composition requires a channel message identity")

    team_id = identity.team_id
    channel_id = identity.channel_id
    if team_id is None or channel_id is None:
        raise ValueError("Channel message identity is missing channel scope")

    if identity.location is TeamsMessageLocation.CHANNEL_ROOT:
        return team_id, channel_id, identity.message_id, None

    root_message_id = identity.root_message_id
    if root_message_id is None:
        raise ValueError("Channel reply identity is missing its root message ID")
    return team_id, channel_id, root_message_id, identity.message_id


def _channel_collection(resources: Any, **scope: str) -> None:
    """Validate collection shape and path scope even when no messages exist."""
    if not isinstance(resources, list):
        raise GraphObjectTypeError("Teams channel messages must be a JSON array")
    for name, value in scope.items():
        if not isinstance(value, str) or not value:
            raise ValueError(f"Teams channel collection requires a non-empty {name}")


def parse_channel_root_messages(
    resources: list[Any],
    *,
    host_team_id: str,
    channel_id: str,
    item_type: type[TeamsMessageItem] = TeamsMessageItem,
    **item_kwargs: Any,
) -> tuple[TeamsMessageItem, ...]:
    """
    Parse root-message collection values under the channel content host.

    Envelope and continuation validation remain owned by GraphCollectionPage.
    """
    _channel_collection(resources, host_team_id=host_team_id, channel_id=channel_id)
    return tuple(
        item_type.from_channel_root_graph(
            resource,
            team_id=host_team_id,
            channel_id=channel_id,
            **item_kwargs,
        )
        for resource in resources
    )


def parse_channel_replies(
    resources: list[Any],
    *,
    host_team_id: str,
    channel_id: str,
    root_message_id: str,
    item_type: type[TeamsMessageItem] = TeamsMessageItem,
    **item_kwargs: Any,
) -> tuple[TeamsMessageItem, ...]:
    """Parse reply collection values under their traversal-path root scope."""
    _channel_collection(
        resources,
        host_team_id=host_team_id,
        channel_id=channel_id,
        root_message_id=root_message_id,
    )
    return tuple(
        item_type.from_channel_reply_graph(
            resource,
            team_id=host_team_id,
            channel_id=channel_id,
            root_message_id=root_message_id,
            **item_kwargs,
        )
        for resource in resources
    )


def parse_channel_hosted_contents(
    resources: list[Any],
    *,
    message_identity: TeamsMessageIdentity,
    item_type: type[TeamsHostedContentItem] = TeamsHostedContentItem,
    **item_kwargs: Any,
) -> tuple[TeamsHostedContentItem, ...]:
    """
    Parse hosted metadata under one channel root/reply identity.

    The common hosted-content parser owns collection-value validation. Consumer
    subclasses are then constructed from the same retained raw objects so
    application provenance can be supplied without changing provider models.
    """
    _channel_message_parts(message_identity)
    parsed = parse_hosted_contents(
        resources,
        message_identity=message_identity,
    )
    if item_type is TeamsHostedContentItem and not item_kwargs:
        return parsed
    return tuple(
        item_type.from_graph(
            item.raw,
            message_identity=message_identity,
            **item_kwargs,
        )
        for item in parsed
    )


class MicrosoftTeamsChannelCompositionSpider(MicrosoftTeamsChannelSpider):
    """
    Build channel message/content Requests without owning response callbacks.

    Application spiders supply named callbacks, errbacks, and callback context.
    This layer never consumes a Response or emits application items.
    """

    def root_messages_request(
        self,
        host_team_id: str,
        channel_id: str,
        *,
        callback: Callback,
        errback: Callback,
        cb_kwargs: dict[str, Any] | None = None,
        page_size: int | None = None,
        operation: str = "teams-channel-root-messages",
    ) -> Request:
        """Build one enum-aware channel-root collection request."""
        return self.graph_request(
            self.root_messages_path(
                host_team_id,
                channel_id,
                page_size=page_size,
            ),
            callback=callback,
            errback=errback,
            operation=operation,
            cb_kwargs=cb_kwargs,
            prefer=self.representation_prefer,
        )

    def replies_request(
        self,
        host_team_id: str,
        channel_id: str,
        root_message_id: str,
        *,
        callback: Callback,
        errback: Callback,
        cb_kwargs: dict[str, Any] | None = None,
        page_size: int | None = None,
        operation: str = "teams-channel-replies",
    ) -> Request:
        """Build one enum-aware reply collection request."""
        return self.graph_request(
            self.replies_path(
                host_team_id,
                channel_id,
                root_message_id,
                page_size=page_size,
            ),
            callback=callback,
            errback=errback,
            operation=operation,
            cb_kwargs=cb_kwargs,
            prefer=self.representation_prefer,
        )

    def message_detail_request(
        self,
        message_identity: TeamsMessageIdentity,
        *,
        callback: Callback,
        errback: Callback,
        cb_kwargs: dict[str, Any] | None = None,
        operation: str = "teams-channel-message-detail",
    ) -> Request:
        """Build an enum-aware root or reply detail request from scoped identity."""
        team_id, channel_id, root_id, reply_id = _channel_message_parts(
            message_identity
        )
        if reply_id is None:
            path = self.root_message_path(team_id, channel_id, root_id)
        else:
            path = self.reply_message_path(
                team_id,
                channel_id,
                root_id,
                reply_id,
            )
        return self.graph_request(
            path,
            callback=callback,
            errback=errback,
            operation=operation,
            cb_kwargs=cb_kwargs,
            prefer=self.representation_prefer,
        )

    def message_continuation_request(
        self,
        next_link: str,
        *,
        callback: Callback,
        errback: Callback,
        cb_kwargs: dict[str, Any] | None = None,
        operation: str = "teams-channel-message-page",
    ) -> Request:
        """Replay an opaque root/reply continuation with its representation."""
        return self.continuation_request(
            next_link,
            callback=callback,
            errback=errback,
            operation=operation,
            cb_kwargs=cb_kwargs,
            prefer=self.representation_prefer,
        )

    def hosted_contents_request(
        self,
        message_identity: TeamsMessageIdentity,
        *,
        callback: Callback,
        errback: Callback,
        cb_kwargs: dict[str, Any] | None = None,
        operation: str = "teams-channel-hosted-contents",
    ) -> Request:
        """Build a hosted-content metadata collection request."""
        team_id, channel_id, root_id, reply_id = _channel_message_parts(
            message_identity
        )
        return self.graph_request(
            self.hosted_contents_path(
                team_id,
                channel_id,
                root_id,
                reply_id=reply_id,
            ),
            callback=callback,
            errback=errback,
            operation=operation,
            cb_kwargs=cb_kwargs,
            prefer=None,
        )

    def hosted_contents_continuation_request(
        self,
        next_link: str,
        *,
        callback: Callback,
        errback: Callback,
        cb_kwargs: dict[str, Any] | None = None,
        operation: str = "teams-channel-hosted-contents",
    ) -> Request:
        """Replay an opaque hosted-metadata continuation and caller context."""
        return self.continuation_request(
            next_link,
            callback=callback,
            errback=errback,
            operation=operation,
            cb_kwargs=cb_kwargs,
            prefer=None,
        )

    def _hosted_current_request(
        self,
        path: str,
        *,
        callback: Callback,
        errback: Callback,
        cb_kwargs: dict[str, Any] | None,
        operation: str,
        accept: str = "application/json",
    ) -> Request:
        """Build one uncached current hosted item/byte representation."""
        request = self.graph_request(
            path,
            callback=callback,
            errback=errback,
            operation=operation,
            cb_kwargs=cb_kwargs,
            accept=accept,
            prefer=None,
            dont_cache=True,
        )
        request.headers["ConsistencyLevel"] = self.hosted_consistency_level
        return request

    def hosted_content_request(
        self,
        message_identity: TeamsMessageIdentity,
        hosted_content_id: str,
        *,
        callback: Callback,
        errback: Callback,
        cb_kwargs: dict[str, Any] | None = None,
        operation: str = "teams-channel-hosted-content",
    ) -> Request:
        """Build an eventual, uncached hosted metadata-item GET."""
        team_id, channel_id, root_id, reply_id = _channel_message_parts(
            message_identity
        )
        return self._hosted_current_request(
            self.hosted_content_path(
                team_id,
                channel_id,
                root_id,
                hosted_content_id,
                reply_id=reply_id,
            ),
            callback=callback,
            errback=errback,
            cb_kwargs=cb_kwargs,
            operation=operation,
        )

    def hosted_content_bytes_request(
        self,
        message_identity: TeamsMessageIdentity,
        hosted_content_id: str,
        *,
        callback: Callback,
        errback: Callback,
        cb_kwargs: dict[str, Any] | None = None,
        operation: str = "teams-channel-hosted-content-bytes",
    ) -> Request:
        """
        Build an eventual uncached binary GET with no version selector.

        The path contains only the scoped message and hosted-content IDs. It
        cannot claim that returned bytes belong to a historical message etag.
        """
        team_id, channel_id, root_id, reply_id = _channel_message_parts(
            message_identity
        )
        return self._hosted_current_request(
            self.hosted_content_bytes_path(
                team_id,
                channel_id,
                root_id,
                hosted_content_id,
                reply_id=reply_id,
            ),
            callback=callback,
            errback=errback,
            cb_kwargs=cb_kwargs,
            operation=operation,
            accept=self.hosted_bytes_accept,
        )


__all__ = [
    "MicrosoftTeamsChannelCompositionSpider",
    "parse_channel_hosted_contents",
    "parse_channel_replies",
    "parse_channel_root_messages",
]
