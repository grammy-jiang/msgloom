"""Pin Teams message scope identity and attachment taxonomy."""

import pytest

from microsoft_graph.protocol.teams import (
    TeamsAttachmentKind,
    TeamsMessageIdentity,
    TeamsMessageLocation,
    classify_teams_attachment,
)


def test_scoped_message_identity_preserves_opaque_ids_and_duplicates():
    message_id = "same/+%2F ?é"
    chat = TeamsMessageIdentity.chat(message_id, chat_id="chat/+%")
    root = TeamsMessageIdentity.channel_root(
        message_id,
        team_id="team/+%",
        channel_id="channel/%2f",
    )
    reply = TeamsMessageIdentity.channel_reply(
        message_id,
        team_id="team/+%",
        channel_id="channel/%2f",
        root_message_id="root/+%2F",
    )

    if chat.message_id != message_id or chat.chat_id != "chat/+%":
        pytest.fail("Chat message IDs were normalized")
    if root.scope_key == reply.scope_key or chat.scope_key == root.scope_key:
        pytest.fail("Duplicate message IDs must remain distinct across scopes")
    if reply.scope_key != (
        "channel-reply",
        "team/+%",
        "channel/%2f",
        "root/+%2F",
        message_id,
    ):
        pytest.fail("Reply identity lost an opaque parent ID")


@pytest.mark.parametrize(
    "factory,kwargs",
    [
        (TeamsMessageIdentity.chat, {"chat_id": ""}),
        (
            TeamsMessageIdentity.channel_root,
            {"team_id": "", "channel_id": "channel"},
        ),
        (
            TeamsMessageIdentity.channel_root,
            {"team_id": "team", "channel_id": ""},
        ),
        (
            TeamsMessageIdentity.channel_reply,
            {
                "team_id": "team",
                "channel_id": "channel",
                "root_message_id": "",
            },
        ),
    ],
)
def test_scoped_message_identity_rejects_missing_parent_ids(factory, kwargs):
    with pytest.raises(ValueError):
        factory("message", **kwargs)


def test_scoped_message_identity_rejects_mixed_context():
    with pytest.raises(ValueError):
        TeamsMessageIdentity(
            location=TeamsMessageLocation.CHAT,
            message_id="message",
            chat_id="chat",
            team_id="team",
        )
    with pytest.raises(ValueError):
        TeamsMessageIdentity(
            location=TeamsMessageLocation.CHANNEL_ROOT,
            message_id="message",
            team_id="team",
            channel_id="channel",
            root_message_id="root",
        )


@pytest.mark.parametrize(
    "content_type,expected",
    [
        ("reference", TeamsAttachmentKind.REFERENCE),
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
        (
            "application/vnd.microsoft.card.codeSnippet",
            TeamsAttachmentKind.CODE_CARD,
        ),
        (
            "application/vnd.microsoft.card.announcement",
            TeamsAttachmentKind.ANNOUNCEMENT_CARD,
        ),
        (
            "application/vnd.microsoft.card.adaptive",
            TeamsAttachmentKind.CARD,
        ),
        ("application/x-future-card", TeamsAttachmentKind.UNKNOWN),
        ("", TeamsAttachmentKind.UNKNOWN),
        (False, TeamsAttachmentKind.UNKNOWN),
        (None, TeamsAttachmentKind.UNKNOWN),
    ],
)
def test_attachment_taxonomy_is_additive_and_unknown_safe(content_type, expected):
    actual = classify_teams_attachment(content_type)
    if actual is not expected:
        pytest.fail(f"Unexpected attachment classification: {actual!r}")


def test_attachment_classifier_does_not_rewrite_provider_value():
    content_type = "application/VND.MICROSOFT.CARD.FLUIDEMBEDCARD"
    actual = classify_teams_attachment(content_type)
    if actual is not TeamsAttachmentKind.LOOP_CARD:
        pytest.fail("Known card classification should be case-insensitive")
    if content_type != "application/VND.MICROSOFT.CARD.FLUIDEMBEDCARD":
        pytest.fail("Classifier mutated provider contentType")
