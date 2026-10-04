"""Application helpers for evidence-first Teams chat message traversal."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from scrapy.http import TextResponse

from message_ingest.items.microsoft.teams.message import TeamsMessageItem
from microsoft_graph.items.teams.message import (
    TeamsMessageItem as GraphTeamsMessageItem,
)
from microsoft_graph.protocol import GraphCollectionPage
from microsoft_graph.spiders.teams.chat_composition import (
    parse_chat_message,
    parse_chat_messages,
)

from ._chat_content import message_content_outputs


def _application_message(item: GraphTeamsMessageItem) -> TeamsMessageItem:
    """Narrow a provider-parser result to the requested application subtype."""
    if not isinstance(item, TeamsMessageItem):
        raise TypeError("Provider parser returned a non-application Teams message")
    return item


def message_page_outputs(
    spider: Any,
    response: TextResponse,
    *,
    chat_id: str,
    purpose: str,
) -> Iterator[Any]:
    """Emit one chat-message page and schedule content or the next page."""
    evidence = spider._raw_http_evidence_item(response, purpose)
    yield evidence
    page = GraphCollectionPage.from_payload(
        response.json(),
        context="Teams chat messages",
        validate_links=False,
    )
    items = parse_chat_messages(
        page.values,
        chat_id=chat_id,
        item_type=TeamsMessageItem,
        **spider._teams_provenance(evidence),
    )
    for parsed_item in items:
        item = _application_message(parsed_item)
        spider._observed_message_ids.add((chat_id, item.message_id))
        yield item
        yield from message_content_outputs(spider, item)

    if next_link := page.next_link:
        yield spider.chat_messages_continuation_request(
            next_link,
            callback=spider.parse_chat_messages,
            errback=spider.errback,
            cb_kwargs={"chat_id": chat_id, "purpose": purpose},
            operation=purpose,
        )
        return

    pin_purpose = "teams-chat-pins"
    yield spider._chat_request(
        spider.chat_pins_path(chat_id),
        callback=spider.parse_chat_pins,
        purpose=pin_purpose,
        cb_kwargs={"chat_id": chat_id},
    )


def targeted_message_outputs(
    spider: Any,
    response: TextResponse,
    *,
    chat_id: str,
    message_id: str,
    purpose: str,
) -> Iterator[Any]:
    """Emit a pin-triggered targeted message without using pin expansion."""
    evidence = spider._raw_http_evidence_item(response, purpose)
    yield evidence
    item = _application_message(
        parse_chat_message(
            response.json(),
            chat_id=chat_id,
            message_id=message_id,
            item_type=TeamsMessageItem,
            **spider._teams_provenance(evidence),
        )
    )
    spider._observed_message_ids.add((chat_id, item.message_id))
    yield item
    yield from message_content_outputs(spider, item)


__all__ = ["message_page_outputs", "targeted_message_outputs"]
