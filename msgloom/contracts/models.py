"""Immutable provider-neutral operation and result contracts."""

from __future__ import annotations

from dataclasses import dataclass
from string import hexdigits

from msgloom.contracts.enums import (
    ClaimKind,
    ExternalEffectState,
    PhaseCapability,
    TerminalStatus,
)


def _require_text(value: str, field: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"{field} must be non-empty")


@dataclass(frozen=True, slots=True)
class ExecutionIdentity:
    """Stable identity for one explicitly requested application execution."""

    value: str

    def __post_init__(self) -> None:
        _require_text(self.value, "execution identity")


@dataclass(frozen=True, slots=True)
class AttemptIdentity:
    """Identity for one processing attempt within an execution."""

    value: str

    def __post_init__(self) -> None:
        _require_text(self.value, "attempt identity")


@dataclass(frozen=True, slots=True)
class VersionRef:
    """Reference an exact version without importing provider or ORM types."""

    kind: str
    identity: str
    version: str

    def __post_init__(self) -> None:
        _require_text(self.kind, "version reference kind")
        _require_text(self.identity, "version reference identity")
        _require_text(self.version, "version reference version")


@dataclass(frozen=True, slots=True)
class ResultRef:
    """Reference one immutable stage result and its required schema."""

    result_id: str
    kind: str
    schema_version: str

    def __post_init__(self) -> None:
        _require_text(self.result_id, "result reference identity")
        _require_text(self.kind, "result reference kind")
        _require_text(self.schema_version, "result reference schema version")


@dataclass(frozen=True, slots=True)
class SemanticDataRef:
    """Reference immutable validated semantic data by schema and integrity."""

    data_id: str
    kind: str
    schema_version: str
    sha256: str
    byte_count: int

    def __post_init__(self) -> None:
        _require_text(self.data_id, "semantic data identity")
        _require_text(self.kind, "semantic data kind")
        _require_text(self.schema_version, "semantic data schema version")
        if len(self.sha256) != 64 or any(c not in hexdigits for c in self.sha256):
            raise ValueError("semantic data sha256 must be 64 hexadecimal characters")
        if isinstance(self.byte_count, bool) or not isinstance(self.byte_count, int):
            raise TypeError("semantic data byte count must be an integer")
        if self.byte_count < 1:
            raise ValueError("semantic data byte count must be positive")


@dataclass(frozen=True, slots=True)
class Limitation:
    """Expose a bounded reason why available work is incomplete."""

    code: str
    detail: str

    def __post_init__(self) -> None:
        _require_text(self.code, "limitation code")
        _require_text(self.detail, "limitation detail")


@dataclass(frozen=True, slots=True)
class Failure:
    """Expose a safe failure classification without transport exceptions."""

    code: str
    detail: str
    retryable: bool = False

    def __post_init__(self) -> None:
        _require_text(self.code, "failure code")
        _require_text(self.detail, "failure detail")


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """Expose a safe diagnostic retained from a stage attempt."""

    code: str
    detail: str

    def __post_init__(self) -> None:
        _require_text(self.code, "diagnostic code")
        _require_text(self.detail, "diagnostic detail")


@dataclass(frozen=True, slots=True)
class OperationRequest:
    """Request one finite Application capability from any transport."""

    execution: ExecutionIdentity
    caller: str
    capability: PhaseCapability
    target_inputs: tuple[VersionRef, ...] = ()
    authority_ref: str | None = None
    parameters: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.caller, "caller")
        if self.authority_ref is not None:
            _require_text(self.authority_ref, "authority reference")
        for key, _value in self.parameters:
            _require_text(key, "parameter key")


@dataclass(frozen=True, slots=True)
class TrustedAdmission:
    """
    Bind one trusted caller/authority pair to explicitly enabled capabilities.

    Requests carry untrusted names and references. A CLI or other transport
    constructs these bindings only from trusted configuration or approval
    state; an empty binding set is intentionally deny-by-default.
    """

    caller: str
    authority_ref: str
    capabilities: frozenset[PhaseCapability]

    def __post_init__(self) -> None:
        _require_text(self.caller, "trusted caller")
        _require_text(self.authority_ref, "trusted authority reference")
        if not self.capabilities:
            raise ValueError("trusted admission must enable a capability")

    def admits(self, request: OperationRequest) -> bool:
        """Return whether this trusted binding admits the exact request."""
        return (
            request.caller == self.caller
            and request.authority_ref == self.authority_ref
            and request.capability in self.capabilities
        )


