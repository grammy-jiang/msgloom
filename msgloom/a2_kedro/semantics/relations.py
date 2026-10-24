"""
Native relation recovery for ``native_relations@1`` (P3-01).

This module is a pure, deterministic function layer. It reads typed,
already-extracted evidence of ONE source and returns a
:class:`~msgloom.a2_kedro.contracts.relations.NativeRelations` record plus
the unresolved relations and limitations that the record cannot hold. It
reads no file, clock, database or provider.

Evidence
========

A :class:`SourceEvidence` names one scope (scope kind and scope ID, for
example a thread with its conversation ID) and lists its
:class:`MessageEvidence` items. A message carries only explicit facts:

* ``reply_parent_ids``: IDs named by an explicit parent field
  (``In-Reply-To``, a reply-to-message field).
* ``ancestor_ids``: IDs of an explicit ancestor list (``References``),
  ordered root first. The list order is kept.
* ``quote_markers``: quote markers, each with an optional target ID.
* ``conversation_id``: an optional conversation ID, used only as a
  consistency check.

The function never reads a subject, a time or an author. It never links
two sources. One call handles one source.

Rules
=====

======================  ====================================================
Relation kind           Evidence and basis text
======================  ====================================================
``reply_to``            one distinct ID in ``reply_parent_ids``;
                        basis ``same_source:reply_parent``
``ancestor``            each ID in ``ancestor_ids``, nearest
                        ``MAX_ANCESTOR_DEPTH`` kept;
                        basis ``same_source:ancestor_list``
``reference``           a quote marker with a target ID;
                        basis ``same_source:quote_marker``
======================  ====================================================

The contract has no quote kind, so a quote source is a ``reference``. The
basis text tells the kinds apart. The three kinds are never merged. A
parent that also appears in the ancestor list gives one ``reply_to`` and
one ``ancestor`` relation.

A target that is not a message of the source gives an
:class:`UnresolvedRelation` and a limitation. The function never guesses a
link, and a native record never holds an unresolved endpoint.

Limitations
===========

Each problem below gives a :class:`RelationLimitation`. The function
drops the affected relation and keeps the rest.

* ``self_reference``: a message names itself.
* ``conflicting_parents``: two or more distinct parent IDs. No ``reply_to``.
* ``duplicate_reference``: an ID repeats in one list. The list is deduped.
* ``duplicate_message_id``: two items share one ID. Equal items merge.
  Items that differ make the ID ambiguous: the node stays, its outgoing
  relations are dropped, and an incoming relation is unresolved with
  ``ambiguous_target``.
* ``unresolved_target``: the target is not in the source.
* ``conversation_mismatch``: both messages have a conversation ID and the
  IDs differ. The relation is dropped.
* ``quote_without_target``: a quote marker names no target.
* ``cycle``: ``reply_to`` and ``ancestor`` edges form a cycle. Every such
  edge inside one strongly connected group is dropped, so no edge is chosen
  by input order. ``reference`` cycles are legal.
* ``depth_exceeded``, ``list_too_long``, ``too_many_messages``,
  ``too_many_relations``, ``too_many_unresolved``,
  ``too_many_limitations``: a bound was hit. Truncation is deterministic.
  A target lost to ``too_many_messages`` is unresolved.

Output bounds
=============

The output is bounded. ``unresolved`` holds at most ``MAX_UNRESOLVED``
items and ``limitations`` at most ``MAX_LIMITATIONS`` items. Each list keeps
its sorted prefix. One stand-in limitation names each cut. The stand-ins
(all ``too_many_*`` codes) are never cut away. The input is bounded too:
``SourceEvidence.messages`` holds at most ``MAX_INPUT_MESSAGES`` items and
each ID or marker tuple at most ``MAX_INPUT_IDS`` items. A longer tuple is
rejected as a malformed model, not truncated.

Ordering and failure handling
=============================

Output order does not depend on input order. Nodes, relations, unresolved
relations and limitations are sorted. The function does not raise for bad
evidence; it reports a limitation. A malformed model raises a pydantic
error that hides the input, so an ID is not echoed.

CANDIDATE/RESEARCH, PROVISIONAL: names and limits are not frozen. See
``docs/notes/a2-v2-semantics-p3-01.md``.
"""

from __future__ import annotations

from collections import defaultdict
from enum import StrEnum

from pydantic import Field

from msgloom.a2_kedro.contracts.codec import Text
from msgloom.a2_kedro.contracts.relations import (
    ACYCLIC_KINDS,
    MAX_NODES,
    MAX_RELATIONS,
    NativeRelations,
    NodeRef,
    Relation,
    RelationKind,
    ScopeKind,
)
from msgloom.a2_kedro.contracts.result_base import ResultPart

