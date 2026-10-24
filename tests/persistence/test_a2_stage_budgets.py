"""C0-22: stage storage budget and retention policy (pure, no database)."""

from __future__ import annotations

import dataclasses

import pytest

from msgloom.a2_kedro.contracts.codec import A2ContractError
from msgloom.a2_kedro.contracts.schema_ids import STAGE_SCHEMAS
from msgloom.persistence.a2_acceptance_models import MAX_PAYLOAD_BYTES
from msgloom.persistence.a2_stage_budgets import (
    DEFAULT_POLICY,
    A2BudgetConfigError,
    A2BudgetExceeded,
    ArtifactBudget,
    RetentionAction,
    StageBudgetPolicy,
    check_artifact,
    retention_action,
)

KIND = "zones"


def check(condition: bool, message: str) -> None:
    """Fail the test with ``message`` unless ``condition`` holds."""
    if not condition:
        pytest.fail(message)


def small_policy(
    *, entries: int = 3, workset_bytes: int = 100, payload: int = 40
) -> StageBudgetPolicy:
    """Return a tiny policy that covers every approved kind."""
    return StageBudgetPolicy(
        artifacts=tuple(
            ArtifactBudget(kind, payload, 10, 20) for kind in STAGE_SCHEMAS
        ),
        max_entries_per_workset=entries,
        max_bytes_per_workset=workset_bytes,
    )


def reason_of(call, *args: object) -> str:  # type: ignore[no-untyped-def]
    """Return the reason code of the budget error ``call`` raises."""
    try:
        call(*args)
    except A2BudgetExceeded as error:
        return error.reason
    pytest.fail("expected A2BudgetExceeded")


def test_default_policy_is_finite_and_covers_every_kind() -> None:
    kinds = {budget.kind for budget in DEFAULT_POLICY.artifacts}
    check(kinds == set(STAGE_SCHEMAS), "every approved kind needs a budget")
    for budget in DEFAULT_POLICY.artifacts:
        check(0 < budget.max_payload_bytes <= MAX_PAYLOAD_BYTES, budget.kind)
        check(
            budget.max_payload_bytes <= DEFAULT_POLICY.max_bytes_per_workset,
            budget.kind,
        )
        check(0 < budget.payload_days < budget.digest_days, budget.kind)


def test_policy_is_frozen() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        DEFAULT_POLICY.max_entries_per_workset = 1  # type: ignore[misc]


def test_artifact_exactly_at_payload_limit_passes() -> None:
    policy = small_policy()
    check_artifact(KIND, 40, 0, 0, policy)


def test_artifact_one_byte_over_payload_limit_is_refused() -> None:
    policy = small_policy()
    reason = reason_of(check_artifact, KIND, 41, 0, 0, policy)
    check(reason == "payload-too-large", reason)


def test_last_allowed_entry_passes_and_next_is_refused() -> None:
    policy = small_policy(entries=3)
    check_artifact(KIND, 1, 2, 0, policy)
    reason = reason_of(check_artifact, KIND, 1, 3, 0, policy)
    check(reason == "workset-entries-exceeded", reason)


def test_workset_bytes_at_limit_passes_and_one_over_is_refused() -> None:
    policy = small_policy(workset_bytes=100, payload=40)
    check_artifact(KIND, 40, 1, 60, policy)
    reason = reason_of(check_artifact, KIND, 40, 1, 61, policy)
    check(reason == "workset-bytes-exceeded", reason)


def test_default_policy_accepts_the_largest_artifact_in_an_empty_workset() -> None:
    check_artifact("parsed_parts", MAX_PAYLOAD_BYTES, 0, 0)
    reason = reason_of(check_artifact, "parsed_parts", MAX_PAYLOAD_BYTES + 1, 0, 0)
    check(reason == "payload-too-large", reason)


def test_unknown_and_historical_kind_is_refused() -> None:
    check(reason_of(check_artifact, "mystery", 1, 0, 0) == "unknown-kind", "kind")
    check(reason_of(retention_action, "mystery", 1) == "unknown-kind", "kind")


