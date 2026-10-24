"""
V0-05 acceptance: relation, rule and grouping anomalies against the gold.

Oracle: ``golden/t0_02.json`` (Mail relation cases), ``golden/t0_03.json``
(Teams) and ``golden/t0_04.json`` (Calendar, To Do, OneDrive, Contacts),
checked against ``golden/MANIFEST.sha256`` at test start. The gold files
are read only.

Method: as in V0-04. For each gold case the test builds typed evidence by
hand from the case ``input`` (``v0_05_mail``, ``v0_05_teams``,
``v0_05_context``), runs the real P3 function and compares observed facts
with the gold ``expected`` block. No expected value comes from the
implementation. A disagreement is marked ``xfail(strict=True)`` and pinned
by a second test that names the exact fields that differ. The mapping
decisions are written at the top of each ``v0_05_*`` module.

Rules (P3-03 filters) and replay keys (P3-07): no gold case of ``t0_02``
to ``t0_04`` states a rule or a replay expectation, so no gold-driven test
exists for them. The requirement tests state only facts that the gold fixes.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from msgloom.a2_kedro.contracts.codec import A2ContractError
from msgloom.a2_kedro.contracts.relations import NodeRef
from msgloom.a2_kedro.semantics import outlook_grouping as og
from msgloom.a2_kedro.semantics import relations as rel
from msgloom.a2_kedro.semantics.context_types import ContextRefusal
from msgloom.a2_kedro.semantics.outlook_grouping import (
    ConflictCode,
    group_outlook_messages,
)
from msgloom.a2_kedro.semantics.relation_safety import (
    CandidateRelation,
    RelationReviewInput,
    ReviewReason,
    SafetyStatus,
    review_relations,
)
from msgloom.a2_kedro.semantics.relations import LimitationCode, MessageEvidence
from msgloom.a2_kedro.semantics.teams_grouping import TeamsEntry, TeamsScope
from msgloom.preparation.records import PreparedSourceType
from tests.a2_kedro.acceptance import v0_05_context as ctx
from tests.a2_kedro.acceptance import v0_05_mail as mail
from tests.a2_kedro.acceptance import v0_05_teams as tm
from tests.a2_kedro.acceptance.v0_05_gold import (
    CANARY,
    CASES,
    CHECKS,
    GOLD_FILES,
    file_digest,
    manifest_digests,
    run,
)
from tests.a2_kedro.acceptance.v0_05_tables import (
    DISAGREEMENTS,
    NOT_MAPPABLE,
    UNMAPPED,
)
from tests.a2_kedro.helpers import check

# --- tests: oracle, scan guard, gold cases ----------------------------------


def test_gold_digests_match_manifest() -> None:
    table = manifest_digests()
    for name in GOLD_FILES:
        check(name in table, f"{name} is listed in MANIFEST.sha256")
        check(file_digest(name) == table[name], f"{name} digest differs")


def test_scan_guard_every_gold_case_is_covered_or_listed() -> None:
    check(len(CASES) == 8 + 17 + 15, "8 mail relation, 17 Teams and 15 context cases")
    check(set(CHECKS).isdisjoint(NOT_MAPPABLE), "a case is checked or not mappable")
    check(set(CHECKS) | set(NOT_MAPPABLE) == set(CASES), "every gold id is accounted")
    check(set(DISAGREEMENTS) <= set(CHECKS), "a disagreement is a checked case")
    check(all(NOT_MAPPABLE.values()), "every not-mappable case names a reason")
    check(all(why for why, _ in DISAGREEMENTS.values()), "every xfail has a reason")
    for case_id, keys in UNMAPPED.items():
        check(case_id in CHECKS and all(keys.values()), f"{case_id}: unmapped reasons")


@pytest.mark.parametrize("case_id", sorted(CHECKS))
def test_every_expected_key_is_checked_or_declared_unmapped(case_id: str) -> None:
    cm = run(case_id)
    keys = set(cm.expected)
    seen = {k.split("[")[0] for k in cm.checked}
    unmapped = set(UNMAPPED.get(case_id, {}))
    check(not seen & unmapped, f"{case_id}: an unmapped key was also checked")
    check(keys - seen == unmapped, f"{case_id}: unchecked {sorted(keys - seen)}")


def _param(case_id: str) -> Any:
    marks = []
    if case_id in DISAGREEMENTS:
        reason = f"V0-05 DISAGREEMENT {case_id}: {DISAGREEMENTS[case_id][0]}"
        marks.append(pytest.mark.xfail(strict=True, reason=reason))
    return pytest.param(case_id, marks=marks, id=case_id)


@pytest.mark.parametrize("case_id", [_param(c) for c in sorted(CHECKS)])
def test_gold_case(case_id: str) -> None:
    cm = run(case_id)
    check(not cm.bad, f"{case_id} differs from gold in {cm.bad}")


@pytest.mark.parametrize("case_id", sorted(DISAGREEMENTS))
def test_disagreement_is_pinned_to_exact_fields(case_id: str) -> None:
    cm = run(case_id)
    pinned = {key.split("[")[0] for key in cm.bad}
    check(
        pinned == DISAGREEMENTS[case_id][1], f"{case_id}: differs in {sorted(pinned)}"
    )


# --- requirement 1: cannot attribute ----------------------------------------


def test_item_without_relation_evidence_stays_ungrouped() -> None:
    res = group_outlook_messages([mail.omsg("<a@x>", subject="Budget")])
    check(not res.groups, "a lone message forms no group")
    check(
        [u.code for u in res.unresolved] == [og.LimitationCode.NO_NATIVE_EVIDENCE],
        "unknown",
    )
    lone = mail.recover(mail.ev("<a@x>"))
    check(
        not lone.relations.relations and not lone.limitations, "no relation, no guess"
    )


def test_item_with_evidence_groups_and_unknown_parent_is_not_guessed() -> None:
    both = group_outlook_messages(
        [mail.omsg("<a@x>", internet_message_id="<a@x>"),
         mail.omsg("<b@x>", in_reply_to=("<a@x>",))]
    )  # fmt: skip
    check(mail.same_outlook_group(both, "<a@x>", "<b@x>"), "a resolvable parent groups")
    orphan = mail.recover(mail.ev("<b@x>", "<gone@x>"), mail.ev("<c@x>"))
    check(not orphan.relations.relations, "an unknown parent gives no relation")
    check([u.target_id for u in orphan.unresolved] == ["<gone@x>"], "unresolved named")
    check(LimitationCode.UNRESOLVED_TARGET in mail.codes(orphan), "limitation kept")


# --- requirement 2: cross scope ---------------------------------------------


def test_same_conversation_id_in_two_scopes_never_groups() -> None:
    msgs = [mail.omsg("a", "box-A", conversation_id="conv-1"),
            mail.omsg("b", "box-B", conversation_id="conv-1")]  # fmt: skip
    res = group_outlook_messages(msgs)
    check(not res.groups, "no group spans or forms from two scopes")
    codes = [c.code for c in res.conflicts]
    check(codes == [ConflictCode.CONVERSATION_ID_ACROSS_SCOPES], "conflict visible")
    mixed = group_outlook_messages(
        [*msgs, mail.omsg("c", "box-A", conversation_id="conv-1")]
    )
    check(
        [g.members for g in mixed.groups] == [("a", "c")], "only the scope of A groups"
    )
    check(not mail.same_outlook_group(mixed, "a", "b"), "B stays out of the group")


def test_same_conversation_id_in_one_scope_groups_as_candidate_only() -> None:
    res = group_outlook_messages([mail.omsg(n, conversation_id="conv-1") for n in "ab"])
    check([g.members for g in res.groups] == [("a", "b")], "one scope groups")
    check(og.LimitationCode.CANDIDATE_ONLY in res.groups[0].limitations, "candidate")


def test_reply_across_scopes_needs_review_and_same_scope_confirms() -> None:
    def node(scope: str, nid: str) -> NodeRef:
        return NodeRef(scope_kind="thread", scope_id=scope, node_id=nid)

    nodes = (node("A", "p"), node("A", "c"), node("B", "q"))
    basis = "same_source:reply_parent"
    cross = CandidateRelation(
        kind="reply_to", child=nodes[2], parent=nodes[0], basis=basis
    )
    same = CandidateRelation(
        kind="reply_to", child=nodes[1], parent=nodes[0], basis=basis
    )
    out = review_relations(RelationReviewInput(nodes=nodes, relations=(cross, same)))
    by_child = {r.relation.child.node_id: r for r in out.reviews}
    check(
        by_child["q"].status is SafetyStatus.NEEDS_REVIEW, "cross scope not confirmed"
    )
    check(ReviewReason.CROSS_SCOPE in by_child["q"].reasons, "reason cross_scope")
    check(by_child["c"].status is SafetyStatus.CONFIRMED, "same scope confirms")


def test_teams_equal_message_id_in_two_scopes_is_two_messages() -> None:
    one, two = (
        TeamsScope(kind="chat", chat_id="A"),
        TeamsScope(kind="chat", chat_id="B"),
    )
    res = tm.teams(
        tm.message(one, "m1"), tm.message(two, "m1"), tm.message(two, "m2", (two, "m1"))
    )
    check(tm.members_of(res, one) == ["m1"], "scope A keeps its own m1")
    check(tm.members_of(res, two) == ["m1", "m2"], "scope B keeps its own m1")
    check(tm.status_of(res, "m2") == "confirmed", "reply inside B confirms")
    check(res.group_for(one) != res.group_for(two), "two scopes, two groups")


# --- requirement 3: duplicate IDs -------------------------------------------


def test_differing_duplicates_are_flagged_and_name_no_parent() -> None:
    dup_a, dup_b = mail.ev("<d@x>"), mail.ev("<d@x>", "<p@x>")
    rec = mail.recover(dup_a, dup_b, mail.ev("<p@x>"), mail.ev("<c@x>", "<d@x>"))
    check(LimitationCode.DUPLICATE_MESSAGE_ID in mail.codes(rec), "duplicate flagged")
    check(
        LimitationCode.AMBIGUOUS_TARGET in mail.codes(rec), "ambiguous target flagged"
    )
    check(mail.chosen_parent(rec, "<c@x>") is None, "no parent is chosen")
    check(mail.status_of(rec, "<c@x>") == "uncertain", "child is uncertain")


def test_unique_ids_raise_no_duplicate_flag() -> None:
    rec = mail.recover(mail.ev("<p@x>"), mail.ev("<c@x>", "<p@x>"))
    check(not mail.codes(rec), "no limitation")
    check(mail.chosen_parent(rec, "<c@x>") == "<p@x>", "parent named")
    check(mail.status_of(rec, "<c@x>") == "confirmed", "confirmed")


def test_outlook_differing_duplicates_are_withdrawn_not_merged() -> None:
    res = group_outlook_messages(
        [mail.omsg("d", subject="one"), mail.omsg("d", subject="two"),
         mail.omsg("e", conversation_id="c"), mail.omsg("f", conversation_id="c")]
    )  # fmt: skip
    check(
        [c.code for c in res.conflicts] == [ConflictCode.DUPLICATE_MESSAGE_ID], "flag"
    )
    check(all("d" not in g.members for g in res.groups), "duplicate joins no group")


def test_review_flags_duplicate_node_and_teams_double_body() -> None:
    n = [NodeRef(scope_kind="thread", scope_id="A", node_id=x) for x in ("p", "c")]
    basis = "same_source:reply_parent"
    cand = CandidateRelation(kind="reply_to", child=n[1], parent=n[0], basis=basis)
    out = review_relations(
        RelationReviewInput(nodes=(n[0], n[0], n[1]), relations=(cand,))
    )
    check(out.reviews[0].reasons == (ReviewReason.DUPLICATE_MESSAGE_ID,), "flagged")
    scope = TeamsScope(kind="chat", chat_id="A")
    res = tm.teams(
        tm.message(scope, "p"),
        tm.message(scope, "p"),
        tm.message(scope, "c", (scope, "p")),
    )
    check(res.replies[0].status is SafetyStatus.NEEDS_REVIEW, "reply to a double body")
    check(ReviewReason.DUPLICATE_MESSAGE_ID in res.replies[0].reasons, "reason kept")


# --- requirement 4: source-native context -----------------------------------


@pytest.mark.parametrize("key", sorted(ctx.TYPES))
def test_context_source_yields_context_record_not_group(key: str) -> None:
    pub = ctx.publish(key, "item-1")
    check(pub.stream == ctx.TYPES[key][1], "record keeps its own stream")
    check(not ctx.field_names(pub) & {"members", "group_id", "evidence"}, "no group")
    check(ctx.refusal_code(ctx.TYPES[key][0]) == "accepted", "context type accepted")


@pytest.mark.parametrize(
    "source_type",
    [
        PreparedSourceType.OUTLOOK_EMAIL,
        PreparedSourceType.TEAMS_CHANNEL_MESSAGE,
        PreparedSourceType.TEAMS_CHAT_MESSAGE,
    ],
)
def test_communication_source_is_not_context(source_type: PreparedSourceType) -> None:
    check(ctx.refusal_code(source_type) == "not_context_source", "refused as context")


# --- requirement 5: cycle and ambiguous parent are bounded ------------------


def test_parent_cycle_is_limited_and_never_loops() -> None:
    size = 300
    ring = [mail.ev(f"<{i}@x>", f"<{(i + 1) % size}@x>") for i in range(size)]
    rec = mail.recover(*ring)
    check(LimitationCode.CYCLE in mail.codes(rec), "cycle limitation")
    check(not rec.relations.relations, "no edge of the cycle is chosen")
    check(mail.limits_of(rec).incomplete, "recovery is incomplete")
    check(mail.status_of(rec, "<0@x>") == "uncertain", "never confirmed")
    chain = mail.recover(mail.ev("<a@x>"), mail.ev("<b@x>", "<a@x>"))
    check(LimitationCode.CYCLE not in mail.codes(chain), "a chain is no cycle")


def test_teams_reply_cycle_needs_review() -> None:
    scope = TeamsScope(kind="chat", chat_id="A")
    res = tm.teams(
        tm.message(scope, "a", (scope, "b")), tm.message(scope, "b", (scope, "a"))
    )
    check(all(ReviewReason.CYCLE in r.reasons for r in res.replies), "cycle flagged")
    check(tm.each(res, ["a", "b"]) == "uncertain", "neither is confirmed")


def test_ambiguous_parent_is_limited_and_depth_is_bounded() -> None:
    two = MessageEvidence(message_id="<c@x>", reply_parent_ids=("<a@x>", "<b@x>"))
    rec = mail.recover(mail.ev("<a@x>"), mail.ev("<b@x>"), two)
    check(LimitationCode.CONFLICTING_PARENTS in mail.codes(rec), "two parents flagged")
    check(mail.chosen_parent(rec, "<c@x>") is None, "no parent is chosen")
    deep = rel.MAX_ANCESTOR_DEPTH + 5
    names = tuple(f"<n{i}@x>" for i in range(deep))
    long = mail.recover(*(mail.ev(n) for n in names), mail.ev("<top@x>", refs=names))
    check(LimitationCode.DEPTH_EXCEEDED in mail.codes(long), "depth limit visible")
    check(len(mail.ancestors_of(long, "<top@x>")) == rel.MAX_ANCESTOR_DEPTH, "cut")


def test_outlook_input_bound_fails_closed() -> None:
    many = [mail.omsg(f"m{i}") for i in range(og.MAX_MESSAGES + 1)]
    with pytest.raises(A2ContractError):
        group_outlook_messages(many)
    check(
        len(group_outlook_messages(many[:2]).unresolved) == 2, "at the bound it works"
    )


# --- requirement 6: PII canary ----------------------------------------------


def leaked(*parts: object) -> bool:
    """Return True when the canary is in the repr or text of any part."""
    return any(CANARY in f"{part!r} {part}" for part in parts)


def test_canary_detector_sees_a_leak_and_clean_text() -> None:
    check(leaked(f"x {CANARY}"), "detector finds the canary")
    check(not leaked("clean"), "detector accepts clean text")


def test_canary_in_content_never_reaches_results() -> None:
    res = group_outlook_messages(
        [mail.omsg("a", subject=CANARY, conversation_id="c"),
         mail.omsg("b", subject=CANARY, conversation_id="c"),
         mail.omsg("c", subject=CANARY)]
    )  # fmt: skip
    check(bool(res.groups) and bool(res.subject_hints), "result has groups and hints")
    check(not leaked(res), "no subject text in the grouping result")
    for key in ctx.TYPES:
        check(not leaked(ctx.publish(key, "i", subject=CANARY)), f"{key} publication")


def test_canary_in_rejected_input_is_not_echoed() -> None:
    ids = tuple(f"{CANARY}-{i}" for i in range(og.MAX_REFERENCE_IDS + 1))
    with pytest.raises(ValidationError) as caught:
        mail.omsg("a", references=ids)
    check(not leaked(caught.value), "reference bound error hides ids")
    with pytest.raises(ValidationError) as relation:
        rel.MessageEvidence(message_id="a", ancestor_ids=ids * 8)
    check(not leaked(relation.value), "relation input error hides ids")
    with pytest.raises(ValidationError) as entry:
        TeamsEntry(
            source_id="s", scope=TeamsScope(kind="chat", chat_id="A"),
            message_id=f"{CANARY}\x00", kind="message",
        )  # fmt: skip
    check(not leaked(entry.value), "teams control-character error hides the id")
    with pytest.raises(ContextRefusal) as refusal:
        ctx.publish("todo", "i", subject=CANARY * 600)
    check(not leaked(refusal.value), "context refusal")


def test_canary_message_id_is_hidden_from_teams_repr() -> None:
    scope = TeamsScope(kind="chat", chat_id=CANARY)
    res = tm.teams(
        tm.message(scope, f"{CANARY}-1"),
        tm.message(scope, "m2", (scope, f"{CANARY}-1")),
    )
    check(not leaked(res), "teams ids are hidden from repr")
    check(tm.status_of(res, "m2") == "confirmed", "the result is still correct")