#: Provisional bounds.
MAX_ANCESTOR_DEPTH = 64
MAX_PARENT_REFS = 8
MAX_QUOTE_MARKERS = 16
MAX_UNRESOLVED = 256
MAX_LIMITATIONS = 256
#: Input bounds. They sit above the processing bounds, so a long but
#: plausible list still gets a limitation instead of a rejection.
MAX_INPUT_MESSAGES = 2 * MAX_NODES
MAX_INPUT_IDS = 2 * MAX_ANCESTOR_DEPTH

BASIS_REPLY = "same_source:reply_parent"
BASIS_ANCESTOR = "same_source:ancestor_list"
BASIS_QUOTE = "same_source:quote_marker"


class LimitationCode(StrEnum):
    """Closed, content-free reasons that recovery is not complete."""

    SELF_REFERENCE = "self_reference"
    CONFLICTING_PARENTS = "conflicting_parents"
    DUPLICATE_REFERENCE = "duplicate_reference"
    DUPLICATE_MESSAGE_ID = "duplicate_message_id"
    AMBIGUOUS_TARGET = "ambiguous_target"
    UNRESOLVED_TARGET = "unresolved_target"
    CONVERSATION_MISMATCH = "conversation_mismatch"
    QUOTE_WITHOUT_TARGET = "quote_without_target"
    CYCLE = "cycle"
    DEPTH_EXCEEDED = "depth_exceeded"
    LIST_TOO_LONG = "list_too_long"
    TOO_MANY_MESSAGES = "too_many_messages"
    TOO_MANY_RELATIONS = "too_many_relations"
    TOO_MANY_UNRESOLVED = "too_many_unresolved"
    TOO_MANY_LIMITATIONS = "too_many_limitations"


_STAND_INS = frozenset(
    {
        LimitationCode.TOO_MANY_MESSAGES,
        LimitationCode.TOO_MANY_RELATIONS,
        LimitationCode.TOO_MANY_UNRESOLVED,
        LimitationCode.TOO_MANY_LIMITATIONS,
    }
)


class QuoteMarker(ResultPart):
    """One quote marker. ``target_id`` is the quoted message, if named."""

    target_id: Text | None = None


class MessageEvidence(ResultPart):
    """Explicit relation facts of one message of one source."""

    message_id: Text
    conversation_id: Text | None = None
    reply_parent_ids: tuple[Text, ...] = Field(default=(), max_length=MAX_INPUT_IDS)
    ancestor_ids: tuple[Text, ...] = Field(default=(), max_length=MAX_INPUT_IDS)
    quote_markers: tuple[QuoteMarker, ...] = Field(default=(), max_length=MAX_INPUT_IDS)


class SourceEvidence(ResultPart):
    """All messages of one source and the scope that holds them."""

    scope_kind: ScopeKind
    scope_id: Text
    messages: tuple[MessageEvidence, ...] = Field(
        default=(), max_length=MAX_INPUT_MESSAGES
    )


class RelationLimitation(ResultPart):
    """One reason that a relation or a list was dropped or cut."""

    code: LimitationCode
    kind: RelationKind | None = None
    message_id: Text | None = None
    target_id: Text | None = None

    def sort_key(self) -> tuple[str, str, str, str]:
        """Return the canonical ordering key."""
        return (
            self.code.value,
            self.kind or "",
            self.message_id or "",
            self.target_id or "",
        )


class UnresolvedRelation(ResultPart):
    """A named relation whose target is not a usable node of the source."""

    kind: RelationKind
    source_id: Text
    target_id: Text
    limitation: LimitationCode

    def sort_key(self) -> tuple[str, str, str]:
        """Return the canonical ordering key."""
        return (self.kind, self.source_id, self.target_id)


class RelationRecovery(ResultPart):
    """Recovered relations, unresolved relations and limitations."""

    relations: NativeRelations
    unresolved: tuple[UnresolvedRelation, ...] = ()
    limitations: tuple[RelationLimitation, ...] = ()


_Limit = tuple[LimitationCode, RelationKind | None, str | None, str | None]


def _limit_key(item: _Limit) -> tuple[str, str, str, str]:
    code, kind, message_id, target_id = item
    return (code.value, kind or "", message_id or "", target_id or "")


