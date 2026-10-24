"""
``native_relations@1``: scoped reply, ancestor and reference hypotheses.

A relation is a hypothesis. It is never a fact. Every relation carries
``status="hypothesis"`` and a ``basis`` text that names its evidence. A
later stage may confirm a hypothesis; this record cannot.

Every node has an explicit scope: a scope kind (``mailbox``, ``thread`` or
``channel``), a scope ID and a node ID. Two nodes with the same node ID in
different scopes are different nodes. A relation joins two declared nodes
of the same scope. Equal thread IDs in different scopes never relate.

Rules:

* Relation kinds are closed: ``reply_to``, ``ancestor``, ``reference``.
* Both endpoints must be declared nodes (no dangling target or source).
* No self reference, no duplicate ``(kind, source, target)``.
* The ``reply_to`` and ``ancestor`` edges together have no cycle.
* Nodes and relations are sorted, so the canonical bytes are unique.

CANDIDATE/RESEARCH, PROVISIONAL: field names and limits are not frozen.
See ``docs/notes/a2-v2-contract-c0-06.md``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from msgloom.a2_kedro.contracts.codec import (
    A2ContractError,
    A2Model,
    Text,
    canonical_model_bytes,
    decode_model_bytes,
)
from msgloom.a2_kedro.contracts.header import StageHeader

KIND = "native_relations"
VERSION = "1"

#: Provisional bounds.
MAX_NODES = 1024
MAX_RELATIONS = 4096

ScopeKind = Literal["mailbox", "thread", "channel"]
RelationKind = Literal["reply_to", "ancestor", "reference"]
ACYCLIC_KINDS: frozenset[str] = frozenset({"reply_to", "ancestor"})


class NodeRef(A2Model):
    """One node, identified by scope kind, scope ID and node ID together."""

    scope_kind: ScopeKind
    scope_id: Text
    node_id: Text

    def sort_key(self) -> tuple[str, str, str]:
        """Return the canonical ordering key."""
        return (self.scope_kind, self.scope_id, self.node_id)


class Relation(A2Model):
    """One hypothesis that ``source`` relates to ``target``."""

    kind: RelationKind
    source: NodeRef
    target: NodeRef
    status: Literal["hypothesis"] = "hypothesis"
    basis: Text

    @model_validator(mode="after")
    def _same_scope_no_self(self) -> Relation:
        if self.source == self.target:
            raise A2ContractError("relation refers to itself")
        if self.source.scope_kind != self.target.scope_kind or (
            self.source.scope_id != self.target.scope_id
        ):
            raise A2ContractError("relation crosses scopes")
        return self

    def sort_key(self) -> tuple[object, ...]:
        """Return the canonical ordering key."""
        return (self.kind, self.source.sort_key(), self.target.sort_key())


def _find_cycle(edges: dict[NodeRef, list[NodeRef]]) -> bool:
    state: dict[NodeRef, int] = {}
    for start in edges:
        if state.get(start):
            continue
        stack = [(start, iter(edges.get(start, ())))]
        state[start] = 1
        while stack:
            node, children = stack[-1]
            child = next(children, None)
            if child is None:
                state[node] = 2
                stack.pop()
                continue
            if state.get(child) == 1:
                return True
            if state.get(child) is None:
                state[child] = 1
                stack.append((child, iter(edges.get(child, ()))))
    return False


class NativeRelations(A2Model):
    """Declared nodes plus relation hypotheses among them."""

    header: StageHeader = Field(
        default_factory=lambda: StageHeader(kind=KIND, version=VERSION)
    )
    nodes: tuple[NodeRef, ...]
    relations: tuple[Relation, ...] = ()

    @model_validator(mode="after")
    def _closed(self) -> NativeRelations:
        if (self.header.kind, self.header.version) != (KIND, VERSION):
            raise A2ContractError("header is not native_relations@1")
        if len(self.nodes) > MAX_NODES or len(self.relations) > MAX_RELATIONS:
            raise A2ContractError("relation record exceeds count bound")
        keys = [node.sort_key() for node in self.nodes]
        if len(set(keys)) != len(keys):
            raise A2ContractError("duplicate node")
        if keys != sorted(keys):
            raise A2ContractError("nodes are not sorted")
        rkeys = [rel.sort_key() for rel in self.relations]
        if len(set(rkeys)) != len(rkeys):
            raise A2ContractError("duplicate relation")
        if rkeys != sorted(rkeys):
            raise A2ContractError("relations are not sorted")
        declared = set(self.nodes)
        edges: dict[NodeRef, list[NodeRef]] = {}
        for rel in self.relations:
            if rel.source not in declared or rel.target not in declared:
                raise A2ContractError("relation endpoint is not declared")
            if rel.kind in ACYCLIC_KINDS:
                edges.setdefault(rel.source, []).append(rel.target)
        if _find_cycle(edges):
            raise A2ContractError("ancestor or reply cycle")
        return self

    def encode(self) -> bytes:
        """Return the bounded canonical bytes of this record."""
        return canonical_model_bytes(self)

    @classmethod
    def decode(cls, data: bytes) -> NativeRelations:
        """Strictly decode canonical bytes; reject anything else."""
        return decode_model_bytes(cls, data)
