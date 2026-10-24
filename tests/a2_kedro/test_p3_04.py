"""P3-04 Outlook native grouping: candidate-only groups, no subject merge."""

from __future__ import annotations

import base64
from typing import Any

import pytest
from pydantic import ValidationError

from msgloom.a2_kedro.contracts.relations import NodeRef
from msgloom.a2_kedro.semantics.outlook_grouping import (
    MAX_HINT_MEMBERS,
    MAX_HINTS,
    MAX_MESSAGES,
    MAX_REFERENCE_IDS,
    CandidateGroup,
    ConflictCode,
    EvidenceKind,
    LimitationCode,
    OutlookGrouping,
    OutlookMessage,
    group_outlook_messages,
)
from tests.a2_kedro.helpers import check

CID = EvidenceKind.CONVERSATION_ID
INDEX = EvidenceKind.CONVERSATION_INDEX


def header(seed: int) -> bytes:
    """Return a synthetic 22-byte header: byte 0x01, then a non-zero seed."""
    return b"\x01" + bytes([seed]) * 21


def index(seed: int, children: int = 0) -> str:
    """Return a base64 conversation index; each child adds 5 bytes."""
    return base64.b64encode(header(seed) + b"\x01" * (5 * children)).decode()


def msg(
    mid: str,
    *,
    workset: str = "w1",
    scope: str = "mb1",
    kind: str = "mailbox",
    **fields: Any,
) -> OutlookMessage:
    return OutlookMessage(
        workset_id=workset,
        ref=NodeRef(scope_kind=kind, scope_id=scope, node_id=mid),  # type: ignore[arg-type]
        **fields,
    )


def run(*items: OutlookMessage) -> OutlookGrouping:
    return group_outlook_messages(items)


def members(result: OutlookGrouping) -> list[tuple[str, ...]]:
    return [group.members for group in result.groups]


def codes(result: OutlookGrouping) -> list[str]:
    return [conflict.code.value for conflict in result.conflicts]


def unknown(result: OutlookGrouping, code: LimitationCode) -> list[str]:
    return [u.node.node_id for u in result.unresolved if u.code is code]


def test_empty_input_gives_empty_result() -> None:
    result = run()
    check(result == OutlookGrouping(), "empty result")


def test_conversation_id_gives_a_candidate_group_with_evidence() -> None:
    result = run(
        msg("a", conversation_id="c1", subject="Budget"),
        msg("b", conversation_id="c1", subject="Totally different"),
        msg("z", conversation_id="c2"),
    )
    check(members(result) == [("a", "b")], "same conversation id is grouped")
    group = result.groups[0]
    check(group.status == "candidate", "status is candidate")
    check(group.evidence == (CID,), "evidence names the conversation id")
    check(
        group.limitations == (LimitationCode.CANDIDATE_ONLY,),
        "limitation says candidate only",
    )
    check(unknown(result, LimitationCode.NO_NATIVE_EVIDENCE) == ["z"], "z unknown")
    check(result.conflicts == (), "no conflict")


def test_conversation_index_header_groups_and_children_share_it() -> None:
    result = run(
        msg("a", conversation_index=index(1)),
        msg("b", conversation_index=index(1, children=2)),
        msg("c", conversation_index=index(2)),
    )
    check(members(result) == [("a", "b")], "same 22-byte header is grouped")
    check(result.groups[0].evidence == (INDEX,), "index evidence")


def test_invalid_conversation_index_is_unknown_not_a_match() -> None:
    result = run(
        msg("a", conversation_index="not base64 !"),
        msg("b", conversation_index=base64.b64encode(b"short").decode()),
        msg("c", conversation_index="not base64 !"),
    )
    check(result.groups == (), "unusable index never groups")
    check(
        unknown(result, LimitationCode.INVALID_CONVERSATION_INDEX) == ["a", "b", "c"],
        "reported per message",
    )


# Hand-written base64 of 22-byte headers (and one with a 5-byte child block).
ZERO_HEADER = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=="  # 22 bytes of 0x00
BAD_FIRST_BYTE = "AgICAgICAgICAgICAgICAgICAgICAg=="  # 0x02, then 21 bytes 0x02
ZERO_GUID = "AQICAgICAAAAAAAAAAAAAAAAAAAAAA=="  # 0x01, 5 bytes 0x02, 16 bytes 0x00
GOOD_HEADER = "AQICAgICAwMDAwMDAwMDAwMDAwMDAw=="  # 0x01, 5 bytes 0x02, 16 bytes 0x03
GOOD_CHILD = "AQICAgICAwMDAwMDAwMDAwMDAwMDAwEBAQEB"  # GOOD_HEADER + 5 bytes 0x01


