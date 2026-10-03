"""Verify pure Teams chat message/content composition and request policy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
from scrapy.utils.request import request_from_dict

from microsoft_graph.fingerprints import GraphRequestFingerprinter
from microsoft_graph.items.teams.message import TeamsMessageItem
from microsoft_graph.protocol import GraphCollectionPage, GraphObjectTypeError
from microsoft_graph.protocol.teams import (
    TeamsAttachmentKind,
    TeamsMessageLocation,
)
from microsoft_graph.spiders.teams.chat_composition import (
    MicrosoftTeamsChatCompositionSpider,
    parse_chat_hosted_contents,
    parse_chat_message,
    parse_chat_messages,
)


class ApplicationCallbacks(MicrosoftTeamsChatCompositionSpider):
    """Provide named application-owned callback surfaces for request tests."""

    name = "teams_chat_composition_test"

    def parse_messages(self, response, **kwargs):
        """Represent an application response callback without provider parsing."""
        return []

    def parse_hosted(self, response, **kwargs):
        """Represent a separate application callback for hosted content."""
        return []

    def application_errback(self, failure):
        """Represent the application terminal errback."""
        return []


@dataclass(slots=True)
class ApplicationMessage(TeamsMessageItem):
    """Prove common parser kwargs can populate an application subclass."""

    evidence_id: str


def _spider() -> ApplicationCallbacks:
    return ApplicationCallbacks()


def _callback_context() -> dict[str, Any]:
    return {
        "chat_id": "chat/A+=%2F",
        "purpose": {"kind": "messages", "falsey": [0, False, ""]},
    }


def test_message_requests_use_named_application_callbacks_and_prefer() -> None:
    spider = _spider()
    context = _callback_context()
    requests = (
        spider.chat_messages_request(
            context["chat_id"],
            callback=spider.parse_messages,
            errback=spider.application_errback,
            cb_kwargs=context,
        ),
        spider.chat_message_request(
            context["chat_id"],
            "message/A+=%2F",
            callback=spider.parse_messages,
            errback=spider.application_errback,
            cb_kwargs=context,
        ),
    )

    for request in requests:
        if request.headers.get("Prefer") != b"include-unknown-enum-members":
            pytest.fail("Message requests lost include-unknown-enum-members")
        if request.cb_kwargs != context:
            pytest.fail("Message request changed caller callback context")
        saved = request.to_dict(spider=spider)
        if saved.get("callback") != "parse_messages":
            pytest.fail("Message callback must serialize by application name")
        if saved.get("errback") != "application_errback":
            pytest.fail("Message errback must serialize by application name")


def test_message_continuation_is_opaque_and_retains_context_and_prefer() -> None:
    spider = _spider()
    context = _callback_context()
    next_link = (
        "https://graph.microsoft.com/v1.0/chats/c/messages?"
        "$skiptoken=A%2fb%2F+%2B%20&x=2&x=1"
    )
    request = spider.chat_messages_continuation_request(
        next_link,
        callback=spider.parse_messages,
        errback=spider.application_errback,
        cb_kwargs=context,
    )
    restored = request_from_dict(request.to_dict(spider=spider), spider=spider)

    if request.url != next_link or restored.url != next_link:
        pytest.fail("Encoded Graph message nextLink was modified")
    if request.meta.get("verbatim_url") is not True:
        pytest.fail("Message continuation must use continuation_request")
    if request.headers.get("Prefer") != b"include-unknown-enum-members":
        pytest.fail("Message continuation lost representation preference")
    if request.cb_kwargs != context or restored.cb_kwargs != context:
        pytest.fail("Message continuation lost callback context")


def test_hosted_collection_continuation_is_opaque_and_context_preserving() -> None:
    spider = _spider()
    context = {"chat_id": "chat", "message_id": "message", "page": 2}
    next_link = (
        "https://graph.microsoft.com/v1.0/chats/c/messages/m/hostedContents?"
        "$skiptoken=%2f%2F+%20&repeat=1&repeat=0"
    )
    request = spider.chat_hosted_contents_continuation_request(
        next_link,
        callback=spider.parse_hosted,
        errback=spider.application_errback,
        cb_kwargs=context,
    )

    if request.url != next_link:
        pytest.fail("Hosted-content nextLink was decoded or rebuilt")
    if request.meta.get("verbatim_url") is not True:
        pytest.fail("Hosted continuation must use native continuation_request")
    if request.headers.get("Accept") != b"application/json":
        pytest.fail("Hosted continuation lost its JSON representation")
    if request.cb_kwargs != context:
        pytest.fail("Hosted continuation lost application context")


def test_hosted_item_and_bytes_are_uncached_eventual_reads() -> None:
    spider = _spider()
    context = {"triggering_observation": "obs-1"}
    item = spider.chat_hosted_content_request(
        "chat",
        "message",
        "hosted",
        callback=spider.parse_hosted,
        errback=spider.application_errback,
        cb_kwargs=context,
    )
    binary = spider.chat_hosted_content_bytes_request(
        "chat",
        "message",
        "hosted",
        callback=spider.parse_hosted,
        errback=spider.application_errback,
        cb_kwargs=context,
    )

    for request in (item, binary):
        if request.headers.get("ConsistencyLevel") != b"eventual":
            pytest.fail("Hosted current read lost ConsistencyLevel eventual")
        if request.meta.get("dont_cache") is not True:
            pytest.fail("Hosted current read must bypass HTTP response cache")
        if request.cb_kwargs != context:
            pytest.fail("Hosted current read lost triggering context")

    if item.headers.get("Accept") != b"application/json":
        pytest.fail("Hosted item request must retain JSON Accept")
    if binary.headers.get("Accept") != b"application/octet-stream":
        pytest.fail("Hosted byte request must use binary Accept")
    if "?" in binary.url:
        pytest.fail("Hosted bytes must not add a message-version selector")


def test_required_representation_headers_change_graph_fingerprints() -> None:
    spider = _spider()
    fingerprinter = GraphRequestFingerprinter()
    context = {"chat_id": "chat"}

    message = spider.chat_message_request(
        "chat",
        "message",
        callback=spider.parse_messages,
        errback=spider.application_errback,
        cb_kwargs=context,
    )
    plain_message = spider.graph_request(
        spider.chat_message_path("chat", "message"),
        callback=spider.parse_messages,
        errback=spider.application_errback,
        cb_kwargs=context,
    )
    if fingerprinter.fingerprint(message) == fingerprinter.fingerprint(plain_message):
        pytest.fail("Prefer representation must affect Graph request identity")

    binary = spider.chat_hosted_content_bytes_request(
        "chat",
        "message",
        "hosted",
        callback=spider.parse_hosted,
        errback=spider.application_errback,
    )
    json_same_url = spider.graph_request(
        spider.hosted_content_bytes_path("chat", "message", "hosted"),
        callback=spider.parse_hosted,
        errback=spider.application_errback,
        dont_cache=True,
    )
    json_same_url.headers["ConsistencyLevel"] = "eventual"
    if fingerprinter.fingerprint(binary) == fingerprinter.fingerprint(json_same_url):
        pytest.fail("Binary Accept representation must affect Graph request identity")


def test_collection_parser_uses_common_model_and_application_subclass_kwargs() -> None:
    raw = {
        "id": "message/A+=%2F",
        "chatId": "payload/chat/does-not-rescope",
        "replyToId": "payload/reply-fact",
        "channelIdentity": {"teamId": "payload-team", "channelId": "payload-channel"},
        "messageType": "futureSystemEvent",
        "body": {"contentType": "html", "content": ""},
        "attachments": [
            {
                "id": "",
                "contentType": "messageReference",
                "content": {"messageId": "other-message"},
                "contentUrl": "https://example.invalid/not-a-fetch-target",
            }
        ],
        "future": {"unknown": [0, False, ""]},
    }
    page = GraphCollectionPage.from_payload({"value": [raw]})
    item = parse_chat_messages(
        page.values,
        chat_id="path/chat",
        item_type=ApplicationMessage,
        evidence_id="evidence-1",
    )[0]

    if not isinstance(item, ApplicationMessage) or item.evidence_id != "evidence-1":
        pytest.fail("Application message subclass kwargs were not retained")
    if item.raw is not raw or item.identity.message_id != raw["id"]:
        pytest.fail("Common chatMessage parser changed raw data or identity")
    if item.identity.scope_key != ("chat", "path/chat", raw["id"]):
        pytest.fail("Message identity did not follow chat collection path scope")
    if item.provider_chat_id != raw["chatId"]:
        pytest.fail("Payload chatId must remain a separate provider fact")
    if item.reply_to_id != raw["replyToId"]:
        pytest.fail("Payload replyToId must remain a separate provider fact")
    if item.identity.location is not TeamsMessageLocation.CHAT:
        pytest.fail("Chat message was incorrectly converted to channel threading")
    if item.identity.root_message_id is not None:
        pytest.fail("Chat messageReference/replyToId must not create a root identity")
    if item.attachment_items[0].kind is not TeamsAttachmentKind.MESSAGE_REFERENCE:
        pytest.fail("Common attachment parser lost messageReference relation candidate")


def test_targeted_parser_uses_request_message_id_not_payload_context_fields() -> None:
    raw = {
        "id": "message",
        "chatId": "payload-chat",
        "replyToId": "payload-reply",
        "scope": None,
    }
    item = parse_chat_message(
        raw,
        chat_id="path-chat",
        message_id="message",
        item_type=ApplicationMessage,
        evidence_id="evidence-2",
    )

    if item.identity.scope_key != ("chat", "path-chat", "message"):
        pytest.fail("Targeted message identity did not follow request path")
    if (item.provider_chat_id, item.reply_to_id) != ("payload-chat", "payload-reply"):
        pytest.fail("Targeted parser normalized separate payload context facts")

    with pytest.raises(ValueError):
        parse_chat_message(
            {"id": "different-message"},
            chat_id="path-chat",
            message_id="message",
        )


def test_hosted_parser_reuses_common_content_model_with_chat_scope() -> None:
    raw = {
        "id": "hosted/A+=%2F",
        "contentType": "",
        "contentBytes": "",
        "future": [0, False, ""],
    }
    page = GraphCollectionPage.from_payload({"value": [raw]})
    item = parse_chat_hosted_contents(
        page.values,
        chat_id="chat/A+=%2F",
        message_id="message/A+=%2F",
    )[0]

    if item.raw is not raw:
        pytest.fail("Hosted common parser copied or normalized provider metadata")
    if item.message_identity.scope_key != (
        "chat",
        "chat/A+=%2F",
        "message/A+=%2F",
    ):
        pytest.fail("Hosted metadata lost its chat/message request scope")
    if (item.content_type, item.content_bytes) != ("", ""):
        pytest.fail("Hosted falsey provider values were normalized")


@pytest.mark.parametrize(
    ("parser", "args"),
    [
        (parse_chat_messages, {"resources": [], "chat_id": ""}),
        (
            parse_chat_message,
            {"resource": {"id": "message"}, "chat_id": "", "message_id": "message"},
        ),
        (
            parse_chat_message,
            {"resource": {"id": "message"}, "chat_id": "chat", "message_id": ""},
        ),
        (
            parse_chat_hosted_contents,
            {"resources": [], "chat_id": "", "message_id": "message"},
        ),
        (
            parse_chat_hosted_contents,
            {"resources": [], "chat_id": "chat", "message_id": ""},
        ),
    ],
)
def test_parsers_reject_malformed_request_scope(parser, args) -> None:
    with pytest.raises(ValueError):
        parser(**args)


def test_collection_parser_rejects_envelope_instead_of_reparsing_it() -> None:
    envelope = {"value": [{"id": "message"}]}
    with pytest.raises(GraphObjectTypeError):
        parse_chat_messages(envelope, chat_id="chat")
