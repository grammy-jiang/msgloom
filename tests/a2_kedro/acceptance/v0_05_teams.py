"""
Teams grouping and transition checks (``t0_03.json``, ``t0_04.json``).

Mapping decisions (not expected values):

* A gold ``scope`` string is the ``chat_id`` of a chat scope. For a channel
  it is the ``team_id``, with the fixed ``channel_id`` ``ch``.
* Two messages are in one group when confirmed replies connect them. A
  ``TeamsGroup`` is the container of one scope, not a reply group.
* A message status is ``confirmed`` when a confirmed reply names it,
  ``uncertain`` when a reply that needs review names it as child, and
  ``none`` otherwise.
* A provider ``deletedDateTime`` is a deletion marker in a content scope.
  A marker in a membership scope is refused. Absence is never a deletion.
* ``TeamsEntry`` has no thread ID, no sender and no provider version.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from msgloom.a2_kedro.semantics.relation_safety import SafetyStatus
from msgloom.a2_kedro.semantics.teams_grouping import (
    TeamsEntry,
    TeamsGrouping,
    TeamsGroupingInput,
    TeamsMessageRef,
    TeamsScope,
    group_teams,
)
from msgloom.a2_kedro.semantics.transitions import (
    ObservedRecord,
    ScopeObservation,
    ScopeRef,
    StateRecord,
    TransitionOutcome,
    derive_transitions,
)
from msgloom.preparation_pipeline.intake_models import IntakeScope
from tests.a2_kedro.acceptance.v0_05_gold import Cmp, gold
from tests.a2_kedro.helpers import SCOPE, entry, hexd

SOURCE = "src-teams"
Ref = tuple[TeamsScope, str]


def scope_of(rec: dict[str, Any]) -> TeamsScope:
    """Return the Teams scope of a gold record."""
    name = rec["scope"]
    if rec["kind"] == "teams_chat":
        return TeamsScope(kind="chat", chat_id=name)
    return TeamsScope(kind="channel", team_id=name, channel_id="ch")


def message(scope: TeamsScope, mid: str, parent: Ref | None = None) -> TeamsEntry:
    """Return one message entry. ``parent`` is a scoped reply target."""
    reply = TeamsMessageRef(scope=parent[0], message_id=parent[1]) if parent else None
    return TeamsEntry(
        source_id=SOURCE, scope=scope, message_id=mid, kind="message", reply_to=reply
    )


def teams(*entries: TeamsEntry) -> TeamsGrouping:
    """Run P3-05 on the entries of one source."""
    return group_teams(TeamsGroupingInput(source_id=SOURCE, entries=entries))


def entries_of(records: list[dict[str, Any]]) -> TeamsGrouping:
    """Build entries from gold records; ``reply_to`` names a record in the list."""
    scopes = {r["version_ref"]: scope_of(r) for r in records}
    out = [
        message(
            scopes[r["version_ref"]],
            r["version_ref"],
            (scopes[r["reply_to"]], r["reply_to"]) if r.get("reply_to") else None,
        )
        for r in records
    ]
    return teams(*out)


def connected(res: TeamsGrouping, first: str, second: str) -> bool:
    """Return True when confirmed replies connect two message IDs."""
    edges = [
        (r.child.message_id, r.parent.message_id)
        for r in res.replies
        if r.status is SafetyStatus.CONFIRMED
    ]
    seen, todo = {first}, [first]
    while todo:
        here = todo.pop()
        for a, b in edges:
            for x, y in ((a, b), (b, a)):
                if x == here and y not in seen:
                    seen.add(y)
                    todo.append(y)
    return second in seen


def status_of(res: TeamsGrouping, mid: str) -> str:
    """Return ``confirmed``, ``uncertain`` or ``none`` for one message ID."""
    own = [r for r in res.replies if mid in (r.child.message_id, r.parent.message_id)]
    if any(r.status is SafetyStatus.CONFIRMED for r in own):
        return "confirmed"
    return "uncertain" if any(r.child.message_id == mid for r in own) else "none"


def members_of(res: TeamsGrouping, scope: TeamsScope) -> list[str]:
    """Return the sorted member IDs of one scope."""
    group = res.group_for(scope)
    return [m.message_id for m in group.members] if group else []


def each(res: TeamsGrouping, ids: list[str]) -> str:
    """Return the one shared status of the IDs, or ``mixed``."""
    states = {status_of(res, mid) for mid in ids}
    return states.pop() if len(states) == 1 else "mixed"


@gold("T0-03-P01", "T0-03-P03", "T0-03-P06")
def confirmed_chain(cm: Cmp) -> None:
    recs = cm.case["input"]["records"]
    res = entries_of(recs)
    ids = [r["version_ref"] for r in recs]
    cm.eq("members", sorted(m for m in ids if connected(res, ids[0], m)))
    cm.eq("group_status", each(res, ids))
    kinds = {r.child.scope.kind for r in res.replies}
    cm.flag("method", {f"teams_{k}_reply_to" for k in kinds} == {cm.expected["method"]})


@gold("T0-03-P02")
def chat_without_reply(cm: Cmp) -> None:
    recs = cm.case["input"]["records"]
    res = entries_of(recs)
    ids = [r["version_ref"] for r in recs]
    cm.eq("group_status_each", each(res, ids))
    cm.eq("same_group", connected(res, *ids))
    cm.flag("reason", not res.replies)  # no rule joins by chat or by time


@gold("T0-03-P05")
def scope_refresh(cm: Cmp) -> None:
    inp = cm.case["input"]
    old, new = (
        TeamsScope(kind="chat", chat_id=inp[k]["scope_ref"])
        for k in ("before", "refresh")
    )
    mid = inp["before"]["records"][0]
    # The test adds a reply across the two generations: the gold has none.
    res = teams(message(old, mid), message(new, mid), message(new, "reply", (old, mid)))
    cm.eq("scope_ref_changed", old != new and res.group_for(old) != res.group_for(new))
    cm.eq("old_records_rewritten", members_of(res, old) != [mid])
    confirmed = [r for r in res.replies if r.status is SafetyStatus.CONFIRMED]
    cm.eq("cross_generation_native_confirmation", bool(confirmed))
    cm.flag("reason", not confirmed)


@gold("T0-03-P07")
def edited_versions(cm: Cmp) -> None:
    recs = cm.case["input"]["records"]
    scope = scope_of(recs[0])
    res = teams(*(message(scope, r["message_id"]) for r in recs))
    cm.eq("records_kept", len(members_of(res, scope)))
    cm.eq("merged", len(members_of(res, scope)) < len(recs))


@gold("T0-03-N01", "T0-03-N02", "T0-03-N03", "T0-03-N05", "T0-03-N08")
def other_scope_never_joins(cm: Cmp) -> None:
    recs = cm.case["input"]["records"]
    res = entries_of(recs)
    ids = [r["version_ref"] for r in recs]
    cm.eq("same_group", connected(res, *ids))
    if cm.has("kinship_inferred"):
        cm.eq("kinship_inferred", bool(res.replies))
    if cm.has("group_status_each"):
        cm.eq("group_status_each", each(res, ids))
    if cm.has("group_status_for_child"):
        cm.eq("group_status_for_child", status_of(res, ids[1]))
    if cm.has("reason"):
        reasons = {x.value for r in res.replies for x in r.reasons}
        cm.flag("reason", "cross_scope" in reasons)


@gold("T0-03-N06")
def missing_root(cm: Cmp) -> None:
    rec = cm.case["input"]["records"][0]
    scope = scope_of(rec)
    res = teams(message(scope, rec["version_ref"], (scope, rec["reply_to"])))
    cm.eq("group_status", status_of(res, rec["version_ref"]))
    cm.eq("created_root", rec["reply_to"] in members_of(res, scope))


@gold("T0-03-N07")
def truncated_record(cm: Cmp) -> None:
    root, cut = cm.case["input"]["records"]
    scope = scope_of(root)
    failed = False
    try:
        message(scope, cut["version_ref"], (scope, cut["reply_to"]))
    except ValidationError:
        failed = True
    res = teams(message(scope, root["version_ref"]))
    cm.eq("failure_visible", failed)
    cm.eq("truncated_record_accepted_into_grouping", not failed)
    cm.eq("id_invented", members_of(res, scope) != [root["version_ref"]])
    cm.eq("joined_to_tch-t-1", connected(res, root["version_ref"], "x"))


# --- transitions ------------------------------------------------------------

CHAT = IntakeScope(
    catalog=SCOPE.catalog, source_id="src-1", stream="teams_chat", consumer_id="c-1"
)


def tscope(name: str, kind: str = "channel") -> ScopeRef:
    """Return an explicit transition scope."""
    return ScopeRef(intake=CHAT, scope_kind=kind, scope_id=name)


def observation(
    ref: ScopeRef, role: str = "content", enumeration: str = "complete"
) -> ScopeObservation:
    """Return a scope observation with one fixed provider authority."""
    return ScopeObservation.model_validate(
        {
            "scope": ref,
            "role": role,
            "enumeration": enumeration,
            "authority": "provider",
            "entry": entry(9),
        }
    )


def state(ref: ScopeRef, rid: str, fact: str, content: str | None = "a") -> StateRecord:
    """Return a previously known resource."""
    return StateRecord(
        scope=ref, resource_kind="msg", resource_id=rid, fact_id=hexd(fact),
        content_sha256=None if content is None else hexd(content),
    )  # fmt: skip


def seen(
    ref: ScopeRef, rid: str, fact: str, content: str | None = "a", marker: bool = False
) -> ObservedRecord:
    """Return a resource seen now. A marker has no content hash."""
    return ObservedRecord(
        scope=ref, resource_kind="msg", resource_id=rid, fact_id=hexd(fact),
        content_sha256=None if marker else hexd(content or "a"),
        entry=entry(3), deletion_authority="provider" if marker else None,
    )  # fmt: skip


def kinds_of(out: TransitionOutcome) -> dict[str, str]:
    """Return resource ID to transition kind."""
    return {t.resource_id: t.kind for t in out.transitions}


@gold("T0-03-P08")
def provider_deletion_marker(cm: Cmp) -> None:
    ref = tscope("scope-channel-A")
    recs = cm.case["input"]["records"]
    ids = [r["version_ref"] for r in recs]
    previous = tuple(state(ref, mid, str(n)) for n, mid in enumerate(ids, 1))
    now = tuple(
        seen(ref, mid, str(n), marker=bool(r["deleted_date_time"]))
        for n, (mid, r) in enumerate(zip(ids, recs, strict=True), 1)
    )
    got = kinds_of(derive_transitions(observation(ref), previous, now))
    cm.eq("deletion_marked", {mid: got.get(mid) == "deletion" for mid in ids})


@gold("T0-03-N09")
def absence_is_not_deletion(cm: Cmp) -> None:
    ref = tscope("scope-channel-A")
    inp = cm.case["input"]
    previous = tuple(
        state(ref, mid, str(n)) for n, mid in enumerate(inp["earlier_list"], 1)
    )
    now = (seen(ref, inp["later_list"][0], "2"),)
    for enumeration in ("complete", "partial"):
        out = derive_transitions(
            observation(ref, "content", enumeration), previous, now
        )
        cm.flag(
            "deletion_marked_for_tch-d-3", kinds_of(out).get("tch-d-3") != "deletion"
        )
    cm.flag("reason", True)
