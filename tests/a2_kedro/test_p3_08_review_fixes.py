"""P3-08 review fixes: partial outcomes and membership markers."""

from __future__ import annotations

import pytest

from msgloom.a2_kedro.semantics.transitions import (
    ABSENCE_NOT_PROVEN,
    TransitionSemanticsError,
    derive_transitions,
    to_batch,
    to_items,
)
from tests.a2_kedro.helpers import check
from tests.a2_kedro.test_p3_08 import FOLDER, WS, now, obs, prev


def test_partial_outcome_with_transitions_cannot_form_a_batch() -> None:
    # F1: one presence plus one unproven absence must not look complete.
    scope = obs(enumeration="partial")
    out = derive_transitions(scope, (prev("m1"),), (now("m2"),))
    check(len(out.transitions) == 1 and not out.complete, "partial outcome")
    check(out.limitations[0].code == ABSENCE_NOT_PROVEN, "limitation kept")
    with pytest.raises(TransitionSemanticsError) as err:
        to_batch(out, WS, "code-1", "pol-1")
    check(err.value.code == "partial_scope", "partial_scope code")


def test_partial_membership_outcome_cannot_form_a_batch() -> None:
    scope = obs(FOLDER, "membership", "partial")
    out = derive_transitions(
        scope, (prev("m1", None, FOLDER),), (now("m2", None, FOLDER),)
    )
    with pytest.raises(TransitionSemanticsError) as err:
        to_batch(out, WS, "code-1", "pol-1")
    check(err.value.code == "partial_scope", "partial_scope code")


def test_partial_error_does_not_echo_payloads() -> None:
    scope = obs(enumeration="partial", authority="secret-auth-q7")
    out = derive_transitions(scope, (prev("secret-id-q7"),), (now("m2"),))
    with pytest.raises(TransitionSemanticsError) as err:
        to_batch(out, WS, "code-1", "pol-1")
    text = f"{err.value} {err.value!r}"
    check("q7" not in text, "error text leaks a payload")


def test_partial_items_stay_available_with_limitations() -> None:
    scope = obs(enumeration="partial")
    out = derive_transitions(scope, (prev("m1"),), (now("m2"),))
    items = to_items(out.transitions)
    check(len(items) == 1 and items[0].kind == "presence", "items remain")
    check(len(out.limitations) == 1, "caller keeps the limitation")


def test_complete_outcome_still_forms_a_batch() -> None:
    out = derive_transitions(obs(), (prev("m1"),), (now("m2"),))
    batch = to_batch(out, WS, "code-1", "pol-1")
    check(len(batch.items) == 2, "complete outcome batches")


@pytest.mark.parametrize("enumeration", ["complete", "partial"])
@pytest.mark.parametrize("known", [True, False])
def test_membership_marker_never_emits_deletion(enumeration: str, known: bool) -> None:
    scope = obs(FOLDER, "membership", enumeration)
    before = (prev("m1", None, FOLDER),) if known else ()
    marker = now("m1", None, FOLDER, marker="content-src")
    with pytest.raises(TransitionSemanticsError) as err:
        derive_transitions(scope, before, (marker,))
    check(err.value.code == "membership_marker", "membership marker code")
    check(err.value.position == 0, "position reported")
    check("content-src" not in str(err.value), "authority is not echoed")


def test_content_scope_marker_still_deletes() -> None:
    out = derive_transitions(
        obs(), (prev("m1"),), (now("m1", None, marker="content-src"),)
    )
    check([t.kind for t in out.transitions] == ["deletion"], "content deletion")


def test_membership_removal_without_marker_is_unchanged() -> None:
    out = derive_transitions(obs(FOLDER, "membership"), (prev("m1", None, FOLDER),), ())
    check(
        [t.kind for t in out.transitions] == ["membership_removal"],
        "removal stays removal",
    )
