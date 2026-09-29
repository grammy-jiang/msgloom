"""Pure handler-handoff helpers for exact saved input part bytes."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from msgloom.contracts import SemanticDataRef

from .models import PartState, TriageInputSnapshot
from .split import encode_part


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")


class SavedPartPayload(_FrozenModel):
    """Exact canonical bytes/reference the handler must persist before AI use."""

    reference: SemanticDataRef
    payload: bytes


class PartExecution(_FrozenModel):
    """Retained execution state for one exact saved input part."""

    reference: SemanticDataRef
    state: PartState
    failure_code: Annotated[str | None, Field(max_length=64)] = None

    @model_validator(mode="after")
    def _failure_shape(self) -> PartExecution:
        if self.state is PartState.FAILED:
            if not self.failure_code or not self.failure_code.strip():
                raise ValueError("failed part requires a bounded failure code")
        elif self.failure_code is not None:
            raise ValueError("only failed parts may carry a failure code")
        return self


def _validated_snapshot(snapshot: TriageInputSnapshot) -> TriageInputSnapshot:
    from .codec import TriageInputCodec

    try:
        codec = TriageInputCodec()
        return codec.decode(codec.encode(snapshot))
    except (TypeError, ValueError):
        raise ValueError("triage input snapshot failed handoff validation") from None


def _validated_states(
    states: tuple[PartExecution, ...],
) -> tuple[PartExecution, ...]:
    checked = []
    try:
        for item in states:
            payload = item.model_dump_json(round_trip=True, warnings="error")
            checked.append(PartExecution.model_validate_json(payload, strict=True))
    except (AttributeError, TypeError, ValueError, ValidationError):
        raise ValueError("part execution states failed validation") from None
    return tuple(checked)


def saved_part_payloads(snapshot: TriageInputSnapshot) -> tuple[SavedPartPayload, ...]:
    """Return exact bytes that must be saved before an AI attempt consumes them."""
    checked = _validated_snapshot(snapshot)
    return tuple(
        SavedPartPayload(
            reference=envelope.reference,
            payload=encode_part(envelope.part),
        )
        for envelope in checked.parts
    )


def initial_part_states(snapshot: TriageInputSnapshot) -> tuple[PartExecution, ...]:
    """Return a pending state for every exact part in canonical snapshot order."""
    checked = _validated_snapshot(snapshot)
    return tuple(
        PartExecution(reference=item.reference, state=PartState.PENDING)
        for item in checked.parts
    )


def validate_parent_part_states(
    snapshot: TriageInputSnapshot,
    states: tuple[PartExecution, ...],
) -> bool:
    """Validate exact states and allow combination only for complete input."""
    checked = _validated_snapshot(snapshot)
    checked_states = _validated_states(states)
    expected = tuple(item.reference for item in checked.parts)
    actual = tuple(item.reference for item in checked_states)
    if len(actual) != len(set(actual)) or set(actual) != set(expected):
        raise ValueError("part execution states must exactly cover snapshot parts")
    if not checked.complete or not expected:
        return False
    by_ref = {item.reference: item for item in checked_states}
    return all(by_ref[reference].state is PartState.COMPLETE for reference in expected)
