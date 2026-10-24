"""P3-08 scoped transition semantics: authority, absence and membership."""

from __future__ import annotations

import random
from typing import Any

import pytest
from pydantic import ValidationError

from msgloom.a2_kedro.contracts.transition import TransitionBatch
from msgloom.a2_kedro.semantics.transitions import (
    ABSENCE_NOT_PROVEN,
    ObservedRecord,
    ScopeObservation,
    ScopeRef,
    StateRecord,
    TransitionOutcome,
    TransitionSemanticsError,
    derive_transitions,
    to_batch,
    to_items,
)
from msgloom.contracts import ResultRef
from msgloom.preparation_pipeline.intake_models import IntakeScope
from msgloom.sources.handoff_models import A1CatalogIdentity
from tests.a2_kedro.helpers import SCOPE, check, entry, hexd

FOLDER = ScopeRef(intake=SCOPE, scope_kind="folder", scope_id="inbox")
STREAM = ScopeRef(intake=SCOPE, scope_kind="stream", scope_id="mail")
OTHER_FOLDER = ScopeRef(intake=SCOPE, scope_kind="folder", scope_id="archive")
OTHER_CONSUMER = ScopeRef(
    intake=IntakeScope(
        catalog=SCOPE.catalog,
        source_id=SCOPE.source_id,
        stream=SCOPE.stream,
        consumer_id="consumer-2",
    ),
    scope_kind="folder",
    scope_id="inbox",
)
WS = ResultRef("ws-1", "preparation_intake_workset", "1")
SECRET = "secret-subject-x9"


def obs(
    ref: ScopeRef = STREAM,
    role: str = "content",
    enumeration: str = "complete",
    authority: str = "content-src",
) -> ScopeObservation:
    return ScopeObservation.model_validate(
        {
            "scope": ref,
            "role": role,
            "enumeration": enumeration,
            "authority": authority,
            "entry": entry(9),
        }
    )


def prev(
    rid: str, content: str | None = "a", ref: ScopeRef = STREAM, **kw: Any
) -> StateRecord:
    return StateRecord(
        scope=ref,
        resource_kind="mail",
        resource_id=rid,
        fact_id=hexd(kw.pop("fact", rid[-1])),
        content_sha256=None if content is None else hexd(content),
        **kw,
    )


def now(
    rid: str,
    content: str | None = "a",
    ref: ScopeRef = STREAM,
    marker: str | None = None,
    seq: int = 3,
    fact: str | None = None,
) -> ObservedRecord:
    return ObservedRecord(
        scope=ref,
        resource_kind="mail",
        resource_id=rid,
        fact_id=hexd(fact or rid[-1]),
        content_sha256=None if content is None else hexd(content),
        entry=entry(seq),
        deletion_authority=marker,
    )


def kinds(outcome: TransitionOutcome) -> list[tuple[str, str]]:
    return [(t.resource_id, t.kind) for t in outcome.transitions]


# (1) content refresh -------------------------------------------------------


def test_changed_hash_is_refresh_with_content_authority() -> None:
    out = derive_transitions(obs(), (prev("m1", "a"),), (now("m1", "b"),))
    check(kinds(out) == [("m1", "context_refresh")], "refresh expected")
    change = out.transitions[0]
    check(change.authority == "content-src", "content authority")
    check(change.entry == entry(3), "refresh uses the observed entry")
    check(out.complete and not out.limitations, "complete outcome")


def test_unchanged_hash_yields_nothing() -> None:
    out = derive_transitions(obs(), (prev("m1", "a"),), (now("m1", "a"),))
    check(out.transitions == () and out.unproven == (), "no change")


def test_new_resource_is_presence() -> None:
    out = derive_transitions(obs(), (), (now("m1", "a"),))
    check(kinds(out) == [("m1", "presence")], "presence expected")


def test_content_scope_requires_hash_and_marker_refuses_it() -> None:
    for bad in (now("m1", None), now("m1", "a", marker="provider")):
        with pytest.raises(TransitionSemanticsError) as err:
            derive_transitions(obs(), (), (bad,))
        check(err.value.code == "role_violation", "role code")


# (2) absence needs a complete enumeration ---------------------------------


