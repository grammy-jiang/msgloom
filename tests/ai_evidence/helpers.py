"""Synthetic fixtures for durable AI evidence tests."""

from __future__ import annotations

from pathlib import Path

from msgloom.ai import AnalysisAttempt, AttemptLimits, TrustedPolicy
from msgloom.ai_evidence import AI_EVIDENCE_CODECS
from msgloom.contracts import (
    AttemptIdentity,
    ExecutionIdentity,
    ResultRef,
    ResultSchemaRegistry,
    StageResult,
    TerminalStatus,
    VersionRef,
)
from msgloom.persistence import Phase1Persistence, SemanticDataRegistry


class SeedCodec:
    """Tiny synthetic prerequisite codec used only by evidence tests."""

    kind = "seed"
    schema_version = "1"
    max_bytes = 64

    def encode(self, value: object) -> bytes:
        """Encode the only accepted synthetic prerequisite."""
        if value != "synthetic-seed":
            raise TypeError("invalid synthetic seed")
        return b'{"value":"synthetic-seed"}'

    def decode(self, payload: bytes) -> object:
        """Decode the only accepted synthetic prerequisite."""
        if payload != b'{"value":"synthetic-seed"}':
            raise ValueError("invalid synthetic seed")
        return "synthetic-seed"


def registries() -> tuple[ResultSchemaRegistry, SemanticDataRegistry]:
    """Return explicit test-only result and semantic registry composition."""
    schemas = frozenset(
        {("seed", "1")}
        | {(codec.kind, codec.schema_version) for codec in AI_EVIDENCE_CODECS}
    )
    return (
        ResultSchemaRegistry(schemas, schemas),
        SemanticDataRegistry((SeedCodec(), *AI_EVIDENCE_CODECS)),
    )


async def open_store(path: Path) -> Phase1Persistence:
    """Open a real Phase1Persistence with explicit evidence schemas."""
    result_registry, semantic_registry = registries()
    return await Phase1Persistence.open(
        f"sqlite:///{path}",
        registry=result_registry,
        semantic_registry=semantic_registry,
    )


async def save_seed(store: Phase1Persistence) -> ResultRef:
    """Persist one required synthetic input with real semantic bytes."""
    reference = store.semantic_reference("seed-data", "seed", "1", "synthetic-seed")
    result = StageResult(
        result_id="seed-result",
        kind="seed",
        schema_version="1",
        execution=ExecutionIdentity("exec-seed"),
        attempt=AttemptIdentity("attempt-seed"),
        input_refs=(),
        source_versions=(),
        prepared_versions=(),
        topic_versions=(),
        configuration_version="config-seed",
        code_version="code-seed",
        status=TerminalStatus.COMPLETE,
        acceptable=True,
        semantic_data_ref=reference,
    )
    await store.append_result_with_data(result, "synthetic-seed")
    return ResultRef("seed-result", "seed", "1")


def analysis_attempt(
    attempt_id: str = "attempt-ai-1",
    *,
    input_text: str = "synthetic input",
    max_input_bytes: int = 4096,
    max_output_bytes: int = 4096,
    max_trace_event_bytes: int = 4096,
) -> AnalysisAttempt:
    """Build one bounded public AI request."""
    return AnalysisAttempt(
        attempt=AttemptIdentity(attempt_id),
        input_refs=(VersionRef("prepared", "prepared-1", "v1"),),
        context_ref=VersionRef("working_context", "context-1", "v1"),
        prompt_ref=VersionRef("prompt", "triage-prompt", "v1"),
        schema_ref=VersionRef("schema", "triage-output", "v1"),
        model_ref=VersionRef("model", "analysis-model", "v1"),
        input_text=input_text,
        context_text="synthetic context",
        prompt_text="Return synthetic structured output.",
        limits=AttemptLimits(
            timeout_seconds=5.0,
            max_input_bytes=max_input_bytes,
            max_context_bytes=4096,
            max_prompt_bytes=4096,
            max_output_bytes=max_output_bytes,
            max_trace_events=8,
            max_trace_event_bytes=max_trace_event_bytes,
            max_turns=2,
            max_tokens=1024,
        ),
    )


def trusted_policy(request: AnalysisAttempt) -> TrustedPolicy:
    """Resolve only the request's declared schema and model references."""
    return TrustedPolicy(
        schemas={
            request.schema_ref: {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
            }
        },
        models={request.model_ref: "synthetic-model"},
    )
