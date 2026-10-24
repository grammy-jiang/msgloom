"""P3-04 Outlook grouping: bounds, determinism and PII-safe errors."""

from __future__ import annotations

import base64
import random
from typing import Any

import pytest
from pydantic import ValidationError

from msgloom.a2_kedro.contracts.codec import A2ContractError
from msgloom.a2_kedro.contracts.relations import NodeRef, ScopeKind
from msgloom.a2_kedro.semantics.outlook_grouping import (
    MAX_HINT_MEMBERS,
    MAX_HINTS,
    MAX_MESSAGES,
    MAX_REFERENCE_IDS,
    LimitationCode,
    OutlookGrouping,
    OutlookMessage,
    group_outlook_messages,
)
from tests.a2_kedro.helpers import check

MARKER = "private-id-x9@example.invalid"
SEEDS = tuple(range(40))
PERMUTATIONS = 4


def msg(
    mid: str,
    *,
    workset: str = "w1",
    scope: str = "mb1",
    kind: ScopeKind = "mailbox",
    **fields: Any,
) -> OutlookMessage:
    ref = NodeRef(scope_kind=kind, scope_id=scope, node_id=mid)
    return OutlookMessage(workset_id=workset, ref=ref, **fields)


def random_messages(seed: int) -> list[OutlookMessage]:
    """Build a synthetic, messy message set. It is the same for a seed."""
    rng = random.Random(seed)
    count = rng.randrange(2, 24)
    ids = [f"m{i}" for i in range(count)]
    index = base64.b64encode(bytes([seed % 7]) * 22).decode()
    items: list[OutlookMessage] = []
    for mid in ids:
        parents = tuple(
            f"<{rng.choice(ids)}@x>" for _ in range(rng.choice((0, 0, 1, 1, 2)))
        )
        refs = tuple(f"<{rng.choice(ids)}@x>" for _ in range(rng.choice((0, 1, 3))))
        items.append(
            msg(
                mid if rng.random() > 0.1 else ids[0],
                workset=rng.choice(("w1", "w2")),
                scope=rng.choice(("mb1", "mb2")),
                internet_message_id=f"<{mid}@x>" if rng.random() > 0.1 else None,
                conversation_id=rng.choice((None, "c1", "c2", "c3")),
                conversation_index=rng.choice((None, index, "bad index")),
                in_reply_to=parents,
                references=refs,
                subject=rng.choice((None, "Topic", "re: topic", "Other")),
            )
        )
    return items


def test_output_is_independent_of_input_order() -> None:
    for seed in SEEDS:
        items = random_messages(seed)
        expected = group_outlook_messages(items)
        for shuffle in range(PERMUTATIONS):
            mixed = list(items)
            random.Random(seed * 100 + shuffle).shuffle(mixed)
            check(
                group_outlook_messages(mixed) == expected,
                "result changed with input order",
            )
            check(
                group_outlook_messages(mixed).model_dump_json()
                == expected.model_dump_json(),
                "bytes changed with input order",
            )


def test_random_inputs_keep_the_safety_invariants() -> None:
    for seed in SEEDS:
        items = random_messages(seed)
        result = group_outlook_messages(items)
        scope_of: dict[tuple[str, str], set[tuple[str, str]]] = {}
        for item in items:
            key = (item.workset_id, item.ref.node_id)
            scope_of.setdefault(key, set()).add(
                (item.ref.scope_kind, item.ref.scope_id)
            )
        seen: set[tuple[str, str, str, str]] = set()
        for group in result.groups:
            check(len(group.members) >= 2, "a group has two members")
            check(group.status == "candidate", "candidate only")
            check(LimitationCode.CANDIDATE_ONLY in group.limitations, "limitation")
            check(bool(group.evidence), "a group names its evidence")
            for mid in group.members:
                key = (group.workset_id, group.scope_kind, group.scope_id, mid)
                check(key not in seen, "a message is in one group")
                seen.add(key)
                check(
                    (group.scope_kind, group.scope_id) in scope_of[(key[0], mid)],
                    "member belongs to the scope and workset of its group",
                )
        for hint in result.subject_hints:
            check(hint.can_merge is False, "hints cannot merge")
        plain = [i.model_copy(update={"subject": None}) for i in items]
        bare = group_outlook_messages(plain)
        check(bare.groups == result.groups, "subject changed membership")
        check(bare.conflicts == result.conflicts, "subject changed conflicts")


