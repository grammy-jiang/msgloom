"""P3-05 Teams grouping: chat versus channel scope, component-only refresh."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from msgloom.a2_kedro.contracts.codec import MAX_TEXT_BYTES
from msgloom.a2_kedro.semantics.teams_grouping import (
    MAX_COMPONENTS,
    MAX_ENTRIES,
    TeamsEntry,
    TeamsGrouping,
    TeamsGroupingInput,
    TeamsMessageRef,
    TeamsScope,
    group_teams,
)
from tests.a2_kedro.helpers import check

SECRET = "secret-id-x9@example.invalid"
SRC = "src-1"


def chat(chat_id: str = "c1") -> TeamsScope:
    return TeamsScope(kind="chat", chat_id=chat_id)


def chan(team: str = "t1", channel: str = "k1") -> TeamsScope:
    return TeamsScope(kind="channel", team_id=team, channel_id=channel)


def ref(scope: TeamsScope, message_id: str) -> TeamsMessageRef:
    return TeamsMessageRef(scope=scope, message_id=message_id)


def msg(
    scope: TeamsScope,
    message_id: str,
    reply_to: TeamsMessageRef | None = None,
    source: str = SRC,
) -> TeamsEntry:
    return TeamsEntry(
        source_id=source,
        scope=scope,
        message_id=message_id,
        kind="message",
        reply_to=reply_to,
    )


def refresh(
    scope: TeamsScope, message_id: str, count: int = 1, source: str = SRC
) -> TeamsEntry:
    return TeamsEntry(
        source_id=source,
        scope=scope,
        message_id=message_id,
        kind="component_refresh",
        component_count=count,
    )


def run(*entries: TeamsEntry) -> TeamsGrouping:
    return group_teams(TeamsGroupingInput(source_id=SRC, entries=entries))


def replies(result: TeamsGrouping) -> list[tuple[str, str, str, tuple[str, ...]]]:
    return [
        (r.child.message_id, r.parent.message_id, str(r.status), tuple(r.reasons))
        for r in result.replies
    ]


def members(result: TeamsGrouping, scope: TeamsScope) -> list[tuple[str, bool, int]]:
    group = result.group_for(scope)
    if group is None:
        pytest.fail("group is missing")
    return [(m.message_id, m.has_body, m.component_count) for m in group.members]


def rejected(**kwargs: Any) -> pytest.ExceptionInfo[ValidationError]:
    """Build an entry and expect a pydantic error that hides the ID."""
    with pytest.raises(ValidationError) as info:
        TeamsEntry(**kwargs)
    check(SECRET not in str(info.value), "error text echoes an ID")
    return info


def test_chat_reply_in_same_chat_is_confirmed() -> None:
    result = run(msg(chat(), "m1"), msg(chat(), "m2", ref(chat(), "m1")))
    check(replies(result) == [("m2", "m1", "confirmed", ())], "chat reply")
    check(
        members(result, chat()) == [("m1", True, 0), ("m2", True, 0)],
        "chat members",
    )
    check(result.source_id == SRC, "source id")


def test_channel_reply_in_same_channel_is_confirmed() -> None:
    result = run(msg(chan(), "r"), msg(chan(), "x", ref(chan(), "r")))
    check(replies(result) == [("x", "r", "confirmed", ())], "channel reply")
    check(result.group_for(chat()) is None, "no chat group appears")


def test_same_message_id_in_chat_and_channel_is_never_related() -> None:
    result = run(msg(chan(), "m1"), msg(chat(), "m2", ref(chan(), "m1")))
    check(
        replies(result) == [("m2", "m1", "needs_review", ("cross_scope",))],
        "chat reply naming a channel message",
    )
    both = run(msg(chan(), "m1"), msg(chat(), "m1"))
    check(replies(both) == [], "equal ids alone relate nothing")
    check(len(both.groups) == 2, "one group per scope")
    check(members(both, chat()) == [("m1", True, 0)], "chat member")
    check(members(both, chan()) == [("m1", True, 0)], "channel member")


def test_other_channel_and_other_team_are_other_scopes() -> None:
    other_channel = run(msg(chan(), "p"), msg(chan("t1", "k2"), "c", ref(chan(), "p")))
    check(
        replies(other_channel) == [("c", "p", "needs_review", ("cross_scope",))],
        "other channel",
    )
    other_team = run(msg(chan(), "p"), msg(chan("t2", "k1"), "c", ref(chan(), "p")))
    check(
        replies(other_team) == [("c", "p", "needs_review", ("cross_scope",))],
        "other team, same channel id",
    )
    other_chat = run(msg(chat("c1"), "p"), msg(chat("c2"), "c", ref(chat("c1"), "p")))
    check(
        replies(other_chat) == [("c", "p", "needs_review", ("cross_scope",))],
        "other chat",
    )


def test_channel_scope_id_is_unambiguous() -> None:
    check(chan("ab", "c").node_scope() == ("channel", "2:abc"), "ab + c")
    check(chan("a", "bc").node_scope() == ("channel", "1:abc"), "a + bc")
    check(chat("c1").node_scope() == ("thread", "c1"), "chat scope")
    result = run(msg(chan("ab", "c"), "m"), msg(chan("a", "bc"), "m"))
    check(len(result.groups) == 2, "two scopes, not one")


def test_component_only_refresh_creates_no_body_and_no_relation() -> None:
    result = run(refresh(chan(), "m9", 3))
    check(members(result, chan()) == [("m9", False, 3)], "member has no body")
    check(replies(result) == [], "refresh creates no relation")


def test_refresh_adds_components_to_a_message_that_has_a_body() -> None:
    result = run(refresh(chat(), "m1", 2), msg(chat(), "m1"), refresh(chat(), "m1", 5))
    check(members(result, chat()) == [("m1", True, 5)], "body kept, max count")
    check(replies(result) == [], "no relation")


def test_refresh_is_scoped_like_a_message() -> None:
    result = run(msg(chat(), "m1"), refresh(chan(), "m1", 1))
    check(members(result, chat()) == [("m1", True, 0)], "chat keeps its body")
    check(members(result, chan()) == [("m1", False, 1)], "channel has no body")


def test_reply_to_a_refresh_only_parent_is_confirmed() -> None:
    result = run(refresh(chan(), "p", 1), msg(chan(), "c", ref(chan(), "p")))
    check(replies(result) == [("c", "p", "confirmed", ())], "parent is declared")
    check(members(result, chan()) == [("c", True, 0), ("p", False, 1)], "no body")


def test_refresh_must_have_components_and_no_parent() -> None:
    base: dict[str, Any] = {
        "source_id": SRC,
        "scope": chat(),
        "message_id": "m",
        "kind": "component_refresh",
    }
    rejected(**base)
    rejected(**base, component_count=0)
    rejected(**base, component_count=1, reply_to=ref(chat(), "p"))
    check(TeamsEntry(**base, component_count=1).component_count == 1, "valid")


def test_missing_duplicate_and_self_parent_need_review() -> None:
    missing = run(msg(chat(), "c", ref(chat(), "gone")))
    check(
        replies(missing) == [("c", "gone", "needs_review", ("missing_parent",))],
        "missing parent",
    )
    dup = run(msg(chat(), "p"), msg(chat(), "p"), msg(chat(), "c", ref(chat(), "p")))
    check(
        replies(dup) == [("c", "p", "needs_review", ("duplicate_message_id",))],
        "duplicate parent",
    )
    check(members(dup, chat()) == [("c", True, 0), ("p", True, 0)], "one member")
    selfy = run(msg(chat(), "s", ref(chat(), "s")))
    check(replies(selfy) == [("s", "s", "needs_review", ("cycle",))], "self reply")


def test_output_does_not_depend_on_input_order() -> None:
    entries = (
        msg(chan(), "b", ref(chan(), "a")),
        msg(chan(), "a"),
        msg(chat(), "z"),
        refresh(chat(), "y", 2),
    )
    forward = run(*entries)
    backward = run(*reversed(entries))
    check(forward == backward, "same result")
    check([g.scope.kind for g in forward.groups] == ["channel", "chat"], "group order")
    check(members(forward, chat()) == [("y", False, 2), ("z", True, 0)], "members")


def test_unknown_scope_is_rejected() -> None:
    for kind in ("group", "team", "thread", "Chat", "", "mailbox"):
        with pytest.raises(ValidationError) as info:
            TeamsScope(kind=kind, chat_id=SECRET)  # type: ignore[arg-type]
        check(SECRET not in str(info.value), "scope error echoes an ID")


def test_scope_fields_must_match_the_kind() -> None:
    bad: list[dict[str, Any]] = [
        {"kind": "chat"},
        {"kind": "chat", "chat_id": "c", "team_id": "t"},
        {"kind": "chat", "chat_id": "c", "channel_id": "k"},
        {"kind": "channel", "team_id": "t"},
        {"kind": "channel", "channel_id": "k"},
        {"kind": "channel", "chat_id": "c", "team_id": "t", "channel_id": "k"},
        {"kind": "channel"},
    ]
    for kwargs in bad:
        with pytest.raises(ValidationError):
            TeamsScope(**kwargs)


def test_cross_source_grouping_is_rejected() -> None:
    entries = (msg(chat(), "a"), msg(chat(), "b", source=SECRET))
    with pytest.raises(ValidationError) as info:
        TeamsGroupingInput(source_id=SRC, entries=entries)
    check("entries span more than one source" in str(info.value), "fixed text")
    check(SECRET not in str(info.value), "error echoes a source ID")
    ok = TeamsGroupingInput(
        source_id=SECRET, entries=(msg(chat(), "a", source=SECRET),)
    )
    check(SECRET not in repr(ok), "repr echoes an ID")


def test_empty_ids_are_rejected() -> None:
    for field in ("source_id", "message_id"):
        kwargs: dict[str, Any] = {
            "source_id": SRC,
            "scope": chat(),
            "message_id": "m",
            "kind": "message",
        }
        kwargs[field] = ""
        rejected(**kwargs)
    for kwargs in ({"kind": "chat", "chat_id": ""},):
        with pytest.raises(ValidationError):
            TeamsScope(**kwargs)
    with pytest.raises(ValidationError):
        TeamsScope(kind="channel", team_id="", channel_id="k")
    with pytest.raises(ValidationError):
        TeamsScope(kind="channel", team_id="t", channel_id="")
    with pytest.raises(ValidationError):
        ref(chat(), "")
    with pytest.raises(ValidationError):
        TeamsGroupingInput(source_id="")


def test_oversized_ids_are_rejected_at_the_byte_bound() -> None:
    edge = "a" * MAX_TEXT_BYTES
    check(ref(chat(edge), edge).message_id == edge, "2048 bytes are accepted")
    with pytest.raises(ValidationError) as info:
        ref(chat(), edge + SECRET)
    check(SECRET not in str(info.value), "error echoes an ID")
    with pytest.raises(ValidationError):
        chat("a" * (MAX_TEXT_BYTES + 1))
    # 683 three-byte characters are 2049 bytes.
    with pytest.raises(ValidationError):
        ref(chat(), "\u20ac" * 683)
    check(len(ref(chat(), "\u20ac" * 682).message_id) == 682, "682 chars fit")


def test_channel_scope_id_is_bounded_after_joining() -> None:
    half = "a" * 1100
    with pytest.raises(ValidationError) as info:
        chan(half + SECRET, half)
    check(SECRET not in str(info.value), "error echoes an ID")
    check(chan("a" * 1000, "b" * 1000).kind == "channel", "joined id fits")


def test_entry_count_is_bounded_before_validation() -> None:
    entries = tuple(msg(chat(), f"m{i}") for i in range(MAX_ENTRIES))
    result = run(*entries)
    check(len(result.groups[0].members) == MAX_ENTRIES, "bound is accepted")
    with pytest.raises(ValidationError) as info:
        TeamsGroupingInput(source_id=SRC, entries=(*entries, entries[0]))
    check("at most" in str(info.value), "length limit rejects first")


def test_bool_and_other_non_int_counts_are_rejected() -> None:
    base: dict[str, Any] = {
        "source_id": SRC,
        "scope": chat(),
        "message_id": "m",
        "kind": "component_refresh",
    }
    for count in (True, False, 1.0, "1", None, -1, MAX_COMPONENTS + 1):
        rejected(**base, component_count=count)
    check(
        TeamsEntry(**base, component_count=MAX_COMPONENTS).component_count == 1024,
        "upper bound is accepted",
    )


def test_non_str_ids_are_rejected() -> None:
    class Sub(str):
        __slots__ = ()

    for bad in (1, True, b"m", None, Sub("m")):
        with pytest.raises(ValidationError):
            ref(chat(), bad)  # type: ignore[arg-type]
        with pytest.raises(ValidationError):
            TeamsScope(kind="chat", chat_id=bad)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "bad",
    [
        SECRET + "\x00",
        SECRET + "\n",
        SECRET + "\t",
        SECRET + "\x7f",
        SECRET + "\x85",
        SECRET + "\u2028",
        SECRET + "\u2029",
        SECRET + "\ud800",
        "\udc00" + SECRET,
    ],
)
def test_hostile_control_and_surrogate_ids_are_rejected(bad: str) -> None:
    kwargs: dict[str, Any] = {
        "source_id": SRC,
        "scope": chat(),
        "message_id": bad,
        "kind": "message",
    }
    info = rejected(**kwargs)
    check(SECRET not in repr(info.value), "repr of the error echoes an ID")
    with pytest.raises(ValidationError) as scope_info:
        TeamsScope(kind="chat", chat_id=bad)
    check(SECRET not in str(scope_info.value), "scope error echoes an ID")
    with pytest.raises(ValidationError) as chan_info:
        chan(bad, "k")
    check(SECRET not in str(chan_info.value), "channel error echoes an ID")


def test_hostile_format_characters_stay_opaque_and_distinct() -> None:
    rlo = "m\u202e1"
    zwj = "m\u200d1"
    fold = "\u00e9"
    nfd = "e\u0301"
    result = run(
        msg(chat(), rlo),
        msg(chat(), zwj),
        msg(chat(), "m1"),
        msg(chat(), fold),
        msg(chat(), nfd),
        msg(chat(), "\u00c9"),
    )
    check(
        members(result, chat())
        == [
            ("e\u0301", True, 0),
            ("m1", True, 0),
            ("m\u200d1", True, 0),
            ("m\u202e1", True, 0),
            ("\u00c9", True, 0),
            ("\u00e9", True, 0),
        ],
        "six distinct ids, none normalized",
    )
    link = run(msg(chat(), rlo), msg(chat(), "m1", ref(chat(), rlo)))
    check(
        replies(link) == [("m1", "m\u202e1", "confirmed", ())],
        "exact id match only",
    )
    near = run(msg(chat(), nfd), msg(chat(), "c", ref(chat(), fold)))
    check(
        replies(near) == [("c", "\u00e9", "needs_review", ("missing_parent",))],
        "NFC does not match NFD",
    )


def test_ids_never_appear_in_repr_of_inputs_or_results() -> None:
    scope = chan(SECRET, SECRET + "k")
    entries = (
        msg(scope, SECRET, source=SRC),
        msg(scope, SECRET + "2", ref(scope, SECRET)),
        refresh(scope, SECRET + "3", 2),
    )
    result = run(*entries)
    for value in (*entries, scope, result, *result.groups, *result.replies):
        check(SECRET not in repr(value), "repr echoes an ID")
    check(len(result.replies) == 1, "the reply was reviewed")
