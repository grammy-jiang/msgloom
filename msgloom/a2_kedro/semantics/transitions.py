"""
Scoped transition semantics for ``prepared_transitions@2`` (P3-08).

This module is a pure, deterministic function layer. It compares the
previous state and the observed state of one explicit scope and returns
transitions that fit :class:`~msgloom.a2_kedro.contracts.transition.
TransitionItem`. It reads no file, clock, database or provider.

Scope and role
==============

A :class:`ScopeObservation` names one scope (catalog, source, stream and
consumer through :class:`ScopeRef`, plus a scope kind and a scope ID). It
has one role:

* ``content``: the scope owns the content of its resources. A changed
  content hash is a content refresh.
* ``membership``: the scope lists which resources belong to a container,
  for example a folder. Content hashes are not part of this role. A
  record with a content hash is rejected, so the two kinds of fact stay
  separate.

A producer that tracks both facts runs the function twice, once per
role and scope. The two outputs never merge, because each transition
carries its own scope kind and scope ID.

Decision table
==============

For one resource key (resource kind plus resource ID):

======================  =====================  ===========================
previous / observed     condition              result
======================  =====================  ===========================
any / provider marker   content role,          ``deletion`` (marker
                        marker has authority   authority)
any / provider marker   membership role        refused (``membership_marker``)
absent / present        none                   ``presence``
present / present       content hash differs   ``context_refresh``
                        (content role only)
present / present       same hash or           no transition
                        membership role
present / absent        complete enumeration,  ``absence``
                        content role
present / absent        complete enumeration,  ``membership_removal``
                        membership role
present / absent        partial enumeration    no transition; one
                                               :class:`UnprovenAbsence`
absent / absent         none                   no transition
======================  =====================  ===========================

A resource that leaves a membership scope is not deleted. Only an
explicit provider marker in a content scope produces ``deletion``. A
marker needs no complete enumeration, because the provider states the
deletion. A marker in a membership scope is refused with
``membership_marker``: the scope cannot say whether the deletion applies
to the container or to the content. The producer must run the marker
through a content scope. The owner may change this rule.

Partial enumeration
===================

A partial scope yields :class:`UnprovenAbsence` values and one
``absence_not_proven`` limitation. :func:`to_batch` refuses such an
outcome with ``partial_scope``, because :class:`TransitionBatch` has no
field for a limitation and the batch would look complete. A caller that
accepts a partial outcome must use :func:`to_items` and keep the
limitations beside the items.

Authority
=========

The scope observation carries the authority of its source. Presence,
refresh, absence and membership removal use it. A deletion uses the
authority of its marker. The marker authority must equal the scope
authority, or the function raises ``authority_mismatch``. A record
cannot claim another authority than its scope. The function never
invents an authority.

Ordering and replay
===================

The result sorts by ``(resource_kind, resource_id)``. Input order does
not change it. The same input gives the same output. Each key yields at
most one transition, so the item order is stable.

Failure handling
================

A bad input raises :exc:`TransitionSemanticsError`. The error holds a
closed ``code`` and a record position. It never holds a resource ID,
scope text, hash or authority. Cross-scope input, a duplicate record,
a conflicting record, a role violation, an observed item of the wrong
type and a fact ID shared by two transitions are all rejected. The
scope entry must belong to the scope catalog. The function never repairs input.

The record models derive from ``ResultPart``. It hides input values in
pydantic construction errors, so a rejected payload is not echoed.

CANDIDATE/RESEARCH, PROVISIONAL: names are not frozen. See
``docs/notes/a2-v2-semantics-p3-08.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from msgloom.a2_kedro.contracts.codec import (
    A2ContractError,
    Digest,
    Text,
)
from msgloom.a2_kedro.contracts.header import LIMITS
from msgloom.a2_kedro.contracts.result_base import ResultPart
from msgloom.a2_kedro.contracts.transition import (
    TransitionBatch,
    TransitionItem,
    TransitionKind,
)
from msgloom.contracts import Limitation, ResultRef
from msgloom.preparation_pipeline.intake_models import IntakeScope
from msgloom.sources.handoff_models import ReleaseEntryRef

#: Provisional bound for one input list.
MAX_RECORDS = 65536

ABSENCE_NOT_PROVEN = "absence_not_proven"

Role = Literal["content", "membership"]
Enumeration = Literal["complete", "partial"]

#: Closed error codes. Messages are fixed text and carry no payload.
_MESSAGES = {
    "cross_scope": "record belongs to another scope",
    "duplicate_record": "duplicate record for one key",
    "conflicting_record": "conflicting records for one key",
    "role_violation": "record does not fit the scope role",
    "fact_conflict": "one fact ID is used by two transitions",
    "too_many": "record or transition count is out of bounds",
    "bad_record_type": "observed item is not an observed record",
    "authority_mismatch": "deletion authority differs from scope authority",
    "membership_marker": "deletion marker is not allowed in a membership scope",
    "partial_scope": "outcome is partial and cannot form a complete batch",
}


class TransitionSemanticsError(A2ContractError):
    """
    Input to the transition layer is unsafe.

    ``code`` is one of a closed set. ``position`` is the index of the
    offending record in its input list, or ``None``. The message never
    contains resource, scope, hash or authority text.
    """

    def __init__(self, code: str, position: int | None = None) -> None:
        if code not in _MESSAGES:
            raise ValueError("unknown transition error code")
        self.code = code
        self.position = position
        where = "" if position is None else f" (record {position})"
        super().__init__(f"{code}: {_MESSAGES[code]}{where}")


class ScopeRef(ResultPart):
    """One explicit scope: the intake scope plus a scope kind and ID."""

    intake: IntakeScope
    scope_kind: Text
    scope_id: Text


class StateRecord(ResultPart):
    """
    One known resource of one scope in one state snapshot.

    ``content_sha256`` is required in a content scope and refused in a
    membership scope. ``fact_id`` is the A1 released fact of the
    resource.
    """

    scope: ScopeRef
    resource_kind: Text
    resource_id: Text
    fact_id: Digest
    content_sha256: Digest | None = None

    def key(self) -> tuple[str, str]:
        """Return the resource key inside the scope."""
        return (self.resource_kind, self.resource_id)


class ObservedRecord(StateRecord):
    """
    One resource seen now, with the release entry that carried it.

    ``deletion_authority`` is set only for an explicit provider deletion
    marker. It must equal ``ScopeObservation.authority``. A marker record
    has no content hash.
    """

    entry: ReleaseEntryRef
    deletion_authority: Text | None = None


class ScopeObservation(ResultPart):
    """
    The scope being compared and what the observation proves about it.

    ``enumeration="complete"`` states that the observed records list
    every resource of the scope. ``entry`` is the release entry that
    carries absence and removal facts, which have no observed record.
    """

    scope: ScopeRef
    role: Role
    enumeration: Enumeration
    authority: Text
    entry: ReleaseEntryRef


class ScopedTransition(ResultPart):
    """One derived transition, ready for :class:`TransitionItem`."""

    entry: ReleaseEntryRef
    fact_id: Digest
    scope_kind: Text
    scope_id: Text
    kind: TransitionKind
    authority: Text
    resource_kind: Text
    resource_id: Text


class UnprovenAbsence(ResultPart):
    """A resource missing from a partial scope. Deletion is not proven."""

    scope_kind: Text
    scope_id: Text
    resource_kind: Text
    resource_id: Text
    fact_id: Digest


@dataclass(frozen=True, slots=True)
class TransitionOutcome:
    """
    Result of one comparison.

    ``unproven`` lists absences that a partial scope cannot prove.
    ``limitations`` holds one ``absence_not_proven`` limitation when
    ``unproven`` is not empty. The detail text holds a count only.
    """

    transitions: tuple[ScopedTransition, ...]
    unproven: tuple[UnprovenAbsence, ...]
    limitations: tuple[Limitation, ...]

    @property
    def complete(self) -> bool:
        """Return whether every absence in the scope was decided."""
        return not self.unproven


def _index(
    records: tuple[StateRecord, ...], scope: ScopeObservation
) -> dict[tuple[str, str], StateRecord]:
    """Validate scope, role and key uniqueness; return records by key."""
    if len(records) > MAX_RECORDS:
        raise TransitionSemanticsError("too_many")
    found: dict[tuple[str, str], StateRecord] = {}
    for position, record in enumerate(records):
        if record.scope != scope.scope:
            raise TransitionSemanticsError("cross_scope", position)
        if isinstance(record, ObservedRecord) and (
            record.entry.catalog != scope.scope.intake.catalog
        ):
            raise TransitionSemanticsError("cross_scope", position)
        _check_role(record, scope.role, position)
        _check_authority(record, scope, position)
        key = record.key()
        if key not in found:
            found[key] = record
            continue
        code = "duplicate_record" if found[key] == record else "conflicting_record"
        raise TransitionSemanticsError(code, position)
    return found


def _check_role(record: StateRecord, role: Role, position: int) -> None:
    marker = (
        isinstance(record, ObservedRecord) and record.deletion_authority is not None
    )
    has_hash = record.content_sha256 is not None
    if role == "membership" and marker:
        # Leaving membership is not deletion. Refuse the marker, whatever
        # its authority or hash, instead of guessing its meaning.
        raise TransitionSemanticsError("membership_marker", position)
    if role == "membership" and has_hash:
        raise TransitionSemanticsError("role_violation", position)
    if role == "content" and has_hash == marker:
        # A content record needs a hash. A marker must not have one.
        raise TransitionSemanticsError("role_violation", position)


def _check_authority(
    record: StateRecord, scope: ScopeObservation, position: int
) -> None:
    """Refuse a deletion marker that claims another authority than the scope."""
    if not isinstance(record, ObservedRecord):
        return
    claim = record.deletion_authority
    if claim is not None and claim != scope.authority:
        raise TransitionSemanticsError("authority_mismatch", position)


def _transition(
    scope: ScopeObservation,
    record: StateRecord,
    entry: ReleaseEntryRef,
    kind: TransitionKind,
    authority: str,
) -> ScopedTransition:
    return ScopedTransition(
        entry=entry,
        fact_id=record.fact_id,
        scope_kind=scope.scope.scope_kind,
        scope_id=scope.scope.scope_id,
        kind=kind,
        authority=authority,
        resource_kind=record.resource_kind,
        resource_id=record.resource_id,
    )


def _present(
    scope: ScopeObservation, before: StateRecord | None, now: ObservedRecord
) -> ScopedTransition | None:
    if now.deletion_authority is not None:
        # ``_index`` proved that the marker authority equals the scope's.
        return _transition(scope, now, now.entry, "deletion", scope.authority)
    if before is None:
        return _transition(scope, now, now.entry, "presence", scope.authority)
    changed = before.content_sha256 != now.content_sha256
    if scope.role == "content" and changed:
        return _transition(scope, now, now.entry, "context_refresh", scope.authority)
    return None


def derive_transitions(
    scope: ScopeObservation,
    previous: tuple[StateRecord, ...],
    observed: tuple[ObservedRecord, ...],
) -> TransitionOutcome:
    """
    Compare previous and observed state of one scope.

    ``previous`` holds the resources known to be present before. It must
    not hold provider markers. ``observed`` holds the resources seen now.
    Both must belong to ``scope``. See the module docstring for the
    decision table. Raise :exc:`TransitionSemanticsError` for any
    violation.
    """
    if scope.entry.catalog != scope.scope.intake.catalog:
        raise TransitionSemanticsError("cross_scope")
    if any(isinstance(record, ObservedRecord) for record in previous):
        raise TransitionSemanticsError("role_violation")
    for position, item in enumerate(observed):
        if not isinstance(item, ObservedRecord):
            raise TransitionSemanticsError("bad_record_type", position)
    before = _index(previous, scope)
    now = _index(observed, scope)
    transitions: list[ScopedTransition] = []
    unproven: list[UnprovenAbsence] = []
    for key in sorted(before.keys() | now.keys()):
        seen = now.get(key)
        old = before.get(key)
        if isinstance(seen, ObservedRecord):
            if (change := _present(scope, old, seen)) is not None:
                transitions.append(change)
            continue
        if old is None:
            continue
        if scope.enumeration == "partial":
            unproven.append(_unproven(scope, old))
            continue
        kind: TransitionKind = (
            "absence" if scope.role == "content" else "membership_removal"
        )
        transitions.append(_transition(scope, old, scope.entry, kind, scope.authority))
    _check_facts(transitions)
    return TransitionOutcome(
        transitions=tuple(transitions),
        unproven=tuple(unproven),
        limitations=_limitations(len(unproven)),
    )


def _unproven(scope: ScopeObservation, record: StateRecord) -> UnprovenAbsence:
    return UnprovenAbsence(
        scope_kind=scope.scope.scope_kind,
        scope_id=scope.scope.scope_id,
        resource_kind=record.resource_kind,
        resource_id=record.resource_id,
        fact_id=record.fact_id,
    )


def _limitations(count: int) -> tuple[Limitation, ...]:
    if count == 0:
        return ()
    detail = f"{count} absence(s) not proven: scope enumeration is partial"
    return (Limitation(ABSENCE_NOT_PROVEN, detail),)


def _check_facts(transitions: list[ScopedTransition]) -> None:
    if len(transitions) > LIMITS["max_transitions"]:
        raise TransitionSemanticsError("too_many")
    facts = [change.fact_id for change in transitions]
    if len(set(facts)) != len(facts):
        raise TransitionSemanticsError("fact_conflict")


def to_items(
    transitions: tuple[ScopedTransition, ...], first_ordinal: int = 0
) -> tuple[TransitionItem, ...]:
    """Return contiguous :class:`TransitionItem` values in input order."""
    return tuple(
        TransitionItem(
            ordinal=first_ordinal + offset,
            entry=change.entry,
            fact_id=change.fact_id,
            scope_kind=change.scope_kind,
            scope_id=change.scope_id,
            kind=change.kind,
            authority=change.authority,
        )
        for offset, change in enumerate(transitions)
    )


def to_batch(
    outcome: TransitionOutcome,
    workset: ResultRef,
    code_version: str,
    policy_version: str,
) -> TransitionBatch:
    """
    Build a :class:`TransitionBatch` from the decided transitions.

    Raise ``partial_scope`` for an outcome with unproven absences. The
    batch has no limitation field, so it would look complete. An outcome
    with no transition cannot form a batch, because a batch needs at
    least one item.
    """
    if not outcome.complete or outcome.limitations:
        raise TransitionSemanticsError("partial_scope")
    items = to_items(outcome.transitions)
    return TransitionBatch.build(workset, code_version, policy_version, items)
