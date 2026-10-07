"""Prepare exact scoped transition facts as finite durable downstream input."""

from __future__ import annotations

import asyncio
import hashlib
import json
from typing import TYPE_CHECKING, Annotated

from pydantic import BaseModel, ConfigDict, Field

from msgloom.contracts import ClaimKind, ResultRef, StageResult, TerminalStatus
from msgloom.preparation_pipeline.intake_models import (
    IntakeTransition,
    PreparationIntakeWorkset,
)

if TYPE_CHECKING:
    from msgloom.persistence import Phase1Persistence


class PreparedTransitions(BaseModel):
    """Retain exact frozen facts without claiming downstream deletion effects."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    transitions: Annotated[
        tuple[IntakeTransition, ...], Field(min_length=1, max_length=1024)
    ]


class PreparedTransitionsCodec:
    """Revalidate bounded typed facts and require canonical serialization."""

    kind = "prepared_transitions"
    schema_version = "1"
    max_bytes = 4 * 1024 * 1024

    def encode(self, value: object) -> bytes:
        """Reject forged models and oversized or noncanonical facts."""
        if not isinstance(value, PreparedTransitions):
            raise TypeError("transition payload must be PreparedTransitions")
        payload = json.dumps(
            value.model_dump(mode="json", round_trip=True, warnings="error"),
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        if len(payload) > self.max_bytes:
            raise ValueError("prepared transitions exceed codec byte bound")
        PreparedTransitions.model_validate_json(payload, strict=True)
        return payload

    def decode(self, payload: bytes) -> PreparedTransitions:
        """Load only bounded canonical transition data."""
        if len(payload) > self.max_bytes:
            raise ValueError("prepared transitions exceed codec byte bound")
        value = PreparedTransitions.model_validate_json(payload, strict=True)
        if self.encode(value) != payload:
            raise ValueError("prepared transitions encoding is not canonical")
        return value


async def prepare_transitions(
    persistence: Phase1Persistence,
    reference: ResultRef,
    request,
    attempt,
    *,
    configuration_version: str,
    code_version: str,
    lease_seconds: float,
) -> tuple[ResultRef, ...]:
    """
    Publish one exact tuple under a separate finite accepted PREPARE claim.

    Read only the saved workset. COMPLETE means these scoped facts are prepared
    for downstream use, not that any resource was globally deleted or retired.
    Failed or cancelled publication cannot fabricate an accepted receipt.
    Normal acceptance and cleanup drain before cancellation reaches the caller.
    """
    from .stage_steps import _finish_uninterrupted

    saved = await persistence.get_result(reference.result_id)
    if (
        saved is None
        or saved.semantic_data_ref is None
        or ResultRef(saved.result_id, saved.kind, saved.schema_version) != reference
        or (reference.kind, reference.schema_version)
        != ("preparation_intake_workset", "1")
    ):
        raise ValueError("transition producer requires an exact saved workset")
    workset = await persistence.load_semantic_data(saved.semantic_data_ref)
    if not isinstance(workset, PreparationIntakeWorkset):
        raise TypeError("transition producer requires a typed intake workset")
    value = PreparedTransitions(transitions=workset.transitions)
    identity = hashlib.sha256(
        json.dumps(
            (reference.result_id, configuration_version, code_version),
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    token = await persistence.acquire_claim(
        "prepare:transitions:" + identity,
        ClaimKind.PREPARE,
        request.execution,
        attempt,
        required_inputs=(reference,),
        lease_seconds=lease_seconds,
    )
    try:
        result_id = (
            "a2-transitions-"
            + hashlib.sha256(
                json.dumps(
                    (identity, request.execution.value, attempt.value),
                    separators=(",", ":"),
                ).encode()
            ).hexdigest()
        )
        result = StageResult(
            result_id=result_id,
            kind="prepared_transitions",
            schema_version="1",
            execution=request.execution,
            attempt=attempt,
            input_refs=(reference,),
            source_versions=(),
            prepared_versions=(),
            topic_versions=(),
            configuration_version=configuration_version,
            code_version=code_version,
            status=TerminalStatus.COMPLETE,
            acceptable=True,
            semantic_data_ref=persistence.semantic_reference(
                result_id + "-data",
                "prepared_transitions",
                "1",
                value,
            ),
        )
        await persistence.append_result_with_data(result, value, claim=token)
        refs = (ResultRef(result_id, "prepared_transitions", "1"),)
        await _finish_uninterrupted(
            persistence,
            token,
            TerminalStatus.COMPLETE,
            accepted_preparation_results=refs,
        )
        return refs
    except asyncio.CancelledError:
        await _finish_uninterrupted(
            persistence,
            token,
            TerminalStatus.CANCELLED,
            suppress_stale=True,
            preserve_cancellation=True,
        )
        raise
    except Exception:
        await _finish_uninterrupted(
            persistence,
            token,
            TerminalStatus.FAILED,
            suppress_stale=True,
        )
        raise