@dataclass(frozen=True, slots=True)
class OperationOutcome:
    """Saved terminal outcome returned by the shared Application boundary."""

    execution: ExecutionIdentity
    capability: PhaseCapability
    status: TerminalStatus
    result_refs: tuple[ResultRef, ...] = ()
    limitations: tuple[Limitation, ...] = ()
    failures: tuple[Failure, ...] = ()
    external_effect: ExternalEffectState = ExternalEffectState.NONE


@dataclass(frozen=True, slots=True)
class StageResult:
    """Immutable terminal result with complete replay and lineage versions."""

    result_id: str
    kind: str
    schema_version: str
    execution: ExecutionIdentity
    attempt: AttemptIdentity
    input_refs: tuple[ResultRef, ...]
    source_versions: tuple[VersionRef, ...]
    prepared_versions: tuple[VersionRef, ...]
    topic_versions: tuple[VersionRef, ...]
    configuration_version: str
    code_version: str
    status: TerminalStatus
    acceptable: bool
    rule_version: str | None = None
    prompt_version: str | None = None
    model_identifier: str | None = None
    working_context_version: VersionRef | None = None
    semantic_data_ref: SemanticDataRef | None = None
    exposed_output_ref: VersionRef | None = None
    exposed_diagnostics: tuple[Diagnostic, ...] = ()
    limitations: tuple[Limitation, ...] = ()
    failures: tuple[Failure, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.result_id, "result identity")
        _require_text(self.kind, "result kind")
        _require_text(self.schema_version, "result schema version")
        _require_text(self.configuration_version, "configuration version")
        _require_text(self.code_version, "code version")
        for value, field in (
            (self.rule_version, "rule version"),
            (self.prompt_version, "prompt version"),
            (self.model_identifier, "model identifier"),
        ):
            if value is not None:
                _require_text(value, field)
        if self.acceptable and self.status not in {
            TerminalStatus.COMPLETE,
            TerminalStatus.INCOMPLETE,
        }:
            raise ValueError("only complete or incomplete results can be acceptable")


@dataclass(frozen=True, slots=True)
class ClaimToken:
    """Opaque ownership proof for one durable work claim attempt."""

    claim_key: str
    token: str
    kind: ClaimKind
    execution: ExecutionIdentity
    attempt: AttemptIdentity

    def __post_init__(self) -> None:
        _require_text(self.claim_key, "claim key")
        _require_text(self.token, "claim token")


@dataclass(frozen=True, slots=True)
class ResultSchemaRegistry:
    """Immutable allowlist of result schemas and their semantic-data policy."""

    schemas: frozenset[tuple[str, str]]
    semantic_data_required: frozenset[tuple[str, str]] = frozenset()

    def __post_init__(self) -> None:
        if not self.semantic_data_required <= self.schemas:
            raise ValueError(
                "semantic-data requirements must reference registered result schemas"
            )

    @classmethod
    def phase1(cls) -> ResultSchemaRegistry:
        """Return the result schemas owned by the Phase 1 product path."""
        schemas = frozenset(
            {
                ("prepared", "1"),
                ("filter_result", "1"),
                ("group_result", "1"),
                ("working_context", "1"),
                ("triage_rules", "1"),
                ("triage_input", "1"),
                ("triage", "1"),
                ("report", "1"),
                ("report_submission", "1"),
            }
        )
        return cls(
            schemas,
            frozenset(
                {
                    ("prepared", "1"),
                    ("filter_result", "1"),
                    ("group_result", "1"),
                    ("working_context", "1"),
                    ("triage_rules", "1"),
                    ("triage_input", "1"),
                    ("triage", "1"),
                    ("report", "1"),
                }
            ),
        )

    def with_schema(
        self,
        kind: str,
        schema_version: str,
        *,
        semantic_data_required: bool = False,
    ) -> ResultSchemaRegistry:
        """Return a registry extended by one explicitly reviewed producer schema."""
        _require_text(kind, "result kind")
        _require_text(schema_version, "result schema version")
        key = (kind, schema_version)
        required = self.semantic_data_required
        if semantic_data_required:
            required = required | {key}
        return ResultSchemaRegistry(self.schemas | {key}, required)

    def supports(self, kind: str, schema_version: str) -> bool:
        """Return whether the exact kind/version pair is registered."""
        return (kind, schema_version) in self.schemas

    def requires_data(self, kind: str, schema_version: str) -> bool:
        """Return whether acceptable results require a semantic payload."""
        return (kind, schema_version) in self.semantic_data_required
