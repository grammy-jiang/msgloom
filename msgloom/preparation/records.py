"""
Validated immutable prepared-source contracts for downstream Phase 1 stages.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from msgloom.contracts import Limitation, VersionRef
from msgloom.preparation.contracts import (
    ParserOutput,
    SavedByteReference,
    SourceLocation,
)


class PreparedSourceType(StrEnum):
    """Provider-neutral source categories retained from collection."""

    OUTLOOK_CALENDAR = "outlook_calendar"
    OUTLOOK_EMAIL = "outlook_email"
    TEAMS_CHANNEL_MESSAGE = "teams_channel_message"
    TEAMS_CHAT_MESSAGE = "teams_chat_message"
    TODO = "todo"
    ONEDRIVE = "onedrive"
    CONTACT = "contact"


class RecipientRole(StrEnum):
    """Source-native recipient roles without implying a communication group."""

    TO = "to"
    CC = "cc"
    BCC = "bcc"
    MEMBER = "member"


class FilteringDisposition(StrEnum):
    """Explicit deterministic filtering state for one prepared source."""

    PENDING = "pending"
    INCLUDED = "included"
    EXCLUDED = "excluded"


class _FrozenModel(BaseModel):
    """Reject coercion and mutation at the shared producer boundary."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")


class PreparedParty(_FrozenModel):
    """Opaque source participant identity with optional display text."""

    identity: str
    display_name: str | None = None

    @field_validator("identity")
    @classmethod
    def _identity_nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("party identity must be non-empty")
        return value


class PreparedRecipient(_FrozenModel):
    """One recipient and its source-native role."""

    party: PreparedParty
    role: RecipientRole


class NativeRelationship(_FrozenModel):
    """One source-native relationship to an exact source version."""

    kind: str
    target: VersionRef

    @field_validator("kind")
    @classmethod
    def _kind_nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("relationship kind must be non-empty")
        return value


class PreparedAttachment(_FrozenModel):
    """Attachment identity, saved bytes, and parsed-content reference."""

    reference: VersionRef
    saved_bytes: SavedByteReference | None = None
    parsed_content_ref: VersionRef | None = None
    limitations: tuple[Limitation, ...] = ()


class ReferencedParserOutput(_FrozenModel):
    """Bind validated parser output to the exact prepared-content version."""

    reference: VersionRef
    output: ParserOutput


class SourceMapping(_FrozenModel):
    """Map a prepared field range to an exact source version and location."""

    source: VersionRef
    field: str
    location: SourceLocation
    start: int | None = None
    end: int | None = None

    @field_validator("field")
    @classmethod
    def _field_nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("source mapping field must be non-empty")
        return value

    @model_validator(mode="after")
    def _validate_range(self) -> SourceMapping:
        start = self.start
        end = self.end
        if (start is None) != (end is None):
            raise ValueError("source mapping range must provide both start and end")
        if start is None or end is None:
            return self
        if isinstance(start, bool) or isinstance(end, bool):
            raise TypeError("source mapping offsets must be integers")
        if start < 0 or end <= start:
            raise ValueError("source mapping range must be increasing and non-negative")
        return self


class FilteringDecision(_FrozenModel):
    """
    Explicit filtering disposition and the exact rule version when matched.
    """

    disposition: FilteringDisposition
    rule_ref: VersionRef | None = None

    @model_validator(mode="after")
    def _pending_has_no_rule(self) -> FilteringDecision:
        if (
            self.disposition is FilteringDisposition.PENDING
            and self.rule_ref is not None
        ):
            raise ValueError("pending filtering cannot claim a matched rule")
        return self


class PreparedRecord(_FrozenModel):
    """
    Preserve one source version for deterministic filtering and grouping.

    Raw source bytes are referenced, never embedded.
    Parser output is structured
    semantic data and retains ordered blocks, tables, links, and locations.
    """

    source: VersionRef
    source_type: PreparedSourceType
    sender: PreparedParty | None
    author: PreparedParty | None
    recipients: tuple[PreparedRecipient, ...]
    source_time: datetime
    subject: str | None
    body: str | None
    relationships: tuple[NativeRelationship, ...]
    attachments: tuple[PreparedAttachment, ...]
    parsed_contents: tuple[ReferencedParserOutput, ...]
    limitations: tuple[Limitation, ...]
    source_mappings: tuple[SourceMapping, ...]
    filtering: FilteringDecision

    @field_validator("source_time")
    @classmethod
    def _source_time_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("source_time must be timezone-aware")
        return value

    @model_validator(mode="after")
    def _validate_references(self) -> PreparedRecord:
        refs = tuple(item.reference for item in self.parsed_contents)
        if len(refs) != len(set(refs)):
            raise ValueError("parsed content references must be unique")
        known = set(refs)
        for attachment in self.attachments:
            ref = attachment.parsed_content_ref
            if ref is not None and ref not in known:
                raise ValueError(
                    "attachment parsed-content reference must be included in "
                    "parsed_contents"
                )
        return self
