"""Verify Teams attachment and hosted-content fidelity without fetching."""

from dataclasses import fields

import pytest
from itemadapter import ItemAdapter

from microsoft_graph.items.teams.content import (
    TeamsHostedContentItem,
    TeamsMessageAttachmentItem,
    parse_hosted_contents,
    parse_message_attachments,
)
from microsoft_graph.protocol.teams import TeamsAttachmentKind, TeamsMessageIdentity


def _identity() -> TeamsMessageIdentity:
    return TeamsMessageIdentity.chat("message/+%2F", chat_id="chat/+%")


def test_attachment_preserves_raw_fields_and_reference_url_only():
    raw = {
        "id": "",
        "contentType": "reference",
        "contentUrl": "https://contoso.example/file?x=%2F+%20",
        "content": "",
        "name": "",
        "thumbnailUrl": False,
        "teamsAppId": 0,
        "future": {"nested": [0, False, "", {"x": None}]},
    }
    item = TeamsMessageAttachmentItem.from_graph(
        raw,
        message_identity=_identity(),
    )

    if item.raw is not raw or ItemAdapter(item).asdict()["raw"] != raw:
        pytest.fail("Attachment raw provider JSON was changed")
    if item.content_url is not raw["contentUrl"] or item.content != "":
        pytest.fail("Attachment reference metadata was normalized")
    if (item.name, item.thumbnail_url, item.teams_app_id) != ("", False, 0):
        pytest.fail("Falsey attachment metadata was lost")
    if item.kind is not TeamsAttachmentKind.REFERENCE:
        pytest.fail("Reference attachment taxonomy was lost")
    for forbidden in ("fetch_url", "request", "download_url"):
        if hasattr(item, forbidden):
            pytest.fail("Attachment metadata must not become a fetch target")


@pytest.mark.parametrize(
    "content_type,expected",
    [
        (
            "forwardedMessageReference",
            TeamsAttachmentKind.FORWARDED_MESSAGE_REFERENCE,
        ),
        ("messageReference", TeamsAttachmentKind.MESSAGE_REFERENCE),
        ("meetingReference", TeamsAttachmentKind.MEETING_REFERENCE),
        ("tabReference", TeamsAttachmentKind.TAB_REFERENCE),
        (
            "application/vnd.microsoft.card.fluidEmbedCard",
            TeamsAttachmentKind.LOOP_CARD,
        ),
        ("application/x-unknown", TeamsAttachmentKind.UNKNOWN),
    ],
)
def test_attachment_parser_keeps_known_and_unknown_content_types(
    content_type,
    expected,
):
    raw = {
        "id": "attachment",
        "contentType": content_type,
        "content": {"future": False},
    }
    item = parse_message_attachments([raw], message_identity=_identity())[0]
    if item.content_type != content_type or item.kind is not expected:
        pytest.fail("Attachment contentType was not preserved and classified")
    if item.raw["content"] is not raw["content"]:
        pytest.fail("Unknown attachment content was copied or interpreted")


def test_attachment_collection_rejects_malformed_known_collection_shape():
    with pytest.raises(TypeError):
        parse_message_attachments(False, message_identity=_identity())
    with pytest.raises(TypeError):
        parse_message_attachments(["not-an-object"], message_identity=_identity())


def test_hosted_content_preserves_metadata_without_message_version_claim():
    raw = {
        "id": "hosted/+%2F",
        "contentType": "",
        "contentBytes": "",
        "future": {"falsey": [False, 0, ""]},
    }
    item = TeamsHostedContentItem.from_graph(
        raw,
        message_identity=_identity(),
    )
    if item.raw is not raw or item.hosted_content_id != "hosted/+%2F":
        pytest.fail("Hosted-content identity or raw JSON changed")
    if (item.content_type, item.content_bytes) != ("", ""):
        pytest.fail("Falsey hosted-content metadata was normalized")

    forbidden = {
        "evidence_id",
        "message_etag",
        "provider_version",
        "triggering_version",
    }
    actual_fields = {value.name for value in fields(TeamsHostedContentItem)}
    if forbidden.intersection(actual_fields):
        pytest.fail("Hosted content must not claim an exact message version")


def test_hosted_collection_keeps_scoped_message_identity():
    identity = TeamsMessageIdentity.channel_reply(
        "reply",
        team_id="team",
        channel_id="channel",
        root_message_id="root",
    )
    raw = {"id": "hosted", "contentType": "image/png", "unknown": False}
    item = parse_hosted_contents([raw], message_identity=identity)[0]
    if item.message_identity is not identity or item.raw is not raw:
        pytest.fail("Hosted metadata lost message scope or provider object")


@pytest.mark.parametrize("raw", [None, [], {}, {"id": ""}, {"id": False}])
def test_hosted_content_rejects_unstable_resource_identity(raw):
    with pytest.raises((TypeError, ValueError)):
        TeamsHostedContentItem.from_graph(
            raw,
            message_identity=_identity(),
        )