def test_complete_scope_absence_is_absence_with_scope_authority() -> None:
    out = derive_transitions(obs(), (prev("m1"), prev("m2")), (now("m2"),))
    check(kinds(out) == [("m1", "absence")], "absence expected")
    check(out.transitions[0].authority == "content-src", "absence authority")
    check(out.transitions[0].entry == entry(9), "absence uses scope entry")
    check(out.transitions[0].fact_id == hexd("1"), "previous fact kept")


def test_partial_scope_absence_is_not_a_deletion() -> None:
    scope = obs(enumeration="partial")
    out = derive_transitions(scope, (prev("m1"), prev("m2")), (now("m2"),))
    check(out.transitions == (), "partial scope must not emit a transition")
    check([u.resource_id for u in out.unproven] == ["m1"], "unproven listed")
    check(not out.complete, "outcome is not complete")
    check(len(out.limitations) == 1, "one limitation")
    limit = out.limitations[0]
    check(limit.code == ABSENCE_NOT_PROVEN, "limitation code")
    check("m1" not in limit.detail, "limitation holds no resource ID")
    check(out.unproven[0].fact_id == hexd("1"), "unproven keeps fact")


def test_partial_scope_still_reports_what_it_saw() -> None:
    scope = obs(enumeration="partial")
    out = derive_transitions(scope, (prev("m1", "a"),), (now("m1", "b"), now("m3")))
    check(
        kinds(out) == [("m1", "context_refresh"), ("m3", "presence")],
        "observed records still count",
    )
    check(out.unproven == (), "nothing missing")


# (3) membership is separate from content ----------------------------------


def test_leaving_a_folder_is_membership_removal_not_deletion() -> None:
    scope = obs(FOLDER, "membership", authority="folder-src")
    out = derive_transitions(
        scope, (prev("m1", None, FOLDER),), (now("m2", None, FOLDER),)
    )
    check(
        kinds(out) == [("m1", "membership_removal"), ("m2", "presence")],
        "removal and add",
    )
    check(all(t.kind != "deletion" for t in out.transitions), "no deletion")
    check(all(t.authority == "folder-src" for t in out.transitions), "authority")
    check(all(t.scope_kind == "folder" for t in out.transitions), "scope kind")


def test_membership_scope_ignores_content_and_refuses_hash() -> None:
    scope = obs(FOLDER, "membership")
    out = derive_transitions(
        scope, (prev("m1", None, FOLDER),), (now("m1", None, FOLDER),)
    )
    check(out.transitions == (), "unchanged membership")
    with pytest.raises(TransitionSemanticsError) as err:
        derive_transitions(scope, (), (now("m1", "a", FOLDER),))
    check(err.value.code == "role_violation", "hash in membership scope")


def test_partial_membership_removal_is_unproven() -> None:
    scope = obs(FOLDER, "membership", "partial")
    out = derive_transitions(scope, (prev("m1", None, FOLDER),), ())
    check(out.transitions == () and len(out.unproven) == 1, "unproven")


def test_content_and_membership_runs_stay_separate() -> None:
    content = derive_transitions(obs(), (prev("m1", "a"),), (now("m1", "b"),))
    member = derive_transitions(
        obs(FOLDER, "membership"), (), (now("m1", None, FOLDER),)
    )
    check(content.transitions[0].scope_kind == "stream", "content scope")
    check(member.transitions[0].scope_kind == "folder", "membership scope")
    check(member.transitions[0].kind == "presence", "membership kind")


# (4) provider deletion marker ---------------------------------------------


def test_marker_is_deletion_with_scope_authority() -> None:
    out = derive_transitions(
        obs(), (prev("m1"),), (now("m1", None, marker="content-src"),)
    )
    check(kinds(out) == [("m1", "deletion")], "deletion expected")
    check(out.transitions[0].authority == "content-src", "marker authority")


def test_marker_in_partial_scope_still_deletes() -> None:
    scope = obs(enumeration="partial")
    out = derive_transitions(scope, (), (now("m1", None, marker="content-src"),))
    check(kinds(out) == [("m1", "deletion")], "marker needs no enumeration")


def test_membership_marker_is_a_deletion() -> None:
    scope = obs(FOLDER, "membership")
    gone = now("m1", None, FOLDER, marker="content-src")
    out = derive_transitions(scope, (prev("m1", None, FOLDER),), (gone,))
    check(kinds(out) == [("m1", "deletion")], "marker wins over removal")


