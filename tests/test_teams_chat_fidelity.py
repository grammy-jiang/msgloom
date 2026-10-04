"""Prove Teams chat message fidelity and reference boundaries through storage."""

from pathlib import Path

import pytest
from sqlalchemy import select
from teams_support import GraphFixture, crawl, json_reply

from message_ingest.catalog.models.microsoft.teams import (
    TeamsMessageAttachmentObservation,
    TeamsMessageObservation,
    TeamsReferenceResolutionObservation,
    TeamsTopologyObservation,
)
from message_ingest.catalog.store import Catalog

pytest_plugins = ("teams_support",)

CHAT_SETTINGS = {"SPIDER_MODULES": "message_ingest.spiders.microsoft.teams"}


def test_message_fidelity_and_reference_taxonomy_survive_real_crawl(
    tmp_path: Path,
    graph_fixture: GraphFixture,
) -> None:
    """Store system/message/reference/card forms without fetching file URLs."""
    forbidden_file_target = "/unselected-file-profile/content"
    attachments = [
        {
            "id": "file-ref",
            "contentType": "reference",
            "contentUrl": graph_fixture.url(forbidden_file_target),
            "name": "linked.docx",
        },
        {
            "id": "forward",
            "contentType": "forwardedMessageReference",
            "content": '{"messageId":"forwarded"}',
        },
        {
            "id": "reply",
            "contentType": "messageReference",
            "content": '{"messageId":"earlier-chat-message"}',
        },
        {
            "id": "meeting",
            "contentType": "meetingReference",
            "content": '{"eventId":"exchange-event"}',
        },
        {
            "id": "tab",
            "contentType": "tabReference",
            "content": '{"tabId":"tab-a"}',
        },
        {
            "id": "loop",
            "contentType": "application/vnd.microsoft.card.fluidEmbedCard",
            "content": '{"component":"loop"}',
        },
        {
            "id": "code",
            "contentType": "application/vnd.microsoft.card.codesnippet",
            "content": '{"language":"python"}',
        },
        {
            "id": "announcement",
            "contentType": "application/vnd.microsoft.card.announcement",
            "content": '{"title":"notice"}',
        },
        {
            "id": "card",
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": '{"type":"AdaptiveCard"}',
        },
        {
            "id": "unknown",
            "contentType": "application/x-future-teams-card",
            "content": '{"future":true}',
            "teamsAppId": "app-a",
        },
    ]
    message = {
        "id": "message-fidelity",
        "etag": "etag-fidelity",
        "messageType": "systemEventMessage",
        "eventDetail": {
            "@odata.type": "#microsoft.graph.membersAddedEventMessageDetail"
        },
        "from": {"user": {"id": "sender-a"}},
        "onBehalfOf": {"user": {"id": "delegate-a"}},
        "body": {
            "contentType": "html",
            "content": '<p>Hello <emoji id="custom-emoji"/></p>',
        },
        "mentions": [
            {
                "id": 0,
                "mentionText": "Foreign User",
                "mentioned": {
                    "user": {"id": "foreign-user", "tenantId": "foreign-tenant"}
                },
            }
        ],
        "reactions": [
            {
                "reactionType": "heart",
                "createdDateTime": "2026-10-04T01:00:00Z",
                "user": {"user": {"id": "reactor-a"}},
            }
        ],
        "messageHistory": [
            {
                "actions": "reactionAdded",
                "modifiedDateTime": "2026-10-04T01:01:00Z",
                "reaction": {"reactionType": "heart"},
            }
        ],
        "attachments": attachments,
        "scope": "chat",
        "webUrl": "https://teams.invalid/message",
    }
    graph_fixture.add(
        "/v1.0/me/chats?%24top=50",
        json_reply({"value": [{"id": "chat-fidelity", "chatType": "group"}]}),
    )
    graph_fixture.add(
        "/v1.0/chats/chat-fidelity/members",
        json_reply({"value": []}),
    )
    graph_fixture.add(
        "/v1.0/chats/chat-fidelity/messages?%24top=50",
        json_reply({"value": [message]}),
    )
    graph_fixture.add(
        "/v1.0/chats/chat-fidelity/messages/message-fidelity/hostedContents",
        json_reply({"value": []}),
    )
    graph_fixture.add(
        "/v1.0/chats/chat-fidelity/pinnedMessages",
        json_reply({"value": []}),
    )

    result = crawl(
        tmp_path,
        graph_fixture,
        ["crawl", "microsoft_teams_chat_discover"],
        extra_settings=CHAT_SETTINGS,
    )
    if result.returncode != 0:
        pytest.fail(result.stderr)
    if forbidden_file_target in [seen.target for seen in graph_fixture.seen]:
        pytest.fail("Core chat discovery fetched an arbitrary attachment contentUrl")

    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            stored_message = session.scalar(select(TeamsMessageObservation))
            stored_attachments = session.scalars(
                select(TeamsMessageAttachmentObservation).order_by(
                    TeamsMessageAttachmentObservation.ordinal
                )
            ).all()
            resolutions = session.scalars(
                select(TeamsReferenceResolutionObservation)
            ).all()
            topology = session.scalars(select(TeamsTopologyObservation)).all()
        if stored_message is None:
            pytest.fail("Fidelity message was not persisted")
        if (
            stored_message.location != "chat"
            or stored_message.root_message_id is not None
        ):
            pytest.fail(
                "Chat messageReference was mis-modeled as channel reply topology"
            )
        raw = stored_message.raw
        if raw.get("eventDetail") != message["eventDetail"]:
            pytest.fail("System-event detail was not preserved losslessly")
        if raw.get("mentions") != message["mentions"]:
            pytest.fail("Mention identity payload was changed")
        if raw.get("reactions") != message["reactions"]:
            pytest.fail("Reaction payload was changed")
        if raw.get("messageHistory") != message["messageHistory"]:
            pytest.fail("messageHistory action records were changed")
        if raw.get("body") != message["body"]:
            pytest.fail("Custom emoji/body content was changed")

        expected_kinds = [
            "reference",
            "forwarded-message-reference",
            "message-reference",
            "meeting-reference",
            "tab-reference",
            "loop-card",
            "code-card",
            "announcement-card",
            "card",
            "unknown",
        ]
        if [row.kind for row in stored_attachments] != expected_kinds:
            pytest.fail("Stored attachment taxonomy did not preserve all frozen forms")
        if [row.raw for row in stored_attachments] != attachments:
            pytest.fail("Stored crawl output changed attachment provider dictionaries")
        if len(resolutions) != 1:
            pytest.fail(
                "Only the broad file reference needs an explicit resolution fact"
            )
        resolution = resolutions[0]
        if resolution.attachment_ordinal != 0 or resolution.state != "not-attempted":
            pytest.fail("Unselected file profile must remain explicitly not-attempted")
        if resolution.details.get("reason") != "broad-file-profile-disabled":
            pytest.fail("Reference limitation reason was not explicit")
        if any(row.resource_kind.startswith("channel") for row in topology):
            pytest.fail("Chat reference fidelity invented channel reply topology")
    finally:
        catalog.close()
