"""Closed, provider-neutral contracts for durable acquisition publication."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from typing import Literal


class AcquisitionStream(StrEnum):
    """Acquisition families with independent downstream cursors."""

    OUTLOOK_MAIL = "outlook_mail"
    OUTLOOK_CALENDAR = "outlook_calendar"
    TODO = "todo"
    CONTACTS = "contacts"
    ONEDRIVE = "onedrive"


class AcquisitionFactKind(StrEnum):
    """Closed fact semantics; observations alone are not publication."""

    RESOURCE_OBSERVATION = "resource_observation"
    COMPONENT_OBSERVATION = "component_observation"
    SCOPED_STATE_TRANSITION = "scoped_state_transition"
    CONTROL_CONTEXT = "control_context"


class StorageRelation(StrEnum):
    """Write-time freshness; release-time freshness is checked separately."""

    ADVANCED = "advanced"
    CURRENT_EQUIVALENT = "current_equivalent"
    AUTHORITY_STAGED = "authority_staged"
    STALE = "stale"


class ReleaseKind(StrEnum):
    """Semantic completion decisions owned by A1."""

    RESOURCE_SET = "resource_set"
    RESOURCE_PROFILE = "resource_profile"
    AUTHORITY_SCOPE = "authority_scope"
    CONTENT_CAPTURE = "content_capture"
    CONTEXT_INVENTORY = "context_inventory"


class ReleaseEntryKind(StrEnum):
    """Independently pageable impacts under one atomic completion group."""

    RESOURCE = "resource"
    COMPONENT = "component"
    CONTEXT = "context"
    TRANSITION = "transition"


SourceStateKey = str
FactRole = Literal["primary", "component", "context", "transition", "proof"]


def canonical_json(value: object) -> str:
    """Encode deterministic JSON; reject non-finite floats and oversized data."""
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    if len(encoded.encode()) > 65536:
        raise ValueError("Handoff metadata exceeds 64 KiB")
    return encoded


def source_state_key(projection: object) -> SourceStateKey:
    """Hash a provider-owned semantic projection, excluding transport values."""
    return hashlib.sha256(canonical_json(projection).encode()).hexdigest()


def _text(value: str | None) -> None:
    if value is not None and (not value or len(value.encode()) > 2048):
        raise ValueError("Handoff identifiers must be nonempty and bounded")


def _pair(kind: str | None, identity: str | None) -> None:
    if (kind is None) != (identity is None):
        raise ValueError("Scoped identities require both kind and identity")
    _text(kind)
    _text(identity)


@dataclass(frozen=True)
class SourceVersionLocator:
    """
    Resolve immutable evidence, observation, or content-capture association.

    Values are identifiers, never filesystem paths or provider payloads. The
    source reader validates the referenced association before loading evidence.
    """

    kind: Literal["evidence", "observation", "content_capture"]
    evidence_id: str
    resource_identity: str
    observation_id: str | None = None
    capture_id: str | None = None
    component_kind: str | None = None
    resource_version: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in {"evidence", "observation", "content_capture"}:
            raise ValueError("Unknown source-version locator kind")
        for value in asdict(self).values():
            _text(value)
        if self.kind == "observation" and not self.observation_id:
            raise ValueError("Observation locator requires observation_id")
        if self.kind == "content_capture" and not self.capture_id:
            raise ValueError("Content locator requires capture_id")


@dataclass(frozen=True)
class EffectiveStateKey:
    """Identity of one independently fresh resource or component state."""

    source_id: str
    stream: AcquisitionStream
    resource_kind: str
    resource_identity: str
    parent_resource_kind: str | None = None
    parent_resource_identity: str | None = None
    scope_kind: str | None = None
    scope_identity: str | None = None
    component_kind: str | None = None

    @property
    def digest(self) -> str:
        return source_state_key(asdict(self))


@dataclass(frozen=True)
class FactSpec:
    """
    An immutable acquisition fact with current logical-run provenance.

    The store owns ``revalidated_fact_id`` as a write-time effective-state
    pin. For equivalent observations it pins the state being revalidated and
    is excluded from retry identity. Missing equivalent pins fail closed.
    For an advanced reapplication of an already staged capture, it pins the
    displaced effective fact instead. This distinguishes the new application
    without changing provider order, evidence, or source-version identity.
    Advanced pins participate in identity but never grant recovery rights;
    an advanced fact must itself remain effective to publish.
    """

    source_id: str
    stream: AcquisitionStream
    run_id: str
    spider_name: str
    fact_kind: AcquisitionFactKind
    resource_kind: str
    resource_identity: str
    provider_observed_at: str
    source_state_key: SourceStateKey | None = None
    source_version_locator: SourceVersionLocator | None = None
    storage_relation: StorageRelation = StorageRelation.ADVANCED
    parent_resource_kind: str | None = None
    parent_resource_identity: str | None = None
    scope_kind: str | None = None
    scope_identity: str | None = None
    component_kind: str | None = None
    evidence_id: str | None = None
    authority_revision: str | None = None
    provider_order: int | None = None
    transition_reason: str | None = None
    revalidated_fact_id: str | None = None

    def __post_init__(self) -> None:
        AcquisitionStream(self.stream)
        AcquisitionFactKind(self.fact_kind)
        StorageRelation(self.storage_relation)
        for value in asdict(self).values():
            if isinstance(value, str):
                _text(value)
        _pair(self.parent_resource_kind, self.parent_resource_identity)
        _pair(self.scope_kind, self.scope_identity)
        if self.fact_kind == AcquisitionFactKind.COMPONENT_OBSERVATION and (
            not self.parent_resource_identity or not self.component_kind
        ):
            raise ValueError("Component fact requires parent and component")
        if (
            self.fact_kind == AcquisitionFactKind.SCOPED_STATE_TRANSITION
            and not self.scope_identity
        ):
            raise ValueError("Transition fact requires exact scope")
        if self.source_state_key is not None:
            if len(self.source_state_key) != 64:
                raise ValueError("Source state key must be SHA-256")
            int(self.source_state_key, 16)
        canonical_json(asdict(self))

    @property
    def effective_key(self) -> EffectiveStateKey:
        return EffectiveStateKey(
            **{
                name: getattr(self, name)
                for name in EffectiveStateKey.__dataclass_fields__
            }
        )

    @property
    def fact_id(self) -> str:
        material = asdict(self)
        # Preserve digests of immutable facts created before recovery pins.
        if self.revalidated_fact_id is None:
            material.pop("revalidated_fact_id")
        return source_state_key(material)

    @property
    def staging_key(self) -> str:
        """Identify retry before derived advanced/equivalent classification."""
        return replace(
            self,
            revalidated_fact_id=(
                self.revalidated_fact_id
                if self.storage_relation == StorageRelation.ADVANCED
                else None
            ),
            storage_relation=(
                StorageRelation.AUTHORITY_STAGED
                if self.storage_relation == StorageRelation.AUTHORITY_STAGED
                else StorageRelation.STALE
                if self.storage_relation == StorageRelation.STALE
                else StorageRelation.ADVANCED
            ),
        ).fact_id

    @classmethod
    def from_json(cls, value: str) -> FactSpec:
        data = json.loads(value)
        if data["source_version_locator"] is not None:
            data["source_version_locator"] = SourceVersionLocator(
                **data["source_version_locator"]
            )
        return cls(**data)


@dataclass(frozen=True)
class ReleaseGroupSpec:
    """One semantic completion/authority decision, independent of entry size."""

    source_id: str
    stream: AcquisitionStream
    release_kind: ReleaseKind
    subject_kind: str
    subject_identity: str
    owner_run_id: str
    released_at: str
    coverage_kind: Literal["complete", "truncated", "terminal_with_limitations"]
    scope_kind: str | None = None
    scope_identity: str | None = None
    profile: str | None = None
    authority_revision: str | None = None
    limitation_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        AcquisitionStream(self.stream)
        ReleaseKind(self.release_kind)
        if self.coverage_kind not in {
            "complete",
            "truncated",
            "terminal_with_limitations",
        }:
            raise ValueError("Unknown coverage kind")
        _pair(self.scope_kind, self.scope_identity)
        for value in asdict(self).values():
            if isinstance(value, str):
                _text(value)
        if len(self.limitation_codes) > 64:
            raise ValueError("Too many limitation codes")
        for code in self.limitation_codes:
            _text(code)

    @property
    def release_group_id(self) -> str:
        identity = asdict(self)
        for field in ("released_at", "coverage_kind", "limitation_codes"):
            identity.pop(field)
        return source_state_key(identity)


@dataclass(frozen=True)
class ReleaseEntrySpec:
    """One bounded impact and exact immutable fact-role associations."""

    resource_kind: str
    resource_identity: str
    facts: tuple[tuple[str, FactRole], ...]
    entry_kind: ReleaseEntryKind = ReleaseEntryKind.RESOURCE
    parent_resource_kind: str | None = None
    parent_resource_identity: str | None = None
    scope_kind: str | None = None
    scope_identity: str | None = None

    def __post_init__(self) -> None:
        ReleaseEntryKind(self.entry_kind)
        _text(self.resource_kind)
        _text(self.resource_identity)
        _pair(self.parent_resource_kind, self.parent_resource_identity)
        _pair(self.scope_kind, self.scope_identity)
        if not 1 <= len(self.facts) <= 128 or len(set(self.facts)) != len(self.facts):
            raise ValueError("Entry requires 1–128 distinct fact-role members")
        for fact_id, role in self.facts:
            _text(fact_id)
            if role not in {"primary", "component", "context", "transition", "proof"}:
                raise ValueError("Unknown fact role")
        canonical_json(asdict(self))
