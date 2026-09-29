"""Prepared-source contract and exact round-trip tests."""

from __future__ import annotations

import asyncio
import warnings
from pathlib import Path

import pytest
from pydantic import ValidationError

from msgloom.contracts import (
    AttemptIdentity,
    ClaimKind,
    ExecutionIdentity,
    ExternalEffectState,
    ResultRef,
    SemanticDataRef,
    TerminalStatus,
)
from msgloom.persistence import (
    DependencyNotReadyError,
    Phase1Persistence,
    SemanticDataTypeError,
)
from msgloom.preparation import CellLocation, PreparedParty, PreparedRecord, TableBlock
from tests.prepared_contract_fixtures import (
    phase1_url,
    prepared_record,
    prepared_result,
)


def test_prepared_contract_rejects_mutable_collection_and_naive_time() -> None:
    record = prepared_record()
    kwargs = {
        "source": record.source,
        "source_type": record.source_type,
        "sender": record.sender,
        "author": record.author,
        "subject": record.subject,
        "body": record.body,
        "relationships": record.relationships,
        "attachments": record.attachments,
        "parsed_contents": record.parsed_contents,
        "limitations": record.limitations,
        "source_mappings": record.source_mappings,
        "filtering": record.filtering,
    }
    with pytest.raises(ValidationError):
        PreparedRecord(
            **kwargs,
            recipients=list(record.recipients),  # type: ignore[arg-type]
            source_time=record.source_time,
        )
    with pytest.raises(ValidationError, match="timezone-aware"):
        PreparedRecord(
            **kwargs,
            recipients=record.recipients,
            source_time=record.source_time.replace(tzinfo=None),
        )


def test_prepared_codec_revalidates_bypassed_model_state_before_persistence(
    tmp_path: Path,
) -> None:
    sensitive_body = "source-body-must-not-appear-in-validation-errors"
    record = prepared_record(body=sensitive_body)
    copied = record.model_copy(
        update={"source_time": record.source_time.replace(tzinfo=None)}
    )
    wrong_type = record.model_copy(update={"source_time": sensitive_body})
    values = {name: getattr(record, name) for name in PreparedRecord.model_fields}
    values["sender"] = PreparedParty.model_construct(identity="")
    constructed = PreparedRecord.model_construct(**values)

    async def exercise() -> None:
        persistence = await Phase1Persistence.open(
            phase1_url(tmp_path / "phase1.sqlite3")
        )
        try:
            reference = persistence.semantic_reference(
                "validated-data", "prepared", "1", record
            )
            for suffix, invalid in (
                ("model-copy", copied),
                ("wrong-type", wrong_type),
                ("model-construct", constructed),
            ):
                result = prepared_result(reference, result_id=f"invalid-{suffix}")
                with warnings.catch_warnings(record=True) as emitted:
                    warnings.simplefilter("always")
                    with pytest.raises(SemanticDataTypeError) as raised:
                        await persistence.append_result_with_data(result, invalid)
                if emitted:
                    pytest.fail("Semantic validation emitted unredacted warnings")
                if sensitive_body in str(raised.value):
                    pytest.fail("Semantic validation error exposed source content")
                if await persistence.get_result(result.result_id) is not None:
                    pytest.fail("Invalid prepared data persisted a stage result")
            with pytest.raises(DependencyNotReadyError):
                await persistence.load_semantic_data(reference)
        finally:
            await persistence.close()

    asyncio.run(exercise())


def test_prepared_data_round_trip_reopen_preserves_exact_locations(
    tmp_path: Path,
) -> None:
    path = tmp_path / "phase1.sqlite3"
    prepared = prepared_record()

    async def save() -> SemanticDataRef:
        persistence = await Phase1Persistence.open(phase1_url(path))
        try:
            reference = persistence.semantic_reference(
                "prepared-data-1", "prepared", "1", prepared
            )
            await persistence.append_result_with_data(
                prepared_result(reference), prepared
            )
            if await persistence.load_semantic_data(reference) != prepared:
                pytest.fail("Prepared semantic data changed during initial round trip")
            return reference
        finally:
            await persistence.close()

    reference = asyncio.run(save())

    async def reopen() -> None:
        persistence = await Phase1Persistence.open(phase1_url(path))
        try:
            result = await persistence.get_result("prepared-1")
            if result is None or result.semantic_data_ref != reference:
                pytest.fail("Reopened result lost its semantic data reference")
            loaded = await persistence.load_semantic_data(reference)
            if loaded != prepared or not isinstance(loaded, PreparedRecord):
                pytest.fail("Prepared semantic data changed after reopen")
            block = loaded.parsed_contents[0].output.blocks[1]
            if not isinstance(block, TableBlock):
                pytest.fail("Ordered table block type did not survive storage")
            if block.table.cells[0].location != CellLocation("Budget", 7, 2, "B7"):
                pytest.fail("Exact parser cell location did not survive storage")
            token = await persistence.acquire_claim(
                "triage:synthetic",
                ClaimKind.TRIAGE,
                ExecutionIdentity("execution-triage"),
                AttemptIdentity("attempt-triage"),
                required_inputs=(ResultRef("prepared-1", "prepared", "1"),),
            )
            await persistence.finish_claim(
                token, TerminalStatus.COMPLETE, ExternalEffectState.NONE
            )
        finally:
            await persistence.close()

    asyncio.run(reopen())
