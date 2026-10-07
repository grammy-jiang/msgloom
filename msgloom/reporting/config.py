"""Closed trusted configuration for one finite report build."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from msgloom.contracts import AttemptIdentity, VersionRef


class ReportHandlerConfig(BaseModel):
    """Trusted finite identities and budget for one configured build."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    report_ref: VersionRef
    result_id: Annotated[str, Field(min_length=1, max_length=256)]
    semantic_data_id: Annotated[str, Field(min_length=1, max_length=256)]
    selection_result_id: Annotated[str, Field(min_length=1, max_length=256)]
    selection_semantic_data_id: Annotated[str, Field(min_length=1, max_length=256)]
    max_input_bytes: Annotated[int, Field(ge=1, le=64 * 1024 * 1024)]
    attempt: AttemptIdentity
    code_version: Annotated[str, Field(min_length=1, max_length=256)]
    expected_parameters: Annotated[tuple[tuple[str, str], ...], Field(max_length=32)]
    timeout_seconds: Annotated[float, Field(gt=0.0, le=300.0)]
    claim_lease_seconds: Annotated[float, Field(gt=0.0, le=600.0)]

    @model_validator(mode="after")
    def _budget_fits_lease(self) -> ReportHandlerConfig:
        if self.report_ref.kind != "report":
            raise ValueError("configured report reference must be report kind")
        keys = tuple(key for key, _value in self.expected_parameters)
        if len(keys) != len(set(keys)):
            raise ValueError("trusted handler parameters must have unique keys")
        if self.claim_lease_seconds < self.timeout_seconds + 1.0:
            raise ValueError("claim lease must exceed the finite operation budget")
        return self
