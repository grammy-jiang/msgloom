"""Compose Teams chat topology with common message/content provider models."""

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
from microsoft_graph.protocol.teams import TeamsMessageIdentity
from microsoft_graph.spiders.teams.chat import MicrosoftTeamsChatSpider

TEAMS_MESSAGE_PREFER = "include-unknown-enum-members"
TEAMS_HOSTED_CONSISTENCY = "eventual"
TEAMS_HOSTED_BINARY_ACCEPT = "application/octet-stream"


def _chat_scope(chat_id: str) -> None:
    """Require one opaque chat scope even when a collection is empty."""
    if not isinstance(chat_id, str) or not chat_id:
        raise ValueError("Teams chat composition requires a non-empty chat_id")


def parse_chat_messages(
    resources: Any,
    *,
    chat_id: str,
    item_type: type[TeamsMessageItem] = TeamsMessageItem,
    **item_kwargs: Any,
) -> tuple[TeamsMessageItem, ...]:
    """
    Parse resources returned under one chat message collection path.

    ``resources`` is the validated value list from
    :class:`~microsoft_graph.protocol.GraphCollectionPage`, not a collection
    envelope. Application subclasses may supply constructor fields through
    ``item_kwargs``.
    """
    _chat_scope(chat_id)
    if not isinstance(resources, list):
        raise GraphObjectTypeError("Teams chat messages must be a JSON array")
    return tuple(
        item_type.from_chat_graph(
            resource,
            chat_id=chat_id,
            **item_kwargs,
        )
        for resource in resources
    )


def parse_chat_message(
    resource: Any,
    *,
    chat_id: str,
    message_id: str,
    item_type: type[TeamsMessageItem] = TeamsMessageItem,
    **item_kwargs: Any,
) -> TeamsMessageItem:
    """
    Parse one targeted chat message using the request path as identity scope.

    Payload ``chatId``, ``replyToId``, and ``channelIdentity`` remain provider
    facts. They never replace or extend the chat identity established by the
    targeted request path.
    """
    identity = TeamsMessageIdentity.chat(message_id, chat_id=chat_id)
    return item_type.from_graph(
        resource,
        identity=identity,
        **item_kwargs,
    )


def parse_chat_hosted_contents(
    resources: Any,
    *,
    chat_id: str,
    message_id: str,
) -> tuple[TeamsHostedContentItem, ...]:
    """Parse hosted metadata under the exact chat/message request scope."""
    identity = TeamsMessageIdentity.chat(message_id, chat_id=chat_id)
    return parse_hosted_contents(resources, message_identity=identity)


