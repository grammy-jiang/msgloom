"""C0 edge checks for payload replay and selected-root identity."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from msgloom.sources.handoff_models import A1CatalogIdentity
from scripts.research.c0_contract_prototype import (
    AcceptedPayload,
    C0ContractError,
    FrozenRoot,
    append_or_verify,
)
from tests.research.test_c0_contract_prototype import (
    _entry,
    digest,
    fixture_workset,
    frozen_root,
    ref,
    stage_identity,
)


def _accepted(logical_key: str, byte_count: int = 23) -> AcceptedPayload:
    return AcceptedPayload(
        logical_key=logical_key,
        output=ref("prepared", 11, "2"),
        canonical_sha256=digest("accepted-first-output"),
        canonical_byte_count=byte_count,
    )


def test_replay_differing_only_in_byte_count_or_key_is_a_conflict() -> None:
    """
    A byte-count-only or key-only difference is not an equal replay.

    Each case changes exactly one field of ``AcceptedPayload``. The output
    reference and the canonical digest stay equal to the stored payload.
    """
    workset, workset_ref = fixture_workset()
    key = stage_identity(workset, workset_ref).logical_acceptance_key()
    other_key = stage_identity(
        workset, workset_ref, rule_version="c0-filter-v2"
    ).logical_acceptance_key()
    known = _accepted(key)
    # Positive control: an identical replay returns the stored payload.
    if append_or_verify(known, known.model_copy()) != known:
        pytest.fail("an identical replay must return the stored payload")
    if other_key == key:
        pytest.fail("the key-only case needs a different valid logical key")
    for update in ({"canonical_byte_count": 24}, {"logical_key": other_key}):
        changed = known.model_copy(update=update)
        if changed.model_dump(exclude=set(update)) != known.model_dump(
            exclude=set(update)
        ):
            pytest.fail(f"case {update} must change only its own field")
        with pytest.raises(C0ContractError, match="integrity-conflict"):
            append_or_verify(known, changed)


def test_stage_identity_rejects_duplicate_selected_occurrence() -> None:
    """
    Two equal selected occurrences fail; two distinct occurrences pass.

    The duplicate has the same entry, selected result and occurrence. The
    control differs only in ``occurrence``.
    """
    workset, workset_ref = fixture_workset()
    first = frozen_root(workset)
    distinct = first.model_copy(update={"occurrence": 1})
    # Positive control: distinct occurrences are accepted.
    stage_identity(workset, workset_ref, selected=(first, distinct))
    with pytest.raises(ValidationError, match="duplicate selected occurrence"):
        stage_identity(workset, workset_ref, selected=(first, first.model_copy()))


def test_stage_identity_rejects_cross_catalog_selected_roots() -> None:
    """
    Selected roots from two catalogs fail; the same catalog passes.

    The foreign root has a distinct occurrence, so the duplicate-occurrence
    check cannot be the cause. The control uses the workset catalog.
    """
    workset, workset_ref = fixture_workset()
    first = frozen_root(workset)
    catalog = workset.scope.catalog
    foreign_catalog = A1CatalogIdentity(
        catalog_identity="other-synthetic-a1-catalog", schema_version=1
    )

    def second_root(entry_catalog: A1CatalogIdentity) -> FrozenRoot:
        return first.model_copy(
            update={"entry": _entry(entry_catalog, 8), "occurrence": 1}
        )

    same = second_root(catalog)
    # Positive control: the same catalog is accepted.
    stage_identity(workset, workset_ref, selected=(first, same))
    with pytest.raises(ValidationError, match="cross-catalog selected roots"):
        stage_identity(
            workset, workset_ref, selected=(first, second_root(foreign_catalog))
        )