@pytest.mark.parametrize(
    "args",
    [
        (0, 0, 0),
        (-1, 0, 0),
        (1, -1, 0),
        (1, 0, -1),
        (True, 0, 0),
        (1.5, 0, 0),
    ],
)
def test_invalid_measurements_are_refused(args: tuple[object, ...]) -> None:
    with pytest.raises(A2BudgetExceeded):
        check_artifact(KIND, *args)  # type: ignore[arg-type]


def test_error_family_is_the_contract_error() -> None:
    check(issubclass(A2BudgetExceeded, A2ContractError), "must be contract error")
    check(issubclass(A2BudgetConfigError, A2ContractError), "must be contract error")


def test_error_text_carries_the_reason_code_only() -> None:
    try:
        check_artifact(KIND, 10**9, 0, 0)
    except A2BudgetExceeded as error:
        check(str(error) == error.reason == "payload-too-large", str(error))
        return
    pytest.fail("expected A2BudgetExceeded")


@pytest.mark.parametrize("bad", [0, -1, MAX_PAYLOAD_BYTES + 1, True, 1.5])
def test_artifact_budget_rejects_bad_payload_limit(bad: object) -> None:
    with pytest.raises(A2BudgetConfigError):
        ArtifactBudget(KIND, bad, 1, 2)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("payload", "digest"),
    [(0, 5), (-1, 5), (1, 0), (1, -3), (5, 5), (6, 5), (1, 3651)],
)
def test_artifact_budget_rejects_bad_retention_ages(payload: int, digest: int) -> None:
    with pytest.raises(A2BudgetConfigError):
        ArtifactBudget(KIND, 10, payload, digest)


def test_artifact_budget_rejects_unknown_kind() -> None:
    with pytest.raises(A2BudgetConfigError):
        ArtifactBudget("prepared_v1_history", 10, 1, 2)


@pytest.mark.parametrize("entries", [0, -1, True])
def test_policy_rejects_bad_entry_limit(entries: int) -> None:
    with pytest.raises(A2BudgetConfigError):
        small_policy(entries=entries)


@pytest.mark.parametrize("total", [0, -1])
def test_policy_rejects_bad_workset_byte_limit(total: int) -> None:
    with pytest.raises(A2BudgetConfigError):
        small_policy(workset_bytes=total, payload=1)


def test_policy_rejects_artifact_limit_above_workset_limit() -> None:
    with pytest.raises(A2BudgetConfigError) as caught:
        small_policy(workset_bytes=39, payload=40)
    check(caught.value.reason == "artifact-limit-above-workset-limit", "reason")


def test_policy_rejects_missing_duplicate_and_empty_kinds() -> None:
    full = DEFAULT_POLICY.artifacts
    for artifacts in (full[:-1], full + full[:1], ()):
        with pytest.raises(A2BudgetConfigError):
            StageBudgetPolicy(artifacts, 10, 512 * 1024 * 1024)


def test_retention_boundaries() -> None:
    policy = small_policy()  # payload 10 days, digest 20 days
    expected = [
        (0, RetentionAction.KEEP),
        (9, RetentionAction.KEEP),
        (10, RetentionAction.DROP_PAYLOAD_KEEP_DIGEST),
        (19, RetentionAction.DROP_PAYLOAD_KEEP_DIGEST),
        (20, RetentionAction.DELETE),
        (10_000, RetentionAction.DELETE),
    ]
    for age, action in expected:
        got = retention_action(KIND, age, policy)
        check(got is action, f"age {age}: {got}")


@pytest.mark.parametrize("age", [-1, True, 1.5])
def test_retention_rejects_bad_age(age: object) -> None:
    with pytest.raises(A2BudgetExceeded):
        retention_action(KIND, age, small_policy())  # type: ignore[arg-type]


def test_default_retention_keeps_digest_longer_than_payload() -> None:
    for budget in DEFAULT_POLICY.artifacts:
        at_payload = retention_action(budget.kind, budget.payload_days)
        at_digest = retention_action(budget.kind, budget.digest_days)
        check(
            at_payload is RetentionAction.DROP_PAYLOAD_KEEP_DIGEST,
            budget.kind,
        )
        check(at_digest is RetentionAction.DELETE, budget.kind)
