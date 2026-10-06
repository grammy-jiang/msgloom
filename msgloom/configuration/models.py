"""Closed models for operator-controlled Phase 1 configuration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from msgloom.ai.models import AttemptLimits
from msgloom.contracts import PhaseCapability, VersionRef
from msgloom.preparation import DocumentFormat
from msgloom.preparation.filtering import FilterConfig
from msgloom.preparation.isolation.registry import PRODUCTION_REGISTRY
from msgloom.preparation_pipeline import ParserProfile
from msgloom.reporting import RendererConfig, ReportPolicy
from msgloom.triage import TriageRuleConfig

_PHASE1 = frozenset(
    {
        PhaseCapability.PREPARE,
        PhaseCapability.TRIAGE,
        PhaseCapability.REPORT_BUILD,
        PhaseCapability.REPORT_SUBMIT,
    }
)
_AI_CREDENTIAL_KEYS = frozenset(
    {
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_REGION",
        "AWS_DEFAULT_REGION",
        "AWS_BEARER_TOKEN_BEDROCK",
        "CLAUDE_CODE_USE_BEDROCK",
    }
)
ShortText = Annotated[str, Field(min_length=1, max_length=256)]
JsonObject = dict[str, Any]

_PARSER_PROFILES = {
    DocumentFormat.MIME: "mime-html-v1",
    DocumentFormat.HTML: "mime-html-v1",
    DocumentFormat.TEXT: "mime-html-v1",
    DocumentFormat.JSON: "mime-html-v1",
    DocumentFormat.PDF: "pdf-primary-v1",
    DocumentFormat.DOCX: "word-native-v1",
    DocumentFormat.DOC: "word-native-v1",
    DocumentFormat.XLSX: "excel-primary-v1",
    DocumentFormat.XLSM: "excel-primary-v1",
    DocumentFormat.XLS: "excel-primary-v1",
    DocumentFormat.XLSB: "excel-primary-v1",
    DocumentFormat.ODS: "excel-primary-v1",
}
_EXCEL_FORMATS = frozenset(
    {
        DocumentFormat.XLSX,
        DocumentFormat.XLSM,
        DocumentFormat.XLS,
        DocumentFormat.XLSB,
        DocumentFormat.ODS,
    }
)
_EXCEL_SETTING_KEYS = frozenset(
    {"include_hidden_sheets", "include_hidden_rows", "include_hidden_columns"}
)
_EXCEL_BOOL_VALUES = frozenset({"1", "true", "yes", "0", "false", "no"})


def _validate_parser_profile(profile: ParserProfile) -> None:
    """Require the exact reviewed production parser and reusable profile."""
    entry = PRODUCTION_REGISTRY.resolve(profile.format)
    if profile.parser != entry.identity:
        raise ValueError("parser identity is not registered for the selected format")
    if profile.config.profile != _PARSER_PROFILES[profile.format]:
        raise ValueError("parser profile is not supported for the selected format")
    settings = dict(profile.config.settings)
    if profile.format not in _EXCEL_FORMATS:
        if settings:
            raise ValueError("selected parser profile does not accept settings")
        return
    if set(settings) - _EXCEL_SETTING_KEYS:
        raise ValueError("spreadsheet parser setting is not supported")
    if any(
        value.strip().lower() not in _EXCEL_BOOL_VALUES for value in settings.values()
    ):
        raise ValueError("spreadsheet parser setting value is invalid")


class SecretPurpose(StrEnum):
    """Keep provider credential surfaces separated by execution purpose."""

    SOURCE = "source"
    AI = "ai"
    REPORT = "report"


class SecretSource(StrEnum):
    """Approved private credential locations."""

    ENVIRONMENT = "environment"
    MOUNTED_FILE = "mounted-file"


class _ClosedModel(BaseModel):
    """Reject undeclared configuration while keeping settings-source parsing."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class StorageSettings(_ClosedModel):
    """Name the one Phase 1 SQLite persistence file."""

    sqlite_path: Path


