"""Bounded immutable admission contracts, independent of source assembly."""

from __future__ import annotations

import hashlib
import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from msgloom.contracts import ResultRef, TerminalStatus
from msgloom.sources.handoff_models import (
    A1CatalogIdentity,
    Digest,
    Identifier,
    ReleaseEntryRef,
    Sequence,
    Stream,
)

INTAKE_KIND = "preparation_intake_workset"
INTAKE_SCHEMA_VERSION = "1"
MAX_INTAKE_ENTRIES = 1024


class _IntakeModel(BaseModel):
    """
    Reject coercion, mutation, arbitrary fields, and unbounded identifiers.
    """

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    @field_validator("*")
    @classmethod
    def _text(cls, value):
        if isinstance(value, str) and (not value.strip() or len(value.encode()) > 2048):
            raise ValueError("intake identifiers must be bounded non-empty text")
        return value


class IntakeScope(_IntakeModel):
    """
    Bind cursor ownership to a stable consumer, never a code/config version.
    """

    catalog: A1CatalogIdentity
    source_id: Identifier
    stream: Stream
    consumer_id: Identifier

    def claim_key(self) -> str:
        """Return the collision-resistant PREPARE_INTAKE ownership scope."""
        # Revalidate copied or constructed models at public boundaries.
        scope = IntakeScope.model_validate_json(self.model_dump_json(), strict=True)
        if not scope.catalog.catalog_identity.strip():
            raise ValueError("catalog identity must be non-empty")
        identity = (
            scope.catalog.catalog_identity,
            scope.source_id,
            scope.stream,
            scope.consumer_id,
        )
        payload = json.dumps(identity, ensure_ascii=False, separators=(",", ":"))
        return "prepare_intake:" + hashlib.sha256(payload.encode()).hexdigest()


class IntakeAnchor(_IntakeModel):
    """Store an exact release sequence/digest, or the unique genesis anchor."""

    last_release_entry_seq: Sequence = 0
    last_release_entry_digest: Digest | None = None

    @model_validator(mode="after")
    def _genesis(self) -> IntakeAnchor:
        if (self.last_release_entry_seq == 0) != (
            self.last_release_entry_digest is None
        ):
            raise ValueError("only genesis has no release digest")
        return self


class IntakeSelection(_IntakeModel):
    """Associate a release with an already durable exact CollectedSelection."""

    entry: ReleaseEntryRef
    result: ResultRef

    @model_validator(mode="after")
    def _selection_schema(self) -> IntakeSelection:
        if (self.result.kind, self.result.schema_version) != (
            "collected_selection",
            "1",
        ):
            raise ValueError("intake selection requires collected_selection@1")
        if (
            not self.result.result_id.strip()
            or len(self.result.result_id.encode()) > 2048
        ):
            raise ValueError("selection result identity exceeds intake bound")
        return self


class IntakeTransition(_IntakeModel):
    """
    Preserve a typed fact and exact scope without inventing readable bytes.

    Classification belongs to the release-aware adapter. Persistence retains
    only identity and a closed transition vocabulary, never provider bodies.
    """

    entry: ReleaseEntryRef
    fact_id: Digest
    transition_kind: Literal[
        "presence", "absence", "membership_removal", "deletion", "context_refresh"
    ]
    resource_kind: Identifier
    resource_identity: Identifier
    scope_kind: Identifier
    scope_identity: Identifier


class HeldIntakeEntry(_IntakeModel):
    """
    Retain exact replay identity and a safe bounded materialization reason.
    """

    entry: ReleaseEntryRef
    reason: Literal[
        "missing_evidence",
        "corrupt_evidence",
        "unsupported_source_type",
        "byte_limit",
        "query_limit",
        "materialization_failed",
    ]


