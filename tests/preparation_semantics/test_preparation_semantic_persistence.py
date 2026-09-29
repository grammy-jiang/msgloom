"""Verify the registered preparation chain survives a persistence restart."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path

import pytest

from msgloom.contracts import (
    AttemptIdentity,
    ClaimKind,
    ExecutionIdentity,
    ExternalEffectState,
    ResultRef,
    TerminalStatus,
    VersionRef,
)
from msgloom.persistence import Phase1Persistence
from msgloom.preparation.filtering import (
    AddressNormalization,
    FilterConfig,
    apply_filters,
)
from msgloom.preparation.grouping import group_records
from tests.prepared_contract_fixtures import (
    phase1_url,
    prepared_record,
    prepared_result,
)


def test_saved_filter_and_group_data_admit_a_dependent_claim_after_restart(
    tmp_path: Path,
) -> None:
    """Use production registries for typed data and exact dependency lineage."""

    async def exercise() -> None:
        record = prepared_record()
        config = FilterConfig(
            reference=VersionRef("filter_config", "synthetic", "v1"),
            address_normalization=AddressNormalization.EXACT,
            rules=(),
        )
        filtered = apply_filters(record, config)
        group = group_records((record,), (filtered,))[0]
        values = (
            ("prepared", record),
            ("filter_result", filtered),
            ("group_result", group),
        )
        url = phase1_url(tmp_path / "phase1.sqlite3")
        persistence = await Phase1Persistence.open(url)
        refs: tuple[ResultRef, ...] = ()
        try:
            for kind, value in values:
                reference = persistence.semantic_reference(
                    f"data-{kind}", kind, "1", value
                )
                result = replace(
                    prepared_result(reference, result_id=f"result-{kind}"),
                    kind=kind,
                    input_refs=refs,
                )
                await persistence.append_result_with_data(result, value)
                refs = (ResultRef(result.result_id, kind, "1"),)
        finally:
            await persistence.close()

        reopened = await Phase1Persistence.open(url)
        try:
            for kind, expected in values:
                saved = await reopened.get_result(f"result-{kind}")
                if saved is None or saved.semantic_data_ref is None:
                    pytest.fail("saved preparation data reference is missing")
                actual = await reopened.load_semantic_data(saved.semantic_data_ref)
                if type(actual) is not type(expected) or actual != expected:
                    pytest.fail("preparation data did not retain its typed value")
            claim = await reopened.acquire_claim(
                "triage:synthetic-chain",
                ClaimKind.TRIAGE,
                ExecutionIdentity("execution-triage"),
                AttemptIdentity("attempt-triage"),
                required_inputs=refs,
            )
            await reopened.finish_claim(
                claim, TerminalStatus.COMPLETE, ExternalEffectState.NONE
            )
        finally:
            await reopened.close()

    asyncio.run(exercise())
