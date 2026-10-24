"""
``prepared@2``, ``filter_result@2`` and ``group_result@2`` records.

Bases, header rules and reference checks live in
:mod:`~msgloom.a2_kedro.contracts.result_base`. The manifest lives in
:mod:`~msgloom.a2_kedro.contracts.result_manifest` and is re-exported here.
:func:`decode_result` reads the header first and refuses a historical
``@1`` pair, so ``prepared@1`` never decodes as ``prepared@2`` and the
reverse.

No record holds body text, an address or a subject. Text rules forbid
control characters, so content is kept as zone spans and SHA-256 digests.
A participant is a digest, never an address.

* :class:`Prepared` binds the frozen root and the accepted parsed,
  normalized, zones and relations refs. Its ``parts`` list covers every
  parsed part (body, alternate, attachment, embedded). Its ``blocks`` list
  covers every zone. Parts are sorted by ``part_id``. A block never names
  a body part whose status is ``missing``. A body, an attachment, a time
  or a participant list that is missing or not usable needs a named
  limitation. A record cannot be COMPLETE and carry a limitation.
* :class:`FilterResult` lists every rule that ran, not the best match. The
  ``matched`` list, the verdict and the reasons must equal what the
  evaluations imply, so a record with only the best match fails.
* :class:`GroupResult` has one exact scope. Every member must sit in that
  scope. Members join only through source-native evidence (thread, reply
  or ancestor). Equal subjects never join members.

Failure handling: a violation raises :exc:`A2ContractError` or a pydantic
``ValueError``. Messages are fixed text and never carry values.

CANDIDATE/RESEARCH, PROVISIONAL: names and limits are not frozen. See
``docs/notes/a2-v2-contract-c0-07.md``.
"""

from __future__ import annotations

from typing import Annotated, Any, ClassVar, Literal

from pydantic import Field, model_validator

from msgloom.a2_kedro.contracts.codec import (
    A2ContractError,
    Digest,
    Text,
    decode_canonical_json,
)
from msgloom.a2_kedro.contracts.extract import ComponentStatus
from msgloom.a2_kedro.contracts.identity import lineage_digest
from msgloom.a2_kedro.contracts.parse import ParsedParts, PartRole
from msgloom.a2_kedro.contracts.relations import NodeRef
from msgloom.a2_kedro.contracts.result_base import (
    Accepted,
    Effect,
    NormalizedRef,
    ParsedRef,
    PreparedRef,
    RelationsRef,
    ResultModel,
    ResultPart,
    ZonesRef,
    check_limitations,
    header_for,
    sorted_unique,
)
from msgloom.a2_kedro.contracts.result_manifest import (
    ManifestEntry,
    ResultManifest,
)
from msgloom.a2_kedro.contracts.schema_ids import HISTORICAL_READ_ONLY, STAGE_SCHEMAS
from msgloom.a2_kedro.contracts.source import FrozenRoot
from msgloom.a2_kedro.contracts.zones import ContentZones, Span, ZoneKind
from msgloom.contracts import Limitation, ResultRef

__all__ = [
    "FilterResult",
    "GroupResult",
    "ManifestEntry",
    "Prepared",
    "ResultManifest",
    "decode_result",
    "header_for",
]

#: Provisional bounds. They are wire decisions, not production limits.
MAX_PARTS = 256
MAX_BLOCKS = 1024
MAX_PARTICIPANTS = 256
MAX_RULES = 1024
MAX_MEMBERS = 1024
MAX_EVIDENCE = 4096

Verdict = Literal["include", "exclude", "conflict", "unknown", "no_match"]

# --- prepared@2 -----------------------------------------------------------


class PartRecord(ResultPart):
    """One parsed part. Nothing may drop out of this list."""

    part_id: Text
    role: PartRole
    status: ComponentStatus
    sha256: Digest | None = None

    @model_validator(mode="after")
    def _proof(self) -> PartRecord:
        if self.status in ("present", "partial") and self.sha256 is None:
            raise A2ContractError("usable part needs a digest")
        return self


class ContentBlock(ResultPart):
    """One zone of a body part, by span and digest. No text."""

    part_id: Text
    zone_id: Text
    kind: ZoneKind
    original: Span
    text_sha256: Digest


class Participant(ResultPart):
    """A participant by role and address digest. Never an address."""

    role: Literal["sender", "from", "to", "cc", "bcc", "reply_to"]
    identity_sha256: Digest


