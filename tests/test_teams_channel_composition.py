"""Exercise channel topology/message composition without application ownership."""

from dataclasses import fields, make_dataclass

import pytest
from itemadapter import ItemAdapter
from scrapy import Request
from scrapy.utils.request import request_from_dict
from twisted.python.failure import Failure

from microsoft_graph.fingerprints import GraphRequestFingerprinter
from microsoft_graph.items.teams.channel import TeamsChannelItem
from microsoft_graph.items.teams.content import TeamsHostedContentItem
from microsoft_graph.items.teams.membership import TeamsChannelMembershipItem
from microsoft_graph.items.teams.message import TeamsMessageItem
from microsoft_graph.protocol import GraphCollectionPage
from microsoft_graph.protocol.teams import TeamsAttachmentKind, TeamsMessageIdentity
from microsoft_graph.request import GRAPH_OPERATION_META_KEY
from microsoft_graph.spiders.teams.channel_composition import (
    MicrosoftTeamsChannelCompositionSpider,
    parse_channel_hosted_contents,
    parse_channel_replies,
    parse_channel_root_messages,
)


class ConsumerSpider(MicrosoftTeamsChannelCompositionSpider):
    """Provide named application-side callbacks for request serialization."""

    name = "teams-channel-composition-consumer"

    def parse_roots(self, response, **kwargs):
        """Application callback placeholder; provider helpers never invoke it."""

    def parse_replies(self, response, **kwargs):
        """Application callback placeholder; provider helpers never invoke it."""

    def parse_hosted(self, response, **kwargs):
        """Application callback placeholder; provider helpers never invoke it."""

    def failed(self, failure: Failure):
        """Application errback placeholder; provider helpers never invoke it."""


def _spider() -> ConsumerSpider:
    return ConsumerSpider()


def _reply_identity() -> TeamsMessageIdentity:
    return TeamsMessageIdentity.channel_reply(
        "reply/+%2F",
        team_id="host/+%",
        channel_id="channel/+%",
        root_message_id="root/+%",
    )


def test_message_requests_are_native_named_and_preserve_context_and_prefer():
    spider = _spider()
    context = {
        "host_team_id": "host",
        "receiving_team_id": "receiving",
        "channel_id": "channel",
        "page_number": 1,
    }
    root = spider.root_messages_request(
        "host",
        "channel",
        callback=spider.parse_roots,
        errback=spider.failed,
        cb_kwargs=context,
        operation="roots",
    )
    replies = spider.replies_request(
        "host",
        "channel",
        "root",
        callback=spider.parse_replies,
        errback=spider.failed,
        cb_kwargs=context,
        operation="replies",
    )
    detail = spider.message_detail_request(
        _reply_identity(),
        callback=spider.parse_replies,
        errback=spider.failed,
        cb_kwargs=context,
        operation="detail",
    )

    expected_urls = (
        (
            "https://graph.microsoft.com/v1.0/teams/host/channels/channel/"
            "messages?%24top=50"
        ),
        (
            "https://graph.microsoft.com/v1.0/teams/host/channels/channel/"
            "messages/root/replies?%24top=50"
        ),
        (
            "https://graph.microsoft.com/v1.0/teams/host%2F%2B%25/channels/"
            "channel%2F%2B%25/messages/root%2F%2B%25/replies/reply%2F%2B%252F"
        ),
    )
    for request, expected, operation in zip(
        (root, replies, detail),
        expected_urls,
        ("roots", "replies", "detail"),
        strict=True,
    ):
        if not isinstance(request, Request) or request.url != expected:
            pytest.fail("Composition did not return the expected native Request")
        if request.headers.get("Prefer") != b"include-unknown-enum-members":
            pytest.fail("Message request lost the frozen enum representation")
        if request.cb_kwargs != context:
            pytest.fail("Caller callback context was changed")
        if request.meta.get(GRAPH_OPERATION_META_KEY) != operation:
            pytest.fail("Caller operation context was changed")

    saved = root.to_dict(spider=spider)
    if saved.get("callback") != "parse_roots" or saved.get("errback") != "failed":
        pytest.fail("Application callbacks/errbacks must serialize by name")
    restored = request_from_dict(saved, spider=spider)
    if restored.callback != spider.parse_roots or restored.errback != spider.failed:
        pytest.fail("Named callbacks/errbacks did not restore on the consumer")