class SourceSettings(_ClosedModel):
    """Name bounded saved A1 catalog/evidence inputs for A2."""

    catalog_path: Path
    evidence_roots: Annotated[tuple[Path, ...], Field(min_length=1, max_length=16)]
    limits: JsonObject = Field(default_factory=dict)
    secret_binding_ids: Annotated[tuple[ShortText, ...], Field(max_length=16)] = ()

    @field_validator("evidence_roots")
    @classmethod
    def _unique_roots(cls, value: tuple[Path, ...]) -> tuple[Path, ...]:
        if len(value) != len(set(value)):
            raise ValueError("source evidence roots must be unique")
        return value


class AdmissionSettings(_ClosedModel):
    """Bind a trusted caller/authority to Phase 1 capabilities."""

    caller: ShortText
    authority_ref: ShortText
    capabilities: Annotated[
        tuple[PhaseCapability, ...], Field(min_length=1, max_length=4)
    ]

    @field_validator("capabilities")
    @classmethod
    def _phase1_only(
        cls, value: tuple[PhaseCapability, ...]
    ) -> tuple[PhaseCapability, ...]:
        if len(value) != len(set(value)):
            raise ValueError("trusted capabilities must be unique")
        if set(value) - _PHASE1:
            raise ValueError("unsupported capability is not available in Phase 1")
        return value


class SecretBinding(_ClosedModel):
    """Retain only a reference to credential material, never its value."""

    binding_id: ShortText
    purpose: SecretPurpose
    logical_name: ShortText
    source: SecretSource
    locator: ShortText

    @model_validator(mode="after")
    def _ai_key_is_closed(self) -> SecretBinding:
        if self.purpose is SecretPurpose.AI and self.logical_name not in (
            _AI_CREDENTIAL_KEYS
        ):
            raise ValueError("AI credential logical name is not approved")
        if (
            self.source is SecretSource.MOUNTED_FILE
            and Path(self.locator).name != self.locator
        ):
            raise ValueError("mounted secret locator must be one file name")
        return self


