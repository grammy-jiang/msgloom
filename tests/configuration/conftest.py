"""Synthetic operator-configuration fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def minimal_toml(tmp_path: Path) -> Path:
    """Write the smallest explicit inspectable operator TOML."""
    path = tmp_path / "operator.toml"
    path.write_text(
        """
code_version = "toml-code"

[storage]
sqlite_path = "state/phase1.sqlite3"

[[admissions]]
caller = "operator-cli"
authority_ref = "owner-approved"
capabilities = ["a2_prepare", "a3_triage", "a5_report_build", "a5_report_submit"]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def full_options(tmp_path: Path) -> dict[str, object]:
    """Return complete synthetic Phase 1 command-option data."""
    prompt = tmp_path / "policy" / "prompt.md"
    schema = tmp_path / "policy" / "schema.json"
    prompt.parent.mkdir()
    prompt.write_text("Classify only the supplied synthetic work.", encoding="utf-8")
    schema.write_text(
        json.dumps(
            {
                "type": "object",
                "properties": {"topics": {"type": "array"}},
                "required": ["topics"],
            }
        ),
        encoding="utf-8",
    )
    filter_config = {
        "reference": {
            "kind": "filter-config",
            "identity": "phase1-filter",
            "version": "1",
        },
        "address_normalization": "exact",
        "rules": [],
    }
    return {
        "code_version": "build-15e4493",
        "secrets": [
            {
                "binding_id": "ai-region",
                "purpose": "ai",
                "logical_name": "AWS_REGION",
                "source": "environment",
                "locator": "SYNTHETIC_AI_REGION",
            },
            {
                "binding_id": "report-credential",
                "purpose": "report",
                "logical_name": "transport",
                "source": "mounted-file",
                "locator": "report-token",
            },
            {
                "binding_id": "source-credential",
                "purpose": "source",
                "logical_name": "graph",
                "source": "environment",
                "locator": "SYNTHETIC_SOURCE_TOKEN",
            },
        ],
        "source": {
            "catalog_path": "saved/catalog.sqlite3",
            "evidence_roots": ["saved/raw"],
            "limits": {"max_selected_records": 8},
            "secret_binding_ids": ["source-credential"],
        },
        "preparation": {
            "filter_config": filter_config,
            "parser_profiles": [
                {
                    "format": "text",
                    "parser": {
                        "name": "msgloom.mime-html",
                        "version": "1",
                        "backend": "stdlib-email+selectolax-0.4.13",
                    },
                    "config": {"profile": "mime-html-v1", "settings": []},
                    "limits": {
                        "wall_time_seconds": 2.0,
                        "memory_bytes": 1048576,
                        "decompressed_bytes": 1048576,
                        "output_bytes": 262144,
                        "container_members": 4,
                    },
                }
            ],
            "max_records": 8,
        },
        "triage": {
            "filter_config": filter_config,
            "rule_config": {
                "version": {
                    "kind": "triage-rules",
                    "identity": "owner-rules",
                    "version": "1",
                },
                "rules": [],
            },
            "input_config": {
                "repetition": {"remove_exact_text_repetitions": False},
                "split": {"max_part_bytes": 4096, "max_parts_per_unit": 4},
                "max_snapshot_bytes": 65536,
            },
            "working_context": {
                "selected_files": [
                    {"selection_id": "daily", "path": "memory/daily.md"}
                ],
                "allowed_roots": ["memory"],
                "time_policy": {"timezone": "Australia/Sydney"},
                "stale_policy": "capture",
                "stale_after_seconds": 86400.0,
                "future_tolerance_seconds": 1.0,
                "max_files": 4,
                "max_bytes_per_file": 65536,
                "max_total_bytes": 131072,
                "max_capture_seconds": 5.0,
            },
            "prompt_ref": {
                "kind": "prompt",
                "identity": "triage",
                "version": "1",
            },
            "prompt_file": "policy/prompt.md",
            "model_ref": {
                "kind": "model",
                "identity": "claude",
                "version": "qualified",
            },
            "model_identifier": "synthetic-qualified-model",
            "output_schema_ref": {
                "kind": "schema",
                "identity": "triage-output",
                "version": "1",
            },
            "output_schema_file": "policy/schema.json",
            "attempt_limits": {
                "timeout_seconds": 5.0,
                "max_input_bytes": 65536,
                "max_context_bytes": 32768,
                "max_prompt_bytes": 65536,
                "max_output_bytes": 65536,
                "max_trace_events": 32,
                "max_trace_event_bytes": 8192,
                "max_turns": 4,
                "max_tokens": 4096,
            },
            "runtime": {
                "python_executable": "runtime/python",
                "bubblewrap_executable": "runtime/bwrap",
                "runtime_roots": ["runtime/root"],
                "cli_path": "runtime/claude",
                "storage_root": "runtime/state",
            },
            "secret_binding_ids": ["ai-region"],
            "lease_seconds": 30.0,
            "operation_timeout_seconds": 20.0,
            "cleanup_margin_seconds": 2.0,
            "max_upstream_results": 32,
            "max_upstream_bytes": 1048576,
            "max_parts": 8,
        },
        "report": {
            "policy": {
                "policy_ref": {
                    "kind": "report-policy",
                    "identity": "daily-owner",
                    "version": "1",
                },
                "destination": {
                    "owner_identity": "private-owner",
                    "destination_identity": "private-owner@example.invalid",
                },
                "due_at": "2026-09-29T09:00:00+10:00",
                "timezone": "Australia/Sydney",
                "priorities": ["critical", "important"],
                "due_mode": "all-matching",
                "repeat_mode": "never",
                "repeat_after_seconds": None,
                "reminder_mode": "disabled",
                "reminder_after_seconds": None,
            },
            "renderer": {
                "max_part_bytes": 65536,
                "max_total_bytes": 262144,
                "max_parts": 8,
            },
            "max_input_bytes": 1048576,
            "timeout_seconds": 20.0,
            "claim_lease_seconds": 30.0,
            "transport": {
                "transport_ref": {
                    "kind": "report-transport",
                    "identity": "owner-mail",
                    "version": "1",
                },
                "secret_binding_ids": ["report-credential"],
            },
        },
    }
