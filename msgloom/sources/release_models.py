"""Immutable Task12 output contracts, independent of intake persistence."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from msgloom.preparation.contracts import SavedByteReference
from msgloom.sources.handoff_models import (
    Digest,
    Identifier,
    ReleasedFact,
    ReleaseEntryRef,
    Stream,
)
from msgloom.sources.models import CollectedSelection


class _Frozen(BaseModel):
    """Keep reader output closed and immutable."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")


class ScopedTransition(_Frozen):
    """Preserve scoped authority without inventing deleted source bytes."""

    fact_id: Digest
    source_id: Identifier
    stream: Stream
    resource_kind: Identifier
    resource_identity: Identifier
    parent_resource_kind: Identifier | None
    parent_resource_identity: Identifier | None
    scope_kind: Identifier
    scope_identity: Identifier
    reason: Identifier
    authority_revision: Identifier | None
    provider_order: int | None
    evidence: SavedByteReference | None


class ReleasedInput(_Frozen):
    """Bind all exact entry effects to their immutable admission reference."""

    reference: ReleaseEntryRef
    selection: CollectedSelection | None
    components: tuple[CollectedSelection, ...] = ()
    contexts: tuple[CollectedSelection, ...] = ()
    transitions: tuple[ScopedTransition, ...] = ()
    facts: tuple[ReleasedFact, ...]


class SupportingContext(_Frozen):
    """Pin explicitly requested history without admitting primary work."""

    reference: ReleaseEntryRef
    selection: CollectedSelection
    primary: Literal[False] = False
