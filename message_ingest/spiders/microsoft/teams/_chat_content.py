"""Application helpers for Teams chat references and hosted content."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from scrapy import Request
from scrapy.http import Response, TextResponse

from message_ingest.items.acquisition import RawHttpEvidenceItem
from message_ingest.items.microsoft.teams.content import (
    TeamsHostedContentBytesItem,
    TeamsHostedContentFailureItem,
    TeamsHostedContentItem,
    TeamsReferenceResolutionItem,
)
from message_ingest.items.microsoft.teams.message import (
    TeamsMessageItem,
    TeamsMessageTrigger,
)
from microsoft_graph.protocol import GraphCollectionPage
from microsoft_graph.protocol.teams import TeamsAttachmentKind
from microsoft_graph.spiders.teams.chat_composition import (
    parse_chat_hosted_contents,
)

_HOSTED_LIMITATION = "hosted-content-in-deleted-thread-unsupported"


def _message_provenance(item: TeamsMessageItem) -> dict[str, Any]:
    """Return the exact observation provenance carried by one message item."""
    return {
        "source_id": item.source_id,
        "observed_at": item.observed_at,
        "evidence_id": item.evidence_id,
        "run_id": item.run_id,
    }


def _trigger_scope(
    trigger: TeamsMessageTrigger,
    *,
    chat_id: str,
    message_id: str,
) -> None:
    """Require callback context to match the immutable triggering identity."""
    identity = trigger.identity
    if identity.chat_id != chat_id or identity.message_id != message_id:
        raise ValueError("Hosted callback context does not match message trigger")


def _content_type(response: Response) -> str | None:
    """Decode the exact response Content-Type value when Graph supplied one."""
    value = response.headers.get(b"Content-Type")
    return value.decode("latin-1") if value is not None else None


def message_content_outputs(
    spider: Any,
    item: TeamsMessageItem,
) -> Iterator[Any]:
    """
    Emit explicit reference state before scheduling hosted-content follow-ups.

    The caller invokes this only after yielding the message item. The trigger
    snapshots whichever provisional evidence identity the message has at that
    point; the Teams pipeline resolves any later canonical evidence alias.
    """
    trigger = TeamsMessageTrigger.from_message(item)
    provenance = _message_provenance(item)
    for ordinal, attachment in enumerate(item.attachment_items):
        if attachment.kind is not TeamsAttachmentKind.REFERENCE:
            continue
        yield TeamsReferenceResolutionItem(
            trigger=trigger,
            attachment_ordinal=ordinal,
            state="not-attempted",
            details={
                "reason": "broad-file-profile-disabled",
                "attachment_kind": attachment.kind.value,
            },
            **provenance,
        )

    chat_id = item.identity.chat_id
    if not isinstance(chat_id, str) or not chat_id:
        raise ValueError("Chat message content requires chat identity")
    purpose = "teams-chat-hosted-contents"
    request = spider.chat_hosted_contents_request(
        chat_id,
        item.message_id,
        callback=spider.parse_hosted_contents,
        errback=spider.errback,
        cb_kwargs={
            "chat_id": chat_id,
            "message_id": item.message_id,
            "trigger": trigger,
            "purpose": purpose,
        },
        operation=purpose,
    )
    if associated := spider._associate_hosted_request(request, trigger):
        yield associated


def hosted_collection_outputs(
    spider: Any,
    response: TextResponse,
    *,
    chat_id: str,
    message_id: str,
    trigger: TeamsMessageTrigger,
    purpose: str,
) -> Iterator[Any]:
    """Emit hosted-list evidence and metadata, then item/byte follow-ups."""
    _trigger_scope(trigger, chat_id=chat_id, message_id=message_id)
    evidence = spider._raw_http_evidence_item(response, purpose)
    yield evidence
    page = GraphCollectionPage.from_payload(
        response.json(),
        context="Teams chat hosted contents",
        validate_links=False,
    )
    parsed_items = parse_chat_hosted_contents(
        page.values,
        chat_id=chat_id,
        message_id=message_id,
    )
    for parsed in parsed_items:
        item = TeamsHostedContentItem.from_graph(
            parsed.raw,
            message_identity=trigger.identity,
            trigger=trigger,
            **spider._teams_provenance(evidence),
        )
        yield item
        yield from _hosted_item_requests(
            spider,
            chat_id=chat_id,
            message_id=message_id,
            hosted_content_id=item.hosted_content_id,
            trigger=trigger,
        )

    if next_link := page.next_link:
        request = spider.chat_hosted_contents_continuation_request(
            next_link,
            callback=spider.parse_hosted_contents,
            errback=spider.errback,
            cb_kwargs={
                "chat_id": chat_id,
                "message_id": message_id,
                "trigger": trigger,
                "purpose": purpose,
            },
            operation=purpose,
        )
        if associated := spider._associate_hosted_request(request, trigger):
            yield associated


def _hosted_item_requests(
    spider: Any,
    *,
    chat_id: str,
    message_id: str,
    hosted_content_id: str,
    trigger: TeamsMessageTrigger,
) -> Iterator[Request]:
    """Schedule current metadata and bytes under the exact message trigger."""
    for request_kind, builder, callback, purpose in (
        (
            "metadata",
            spider.chat_hosted_content_request,
            spider.parse_hosted_content,
            "teams-chat-hosted-content",
        ),
        (
            "bytes",
            spider.chat_hosted_content_bytes_request,
            spider.parse_hosted_content_bytes,
            "teams-chat-hosted-content-bytes",
        ),
    ):
        request = builder(
            chat_id,
            message_id,
            hosted_content_id,
            callback=callback,
            errback=spider.errback_hosted_content,
            cb_kwargs={
                "chat_id": chat_id,
                "message_id": message_id,
                "hosted_content_id": hosted_content_id,
                "hosted_request_kind": request_kind,
                "trigger": trigger,
                "purpose": purpose,
            },
            operation=purpose,
        )
        if associated := spider._associate_hosted_request(request, trigger):
            yield associated


def hosted_item_outputs(
    spider: Any,
    response: TextResponse,
    *,
    chat_id: str,
    message_id: str,
    hosted_content_id: str,
    trigger: TeamsMessageTrigger,
    purpose: str,
    hosted_request_kind: str,
) -> Iterator[Any]:
    """Emit one hosted metadata response and its application observation."""
    if hosted_request_kind != "metadata":
        raise ValueError("Hosted metadata callback received the wrong request kind")
    _trigger_scope(trigger, chat_id=chat_id, message_id=message_id)
    evidence = spider._raw_http_evidence_item(response, purpose)
    yield evidence
    parsed = parse_chat_hosted_contents(
        [response.json()],
        chat_id=chat_id,
        message_id=message_id,
    )
    if len(parsed) != 1 or parsed[0].hosted_content_id != hosted_content_id:
        raise ValueError("Hosted metadata response does not match requested ID")
    yield TeamsHostedContentItem.from_graph(
        parsed[0].raw,
        message_identity=trigger.identity,
        trigger=trigger,
        **spider._teams_provenance(evidence),
    )


def hosted_bytes_outputs(
    spider: Any,
    response: Response,
    *,
    chat_id: str,
    message_id: str,
    hosted_content_id: str,
    trigger: TeamsMessageTrigger,
    purpose: str,
    hosted_request_kind: str,
) -> Iterator[Any]:
    """Emit raw hosted bytes evidence before digest metadata."""
    if hosted_request_kind != "bytes":
        raise ValueError("Hosted bytes callback received the wrong request kind")
    _trigger_scope(trigger, chat_id=chat_id, message_id=message_id)
    evidence = spider._raw_http_evidence_item(response, purpose)
    yield evidence
    yield TeamsHostedContentBytesItem.from_bytes(
        body=response.body,
        message_identity=trigger.identity,
        hosted_content_id=hosted_content_id,
        trigger=trigger,
        content_type=_content_type(response),
        **spider._teams_provenance(evidence),
    )


def hosted_failure_outputs(spider: Any, failure: Any) -> Iterator[Any]:
    """
    Preserve inherited terminal failure evidence plus hosted limitation state.

    A failed current read cannot prove which historical message version owned
    the hosted bytes. The persisted limitation records the known deleted-thread
    constraint without claiming that it caused every terminal failure.
    """
    evidence: RawHttpEvidenceItem | None = None
    for output in spider.errback(failure):
        if isinstance(output, RawHttpEvidenceItem):
            evidence = output
        yield output
    if evidence is None:
        raise RuntimeError("Hosted failure path did not emit raw evidence")

    request = spider._failure_request(failure)
    trigger = request.cb_kwargs.get("trigger")
    hosted_content_id = request.cb_kwargs.get("hosted_content_id")
    request_kind = request.cb_kwargs.get("hosted_request_kind")
    if not isinstance(trigger, TeamsMessageTrigger):
        raise TypeError("Hosted failure requires a TeamsMessageTrigger")
    if not isinstance(hosted_content_id, str) or not hosted_content_id:
        raise ValueError("Hosted failure requires hosted_content_id")
    if request_kind not in {"metadata", "bytes"}:
        raise ValueError("Hosted failure requires a bounded request kind")

    yield TeamsHostedContentFailureItem(
        message_identity=trigger.identity,
        hosted_content_id=hosted_content_id,
        trigger=trigger,
        failure_kind="hosted-content-retrieval-failed",
        status_code=evidence.response_status,
        details={
            "request_kind": request_kind,
            "known_provider_limitation": _HOSTED_LIMITATION,
            "provider_version_bound": False,
        },
        **spider._teams_provenance(evidence),
    )


__all__ = [
    "hosted_bytes_outputs",
    "hosted_collection_outputs",
    "hosted_failure_outputs",
    "hosted_item_outputs",
    "message_content_outputs",
]
