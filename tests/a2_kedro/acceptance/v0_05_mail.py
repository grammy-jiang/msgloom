"""
Mail relation checks (``t0_02.json``) for the V0-05 acceptance test.

The inputs come from the ``input`` block of each gold case. Mapping
decisions (not expected values):

* ``ancestors`` are the targets of the ``ancestor`` relations of the
  message. ``missing_references`` are the target IDs of its unresolved
  relations. A chosen parent is the target of its ``reply_to`` relation.
* ``grouping_status`` is ``uncertain`` when the recovery is incomplete (a
  limitation or an unresolved relation exists) or when a relation of the
  message needs review. It is ``confirmed`` when the recovery is complete
  and every relation of the message is ``CONFIRMED``. It is ``none`` when
  the message has no relation. ``group_confirmed`` is ``status ==
  confirmed``.
* A candidate Outlook group is a hypothesis (``candidate_only``). It maps
  to ``uncertain`` and is never confirmed.
* Evidence records have no ``version_ref`` and no body. Two versions of one
  Message-ID are two equal evidence items.
"""

from __future__ import annotations

from typing import Any

from msgloom.a2_kedro.contracts.relations import NodeRef
from msgloom.a2_kedro.semantics.outlook_grouping import (
    LimitationCode as OutlookLimit,
)
from msgloom.a2_kedro.semantics.outlook_grouping import (
    OutlookGrouping,
    OutlookMessage,
    group_outlook_messages,
)
from msgloom.a2_kedro.semantics.relation_safety import (
    RecoveryLimits,
    RelationReviewInput,
    SafetyStatus,
    review_relations,
)
from msgloom.a2_kedro.semantics.relations import (
    LimitationCode,
    MessageEvidence,
    RelationRecovery,
    SourceEvidence,
    recover_relations,
)
from tests.a2_kedro.acceptance.v0_05_gold import Cmp, gold

SCOPE_A = "scope-mail-account-A"
WORKSET = "workset-1"


def ev(
    message_id: str,
    parent: str | None = None,
    refs: tuple[str, ...] = (),
    conversation: str | None = None,
) -> MessageEvidence:
    """Return the relation facts of one message."""
    return MessageEvidence(
        message_id=message_id,
        reply_parent_ids=(parent,) if parent else (),
        ancestor_ids=refs,
        conversation_id=conversation,
    )


def recover(*messages: MessageEvidence, scope_id: str = SCOPE_A) -> RelationRecovery:
    """Run P3-01 on one mailbox scope."""
    source = SourceEvidence(scope_kind="mailbox", scope_id=scope_id, messages=messages)
    return recover_relations(source)


def codes(rec: RelationRecovery) -> set[LimitationCode]:
    """Return the limitation codes of a recovery."""
    return {lim.code for lim in rec.limitations}


def limits_of(rec: RelationRecovery) -> RecoveryLimits:
    """Copy the P3-01 limits into the P3-02 input, as its docstring requires."""
    return RecoveryLimits(
        limitation_codes=tuple(lim.code.value for lim in rec.limitations),
        unresolved_count=len(rec.unresolved),
    )


def status_of(rec: RelationRecovery, child: str) -> str:
    """Return ``confirmed``, ``uncertain`` or ``none`` for one message."""
    limits = limits_of(rec)
    review = review_relations(
        RelationReviewInput.from_native(rec.relations, recovery=limits)
    )
    own = [r for r in review.reviews if r.relation.child.node_id == child]
    if limits.incomplete or any(r.status is not SafetyStatus.CONFIRMED for r in own):
        return "uncertain"
    return "confirmed" if own else "none"


def ancestors_of(rec: RelationRecovery, child: str) -> list[str]:
    """Return the ancestor targets of a message."""
    return [
        r.target.node_id
        for r in rec.relations.relations
        if r.kind == "ancestor" and r.source.node_id == child
    ]


def missing_of(rec: RelationRecovery, child: str) -> list[str]:
    """Return the sorted target IDs that a message names and cannot resolve."""
    return sorted({u.target_id for u in rec.unresolved if u.source_id == child})


def chosen_parent(rec: RelationRecovery, child: str) -> str | None:
    """Return the target of the ``reply_to`` relation of a message, if any."""
    for rel in rec.relations.relations:
        if rel.kind == "reply_to" and rel.source.node_id == child:
            return rel.target.node_id
    return None


def omsg(
    node_id: str,
    scope_id: str = SCOPE_A,
    *,
    workset: str = WORKSET,
    kind: str = "mailbox",
    **fields: Any,
) -> OutlookMessage:
    """Return one Outlook message of one scope."""
    ref = NodeRef(scope_kind=kind, scope_id=scope_id, node_id=node_id)  # type: ignore[arg-type]
    return OutlookMessage(workset_id=workset, ref=ref, **fields)


