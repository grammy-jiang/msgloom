"""Async command dispatch and privacy-safe operator output."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from message_ingest.acquisition.microsoft.outlook.email.rule_config import (
    mail_policy_inspection,
    parse_mail_rule_policy,
)
from msgloom.configuration import (
    ConfigurationError,
    OperatorConfiguration,
    configuration_error_payload,
    load_operator_configuration,
    load_operator_configuration_from_document,
    load_universal_config,
)
from msgloom.contracts import OperationOutcome, TerminalStatus
from msgloom.persistence import Phase1PersistenceError
from msgloom.preparation_pipeline import PreparationMode
from msgloom.triage_pipeline import TriageMode

from .codecs import InvocationError, load_invocation
from .composition import (
    CompositionDependencies,
    ExecutionOptions,
    execute_invocation,
    reconcile_invocation,
)
from .models import (
    CliRequest,
    PrepareInvocation,
    ReplayStage,
    ReportBuildInvocation,
    ReportReconcileInvocation,
    ReportSubmitInvocation,
    ScheduledPrepareInvocation,
    StageName,
    TriageInvocation,
)
from .status import StatusError, read_saved_status

_DEFAULT_DEPENDENCIES = CompositionDependencies()


@dataclass(frozen=True, slots=True)
class CliResult:
    """Canonical operator response plus process exit code."""

    exit_code: int
    payload: dict[str, object]

    def render(self) -> str:
        """Return deterministic compact JSON without arbitrary exception text."""
        return json.dumps(
            self.payload,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )


async def run_request(
    request: CliRequest,
    *,
    dependencies: CompositionDependencies = _DEFAULT_DEPENDENCIES,
) -> CliResult:
    """Run one parsed request without owning or nesting an event loop."""
    try:
        mounted = (
            None
            if request.mounted_secret_dir is None
            else Path(request.mounted_secret_dir)
        )
        if request.action in {"config-inspect", "config-validate"}:
            return _run_config_command(request, mounted)

        if request.config_file is None:
            return _error("cli_invalid", 2)
        config_path = Path(request.config_file)
        configuration = load_operator_configuration(
            config_path,
            mounted_secret_dir=mounted,
        )
        if request.action == "status":
            if request.execution is None:
                return _error("cli_invalid", 2)
            saved = read_saved_status(configuration.database_url, request.execution)
            return CliResult(0, {"status": "ok", "saved": saved})
        return await _execute(request, configuration, mounted, dependencies)
    except ConfigurationError as error:
        return CliResult(
            2,
            {
                "status": "error",
                **configuration_error_payload(error),
            },
        )
    except InvocationError as error:
        return _error(error.code, 2)
    except StatusError as error:
        return _error(error.code, 2)
    except PermissionError:
        return _error("authority_not_trusted", 3)
    except (Phase1PersistenceError, OSError):
        return _error("operation_unavailable", 4)
    except (TypeError, ValueError):
        return _error("invocation_invalid", 2)
    except Exception:  # noqa: BLE001
        return _error("operation_failed", 4)


def _run_config_command(
    request: CliRequest,
    mounted: Path | None,
) -> CliResult:
    document = load_universal_config(
        None if request.config_file is None else Path(request.config_file)
    )
    payload: dict[str, object] = {"status": "ok"}

    operator_values = document.operator_values()
    if operator_values is not None:
        configuration = load_operator_configuration_from_document(
            document,
            mounted_secret_dir=mounted,
        )
        payload["configuration_version"] = configuration.version
        if request.action == "config-inspect":
            payload["code_version"] = configuration.code_version

    mail_values = document.outlook_mail_values()
    if mail_values is not None:
        policy = parse_mail_rule_policy(
            mail_values,
            source_label=document.source,
        )
        if request.action == "config-inspect":
            payload["mail"] = mail_policy_inspection(policy)

    return CliResult(0, payload)


async def _execute(
    request: CliRequest,
    configuration: OperatorConfiguration,
    mounted: Path | None,
    dependencies: CompositionDependencies,
) -> CliResult:
    if request.invocation_file is None or request.stage is None:
        return _error("cli_invalid", 2)
    stage = StageName(request.stage.value)
    invocation = load_invocation(Path(request.invocation_file), stage)
    if request.action == "replay":
        replay_error = _replay_gate(request.stage, invocation)
        if replay_error is not None:
            return replay_error
    if stage is StageName.REPORT_RECONCILE:
        if not isinstance(invocation, ReportReconcileInvocation):
            return _error("invocation_invalid", 2)
        result = await reconcile_invocation(
            configuration,
            invocation,
            options=_options(request, mounted),
            dependencies=dependencies,
        )
        return CliResult(
            0,
            {
                "status": "reconciled",
                "reconciliation": result.identity.value,
                "effect": result.decision.value,
                "evidence": [
                    {
                        "result_id": ref.result_id,
                        "kind": ref.kind,
                        "schema_version": ref.schema_version,
                    }
                    for ref in result.evidence
                ],
            },
        )
    if not isinstance(
        invocation,
        (
            PrepareInvocation,
            ScheduledPrepareInvocation,
            TriageInvocation,
            ReportBuildInvocation,
            ReportSubmitInvocation,
        ),
    ):
        return _error("invocation_invalid", 2)
    outcome = await execute_invocation(
        configuration,
        invocation,
        options=_options(request, mounted),
        dependencies=dependencies,
    )
    return _outcome(outcome)


def _replay_gate(
    stage: StageName | ReplayStage, invocation: object
) -> CliResult | None:
    replay_stage = ReplayStage(stage.value)
    if replay_stage is ReplayStage.PREPARE:
        if not isinstance(invocation, PrepareInvocation):
            return _error("invocation_invalid", 2)
        if invocation.mode is not PreparationMode.REPLAY:
            return _error("replay_mode_required", 2)
    elif replay_stage is ReplayStage.TRIAGE:
        if not isinstance(invocation, TriageInvocation):
            return _error("invocation_invalid", 2)
        if invocation.plan.mode is not TriageMode.REPLAY:
            return _error("replay_mode_required", 2)
    return None


def _options(request: CliRequest, mounted: Path | None) -> ExecutionOptions:
    return ExecutionOptions(
        mounted_secret_dir=mounted,
        allowed_secret_environment=frozenset(request.allowed_secret_environment),
        allowed_secret_files=frozenset(request.allowed_secret_files),
    )


def _outcome(outcome: OperationOutcome) -> CliResult:
    payload: dict[str, object] = {
        "status": outcome.status.value,
        "execution": outcome.execution.value,
        "capability": outcome.capability.value,
        "result_refs": [
            {
                "result_id": ref.result_id,
                "kind": ref.kind,
                "schema_version": ref.schema_version,
            }
            for ref in outcome.result_refs
        ],
        "limitation_codes": [item.code for item in outcome.limitations],
        "failure_codes": [item.code for item in outcome.failures],
        "external_effect": outcome.external_effect.value,
    }
    if outcome.status is TerminalStatus.COMPLETE:
        code = 0
    elif outcome.status is TerminalStatus.BLOCKED:
        code = 3
    else:
        code = 4
    return CliResult(code, payload)


def _error(code: str, exit_code: int) -> CliResult:
    return CliResult(exit_code, {"status": "error", "code": code})
