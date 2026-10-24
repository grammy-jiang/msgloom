"""P3-06 review fix F4: a grant is bound to the frozen record workset.

All data is synthetic. Every test builds ``FrozenSelection`` directly and
calls the real ``publish_context``.
"""

from __future__ import annotations

from typing import Any

import pytest

from msgloom.a2_kedro.semantics import context_types as ct
from msgloom.a2_kedro.semantics.context_types import (
    ContextGrant,
    ContextRefusal,
    FrozenSelection,
    PublicationTarget,
    publish_context,
)
from msgloom.contracts import ResultRef
from msgloom.preparation.records import PreparedSourceType
from tests.a2_kedro.helpers import check
from tests.a2_kedro.test_p3_06 import CASES, WORKSET, scope_for, selection_of

OTHER_WORKSET = ResultRef("workset-2", "preparation_intake_workset", "1")
SENTINEL = "SENTINEL-PII-456"


def frozen(workset: Any = WORKSET, scope: Any = None) -> FrozenSelection:
    selection = selection_of(PreparedSourceType.TODO)
    return FrozenSelection(selection, scope or scope_for("todo"), workset)


def code_of(
    frozen_selection: Any, grant_workset: Any = WORKSET, target_workset: Any = None
) -> str:
    scope = scope_for("todo")
    grant = ContextGrant(scope, grant_workset)
    target = PublicationTarget(scope, target_workset or grant_workset)
    with pytest.raises(ContextRefusal) as caught:
        publish_context(frozen_selection, grant, target)
    text = str(caught.value) + repr(caught.value)
    check(SENTINEL not in text, "refusal echoed input")
    return caught.value.code


@pytest.mark.parametrize(("source_type", "_expected", "stream"), CASES)
def test_matching_binding_publishes(
    source_type: PreparedSourceType, _expected: object, stream: str
) -> None:
    scope = scope_for(stream)
    out = publish_context(
        FrozenSelection(selection_of(source_type), scope, WORKSET),
        ContextGrant(scope, WORKSET),
        PublicationTarget(scope, WORKSET),
    )
    check(out.workset == WORKSET and out.stream == stream, "positive case publishes")


def test_grant_for_workset_b_is_refused_for_record_frozen_under_a() -> None:
    # The grant and target agree with each other. Only the record differs.
    check(
        code_of(frozen(WORKSET), grant_workset=OTHER_WORKSET) == "binding_mismatch",
        "workset B grant must not publish a workset A record",
    )


def test_grant_for_another_scope_is_refused() -> None:
    other = scope_for("todo")
    other = type(other)(
        catalog=other.catalog,
        source_id=other.source_id,
        stream=other.stream,
        consumer_id=SENTINEL,
    )
    check(
        code_of(frozen(scope=other)) == "binding_mismatch",
        "consumer scope B grant must not publish a scope A record",
    )


@pytest.mark.parametrize("missing", [None, "", 0, SENTINEL, b"x"])
def test_missing_or_malformed_workset_is_refused(missing: object) -> None:
    check(code_of(frozen(workset=missing)) == "wrong_type", "workset binding")


@pytest.mark.parametrize("missing", [None, "", 0, SENTINEL])
def test_missing_or_malformed_scope_is_refused(missing: object) -> None:
    broken = FrozenSelection(selection_of(PreparedSourceType.TODO), missing, WORKSET)  # type: ignore[arg-type]
    check(code_of(broken) == "wrong_type", "scope binding")


def test_workset_of_wrong_kind_is_refused() -> None:
    wrong = ResultRef("workset-1", "other_kind", "1")
    check(code_of(frozen(workset=wrong)) == "wrong_type", "workset kind")


def test_bare_selection_without_binding_is_refused() -> None:
    selection = selection_of(PreparedSourceType.TODO)
    check(code_of(selection) == "wrong_type", "bare selection")
    check(code_of(selection.record) == "wrong_type", "bare record")
    check(code_of(None) == "wrong_type", "none")


def test_binding_fields_have_no_default() -> None:
    selection = selection_of(PreparedSourceType.TODO)
    with pytest.raises(TypeError):
        FrozenSelection(selection)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        FrozenSelection(selection, scope_for("todo"))  # type: ignore[call-arg]


def test_disabling_the_guard_lets_the_workset_mismatch_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mutation check: the new negative tests depend on the guard."""
    scope = scope_for("todo")
    grant = ContextGrant(scope, OTHER_WORKSET)
    target = PublicationTarget(scope, OTHER_WORKSET)
    with monkeypatch.context() as patch:
        patch.setattr(ct, "_check_scope", lambda *_a, **_k: None)
        out = publish_context(frozen(WORKSET), grant, target)
    check(out.workset == OTHER_WORKSET, "guard off publishes under workset B")
