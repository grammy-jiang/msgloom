"""Discover delegated Microsoft Teams chats through evidence-first callbacks."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any, ClassVar
from urllib.parse import urlsplit

from scrapy import Request
from scrapy.http import Response, TextResponse

from message_ingest.items.microsoft.teams.message import TeamsMessageTrigger
from message_ingest.items.microsoft.teams.topology import (
    TeamsChatItem,
    TeamsChatMemberItem,
    TeamsChatPinItem,
)
from message_ingest.spiders.microsoft.teams._base import MicrosoftTeamsBaseSpider
from microsoft_graph.protocol import GraphCollectionPage
from microsoft_graph.spiders.teams.chat_composition import (
    MicrosoftTeamsChatCompositionSpider,
)

from ._chat_content import (
    hosted_bytes_outputs,
    hosted_collection_outputs,
    hosted_failure_outputs,
    hosted_item_outputs,
)
from ._chat_messages import message_page_outputs, targeted_message_outputs
from ._chat_profile import CHAT_DISCOVERY_PAGE_SIZE, CHAT_DISCOVERY_SCOPES


class MicrosoftTeamsChatDiscoverSpider(
    MicrosoftTeamsChatCompositionSpider,
    MicrosoftTeamsBaseSpider,
):
    """
    Traverse core delegated Teams chats using the existing Graph framework.

    Discovery records observations only. Empty inventories never infer deletion
    or unpin state. Hosted requests retain their exact triggering observation;
    a repeated provider URL is allowed through the native scheduler only when a
    distinct bounded trigger context requires a second acquisition.
    """

    name = "microsoft_teams_chat_discover"
    graph_permissions: ClassVar[tuple[str, ...]] = CHAT_DISCOVERY_SCOPES
    failure_context_keys: ClassVar[tuple[str, ...]] = (
        "chat_id",
        "message_id",
        "hosted_content_id",
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize bounded per-crawl traversal association state."""
        super().__init__(*args, **kwargs)
        self._observed_message_ids: set[tuple[str, str]] = set()
        self._targeted_message_ids: set[tuple[str, str]] = set()
        self._hosted_request_contexts: dict[
            str,
            set[tuple[str, tuple[str, ...], str]],
        ] = {}

    async def start(self) -> AsyncIterator[Any]:
        """Schedule the signed-in user's chat inventory."""
        yield self._chat_request(
            self.chats_path(page_size=CHAT_DISCOVERY_PAGE_SIZE),
            callback=self.parse_chats,
            purpose="teams-chat-list",
            cb_kwargs={},
        )

    def _chat_request(
        self,
        url: str,
        *,
        callback: Any,
        purpose: str,
        cb_kwargs: dict[str, Any],
    ) -> Request:
        """Build a fresh Graph request with explicit failure evidence context."""
        return self.graph_request(
            url,
            callback=callback,
            errback=self.errback,
            operation=purpose,
            cb_kwargs={**cb_kwargs, "purpose": purpose},
        )

    def _chat_continuation_request(
        self,
        url: str,
        *,
        callback: Any,
        purpose: str,
        cb_kwargs: dict[str, Any],
    ) -> Request:
        """Replay one opaque provider continuation with callback context intact."""
        return self.continuation_request(
            url,
            callback=callback,
            errback=self.errback,
            operation=purpose,
            cb_kwargs={**cb_kwargs, "purpose": purpose},
        )

    def _associate_hosted_request(
        self,
        request: Request,
        trigger: TeamsMessageTrigger,
    ) -> Request | None:
        """
        Keep one request per trigger while preserving distinct trigger evidence.

        Native duplicate filtering remains enabled for the first representation
        of a URL. A second exact URL is bypassed only for a different immutable
        message trigger and only when its host is already allowed by the Graph
        spider. This avoids a custom scheduler or request fingerprinter.
        """
        context = (
            trigger.source_id,
            trigger.identity.scope_key,
            trigger.evidence_id,
        )
        contexts = self._hosted_request_contexts.setdefault(request.url, set())
        if context in contexts:
            return None
        repeated_url = bool(contexts)
        contexts.add(context)
        if not repeated_url:
            return request

        host = urlsplit(request.url).hostname
        if host is not None and host in self.allowed_domains:
            request.dont_filter = True
        return request

    def parse_chats(
        self,
        response: TextResponse,
        *,
        purpose: str,
    ) -> Iterator[Any]:
        """Emit chat observations, then explicit member and message traversals."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        page = GraphCollectionPage.from_payload(
            response.json(),
            context="Teams chats",
            validate_links=False,
        )
        for raw in page.values:
            item = TeamsChatItem.from_graph(
                raw,
                **self._teams_provenance(evidence),
            )
            yield item
            member_purpose = "teams-chat-members"
            yield self._chat_request(
                self.chat_members_path(item.chat_id),
                callback=self.parse_chat_members,
                purpose=member_purpose,
                cb_kwargs={"chat_id": item.chat_id},
            )
            message_purpose = "teams-chat-messages"
            yield self.chat_messages_request(
                item.chat_id,
                page_size=CHAT_DISCOVERY_PAGE_SIZE,
                callback=self.parse_chat_messages,
                errback=self.errback,
                cb_kwargs={
                    "chat_id": item.chat_id,
                    "purpose": message_purpose,
                },
                operation=message_purpose,
            )
        if next_link := page.next_link:
            yield self._chat_continuation_request(
                next_link,
                callback=self.parse_chats,
                purpose=purpose,
                cb_kwargs={},
            )

    def parse_chat_members(
        self,
        response: TextResponse,
        *,
        chat_id: str,
        purpose: str,
    ) -> Iterator[Any]:
        """Emit every explicit chat membership page without inline expansion."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        page = GraphCollectionPage.from_payload(
            response.json(),
            context="Teams chat members",
            validate_links=False,
        )
        for raw in page.values:
            yield TeamsChatMemberItem.from_graph(
                raw,
                chat_id=chat_id,
                **self._teams_provenance(evidence),
            )
        if next_link := page.next_link:
            yield self._chat_continuation_request(
                next_link,
                callback=self.parse_chat_members,
                purpose=purpose,
                cb_kwargs={"chat_id": chat_id},
            )

    def parse_chat_messages(
        self,
        response: TextResponse,
        *,
        chat_id: str,
        purpose: str,
    ) -> Iterator[Any]:
        """Delegate pure message parsing while retaining this named callback."""
        yield from message_page_outputs(
            self,
            response,
            chat_id=chat_id,
            purpose=purpose,
        )

    def parse_chat_pins(
        self,
        response: TextResponse,
        *,
        chat_id: str,
        purpose: str,
    ) -> Iterator[Any]:
        """Persist pin relations and target only messages not already observed."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        page = GraphCollectionPage.from_payload(
            response.json(),
            context="Teams chat pinned messages",
            validate_links=False,
        )
        for raw in page.values:
            item = TeamsChatPinItem.from_graph(
                raw,
                chat_id=chat_id,
                **self._teams_provenance(evidence),
            )
            yield item
            key = (chat_id, item.message_id)
            if key in self._observed_message_ids or key in self._targeted_message_ids:
                continue
            self._targeted_message_ids.add(key)
            target_purpose = "teams-chat-message"
            yield self.chat_message_request(
                chat_id,
                item.message_id,
                callback=self.parse_pinned_message,
                errback=self.errback,
                cb_kwargs={
                    "chat_id": chat_id,
                    "message_id": item.message_id,
                    "purpose": target_purpose,
                },
                operation=target_purpose,
            )
        if next_link := page.next_link:
            yield self._chat_continuation_request(
                next_link,
                callback=self.parse_chat_pins,
                purpose=purpose,
                cb_kwargs={"chat_id": chat_id},
            )

    def parse_pinned_message(
        self,
        response: TextResponse,
        *,
        chat_id: str,
        message_id: str,
        purpose: str,
    ) -> Iterator[Any]:
        """Persist a needed pin-targeted message as its own response capture."""
        yield from targeted_message_outputs(
            self,
            response,
            chat_id=chat_id,
            message_id=message_id,
            purpose=purpose,
        )

    def parse_hosted_contents(
        self,
        response: TextResponse,
        *,
        chat_id: str,
        message_id: str,
        trigger: TeamsMessageTrigger,
        purpose: str,
    ) -> Iterator[Any]:
        """Traverse every hosted metadata page under one exact trigger."""
        yield from hosted_collection_outputs(
            self,
            response,
            chat_id=chat_id,
            message_id=message_id,
            trigger=trigger,
            purpose=purpose,
        )

    def parse_hosted_content(
        self,
        response: TextResponse,
        *,
        chat_id: str,
        message_id: str,
        hosted_content_id: str,
        trigger: TeamsMessageTrigger,
        purpose: str,
        hosted_request_kind: str,
    ) -> Iterator[Any]:
        """Persist one current hosted metadata item response."""
        yield from hosted_item_outputs(
            self,
            response,
            chat_id=chat_id,
            message_id=message_id,
            hosted_content_id=hosted_content_id,
            trigger=trigger,
            purpose=purpose,
            hosted_request_kind=hosted_request_kind,
        )

    def parse_hosted_content_bytes(
        self,
        response: Response,
        *,
        chat_id: str,
        message_id: str,
        hosted_content_id: str,
        trigger: TeamsMessageTrigger,
        purpose: str,
        hosted_request_kind: str,
    ) -> Iterator[Any]:
        """Persist hosted bytes only as evidence-linked digest metadata."""
        yield from hosted_bytes_outputs(
            self,
            response,
            chat_id=chat_id,
            message_id=message_id,
            hosted_content_id=hosted_content_id,
            trigger=trigger,
            purpose=purpose,
            hosted_request_kind=hosted_request_kind,
        )

    def errback_hosted_content(self, failure: Any) -> Iterator[Any]:
        """Extend inherited terminal failure evidence with hosted limitation."""
        yield from hosted_failure_outputs(self, failure)


__all__ = ["MicrosoftTeamsChatDiscoverSpider"]
