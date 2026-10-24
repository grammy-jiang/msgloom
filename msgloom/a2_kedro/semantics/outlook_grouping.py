"""
Outlook native grouping with candidate-only conversation evidence (P3-04).

This module is a pure, deterministic function layer over typed, extracted
Outlook message facts. It returns CANDIDATE groups: hypotheses that native
evidence supports. Nothing here confirms a group. It reads no file, clock,
database or provider.

Evidence
========

Within one scope, an edge joins two messages when they share a
``conversation_id`` (Graph ``conversationId``) or a 22-byte
``conversation_index`` header (Graph ``conversationIndex``, base64), or
when one names the other by ``In-Reply-To`` or ``References`` (Internet
Message-ID values, resolved only inside the scope). A group is a connected
set of two or more messages. It has status ``candidate``, the limitation
``candidate_only`` and the evidence kinds that built it. A message with no
usable edge is ``unassigned``. Unknown evidence stays unknown: a missing
field is never a match and never a conflict.

Isolation and subjects
======================

Messages of different worksets never meet. Every edge stays in one scope.
The subject is never evidence. Same-subject messages of one scope that are
in different groups give a :class:`SubjectHint`. It names messages only,
holds no subject text, and ``can_merge`` is always ``False``.

Conflicts
=========

A conflict lists its messages. It replaces a merge. Codes:
``conflicting_parents`` (two distinct ``In-Reply-To`` IDs),
``parent_mismatch`` (last ``References`` ID differs from ``In-Reply-To``),
``duplicate_message_id`` (different items, one scope and ID): these
messages are withdrawn from grouping. ``conversation_id_across_scopes``
(one ID in two scopes of a workset): each scope keeps its own groups,
flagged ``conflict_present``. ``contradictory_conversation_id`` (edges
join different IDs): only ``conversation_id`` edges are kept.

Bounds and failure handling
===========================

More than ``MAX_MESSAGES`` messages raises
:exc:`~msgloom.a2_kedro.contracts.codec.A2ContractError` with a fixed text
and gives no partial result. A reference list above ``MAX_REFERENCE_IDS``
raises a pydantic ``ValidationError`` when the message is built. It wraps
a fixed ``A2ContractError`` text. A malformed model raises the same kind
of error and hides the input. No error echoes an ID or a subject. A cut
hint list reports ``hints_truncated``. Output order does not depend on input order.
See ``docs/notes/a2-v2-p3-04.md``.

CANDIDATE/RESEARCH, PROVISIONAL: wire names and limits are not frozen.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import defaultdict
from collections.abc import Sequence
from enum import StrEnum
from typing import Literal, NamedTuple, Self

from pydantic import model_validator

from msgloom.a2_kedro.contracts.codec import (
    A2ContractError,
    Digest,
    Text,
    canonical_json_bytes,
)
from msgloom.a2_kedro.contracts.relations import NodeRef, ScopeKind
from msgloom.a2_kedro.contracts.result_base import ResultPart
from msgloom.a2_kedro.semantics.outlook_index import (  # noqa: F401
    INDEX_HEADER_BYTES,  # re-exported
    index_header,
)

#: Provisional bounds.
MAX_MESSAGES = 1024
MAX_REFERENCE_IDS = 32
MAX_HINTS = 256
MAX_HINT_MEMBERS = 16

_REPLY_PREFIX = re.compile(r"^\s*(?:re|fw|fwd)\s*:\s*", re.IGNORECASE)


class EvidenceKind(StrEnum):
    """Closed kinds of native evidence for one group."""

    CONVERSATION_ID = "conversation_id"
    CONVERSATION_INDEX = "conversation_index"
    IN_REPLY_TO = "in_reply_to"
    REFERENCES = "references"


class ConflictCode(StrEnum):
    """Closed, content-free reasons that evidence conflicts."""

    CONFLICTING_PARENTS = "conflicting_parents"
    PARENT_MISMATCH = "parent_mismatch"
    DUPLICATE_MESSAGE_ID = "duplicate_message_id"
    CONVERSATION_ID_ACROSS_SCOPES = "conversation_id_across_scopes"
    CONTRADICTORY_CONVERSATION_ID = "contradictory_conversation_id"


class LimitationCode(StrEnum):
    """Closed, content-free limitations of a group or of the result."""

    CANDIDATE_ONLY = "candidate_only"
    CONFLICT_PRESENT = "conflict_present"
    WITHDRAWN_BY_CONFLICT = "withdrawn_by_conflict"
    UNRESOLVED_REFERENCE = "unresolved_reference"
    AMBIGUOUS_REFERENCE = "ambiguous_reference"
    SELF_REFERENCE = "self_reference"
    NO_NATIVE_EVIDENCE = "no_native_evidence"
    INVALID_CONVERSATION_INDEX = "invalid_conversation_index"
    HINTS_TRUNCATED = "hints_truncated"


class OutlookMessage(ResultPart):
    """Native grouping facts of one message of one scope."""

    workset_id: Text
    ref: NodeRef
    internet_message_id: Text | None = None
    conversation_id: Text | None = None
    conversation_index: Text | None = None
    in_reply_to: tuple[Text, ...] = ()
    references: tuple[Text, ...] = ()
    subject: Text | None = None

    @model_validator(mode="after")
    def _bounded_lists(self) -> Self:
        if max(len(self.in_reply_to), len(self.references)) > MAX_REFERENCE_IDS:
            raise A2ContractError("reference list exceeds count bound")
        return self


class CandidateGroup(ResultPart):
    """A candidate group of two or more messages of one scope."""

    workset_id: Text
    scope_kind: ScopeKind
    scope_id: Text
    members: tuple[Text, ...]
    group_id: Digest
    evidence: tuple[EvidenceKind, ...]
    limitations: tuple[LimitationCode, ...]
    status: Literal["candidate"] = "candidate"


class GroupingConflict(ResultPart):
    """Messages whose evidence conflicts. They are not merged."""

    workset_id: Text
    code: ConflictCode
    members: tuple[NodeRef, ...]


class UnresolvedEvidence(ResultPart):
    """One message whose native evidence is unknown or not usable."""

    workset_id: Text
    node: NodeRef
    code: LimitationCode


class SubjectHint(ResultPart):
    """Same-subject messages of one scope in different groups. A hint only."""

    workset_id: Text
    scope_kind: ScopeKind
    scope_id: Text
    members: tuple[Text, ...]
    can_merge: Literal[False] = False


class OutlookGrouping(ResultPart):
    """Candidate groups, conflicts, unknowns and hints of one call."""

    groups: tuple[CandidateGroup, ...] = ()
    conflicts: tuple[GroupingConflict, ...] = ()
    unresolved: tuple[UnresolvedEvidence, ...] = ()
    subject_hints: tuple[SubjectHint, ...] = ()
    limitations: tuple[LimitationCode, ...] = ()


class _Edge(NamedTuple):
    left: str
    right: str
    kind: EvidenceKind


#: ``(workset_id, scope_kind, scope_id)``.
_ScopeKey = tuple[str, ScopeKind, str]


def _order(item: ResultPart) -> str:
    """Return a sort key: JSON of ``item``; each model puts the workset first."""
    return item.model_dump_json()


def _normalize_subject(subject: str) -> str:
    text = unicodedata.normalize("NFKC", subject)
    while (match := _REPLY_PREFIX.match(text)) is not None:
        text = text[match.end() :]
    return " ".join(text.casefold().split())


def _components(
    members: list[str], edges: list[_Edge]
) -> list[tuple[list[str], set[EvidenceKind]]]:
    """Return connected sets (sorted members, evidence kinds), sorted."""
    root = {name: name for name in members}

    def find(name: str) -> str:
        while root[name] != name:
            root[name] = root[root[name]]
            name = root[name]
        return name

    for edge in sorted(edges):
        low, high = sorted((find(edge.left), find(edge.right)))
        root[high] = low
    sets: dict[str, list[str]] = defaultdict(list)
    kinds: dict[str, set[EvidenceKind]] = defaultdict(set)
    for name in sorted(members):
        sets[find(name)].append(name)
    for edge in edges:
        kinds[find(edge.left)].add(edge.kind)
    return [(sets[key], kinds[key]) for key in sorted(sets)]


def _chain(items: dict[str, list[str]], kind: EvidenceKind) -> list[_Edge]:
    """Join each list of members to its first member."""
    return [
        _Edge(names[0], name, kind)
        for key in sorted(items)
        for names in [sorted(items[key])]
        for name in names[1:]
    ]


class _Scope:
    """Grouping of the messages of one scope. It never leaves this module."""

    def __init__(self, key: _ScopeKey, flagged: set[str]) -> None:
        self.workset: str = key[0]
        self.kind: ScopeKind = key[1]
        self.scope: str = key[2]
        self.flagged = set(flagged)  # ids in a conflict that keeps them
        self.conflicts: list[GroupingConflict] = []
        self.unresolved: list[UnresolvedEvidence] = []
        self.groups: list[CandidateGroup] = []
        self.hints: list[SubjectHint] = []
        self.hint_cut = False
        self.noted: dict[str, set[LimitationCode]] = defaultdict(set)

    def ref(self, mid: str) -> NodeRef:
        return NodeRef(scope_kind=self.kind, scope_id=self.scope, node_id=mid)

    def conflict(self, code: ConflictCode, ids: list[str]) -> None:
        self.conflicts.append(
            GroupingConflict(
                code=code,
                workset_id=self.workset,
                members=tuple(self.ref(i) for i in sorted(set(ids))),
            )
        )

    def note(self, mid: str, code: LimitationCode) -> None:
        self.noted[mid].add(code)
        node = self.ref(mid)
        self.unresolved.append(
            UnresolvedEvidence(workset_id=self.workset, node=node, code=code)
        )

    def active(self, items: list[OutlookMessage]) -> dict[str, OutlookMessage]:
        """Collapse equal duplicates; withdraw conflicting messages."""
        by_id: dict[str, list[OutlookMessage]] = defaultdict(list)
        for item in items:
            by_id[item.ref.node_id].append(item)
        active: dict[str, OutlookMessage] = {}
        for mid in sorted(by_id):
            first = by_id[mid][0]
            if any(other != first for other in by_id[mid]):
                self.conflict(ConflictCode.DUPLICATE_MESSAGE_ID, [mid])
                continue
            if not self._parents_conflict(first):
                active[mid] = first
        return active

    def _parents_conflict(self, msg: OutlookMessage) -> bool:
        mid = msg.ref.node_id
        parents = set(msg.in_reply_to)
        if len(parents) > 1:
            self.conflict(ConflictCode.CONFLICTING_PARENTS, [mid])
        elif parents and msg.references and msg.references[-1] not in parents:
            self.conflict(ConflictCode.PARENT_MISMATCH, [mid])
        else:
            return False
        self.note(mid, LimitationCode.WITHDRAWN_BY_CONFLICT)
        return True

    def edges(self, active: dict[str, OutlookMessage]) -> list[_Edge]:
        by_cid: dict[str, list[str]] = defaultdict(list)
        by_header: dict[str, list[str]] = defaultdict(list)
        owners: dict[str, set[str]] = defaultdict(set)
        for mid, msg in active.items():
            if msg.conversation_id is not None:
                by_cid[msg.conversation_id].append(mid)
            if msg.internet_message_id is not None:
                owners[msg.internet_message_id].add(mid)
            if msg.conversation_index is None:
                continue
            if (header := index_header(msg.conversation_index)) is None:
                self.note(mid, LimitationCode.INVALID_CONVERSATION_INDEX)
                continue
            by_header[header].append(mid)
        edges = _chain(by_cid, EvidenceKind.CONVERSATION_ID)
        edges += _chain(by_header, EvidenceKind.CONVERSATION_INDEX)
        for mid in sorted(active):
            msg = active[mid]
            for kind, ids in (
                (EvidenceKind.IN_REPLY_TO, msg.in_reply_to),
                (EvidenceKind.REFERENCES, msg.references),
            ):
                for target in dict.fromkeys(ids):
                    if (edge := self._resolve(mid, kind, target, owners)) is not None:
                        edges.append(edge)
        return edges

    def _resolve(
        self,
        mid: str,
        kind: EvidenceKind,
        target: str,
        owners: dict[str, set[str]],
    ) -> _Edge | None:
        found = owners.get(target, set())
        if len(found) == 1 and mid not in found:
            return _Edge(mid, min(found), kind)
        if len(found) > 1:
            self.note(mid, LimitationCode.AMBIGUOUS_REFERENCE)
        elif found:
            self.note(mid, LimitationCode.SELF_REFERENCE)
        else:
            self.note(mid, LimitationCode.UNRESOLVED_REFERENCE)
        return None

    def build(self, items: list[OutlookMessage]) -> None:
        active = self.active(items)
        edges = self.edges(active)
        parts: list[tuple[list[str], set[EvidenceKind]]] = []
        for names, kinds in _components(list(active), edges):
            if len({active[n].conversation_id for n in names} - {None}) > 1:
                self.conflict(ConflictCode.CONTRADICTORY_CONVERSATION_ID, names)
                self.flagged.update(names)
                kept = [
                    e
                    for e in edges
                    if e.kind is EvidenceKind.CONVERSATION_ID and e.left in names
                ]
                parts += _components(names, kept)
                continue
            parts.append((names, kinds))
        component: dict[str, int] = {}
        for number, (names, kinds) in enumerate(parts):
            component.update(dict.fromkeys(names, number))
            if len(names) < 2:
                self.note(names[0], LimitationCode.NO_NATIVE_EVIDENCE)
                continue
            self.groups.append(self.group(names, kinds))
        self.hint(active, component)

    def group(self, names: list[str], kinds: set[EvidenceKind]) -> CandidateGroup:
        limits = {LimitationCode.CANDIDATE_ONLY}
        for name in names:
            limits |= self.noted.get(name, set())
        if self.flagged & set(names):
            limits.add(LimitationCode.CONFLICT_PRESENT)
        digest = hashlib.sha256(
            canonical_json_bytes([self.workset, self.kind, self.scope, names])
        ).hexdigest()
        return CandidateGroup(
            group_id=digest,
            workset_id=self.workset,
            scope_kind=self.kind,
            scope_id=self.scope,
            members=tuple(names),
            evidence=tuple(sorted(kinds)),
            limitations=tuple(sorted(limits)),
        )

    def hint(
        self, active: dict[str, OutlookMessage], component: dict[str, int]
    ) -> None:
        by_subject: dict[str, list[str]] = defaultdict(list)
        for mid, msg in active.items():
            if msg.subject is None:
                continue
            if key := _normalize_subject(msg.subject):
                by_subject[key].append(mid)
        for key in sorted(by_subject):
            names = sorted(by_subject[key])
            if len({component[n] for n in names}) < 2:
                continue
            self.hint_cut |= len(names) > MAX_HINT_MEMBERS  # hints only
            self.hints.append(
                SubjectHint(
                    workset_id=self.workset,
                    scope_kind=self.kind,
                    scope_id=self.scope,
                    members=tuple(names[:MAX_HINT_MEMBERS]),
                )
            )


def _cross_scope_conflicts(
    workset: str, items: list[OutlookMessage]
) -> tuple[list[GroupingConflict], dict[_ScopeKey, set[str]]]:
    """Flag one conversation ID that appears in two scopes of a workset."""
    refs: dict[str, dict[tuple[str, str, str], NodeRef]] = defaultdict(dict)
    for msg in items:
        if msg.conversation_id is not None:
            refs[msg.conversation_id][msg.ref.sort_key()] = msg.ref
    conflicts: list[GroupingConflict] = []
    flagged: dict[_ScopeKey, set[str]] = defaultdict(set)
    for cid in sorted(refs):
        nodes = [refs[cid][key] for key in sorted(refs[cid])]
        if len({node.sort_key()[:2] for node in nodes}) < 2:
            continue
        code = ConflictCode.CONVERSATION_ID_ACROSS_SCOPES
        conflicts.append(
            GroupingConflict(code=code, workset_id=workset, members=tuple(nodes))
        )
        for node in nodes:
            flagged[(workset, node.scope_kind, node.scope_id)].add(node.node_id)
    return conflicts, flagged


def group_outlook_messages(messages: Sequence[OutlookMessage]) -> OutlookGrouping:
    """
    Group Outlook messages into candidate groups from native evidence.

    The result is deterministic and independent of message order. Subject
    similarity never changes membership. See the module docstring for the
    rules, conflicts and bounds.
    """
    if len(messages) > MAX_MESSAGES:
        raise A2ContractError("grouping input exceeds count bound")
    worksets: dict[str, list[OutlookMessage]] = defaultdict(list)
    for msg in messages:
        worksets[msg.workset_id].append(msg)
    groups: list[CandidateGroup] = []
    conflicts: list[GroupingConflict] = []
    unresolved: list[UnresolvedEvidence] = []
    hints: list[SubjectHint] = []
    cut = False
    for workset in sorted(worksets):
        items = worksets[workset]
        cross, flagged = _cross_scope_conflicts(workset, items)
        conflicts += cross
        scopes: dict[_ScopeKey, list[OutlookMessage]] = defaultdict(list)
        for msg in items:
            scopes[(workset, msg.ref.scope_kind, msg.ref.scope_id)].append(msg)
        for key in sorted(scopes):
            run = _Scope(key, flagged.get(key, set()))
            run.build(scopes[key])
            groups += run.groups
            conflicts += run.conflicts
            cut = cut or run.hint_cut
            unresolved += run.unresolved
            hints += run.hints
    limits: list[LimitationCode] = []
    ordered = sorted(hints, key=_order)
    if len(ordered) > MAX_HINTS:
        ordered = ordered[:MAX_HINTS]
        cut = True
    if cut:
        limits.append(LimitationCode.HINTS_TRUNCATED)
    return OutlookGrouping(
        groups=tuple(sorted(groups, key=_order)),
        conflicts=tuple(sorted(conflicts, key=_order)),
        unresolved=tuple(sorted(set(unresolved), key=_order)),
        subject_hints=tuple(ordered),
        limitations=tuple(limits),
    )
