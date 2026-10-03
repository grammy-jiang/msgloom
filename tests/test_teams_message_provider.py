"""Exercise common Teams chatMessage parsing and scoped fidelity."""

import subprocess
import sys
from dataclasses import fields

import pytest
from itemadapter import ItemAdapter

from microsoft_graph.items.teams.message import (
    TeamsMessageHistoryEntry,
    TeamsMessageItem,
    TeamsMessageMention,
    TeamsMessageReaction,
    TeamsMessageVersionFacts,
)
from microsoft_graph.protocol.teams import TeamsAttachmentKind, TeamsMessageIdentity


def _full_message() -> dict:
    return {
        "id": "message/+%2F",
        "etag": 'W/"version/+%"',
        "createdDateTime": "2026-10-03T01:02:03Z",
        "lastModifiedDateTime": "",
        "lastEditedDateTime": None,
        "deletedDateTime": "",
        "messageType": "systemEventMessage",
        "eventDetail": {
            "@odata.type": "#microsoft.graph.membersAddedEventMessageDetail",
            "members": [{"id": "member", "future": False}],
        },
        "from": {"user": {"id": "sender", "displayName": ""}},
        "onBehalfOf": {"user": {"id": "delegate", "tenantId": ""}},
        "body": {"contentType": "html", "content": ""},
        "mentions": [
            {
                "id": 0,
                "mentionText": "",
                "mentioned": {"user": {"id": "mentioned", "future": 0}},
                "future": False,
            }
        ],
        "reactions": [
            {
                "reactionType": "like",
                "createdDateTime": "",
                "user": {"user": {"id": "reactor"}},
                "future": [],
            }
        ],
        "messageHistory": [
            {
                "actions": [],
                "modifiedDateTime": "",
                "reaction": {"reactionType": "like", "future": False},
                "body": {"content": "unknown-future-provider-field"},
            }
        ],
        "importance": "",
        "subject": "",
        "summary": "",
        "scope": "futureScope",
        "webUrl": "https://teams.example.invalid/l/message?x=%2F+%20",
        "replyToId": "",
        "chatId": "",
        "channelIdentity": {"teamId": "", "channelId": "", "future": False},
        "locale": "",
        "policyViolation": {"future": False},
        "attachments": [
            {
                "id": "attachment",
                "contentType": "messageReference",
                "contentUrl": "https://teams.example.invalid/reference",
                "content": {"messageId": "other", "future": False},
            }
        ],
        "future": {"nested": [0, False, "", {"x": None}]},
    }


def test_message_preserves_raw_provider_fidelity_and_version_facts():
    raw = _full_message()
    item = TeamsMessageItem.from_chat_graph(raw, chat_id="chat/+%")

    if item.raw is not raw or ItemAdapter(item).asdict()["raw"] != raw:
        pytest.fail("Message raw provider JSON was changed")
    if item.message_id != raw["id"] or item.etag != raw["etag"]:
        pytest.fail("Message or provider etag identity was lost")
    if item.version_facts != TeamsMessageVersionFacts(
        etag=raw["etag"],
        created_date_time=raw["createdDateTime"],
        last_modified_date_time=raw["lastModifiedDateTime"],
        last_edited_date_time=raw["lastEditedDateTime"],
        deleted_date_time=raw["deletedDateTime"],
    ):
        pytest.fail("Observed provider version facts changed")

    object_fields = {
        "event_detail": "eventDetail",
        "sender": "from",
        "on_behalf_of": "onBehalfOf",
        "body": "body",
        "mentions": "mentions",
        "reactions": "reactions",
        "message_history": "messageHistory",
        "channel_identity": "channelIdentity",
        "policy_violation": "policyViolation",
        "attachments": "attachments",
    }
    for field_name, raw_name in object_fields.items():
        if getattr(item, field_name) is not raw[raw_name]:
            pytest.fail(f"Nested provider field {raw_name} was copied or changed")

    if (item.body_content_type, item.body_content) != ("html", ""):
        pytest.fail("Falsey message body content was normalized")
    if (item.importance, item.subject, item.summary) != ("", "", ""):
        pytest.fail("Falsey scalar message fields were normalized")
    if (item.scope, item.web_url, item.reply_to_id) != (
        raw["scope"],
        raw["webUrl"],
        "",
    ):
        pytest.fail("scope, webUrl, or replyToId was not preserved")
    if hasattr(item, "fetch_url") or hasattr(item, "request"):
        pytest.fail("Message webUrl must remain metadata, not a crawl target")


def test_message_projects_sender_system_event_mentions_reactions_and_attachments():
    raw = _full_message()
    item = TeamsMessageItem.from_chat_graph(raw, chat_id="chat")

    if item.message_type != "systemEventMessage":
        pytest.fail("System-event message type was lost")
    if item.event_detail is not raw["eventDetail"]:
        pytest.fail("System-event detail was transformed")
    mention = item.mention_items[0]
    if (
        mention.raw is not raw["mentions"][0]
        or mention.mention_id != 0
        or mention.mention_text != ""
        or mention.mentioned is not raw["mentions"][0]["mentioned"]
    ):
        pytest.fail("Mention identity or falsey values changed")
    reaction = item.reaction_items[0]
    if (
        reaction.raw is not raw["reactions"][0]
        or reaction.reaction_type != "like"
        or reaction.created_date_time != ""
        or reaction.user is not raw["reactions"][0]["user"]
    ):
        pytest.fail("Reaction provider values changed")
    attachment = item.attachment_items[0]
    if attachment.raw is not raw["attachments"][0]:
        pytest.fail("Embedded attachment provider JSON was copied")
    if attachment.kind is not TeamsAttachmentKind.MESSAGE_REFERENCE:
        pytest.fail("messageReference taxonomy was not retained")


