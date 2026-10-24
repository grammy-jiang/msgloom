"""P3-06 review fix: a grant is bound to the record source scope.

All data is synthetic. No test touches a provider, a network or a file.
"""

from __future__ import annotations

import pytest

from msgloom.a2_kedro.semantics.context_types import (
    ContextGrant,
    ContextRefusal,
    PublicationTarget,
)
from msgloom.preparation.records import PreparedSourceType
from msgloom.preparation_pipeline.intake_models import IntakeScope
from msgloom.sources.handoff_models import A1CatalogIdentity
from tests.a2_kedro.helpers import check
from tests.a2_kedro.p3_06_bound import publish_context
from tests.a2_kedro.test_p3_06 import CASES, WORKSET, scope_for, selection_of

SENTINEL = "SENTINEL-PII-123"


def scope_with(base_stream: str, /, **changes: object) -> IntakeScope:
    base = scope_for(base_stream)
    values: dict[str, object] = {
        "catalog": base.catalog,
        "source_id": base.source_id,
        "stream": base.stream,
        "consumer_id": base.consumer_id,
    }
    values.update(changes)
    return IntakeScope(**values)  # type: ignore[arg-type]


def refusal(
    source_type: PreparedSourceType, grant: IntakeScope, target: IntakeScope
) -> ContextRefusal:
    with pytest.raises(ContextRefusal) as caught:
        publish_context(
            selection_of(source_type),
            ContextGrant(grant, WORKSET),
            PublicationTarget(target, WORKSET),
        )
    error = caught.value
    check(SENTINEL not in str(error) and SENTINEL not in repr(error), "echoed input")
    return error


@pytest.mark.parametrize(("source_type", "_expected", "stream"), CASES)
def test_matching_source_still_publishes(
    source_type: PreparedSourceType, _expected: object, stream: str
) -> None:
    scope = scope_with(stream)
    out = publish_context(
        selection_of(source_type),
        ContextGrant(scope, WORKSET),
        PublicationTarget(scope, WORKSET),
    )
    check(out.stream == stream, "positive case publishes")


@pytest.mark.parametrize(("source_type", "_expected", "stream"), CASES)
def test_grant_for_another_source_is_refused(
    source_type: PreparedSourceType, _expected: object, stream: str
) -> None:
    other = scope_with(stream, source_id=SENTINEL)
    error = refusal(source_type, other, other)
    check(error.code == "source_mismatch", "record of source A, grant for B")


@pytest.mark.parametrize(
    "change",
    [
        {"consumer_id": SENTINEL},
        {"catalog": A1CatalogIdentity(catalog_identity=SENTINEL, schema_version=1)},
        {"stream": "onedrive"},
        {"source_id": SENTINEL},
    ],
    ids=["consumer", "catalog", "stream", "source"],
)
def test_target_differing_in_one_part_is_refused(change: dict[str, object]) -> None:
    grant = scope_with("todo")
    target = scope_with("todo", **change)
    error = refusal(PreparedSourceType.TODO, grant, target)
    check(error.code == "out_of_scope", "one differing part refuses")


@pytest.mark.parametrize(
    "change",
    [
        {"consumer_id": SENTINEL},
        {"catalog": A1CatalogIdentity(catalog_identity=SENTINEL, schema_version=1)},
    ],
    ids=["consumer", "catalog"],
)
def test_other_consumer_or_catalog_is_not_the_granted_scope(
    change: dict[str, object],
) -> None:
    other = scope_with("todo", **change)
    error = refusal(PreparedSourceType.TODO, scope_with("todo"), other)
    check(error.code == "out_of_scope", "target is not the grant")


def test_refusal_text_is_fixed() -> None:
    other = scope_with("todo", source_id=SENTINEL)
    error = refusal(PreparedSourceType.TODO, other, other)
    check(
        str(error) == "grant source does not match the record source scope",
        "fixed message",
    )
    check(error.args == (str(error),), "no extra args")
