"""
Bounded immutable read contracts for the version-one A1 release ledger.

The wire format is independent of A1 Python types. Extra fields, provider
bodies, credentials, mutable projections, and file paths are not part of it.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Stream = Literal["outlook_mail", "outlook_calendar", "todo", "onedrive", "contacts"]
FactRole = Literal["primary", "component", "context", "transition", "proof"]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Sequence = Annotated[int, Field(ge=0, le=2**63 - 1)]
Identifier = Annotated[str, Field(min_length=1, max_length=2048)]


class _BoundedModel(BaseModel):
    """Reject mutation, coercion, unknown fields, and oversized identifiers."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    @field_validator("*")
    @classmethod
    def _bounded_text(cls, value):
        if isinstance(value, str) and len(value.encode()) > 2048:
            raise ValueError("Ledger text exceeds identifier bound")
        return value


class A1CatalogIdentity(_BoundedModel):
    """Stable catalog identity and supported ledger schema, preserved by backup."""

    catalog_identity: Identifier
    schema_version: Literal[1]


class SourceVersionLocator(_BoundedModel):
    """Closed exact evidence/observation/content reference, never a fetch URL."""

    kind: Literal["evidence", "observation", "content_capture"]
    evidence_id: Identifier
    resource_identity: Identifier
    observation_id: Identifier | None = None
    capture_id: Identifier | None = None
    component_kind: Identifier | None = None
    resource_version: Identifier | None = None

    @model_validator(mode="after")
    def _required_association(self) -> SourceVersionLocator:
        if self.kind == "observation" and not self.observation_id:
            raise ValueError("Observation locator lacks its identity")
        if self.kind == "content_capture" and not self.capture_id:
            raise ValueError("Content locator lacks its identity")
        return self


class _ScopedModel(_BoundedModel):
    """Keep optional parent and scope pairs structurally complete."""

    parent_resource_kind: Identifier | None = None
    parent_resource_identity: Identifier | None = None
    scope_kind: Identifier | None = None
    scope_identity: Identifier | None = None

    @model_validator(mode="after")
    def _paired_identity(self) -> _ScopedModel:
        for kind, identity in (
            (self.parent_resource_kind, self.parent_resource_identity),
            (self.scope_kind, self.scope_identity),
        ):
            if (kind is None) != (identity is None):
                raise ValueError("Ledger scope requires kind and identity")
        return self


class FactPayload(_ScopedModel):
    """Exact bounded fact fields; source and component keys stay separate."""

    source_id: Identifier
    stream: Stream
    run_id: Identifier
    spider_name: Identifier
    fact_kind: Literal[
        "resource_observation",
        "component_observation",
        "scoped_state_transition",
        "control_context",
    ]
    resource_kind: Identifier
    resource_identity: Identifier
    provider_observed_at: Identifier
    source_state_key: Digest | None = None
    source_version_locator: SourceVersionLocator | None = None
    storage_relation: Literal[
        "advanced", "current_equivalent", "authority_staged", "stale"
    ]
    component_kind: Identifier | None = None
    evidence_id: Identifier | None = None
    authority_revision: Identifier | None = None
    provider_order: int | None = None
    transition_reason: Identifier | None = None
    revalidated_fact_id: Digest | None = None

    @model_validator(mode="after")
    def _fact_scope(self) -> FactPayload:
        if self.fact_kind == "component_observation" and (
            not self.parent_resource_identity or not self.component_kind
        ):
            raise ValueError("Component fact lacks parent/component")
        if self.fact_kind == "scoped_state_transition" and not self.scope_identity:
            raise ValueError("Transition fact lacks exact scope")
        return self


class ReleasedFact(FactPayload):
    """One immutable fact with its ordered role in the requested release."""

    fact_id: Digest
    role: FactRole
    ordinal: Annotated[int, Field(ge=0, le=127)]


class ReleaseGroup(_BoundedModel):
    """Bounded completion metadata shared by entries in an atomic A1 group."""

    source_id: Identifier
    stream: Stream
    release_kind: Literal[
        "resource_set",
        "resource_profile",
        "authority_scope",
        "content_capture",
        "context_inventory",
    ]
    subject_kind: Identifier
    subject_identity: Identifier
    owner_run_id: Identifier
    released_at: Identifier
    coverage_kind: Literal["complete", "truncated", "terminal_with_limitations"]
    scope_kind: Identifier | None = None
    scope_identity: Identifier | None = None
    profile: Identifier | None = None
    authority_revision: Identifier | None = None
    limitation_codes: Annotated[tuple[Identifier, ...], Field(max_length=64)] = ()


class EntryPayload(_ScopedModel):
    """One bounded resource impact and ordered immutable fact-role members."""

    resource_kind: Identifier
    resource_identity: Identifier
    facts: Annotated[
        tuple[tuple[Digest, FactRole], ...], Field(min_length=1, max_length=128)
    ]
    entry_kind: Literal["resource", "component", "context", "transition"]

    @model_validator(mode="after")
    def _distinct_members(self) -> EntryPayload:
        if len(set(self.facts)) != len(self.facts):
            raise ValueError("Duplicate ledger fact-role membership")
        return self


class ReleaseEntryRef(_BoundedModel):
    """Catalog-bound admission anchor, independent of provider version order."""

    catalog: A1CatalogIdentity
    release_entry_seq: Annotated[int, Field(ge=1, le=2**63 - 1)]
    entry_digest: Digest


class ReleaseEntry(EntryPayload):
    """Exact release metadata plus bounded group context and member identities."""

    catalog: A1CatalogIdentity
    release_entry_seq: Annotated[int, Field(ge=1, le=2**63 - 1)]
    release_group_id: Digest
    source_id: Identifier
    stream: Stream
    entry_digest: Digest
    group_digest: Digest
    group: ReleaseGroup

    @property
    def reference(self) -> ReleaseEntryRef:
        """Return the minimal catalog-bound reference for later exact loading."""
        return ReleaseEntryRef(
            catalog=self.catalog,
            release_entry_seq=self.release_entry_seq,
            entry_digest=self.entry_digest,
        )


class ReleaseEntryPage(_BoundedModel):
    """
    Finite ordered cut with a fixed upper bound and explicit continuation.

    Advance only to the last admitted entry after durable downstream storage.
    The through sequence is a requested ceiling, not an admitted cursor.
    """

    catalog: A1CatalogIdentity
    source_id: Identifier
    stream: Stream
    after_seq: Sequence
    through_seq: Sequence
    entries: Annotated[tuple[ReleaseEntry, ...], Field(max_length=1000)]
    has_more: bool
