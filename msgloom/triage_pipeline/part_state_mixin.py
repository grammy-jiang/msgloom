"""Claim-fenced terminal per-part state publication for A3."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from msgloom.contracts import ResultRef, TerminalStatus
from msgloom.persistence import Phase1Persistence
from msgloom.triage_input import PART_KIND, PART_SCHEMA_VERSION, PartState

from .codecs import (
    TRIAGE_PART_STATE_KIND,
    TRIAGE_PART_STATE_SCHEMA_VERSION,
    TriagePartState,
)
from .common import ensure_acceptance_time, record_result, result_ref, stable_id
from .models import TriageProducerConfig


class _TriagePartStateMixin:
    """Publish one exact terminal state for an owned semantic input part."""

    _persistence: Phase1Persistence
    _config: TriageProducerConfig
    _stage: Callable[..., Any]
    _semantic_ref: Callable[..., Any]

    async def _save_part_state(
        self, request, claim, part, attempt, state, terminal, failure_code, inputs
    ) -> ResultRef:
        part_ref = await self._semantic_ref(
            stable_id(
                "triage-part-data",
                request.execution.value,
                part.part_id,
                part.versions.prompt.version,
                self._config.semantic_fingerprint(),
            ),
            PART_KIND,
            PART_SCHEMA_VERSION,
            part,
        )
        value = TriagePartState(
            part_ref=part_ref,
            attempt=attempt,
            state=state,
            ai_response_ref=terminal,
            failure_code=failure_code,
        )
        result_id = stable_id(
            "triage-part-state",
            request.execution.value,
            part.part_id,
            attempt.value,
            self._config.semantic_fingerprint(),
        )
        semantic = await self._semantic_ref(
            f"{result_id}:data",
            TRIAGE_PART_STATE_KIND,
            TRIAGE_PART_STATE_SCHEMA_VERSION,
            value,
        )
        result = self._stage(
            request,
            attempt,
            result_id,
            TRIAGE_PART_STATE_KIND,
            (*inputs, terminal),
            tuple(
                sorted(
                    {item.source_ref for item in part.fragments},
                    key=lambda ref: (ref.kind, ref.identity, ref.version),
                )
            ),
            semantic=semantic,
            working_context=part.working_context_ref,
            acceptable=state is PartState.COMPLETE,
            status=(
                TerminalStatus.COMPLETE
                if state is PartState.COMPLETE
                else TerminalStatus.FAILED
            ),
        )
        ensure_acceptance_time()
        await self._persistence.append_result_with_data(result, value, claim=claim)
        return record_result(result_ref(result))
