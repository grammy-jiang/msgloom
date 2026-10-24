"""
Relation safety review over native relation hypotheses (P3-02).

This module is a pure, deterministic function layer. It reviews a set of
relation candidates and says, for each one, whether a later stage may
confirm it without a human look. It reads no file, clock, database or
provider, and it never changes a relation.

Input
=====

A :class:`RelationReviewInput` holds the declared nodes and the candidate
relations. A :class:`CandidateRelation` has a kind, a ``child``, a
``parent`` and a ``basis`` (the evidence text). Each end is a
:class:`~msgloom.a2_kedro.contracts.relations.NodeRef`, so the scope of
each end is explicit. For ``reply_to`` and ``ancestor`` the child is the
later message and the parent is the earlier one; this matches the
``source`` and ``target`` of the contract.

The contract type
:class:`~msgloom.a2_kedro.contracts.relations.Relation` cannot carry a
cross-scope edge, a self edge or a cycle: its validator rejects them. The
reviewer therefore takes its own looser input. :meth:`from_native` turns a
valid P3-01 record into this input.

Review rules
============

A relation is ``CONFIRMED`` only when no reason below applies. Otherwise it
is ``NEEDS_REVIEW`` and lists every reason that applies, sorted.

===========================  ===============================================
Reason                       Condition
===========================  ===============================================
``cycle``                    the ``reply_to`` or ``ancestor`` edge lies in a
                             cycle of any length, a self parent included
``missing_parent``           the parent is not a declared node
``duplicate_message_id``     the child or the parent is declared more than
                             once with the same scope and ID
``cross_scope``              child and parent have different scopes
===========================  ===============================================

Notes for a reviewer of this module:

* Every edge inside a cycle is flagged, so every member is flagged. An
  edge that only leads into a cycle is not part of it and is not flagged.
* A duplicate ID flags every relation that touches it. The module never
  picks a winner among colliding nodes.
* A Message-ID is scoped. The same ID in two scopes is two nodes, as in
  the contract, and is not a duplicate.
* ``reference`` edges may form a cycle (as in the contract), so they are
  not checked for cycles. They are checked for the other reasons.
* A cross-scope relation is never ``CONFIRMED``, even when it is otherwise
  perfect.

Ordering and failure handling
=============================

Output order does not depend on input order. Reviews sort by kind, child,
parent and basis. Equal candidates collapse to one review. The cycle search
is iterative, so a long chain does not reach a recursion limit.

A candidate whose child is not declared, or an input above the bounds,
raises :exc:`~msgloom.a2_kedro.contracts.codec.A2ContractError` with a fixed
text. A malformed model raises a pydantic error that hides the input. No
error echoes an ID.

CANDIDATE/RESEARCH, PROVISIONAL: names and limits are not frozen.
"""

from __future__ import annotations

from collections import Counter
from enum import StrEnum
from typing import Self

from pydantic import model_validator

from msgloom.a2_kedro.contracts.codec import A2ContractError, Text
from msgloom.a2_kedro.contracts.relations import (
    ACYCLIC_KINDS,
    NativeRelations,
    NodeRef,
    RelationKind,
)
from msgloom.a2_kedro.contracts.result_base import ResultPart

#: Provisional bounds. They exceed the P3-01 record bounds on purpose.
MAX_REVIEW_NODES = 65536
MAX_REVIEW_RELATIONS = 65536


class SafetyStatus(StrEnum):
    """Closed review outcome of one relation."""

    CONFIRMED = "confirmed"
    NEEDS_REVIEW = "needs_review"


class ReviewReason(StrEnum):
    """Closed, content-free reasons that a relation needs review."""

    CROSS_SCOPE = "cross_scope"
    CYCLE = "cycle"
    DUPLICATE_MESSAGE_ID = "duplicate_message_id"
    MISSING_PARENT = "missing_parent"


class CandidateRelation(ResultPart):
    """One relation hypothesis: ``child`` relates to ``parent``."""

    kind: RelationKind
    child: NodeRef
    parent: NodeRef
    basis: Text

    def sort_key(self) -> tuple[object, ...]:
        """Return the canonical ordering key."""
        return (self.kind, self.child.sort_key(), self.parent.sort_key(), self.basis)


class RelationReviewInput(ResultPart):
    """Declared nodes and candidate relations of one review call."""

    nodes: tuple[NodeRef, ...]
    relations: tuple[CandidateRelation, ...] = ()

    @model_validator(mode="after")
    def _bounded_and_declared(self) -> Self:
        if (
            len(self.nodes) > MAX_REVIEW_NODES
            or len(self.relations) > MAX_REVIEW_RELATIONS
        ):
            raise A2ContractError("review input exceeds count bound")
        declared = set(self.nodes)
        if any(rel.child not in declared for rel in self.relations):
            raise A2ContractError("relation child is not a declared node")
        return self

    @classmethod
    def from_native(cls, record: NativeRelations) -> Self:
        """Build the input from a valid P3-01 relation record."""
        return cls(
            nodes=record.nodes,
            relations=tuple(
                CandidateRelation(
                    kind=rel.kind,
                    child=rel.source,
                    parent=rel.target,
                    basis=rel.basis,
                )
                for rel in record.relations
            ),
        )


