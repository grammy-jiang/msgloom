"""Lossless common chatMessage projections for chats and channels."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Self

from microsoft_graph.items.teams.content import (
    TeamsMessageAttachmentItem,
    parse_message_attachments,
)
from microsoft_graph.protocol import GraphObjectTypeError, graph_object
from microsoft_graph.protocol.teams import TeamsMessageIdentity


def _embedded_objects(value: Any, *, context: str) -> tuple[dict[str, Any], ...]:
    """Validate a present embedded list without copying provider objects."""
    if value is None:
        return ()
    if not isinstance(value, list):
        raise GraphObjectTypeError(f"{context} must be a JSON array")
    return tuple(graph_object(entry, context=f"{context} entry") for entry in value)


def _message_raw(resource: Any, identity: TeamsMessageIdentity) -> dict[str, Any]:
    """Validate object identity and its caller-supplied Graph path scope."""
    raw = graph_object(resource, context="Teams chatMessage")
    message_id = raw.get("id")
    if not isinstance(message_id, str) or not message_id:
        raise ValueError("Teams chatMessage requires a non-empty id")
    if message_id != identity.message_id:
        raise ValueError("Teams chatMessage id does not match scoped identity")
    return raw


def _resource_message_id(resource: Any) -> tuple[dict[str, Any], str]:
    """Read an opaque message ID before constructing its path scope."""
    raw = graph_object(resource, context="Teams chatMessage")
    message_id = raw.get("id")
    if not isinstance(message_id, str) or not message_id:
        raise ValueError("Teams chatMessage requires a non-empty id")
    return raw, message_id


@dataclass(frozen=True, slots=True)
class TeamsMessageVersionFacts:
    """
    Retain provider version and lifecycle facts from one observed message.

    These values identify what Graph returned. They are not an application
    evidence ID and do not claim that unobserved historical bodies are known.
    """

    etag: Any
    created_date_time: Any
    last_modified_date_time: Any
    last_edited_date_time: Any
    deleted_date_time: Any

    @classmethod
    def from_graph(cls, raw: dict[str, Any]) -> TeamsMessageVersionFacts:
        """Project provider facts without parsing or normalizing timestamps."""
        return cls(
            etag=raw.get("etag"),
            created_date_time=raw.get("createdDateTime"),
            last_modified_date_time=raw.get("lastModifiedDateTime"),
            last_edited_date_time=raw.get("lastEditedDateTime"),
            deleted_date_time=raw.get("deletedDateTime"),
        )


@dataclass(slots=True)
class TeamsMessageMention:
    """Preserve one mention and its nested identity payload."""

    message_identity: TeamsMessageIdentity
    raw: dict[str, Any]
    mention_id: Any = field(init=False)
    mention_text: Any = field(init=False)
    mentioned: Any = field(init=False)

    def __post_init__(self) -> None:
        """Project known mention fields without changing nested values."""
        self.mention_id = self.raw.get("id")
        self.mention_text = self.raw.get("mentionText")
        self.mentioned = self.raw.get("mentioned")


@dataclass(slots=True)
class TeamsMessageReaction:
    """Preserve one reaction and the provider identity that made it."""

    message_identity: TeamsMessageIdentity
    raw: dict[str, Any]
    reaction_type: Any = field(init=False)
    created_date_time: Any = field(init=False)
    user: Any = field(init=False)

    def __post_init__(self) -> None:
        """Project known reaction fields without interpreting reaction type."""
        self.reaction_type = self.raw.get("reactionType")
        self.created_date_time = self.raw.get("createdDateTime")
        self.user = self.raw.get("user")


@dataclass(slots=True)
class TeamsMessageHistoryEntry:
    """
    Preserve one provider messageHistory action record.

    messageHistory records actions such as reaction changes. This projection
    intentionally has no old-body field; unseen message bodies are not
    reconstructed from provider action history.
    """

    message_identity: TeamsMessageIdentity
    raw: dict[str, Any]
    actions: Any = field(init=False)
    modified_date_time: Any = field(init=False)
    reaction: Any = field(init=False)

    def __post_init__(self) -> None:
        """Project action metadata while retaining the complete raw entry."""
        self.actions = self.raw.get("actions")
        self.modified_date_time = self.raw.get("modifiedDateTime")
        self.reaction = self.raw.get("reaction")


def _mentions(
    value: Any,
    identity: TeamsMessageIdentity,
) -> tuple[TeamsMessageMention, ...]:
    return tuple(
        TeamsMessageMention(identity, raw)
        for raw in _embedded_objects(value, context="Teams message mentions")
    )


def _reactions(
    value: Any,
    identity: TeamsMessageIdentity,
) -> tuple[TeamsMessageReaction, ...]:
    return tuple(
        TeamsMessageReaction(identity, raw)
        for raw in _embedded_objects(value, context="Teams message reactions")
    )


def _history(
    value: Any,
    identity: TeamsMessageIdentity,
) -> tuple[TeamsMessageHistoryEntry, ...]:
    return tuple(
        TeamsMessageHistoryEntry(identity, raw)
        for raw in _embedded_objects(value, context="Teams messageHistory")
    )


@dataclass(slots=True)
class TeamsMessageItem:
    """
    Common Teams chatMessage with scoped identity and unchanged provider JSON.

    Optional fields preserve missing versus falsey provider values. Raw nested
    sender, event, body, relation, and unknown values are never normalized.
    Attachments are embedded metadata only; no attachment or web URL is fetched.
    """

    identity: TeamsMessageIdentity
    raw: dict[str, Any]
    message_id: str = field(init=False)
    version_facts: TeamsMessageVersionFacts = field(init=False)
    etag: Any = field(init=False)
    created_date_time: Any = field(init=False)
    last_modified_date_time: Any = field(init=False)
    last_edited_date_time: Any = field(init=False)
    deleted_date_time: Any = field(init=False)
    message_type: Any = field(init=False)
    event_detail: Any = field(init=False)
    sender: Any = field(init=False)
    on_behalf_of: Any = field(init=False)
    body: Any = field(init=False)
    body_content_type: Any = field(init=False)
    body_content: Any = field(init=False)
    mentions: Any = field(init=False)
    mention_items: tuple[TeamsMessageMention, ...] = field(init=False)
    reactions: Any = field(init=False)
    reaction_items: tuple[TeamsMessageReaction, ...] = field(init=False)
    message_history: Any = field(init=False)
    history_items: tuple[TeamsMessageHistoryEntry, ...] = field(init=False)
    importance: Any = field(init=False)
    subject: Any = field(init=False)
    summary: Any = field(init=False)
    scope: Any = field(init=False)
    web_url: Any = field(init=False)
    reply_to_id: Any = field(init=False)
    provider_chat_id: Any = field(init=False)
    channel_identity: Any = field(init=False)
    locale: Any = field(init=False)
    policy_violation: Any = field(init=False)
    attachments: Any = field(init=False)
    attachment_items: tuple[TeamsMessageAttachmentItem, ...] = field(init=False)

    def __post_init__(self) -> None:
        """Project known fields without truth-value or timestamp coercion."""
        self.message_id = self.identity.message_id
        self.version_facts = TeamsMessageVersionFacts.from_graph(self.raw)
        self.etag = self.version_facts.etag
        self.created_date_time = self.version_facts.created_date_time
        self.last_modified_date_time = self.version_facts.last_modified_date_time
        self.last_edited_date_time = self.version_facts.last_edited_date_time
        self.deleted_date_time = self.version_facts.deleted_date_time
        self.message_type = self.raw.get("messageType")
        self.event_detail = self.raw.get("eventDetail")
        self.sender = self.raw.get("from")
        self.on_behalf_of = self.raw.get("onBehalfOf")
        self.body = self.raw.get("body")
        body = self.body if isinstance(self.body, dict) else {}
        self.body_content_type = body.get("contentType")
        self.body_content = body.get("content")
        self.mentions = self.raw.get("mentions")
        self.mention_items = _mentions(self.mentions, self.identity)
        self.reactions = self.raw.get("reactions")
        self.reaction_items = _reactions(self.reactions, self.identity)
        self.message_history = self.raw.get("messageHistory")
        self.history_items = _history(self.message_history, self.identity)
        self.importance = self.raw.get("importance")
        self.subject = self.raw.get("subject")
        self.summary = self.raw.get("summary")
        self.scope = self.raw.get("scope")
        self.web_url = self.raw.get("webUrl")
        self.reply_to_id = self.raw.get("replyToId")
        self.provider_chat_id = self.raw.get("chatId")
        self.channel_identity = self.raw.get("channelIdentity")
        self.locale = self.raw.get("locale")
        self.policy_violation = self.raw.get("policyViolation")
        self.attachments = self.raw.get("attachments")
        self.attachment_items = parse_message_attachments(
            self.attachments,
            message_identity=self.identity,
        )

    @classmethod
    def from_graph(
        cls,
        resource: Any,
        *,
        identity: TeamsMessageIdentity,
        **kwargs: Any,
    ) -> Self:
        """Map a chatMessage already associated with its traversal scope."""
        raw = _message_raw(resource, identity)
        return cls(identity=identity, raw=raw, **kwargs)

    @classmethod
    def from_chat_graph(
        cls,
        resource: Any,
        *,
        chat_id: str,
        **kwargs: Any,
    ) -> Self:
        """Map one message returned under a chat."""
        raw, message_id = _resource_message_id(resource)
        identity = TeamsMessageIdentity.chat(message_id, chat_id=chat_id)
        return cls.from_graph(raw, identity=identity, **kwargs)

    @classmethod
    def from_channel_root_graph(
        cls,
        resource: Any,
        *,
        team_id: str,
        channel_id: str,
        **kwargs: Any,
    ) -> Self:
        """Map one channel root message."""
        raw, message_id = _resource_message_id(resource)
        identity = TeamsMessageIdentity.channel_root(
            message_id,
            team_id=team_id,
            channel_id=channel_id,
        )
        return cls.from_graph(raw, identity=identity, **kwargs)

    @classmethod
    def from_channel_reply_graph(
        cls,
        resource: Any,
        *,
        team_id: str,
        channel_id: str,
        root_message_id: str,
        **kwargs: Any,
    ) -> Self:
        """Map one channel reply under the root path used to retrieve it."""
        raw, message_id = _resource_message_id(resource)
        identity = TeamsMessageIdentity.channel_reply(
            message_id,
            team_id=team_id,
            channel_id=channel_id,
            root_message_id=root_message_id,
        )
        return cls.from_graph(raw, identity=identity, **kwargs)


__all__ = [
    "TeamsMessageHistoryEntry",
    "TeamsMessageItem",
    "TeamsMessageMention",
    "TeamsMessageReaction",
    "TeamsMessageVersionFacts",
]
