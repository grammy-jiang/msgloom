"""Validate immutable entry ownership, payloads, and ordered membership."""

import json
from dataclasses import asdict
from typing import cast

from sqlalchemy import Connection, Table, select
from sqlalchemy.engine import RowMapping
from sqlalchemy.orm import Session

from message_ingest.acquisition.handoff import (
    FactRole,
    FactSpec,
    ReleaseEntrySpec,
    canonical_json,
    source_state_key,
)
from message_ingest.catalog.models.handoff import AcquisitionReleaseEntryFact

_MEMBER = cast(Table, AcquisitionReleaseEntryFact.__table__)


def validate_impact(entry: ReleaseEntrySpec, fact: FactSpec, role: FactRole) -> None:
    """
    Preserve direct scope/ownership while allowing parent and proof roles.

    A direct resource or component impact retains its own parent and scope.
    A component-parent impact names the fact's parent as its target; that
    parent's own parent is not described by the component fact. Profile proof
    facts can describe other resources. Transitions always retain exact scope.
    """
    scope = (entry.scope_kind, entry.scope_identity)
    fact_scope = (fact.scope_kind, fact.scope_identity)
    if fact.fact_kind == "scoped_state_transition" and scope != fact_scope:
        raise ValueError("Transition entry changes fact scope")
    if role == "proof":
        return
    target = (entry.resource_kind, entry.resource_identity)
    own = (fact.resource_kind, fact.resource_identity)
    parent = (fact.parent_resource_kind, fact.parent_resource_identity)
    if target not in (own, parent):
        raise ValueError("Entry fact has unrelated resource/parent")
    if target == own:
        if scope != fact_scope:
            raise ValueError("Direct entry changes fact scope")
        if (entry.parent_resource_kind, entry.parent_resource_identity) != parent:
            raise ValueError("Direct entry changes fact parent")


def validate_entry(writer: Session | Connection, row: RowMapping) -> ReleaseEntrySpec:
    """
    Fail closed on bounded payload, digest, or ordered membership mismatch.

    Every public entry reader uses this check within its read transaction.
    Read one sentinel beyond the maximum membership size so extra rows are
    rejected rather than hidden by a limit. No mutable source state is read.
    """
    payload = row["payload"]
    try:
        if len(payload.encode()) > 65536:
            raise ValueError("Oversized entry payload")
        data = json.loads(payload)
        pairs = data["facts"]
        if not isinstance(pairs, list) or any(
            not isinstance(pair, list)
            or len(pair) != 2
            or any(not isinstance(value, str) for value in pair)
            for pair in pairs
        ):
            raise ValueError("Malformed entry membership")
        data["facts"] = tuple(tuple(pair) for pair in pairs)
        spec = ReleaseEntrySpec(**data)
        if canonical_json(asdict(spec)) != payload:
            raise ValueError("Noncanonical entry payload")
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Invalid acquisition entry payload") from error
    digest = source_state_key({"group": row["release_group_id"], "entry": asdict(spec)})
    if digest != row["entry_digest"]:
        raise ValueError("Acquisition entry digest mismatch")
    members = writer.execute(
        select(_MEMBER.c.ordinal, _MEMBER.c.fact_id, _MEMBER.c.role)
        .where(_MEMBER.c.release_entry_seq == row["release_entry_seq"])
        .order_by(_MEMBER.c.ordinal)
        .limit(129)
    ).all()
    expected = [
        (ordinal, fact_id, role) for ordinal, (fact_id, role) in enumerate(spec.facts)
    ]
    if members != expected:
        raise ValueError("Acquisition entry membership mismatch")
    return spec
