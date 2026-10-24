"""P3-08 authority: exact comparison and no payload leak on refusal."""

from __future__ import annotations

import pytest

from msgloom.a2_kedro.semantics.transitions import (
    ObservedRecord,
    ScopeObservation,
    ScopeRef,
    TransitionSemanticsError,
    derive_transitions,
)
from tests.a2_kedro.helpers import SCOPE, check, entry, hexd

STREAM = ScopeRef(intake=SCOPE, scope_kind="stream", scope_id="mail")
AUTHORITY = "content-src"
SENTINEL_CLAIM = "claim-sentinel-q7"
SENTINEL_AUTHORITY = "scope-sentinel-z3"


def scope(authority: str = AUTHORITY) -> ScopeObservation:
    return ScopeObservation(
        scope=STREAM,
        role="content",
        enumeration="complete",
        authority=authority,
        entry=entry(9),
    )


def marker(claim: str) -> ObservedRecord:
    return ObservedRecord(
        scope=STREAM,
        resource_kind="mail",
        resource_id="m1",
        fact_id=hexd("1"),
        content_sha256=None,
        entry=entry(3),
        deletion_authority=claim,
    )


@pytest.mark.parametrize(
    "claim",
    [
        AUTHORITY.upper(),
        AUTHORITY.title(),
        f" {AUTHORITY}",
        f"{AUTHORITY} ",
        "content\u200b-src",
        f"{AUTHORITY}\u200b",
        "content\u2011src",
        "content\u2010src",
        "content src",
    ],
    ids=lambda claim: ascii(claim),
)
def test_marker_authority_variants_are_refused(claim: str) -> None:
    check(claim != AUTHORITY, "variant differs from the scope authority")
    with pytest.raises(TransitionSemanticsError) as err:
        derive_transitions(scope(), (), (marker(claim),))
    check(err.value.code == "authority_mismatch", "variant must be refused")
    check(err.value.position == 0, "position reported")


def test_exact_marker_authority_is_accepted() -> None:
    out = derive_transitions(scope(), (), (marker(AUTHORITY),))
    check([t.kind for t in out.transitions] == ["deletion"], "exact match")


def test_authority_refusal_does_not_leak_claim_or_scope_authority() -> None:
    with pytest.raises(TransitionSemanticsError) as err:
        derive_transitions(scope(SENTINEL_AUTHORITY), (), (marker(SENTINEL_CLAIM),))
    check(err.value.code == "authority_mismatch", "authority code")
    views = {
        "str": str(err.value),
        "repr": repr(err.value),
        "args": repr(err.value.args),
    }
    for name, text in views.items():
        check(SENTINEL_CLAIM not in text, f"{name} leaks the claim")
        check(SENTINEL_AUTHORITY not in text, f"{name} leaks the scope authority")
        check("authority_mismatch" in text, f"{name} names the code")