def test_message_history_is_action_history_not_old_body_history():
    raw = _full_message()
    item = TeamsMessageItem.from_chat_graph(raw, chat_id="chat")
    history = item.history_items[0]

    if history.raw is not raw["messageHistory"][0]:
        pytest.fail("messageHistory raw record was changed")
    if (history.actions, history.modified_date_time) != ([], ""):
        pytest.fail("messageHistory falsey action fields were normalized")
    if history.reaction is not raw["messageHistory"][0]["reaction"]:
        pytest.fail("messageHistory reaction metadata was transformed")
    if hasattr(history, "body"):
        pytest.fail("messageHistory must not be projected as an old message body")
    if history.raw.get("body") != {"content": "unknown-future-provider-field"}:
        pytest.fail("Unknown history fields must remain available in raw JSON")


def test_same_message_id_remains_distinct_in_chat_root_and_reply_scopes():
    payload = {"id": "duplicate", "replyToId": "provider-root"}
    chat = TeamsMessageItem.from_chat_graph(payload.copy(), chat_id="chat")
    root = TeamsMessageItem.from_channel_root_graph(
        payload.copy(),
        team_id="team",
        channel_id="channel",
    )
    reply = TeamsMessageItem.from_channel_reply_graph(
        payload.copy(),
        team_id="team",
        channel_id="channel",
        root_message_id="path-root",
    )

    keys = {chat.identity.scope_key, root.identity.scope_key, reply.identity.scope_key}
    if len(keys) != 3:
        pytest.fail("Duplicate provider message IDs collapsed across scopes")
    if reply.identity.root_message_id != "path-root":
        pytest.fail("Reply scope must retain the traversal-path root ID")
    if reply.reply_to_id != "provider-root":
        pytest.fail("Provider replyToId must survive independently of path scope")


def test_deletion_marker_preserves_missing_and_explicit_falsey_distinction():
    missing = TeamsMessageItem.from_chat_graph({"id": "one"}, chat_id="chat")
    explicit = TeamsMessageItem.from_chat_graph(
        {"id": "two", "deletedDateTime": ""},
        chat_id="chat",
    )
    if missing.deleted_date_time is not None:
        pytest.fail("Missing deletedDateTime must remain absent")
    if explicit.deleted_date_time != "":
        pytest.fail("Explicit falsey deletedDateTime must be preserved")


@pytest.mark.parametrize("raw", [None, [], {}, {"id": ""}, {"id": False}])
def test_message_rejects_unstable_resource_identity(raw):
    with pytest.raises((TypeError, ValueError)):
        TeamsMessageItem.from_chat_graph(raw, chat_id="chat")


def test_message_rejects_identity_mismatch_and_malformed_embedded_lists():
    identity = TeamsMessageIdentity.chat("expected", chat_id="chat")
    with pytest.raises(ValueError):
        TeamsMessageItem.from_graph({"id": "actual"}, identity=identity)
    with pytest.raises(TypeError):
        TeamsMessageItem.from_chat_graph(
            {"id": "message", "mentions": False},
            chat_id="chat",
        )
    with pytest.raises(TypeError):
        TeamsMessageItem.from_chat_graph(
            {"id": "message", "messageHistory": ["bad"]},
            chat_id="chat",
        )


def test_provider_items_exclude_application_evidence_and_run_state():
    providers = [
        TeamsMessageItem,
        TeamsMessageVersionFacts,
        TeamsMessageMention,
        TeamsMessageReaction,
        TeamsMessageHistoryEntry,
    ]
    forbidden = {"evidence_id", "run_id", "source_id", "observed_at"}
    for provider in providers:
        names = {value.name for value in fields(provider)}
        if forbidden.intersection(names):
            pytest.fail(f"Application state leaked into {provider.__name__}")


def test_message_provider_imports_without_application_or_sqlalchemy():
    code = """
import importlib.abc
import sys

class ForbidApplication(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"message_ingest", "msgloom", "sqlalchemy"}:
            raise ImportError(f"Forbidden dependency: {fullname}")
        return None

sys.meta_path.insert(0, ForbidApplication())
from microsoft_graph.items.teams.content import TeamsHostedContentItem
from microsoft_graph.items.teams.message import TeamsMessageItem
from microsoft_graph.protocol.teams import TeamsMessageIdentity

message = TeamsMessageItem.from_chat_graph({"id": "m"}, chat_id="c")
TeamsHostedContentItem.from_graph(
    {"id": "h"},
    message_identity=message.identity,
)
TeamsMessageIdentity.channel_reply(
    "r",
    team_id="t",
    channel_id="c",
    root_message_id="root",
)
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if result.returncode:
        pytest.fail(result.stderr)