def test_marker_with_other_authority_is_refused() -> None:
    other = now("m1", None, marker="other-src")
    for scope in (obs(), obs(enumeration="partial")):
        with pytest.raises(TransitionSemanticsError) as err:
            derive_transitions(scope, (prev("m1"),), (now("m0"), other))
        check(err.value.code == "authority_mismatch", "authority code")
        check(err.value.position == 1, "position reported")
        check("other-src" not in str(err.value), "claim is not echoed")
    member = obs(FOLDER, "membership")
    with pytest.raises(TransitionSemanticsError) as err2:
        derive_transitions(member, (), (now("m1", None, FOLDER, marker="x"),))
    check(err2.value.code == "authority_mismatch", "membership scope")


def test_blank_marker_authority_is_refused() -> None:
    with pytest.raises(ValueError):
        now("m1", None, marker="")


# (5) transitions never cross scopes ---------------------------------------


@pytest.mark.parametrize("other", [OTHER_FOLDER, OTHER_CONSUMER, FOLDER])
def test_cross_scope_observed_is_rejected(other: ScopeRef) -> None:
    with pytest.raises(TransitionSemanticsError) as err:
        derive_transitions(obs(), (), (now("m1", ref=other),))
    check(err.value.code == "cross_scope", "cross scope code")
    check(err.value.position == 0, "position reported")


def test_cross_scope_previous_is_rejected() -> None:
    with pytest.raises(TransitionSemanticsError) as err:
        derive_transitions(obs(), (prev("m1"), prev("m2", ref=FOLDER)), ())
    check(err.value.code == "cross_scope" and err.value.position == 1, "previous")


def test_foreign_catalog_entry_is_rejected() -> None:
    bad = now("m1").model_copy(
        update={
            "entry": entry(3).model_copy(
                update={
                    "catalog": A1CatalogIdentity(
                        catalog_identity="cat-2", schema_version=1
                    )
                }
            )
        }
    )
    with pytest.raises(TransitionSemanticsError) as err:
        derive_transitions(obs(), (), (bad,))
    check(err.value.code == "cross_scope", "foreign catalog")


def test_foreign_catalog_scope_entry_is_rejected() -> None:
    foreign = A1CatalogIdentity(catalog_identity="cat-2", schema_version=1)
    bad_entry = entry(9).model_copy(update={"catalog": foreign})
    for role, ref in (("content", STREAM), ("membership", FOLDER)):
        scope = obs(ref, role).model_copy(update={"entry": bad_entry})
        with pytest.raises(TransitionSemanticsError) as err:
            derive_transitions(scope, (prev("m1", None, ref),), ())
        check(err.value.code == "cross_scope", "foreign scope entry")


def test_plain_state_record_in_observed_is_rejected() -> None:
    plain: Any = prev("m1")
    with pytest.raises(TransitionSemanticsError) as err:
        derive_transitions(obs(), (prev("m1"),), (now("m2"), plain))
    check(err.value.code == "bad_record_type", "plain record as observed")
    check(err.value.position == 1, "position reported")


# (6) determinism, duplicates and conflicts --------------------------------


def test_duplicate_and_conflicting_records_are_rejected() -> None:
    with pytest.raises(TransitionSemanticsError) as dup:
        derive_transitions(obs(), (), (now("m1"), now("m1")))
    check(dup.value.code == "duplicate_record", "duplicate")
    with pytest.raises(TransitionSemanticsError) as con:
        derive_transitions(obs(), (), (now("m1", "a"), now("m1", "b")))
    check(con.value.code == "conflicting_record", "conflict")
    with pytest.raises(TransitionSemanticsError) as pre:
        derive_transitions(obs(), (prev("m1"), prev("m1", "b")), ())
    check(pre.value.code == "conflicting_record", "previous conflict")


def test_shared_fact_id_is_rejected() -> None:
    with pytest.raises(TransitionSemanticsError) as err:
        derive_transitions(obs(), (), (now("m1", fact="d"), now("m2", fact="d")))
    check(err.value.code == "fact_conflict", "fact conflict")


def test_marker_in_previous_state_is_rejected() -> None:
    with pytest.raises(TransitionSemanticsError) as err:
        derive_transitions(obs(), (now("m1"),), ())
    check(err.value.code == "role_violation", "observed record as previous")