class RelationReview(ResultPart):
    """The safety status of one relation and the reasons for it."""

    relation: CandidateRelation
    status: SafetyStatus
    reasons: tuple[ReviewReason, ...] = ()

    @model_validator(mode="after")
    def _status_matches_reasons(self) -> Self:
        if list(self.reasons) != sorted(set(self.reasons)):
            raise A2ContractError("reasons are not sorted and distinct")
        confirmed = self.status is SafetyStatus.CONFIRMED
        if confirmed == bool(self.reasons):
            raise A2ContractError("status does not match reasons")
        return self


class RelationSafetyReview(ResultPart):
    """All reviews of one call, sorted by relation."""

    reviews: tuple[RelationReview, ...] = ()

    def with_status(self, status: SafetyStatus) -> tuple[RelationReview, ...]:
        """Return the reviews that have ``status``, in order."""
        return tuple(item for item in self.reviews if item.status is status)


#: A hashable node identity: ``(scope_kind, scope_id, node_id)``.
Key = tuple[str, str, str]


def _component_numbers(
    nodes: list[Key], edges: list[tuple[Key, Key]]
) -> dict[Key, int]:
    """
    Return a strongly connected group number for each node.

    This is Kosaraju's two-pass search with explicit stacks. An edge is on
    a cycle if and only if both of its ends are in one group.
    """
    forward: dict[Key, list[Key]] = {node: [] for node in nodes}
    backward: dict[Key, list[Key]] = {node: [] for node in nodes}
    for src, dst in edges:
        forward[src].append(dst)
        backward[dst].append(src)

    seen: set[Key] = set()
    finished: list[Key] = []
    for root in nodes:
        if root in seen:
            continue
        seen.add(root)
        stack = [(root, iter(forward[root]))]
        while stack:
            node, children = stack[-1]
            for child in children:
                if child not in seen:
                    seen.add(child)
                    stack.append((child, iter(forward[child])))
                    break
            else:
                finished.append(node)
                stack.pop()

    number: dict[Key, int] = {}
    groups = 0
    for root in reversed(finished):
        if root in number:
            continue
        number[root] = groups
        groups += 1
        pending = [root]
        while pending:
            for prev in backward[pending.pop()]:
                if prev not in number:
                    number[prev] = number[root]
                    pending.append(prev)
    return number


def _cyclic_edges(candidates: list[CandidateRelation]) -> set[tuple[object, ...]]:
    """Return the sort keys of ``reply_to``/``ancestor`` edges on a cycle."""
    acyclic = [rel for rel in candidates if rel.kind in ACYCLIC_KINDS]
    edges = [(rel.child.sort_key(), rel.parent.sort_key()) for rel in acyclic]
    nodes = sorted({end for edge in edges for end in edge})
    groups = _component_numbers(nodes, edges)
    return {
        rel.sort_key()
        for rel, (src, dst) in zip(acyclic, edges, strict=True)
        if groups[src] == groups[dst]
    }


def _same_scope(child: NodeRef, parent: NodeRef) -> bool:
    return (child.scope_kind, child.scope_id) == (parent.scope_kind, parent.scope_id)


def review_relations(review: RelationReviewInput) -> RelationSafetyReview:
    """
    Review every relation candidate and return a safety status for each.

    The result is deterministic and independent of input order. See the
    module docstring for the rules.
    """
    counts = Counter(node.sort_key() for node in review.nodes)
    duplicated = {key for key, count in counts.items() if count > 1}
    unique = {rel.sort_key(): rel for rel in review.relations}
    candidates = [unique[key] for key in sorted(unique)]
    on_cycle = _cyclic_edges(candidates)

    items: list[RelationReview] = []
    for rel in candidates:
        reasons: set[ReviewReason] = set()
        if rel.sort_key() in on_cycle:
            reasons.add(ReviewReason.CYCLE)
        if rel.parent.sort_key() not in counts:
            reasons.add(ReviewReason.MISSING_PARENT)
        if {rel.child.sort_key(), rel.parent.sort_key()} & duplicated:
            reasons.add(ReviewReason.DUPLICATE_MESSAGE_ID)
        if not _same_scope(rel.child, rel.parent):
            reasons.add(ReviewReason.CROSS_SCOPE)
        items.append(
            RelationReview(
                relation=rel,
                status=(
                    SafetyStatus.NEEDS_REVIEW if reasons else SafetyStatus.CONFIRMED
                ),
                reasons=tuple(sorted(reasons)),
            )
        )
    return RelationSafetyReview(reviews=tuple(items))