class PreparationIntakeWorkset(_IntakeModel):
    """
    Freeze one nonempty ordered cut with explicit disposition of every entry.

    Sequence gaps are legal because A1 publication is global across streams.
    The caller verifies A1 anchors and enumerates the complete bounded stream
    cut before this contract is finalized. Persistence never reads A1 here.
    """

    scope: IntakeScope
    previous: IntakeAnchor
    cutoff: IntakeAnchor
    entries: Annotated[
        tuple[ReleaseEntryRef, ...], Field(min_length=1, max_length=MAX_INTAKE_ENTRIES)
    ]
    selections: Annotated[
        tuple[IntakeSelection, ...], Field(max_length=MAX_INTAKE_ENTRIES)
    ] = ()
    transitions: Annotated[
        tuple[IntakeTransition, ...], Field(max_length=MAX_INTAKE_ENTRIES)
    ] = ()
    held: Annotated[
        tuple[HeldIntakeEntry, ...], Field(max_length=MAX_INTAKE_ENTRIES)
    ] = ()
    configuration_version: Identifier
    code_version: Identifier

    @model_validator(mode="after")
    def _accounted_cut(self) -> PreparationIntakeWorkset:
        self.scope.claim_key()
        sequences = tuple(ref.release_entry_seq for ref in self.entries)
        if sequences != tuple(sorted(set(sequences))):
            raise ValueError("release entries must be unique and ordered")
        if sequences[0] <= self.previous.last_release_entry_seq:
            raise ValueError("release entries must follow the previous anchor")
        last = self.entries[-1]
        if (
            last.release_entry_seq != self.cutoff.last_release_entry_seq
            or last.entry_digest != self.cutoff.last_release_entry_digest
        ):
            raise ValueError("cutoff must equal the last admitted entry")
        if any(ref.catalog != self.scope.catalog for ref in self.entries):
            raise ValueError("entry belongs to another A1 catalog")
        admitted = {ref.release_entry_seq: ref for ref in self.entries}
        dispositions = (*self.selections, *self.transitions, *self.held)
        if {item.entry.release_entry_seq for item in dispositions} != set(
            admitted
        ) or any(
            admitted.get(item.entry.release_entry_seq) != item.entry
            for item in dispositions
        ):
            raise ValueError("every admitted entry needs an exact disposition")
        held = tuple(item.entry.release_entry_seq for item in self.held)
        readable = {
            item.entry.release_entry_seq
            for item in (*self.selections, *self.transitions)
        }
        if len(set(held)) != len(held) or set(held) & readable:
            raise ValueError("held entries cannot have conflicting dispositions")
        for keys in (
            tuple(
                (item.entry.release_entry_seq, item.result) for item in self.selections
            ),
            tuple(
                (item.entry.release_entry_seq, item.fact_id)
                for item in self.transitions
            ),
        ):
            if len(keys) != len(set(keys)):
                raise ValueError("duplicate intake disposition")
        return self

    @property
    def selection_refs(self) -> tuple[ResultRef, ...]:
        """Return deterministic unique dependencies for the workset result."""
        return tuple(dict.fromkeys(item.result for item in self.selections))


class IntakeWorksetState(_IntakeModel):
    """
    Expose bounded pending/terminal processing metadata without source reads.
    """

    workset: ResultRef
    cutoff: IntakeAnchor
    state: Literal["pending", "terminal"]
    terminal_status: TerminalStatus | None = None
    result_refs: tuple[ResultRef, ...] = ()


class IndexedHeldIntakeEntry(_IntakeModel):
    """Locate one held admission for explicit operator repair or replay."""

    workset: ResultRef
    disposition: HeldIntakeEntry


def workset_claim_key(result_id: str) -> str:
    """
    Bind a distinct PREPARE processing claim to one immutable intake result.
    """
    if not result_id.strip() or len(result_id.encode()) > 2048:
        raise ValueError("workset result identity must be bounded non-empty text")
    return "prepare_intake_workset:" + hashlib.sha256(result_id.encode()).hexdigest()