def test_all_zero_or_wrong_first_byte_header_is_rejected() -> None:
    result = run(
        msg("a", conversation_index=ZERO_HEADER),
        msg("b", conversation_index=ZERO_HEADER),
        msg("c", conversation_index=BAD_FIRST_BYTE),
        msg("d", conversation_index=BAD_FIRST_BYTE),
    )
    check(result.groups == (), "an invalid header never groups")
    check(
        unknown(result, LimitationCode.INVALID_CONVERSATION_INDEX)
        == ["a", "b", "c", "d"],
        "each message reports an invalid index",
    )


def test_header_with_zero_guid_is_rejected() -> None:
    result = run(
        msg("a", conversation_index=ZERO_GUID),
        msg("b", conversation_index=ZERO_GUID),
    )
    check(result.groups == (), "a zero GUID never groups")
    check(
        unknown(result, LimitationCode.INVALID_CONVERSATION_INDEX) == ["a", "b"],
        "reported",
    )


def test_valid_header_with_nonzero_guid_still_groups() -> None:
    result = run(
        msg("a", conversation_index=GOOD_HEADER),
        msg("b", conversation_index=GOOD_CHILD),
        msg("c", conversation_index=ZERO_HEADER),
    )
    check(members(result) == [("a", "b")], "valid headers group")
    check(result.groups[0].evidence == (INDEX,), "index evidence")
    check(
        unknown(result, LimitationCode.INVALID_CONVERSATION_INDEX) == ["c"],
        "only the invalid one is reported",
    )


def test_reply_and_reference_chain_gives_one_group() -> None:
    result = run(
        msg("a", internet_message_id="<a@x>"),
        msg("b", internet_message_id="<b@x>", in_reply_to=("<a@x>",)),
        msg(
            "c",
            internet_message_id="<c@x>",
            in_reply_to=("<b@x>",),
            references=("<a@x>", "<b@x>"),
        ),
    )
    check(members(result) == [("a", "b", "c")], "chain is one group")
    check(
        result.groups[0].evidence
        == (EvidenceKind.IN_REPLY_TO, EvidenceKind.REFERENCES),
        "reply and reference evidence",
    )


def test_unresolved_and_self_references_stay_unknown() -> None:
    result = run(
        msg("a", internet_message_id="<a@x>", in_reply_to=("<missing@x>",)),
        msg("b", internet_message_id="<b@x>", references=("<b@x>",)),
    )
    check(result.groups == (), "no group from unusable references")
    check(unknown(result, LimitationCode.UNRESOLVED_REFERENCE) == ["a"], "unresolved")
    check(unknown(result, LimitationCode.SELF_REFERENCE) == ["b"], "self reference")


def test_ambiguous_target_id_does_not_link() -> None:
    result = run(
        msg("a", internet_message_id="<d@x>"),
        msg("b", internet_message_id="<d@x>"),
        msg("c", in_reply_to=("<d@x>",)),
    )
    check(result.groups == (), "ambiguous target is not guessed")
    check(unknown(result, LimitationCode.AMBIGUOUS_REFERENCE) == ["c"], "reported")


def test_equal_subject_different_conversations_are_not_merged() -> None:
    result = run(
        msg("a", conversation_id="c1", subject="Weekly report"),
        msg("b", conversation_id="c2", subject="RE: weekly   REPORT"),
        msg("c", subject="Fwd: Weekly report"),
    )
    check(result.groups == (), "subject never merges")
    check(result.conflicts == (), "no conflict")
    check(len(result.subject_hints) == 1, "one hint")
    hint = result.subject_hints[0]
    check(hint.members == ("a", "b", "c"), "hint names the messages")
    check(hint.can_merge is False, "hint cannot merge")
    check("report" not in result.model_dump_json().lower(), "no subject text")