def outlook_status(res: OutlookGrouping, node_id: str, scope_id: str = SCOPE_A) -> str:
    """Return ``uncertain`` (candidate), ``none`` or ``uncertain`` for a conflict."""
    if any(node_id in g.members and g.scope_id == scope_id for g in res.groups):
        return "uncertain"
    own = [u for u in res.unresolved if u.node.node_id == node_id]
    flagged = any(
        n.node_id == node_id and n.scope_id == scope_id
        for c in res.conflicts
        for n in c.members
    )
    if (
        own
        and not flagged
        and all(u.code is OutlookLimit.NO_NATIVE_EVIDENCE for u in own)
    ):
        return "none"
    return "uncertain"


def same_outlook_group(res: OutlookGrouping, first: str, second: str) -> bool:
    """Return True when one candidate group holds both messages."""
    return any(first in g.members and second in g.members for g in res.groups)


def _reply_evidence(inp: dict[str, Any]) -> list[MessageEvidence]:
    items = [ev(inp["message_id"], inp.get("in_reply_to"), tuple(inp["references"]))]
    for rec in inp.get("present_records", []):
        items.append(ev(rec["message_id"], rec.get("in_reply_to")))
    items += [ev(mid) for mid in inp.get("present_message_ids", [])]
    first: dict[str, MessageEvidence] = {}
    for item in items:
        first.setdefault(item.message_id, item)  # the message under test wins
    return list(first.values())


@gold("T0-02-P02", "T0-02-P03", "T0-02-P04")
def reply_with_ancestors(cm: Cmp) -> None:
    inp = cm.case["input"]
    rec = recover(*_reply_evidence(inp))
    child = inp["message_id"]
    cm.eq("ancestors", ancestors_of(rec, child))
    cm.eq("missing_references", missing_of(rec, child))
    status = status_of(rec, child)
    cm.eq("grouping_status", status)
    cm.eq("group_confirmed", status == "confirmed")


@gold("T0-02-N01")
def duplicate_message_id(cm: Cmp) -> None:
    ids = [r["message_id"] for r in cm.case["input"]["records"]]
    rec = recover(*(ev(mid) for mid in ids))
    flagged = LimitationCode.DUPLICATE_MESSAGE_ID in codes(rec)
    copies = [omsg(mid, internet_message_id=mid) for mid in ids]
    flagged = flagged and bool(group_outlook_messages(copies).conflicts)
    cm.eq("merged", not flagged)
    cm.eq("message_id_treated_as_unique_key", not flagged)
    cm.eq("grouping_status_for_both", status_of(rec, ids[0]))


@gold("T0-02-N02")
def ambiguous_duplicate_parent(cm: Cmp) -> None:
    inp = cm.case["input"]
    parent = inp["in_reply_to"]
    rec = recover(ev(parent), ev(parent), ev(inp["message_id"], parent))
    status = status_of(rec, inp["message_id"])
    cm.eq("grouping_status", status)
    cm.eq("group_confirmed", status == "confirmed")
    cm.eq("chosen_parent", chosen_parent(rec, inp["message_id"]))


@gold("T0-02-N03")
def equal_subjects(cm: Cmp) -> None:
    recs = cm.case["input"]["records"]
    res = group_outlook_messages(
        [
            omsg(
                r["message_id"],
                internet_message_id=r["message_id"],
                subject=r["subject"],
            )
            for r in recs
        ]
    )
    ids = [r["message_id"] for r in recs]
    states = {outlook_status(res, mid) for mid in ids}
    cm.eq("grouping_status_each", states.pop() if len(states) == 1 else "mixed")
    cm.eq("same_group", same_outlook_group(res, *ids))


@gold("T0-02-N05")
def parent_cycle(cm: Cmp) -> None:
    recs = cm.case["input"]["records"]
    rec = recover(*(ev(r["message_id"], r["in_reply_to"]) for r in recs))
    ids = [r["message_id"] for r in recs]
    states = {status_of(rec, mid) for mid in ids}
    cm.eq("grouping_status_each", states.pop() if len(states) == 1 else "mixed")
    cm.eq("group_confirmed", "confirmed" in {status_of(rec, mid) for mid in ids})
    cm.flag("reason[cycle]", LimitationCode.CYCLE in codes(rec))


@gold("T0-02-N06")
def shared_conversation_id(cm: Cmp) -> None:
    recs = cm.case["input"]["records"]
    names = ["mail-x", "mail-y"]
    msgs = [
        omsg(name, conversation_id=r["conversation_id"])
        for name, r in zip(names, recs, strict=True)
    ]
    res = group_outlook_messages(msgs)
    states = {outlook_status(res, name) for name in names}
    cm.eq("grouping_status_each", states.pop() if len(states) == 1 else "mixed")
    cm.eq("group_confirmed", any(g.status != "candidate" for g in res.groups))
