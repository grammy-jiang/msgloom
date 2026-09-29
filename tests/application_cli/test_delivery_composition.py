"""Explicit report submission and evidence-only reconciliation composition."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from msgloom.cli.composition import (
    CompositionDependencies,
    execute_invocation,
    reconcile_invocation,
)
from msgloom.cli.models import ReportReconcileInvocation, ReportSubmitInvocation
from msgloom.configuration import SecretResolver, load_operator_configuration
from msgloom.contracts import (
    AttemptIdentity,
    ExternalEffectState,
    ResultSchemaRegistry,
    TerminalStatus,
)
from msgloom.delivery import ReportReconciliationPlan, submission_claim_key
from msgloom.persistence import Phase1Persistence, SemanticDataRegistry
from tests.application_cli.helpers import minimal_config
from tests.delivery.helpers import (
    RecordingTransport,
    build_report,
    submission_plan,
)
from tests.reporting.helpers import policy


def _configuration(tmp_path: Path):
    config_path = minimal_config(tmp_path / "operator.toml", ("a5_report_submit",))
    report_policy = policy()
    return load_operator_configuration(
        config_path,
        command_options={
            "secrets": [
                {
                    "binding_id": "report-token",
                    "purpose": "report",
                    "logical_name": "transport-token",
                    "source": "environment",
                    "locator": "SYNTHETIC_REPORT_TOKEN",
                }
            ],
            "report": {
                "policy": report_policy.model_dump(mode="json"),
                "renderer": {
                    "max_part_bytes": 65536,
                    "max_total_bytes": 262144,
                    "max_parts": 8,
                },
                "max_input_bytes": 4 * 1024 * 1024,
                "timeout_seconds": 20.0,
                "claim_lease_seconds": 30.0,
                "transport": {
                    "transport_ref": {
                        "kind": "report-transport",
                        "identity": "synthetic-test-transport",
                        "version": "1",
                    },
                    "secret_binding_ids": ["report-token"],
                },
            },
        },
    )


def test_submission_requires_factory_and_reconciliation_never_sends(
    tmp_path: Path,
) -> None:
    """Keep missing transport blocked and recovery strictly evidence-only."""
    configuration = _configuration(tmp_path)
    resolver = SecretResolver(
        allowed_environment={"SYNTHETIC_REPORT_TOKEN"},
        allowed_files=set(),
        mounted_secret_dir=None,
        environ={"SYNTHETIC_REPORT_TOKEN": "synthetic-token"},
    )

    async def exercise() -> None:
        seed = await Phase1Persistence.open(
            configuration.database_url,
            registry=ResultSchemaRegistry.phase1(),
            semantic_registry=SemanticDataRegistry.phase1(),
        )
        try:
            report_ref, report = await build_report(seed)
        finally:
            await seed.close()

        blocked_plan = submission_plan(report_ref, report, suffix="blocked")
        blocked = ReportSubmitInvocation(
            configuration_version=configuration.version,
            execution="submit-blocked",
            attempt="submit-blocked-attempt",
            caller="operator-cli",
            authority_ref="owner-approved",
            parameters=blocked_plan.expected_parameters,
            plan=blocked_plan,
            timeout_seconds=2.0,
            claim_lease_seconds=3.0,
        )
        blocked_outcome = await execute_invocation(configuration, blocked)
        if blocked_outcome.status is not TerminalStatus.BLOCKED:
            pytest.fail("missing report transport was not an honest blocked outcome")
        if blocked_outcome.external_effect is not ExternalEffectState.NONE:
            pytest.fail("missing transport incorrectly created effect uncertainty")

        uncertain_transport = RecordingTransport(TimeoutError())
        uncertain_plan = submission_plan(report_ref, report, suffix="unknown")
        uncertain = blocked.model_copy(
            update={
                "execution": "submit-unknown",
                "attempt": "submit-unknown-attempt",
                "plan": uncertain_plan,
            }
        )

        def transport_factory(
            operation, owner_identity, destination_identity, credentials
        ):
            del operation, owner_identity, destination_identity, credentials
            return uncertain_transport

        uncertain_outcome = await execute_invocation(
            configuration,
            uncertain,
            dependencies=CompositionDependencies(
                secret_resolver=resolver,
                report_transport_factory=transport_factory,
            ),
        )
        if uncertain_outcome.external_effect is not ExternalEffectState.UNKNOWN:
            pytest.fail(
                f"uncertain provider call did not retain unknown effect: {uncertain_outcome}"
            )

        store = await Phase1Persistence.open(
            configuration.database_url,
            registry=ResultSchemaRegistry.phase1(),
            semantic_registry=SemanticDataRegistry.phase1(),
        )
        try:
            key = submission_claim_key(
                report.report_ref.identity,
                report.report_ref.version,
                report.policy_ref.identity,
                report.policy_ref.version,
                1,
            )
            inspection = await store.inspect_claim(key)
            target = inspection.current_token
            if target is None:
                pytest.fail("unknown submission did not retain its exact token")
        finally:
            await store.close()

        reconciliation = ReportReconciliationPlan(
            identity="reconcile-cli-unknown",
            target=target,
            report_ref=report.report_ref,
            policy_ref=report.policy_ref,
            part_number=1,
            decision=ExternalEffectState.UNKNOWN,
            provider_evidence=(),
            recovery_attempt=AttemptIdentity("recovery-cli-attempt"),
            recovery_result_id="recovery-cli-result",
            code_version=configuration.code_version,
            claim_lease_seconds=10.0,
        )
        before = len(uncertain_transport.calls)
        result = await reconcile_invocation(
            configuration,
            ReportReconcileInvocation(
                configuration_version=configuration.version,
                execution="reconcile-cli-execution",
                caller="operator-cli",
                authority_ref="owner-approved",
                plan=reconciliation,
            ),
        )
        if result.decision is not ExternalEffectState.UNKNOWN:
            pytest.fail("evidence-only reconciliation changed the supplied decision")
        if len(uncertain_transport.calls) != before:
            pytest.fail("reconciliation performed an external send")

    asyncio.run(exercise())
