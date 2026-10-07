"""Bounded pydantic-settings loader and Phase 1 configuration composition."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from pydantic import ValidationError

from msgloom.ai.policy import TrustedPolicy
from msgloom.contracts import PhaseCapability, VersionRef
from msgloom.sources import SavedSourceReaderConfig
from msgloom.triage_input import TrustedInputVersions

from .composition import (
    OperationData,
    OperatorConfiguration,
    PreparationOperationData,
    ReportOperationData,
    ReportSubmitOperationData,
    TriageOperationData,
    build_input_config,
    build_working_context,
    resolve_path,
)
from .errors import ConfigurationError, ConfigurationErrorCode
from .models import (
    AIRuntimeSettings,
    OperatorSettings,
    SecretBinding,
    SecretPurpose,
    SourceSettings,
    StorageSettings,
    TriageSettings,
)
from .snapshot import make_snapshot
from .sources import bound_sources
from .universal import (
    MAX_CONFIG_BYTES,
    UniversalConfigDocument,
    _decode_utf8,
    _read_bounded,
    _read_regular_fd,
    load_universal_config,
)
from .validation import canonical_json, strict_model

MAX_SETTINGS_SECRET_BYTES = 64 * 1024
MAX_PROMPT_BYTES = 64 * 1024
MAX_SCHEMA_BYTES = 256 * 1024
_ENV_PREFIX = "MSGLOOM_CONFIG__"
_TOP_LEVEL = frozenset(OperatorSettings.model_fields)


def load_operator_configuration(
    config_file: Path,
    *,
    command_options: Mapping[str, object] | None = None,
    mounted_secret_dir: Path | None = None,
) -> OperatorConfiguration:
    """Load one explicit universal document through the legacy operator projection."""
    document = load_universal_config(config_file)
    return load_operator_configuration_from_document(
        document,
        command_options=command_options,
        mounted_secret_dir=mounted_secret_dir,
    )


def load_operator_configuration_from_document(
    document: UniversalConfigDocument,
    *,
    command_options: Mapping[str, object] | None = None,
    mounted_secret_dir: Path | None = None,
) -> OperatorConfiguration:
    """Compose the strict legacy operator contract from one universal snapshot."""
    try:
        config_values = document.operator_values() or {}
        options = dict(command_options or {})
        _check_options(options)
        _check_environment()
        mounted_values = _load_mounted_settings(mounted_secret_dir)
        settings = _load_settings(
            options=options,
            config_values=config_values,
            mounted_values=mounted_values,
        )
        base_dir = document.path.parent if document.path is not None else Path.cwd()
        settings = _resolve_paths(settings, base_dir)
        prompt_text, prompt_digest, schema, schema_digest = _triage_files(settings)
        snapshot = make_snapshot(
            settings,
            prompt_digest=prompt_digest,
            schema_digest=schema_digest,
        )
        return _compose(
            settings,
            snapshot_version=snapshot.version,
            snapshot=snapshot,
            base_dir=base_dir,
            prompt_text=prompt_text,
            schema=schema,
        )
    except ConfigurationError:
        raise
    except (OSError, ValueError, TypeError, ValidationError, json.JSONDecodeError):
        raise ConfigurationError(ConfigurationErrorCode.INVALID_INPUT) from None


def _load_settings(
    *,
    options: dict[str, object],
    config_values: Mapping[str, object],
    mounted_values: Mapping[str, object],
) -> OperatorSettings:
    with bound_sources(config_values, mounted_values):
        return OperatorSettings(**cast(Any, options))


def _resolve_paths(settings: OperatorSettings, base_dir: Path) -> OperatorSettings:
    storage = StorageSettings(
        sqlite_path=resolve_path(base_dir, settings.storage.sqlite_path)
    )
    source = settings.source
    if source is not None:
        source = SourceSettings(
            catalog_path=resolve_path(base_dir, source.catalog_path),
            evidence_roots=tuple(
                resolve_path(base_dir, path) for path in source.evidence_roots
            ),
            limits=source.limits,
            secret_binding_ids=source.secret_binding_ids,
        )
    triage = settings.triage
    if triage is not None:
        runtime = triage.runtime
        runtime = AIRuntimeSettings(
            python_executable=resolve_path(base_dir, runtime.python_executable),
            bubblewrap_executable=resolve_path(base_dir, runtime.bubblewrap_executable),
            runtime_roots=tuple(
                resolve_path(base_dir, path) for path in runtime.runtime_roots
            ),
            cli_path=resolve_path(base_dir, runtime.cli_path),
            storage_root=resolve_path(base_dir, runtime.storage_root),
            termination_grace_seconds=runtime.termination_grace_seconds,
        )
        triage = TriageSettings(
            filter_config=triage.filter_config,
            rule_config=triage.rule_config,
            input_config=triage.input_config,
            working_context=triage.working_context,
            prompt_ref=triage.prompt_ref,
            prompt_file=_resolve_unfollowed(base_dir, triage.prompt_file),
            model_ref=triage.model_ref,
            model_identifier=triage.model_identifier,
            output_schema_ref=triage.output_schema_ref,
            output_schema_file=_resolve_unfollowed(base_dir, triage.output_schema_file),
            attempt_limits=triage.attempt_limits,
            runtime=runtime,
            secret_binding_ids=triage.secret_binding_ids,
            lease_seconds=triage.lease_seconds,
            operation_timeout_seconds=triage.operation_timeout_seconds,
            cleanup_margin_seconds=triage.cleanup_margin_seconds,
            max_upstream_results=triage.max_upstream_results,
            max_upstream_bytes=triage.max_upstream_bytes,
            max_parts=triage.max_parts,
        )
    return settings.model_copy(
        update={"storage": storage, "source": source, "triage": triage}
    )


def _resolve_unfollowed(base_dir: Path, path: Path) -> Path:
    """Resolve relative syntax without following the final filesystem object."""
    value = path if path.is_absolute() else base_dir / path
    return Path(os.path.abspath(value))


def _triage_files(
    settings: OperatorSettings,
) -> tuple[str | None, str | None, dict[str, object] | None, str | None]:
    if settings.triage is None:
        return None, None, None, None
    prompt_bytes = _read_bounded(settings.triage.prompt_file, MAX_PROMPT_BYTES)
    schema_bytes = _read_bounded(settings.triage.output_schema_file, MAX_SCHEMA_BYTES)
    try:
        prompt = prompt_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise ConfigurationError(ConfigurationErrorCode.INVALID_INPUT) from None
    if not prompt.strip() or "\x00" in prompt:
        raise ConfigurationError(ConfigurationErrorCode.INVALID_INPUT)
    schema = _decode_json_object(schema_bytes)
    return (
        prompt,
        hashlib.sha256(prompt_bytes).hexdigest(),
        schema,
        hashlib.sha256(schema_bytes).hexdigest(),
    )


def _compose(
    settings: OperatorSettings,
    *,
    snapshot_version: str,
    snapshot: object,
    base_dir: Path,
    prompt_text: str | None,
    schema: dict[str, object] | None,
) -> OperatorConfiguration:
    from .models import ConfigurationSnapshot

    if not isinstance(snapshot, ConfigurationSnapshot):
        raise ConfigurationError(ConfigurationErrorCode.INVALID_INPUT)
    bindings = {item.binding_id: item for item in settings.secrets}
    _validate_binding_refs(settings, bindings)
    source_reader = _source_reader(settings)
    operations: dict[PhaseCapability, OperationData] = {}
    if settings.preparation is not None and source_reader is not None:
        item = settings.preparation
        operations[PhaseCapability.PREPARE] = PreparationOperationData(
            intake_targets=item.intake_targets,
            filter_config=item.filter_config,
            parser_profiles=item.parser_profiles,
            configuration_version=snapshot_version,
            code_version=settings.code_version,
            execution_timeout_seconds=item.execution_timeout_seconds,
            claim_lease_seconds=item.claim_lease_seconds,
            max_records=item.max_records,
            max_total_selected_bytes=item.max_total_selected_bytes,
            max_derived_bytes=item.max_derived_bytes,
            max_total_derived_bytes=item.max_total_derived_bytes,
            max_total_parser_output_bytes=item.max_total_parser_output_bytes,
        )
    if settings.triage is not None:
        if prompt_text is None or schema is None:
            raise ConfigurationError(ConfigurationErrorCode.INVALID_INPUT)
        item = settings.triage
        # The reviewed A3 contract names the composed triage input version
        # ``triage_input_config``. The redacted snapshot version keeps it
        # change-sensitive with the rest of the operator configuration.
        config_ref = VersionRef("triage_input_config", "phase1", snapshot_version)
        input_config = build_input_config(item.input_config, config_ref)
        context = build_working_context(item.working_context, base_dir)
        versions = TrustedInputVersions(
            prompt=item.prompt_ref,
            model=item.model_ref,
            output_schema=item.output_schema_ref,
            configuration=config_ref,
        )
        policy = TrustedPolicy(
            schemas={item.output_schema_ref: schema},
            models={item.model_ref: item.model_identifier},
        )
        operations[PhaseCapability.TRIAGE] = TriageOperationData(
            filter_config=item.filter_config,
            rule_config=item.rule_config,
            input_config=input_config,
            versions=versions,
            working_context_config=context,
            prompt_text=prompt_text,
            trusted_policy=policy,
            attempt_limits=item.attempt_limits,
            runtime=item.runtime,
            secret_binding_ids=item.secret_binding_ids,
            configuration_version=snapshot_version,
            code_version=settings.code_version,
            lease_seconds=item.lease_seconds,
            operation_timeout_seconds=item.operation_timeout_seconds,
            cleanup_margin_seconds=item.cleanup_margin_seconds,
            max_upstream_results=item.max_upstream_results,
            max_upstream_bytes=item.max_upstream_bytes,
            max_parts=item.max_parts,
        )
    if settings.report is not None:
        item = settings.report
        operations[PhaseCapability.REPORT_BUILD] = ReportOperationData(
            policy=item.policy,
            renderer=item.renderer,
            configuration_version=snapshot_version,
            code_version=settings.code_version,
            max_input_bytes=item.max_input_bytes,
            timeout_seconds=item.timeout_seconds,
            claim_lease_seconds=item.claim_lease_seconds,
        )
        if item.transport is not None:
            operations[PhaseCapability.REPORT_SUBMIT] = ReportSubmitOperationData(
                transport_ref=item.transport.transport_ref,
                secret_binding_ids=item.transport.secret_binding_ids,
                policy_ref=item.policy.policy_ref,
            )
    return OperatorConfiguration(
        settings=settings,
        snapshot=snapshot,
        source_reader=source_reader,
        operations=operations,
    )


def _source_reader(settings: OperatorSettings) -> SavedSourceReaderConfig | None:
    if settings.source is None:
        return None
    raw = {
        "catalog_path": str(settings.source.catalog_path),
        "evidence_roots": [str(path) for path in settings.source.evidence_roots],
        "limits": settings.source.limits,
    }
    return strict_model(SavedSourceReaderConfig, raw)


def _validate_binding_refs(
    settings: OperatorSettings, bindings: Mapping[str, SecretBinding]
) -> None:
    if settings.source is not None:
        _require_purpose(
            settings.source.secret_binding_ids, SecretPurpose.SOURCE, bindings
        )
    if settings.triage is not None:
        _require_purpose(settings.triage.secret_binding_ids, SecretPurpose.AI, bindings)
    if settings.report is not None and settings.report.transport is not None:
        _require_purpose(
            settings.report.transport.secret_binding_ids,
            SecretPurpose.REPORT,
            bindings,
        )


def _require_purpose(
    ids: tuple[str, ...],
    purpose: SecretPurpose,
    bindings: Mapping[str, SecretBinding],
) -> None:
    if len(ids) != len(set(ids)):
        raise ConfigurationError(ConfigurationErrorCode.INVALID_INPUT)
    for binding_id in ids:
        binding = bindings.get(binding_id)
        if binding is None or binding.purpose is not purpose:
            raise ConfigurationError(ConfigurationErrorCode.INVALID_INPUT)


def _check_options(options: dict[str, object]) -> None:
    if len(options) > len(_TOP_LEVEL) or set(options) - _TOP_LEVEL:
        raise ConfigurationError(ConfigurationErrorCode.UNKNOWN_INPUT)
    if len(canonical_json(options).encode("utf-8")) > MAX_CONFIG_BYTES:
        raise ConfigurationError(ConfigurationErrorCode.INPUT_TOO_LARGE)


def _check_environment() -> None:
    prefix = _ENV_PREFIX.casefold()
    seen: list[tuple[str, ...]] = []
    for key, value in os.environ.items():
        if not key.casefold().startswith(prefix):
            continue
        tail = key[len(_ENV_PREFIX) :]
        segments = tuple(part.casefold() for part in tail.split("__"))
        if not segments or not segments[0] or segments[0] not in _TOP_LEVEL:
            raise ConfigurationError(ConfigurationErrorCode.UNKNOWN_INPUT)
        if any(not part for part in segments):
            raise ConfigurationError(ConfigurationErrorCode.UNKNOWN_INPUT)
        if len(value.encode("utf-8")) > MAX_SETTINGS_SECRET_BYTES:
            raise ConfigurationError(ConfigurationErrorCode.INPUT_TOO_LARGE)
        if any(
            segments == prior
            or segments[: len(prior)] == prior
            or prior[: len(segments)] == segments
            for prior in seen
        ):
            raise ConfigurationError(ConfigurationErrorCode.INVALID_INPUT)
        seen.append(segments)


def _load_mounted_settings(directory: Path | None) -> dict[str, object]:
    if directory is None:
        return {}
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        root_fd = os.open(directory, flags)
    except OSError:
        raise ConfigurationError(ConfigurationErrorCode.INVALID_INPUT) from None
    values: dict[str, object] = {}
    try:
        for field in _TOP_LEVEL:
            data = _read_named_bounded(root_fd, field, MAX_SETTINGS_SECRET_BYTES)
            if data is None:
                continue
            text = _decode_utf8(data).strip()
            if not text:
                continue
            values[field] = (
                text if field == "code_version" else _decode_json_value(text)
            )
    finally:
        os.close(root_fd)
    return values


def _read_named_bounded(root_fd: int, name: str, maximum: int) -> bytes | None:
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    try:
        fd = os.open(name, flags, dir_fd=root_fd)
    except FileNotFoundError:
        return None
    except OSError:
        raise ConfigurationError(ConfigurationErrorCode.INVALID_INPUT) from None
    try:
        return _read_regular_fd(fd, maximum)
    finally:
        os.close(fd)


def _decode_json_value(text: str) -> object:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result

    return json.loads(text, object_pairs_hook=pairs)


def _decode_json_object(data: bytes) -> dict[str, object]:
    value = _decode_json_value(_decode_utf8(data))
    if not isinstance(value, dict) or not value:
        raise ValueError("schema must be a non-empty object")
    return value