class PreparationIntakeTarget(_ClosedModel):
    """Pin stable cursor identity and finite per-target scheduling budgets."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    source_id: ShortText
    stream: Literal["outlook_mail", "outlook_calendar", "todo", "contacts", "onedrive"]
    consumer_id: ShortText
    max_entries: Annotated[int, Field(ge=1, le=1000)] = 100
    max_pending_worksets: Annotated[int, Field(ge=1, le=100)] = 10

    @field_validator("source_id", "consumer_id")
    @classmethod
    def _identity(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("intake identity must be non-empty")
        return value


class PreparationSettings(_ClosedModel):
    """Reusable A2 semantics and finite producer budgets."""

    intake_targets: Annotated[
        tuple[PreparationIntakeTarget, ...], Field(max_length=32)
    ] = ()
    filter_config: FilterConfig
    parser_profiles: Annotated[tuple[ParserProfile, ...], Field(max_length=16)]
    execution_timeout_seconds: Annotated[float, Field(gt=0.0, le=600.0)] = 120.0
    claim_lease_seconds: Annotated[float, Field(gt=1.0, le=900.0)] = 180.0
    max_records: Annotated[int, Field(ge=1, le=1000)] = 100
    max_total_selected_bytes: Annotated[int, Field(ge=1, le=512 * 1024 * 1024)] = (
        64 * 1024 * 1024
    )
    max_derived_bytes: Annotated[int, Field(ge=1, le=64 * 1024 * 1024)] = (
        16 * 1024 * 1024
    )
    max_total_derived_bytes: Annotated[int, Field(ge=1, le=256 * 1024 * 1024)] = (
        32 * 1024 * 1024
    )
    max_total_parser_output_bytes: Annotated[int, Field(ge=1, le=256 * 1024 * 1024)] = (
        32 * 1024 * 1024
    )

    @field_validator("filter_config", mode="before")
    @classmethod
    def _strict_filter(cls, value: object) -> FilterConfig:
        return _strict_model(FilterConfig, value)

    @field_validator("parser_profiles", mode="before")
    @classmethod
    def _strict_profiles(cls, value: object) -> tuple[ParserProfile, ...]:
        if not isinstance(value, (list, tuple)):
            raise TypeError("parser profiles must be a finite sequence")
        return tuple(_strict_model(ParserProfile, item) for item in value)

    @model_validator(mode="after")
    def _usable_operation(self) -> PreparationSettings:
        keys = tuple(
            (t.source_id, t.stream, t.consumer_id) for t in self.intake_targets
        )
        if len(set(keys)) != len(keys):
            raise ValueError("intake targets must be unique")
        if any(t.max_entries > self.max_records for t in self.intake_targets):
            raise ValueError("intake entry budget exceeds preparation max_records")
        formats = tuple(profile.format for profile in self.parser_profiles)
        if len(formats) != len(set(formats)):
            raise ValueError("parser profiles must have unique formats")
        for profile in self.parser_profiles:
            _validate_parser_profile(profile)
        if self.max_derived_bytes > self.max_total_derived_bytes:
            raise ValueError("per-artifact derived bound exceeds aggregate bound")
        if self.claim_lease_seconds <= self.execution_timeout_seconds + 1.0:
            raise ValueError("claim lease must exceed execution budget by one second")
        return self


class AIRuntimeSettings(_ClosedModel):
    """Paths used only when the CLI later constructs the isolated AI runner."""

    python_executable: Path
    bubblewrap_executable: Path
    runtime_roots: Annotated[tuple[Path, ...], Field(min_length=1, max_length=16)]
    cli_path: Path
    storage_root: Path
    termination_grace_seconds: Annotated[float, Field(gt=0.0, le=30.0)] = 1.0


class TriageSettings(_ClosedModel):
    """Reusable A3 policy, selections, paths, and operation ceilings."""

    filter_config: FilterConfig
    rule_config: TriageRuleConfig
    input_config: JsonObject
    working_context: JsonObject
    prompt_ref: VersionRef
    prompt_file: Path
    model_ref: VersionRef
    model_identifier: ShortText
    output_schema_ref: VersionRef
    output_schema_file: Path
    attempt_limits: AttemptLimits
    runtime: AIRuntimeSettings
    secret_binding_ids: Annotated[
        tuple[ShortText, ...], Field(min_length=1, max_length=16)
    ]
    lease_seconds: Annotated[float, Field(gt=0.0, le=900.0)]
    operation_timeout_seconds: Annotated[float, Field(gt=0.0, le=600.0)]
    cleanup_margin_seconds: Annotated[float, Field(gt=0.0, le=60.0)]
    max_upstream_results: Annotated[int, Field(ge=1, le=1024)]
    max_upstream_bytes: Annotated[int, Field(ge=1, le=256 * 1024 * 1024)]
    max_parts: Annotated[int, Field(ge=1, le=256)]

    @field_validator("filter_config", mode="before")
    @classmethod
    def _strict_filter(cls, value: object) -> FilterConfig:
        return _strict_model(FilterConfig, value)

    @field_validator("rule_config", mode="before")
    @classmethod
    def _strict_rules(cls, value: object) -> TriageRuleConfig:
        return _strict_model(TriageRuleConfig, value)

    @field_validator("prompt_ref", "model_ref", "output_schema_ref", mode="before")
    @classmethod
    def _strict_refs(cls, value: object) -> VersionRef:
        return _strict_dataclass(VersionRef, value)

    @field_validator("attempt_limits", mode="before")
    @classmethod
    def _strict_limits(cls, value: object) -> AttemptLimits:
        return _strict_dataclass(AttemptLimits, value)

    @model_validator(mode="after")
    def _usable_operation(self) -> TriageSettings:
        acceptance = self.operation_timeout_seconds - self.cleanup_margin_seconds
        if acceptance <= 0:
            raise ValueError("operation timeout must leave a cleanup margin")
        if self.attempt_limits.timeout_seconds > acceptance:
            raise ValueError("attempt timeout exceeds operation acceptance budget")
        if self.lease_seconds < self.operation_timeout_seconds:
            raise ValueError("claim lease must cover the total operation budget")
        return self


class ReportTransportSettings(_ClosedModel):
    """Reference one manager-integrated report transport without constructing it."""

    transport_ref: VersionRef
    secret_binding_ids: Annotated[
        tuple[ShortText, ...], Field(min_length=1, max_length=8)
    ]

    @field_validator("transport_ref", mode="before")
    @classmethod
    def _strict_ref(cls, value: object) -> VersionRef:
        return _strict_dataclass(VersionRef, value)


class ReportSettings(_ClosedModel):
    """Reusable A5 report policy, renderer, and finite build limits."""

    policy: ReportPolicy
    renderer: RendererConfig
    max_input_bytes: Annotated[int, Field(ge=1, le=64 * 1024 * 1024)]
    timeout_seconds: Annotated[float, Field(gt=0.0, le=300.0)]
    claim_lease_seconds: Annotated[float, Field(gt=1.0, le=600.0)]
    transport: ReportTransportSettings | None = None

    @field_validator("policy", mode="before")
    @classmethod
    def _strict_policy(cls, value: object) -> ReportPolicy:
        return _strict_model(ReportPolicy, value)

    @field_validator("renderer", mode="before")
    @classmethod
    def _strict_renderer(cls, value: object) -> RendererConfig:
        return _strict_model(RendererConfig, value)

    @model_validator(mode="after")
    def _usable_operation(self) -> ReportSettings:
        if self.claim_lease_seconds < self.timeout_seconds + 1.0:
            raise ValueError("claim lease must exceed the finite operation budget")
        return self


class OperatorSettings(BaseSettings):
    """Raw pydantic-settings surface before path and cross-section validation."""

    model_config = SettingsConfigDict(
        extra="forbid",
        env_prefix="MSGLOOM_CONFIG__",
        env_nested_delimiter="__",
        env_ignore_empty=True,
        env_file=None,
        frozen=True,
    )

    code_version: ShortText
    storage: StorageSettings
    admissions: Annotated[
        tuple[AdmissionSettings, ...], Field(min_length=1, max_length=32)
    ]
    secrets: Annotated[tuple[SecretBinding, ...], Field(max_length=32)] = ()
    source: SourceSettings | None = None
    preparation: PreparationSettings | None = None
    triage: TriageSettings | None = None
    report: ReportSettings | None = None

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Apply the project precedence and intentionally omit dotenv."""
        from msgloom.configuration.sources import (
            MappingSettingsSource,
            config_values,
            mounted_values,
        )

        del dotenv_settings, file_secret_settings
        return (
            init_settings,
            env_settings,
            MappingSettingsSource(settings_cls, mounted_values()),
            MappingSettingsSource(settings_cls, config_values()),
        )

    @model_validator(mode="after")
    def _closed_bindings(self) -> OperatorSettings:
        admission_keys = tuple(
            (item.caller, item.authority_ref) for item in self.admissions
        )
        if len(admission_keys) != len(set(admission_keys)):
            raise ValueError("trusted admissions must be unique")
        binding_ids = tuple(item.binding_id for item in self.secrets)
        if len(binding_ids) != len(set(binding_ids)):
            raise ValueError("secret binding identities must be unique")
        return self


@dataclass(frozen=True, slots=True)
class ConfigurationSnapshot:
    """Deterministic redacted snapshot safe for status/config inspection."""

    version: str
    payload: str


def _strict_model[T: BaseModel](model: type[T], value: object) -> T:
    from msgloom.configuration.validation import strict_model

    return strict_model(model, value)


def _strict_dataclass[T](model: type[T], value: object) -> T:
    from msgloom.configuration.validation import strict_dataclass

    return strict_dataclass(model, value)
