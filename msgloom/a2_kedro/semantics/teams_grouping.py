"""
Teams grouping: chat reply scope versus channel scope (P3-05).

This module is a pure, deterministic function layer. It groups the Teams
messages of one source by scope and checks each reply against the P3-02
relation safety review. It reads no file, clock, database or provider.

Scopes
======

A Teams message lives in exactly one scope:

* ``chat``: one chat, named by ``chat_id``. A reply in a chat stays in
  that chat.
* ``channel``: one channel of one team, named by ``team_id`` and
  ``channel_id`` together. A reply in a channel stays in that channel.

A message ID is scoped. The same ID in a chat and in a channel, or in two
chats, or in two channels, is two different messages. The module never
relates two messages because their IDs are equal. A scope kind other than
``chat`` and ``channel`` is rejected.

Mapping to P3-02. A ``chat`` scope becomes the ``thread`` scope kind with
the chat ID as the scope ID. A ``channel`` scope becomes the ``channel``
scope kind. Its scope ID is ``<byte length of team_id>:<team_id><channel_id>``,
so two different ``(team_id, channel_id)`` pairs never give one scope ID.

Input
=====

A :class:`TeamsGroupingInput` holds one ``source_id`` and a bounded tuple
of :class:`TeamsEntry`. Every entry repeats the ``source_id``. An entry
with another ``source_id`` is a cross-source entry. The input is rejected.
This module never groups two sources together.

An entry has one of two kinds:

``message``
    A message that carries a body. It may name a ``reply_to`` parent.
``component_refresh``
    A refresh that carries components (attachments) only. It carries no
    body and it must not name a parent. ``component_count`` is at least 1.

Rules for a component-only refresh
==================================

A component-only refresh never creates a body. For a message ID that has
only refresh entries, the member has ``has_body=False``. The member keeps
the largest ``component_count`` of the refreshes (a refresh is a
snapshot, so the largest value is idempotent). A refresh never creates a
relation. A refresh does declare the message as a node, so a later reply
may name it as a parent.

When both a ``message`` entry and a refresh exist for one message ID in
one scope, the member has ``has_body=True``. The refresh only adds to the
component count.

Reply review
============

Each ``message`` entry with a ``reply_to`` becomes one ``reply_to``
candidate with the same-source basis ``same_source:reply_parent``. The
candidate goes through :func:`~msgloom.a2_kedro.semantics.relation_safety.
review_relations`. The result keeps its status and reasons. A parent in
another scope is ``needs_review`` with ``cross_scope``. A parent that is
not declared is ``needs_review`` with ``missing_parent``. A message that
is declared twice with a body is ``needs_review`` with
``duplicate_message_id``. This module never confirms a cross-scope reply.

Ordering and failure handling
=============================

Output order does not depend on input order. Groups sort by scope, members
sort by message ID and replies sort by child and parent. Equal replies
collapse to one. The module never normalizes an ID: Unicode forms and case
stay as given, so ``NFC`` and ``NFD`` forms are two IDs.

Every bound is a field limit, checked before the elements are validated.
An invalid input raises a pydantic :exc:`~pydantic.ValidationError` or an
:exc:`~msgloom.a2_kedro.contracts.codec.A2ContractError` with a fixed
text. No error text and no ``repr`` holds an ID: ID fields are hidden from
``repr`` and validation errors hide the input. A control character, a
lone surrogate, an empty ID, a non-``str`` ID and an ID above 2048 bytes
are rejected.

CANDIDATE/RESEARCH, PROVISIONAL: names and limits are not frozen.
"""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from msgloom.a2_kedro.contracts.codec import MAX_TEXT_BYTES, A2ContractError, Text
from msgloom.a2_kedro.contracts.relations import NodeRef
from msgloom.a2_kedro.contracts.result_base import ResultPart
from msgloom.a2_kedro.semantics.relation_safety import (
    CandidateRelation,
    RelationReviewInput,
    ReviewReason,
    SafetyStatus,
    review_relations,
)

#: Provisional bounds.
MAX_ENTRIES = 4096
MAX_COMPONENTS = 1024

#: The one basis text that this module writes. It is in the P3-02 set.
REPLY_BASIS = "same_source:reply_parent"

TeamsScopeKind = Literal["chat", "channel"]
EntryKind = Literal["message", "component_refresh"]

#: A text ID that is hidden from ``repr``.
Id = Annotated[Text, Field(repr=False)]
OptionalId = Annotated[Text | None, Field(repr=False)]
Count = Annotated[int, Field(ge=0, le=MAX_COMPONENTS)]


class TeamsScope(ResultPart):
    """A ``chat`` scope or a ``channel`` scope of Teams."""

    kind: TeamsScopeKind
    chat_id: OptionalId = None
    team_id: OptionalId = None
    channel_id: OptionalId = None

    @model_validator(mode="after")
    def _fields_match_kind(self) -> Self:
        if self.kind == "chat":
            if self.chat_id is None or self.team_id or self.channel_id:
                raise A2ContractError("a chat scope names only chat_id")
            return self
        if self.chat_id is not None or not (self.team_id and self.channel_id):
            raise A2ContractError("a channel scope names team_id and channel_id")
        if len(self.node_scope()[1].encode()) > MAX_TEXT_BYTES:
            raise A2ContractError("channel scope exceeds identifier bound")
        return self

    def node_scope(self) -> tuple[Literal["thread", "channel"], str]:
        """Return the P3-02 ``(scope_kind, scope_id)`` of this scope."""
        if self.kind == "chat":
            return ("thread", self.chat_id or "")
        team = self.team_id or ""
        return ("channel", f"{len(team.encode())}:{team}{self.channel_id}")

    def sort_key(self) -> tuple[str, str, str]:
        """Return the canonical ordering key."""
        kind, scope_id = self.node_scope()
        return (self.kind, kind, scope_id)


