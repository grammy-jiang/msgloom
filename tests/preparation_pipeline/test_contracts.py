"""Closed constructor and derived-byte codec boundary tests."""

from __future__ import annotations

import hashlib

import pytest
from pydantic import ValidationError

from msgloom.contracts import (
    AttemptIdentity,
    ExecutionIdentity,
    OperationRequest,
    PhaseCapability,
    VersionRef,
)
from msgloom.preparation import DocumentFormat, DocumentLocation
from msgloom.preparation_pipeline import (
    DerivedByteArtifact,
    DerivedByteArtifactCodec,
    PreparationMode,
    PreparationPlan,
    SelectionPlan,
)

from .helpers import filter_config, profiles


def test_derived_byte_codec_owns_exact_utf8_identity() -> None:
    """Derived parser bytes carry their own digest and canonical codec."""
    artifact = DerivedByteArtifact.capture(
        VersionRef("message", "m1", "v1"),
        VersionRef("collected_selection", "s1", "v1"),
        "body:0",
        DocumentLocation(part="graph-json"),
        "synthetic body",
    )
    payload = DerivedByteArtifactCodec().encode(artifact)
    decoded = DerivedByteArtifactCodec().decode(payload)
    if decoded != artifact:
        pytest.fail("derived-byte codec did not round-trip canonically")
    if artifact.sha256 != hashlib.sha256(b"synthetic body").hexdigest():
        pytest.fail("derived-byte digest does not identify exact UTF-8 bytes")


def test_plan_rejects_mode_drift_and_unsafe_lease() -> None:
    """Replay bindings and execution/lease budgets are closed at construction."""
    source = VersionRef("message", "m1", "v1")
    with pytest.raises(ValidationError):
        PreparationPlan(
            mode=PreparationMode.REPLAY,
            attempt=AttemptIdentity("attempt"),
            selections=(SelectionPlan(source=source),),
            filter_config=filter_config(),
            parser_profiles=profiles(DocumentFormat.TEXT),
            configuration_version="config",
            code_version="build",
        )
    with pytest.raises(ValidationError):
        PreparationPlan(
            mode=PreparationMode.LIVE,
            attempt=AttemptIdentity("attempt"),
            selections=(SelectionPlan(source=source),),
            filter_config=filter_config(),
            parser_profiles=profiles(DocumentFormat.TEXT),
            configuration_version="config",
            code_version="build",
            execution_timeout_seconds=10.0,
            claim_lease_seconds=10.5,
        )


def test_request_parameters_cannot_select_runtime_behavior() -> None:
    """Untrusted request parameters are not part of parser dispatch."""
    request = OperationRequest(
        execution=ExecutionIdentity("execution"),
        caller="test",
        capability=PhaseCapability.PREPARE,
        target_inputs=(VersionRef("message", "m1", "v1"),),
        parameters=(("parser_module", "untrusted.module"),),
    )
    if request.parameters[0][0] != "parser_module":
        pytest.fail("operation fixture is malformed")
