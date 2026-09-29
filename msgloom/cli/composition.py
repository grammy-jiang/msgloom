"""Awaited operator composition over the reviewed Phase 1 Application."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

from msgloom.ai import AIRunner, RuntimeIsolation, TrustedPolicy
from msgloom.application import Application
from msgloom.configuration import (
    OperatorConfiguration,
    PreparationOperationData,
    ReportOperationData,
    ReportSubmitOperationData,
    SecretPurpose,
    SecretResolver,
    TriageOperationData,
    load_operator_configuration,
)
from msgloom.contracts import (
    AttemptIdentity,
    ExecutionIdentity,
    OperationOutcome,
    OperationRequest,
    PhaseCapability,
    ResultSchemaRegistry,
)
from msgloom.delivery import (
    DeliveryReportHistoryResolver,
    ReportReconciler,
    ReportSubmissionHandler,
    ReportTransport,
    SubmissionHandlerConfig,
)
from msgloom.persistence import Phase1Persistence, SemanticDataRegistry
from msgloom.preparation_pipeline import PreparationHandler
from msgloom.reporting import ReportBuildHandler
from msgloom.sources import SavedSourceReader
from msgloom.triage_pipeline import TriageHandler, TriageRunner

from .models import (
    PrepareInvocation,
    ReportBuildInvocation,
    ReportReconcileInvocation,
    ReportSubmitInvocation,
    TriageInvocation,
)


class TriageRunnerFactory(Protocol):
    """Construct one fresh runner at the admitted A3 execution boundary."""

    def __call__(
        self, policy: TrustedPolicy, runtime: RuntimeIsolation
    ) -> TriageRunner:
        """Return one runner without changing trusted policy."""
        ...


class ReportTransportFactory(Protocol):
    """Construct one configured report transport after admission."""

    def __call__(
        self,
        operation: ReportSubmitOperationData,
        owner_identity: str,
        destination_identity: str,
        credentials: Mapping[str, str],
    ) -> ReportTransport:
        """Return the exact configured transport or raise if unavailable."""
        ...


@dataclass(frozen=True, slots=True)
class CompositionDependencies:
    """Injected execution seams; the user-facing CLI exposes none of them."""

    secret_resolver: SecretResolver | None = None
    triage_runner_factory: TriageRunnerFactory | None = None
    report_transport_factory: ReportTransportFactory | None = None


@dataclass(frozen=True, slots=True)
class ExecutionOptions:
    """Execution-owned secret allowlists and mounted-secret location."""

    mounted_secret_dir: Path | None = None
    allowed_secret_environment: frozenset[str] = frozenset()
    allowed_secret_files: frozenset[str] = frozenset()


_DEFAULT_OPTIONS = ExecutionOptions()
_DEFAULT_DEPENDENCIES = CompositionDependencies()


async def execute_invocation(
    configuration: OperatorConfiguration,
    invocation: (
        PrepareInvocation
        | TriageInvocation
        | ReportBuildInvocation
        | ReportSubmitInvocation
    ),
    *,
    options: ExecutionOptions = _DEFAULT_OPTIONS,
    dependencies: CompositionDependencies = _DEFAULT_DEPENDENCIES,
) -> OperationOutcome:
    """Execute one already-decoded finite invocation inside an existing loop."""
    _configuration_gate(configuration, invocation.configuration_version)
    if isinstance(invocation, PrepareInvocation):
        return await _prepare(configuration, invocation)
    if isinstance(invocation, TriageInvocation):
        return await _triage(configuration, invocation, options, dependencies)
    if isinstance(invocation, ReportBuildInvocation):
        return await _report_build(configuration, invocation)
    return await _report_submit(configuration, invocation, options, dependencies)


async def reconcile_invocation(
    configuration: OperatorConfiguration,
    invocation: ReportReconcileInvocation,
    *,
    options: ExecutionOptions = _DEFAULT_OPTIONS,
    dependencies: CompositionDependencies = _DEFAULT_DEPENDENCIES,
):
    """Reconcile one exact unknown report effect without constructing transport."""
    del options, dependencies
    _configuration_gate(configuration, invocation.configuration_version)
    operation = _report_submit_operation(configuration)
    if invocation.plan.policy_ref != operation.policy_ref:
        raise ValueError("reconciliation policy does not match trusted configuration")
    if invocation.plan.code_version != configuration.code_version:
        raise ValueError(
            "reconciliation code version does not match trusted configuration"
        )
    request = OperationRequest(
        execution=ExecutionIdentity(invocation.execution),
        caller=invocation.caller,
        capability=PhaseCapability.REPORT_SUBMIT,
        target_inputs=(invocation.plan.report_ref, invocation.plan.policy_ref),
        authority_ref=invocation.authority_ref,
    )
    if not any(item.admits(request) for item in configuration.admissions):
        raise PermissionError("reconciliation authority is not trusted")
    persistence = await _open(configuration)
    try:
        return await ReportReconciler(persistence).reconcile(
            invocation.plan,
            execution=request.execution,
        )
    finally:
        await persistence.close()


async def load_and_execute(
    config_file: Path,
    invocation: (
        PrepareInvocation
        | TriageInvocation
        | ReportBuildInvocation
        | ReportSubmitInvocation
    ),
    *,
    mounted_secret_dir: Path | None = None,
    allowed_secret_environment: frozenset[str] = frozenset(),
    allowed_secret_files: frozenset[str] = frozenset(),
    dependencies: CompositionDependencies = _DEFAULT_DEPENDENCIES,
) -> OperationOutcome:
    """Load configuration and execute without creating or nesting an event loop."""
    configuration = load_operator_configuration(
        config_file,
        mounted_secret_dir=mounted_secret_dir,
    )
    return await execute_invocation(
        configuration,
        invocation,
        options=ExecutionOptions(
            mounted_secret_dir=mounted_secret_dir,
            allowed_secret_environment=allowed_secret_environment,
            allowed_secret_files=allowed_secret_files,
        ),
        dependencies=dependencies,
    )


async def _prepare(
    configuration: OperatorConfiguration,
    invocation: PrepareInvocation,
) -> OperationOutcome:
    operation = configuration.operation(PhaseCapability.PREPARE)
    if not isinstance(operation, PreparationOperationData):
        raise TypeError("trusted preparation configuration is unavailable")
    plan = operation.plan(
        mode=invocation.mode,
        attempt=AttemptIdentity(invocation.attempt),
        selections=invocation.selections,
    )
    request = _request(
        invocation,
        PhaseCapability.PREPARE,
        tuple(item.source for item in plan.selections),
    )
    source_config = configuration.source_reader_config()
    persistence = await _open(configuration)
    try:
        application = Application(
            persistence,
            trusted_admissions=configuration.admissions,
            prepare_factory=lambda: PreparationHandler(
                persistence,
                SavedSourceReader(source_config),
                plan,
            ),
        )
        return await application.run(request)
    finally:
        await persistence.close()


async def _triage(
    configuration: OperatorConfiguration,
    invocation: TriageInvocation,
    options: ExecutionOptions,
    dependencies: CompositionDependencies,
) -> OperationOutcome:
    operation = configuration.operation(PhaseCapability.TRIAGE)
    if not isinstance(operation, TriageOperationData):
        raise TypeError("trusted triage configuration is unavailable")
    plan = invocation.plan.validated()
    producer = operation.producer_config(
        plan=plan,
        capture_time=invocation.capture_time,
        expected_parameters=invocation.parameters,
        claim_key=invocation.claim_key,
    )
    request = _request(
        invocation,
        PhaseCapability.TRIAGE,
        producer.plan.expected_targets,
    )
    persistence = await _open(configuration)
    resolver = dependencies.secret_resolver or _resolver(options)
    runner_factory = dependencies.triage_runner_factory or _airunner
    try:

        def factory() -> TriageHandler:
            credentials = _credentials(
                configuration,
                operation.secret_binding_ids,
                SecretPurpose.AI,
                resolver,
            )
            runtime = operation.runtime_isolation(credentials)
            runner = runner_factory(operation.trusted_policy, runtime)
            return TriageHandler(persistence, producer, runner)

        application = Application(
            persistence,
            trusted_admissions=configuration.admissions,
            triage_factory=factory,
        )
        return await application.run(request)
    finally:
        await persistence.close()


async def _report_build(
    configuration: OperatorConfiguration,
    invocation: ReportBuildInvocation,
) -> OperationOutcome:
    operation = _report_operation(configuration)
    handler_config = operation.handler_config(
        report_ref=invocation.report_ref,
        result_id=invocation.result_id,
        semantic_data_id=invocation.semantic_data_id,
        selection_result_id=invocation.selection_result_id,
        selection_semantic_data_id=invocation.selection_semantic_data_id,
        attempt=AttemptIdentity(invocation.attempt),
        expected_parameters=invocation.parameters,
    )
    request = _request(
        invocation,
        PhaseCapability.REPORT_BUILD,
        invocation.selection_plan.request_targets,
    )
    persistence = await _open(configuration)
    try:
        application = Application(
            persistence,
            trusted_admissions=configuration.admissions,
            report_build_factory=lambda: ReportBuildHandler(
                policy=operation.policy,
                selection_plan=invocation.selection_plan,
                persistence=persistence,
                renderer_config=operation.renderer,
                config=handler_config,
                history_resolver=DeliveryReportHistoryResolver(persistence),
            ),
        )
        return await application.run(request)
    finally:
        await persistence.close()


async def _report_submit(
    configuration: OperatorConfiguration,
    invocation: ReportSubmitInvocation,
    options: ExecutionOptions,
    dependencies: CompositionDependencies,
) -> OperationOutcome:
    submit = _report_submit_operation(configuration)
    report = _report_operation(configuration)
    plan = invocation.plan
    if (
        plan.policy_ref != submit.policy_ref
        or plan.policy_ref != report.policy.policy_ref
    ):
        raise ValueError("submission policy does not match trusted configuration")
    destination = report.policy.destination
    if (
        plan.owner_identity != destination.owner_identity
        or plan.destination_identity != destination.destination_identity
    ):
        raise ValueError("submission destination does not match trusted configuration")
    request = _request(
        invocation,
        PhaseCapability.REPORT_SUBMIT,
        (plan.report_ref, plan.policy_ref),
    )
    persistence = await _open(configuration)
    resolver = dependencies.secret_resolver or _resolver(options)
    transport_factory = dependencies.report_transport_factory
    try:
        if transport_factory is None:
            application = Application(
                persistence,
                trusted_admissions=configuration.admissions,
            )
            return await application.run(request)

        def factory() -> ReportSubmissionHandler:
            credentials = _credentials(
                configuration,
                submit.secret_binding_ids,
                SecretPurpose.REPORT,
                resolver,
            )
            transport = transport_factory(
                submit,
                destination.owner_identity,
                destination.destination_identity,
                credentials,
            )
            return ReportSubmissionHandler(
                plan=plan,
                config=SubmissionHandlerConfig(
                    attempt=AttemptIdentity(invocation.attempt),
                    code_version=configuration.code_version,
                    timeout_seconds=invocation.timeout_seconds,
                    claim_lease_seconds=invocation.claim_lease_seconds,
                ),
                persistence=persistence,
                transport=transport,
            )

        application = Application(
            persistence,
            trusted_admissions=configuration.admissions,
            report_submit_factory=factory,
        )
        return await application.run(request)
    finally:
        await persistence.close()


def _request(
    invocation: PrepareInvocation
    | TriageInvocation
    | ReportBuildInvocation
    | ReportSubmitInvocation,
    capability: PhaseCapability,
    targets: tuple,
) -> OperationRequest:
    return OperationRequest(
        execution=ExecutionIdentity(invocation.execution),
        caller=invocation.caller,
        capability=capability,
        target_inputs=targets,
        authority_ref=invocation.authority_ref,
        parameters=invocation.parameters,
    )


def _configuration_gate(configuration: OperatorConfiguration, version: str) -> None:
    if version != configuration.version:
        raise ValueError("invocation configuration version does not match")


def _report_operation(configuration: OperatorConfiguration) -> ReportOperationData:
    operation = configuration.operation(PhaseCapability.REPORT_BUILD)
    if not isinstance(operation, ReportOperationData):
        raise TypeError("trusted report configuration is unavailable")
    return operation


def _report_submit_operation(
    configuration: OperatorConfiguration,
) -> ReportSubmitOperationData:
    operation = configuration.operation(PhaseCapability.REPORT_SUBMIT)
    if not isinstance(operation, ReportSubmitOperationData):
        raise TypeError("trusted report submission configuration is unavailable")
    return operation


async def _open(configuration: OperatorConfiguration) -> Phase1Persistence:
    return await Phase1Persistence.open(
        configuration.database_url,
        registry=ResultSchemaRegistry.phase1(),
        semantic_registry=SemanticDataRegistry.phase1(),
    )


def _resolver(options: ExecutionOptions) -> SecretResolver:
    return SecretResolver(
        allowed_environment=options.allowed_secret_environment,
        allowed_files=options.allowed_secret_files,
        mounted_secret_dir=options.mounted_secret_dir,
    )


def _credentials(
    configuration: OperatorConfiguration,
    binding_ids: tuple[str, ...],
    purpose: SecretPurpose,
    resolver: SecretResolver,
) -> dict[str, str]:
    values: dict[str, str] = {}
    for binding_id in binding_ids:
        binding = configuration.secret_binding(binding_id)
        if binding.purpose is not purpose or binding.logical_name in values:
            raise ValueError("credential binding does not match execution purpose")
        values[binding.logical_name] = resolver.resolve(binding).get_secret_value()
    if not values:
        raise ValueError("configured execution credentials are unavailable")
    return values


def _airunner(policy: TrustedPolicy, runtime: RuntimeIsolation) -> TriageRunner:
    return cast(TriageRunner, AIRunner(policy, runtime))
