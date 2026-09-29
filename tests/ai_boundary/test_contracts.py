"""AI boundary contract and trusted-policy tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from msgloom.ai import (
    AnalysisAttempt,
    AttemptLimits,
    RuntimeIsolation,
    TrustedPolicy,
)
from msgloom.contracts import AttemptIdentity, VersionRef


def _ref(kind: str, identity: str) -> VersionRef:
    return VersionRef(kind, identity, "1")


def _limits() -> AttemptLimits:
    return AttemptLimits(5, 20, 20, 20, 4096, 8, 1024, 2, 700)


def test_attempt_enforces_supplied_text_bounds() -> None:
    """Oversized supplied data is rejected before any child can start."""
    with pytest.raises(ValueError, match="input exceeds"):
        AnalysisAttempt(
            AttemptIdentity("attempt-1"),
            (_ref("prepared", "input-1"),),
            _ref("context", "context-1"),
            _ref("prompt", "prompt-1"),
            _ref("schema", "schema-1"),
            _ref("model", "model-1"),
            "x" * 21,
            "",
            "prompt",
            _limits(),
        )


def test_policy_owns_schema_and_model_mapping() -> None:
    """Attempts carry references rather than caller-supplied SDK schema flags."""
    schema_ref = _ref("schema", "schema-1")
    model_ref = _ref("model", "model-1")
    schema = {
        "type": "object",
        "properties": {"value": {"type": "string"}},
    }
    policy = TrustedPolicy(
        {schema_ref: schema},
        {model_ref: "synthetic-model"},
    )
    schema["properties"]["value"]["type"] = "integer"
    stored = policy.schema_for(schema_ref)
    if stored is None:
        pytest.fail("trusted schema mapping disappeared")
    if stored != {
        "type": "object",
        "properties": {"value": {"type": "string"}},
    }:
        pytest.fail("trusted schema was mutable through caller-owned data")
    if policy.models[model_ref] != "synthetic-model":
        pytest.fail("trusted model mapping changed")


def test_runtime_rejects_non_model_credentials(tmp_path: Path) -> None:
    """Source/provider credentials cannot enter the AI child environment."""
    with pytest.raises(ValueError, match="unapproved"):
        RuntimeIsolation(
            Path("/usr/bin/python3"),
            Path("/usr/bin/bwrap"),
            (Path("/usr"),),
            Path("/synthetic/claude"),
            {"MS_GRAPH_TOKEN": "synthetic-not-a-real-token"},
            tmp_path,
        )