class Prepared(ResultModel):
    """``prepared@2``: one occurrence, fully bound to its lineage."""

    KIND: ClassVar[str] = "prepared"
    root: FrozenRoot
    status: Accepted
    limitations: tuple[Limitation, ...] = ()
    parsed: ParsedRef
    normalized: NormalizedRef
    zones: ZonesRef
    relations: RelationsRef
    lineage_sha256: Digest
    parts: tuple[PartRecord, ...]
    blocks: tuple[ContentBlock, ...] = ()
    sent_at: Annotated[int, Field(ge=0, le=2**40)] | None = None
    participants: tuple[Participant, ...] = ()
    rule_version: Text

    def lineage(self) -> tuple[ResultRef, ...]:
        """Return the ordered accepted upstream refs."""
        return (self.parsed, self.normalized, self.zones, self.relations)

    def _required_limitations(self) -> set[str]:
        need = {f"{p.role}_{p.status}" for p in self.parts if p.status != "present"}
        need |= {"body_absent"} if not self.blocks else set()
        need |= {"time_unknown"} if self.sent_at is None else set()
        need |= {"participants_unknown"} if not self.participants else set()
        return need

    @model_validator(mode="after")
    def _closed(self) -> Prepared:
        if not 1 <= len(self.parts) <= MAX_PARTS:
            raise A2ContractError("part count is out of bounds")
        if len(self.blocks) > MAX_BLOCKS or len(self.participants) > MAX_PARTICIPANTS:
            raise A2ContractError("record exceeds count bound")
        if len(set(self.lineage())) != 4:
            raise A2ContractError("lineage refs must be distinct")
        if self.lineage_sha256 != lineage_digest(self.lineage()):
            raise A2ContractError("lineage digest differs from refs")
        sorted_unique([part.part_id for part in self.parts], "part")
        sorted_unique(
            [(b.part_id, b.original.start, b.zone_id) for b in self.blocks], "block"
        )
        if len({(b.part_id, b.zone_id) for b in self.blocks}) != len(self.blocks):
            raise A2ContractError("duplicate block")
        bodies = {p.part_id for p in self.parts if p.role == "body"}
        if any(block.part_id not in bodies for block in self.blocks):
            raise A2ContractError("block names no body part")
        absent = {p.part_id for p in self.parts if p.status == "missing"}
        if any(block.part_id in absent for block in self.blocks):
            raise A2ContractError("block names a missing body part")
        sorted_unique([(p.role, p.identity_sha256) for p in self.participants], "p")
        check_limitations(self.status, self.limitations, self._required_limitations())
        return self

    def validate_against(self, parsed: ParsedParts, zones: ContentZones) -> None:
        """
        Prove that no parsed part and no zone was dropped.

        ``parts`` must list exactly the parts of ``parsed`` with the same
        roles. ``blocks`` must list exactly the zones of ``zones`` on its
        part. Raise :exc:`A2ContractError` otherwise.
        """
        wanted = {(p.part_id, p.role) for p in parsed.parts}
        if {(p.part_id, p.role) for p in self.parts} != wanted:
            raise A2ContractError("parts differ from the parsed parts")
        want_blocks = {
            (zones.part_id, z.zone_id, z.kind, z.original) for z in zones.zones
        }
        have = {(b.part_id, b.zone_id, b.kind, b.original) for b in self.blocks}
        if have != want_blocks or len(self.blocks) != len(want_blocks):
            raise A2ContractError("blocks differ from the zones")


# --- filter_result@2 ------------------------------------------------------


class RuleEvaluation(ResultPart):
    """The outcome of one rule. Every rule that ran has one."""

    rule_id: Text
    rule_version: Text
    outcome: Literal["matched", "not_matched", "unknown"]
    effect: Effect | None = None

    @model_validator(mode="after")
    def _effect(self) -> RuleEvaluation:
        if (self.outcome == "matched") != (self.effect is not None):
            raise A2ContractError("only a matched rule has an effect")
        return self


class Reason(ResultPart):
    """Why the verdict is not a plain include: rule IDs, all of them."""

    code: Literal["conflict", "unknown_rule", "excluded"]
    rule_ids: tuple[Text, ...]


def _expected(evals: tuple[RuleEvaluation, ...]) -> tuple[Verdict, list[Reason]]:
    """Return the only verdict and reasons these evaluations allow."""

    def ids(outcome: str, effect: str | None) -> tuple[str, ...]:
        return tuple(
            e.rule_id for e in evals if (e.outcome, e.effect) == (outcome, effect)
        )

    inc, exc = ids("matched", "include"), ids("matched", "exclude")
    unk = ids("unknown", None)
    reasons: list[Reason] = []
    if inc and exc:
        reasons.append(Reason(code="conflict", rule_ids=(*inc, *exc)))
    if exc:
        reasons.append(Reason(code="excluded", rule_ids=exc))
    if unk:
        reasons.append(Reason(code="unknown_rule", rule_ids=unk))
    if inc and exc:
        return "conflict", reasons
    if exc:
        return "exclude", reasons
    if unk:
        return "unknown", reasons
    return ("include" if inc else "no_match"), reasons


class FilterResult(ResultModel):
    """``filter_result@2``: all rules, all matches, policy and version."""

    KIND: ClassVar[str] = "filter_result"
    prepared: PreparedRef
    policy_id: Text
    policy_version: Text
    evaluations: tuple[RuleEvaluation, ...]
    matched: tuple[Text, ...]
    verdict: Verdict
    reasons: tuple[Reason, ...] = ()
    status: Accepted
    limitations: tuple[Limitation, ...] = ()

    @model_validator(mode="after")
    def _complete(self) -> FilterResult:
        if not 1 <= len(self.evaluations) <= MAX_RULES:
            raise A2ContractError("rule count is out of bounds")
        sorted_unique([e.rule_id for e in self.evaluations], "rule")
        every_match = tuple(e.rule_id for e in self.evaluations if e.effect)
        if self.matched != every_match:
            raise A2ContractError("matched list is not every matched rule")
        verdict, reasons = _expected(self.evaluations)
        if self.verdict != verdict or list(self.reasons) != reasons:
            raise A2ContractError("verdict or reasons differ from evaluations")
        check_limitations(self.status, self.limitations)
        return self


