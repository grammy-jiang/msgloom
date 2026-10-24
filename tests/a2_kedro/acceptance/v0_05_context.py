"""
Source-native context checks (``t0_04.json``) for the V0-05 acceptance test.

Mapping decisions (not expected values):

* A Calendar, To Do, OneDrive or Contacts record goes through P3-06
  ``publish_context``. The result is a ``ContextPublication``. It has no
  group status and no group size, so those gold keys are not mapped.
* A communication group member is a record whose source type
  ``context_type_of`` refuses as ``not_context_source``.
* A context item is "in no group" when no candidate Outlook group and no
  confirmed Teams reply holds its source identity. Context records enter
  neither grouping API, so the communication item is fed alone.
* A gold flag is "preserved" when a field of ``ContextPublication`` is
  named for it. P3-06 publishes counts and digests only.
* A To Do removal and a Calendar delta marker are transitions of their own
  scope (P3-08). The scope kind and ID tell them from a mail scope.
"""

from __future__ import annotations

from dataclasses import fields
from datetime import UTC, datetime
from typing import Any

from msgloom.a2_kedro.semantics.context_types import (
    ContextGrant,
    ContextPublication,
    ContextRefusal,
    FrozenSelection,
    PublicationTarget,
    context_type_of,
    publish_context,
)
from msgloom.a2_kedro.semantics.teams_grouping import TeamsScope
from msgloom.a2_kedro.semantics.transitions import (
    TransitionSemanticsError,
    derive_transitions,
)
from msgloom.contracts import ResultRef, VersionRef
from msgloom.preparation.records import (
    NativeRelationship,
    PreparedParty,
    PreparedRecipient,
    PreparedSourceType,
    RecipientRole,
)
from msgloom.preparation_pipeline.intake_models import IntakeScope
from msgloom.sources import CollectedRecord, ContentKind
from msgloom.sources._snapshot import capture_selection
from msgloom.sources.handoff_models import A1CatalogIdentity
from tests.a2_kedro.acceptance.v0_05_gold import Cmp, gold
from tests.a2_kedro.acceptance.v0_05_mail import group_outlook_messages, omsg
from tests.a2_kedro.acceptance.v0_05_teams import (
    connected,
    message,
    observation,
    seen,
    state,
    teams,
    tscope,
)

WHEN = datetime(2026, 1, 5, 9, 0, 0, tzinfo=UTC)
WORKSET = ResultRef("workset-1", "preparation_intake_workset", "1")
TYPES: dict[str, tuple[PreparedSourceType, str]] = {
    "todo": (PreparedSourceType.TODO, "todo"),
    "onedrive": (PreparedSourceType.ONEDRIVE, "onedrive"),
    "contacts": (PreparedSourceType.CONTACT, "contacts"),
    "outlook_calendar": (PreparedSourceType.OUTLOOK_CALENDAR, "outlook_calendar"),
}


def intake(stream: str) -> IntakeScope:
    """Return the Intake scope of one stream."""
    catalog = A1CatalogIdentity(catalog_identity="cat-1", schema_version=1)
    return IntakeScope(
        catalog=catalog,
        source_id="src-1",
        stream=stream,  # type: ignore[arg-type]
        consumer_id="consumer-1",
    )


def record(
    source_type: PreparedSourceType, identity: str, **changes: Any
) -> CollectedRecord:
    """Return one synthetic collected record."""
    scope = VersionRef("source_scope", "src-1", "1")
    values: dict[str, Any] = {
        "source": VersionRef(source_type.value, identity, "observation-1"),
        "source_scope": scope,
        "source_type": source_type,
        "semantic_identity": identity,
        "observed_at": WHEN,
        "source_time": WHEN,
        "subject": None,
        "sender": None,
        "author": None,
        "recipients": (),
        "source_content_kind": ContentKind.JSON,
        "source_bytes": None,
        "body": None,
        "alternate_bodies": (),
        "attachments": (),
        "relationships": (NativeRelationship(kind="source_scope", target=scope),),
        "metadata": (),
        "source_locations": (),
        "limitations": (),
    }
    values.update(changes)
    return CollectedRecord(**values)


def publish(stream_key: str, identity: str, **changes: Any) -> ContextPublication:
    """Publish one context record under a grant for its own scope and workset."""
    source_type, stream = TYPES[stream_key]
    selection = capture_selection(record(source_type, identity, **changes))
    scope = intake(stream)
    return publish_context(
        FrozenSelection(selection, scope, WORKSET),
        ContextGrant(scope, WORKSET),
        PublicationTarget(scope, WORKSET),
    )


def refusal_code(source_type: PreparedSourceType) -> str:
    """Return the refusal code of ``context_type_of``, or ``accepted``."""
    try:
        context_type_of(source_type)
    except ContextRefusal as error:
        return error.code
    return "accepted"


def none_status(pub: ContextPublication, mail: Any) -> bool:
    """Return True when no candidate group holds the identity of ``pub``."""
    return not any(pub.source.identity in g.members for g in mail.groups)