def test_subject_different_same_conversation_id_is_grouped() -> None:
    result = run(
        msg("a", conversation_id="c1", subject="Alpha"),
        msg("b", conversation_id="c1", subject="Omega"),
    )
    check(members(result) == [("a", "b")], "grouped by native evidence")
    check(result.subject_hints == (), "different subjects give no hint")


def test_same_subject_inside_one_group_gives_no_hint() -> None:
    result = run(
        msg("a", conversation_id="c1", subject="Same"),
        msg("b", conversation_id="c1", subject="re: same"),
    )
    check(result.subject_hints == (), "nothing left to hint")


def test_subject_never_changes_membership() -> None:
    base = [
        msg("a", conversation_id="c1", subject="One"),
        msg("b", conversation_id="c1", subject="Two"),
        msg("c", conversation_id="c3", subject="One"),
        msg("d", subject="One"),
    ]
    plain = [m.model_copy(update={"subject": None}) for m in base]
    left = group_outlook_messages(base)
    right = group_outlook_messages(plain)
    check(left.groups == right.groups, "groups ignore the subject")
    check(left.conflicts == right.conflicts, "conflicts ignore the subject")
    check(left.unresolved == right.unresolved, "unknowns ignore the subject")
    check(right.subject_hints == (), "no subject, no hint")


def test_cross_workset_is_never_associated() -> None:
    result = run(
        msg("a", workset="w1", conversation_id="c1", subject="Same"),
        msg("b", workset="w2", conversation_id="c1", subject="Same"),
        msg("c", workset="w1", conversation_index=index(5)),
        msg("d", workset="w2", conversation_index=index(5)),
    )
    check(result.groups == (), "no group across worksets")
    check(result.conflicts == (), "no cross-workset conflict is reported")
    check(result.subject_hints == (), "no cross-workset hint")
    check(len(result.unresolved) == 4, "all four stay unknown")


def test_cross_workset_message_id_is_not_a_reference_target() -> None:
    result = run(
        msg("a", workset="w1", in_reply_to=("<p@x>",)),
        msg("p", workset="w2", internet_message_id="<p@x>"),
    )
    check(result.groups == (), "no link into another workset")
    check(unknown(result, LimitationCode.UNRESOLVED_REFERENCE) == ["a"], "unresolved")


def test_worksets_group_independently() -> None:
    result = run(
        msg("a", workset="w1", conversation_id="c1"),
        msg("b", workset="w1", conversation_id="c1"),
        msg("a", workset="w2", conversation_id="c1"),
        msg("b", workset="w2", conversation_id="c1"),
    )
    check([g.workset_id for g in result.groups] == ["w1", "w2"], "one group each")
    check(len({g.group_id for g in result.groups}) == 2, "distinct group IDs")


def test_same_conversation_id_in_two_scopes_is_a_flagged_conflict() -> None:
    result = run(
        msg("a", scope="mb1", conversation_id="c1"),
        msg("b", scope="mb1", conversation_id="c1"),
        msg("x", scope="mb2", conversation_id="c1"),
        msg("y", scope="mb2", conversation_id="c1"),
    )
    check(codes(result) == ["conversation_id_across_scopes"], "conflict")
    check(len(result.conflicts[0].members) == 4, "conflict lists all messages")
    check(members(result) == [("a", "b"), ("x", "y")], "scopes are not merged")
    for group in result.groups:
        check(
            LimitationCode.CONFLICT_PRESENT in group.limitations, "groups are flagged"
        )


def test_different_scope_kind_is_a_different_scope() -> None:
    result = run(
        msg("a", scope="s", kind="mailbox", conversation_id="c1"),
        msg("b", scope="s", kind="thread", conversation_id="c1"),
    )
    check(result.groups == (), "scope kind is part of the scope")
    check(codes(result) == ["conversation_id_across_scopes"], "flagged")


def test_conflicting_parents_are_flagged_and_withdrawn() -> None:
    result = run(
        msg("a", internet_message_id="<a@x>", conversation_id="c1"),
        msg("b", internet_message_id="<b@x>", conversation_id="c1"),
        msg("c", conversation_id="c1", in_reply_to=("<a@x>", "<b@x>")),
    )
    check(codes(result) == ["conflicting_parents"], "conflict")
    check([n.node_id for n in result.conflicts[0].members] == ["c"], "names c")
    check(members(result) == [("a", "b")], "c is not merged")
    check(
        unknown(result, LimitationCode.WITHDRAWN_BY_CONFLICT) == ["c"],
        "withdrawn message is recorded as unresolved",
    )