def test_output_order_ignores_input_order() -> None:
    rids = ["m5", "m1", "m3", "m2", "m4"]
    base = derive_transitions(obs(), (), tuple(now(r) for r in sorted(rids)))
    check([t.resource_id for t in base.transitions] == sorted(rids), "sorted")
    rng = random.Random(7)
    for _ in range(5):
        rng.shuffle(rids)
        out = derive_transitions(obs(), (), tuple(now(r) for r in rids))
        check(out == base, "order must not change the outcome")


def test_replay_gives_identical_output_and_batch() -> None:
    before = (prev("m1", "a"), prev("m2", "a"), prev("m3", "a"))
    after = (now("m1", "b"), now("m4"), now("m2", None, marker="content-src"))
    first = derive_transitions(obs(), before, after)
    second = derive_transitions(obs(), before, after)
    check(first == second, "same input, same outcome")
    check(
        kinds(first)
        == [
            ("m1", "context_refresh"),
            ("m2", "deletion"),
            ("m3", "absence"),
            ("m4", "presence"),
        ],
        "mixed kinds in key order",
    )
    one = to_batch(first, WS, "code-1", "pol-1")
    two = to_batch(second, WS, "code-1", "pol-1")
    check(one.batch_sha256 == two.batch_sha256, "same batch identity")
    check(TransitionBatch.decode(one.encode()) == one, "batch round trip")
    check([i.ordinal for i in one.items] == [0, 1, 2, 3], "ordinals")


def test_items_fit_the_existing_wire_model() -> None:
    out = derive_transitions(obs(), (), (now("m1"),))
    item = to_items(out.transitions, first_ordinal=4)[0]
    check(item.ordinal == 4 and item.kind == "presence", "item fields")
    check(item.scope_kind == "stream" and item.scope_id == "mail", "scope")
    with pytest.raises(ValidationError):
        to_batch(derive_transitions(obs(), (), ()), WS, "c", "p")


# PII ----------------------------------------------------------------------


def test_error_messages_do_not_echo_payloads() -> None:
    secret_ref = ScopeRef(intake=SCOPE, scope_kind="folder", scope_id=SECRET)
    cases: list[Any] = [
        lambda: derive_transitions(obs(), (), (now(SECRET, ref=secret_ref),)),
        lambda: derive_transitions(obs(), (), (now(SECRET), now(SECRET))),
        lambda: derive_transitions(obs(), (), (now(SECRET, "a"), now(SECRET, "b"))),
        lambda: derive_transitions(obs(), (), (now(SECRET, None),)),
        lambda: derive_transitions(
            obs(authority=SECRET),
            (),
            (now(SECRET, fact="d"), now("m2", fact="d")),
        ),
        lambda: derive_transitions(obs(), (now(SECRET),), ()),
    ]
    for call in cases:
        with pytest.raises(TransitionSemanticsError) as err:
            call()
        text = f"{err.value} {err.value!r} {err.value.args}"
        check(SECRET not in text, "error text leaks a payload")
        check(err.value.code in text, "error names its code")


def test_construction_errors_do_not_echo_input() -> None:
    bad: Any = {"scope": STREAM, "resource_kind": "mail", "resource_id": SECRET}
    for model in (StateRecord, ObservedRecord):
        with pytest.raises(ValidationError) as err:
            model.model_validate({**bad, "fact_id": "not-a-digest"})
        check(SECRET not in str(err.value), "construction error leaks input")
    with pytest.raises(ValidationError) as err2:
        ScopeRef.model_validate(
            {"intake": SCOPE, "scope_kind": "folder", "scope_id": SECRET, "x": 1}
        )
    check(SECRET not in str(err2.value), "scope error leaks input")
    with pytest.raises(ValidationError) as err3:
        ScopeObservation.model_validate(
            {**obs().model_dump(), "authority": SECRET, "role": "bogus"}
        )
    check(SECRET not in str(err3.value), "observation error leaks input")


def test_limitation_text_does_not_echo_payloads() -> None:
    scope = obs(enumeration="partial", authority=SECRET)
    out = derive_transitions(scope, (prev(SECRET),), ())
    text = " ".join(f"{lim.code} {lim.detail}" for lim in out.limitations)
    check(text != "" and SECRET not in text, "limitation is payload free")


def test_unknown_error_code_is_refused() -> None:
    with pytest.raises(ValueError):
        TransitionSemanticsError("made_up")
