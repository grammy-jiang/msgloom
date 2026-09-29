"""Closed CLI-local invocation envelopes for finite Phase 1 work."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from msgloom.contracts import VersionRef
from msgloom.delivery import ReportReconciliationPlan, ReportSubmissionPlan
from msgloom.preparation_pipeline import PreparationMode, SelectionPlan
from msgloom.reporting import ReportSelectionPlan
from msgloom.triage_pipeline import TriageReplayPlan

ShortText = Annotated[str, Field(min_length=1, max_length=512)]
Parameters = Annotated[tuple[tuple[str, str], ...], Field(max_length=32)]


class _ClosedModel(BaseModel):
    """Reject coercion, mutation, and undeclared invocation fields."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")


class StageName(StrEnum):
    """Finite executable stages exposed by the operator CLI."""

    PREPARE = "prepare"
    TRIAGE = "triage"
    REPORT_BUILD = "report-build"
    REPORT_SUBMIT = "report-submit"
    REPORT_RECONCILE = "report-reconcile"


class ReplayStage(StrEnum):
    """Stages that can be explicitly replayed without external submission."""

    PREPARE = "prepare"
    TRIAGE = "triage"
    REPORT_BUILD = "report-build"


class InvocationBase(_ClosedModel):
    """Bind one invocation to exact trusted configuration and authority."""

    schema_version: Literal["1"] = "1"
    configuration_version: ShortText
    execution: ShortText
    attempt: ShortText
    caller: ShortText
    authority_ref: ShortText
    parameters: Parameters = ()

    @model_validator(mode="after")
    def _unique_parameters(self) -> InvocationBase:
        keys = tuple(key for key, _value in self.parameters)
        if len(keys) != len(set(keys)):
            raise ValueError("invocation parameters must be unique")
        return self


class PrepareInvocation(InvocationBase):
    """Exact A2 selection choices; reusable semantics stay in configuration."""

    mode: PreparationMode
    selections: Annotated[
        tuple[SelectionPlan, ...], Field(min_length=1, max_length=1000)
    ]

    @model_validator(mode="after")
    def _no_parameters(self) -> PrepareInvocation:
        if self.parameters:
            raise ValueError("preparation invocation parameters are unsupported")
        return self


class TriageInvocation(InvocationBase):
    """Exact A3 replay/input identities plus finite per-run claim identity."""

    plan: TriageReplayPlan
    capture_time: datetime | None = None
    claim_key: ShortText

    @model_validator(mode="after")
    def _plan_is_closed(self) -> TriageInvocation:
        self.plan.validated()
        return self


class ReportBuildInvocation(InvocationBase):
    """Exact A5 report selection and new downstream result identities."""

    selection_plan: ReportSelectionPlan
    report_ref: VersionRef
    result_id: ShortText
    semantic_data_id: ShortText
    selection_result_id: ShortText
    selection_semantic_data_id: ShortText


class ReportSubmitInvocation(InvocationBase):
    """Exact reviewed delivery plan plus one finite submission attempt budget."""

    plan: ReportSubmissionPlan
    timeout_seconds: Annotated[float, Field(gt=0.0, le=300.0)]
    claim_lease_seconds: Annotated[float, Field(gt=0.0, le=600.0)]

    @model_validator(mode="after")
    def _lease(self) -> ReportSubmitInvocation:
        if self.claim_lease_seconds < self.timeout_seconds + 1.0:
            raise ValueError("submission lease must exceed operation budget")
        return self


class ReportReconcileInvocation(_ClosedModel):
    """Explicit provider-evidence reconciliation; never performs a send."""

    schema_version: Literal["1"] = "1"
    configuration_version: ShortText
    execution: ShortText
    caller: ShortText
    authority_ref: ShortText
    plan: ReportReconciliationPlan


Invocation = (
    PrepareInvocation
    | TriageInvocation
    | ReportBuildInvocation
    | ReportSubmitInvocation
    | ReportReconcileInvocation
)


class CliRequest(_ClosedModel):
    """Parsed CLI request returned before the sole event-loop entrypoint."""

    action: Literal[
        "config-inspect",
        "config-validate",
        "status",
        "execute",
        "replay",
    ]
    config_file: Annotated[str, Field(min_length=1, max_length=4096)]
    invocation_file: Annotated[str | None, Field(max_length=4096)] = None
    execution: ShortText | None = None
    stage: StageName | ReplayStage | None = None
    mounted_secret_dir: Annotated[str | None, Field(max_length=4096)] = None
    allowed_secret_environment: Annotated[
        tuple[ShortText, ...], Field(max_length=32)
    ] = ()
    allowed_secret_files: Annotated[tuple[ShortText, ...], Field(max_length=32)] = ()