# --- group_result@2 -------------------------------------------------------


class Member(ResultPart):
    """One prepared message at one node of the group scope."""

    node: NodeRef
    prepared: PreparedRef

    def sort_key(self) -> tuple[str, str, str]:
        """Return the canonical ordering key."""
        return self.node.sort_key()


class Evidence(ResultPart):
    """Source-native proof that two members belong together."""

    kind: Literal["native_thread", "reply_to", "ancestor"]
    source: NodeRef
    target: NodeRef
    basis: Text

    def sort_key(self) -> tuple[Any, ...]:
        """Return the canonical ordering key."""
        return (self.kind, self.source.sort_key(), self.target.sort_key())


class UnknownRelation(ResultPart):
    """A relation the group could not resolve; kept, never guessed."""

    kind: Literal["missing_parent", "cross_scope", "cycle", "unresolved"]
    node: NodeRef

    def sort_key(self) -> tuple[Any, ...]:
        """Return the canonical ordering key."""
        return (self.kind, self.node.sort_key())


NodeKey = tuple[str, str, str]


def _connected(nodes: set[NodeKey], edges: list[tuple[NodeKey, NodeKey]]) -> bool:
    parent = {node: node for node in nodes}

    def find(node: NodeKey) -> NodeKey:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for a, b in edges:
        parent[find(a)] = find(b)
    return len({find(node) for node in nodes}) <= 1


class GroupResult(ResultModel):
    """``group_result@2``: one exact scope, native evidence, no subject."""

    KIND: ClassVar[str] = "group_result"
    scope_kind: Literal["mailbox", "thread", "channel"]
    scope_id: Text
    rule_version: Text
    relations: RelationsRef
    members: tuple[Member, ...]
    evidence: tuple[Evidence, ...] = ()
    unknown: tuple[UnknownRelation, ...] = ()
    status: Accepted
    limitations: tuple[Limitation, ...] = ()

    @model_validator(mode="after")
    def _one_scope(self) -> GroupResult:
        if not 1 <= len(self.members) <= MAX_MEMBERS:
            raise A2ContractError("member count is out of bounds")
        if len(self.evidence) > MAX_EVIDENCE or len(self.unknown) > MAX_MEMBERS:
            raise A2ContractError("record exceeds count bound")
        scope = (self.scope_kind, self.scope_id)
        if any(m.node.sort_key()[:2] != scope for m in self.members):
            raise A2ContractError("member is outside the group scope")
        sorted_unique([m.sort_key() for m in self.members], "member")
        if len({m.prepared for m in self.members}) != len(self.members):
            raise A2ContractError("duplicate member result")
        nodes = {m.node.sort_key() for m in self.members}
        sorted_unique([e.sort_key() for e in self.evidence], "evidence")
        ends = [(e.source.sort_key(), e.target.sort_key()) for e in self.evidence]
        if any(a not in nodes or b not in nodes for a, b in ends):
            raise A2ContractError("evidence names a non-member")
        if any(a == b for a, b in ends):
            raise A2ContractError("evidence joins a node to itself")
        if not _connected(nodes, ends):
            raise A2ContractError("members lack native evidence to join")
        sorted_unique([u.sort_key() for u in self.unknown], "unknown relation")
        if any(u.node.sort_key() not in nodes for u in self.unknown):
            raise A2ContractError("unknown relation names a non-member")
        need = {"unknown_relations"} if self.unknown else set()
        check_limitations(self.status, self.limitations, need)
        return self


_MODELS: dict[tuple[str, str], type[ResultModel]] = {
    (cls.KIND, STAGE_SCHEMAS[cls.KIND]): cls
    for cls in (Prepared, FilterResult, GroupResult, ResultManifest)
}


def decode_result(
    data: bytes,
) -> Prepared | FilterResult | GroupResult | ResultManifest:
    """
    Decode a result by its header. Refuse a historical or unknown pair.

    The header is read first from canonical JSON. A ``@1`` pair for
    ``prepared``, ``filter_result`` or ``group_result`` is read-only
    history and belongs to the v1 reader, not to this codec.
    """
    value = decode_canonical_json(data)
    header = value.get("header") if isinstance(value, dict) else None
    if not isinstance(header, dict):
        raise A2ContractError("payload has no header")
    kind, version = header.get("kind"), header.get("version")
    if not isinstance(kind, str) or not isinstance(version, str):
        raise A2ContractError("header pair is not text")
    if (kind, version) in HISTORICAL_READ_ONLY:
        raise A2ContractError("historical result needs the v1 reader")
    model = _MODELS.get((kind, version))
    if model is None:
        raise A2ContractError("header pair is not a v2 result")
    return model.decode(data)  # type: ignore[return-value]