class TeamsMessageRef(ResultPart):
    """A message ID inside one scope."""

    scope: TeamsScope
    message_id: Id

    def node(self) -> NodeRef:
        """Return the scoped P3-02 node."""
        kind, scope_id = self.scope.node_scope()
        return NodeRef(scope_kind=kind, scope_id=scope_id, node_id=self.message_id)

    def sort_key(self) -> tuple[str, ...]:
        """Return the canonical ordering key."""
        return (*self.scope.sort_key(), self.message_id)


class TeamsEntry(ResultPart):
    """One Teams message or one component-only refresh."""

    source_id: Id
    scope: TeamsScope
    message_id: Id
    kind: EntryKind
    reply_to: TeamsMessageRef | None = None
    component_count: Count = 0

    @model_validator(mode="after")
    def _kind_rules(self) -> Self:
        if self.kind == "component_refresh" and (
            self.reply_to is not None or self.component_count < 1
        ):
            raise A2ContractError("a refresh has components and no parent")
        return self

    def ref(self) -> TeamsMessageRef:
        """Return the scoped reference of this entry."""
        return TeamsMessageRef(scope=self.scope, message_id=self.message_id)


class TeamsGroupingInput(ResultPart):
    """The entries of exactly one source."""

    source_id: Id
    entries: tuple[TeamsEntry, ...] = Field(default=(), max_length=MAX_ENTRIES)

    @model_validator(mode="after")
    def _one_source(self) -> Self:
        if any(entry.source_id != self.source_id for entry in self.entries):
            raise A2ContractError("entries span more than one source")
        return self


class TeamsMember(ResultPart):
    """One message of a group. ``has_body`` is never invented."""

    message_id: Id
    has_body: bool
    component_count: Count


class TeamsGroup(ResultPart):
    """The members of one scope, sorted by message ID."""

    scope: TeamsScope
    members: tuple[TeamsMember, ...]


class TeamsReply(ResultPart):
    """The safety review of one reply."""

    child: TeamsMessageRef
    parent: TeamsMessageRef
    status: SafetyStatus
    reasons: tuple[ReviewReason, ...] = ()


class TeamsGrouping(ResultPart):
    """Groups and reply reviews of one source."""

    source_id: Id
    groups: tuple[TeamsGroup, ...] = ()
    replies: tuple[TeamsReply, ...] = ()

    def group_for(self, scope: TeamsScope) -> TeamsGroup | None:
        """Return the group of ``scope``, or ``None``."""
        return next((g for g in self.groups if g.scope == scope), None)


def _members(entries: list[TeamsEntry]) -> list[TeamsGroup]:
    state: dict[tuple[str, ...], tuple[TeamsMessageRef, bool, int]] = {}
    for entry in entries:
        ref = entry.ref()
        _, had_body, count = state.get(ref.sort_key(), (ref, False, 0))
        state[ref.sort_key()] = (
            ref,
            had_body or entry.kind == "message",
            max(count, entry.component_count),
        )
    scopes: dict[tuple[str, ...], TeamsScope] = {}
    by_scope: dict[tuple[str, ...], list[TeamsMember]] = {}
    for key in sorted(state):
        ref, has_body, count = state[key]
        scopes[ref.scope.sort_key()] = ref.scope
        by_scope.setdefault(ref.scope.sort_key(), []).append(
            TeamsMember(
                message_id=ref.message_id, has_body=has_body, component_count=count
            )
        )
    return [
        TeamsGroup(scope=scopes[key], members=tuple(by_scope[key]))
        for key in sorted(by_scope)
    ]


def group_teams(grouping: TeamsGroupingInput) -> TeamsGrouping:
    """
    Group Teams entries by scope and review every reply.

    The result is deterministic and independent of input order. See the
    module docstring for the rules.
    """
    entries = list(grouping.entries)
    with_body = {e.ref().sort_key() for e in entries if e.kind == "message"}
    nodes = tuple(
        entry.ref().node()
        for entry in entries
        if entry.kind == "message" or entry.ref().sort_key() not in with_body
    )
    refs: dict[NodeRef, TeamsMessageRef] = {}
    candidates: list[CandidateRelation] = []
    for entry in entries:
        if entry.reply_to is None:
            continue
        child, parent = entry.ref(), entry.reply_to
        refs[child.node()] = child
        refs[parent.node()] = parent
        candidates.append(
            CandidateRelation(
                kind="reply_to",
                child=child.node(),
                parent=parent.node(),
                basis=REPLY_BASIS,
            )
        )
    review = review_relations(
        RelationReviewInput(nodes=nodes, relations=tuple(candidates))
    )
    replies = tuple(
        TeamsReply(
            child=refs[item.relation.child],
            parent=refs[item.relation.parent],
            status=item.status,
            reasons=item.reasons,
        )
        for item in review.reviews
    )
    return TeamsGrouping(
        source_id=grouping.source_id,
        groups=tuple(_members(entries)),
        replies=replies,
    )