class MicrosoftTeamsChatCompositionSpider(MicrosoftTeamsChatSpider):
    """
    Build chat-message requests without owning application response callbacks.

    Consumers supply named callbacks, named errbacks, and callback context.
    This provider layer binds chat paths to required representation headers
    and common pure models. Consumers select permissions and page sizes.
    """

    def chat_messages_request(
        self,
        chat_id: str,
        *,
        callback: Callable[..., Any],
        errback: Callable[..., Any],
        cb_kwargs: dict[str, Any] | None = None,
        page_size: int | None = None,
        modified_after: str | None = None,
        modified_before: str | None = None,
        operation: str = "teams-chat-messages",
    ) -> Request:
        """Build one message-list request with the frozen enum preference."""
        return self.graph_request(
            self.chat_messages_path(
                chat_id,
                page_size=page_size,
                modified_after=modified_after,
                modified_before=modified_before,
            ),
            callback=callback,
            errback=errback,
            cb_kwargs=cb_kwargs,
            operation=operation,
            prefer=TEAMS_MESSAGE_PREFER,
        )

    def chat_messages_continuation_request(
        self,
        next_link: str,
        *,
        callback: Callable[..., Any],
        errback: Callable[..., Any],
        cb_kwargs: dict[str, Any] | None = None,
        operation: str = "teams-chat-messages",
    ) -> Request:
        """Replay an opaque message nextLink with its required representation."""
        return self.continuation_request(
            next_link,
            callback=callback,
            errback=errback,
            cb_kwargs=cb_kwargs,
            operation=operation,
            prefer=TEAMS_MESSAGE_PREFER,
        )

    def chat_message_request(
        self,
        chat_id: str,
        message_id: str,
        *,
        callback: Callable[..., Any],
        errback: Callable[..., Any],
        cb_kwargs: dict[str, Any] | None = None,
        operation: str = "teams-chat-message",
    ) -> Request:
        """Build one targeted message request with the frozen enum preference."""
        return self.graph_request(
            self.chat_message_path(chat_id, message_id),
            callback=callback,
            errback=errback,
            cb_kwargs=cb_kwargs,
            operation=operation,
            prefer=TEAMS_MESSAGE_PREFER,
        )

    def chat_hosted_contents_request(
        self,
        chat_id: str,
        message_id: str,
        *,
        callback: Callable[..., Any],
        errback: Callable[..., Any],
        cb_kwargs: dict[str, Any] | None = None,
        operation: str = "teams-chat-hosted-contents",
    ) -> Request:
        """Build the hosted-content metadata collection request."""
        return self.graph_request(
            self.hosted_contents_path(chat_id, message_id),
            callback=callback,
            errback=errback,
            cb_kwargs=cb_kwargs,
            operation=operation,
        )

    def chat_hosted_contents_continuation_request(
        self,
        next_link: str,
        *,
        callback: Callable[..., Any],
        errback: Callable[..., Any],
        cb_kwargs: dict[str, Any] | None = None,
        operation: str = "teams-chat-hosted-contents",
    ) -> Request:
        """Replay an opaque hosted-content continuation with caller context."""
        return self.continuation_request(
            next_link,
            callback=callback,
            errback=errback,
            cb_kwargs=cb_kwargs,
            operation=operation,
        )

    def chat_hosted_content_request(
        self,
        chat_id: str,
        message_id: str,
        hosted_content_id: str,
        *,
        callback: Callable[..., Any],
        errback: Callable[..., Any],
        cb_kwargs: dict[str, Any] | None = None,
        operation: str = "teams-chat-hosted-content",
    ) -> Request:
        """Build an uncached eventual-consistency hosted metadata read."""
        request = self.graph_request(
            self.hosted_content_path(chat_id, message_id, hosted_content_id),
            callback=callback,
            errback=errback,
            cb_kwargs=cb_kwargs,
            operation=operation,
            dont_cache=True,
        )
        request.headers["ConsistencyLevel"] = TEAMS_HOSTED_CONSISTENCY
        return request

    def chat_hosted_content_bytes_request(
        self,
        chat_id: str,
        message_id: str,
        hosted_content_id: str,
        *,
        callback: Callable[..., Any],
        errback: Callable[..., Any],
        cb_kwargs: dict[str, Any] | None = None,
        operation: str = "teams-chat-hosted-content-bytes",
    ) -> Request:
        """
        Build an uncached binary read without a historical-version selector.

        The provider path can address only current bytes for the supplied
        chat/message/hosted-content IDs. The application owns response evidence,
        retrieval time, and any explicit provider-limit failure state.
        """
        request = self.graph_request(
            self.hosted_content_bytes_path(
                chat_id,
                message_id,
                hosted_content_id,
            ),
            callback=callback,
            errback=errback,
            cb_kwargs=cb_kwargs,
            operation=operation,
            accept=TEAMS_HOSTED_BINARY_ACCEPT,
            dont_cache=True,
        )
        request.headers["ConsistencyLevel"] = TEAMS_HOSTED_CONSISTENCY
        return request


__all__ = [
    "MicrosoftTeamsChatCompositionSpider",
    "parse_chat_hosted_contents",
    "parse_chat_message",
    "parse_chat_messages",
]
