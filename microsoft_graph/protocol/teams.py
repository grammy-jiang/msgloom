"""Pure Microsoft Teams message identities and content-type classification."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class TeamsMessageLocation(StrEnum):
    """Identify the Graph collection that scopes an opaque message ID."""

    CHAT = "chat"
    CHANNEL_ROOT = "channel-root"
    CHANNEL_REPLY = "channel-reply"


def _opaque_id(value: object, *, name: str) -> str:
    """Require a non-empty opaque provider ID without interpreting its bytes."""
    if not isinstance(value, str) or not value:
        raise ValueError(f"Teams message identity requires a non-empty {name}")
    return value


@dataclass(frozen=True, slots=True)
class TeamsMessageIdentity:
    """
    Scope an opaque Teams message ID to its owning chat or channel thread.

    IDs are never normalized or treated as globally unique. Channel replies
    retain the root ID supplied by the traversal path instead of deriving
    topology from the reply payload.
    """

    location: TeamsMessageLocation
    message_id: str
    chat_id: str | None = None
    team_id: str | None = None
    channel_id: str | None = None
    root_message_id: str | None = None

    def __post_init__(self) -> None:
        """Validate the exact identity shape while preserving opaque strings."""
        try:
            location = TeamsMessageLocation(self.location)
        except ValueError as exc:
            raise ValueError(
                f"Unknown Teams message location: {self.location!r}"
            ) from exc
        object.__setattr__(self, "location", location)
        _opaque_id(self.message_id, name="message_id")

        if location is TeamsMessageLocation.CHAT:
            _opaque_id(self.chat_id, name="chat_id")
            if any(
                value is not None
                for value in (self.team_id, self.channel_id, self.root_message_id)
            ):
                raise ValueError("Chat message identity cannot contain channel IDs")
            return

        _opaque_id(self.team_id, name="team_id")
        _opaque_id(self.channel_id, name="channel_id")
        if self.chat_id is not None:
            raise ValueError("Channel message identity cannot contain chat_id")

        if location is TeamsMessageLocation.CHANNEL_ROOT:
            if self.root_message_id is not None:
                raise ValueError("Channel root identity cannot contain root_message_id")
            return

        _opaque_id(self.root_message_id, name="root_message_id")

    @classmethod
    def chat(cls, message_id: str, *, chat_id: str) -> TeamsMessageIdentity:
        """Build a message identity under one chat."""
        return cls(
            location=TeamsMessageLocation.CHAT,
            message_id=message_id,
            chat_id=chat_id,
        )

    @classmethod
    def channel_root(
        cls,
        message_id: str,
        *,
        team_id: str,
        channel_id: str,
    ) -> TeamsMessageIdentity:
        """Build a root-message identity under one team/channel."""
        return cls(
            location=TeamsMessageLocation.CHANNEL_ROOT,
            message_id=message_id,
            team_id=team_id,
            channel_id=channel_id,
        )

    @classmethod
    def channel_reply(
        cls,
        message_id: str,
        *,
        team_id: str,
        channel_id: str,
        root_message_id: str,
    ) -> TeamsMessageIdentity:
        """Build a reply identity under one team/channel/root message."""
        return cls(
            location=TeamsMessageLocation.CHANNEL_REPLY,
            message_id=message_id,
            team_id=team_id,
            channel_id=channel_id,
            root_message_id=root_message_id,
        )

    @property
    def scope_key(self) -> tuple[str, ...]:
        """Return a stable tuple that keeps duplicate provider IDs distinct."""
        if self.location is TeamsMessageLocation.CHAT:
            return (self.location.value, self.chat_id or "", self.message_id)
        if self.location is TeamsMessageLocation.CHANNEL_ROOT:
            return (
                self.location.value,
                self.team_id or "",
                self.channel_id or "",
                self.message_id,
            )
        return (
            self.location.value,
            self.team_id or "",
            self.channel_id or "",
            self.root_message_id or "",
            self.message_id,
        )


class TeamsAttachmentKind(StrEnum):
    """Classify known chatMessageAttachment content types."""

    REFERENCE = "reference"
    FORWARDED_MESSAGE_REFERENCE = "forwarded-message-reference"
    MESSAGE_REFERENCE = "message-reference"
    MEETING_REFERENCE = "meeting-reference"
    TAB_REFERENCE = "tab-reference"
    LOOP_CARD = "loop-card"
    CODE_CARD = "code-card"
    ANNOUNCEMENT_CARD = "announcement-card"
    CARD = "card"
    UNKNOWN = "unknown"


def classify_teams_attachment(content_type: object) -> TeamsAttachmentKind:
    """
    Classify stable Teams attachment forms without rewriting provider values.

    The caller keeps the original contentType and complete attachment JSON.
    Unknown and non-string values deliberately remain unclassified.
    """
    if not isinstance(content_type, str):
        return TeamsAttachmentKind.UNKNOWN

    exact = {
        "reference": TeamsAttachmentKind.REFERENCE,
        "forwardedMessageReference": TeamsAttachmentKind.FORWARDED_MESSAGE_REFERENCE,
        "messageReference": TeamsAttachmentKind.MESSAGE_REFERENCE,
        "meetingReference": TeamsAttachmentKind.MEETING_REFERENCE,
        "tabReference": TeamsAttachmentKind.TAB_REFERENCE,
    }
    if kind := exact.get(content_type):
        return kind

    lowered = content_type.lower()
    if lowered == "application/vnd.microsoft.card.fluidembedcard":
        return TeamsAttachmentKind.LOOP_CARD
    if lowered.startswith("application/vnd.microsoft.card."):
        if "codesnippet" in lowered:
            return TeamsAttachmentKind.CODE_CARD
        if "announcement" in lowered:
            return TeamsAttachmentKind.ANNOUNCEMENT_CARD
        return TeamsAttachmentKind.CARD
    return TeamsAttachmentKind.UNKNOWN


__all__ = [
    "TeamsAttachmentKind",
    "TeamsMessageIdentity",
    "TeamsMessageLocation",
    "classify_teams_attachment",
]
