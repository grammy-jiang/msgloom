"""Validated immutable composition data for later CLI construction."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from urllib.parse import quote

from sqlalchemy import URL

from msgloom.ai.models import AttemptLimits
from msgloom.ai.policy import RuntimeIsolation, TrustedPolicy
from msgloom.contracts import (
    AttemptIdentity,
    PhaseCapability,
    TrustedAdmission,
    VersionRef,
)
from msgloom.preparation.filtering import FilterConfig
from msgloom.preparation_pipeline import (
    ParserProfile,
    PreparationMode,
    PreparationPlan,
    SelectionPlan,
)
from msgloom.reporting import RendererConfig, ReportHandlerConfig, ReportPolicy
from msgloom.sources import SavedSourceReaderConfig
from msgloom.triage import TriageRuleConfig
from msgloom.triage_input import TriageInputConfig, TrustedInputVersions
from msgloom.triage_pipeline import TriageProducerConfig, TriageReplayPlan
from msgloom.working_context import WorkingContextConfig

from .errors import ConfigurationError, ConfigurationErrorCode
from .models import (
    AIRuntimeSettings,
    ConfigurationSnapshot,
    OperatorSettings,
    PreparationIntakeTarget,
    SecretBinding,
)
from .validation import strict_model


@dataclass(frozen=True, slots=True)
class PreparationOperationData:
    """Reusable A2 configuration plus a strict per-run plan builder."""

    filter_config: FilterConfig
    parser_profiles: tuple[ParserProfile, ...]
    configuration_version: str
    code_version: str
    execution_timeout_seconds: float
    claim_lease_seconds: float
    max_records: int
    max_total_selected_bytes: int
    max_derived_bytes: int
    max_total_derived_bytes: int
    max_total_parser_output_bytes: int

    intake_targets: tuple[PreparationIntakeTarget, ...] = ()

    def plan(
        self,
        *,
        mode: PreparationMode,
        attempt: AttemptIdentity,
        selections: tuple[SelectionPlan, ...],
    ) -> PreparationPlan:
        """Build the exact finite A2 plan from caller-supplied selections."""
        return PreparationPlan(
            mode=mode,
            attempt=attempt,
            selections=selections,
            filter_config=self.filter_config,
            parser_profiles=self.parser_profiles,
            configuration_version=self.configuration_version,
            code_version=self.code_version,
            execution_timeout_seconds=self.execution_timeout_seconds,
            claim_lease_seconds=self.claim_lease_seconds,
            max_records=self.max_records,
            max_total_selected_bytes=self.max_total_selected_bytes,
            max_derived_bytes=self.max_derived_bytes,
            max_total_derived_bytes=self.max_total_derived_bytes,
            max_total_parser_output_bytes=self.max_total_parser_output_bytes,
        )


@dataclass(frozen=True, slots=True)
class TriageOperationData:
    """Reusable A3 data with exact prompt/schema bytes already validated."""

    filter_config: FilterConfig
    rule_config: TriageRuleConfig
    input_config: TriageInputConfig
    versions: TrustedInputVersions
    working_context_config: WorkingContextConfig
    prompt_text: str
    trusted_policy: TrustedPolicy
    attempt_limits: AttemptLimits
    runtime: AIRuntimeSettings
    secret_binding_ids: tuple[str, ...]
    configuration_version: str
    code_version: str
    lease_seconds: float
    operation_timeout_seconds: float
    cleanup_margin_seconds: float
    max_upstream_results: int
    max_upstream_bytes: int
    max_parts: int

    def producer_config(
        self,
        *,
        plan: TriageReplayPlan,
        capture_time: datetime | None,
        expected_parameters: tuple[tuple[str, str], ...],
        claim_key: str,
    ) -> TriageProducerConfig:
        """Build one finite A3 producer configuration without starting a runner."""
        return TriageProducerConfig(
            plan=plan,
            filter_config=self.filter_config,
            rule_config=self.rule_config,
            input_config=self.input_config,
            versions=self.versions,
            working_context_config=(
                self.working_context_config if plan.mode.value == "live" else None
            ),
            capture_time=capture_time,
            prompt_text=self.prompt_text,
            trusted_policy=self.trusted_policy,
            attempt_limits=self.attempt_limits,
            expected_parameters=expected_parameters,
            claim_key=claim_key,
            configuration_version=self.configuration_version,
            code_version=self.code_version,
            lease_seconds=self.lease_seconds,
            operation_timeout_seconds=self.operation_timeout_seconds,
            cleanup_margin_seconds=self.cleanup_margin_seconds,
            max_upstream_results=self.max_upstream_results,
            max_upstream_bytes=self.max_upstream_bytes,
            max_parts=self.max_parts,
        )

    def runtime_isolation(self, credentials: Mapping[str, str]) -> RuntimeIsolation:
        """Construct execution-only AI isolation from resolved credentials."""
        return RuntimeIsolation(
            python_executable=self.runtime.python_executable,
            bubblewrap_executable=self.runtime.bubblewrap_executable,
            runtime_roots=self.runtime.runtime_roots,
            cli_path=self.runtime.cli_path,
            credentials=credentials,
            storage_root=self.runtime.storage_root,
            termination_grace_seconds=self.runtime.termination_grace_seconds,
        )


@dataclass(frozen=True, slots=True)
class ReportOperationData:
    """Reusable A5 build data and a strict per-run config builder."""

    policy: ReportPolicy
    renderer: RendererConfig
    configuration_version: str
    code_version: str
    max_input_bytes: int
    timeout_seconds: float
    claim_lease_seconds: float

    def handler_config(
        self,
        *,
        report_ref: VersionRef,
        result_id: str,
        semantic_data_id: str,
        selection_result_id: str,
        selection_semantic_data_id: str,
        attempt: AttemptIdentity,
        expected_parameters: tuple[tuple[str, str], ...],
    ) -> ReportHandlerConfig:
        """Build exact finite A5 handler configuration for one report."""
        return ReportHandlerConfig(
            report_ref=report_ref,
            result_id=result_id,
            semantic_data_id=semantic_data_id,
            selection_result_id=selection_result_id,
            selection_semantic_data_id=selection_semantic_data_id,
            max_input_bytes=self.max_input_bytes,
            attempt=attempt,
            code_version=self.code_version,
            expected_parameters=expected_parameters,
            timeout_seconds=self.timeout_seconds,
            claim_lease_seconds=self.claim_lease_seconds,
        )


@dataclass(frozen=True, slots=True)
class ReportSubmitOperationData:
    """Trusted report-transport reference without constructing the transport."""

    transport_ref: VersionRef
    secret_binding_ids: tuple[str, ...]
    policy_ref: VersionRef


OperationData = (
    PreparationOperationData
    | TriageOperationData
    | ReportOperationData
    | ReportSubmitOperationData
)


class OperatorConfiguration:
    """Small immutable public API consumed by later CLI composition."""

    __slots__ = (
        "_admissions",
        "_code_version",
        "_database_path",
        "_operations",
        "_secret_bindings",
        "_snapshot",
        "_source_reader",
    )

    def __init__(
        self,
        *,
        settings: OperatorSettings,
        snapshot: ConfigurationSnapshot,
        source_reader: SavedSourceReaderConfig | None,
        operations: Mapping[PhaseCapability, OperationData],
    ) -> None:
        self._snapshot = snapshot
        self._code_version = settings.code_version
        self._database_path = settings.storage.sqlite_path
        self._admissions = tuple(
            TrustedAdmission(
                caller=item.caller,
                authority_ref=item.authority_ref,
                capabilities=frozenset(item.capabilities),
            )
            for item in settings.admissions
        )
        self._secret_bindings = MappingProxyType(
            {item.binding_id: item for item in settings.secrets}
        )
        self._source_reader = source_reader
        self._operations = MappingProxyType(dict(operations))

    def __repr__(self) -> str:
        return (
            f"OperatorConfiguration(version={self._snapshot.version!r}, redacted=True)"
        )

    @property
    def version(self) -> str:
        """Return the deterministic redacted configuration version."""
        return self._snapshot.version

    @property
    def code_version(self) -> str:
        """Return the code/build version bound into operation results."""
        return self._code_version

    @property
    def database_url(self) -> str:
        """Return a SQLite URI preserving the exact configured file identity."""
        encoded = quote(str(self._database_path), safe="/")
        url = URL.create(
            "sqlite",
            database=f"file:{encoded}",
            query={"uri": "true"},
        )
        return url.render_as_string(hide_password=False)

    @property
    def admissions(self) -> tuple[TrustedAdmission, ...]:
        """Return trusted caller/authority bindings for Application."""
        return self._admissions

    def snapshot(self) -> ConfigurationSnapshot:
        """Return the immutable privacy-safe inspection snapshot."""
        return self._snapshot

    def source_reader_config(self) -> SavedSourceReaderConfig:
        """Return validated saved-A1 reader configuration without opening it."""
        if self._source_reader is None:
            raise ConfigurationError(ConfigurationErrorCode.CONFIG_UNAVAILABLE)
        return self._source_reader

    def operation(self, capability: PhaseCapability) -> OperationData:
        """Return validated Phase 1 data or a fixed unavailable gate."""
        if capability not in {
            PhaseCapability.PREPARE,
            PhaseCapability.TRIAGE,
            PhaseCapability.REPORT_BUILD,
            PhaseCapability.REPORT_SUBMIT,
        }:
            raise ConfigurationError(ConfigurationErrorCode.CONFIG_UNAVAILABLE)
        try:
            return self._operations[capability]
        except KeyError:
            raise ConfigurationError(
                ConfigurationErrorCode.CONFIG_UNAVAILABLE
            ) from None

    def secret_binding(self, binding_id: str) -> SecretBinding:
        """Return one private execution reference without resolving its value."""
        try:
            return self._secret_bindings[binding_id]
        except KeyError:
            raise ConfigurationError(
                ConfigurationErrorCode.SECRET_UNAVAILABLE
            ) from None


def build_working_context(
    raw: dict[str, object], base_dir: Path
) -> WorkingContextConfig:
    """Resolve selected context paths, then use strict domain validation."""
    value = dict(raw)
    selected = value.get("selected_files")
    if isinstance(selected, list):
        resolved: list[object] = []
        for item in selected:
            if not isinstance(item, dict):
                resolved.append(item)
                continue
            copy = dict(item)
            if isinstance(path := copy.get("path"), str):
                copy["path"] = str(resolve_path(base_dir, Path(path)))
            resolved.append(copy)
        value["selected_files"] = resolved
    roots = value.get("allowed_roots")
    if isinstance(roots, list):
        value["allowed_roots"] = [
            str(resolve_path(base_dir, Path(item))) if isinstance(item, str) else item
            for item in roots
        ]
    return strict_model(WorkingContextConfig, value)


def build_input_config(
    raw: dict[str, object], configuration_ref: VersionRef
) -> TriageInputConfig:
    """Inject exact configuration version before strict domain validation."""
    if "version" in raw:
        raise ConfigurationError(ConfigurationErrorCode.INVALID_INPUT)
    value = dict(raw)
    value["version"] = {
        "kind": configuration_ref.kind,
        "identity": configuration_ref.identity,
        "version": configuration_ref.version,
    }
    return strict_model(TriageInputConfig, value)


def resolve_path(base_dir: Path, path: Path) -> Path:
    """Resolve one operator path relative to the explicit TOML file."""
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()
