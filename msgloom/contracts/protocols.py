"""Typed extension boundaries with no CLI, SDK, or ORM types."""

from __future__ import annotations

from typing import Protocol

from msgloom.contracts.models import (
    OperationOutcome,
    OperationRequest,
    StageResult,
    VersionRef,
)


class OutcomePersistence(Protocol):
    """Persist terminal Application outcomes."""

    async def save_outcome(self, outcome: OperationOutcome) -> None:
        """Save one immutable terminal outcome."""
        ...


class OperationHandler(Protocol):
    """Execute one already-admitted Phase 1 capability."""

    async def run(self, request: OperationRequest) -> OperationOutcome:
        """Run and return a terminal outcome."""
        ...


class EvidenceReader(Protocol):
    """Read exact saved evidence through a provider-neutral reference."""

    async def read(self, reference: VersionRef) -> bytes:
        """Return already-saved evidence bytes for an exact reference."""
        ...


class ResultProducer(Protocol):
    """Optional producer boundary for a registered stage-result schema."""

    async def produce(self, request: OperationRequest) -> StageResult:
        """Produce one terminal stage result from declared saved inputs."""
        ...