def test_message_continuation_is_byte_opaque_and_retains_representation_context():
    spider = _spider()
    next_link = (
        "https://graph.microsoft.com/v1.0/teams/t/channels/c/messages?"
        "%24skiptoken=a%2fb%2F%2f+%20&x=1&x=2"
    )
    context = {"host_team_id": "host", "channel_id": "channel", "page_number": 2}
    request = spider.message_continuation_request(
        next_link,
        callback=spider.parse_roots,
        errback=spider.failed,
        cb_kwargs=context,
        operation="roots",
    )
    if request.url != next_link or request.meta.get("verbatim_url") is not True:
        pytest.fail("Encoded nextLink bytes were normalized or rebuilt")
    if request.headers.get("Prefer") != b"include-unknown-enum-members":
        pytest.fail("Message continuation lost its representation header")
    if request.cb_kwargs != context:
        pytest.fail("Message continuation lost callback context")
    if request.meta.get(GRAPH_OPERATION_META_KEY) != "roots":
        pytest.fail("Message continuation lost operation context")


def test_request_fingerprints_distinguish_prefer_and_binary_representations():
    spider = _spider()
    fingerprinter = GraphRequestFingerprinter()
    root = spider.root_messages_request(
        "host",
        "channel",
        callback=spider.parse_roots,
        errback=spider.failed,
    )
    ordinary_root = root.replace(headers={"Accept": "application/json"})
    if fingerprinter.fingerprint(root) == fingerprinter.fingerprint(ordinary_root):
        pytest.fail("Prefer representation must affect Graph request identity")

    binary = spider.hosted_content_bytes_request(
        _reply_identity(),
        "hosted",
        callback=spider.parse_hosted,
        errback=spider.failed,
    )
    json_variant = binary.replace(
        headers={
            "Accept": "application/json",
            "ConsistencyLevel": "eventual",
        }
    )
    if fingerprinter.fingerprint(binary) == fingerprinter.fingerprint(json_variant):
        pytest.fail("Binary Accept representation must affect request identity")


def test_hosted_root_and_reply_paths_use_current_uncached_eventual_reads():
    spider = _spider()
    root_identity = TeamsMessageIdentity.channel_root(
        "root",
        team_id="host",
        channel_id="channel",
    )
    reply_identity = TeamsMessageIdentity.channel_reply(
        "reply",
        team_id="host",
        channel_id="channel",
        root_message_id="root",
    )
    root = spider.hosted_content_request(
        root_identity,
        "hosted",
        callback=spider.parse_hosted,
        errback=spider.failed,
    )
    reply = spider.hosted_content_request(
        reply_identity,
        "hosted",
        callback=spider.parse_hosted,
        errback=spider.failed,
    )
    binary = spider.hosted_content_bytes_request(
        reply_identity,
        "hosted",
        callback=spider.parse_hosted,
        errback=spider.failed,
    )

    if root.url != (
        "https://graph.microsoft.com/v1.0/teams/host/channels/channel/"
        "messages/root/hostedContents/hosted"
    ):
        pytest.fail("Root hosted-content path lost root scope")
    if reply.url != (
        "https://graph.microsoft.com/v1.0/teams/host/channels/channel/"
        "messages/root/replies/reply/hostedContents/hosted"
    ):
        pytest.fail("Reply hosted-content path lost traversal root/reply scope")
    if binary.url != reply.url + "/$value":
        pytest.fail("Hosted bytes must use the scoped hosted-item $value path")
    for request in (root, reply, binary):
        if request.headers.get("ConsistencyLevel") != b"eventual":
            pytest.fail("Hosted item/byte read lost ConsistencyLevel eventual")
        if request.meta.get("dont_cache") is not True:
            pytest.fail("Hosted item/byte read must deliberately bypass cache")
        if "etag" in request.url.lower() or "version" in request.url.lower():
            pytest.fail("Hosted requests must not invent a message-version selector")
    if binary.headers.get("Accept") != b"application/octet-stream":
        pytest.fail("Hosted bytes must request a binary representation")
    if root.headers.get("Accept") != b"application/json":
        pytest.fail("Hosted metadata item must retain the JSON representation")