def test_parent_mismatch_is_flagged_and_withdrawn() -> None:
    result = run(
        msg("a", internet_message_id="<a@x>"),
        msg("b", internet_message_id="<b@x>"),
        msg(
            "c",
            conversation_id="c1",
            in_reply_to=("<a@x>",),
            references=("<b@x>",),
        ),
    )
    check(codes(result) == ["parent_mismatch"], "conflict")
    check(result.groups == (), "no merge")
    check(
        unknown(result, LimitationCode.WITHDRAWN_BY_CONFLICT) == ["c"],
        "withdrawn message is recorded as unresolved",
    )


def test_matching_parent_and_last_reference_is_not_a_conflict() -> None:
    result = run(
        msg("a", internet_message_id="<a@x>"),
        msg("b", in_reply_to=("<a@x>",), references=("<z@x>", "<a@x>")),
    )
    check(result.conflicts == (), "consistent parents")
    check(members(result) == [("a", "b")], "grouped")
    check(unknown(result, LimitationCode.UNRESOLVED_REFERENCE) == ["b"], "z unknown")


def test_contradictory_conversation_ids_are_not_merged() -> None:
    result = run(
        msg("a", conversation_id="c1", internet_message_id="<a@x>"),
        msg("a2", conversation_id="c1"),
        msg("b", conversation_id="c2", in_reply_to=("<a@x>",)),
        msg("n", internet_message_id="<n@x>", references=("<a@x>",)),
    )
    check(codes(result) == ["contradictory_conversation_id"], "conflict")
    check(members(result) == [("a", "a2")], "only conversation id edges kept")
    check(LimitationCode.CONFLICT_PRESENT in result.groups[0].limitations, "flagged")
    check(
        unknown(result, LimitationCode.NO_NATIVE_EVIDENCE) == ["b", "n"],
        "other messages stay unknown",
    )


def test_index_header_with_two_conversation_ids_is_a_conflict() -> None:
    result = run(
        msg("a", conversation_id="c1", conversation_index=index(1)),
        msg("b", conversation_id="c2", conversation_index=index(1)),
    )
    check(codes(result) == ["contradictory_conversation_id"], "conflict")
    check(result.groups == (), "no merge")


def test_different_duplicate_message_id_is_a_conflict_equal_one_collapses() -> None:
    result = run(
        msg("a", conversation_id="c1"),
        msg("a", conversation_id="c2"),
        msg("e", conversation_id="c3"),
        msg("e", conversation_id="c3"),
        msg("f", conversation_id="c3"),
    )
    check(codes(result) == ["duplicate_message_id"], "conflict")
    check(members(result) == [("e", "f")], "equal duplicates collapse")


def test_unknown_evidence_stays_unknown() -> None:
    result = run(msg("a", subject="x"), msg("b"), msg("c", conversation_id="c1"))
    check(result.groups == () and result.conflicts == (), "no group, no conflict")
    check(
        unknown(result, LimitationCode.NO_NATIVE_EVIDENCE) == ["a", "b", "c"],
        "all unknown",
    )


def test_group_id_is_stable_and_distinct() -> None:
    first = run(msg("a", conversation_id="c1"), msg("b", conversation_id="c1"))
    again = run(msg("b", conversation_id="c1"), msg("a", conversation_id="c1"))
    other = run(msg("a", conversation_id="c1"), msg("c", conversation_id="c1"))
    check(first.groups[0].group_id == again.groups[0].group_id, "stable")
    check(first.groups[0].group_id != other.groups[0].group_id, "distinct")


def test_models_are_frozen() -> None:
    group = run(msg("a", conversation_id="c"), msg("b", conversation_id="c")).groups[0]
    with pytest.raises(ValidationError):
        group.status = "other"  # type: ignore[misc,assignment]
    check(isinstance(group, CandidateGroup), "group type")
    check(MAX_HINT_MEMBERS > 1 and MAX_HINTS > 1, "bounds are positive")
    check(ConflictCode.PARENT_MISMATCH.value == "parent_mismatch", "wire name")
    check(MAX_MESSAGES == 1024 and MAX_REFERENCE_IDS == 32, "documented bounds")