def field_names(pub: ContextPublication) -> set[str]:
    """Return the field names of a publication."""
    return {f.name for f in fields(pub)}


def mail_alone(node_id: str) -> Any:
    """Group one mail message alone. Its subject equals nothing else."""
    return group_outlook_messages([omsg(node_id, subject="Reminder: Buy stamps")])


@gold("T0-04-P01", "T0-04-P02", "T0-04-P03", "T0-04-P04", "T0-04-P06", "T0-04-P07")
@gold("T0-04-P08")
def contextual_item(cm: Cmp) -> None:
    inp = cm.case["input"]
    pub = publish(inp["stream"], inp["version_ref"])
    names = field_names(pub)
    if cm.has("members"):
        cm.eq("members", [pub.source.identity])
    if cm.has("evidence_claimed"):
        cm.eq("evidence_claimed", sorted(names & {"evidence", "relations"}))
    if cm.has("communication_group_member"):
        refused = refusal_code(TYPES[inp["stream"]][0]) == "not_context_source"
        cm.eq("communication_group_member", refused)
    if cm.has("series_master_id_is_grouping_evidence"):
        cm.eq(
            "series_master_id_is_grouping_evidence",
            bool(names & {"members", "group_id"}),
        )
    for key, field in (
        ("is_cancelled_preserved", "is_cancelled"),
        ("is_all_day_preserved", "is_all_day"),
        ("series_master_id_preserved", "series_master_id"),
    ):
        if cm.has(key):
            cm.eq(key, field in names)


@gold("T0-04-P05")
def partitioned(cm: Cmp) -> None:
    refs = cm.case["input"]["version_refs"]
    keys = {
        "todo-1": "todo",
        "od-1": "onedrive",
        "ct-1": "contacts",
        "cal-1": "outlook_calendar",
    }
    pubs = [publish(keys[ref], ref) for ref in refs]
    cm.eq("groups", [[p.source.identity] for p in pubs])
    cm.eq("cross_source_join", len({p.context_type for p in pubs}) < len(pubs))


@gold("T0-04-N01", "T0-04-N02", "T0-04-N03", "T0-04-N07")
def not_joined_to_communication(cm: Cmp) -> None:
    recs = cm.case["input"]["records"]
    context = [r for r in recs if r["stream"] != "outlook_mail"]
    extra: dict[str, Any] = {}
    pubs = []
    for rec in context:
        if "relationship" in rec:
            target = VersionRef("outlook_email", rec["relationship"]["target"], "1")
            extra["relationships"] = (
                NativeRelationship(
                    kind="source_scope", target=VersionRef("source_scope", "src-1", "1")
                ),
                NativeRelationship(kind=rec["relationship"]["kind"], target=target),
            )
        if "attendees" in rec:
            who = PreparedParty(identity=rec["attendees"][0])
            extra["recipients"] = (PreparedRecipient(party=who, role=RecipientRole.TO),)
        pubs.append(publish(rec["stream"], rec["version_ref"], **extra))
    mail = [r for r in recs if r["stream"] == "outlook_mail"]
    res = group_outlook_messages(
        [omsg(m["version_ref"], subject=m.get("text")) for m in mail]
    )
    joined = bool(res.groups) or len({p.identity_sha256 for p in pubs}) < len(pubs)
    cm.eq("same_group", joined)
    for key, pub in (("group_status_todo", pubs[0]), ("group_status_od", pubs[0])):
        if cm.has(key):
            cm.eq(key, "none" if none_status(pub, res) else "candidate")
    if cm.has("groups"):
        cm.eq("groups", [[p.source.identity] for p in pubs])


@gold("T0-04-N04")
def contact_vs_teams(cm: Cmp) -> None:
    contact, chat = cm.case["input"]["records"]
    pub = publish("contacts", contact["version_ref"])
    scope = TeamsScope(kind="chat", chat_id=chat["scope"])
    res = teams(message(scope, chat["version_ref"]))
    cm.eq("same_group", connected(res, chat["version_ref"], pub.source.identity))
    cm.eq("group_status_contact", "none" if not res.replies else "candidate")


@gold("T0-04-N05")
def todo_removed(cm: Cmp) -> None:
    ref = tscope("scope-todo", "list")
    out = derive_transitions(observation(ref), (state(ref, "todo-1", "1"),), ())
    mail_scope = "scope-mail-account-A"
    cm.eq(
        "todo_absence_authority_over_mail",
        any(t.scope_id == mail_scope for t in out.transitions),
    )


@gold("T0-04-N06")
def calendar_marker(cm: Cmp) -> None:
    ref = tscope("view-2026-01-05..12", "view")
    removed = False
    try:
        out = derive_transitions(
            observation(ref, "membership"),
            (state(ref, "cal-6", "1", content=None),),
            (seen(ref, "cal-6", "1", marker=True),),
        )
        removed = any(t.kind == "deletion" for t in out.transitions)
    except TransitionSemanticsError:
        removed = False
    cm.eq("is_removed_set", removed)
    cm.eq("absence_proves_global_deletion", removed)
