"""Deterministic redaction and versioning for operator configuration."""

from __future__ import annotations

import hashlib
import json

from .models import ConfigurationSnapshot, OperatorSettings
from .validation import canonical_json


def _digest(value: object) -> str:
    encoded = canonical_json(value).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _ids(values: tuple[str, ...]) -> list[str]:
    return [_digest(value) for value in values]


def make_snapshot(
    settings: OperatorSettings,
    *,
    prompt_digest: str | None,
    schema_digest: str | None,
) -> ConfigurationSnapshot:
    """Create an exact redacted snapshot whose hash changes with configuration."""
    payload: dict[str, object] = {
        "schema": "operator-configuration-snapshot@1",
        "code_version": settings.code_version,
        "storage": {"sqlite_path": _digest(str(settings.storage.sqlite_path))},
        "admissions": [
            {
                "identity": _digest((item.caller, item.authority_ref)),
                "capabilities": sorted(
                    capability.value for capability in item.capabilities
                ),
            }
            for item in settings.admissions
        ],
        "secrets": [
            {
                "binding": _digest(item.binding_id),
                "purpose": item.purpose.value,
                "source": item.source.value,
                "logical_name": _digest(item.logical_name),
                "locator": _digest(item.locator),
            }
            for item in settings.secrets
        ],
    }
    if settings.source is not None:
        payload["source"] = {
            "catalog": _digest(str(settings.source.catalog_path)),
            "evidence_roots": [
                _digest(str(path)) for path in settings.source.evidence_roots
            ],
            "limits": settings.source.limits,
            "secret_bindings": _ids(settings.source.secret_binding_ids),
        }
    if settings.preparation is not None:
        item = settings.preparation
        payload["preparation"] = {
            "semantics": _digest(
                {
                    "filter": item.filter_config,
                    "parser_profiles": item.parser_profiles,
                }
            ),
            "budgets": {
                "execution_timeout_seconds": item.execution_timeout_seconds,
                "claim_lease_seconds": item.claim_lease_seconds,
                "max_records": item.max_records,
                "max_total_selected_bytes": item.max_total_selected_bytes,
                "max_derived_bytes": item.max_derived_bytes,
                "max_total_derived_bytes": item.max_total_derived_bytes,
                "max_total_parser_output_bytes": item.max_total_parser_output_bytes,
            },
        }
    if settings.triage is not None:
        item = settings.triage
        payload["triage"] = {
            "semantics": _digest(
                {
                    "filter": item.filter_config,
                    "rules": item.rule_config,
                    "input": item.input_config,
                    "working_context": item.working_context,
                    "prompt_ref": item.prompt_ref,
                    "model_ref": item.model_ref,
                    "model_identifier": item.model_identifier,
                    "schema_ref": item.output_schema_ref,
                    "attempt_limits": item.attempt_limits,
                    "runtime": item.runtime,
                }
            ),
            "prompt_content": prompt_digest,
            "schema_content": schema_digest,
            "secret_bindings": _ids(item.secret_binding_ids),
            "budgets": {
                "lease_seconds": item.lease_seconds,
                "operation_timeout_seconds": item.operation_timeout_seconds,
                "cleanup_margin_seconds": item.cleanup_margin_seconds,
                "max_upstream_results": item.max_upstream_results,
                "max_upstream_bytes": item.max_upstream_bytes,
                "max_parts": item.max_parts,
            },
        }
    if settings.report is not None:
        item = settings.report
        report: dict[str, object] = {
            "policy": _digest(item.policy),
            "renderer": item.renderer.model_dump(mode="json"),
            "max_input_bytes": item.max_input_bytes,
            "timeout_seconds": item.timeout_seconds,
            "claim_lease_seconds": item.claim_lease_seconds,
        }
        if item.transport is not None:
            report["transport"] = {
                "reference": _digest(item.transport.transport_ref),
                "secret_bindings": _ids(item.transport.secret_binding_ids),
            }
        payload["report"] = report
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    version = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return ConfigurationSnapshot(version=version, payload=encoded)