class _Run:
    """Mutable collector for one call. It never leaves this module."""

    def __init__(self, source: SourceEvidence) -> None:
        self.source = source
        # Plain tuples are cheap. Models are built after the bounds apply.
        # limit: (code, kind, message ID, target ID)
        self.limits: set[_Limit] = set()
        # unresolved: (kind, source ID, target ID, code)
        self.unresolved: set[tuple[RelationKind, str, str, LimitationCode]] = set()
        # (kind, source id, target id) -> basis text
        self.edges: dict[tuple[str, str, str], str] = {}
        self.known: dict[str, MessageEvidence] = {}
        self.ambiguous: set[str] = set()

    def limit(
        self,
        code: LimitationCode,
        kind: RelationKind | None = None,
        message_id: str | None = None,
        target_id: str | None = None,
    ) -> None:
        self.limits.add((code, kind, message_id, target_id))

    def unresolve(
        self, kind: RelationKind, src: str, dst: str, code: LimitationCode
    ) -> None:
        self.unresolved.add((kind, src, dst, code))
        self.limit(code, kind, src, dst)

    def declare(self) -> None:
        """Group messages by ID, merge equal items and mark ambiguity."""
        groups: dict[str, list[MessageEvidence]] = defaultdict(list)
        for msg in self.source.messages:
            groups[msg.message_id].append(msg)
        ids = sorted(groups)
        if len(ids) > MAX_NODES:
            self.limit(LimitationCode.TOO_MANY_MESSAGES)
            ids = ids[:MAX_NODES]
        for mid in ids:
            items = groups[mid]
            self.known[mid] = items[0]
            if len(items) == 1:
                continue
            self.limit(LimitationCode.DUPLICATE_MESSAGE_ID, message_id=mid)
            if any(item != items[0] for item in items):
                self.ambiguous.add(mid)

    def target_ok(self, kind: RelationKind, msg: MessageEvidence, dst: str) -> bool:
        """Return True if ``dst`` is a usable same-source target."""
        src = msg.message_id
        if dst == src:
            self.limit(LimitationCode.SELF_REFERENCE, kind, src)
            return False
        if dst in self.ambiguous:
            self.unresolve(kind, src, dst, LimitationCode.AMBIGUOUS_TARGET)
            return False
        if (other := self.known.get(dst)) is None:
            self.unresolve(kind, src, dst, LimitationCode.UNRESOLVED_TARGET)
            return False
        if (
            msg.conversation_id
            and other.conversation_id
            and msg.conversation_id != other.conversation_id
        ):
            self.limit(LimitationCode.CONVERSATION_MISMATCH, kind, src, dst)
            return False
        return True

    def deduped(
        self, kind: RelationKind, msg: MessageEvidence, ids: tuple[str, ...]
    ) -> list[str]:
        """Return ``ids`` in order without repeats; report a repeat."""
        seen = list(dict.fromkeys(ids))
        if len(seen) != len(ids):
            self.limit(LimitationCode.DUPLICATE_REFERENCE, kind, msg.message_id)
        return seen

    def add(self, kind: RelationKind, msg: MessageEvidence, dst: str, why: str) -> None:
        if self.target_ok(kind, msg, dst):
            self.edges[(kind, msg.message_id, dst)] = why

    def reply(self, msg: MessageEvidence) -> None:
        parents = self.deduped("reply_to", msg, msg.reply_parent_ids)
        if len(parents) > MAX_PARENT_REFS:
            self.limit(LimitationCode.LIST_TOO_LONG, "reply_to", msg.message_id)
            parents = parents[:MAX_PARENT_REFS]
        if len(parents) > 1:
            self.limit(LimitationCode.CONFLICTING_PARENTS, "reply_to", msg.message_id)
        elif parents:
            self.add("reply_to", msg, parents[0], BASIS_REPLY)

    def ancestors(self, msg: MessageEvidence) -> None:
        chain = self.deduped("ancestor", msg, msg.ancestor_ids)
        if len(chain) > MAX_ANCESTOR_DEPTH:
            self.limit(LimitationCode.DEPTH_EXCEEDED, "ancestor", msg.message_id)
            chain = chain[-MAX_ANCESTOR_DEPTH:]
        for dst in chain:
            self.add("ancestor", msg, dst, BASIS_ANCESTOR)

    def quotes(self, msg: MessageEvidence) -> None:
        targets: list[str] = []
        for marker in msg.quote_markers:
            if marker.target_id is None:
                self.limit(
                    LimitationCode.QUOTE_WITHOUT_TARGET, "reference", msg.message_id
                )
                continue
            targets.append(marker.target_id)
        chain = self.deduped("reference", msg, tuple(targets))
        if len(chain) > MAX_QUOTE_MARKERS:
            self.limit(LimitationCode.LIST_TOO_LONG, "reference", msg.message_id)
            chain = chain[:MAX_QUOTE_MARKERS]
        for dst in chain:
            self.add("reference", msg, dst, BASIS_QUOTE)

    def drop_cycles(self) -> None:
        """Drop ``reply_to`` and ``ancestor`` edges inside a cycle group."""
        graph: dict[str, list[str]] = defaultdict(list)
        for kind, src, dst in sorted(self.edges):
            if kind in ACYCLIC_KINDS:
                graph[src].append(dst)
        group = _components(graph)
        for key in sorted(self.edges):
            kind, src, dst = key
            if kind in ACYCLIC_KINDS and group[src] == group[dst]:
                del self.edges[key]
                self.limit(LimitationCode.CYCLE, _kind(kind), src, dst)


