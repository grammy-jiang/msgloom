"""Transaction-neutral ledger operations for provider-owned writer scopes."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import asdict, replace
from typing import TYPE_CHECKING, Any, cast
from uuid import uuid4

from sqlalchemy import Connection, Table, insert, select, update
from sqlalchemy.orm import Session

from message_ingest.acquisition.handoff import (
    AcquisitionStream,
    EffectiveStateKey,
    FactSpec,
    ReleaseEntrySpec,
    ReleaseGroupSpec,
    StorageRelation,
    canonical_json,
    source_state_key,
)
from message_ingest.catalog.models.handoff import (
    AcquisitionEffectiveState,
    AcquisitionFact,
    AcquisitionLedgerMetadata,
    AcquisitionReleaseEntry,
    AcquisitionReleaseEntryFact,
    AcquisitionReleaseGroup,
)

if TYPE_CHECKING:
    from message_ingest.catalog.store import Catalog

Writer = Session | Connection
FACT = cast(Table, AcquisitionFact.__table__)
STATE = cast(Table, AcquisitionEffectiveState.__table__)
GROUP = cast(Table, AcquisitionReleaseGroup.__table__)
ENTRY = cast(Table, AcquisitionReleaseEntry.__table__)
MEMBER = cast(Table, AcquisitionReleaseEntryFact.__table__)
META = cast(Table, AcquisitionLedgerMetadata.__table__)


def initialize_handoff(connection: Connection) -> None:
    """Initialize identity and immutable-row guards in the schema transaction."""
    row = connection.execute(select(META)).mappings().first()
    if row is None:
        connection.execute(
            insert(META).values(
                singleton=1,
                schema_version=1,
                catalog_identity=str(uuid4()),
            )
        )
    elif row["schema_version"] != 1 or row["singleton"] != 1:
        raise ValueError("Unsupported acquisition ledger schema")
    tables = (
        FACT.name,
        GROUP.name,
        ENTRY.name,
        MEMBER.name,
        META.name,
        "acquisition_run_outcomes",
    )
    for table in tables:
        for operation in ("UPDATE", "DELETE"):
            connection.exec_driver_sql(
                f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{operation} "
                f"BEFORE {operation} ON {table} BEGIN "
                "SELECT RAISE(ABORT, 'immutable acquisition ledger row'); END"
            )


class AcquisitionHandoffStore:
    """
    Stage and publish under the caller's transaction and freshness decision.

    Mutators never begin, commit, flush, or roll back transactions. Callers must
    reserve writer ownership before reading freshness state and must propagate
    errors so the enclosing provider operation rolls back. Core statements work
    with both ORM sessions and Calendar's explicit connection transaction.
    """

    def __init__(self, catalog: Catalog) -> None:
        self.catalog = catalog

    def catalog_identity(self) -> str:
        with self.catalog.Session() as session:
            return session.execute(select(META.c.catalog_identity)).scalar_one()

    def current_effective_state(
        self,
        writer: Writer,
        key: EffectiveStateKey,
    ) -> dict[str, Any] | None:
        row = (
            writer.execute(
                select(STATE).where(
                    STATE.c.effective_key == key.digest,
                )
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def _existing_fact(self, writer: Writer, spec: FactSpec) -> FactSpec | None:
        row = writer.execute(
            select(FACT.c.payload).where(
                FACT.c.staging_key == spec.staging_key,
            )
        ).scalar_one_or_none()
        return FactSpec.from_json(row) if row is not None else None

    def _insert_fact(self, writer: Writer, spec: FactSpec) -> FactSpec:
        writer.execute(
            insert(FACT).values(
                fact_id=spec.fact_id,
                staging_key=spec.staging_key,
                effective_key=spec.effective_key.digest,
                source_id=spec.source_id,
                stream=spec.stream,
                run_id=spec.run_id,
                source_state_key=spec.source_state_key,
                storage_relation=spec.storage_relation,
                payload=canonical_json(asdict(spec)),
            )
        )
        return spec

    def _make_effective(self, writer: Writer, spec: FactSpec) -> None:
        if spec.source_state_key is None:
            raise ValueError("Effective state requires source_state_key")
        values = {"fact_id": spec.fact_id, "source_state_key": spec.source_state_key}
        current = self.current_effective_state(writer, spec.effective_key)
        if current is not None and current["source_state_key"] == spec.source_state_key:
            return
        if current is None:
            writer.execute(
                insert(STATE).values(
                    effective_key=spec.effective_key.digest,
                    **values,
                )
            )
        else:
            writer.execute(
                update(STATE)
                .where(
                    STATE.c.effective_key == spec.effective_key.digest,
                )
                .values(**values)
            )

    def stage_state_fact_in_session(self, writer: Writer, spec: FactSpec) -> FactSpec:
        """
        Stage a provider-accepted write and atomically classify equivalence.

        Pass ``current_equivalent`` for pre-ledger unchanged domain rows. Without
        a prior advanced fact they cannot create future-only bootstrap work.
        Equivalent observations pin the exact effective fact they revalidate.
        A later return to the same semantic state cannot replace that proof.
        """
        if spec.storage_relation == StorageRelation.AUTHORITY_STAGED:
            raise ValueError("Use authority staging for pending provider authority")
        if existing := self._existing_fact(writer, spec):
            return existing
        spec = replace(spec, revalidated_fact_id=None)
        current = self.current_effective_state(writer, spec.effective_key)
        if (
            spec.storage_relation != StorageRelation.STALE
            and current is not None
            and spec.source_state_key == current["source_state_key"]
        ):
            spec = replace(
                spec,
                storage_relation=StorageRelation.CURRENT_EQUIVALENT,
                revalidated_fact_id=current["fact_id"],
            )
        self._insert_fact(writer, spec)
        if spec.storage_relation == StorageRelation.ADVANCED:
            self._make_effective(writer, spec)
        return spec

    def stage_authority_fact_in_session(
        self, writer: Writer, spec: FactSpec
    ) -> FactSpec:
        """Retain staging without making it effective before winning promotion."""
        spec = replace(
            spec,
            storage_relation=StorageRelation.AUTHORITY_STAGED,
            revalidated_fact_id=None,
        )
        if existing := self._existing_fact(writer, spec):
            return existing
        return self._insert_fact(writer, spec)

    def _fact(self, writer: Writer, fact_id: str) -> FactSpec:
        payload = writer.execute(
            select(FACT.c.payload).where(
                FACT.c.fact_id == fact_id,
            )
        ).scalar_one_or_none()
        if payload is None:
            raise ValueError("Unknown acquisition fact")
        spec = FactSpec.from_json(payload)
        if spec.fact_id != fact_id:
            raise ValueError("Acquisition fact digest mismatch")
        return spec

    def _released(self, writer: Writer, spec: FactSpec) -> bool:
        return (
            writer.execute(
                select(MEMBER.c.fact_id)
                .where(
                    MEMBER.c.fact_id == spec.fact_id,
                    MEMBER.c.role != "proof",
                )
                .limit(1)
            ).first()
            is not None
        )

    def _eligible(
        self,
        writer: Writer,
        spec: FactSpec,
        winning: frozenset[str],
    ) -> FactSpec | None:
        if spec.storage_relation == StorageRelation.STALE:
            return None
        if (
            spec.storage_relation == StorageRelation.AUTHORITY_STAGED
            and spec.fact_id not in winning
        ):
            return None
        current = self.current_effective_state(writer, spec.effective_key)
        if current is None or current["source_state_key"] != spec.source_state_key:
            return None
        # Authority winners revalidate in this transaction. Other observations
        # must still name the exact advancement seen at their own write time.
        if spec.storage_relation != StorageRelation.AUTHORITY_STAGED:
            expected = (
                spec.revalidated_fact_id
                if spec.storage_relation == StorageRelation.CURRENT_EQUIVALENT
                else spec.fact_id
            )
            if current["fact_id"] != expected:
                return None
        effective = self._fact(writer, current["fact_id"])
        return effective

    def release_effective_group_in_session(
        self,
        writer: Writer,
        spec: ReleaseGroupSpec,
        entries: Sequence[ReleaseEntrySpec],
    ) -> str:
        """Publish only still-effective, previously unreleased state impacts."""
        if spec.release_kind == "authority_scope":
            raise ValueError("Authority groups require the authority publication API")
        return self._release(writer, spec, entries, frozenset())

    def release_authority_group_in_session(
        self,
        writer: Writer,
        spec: ReleaseGroupSpec,
        entries: Sequence[ReleaseEntrySpec],
        *,
        winning_fact_ids: Sequence[str],
    ) -> str:
        """
        Bind only observations applied by the caller's winning promotion.

        The provider owns CAS/generation checks and skipped-state decisions.
        Only explicitly applied facts become effective in this transaction.
        """
        if spec.release_kind != "authority_scope":
            raise ValueError("Authority publication requires authority_scope")
        winning = frozenset(winning_fact_ids)
        return self._release(writer, spec, entries, winning)

    def _release(
        self,
        writer: Writer,
        spec: ReleaseGroupSpec,
        entries: Sequence[ReleaseEntrySpec],
        winning: frozenset[str],
    ) -> str:
        # Stream input digests: group size must not inherit per-entry JSON limits.
        material = asdict(spec)
        material.pop("released_at")
        digest = hashlib.sha256(canonical_json(material).encode())
        for fact_id in sorted(winning):
            digest.update(fact_id.encode())
        for entry in entries:
            digest.update(canonical_json(asdict(entry)).encode())
        input_digest = digest.hexdigest()
        existing = (
            writer.execute(
                select(GROUP).where(
                    GROUP.c.release_group_id == spec.release_group_id,
                )
            )
            .mappings()
            .first()
        )
        if existing is not None:
            if existing["input_digest"] != input_digest:
                raise ValueError("Release identity reused with a different digest")
            return spec.release_group_id
        applied: set[str] = set()
        for fact_id in sorted(winning):
            candidate = self._fact(writer, fact_id)
            if candidate.effective_key.digest in applied:
                raise ValueError("Ambiguous winning effective state")
            applied.add(candidate.effective_key.digest)
            self._validate_scope(spec, candidate)
            if candidate.storage_relation not in {
                StorageRelation.AUTHORITY_STAGED,
                StorageRelation.ADVANCED,
                StorageRelation.CURRENT_EQUIVALENT,
            }:
                raise ValueError("Stale fact cannot win authority")
            if candidate.storage_relation == StorageRelation.AUTHORITY_STAGED:
                self._make_effective(writer, candidate)
        selected: list[ReleaseEntrySpec] = []
        seen: set[str] = set()
        for entry in entries:
            identity = asdict(entry)
            identity.pop("facts")
            impact_key = source_state_key(identity)
            if impact_key in seen:
                raise ValueError("Duplicate release entry impact")
            seen.add(impact_key)
            members = []
            changed = False
            complete = True
            for fact_id, role in entry.facts:
                candidate = self._fact(writer, fact_id)
                self._validate_scope(spec, candidate)
                if candidate.fact_kind == "scoped_state_transition" and (
                    (entry.scope_kind, entry.scope_identity)
                    != (candidate.scope_kind, candidate.scope_identity)
                ):
                    raise ValueError("Transition entry changes fact scope")
                if role != "proof":
                    target = (entry.resource_kind, entry.resource_identity)
                    own = (candidate.resource_kind, candidate.resource_identity)
                    parent = (
                        candidate.parent_resource_kind,
                        candidate.parent_resource_identity,
                    )
                    if target not in (own, parent):
                        raise ValueError("Entry fact has unrelated resource/parent")
                eligible = self._eligible(writer, candidate, winning)
                if eligible is not None:
                    members.append((eligible.fact_id, role))
                    changed |= role != "proof" and not self._released(writer, eligible)
                else:
                    complete = False
            if members and changed and complete:
                selected.append(replace(entry, facts=tuple(dict.fromkeys(members))))
        group_hash = hashlib.sha256(canonical_json(asdict(spec)).encode())
        for entry in selected:
            group_hash.update(canonical_json(asdict(entry)).encode())
        writer.execute(
            insert(GROUP).values(
                release_group_id=spec.release_group_id,
                source_id=spec.source_id,
                stream=spec.stream,
                group_digest=group_hash.hexdigest(),
                input_digest=input_digest,
                payload=canonical_json(asdict(spec)),
            )
        )
        for entry in selected:
            payload = canonical_json(asdict(entry))
            entry_digest = source_state_key(
                {
                    "group": spec.release_group_id,
                    "entry": asdict(entry),
                }
            )
            seq = writer.execute(
                insert(ENTRY)
                .values(
                    release_group_id=spec.release_group_id,
                    source_id=spec.source_id,
                    stream=spec.stream,
                    entry_digest=entry_digest,
                    payload=payload,
                )
                .returning(ENTRY.c.release_entry_seq)
            ).scalar_one()
            for ordinal, (fact_id, role) in enumerate(entry.facts):
                writer.execute(
                    insert(MEMBER).values(
                        release_entry_seq=seq,
                        ordinal=ordinal,
                        fact_id=fact_id,
                        role=role,
                    )
                )
        return spec.release_group_id

    @staticmethod
    def _validate_scope(group: ReleaseGroupSpec, fact: FactSpec) -> None:
        if (group.source_id, group.stream) != (fact.source_id, fact.stream):
            raise ValueError("Release fact crosses source/stream boundary")

    def list_release_entries(
        self,
        source_id: str,
        stream: AcquisitionStream,
        *,
        after_seq: int = 0,
        through_seq: int | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Read a bounded immutable entry page in admission order."""
        if not 1 <= limit <= 1000 or after_seq < 0:
            raise ValueError("Invalid release page limits")
        query = select(ENTRY).where(
            ENTRY.c.source_id == source_id,
            ENTRY.c.stream == stream,
            ENTRY.c.release_entry_seq > after_seq,
        )
        if through_seq is not None:
            query = query.where(ENTRY.c.release_entry_seq <= through_seq)
        with self.catalog.Session() as session:
            return [
                dict(row)
                for row in session.execute(
                    query.order_by(
                        ENTRY.c.release_entry_seq,
                    ).limit(limit)
                ).mappings()
            ]

    def load_release_entry(self, seq: int) -> dict[str, Any] | None:
        with self.catalog.Session() as session:
            row = (
                session.execute(
                    select(ENTRY).where(
                        ENTRY.c.release_entry_seq == seq,
                    )
                )
                .mappings()
                .first()
            )
            return dict(row) if row else None

    def load_release_facts(self, seq: int) -> list[FactSpec]:
        with self.catalog.Session() as session:
            rows = (
                session.execute(
                    select(MEMBER.c.fact_id)
                    .where(
                        MEMBER.c.release_entry_seq == seq,
                    )
                    .order_by(MEMBER.c.ordinal)
                    .limit(129)
                )
                .scalars()
                .all()
            )
            if len(rows) > 128:
                raise ValueError("Release entry exceeds fact limit")
            return [self._fact(session, fact_id) for fact_id in rows]