def test_hosted_collection_continuation_is_opaque_and_keeps_caller_context():
    spider = _spider()
    identity = _reply_identity()
    request = spider.hosted_contents_request(
        identity,
        callback=spider.parse_hosted,
        errback=spider.failed,
        cb_kwargs={"message_scope": identity.scope_key, "page_number": 1},
    )
    expected = (
        "https://graph.microsoft.com/v1.0/teams/host%2F%2B%25/channels/"
        "channel%2F%2B%25/messages/root%2F%2B%25/replies/"
        "reply%2F%2B%252F/hostedContents"
    )
    if request.url != expected:
        pytest.fail("Hosted reply collection path changed")

    next_link = (
        "https://graph.microsoft.com/v1.0/teams/t/messages/m/hostedContents?"
        "%24skiptoken=%2F%2f+a%20b&same=1&same=2"
    )
    context = {"message_scope": identity.scope_key, "page_number": 2}
    continuation = spider.hosted_contents_continuation_request(
        next_link,
        callback=spider.parse_hosted,
        errback=spider.failed,
        cb_kwargs=context,
    )
    if continuation.url != next_link:
        pytest.fail("Hosted continuation URL was modified")
    if continuation.meta.get("verbatim_url") is not True:
        pytest.fail("Hosted continuation must use continuation_request")
    if continuation.cb_kwargs != context:
        pytest.fail("Hosted continuation lost application callback context")
    if continuation.headers.get("Prefer") is not None:
        pytest.fail("Hosted metadata does not inherit message enum preference")


def test_common_parser_preserves_root_reply_scope_raw_fidelity_and_subclass_kwargs():
    observed = make_dataclass(
        "ObservedChannelMessage",
        [("evidence_id", str), ("run_id", str)],
        bases=(TeamsMessageItem,),
        slots=True,
    )
    raw_root = {
        "id": "duplicate",
        "scope": "",
        "webUrl": "https://teams.example.invalid/message?x=%2F+%20",
        "attachments": [
            {
                "id": "ref",
                "contentType": "reference",
                "contentUrl": "https://sharepoint.example.invalid/file",
                "content": {"future": False},
            }
        ],
        "future": {"unknown": [0, False, ""]},
    }
    raw_reply = {
        "id": "duplicate",
        "replyToId": "payload-root",
        "channelIdentity": {"teamId": "provider-team", "channelId": ""},
        "future": False,
    }
    root_page = GraphCollectionPage.from_payload({"value": [raw_root]})
    reply_page = GraphCollectionPage.from_payload({"value": [raw_reply]})
    root = parse_channel_root_messages(
        root_page.values,
        host_team_id="host-team",
        channel_id="channel",
        item_type=observed,
        evidence_id="root-evidence",
        run_id="run",
    )[0]
    reply = parse_channel_replies(
        reply_page.values,
        host_team_id="host-team",
        channel_id="channel",
        root_message_id="path-root",
        item_type=observed,
        evidence_id="reply-evidence",
        run_id="run",
    )[0]

    if root.raw is not raw_root or reply.raw is not raw_reply:
        pytest.fail("Composition copied or normalized common message JSON")
    if root.identity.scope_key == reply.identity.scope_key:
        pytest.fail("Root and reply scoped identities collapsed")
    if reply.identity.root_message_id != "path-root":
        pytest.fail("Reply identity must use traversal-path root context")
    if reply.reply_to_id != "payload-root":
        pytest.fail("Provider replyToId must remain an independent payload fact")
    if (
        ItemAdapter(root)["evidence_id"],
        ItemAdapter(reply)["evidence_id"],
        ItemAdapter(reply)["run_id"],
    ) != (
        "root-evidence",
        "reply-evidence",
        "run",
    ):
        pytest.fail("Application subclass kwargs were not forwarded")
    attachment = root.attachment_items[0]
    if attachment.kind is not TeamsAttachmentKind.REFERENCE:
        pytest.fail("Common attachment taxonomy was bypassed")
    if attachment.content_url != raw_root["attachments"][0]["contentUrl"]:
        pytest.fail("Reference URL metadata changed")
    for forbidden in ("request", "fetch_url", "download_url"):
        if hasattr(attachment, forbidden):
            pytest.fail("File reference must remain not-attempted metadata")