def _kind(value: str) -> RelationKind:
    """Narrow an edge kind text to the contract literal."""
    if value == "reply_to" or value == "ancestor" or value == "reference":
        return value
    raise ValueError("unknown relation kind")


def _components(graph: dict[str, list[str]]) -> dict[str, int]:
    """Return a strongly connected group number for each graph node."""
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    group: dict[str, int] = {}
    on_stack: list[str] = []
    counter = 0
    number = 0
    nodes = sorted(set(graph) | {d for ds in graph.values() for d in ds})
    for root in nodes:
        if root in index:
            continue
        index[root] = low[root] = counter
        counter += 1
        on_stack.append(root)
        work = [(root, iter(graph.get(root, ())))]
        while work:
            node, children = work[-1]
            child = next(children, None)
            if child is not None:
                if child not in index:
                    index[child] = low[child] = counter
                    counter += 1
                    on_stack.append(child)
                    work.append((child, iter(graph.get(child, ()))))
                elif child not in group:
                    low[node] = min(low[node], index[child])
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[node])
            if low[node] != index[node]:
                continue
            number += 1
            while True:
                member = on_stack.pop()
                group[member] = number
                if member == node:
                    break
    return group


def recover_relations(source: SourceEvidence) -> RelationRecovery:
    """
    Recover reply, ancestor and quote relations of one source.

    The result is deterministic and independent of message order. See the
    module docstring for the rules and limitations.
    """
    run = _Run(source)
    run.declare()
    for mid in sorted(run.known):
        if mid in run.ambiguous:
            continue
        msg = run.known[mid]
        run.reply(msg)
        run.ancestors(msg)
        run.quotes(msg)
    run.drop_cycles()

    def ref(node_id: str) -> NodeRef:
        return NodeRef(
            scope_kind=source.scope_kind, scope_id=source.scope_id, node_id=node_id
        )

    # Every edge shares one scope, so the edge key order is the contract order.
    keys = sorted(run.edges)
    if len(keys) > MAX_RELATIONS:
        run.limit(LimitationCode.TOO_MANY_RELATIONS)
        keys = keys[:MAX_RELATIONS]
    record = NativeRelations(
        nodes=tuple(ref(mid) for mid in sorted(run.known)),
        relations=tuple(
            Relation(
                kind=_kind(kind),
                source=ref(src),
                target=ref(dst),
                basis=run.edges[(kind, src, dst)],
            )
            for kind, src, dst in keys
        ),
    )
    unresolved = sorted(run.unresolved, key=lambda u: u[:3])
    if len(unresolved) > MAX_UNRESOLVED:
        run.limit(LimitationCode.TOO_MANY_UNRESOLVED)
        unresolved = unresolved[:MAX_UNRESOLVED]
    return RelationRecovery(
        relations=record,
        unresolved=tuple(
            UnresolvedRelation(kind=kind, source_id=src, target_id=dst, limitation=code)
            for kind, src, dst, code in unresolved
        ),
        limitations=_bounded_limits(run.limits),
    )


def _bounded_limits(limits: set[_Limit]) -> tuple[RelationLimitation, ...]:
    """Sort limitations, cut them to the bound and keep every stand-in."""
    plain = sorted((x for x in limits if x[0] not in _STAND_INS), key=_limit_key)
    stand = {x for x in limits if x[0] in _STAND_INS}
    if len(plain) + len(stand) > MAX_LIMITATIONS:
        stand.add((LimitationCode.TOO_MANY_LIMITATIONS, None, None, None))
        plain = plain[: MAX_LIMITATIONS - len(stand)]
    return tuple(
        RelationLimitation(code=code, kind=kind, message_id=mid, target_id=dst)
        for code, kind, mid, dst in sorted(plain + sorted(stand), key=_limit_key)
    )