def test_message_count_is_bounded_and_fails_closed() -> None:
    items = [msg(f"m{i}") for i in range(MAX_MESSAGES)]
    check(group_outlook_messages(items) is not None, "the bound itself is allowed")
    items.append(msg("one-more"))
    with pytest.raises(A2ContractError) as caught:
        group_outlook_messages(items)
    check("count bound" in str(caught.value), "fixed text")


def test_reference_lists_are_bounded() -> None:
    ids = tuple(f"<{i}@x>" for i in range(MAX_REFERENCE_IDS))
    check(msg("a", references=ids).references == ids, "the bound is allowed")
    over = (*ids, "<over@x>")
    with pytest.raises(ValidationError):
        msg("a", references=over)
    with pytest.raises(ValidationError):
        msg("a", in_reply_to=over)


def test_hints_are_bounded_and_marked_truncated() -> None:
    items: list[OutlookMessage] = []
    for n in range(MAX_HINTS + 1):
        items += [
            msg(f"a{n:04d}", subject=f"topic {n}"),
            msg(f"b{n:04d}", subject=f"Topic {n}"),
        ]
    result = group_outlook_messages(items)
    check(result.groups == (), "hints never group")
    check(len(result.subject_hints) == MAX_HINTS, "hint cap")
    check(result.limitations == (LimitationCode.HINTS_TRUNCATED,), "reported")
    kept = [hint.members[0] for hint in result.subject_hints]
    check(kept == sorted(kept), "kept hints are a sorted prefix")


def test_hint_members_are_bounded() -> None:
    items = [msg(f"m{i:03d}", subject="Same") for i in range(MAX_HINT_MEMBERS + 4)]
    result = group_outlook_messages(items)
    check(len(result.subject_hints[0].members) == MAX_HINT_MEMBERS, "member cap")
    check(result.limitations == (LimitationCode.HINTS_TRUNCATED,), "reported")


def test_large_chain_is_grouped_without_deep_recursion() -> None:
    items = [msg("m0", internet_message_id="<m0@x>")]
    for i in range(1, MAX_MESSAGES):
        items.append(
            msg(
                f"m{i}",
                internet_message_id=f"<m{i}@x>",
                in_reply_to=(f"<m{i - 1}@x>",),
            )
        )
    result = group_outlook_messages(items)
    check(len(result.groups) == 1, "one group")
    check(len(result.groups[0].members) == MAX_MESSAGES, "all members")


def test_malformed_input_is_rejected_without_echo() -> None:
    ref = NodeRef(scope_kind="mailbox", scope_id="mb", node_id="m")
    bad: list[dict[str, object]] = [
        {"workset_id": MARKER + "\n", "ref": ref},
        {"workset_id": "", "ref": ref},
        {"workset_id": "w", "ref": ref, "conversation_id": MARKER + "\x00"},
        {"workset_id": "w", "ref": ref, "subject": ""},
        {"workset_id": "w", "ref": ref, "in_reply_to": [MARKER]},
        {"workset_id": "w", "ref": ref, "references": (MARKER, "")},
        {"workset_id": "w", "ref": ref, "unknown_field": MARKER},
    ]
    for payload in bad:
        with pytest.raises(ValidationError) as caught:
            OutlookMessage.model_validate(payload)
        check(MARKER not in str(caught.value), "input is hidden in the error")


def test_bound_errors_do_not_echo_message_content() -> None:
    items = [msg(MARKER + str(i), subject=MARKER) for i in range(MAX_MESSAGES + 1)]
    with pytest.raises(A2ContractError) as caught:
        group_outlook_messages(items)
    check(MARKER not in str(caught.value), "no content in the error")
    long_list = tuple(f"<{MARKER}{i}>" for i in range(MAX_REFERENCE_IDS + 1))
    with pytest.raises(ValidationError) as long_caught:
        msg("a", references=long_list)
    check(MARKER not in str(long_caught.value), "no content in the error")


def test_result_never_carries_subject_text() -> None:
    items = [
        msg("a", subject=MARKER, conversation_id="c1"),
        msg("b", subject=MARKER, conversation_id="c2"),
        msg("c", subject=MARKER + " other", conversation_id="c1"),
    ]
    result: OutlookGrouping = group_outlook_messages(items)
    check(MARKER not in result.model_dump_json(), "no subject in output")
    check(len(result.subject_hints) == 1, "hint exists")