def test_hosted_parser_consumes_page_values_and_supports_application_subclass():
    observed = make_dataclass(
        "ObservedHostedContent",
        [("evidence_id", str)],
        bases=(TeamsHostedContentItem,),
        slots=True,
    )
    identity = _reply_identity()
    raw = {
        "id": "hosted/+%2F",
        "contentType": "",
        "contentBytes": "",
        "future": {"unknown": False},
    }
    page = GraphCollectionPage.from_payload({"value": [raw]})
    item = parse_channel_hosted_contents(
        page.values,
        message_identity=identity,
        item_type=observed,
        evidence_id="evidence",
    )[0]
    if item.raw is not raw or item.message_identity is not identity:
        pytest.fail("Common hosted parser lost raw JSON or channel scope")
    if (
        item.content_type,
        item.content_bytes,
        ItemAdapter(item)["evidence_id"],
    ) != (
        "",
        "",
        "evidence",
    ):
        pytest.fail("Hosted falsey fields or subclass kwargs were changed")
    forbidden = {"message_etag", "provider_version", "triggering_version"}
    if forbidden.intersection(value.name for value in fields(item)):
        pytest.fail("Hosted metadata invented a historical message-version claim")


def test_incoming_channel_uses_host_for_content_and_keeps_receiving_topology():
    channel = TeamsChannelItem.from_incoming(
        {"id": "channel", "tenantId": "host-tenant"},
        host_team_id="host-team",
        host_tenant_id="host-tenant",
        receiving_team_id="receiving-team",
        receiving_tenant_id="receiving-tenant",
    )
    message = parse_channel_root_messages(
        [{"id": "message"}],
        host_team_id=channel.host_team_id,
        channel_id=channel.channel_id,
    )[0]
    if message.identity.scope_key != (
        "channel-root",
        "host-team",
        "channel",
        "message",
    ):
        pytest.fail("Channel content scope used the receiving team")
    if (
        channel.receiving_team_id,
        channel.receiving_tenant_id,
        channel.host_team_id,
    ) != ("receiving-team", "receiving-tenant", "host-team"):
        pytest.fail("Host and receiving topology contexts were conflated")


def test_membership_paths_remain_multiplicity_preserving_in_composed_context():
    first = TeamsChannelMembershipItem.from_all_members(
        {
            "id": "same-membership",
            "userId": "same-user",
            "@microsoft.graph.originalSourceMembershipUrl": "source-a",
        },
        host_team_id="host-team",
        channel_id="channel",
    )
    second = TeamsChannelMembershipItem.from_all_members(
        {
            "id": "same-membership",
            "userId": "same-user",
            "@microsoft.graph.originalSourceMembershipUrl": "source-b",
        },
        host_team_id="host-team",
        channel_id="channel",
    )
    paths = (first, second)
    if len(paths) != 2 or paths[0].user_id != paths[1].user_id:
        pytest.fail("Fixture no longer exercises repeated membership identity")
    if (
        paths[0].original_source_membership_url
        == paths[1].original_source_membership_url
    ):
        pytest.fail("Repeated allMembers access paths were collapsed")


def test_malformed_channel_scope_and_collection_context_fail_closed():
    spider = _spider()
    with pytest.raises(ValueError):
        parse_channel_root_messages(
            [{"id": "message"}],
            host_team_id="",
            channel_id="channel",
        )
    with pytest.raises(ValueError):
        parse_channel_replies(
            [{"id": "reply"}],
            host_team_id="host",
            channel_id="channel",
            root_message_id="",
        )
    with pytest.raises(ValueError):
        spider.message_detail_request(
            TeamsMessageIdentity.chat("message", chat_id="chat"),
            callback=spider.parse_roots,
            errback=spider.failed,
        )
    with pytest.raises(TypeError):
        spider.hosted_contents_request(
            "not-an-identity",  # type: ignore[arg-type]
            callback=spider.parse_hosted,
            errback=spider.failed,
        )
    with pytest.raises(TypeError):
        parse_channel_hosted_contents(
            False,  # type: ignore[arg-type]
            message_identity=_reply_identity(),
        )
