"""
Storage budget and retention policy for A2 intermediate stages (C0-22).

CANDIDATE/RESEARCH. This module is pure. It opens no database, reads no
file and is not wired into any store. A caller passes sizes and counts
that it already measured. The functions return nothing or raise.

Budget rules, all explicit, finite and positive (no implicit unlimited):

* ``max_payload_bytes`` per artifact kind. No kind may exceed the
  accepted-stage ceiling :data:`MAX_PAYLOAD_BYTES`.
* ``max_entries_per_workset``: accepted entries one workset may hold.
* ``max_bytes_per_workset``: total payload bytes one workset may hold.
  No single kind may exceed this total.

:func:`check_artifact` takes the counts that already exist in the workset
and tests the state *after* adding the new artifact. A new artifact at
exactly the limit passes. One byte or one entry more is refused.

Retention uses two ages per kind. Before ``payload_days`` the payload and
the digest are kept. From ``payload_days`` up to ``digest_days`` only the
digest-only metadata is kept. From ``digest_days`` the entry is deleted.
Message bodies and addresses never appear in a status, a log line or an
error from this module. Errors carry a short reason code only.

Reading history is not affected. Schema 4 rows and the read-only
historical stage versions are outside this policy (see
``docs/notes/a2-v2-db-storage-budgets.md``).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from msgloom.a2_kedro.contracts.codec import MAX_CANONICAL_BYTES, A2ContractError
from msgloom.a2_kedro.contracts.schema_ids import STAGE_SCHEMAS
from msgloom.persistence.a2_acceptance_models import MAX_PAYLOAD_BYTES
from msgloom.persistence.a2_held_store import MAX_HELD_RECORD_BYTES
from msgloom.persistence.a2_sqlite_store import MAX_RECEIPT_BYTES

_MIB = 1024 * 1024
#: Largest retention age the policy accepts, so a value stays finite.
MAX_RETENTION_DAYS = 3650


class A2StageBudgetError(A2ContractError):
    """
    Base class for stage budget refusals.

    ``reason`` is a short closed code. It never holds payload text, an
    address or a subject.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class A2BudgetConfigError(A2StageBudgetError):
    """A budget policy is zero, negative, unbounded or inconsistent."""


class A2BudgetExceeded(A2StageBudgetError):
    """An artifact would exceed a payload, entry or workset byte limit."""


class RetentionAction(StrEnum):
    """What retention requires for one stored artifact."""

    KEEP = "keep"
    DROP_PAYLOAD_KEEP_DIGEST = "drop_payload_keep_digest"
    DELETE = "delete"


def _require_count(value: object, name: str, upper: int) -> int:
    """Return ``value`` when it is a real int in ``1..upper``."""
    if type(value) is not int:
        raise A2BudgetConfigError(f"{name}-not-int")
    if not 1 <= value <= upper:
        raise A2BudgetConfigError(f"{name}-out-of-range")
    return value


@dataclass(frozen=True, slots=True)
class ArtifactBudget:
    """Payload limit and retention ages for one artifact kind."""

    kind: str
    max_payload_bytes: int
    payload_days: int
    digest_days: int

    def __post_init__(self) -> None:
        if type(self.kind) is not str or self.kind not in STAGE_SCHEMAS:
            raise A2BudgetConfigError("unknown-kind")
        _require_count(self.max_payload_bytes, "max-payload-bytes", MAX_PAYLOAD_BYTES)
        _require_count(self.payload_days, "payload-days", MAX_RETENTION_DAYS)
        _require_count(self.digest_days, "digest-days", MAX_RETENTION_DAYS)
        if self.digest_days <= self.payload_days:
            # Digest-only metadata must outlive the payload.
            raise A2BudgetConfigError("digest-days-not-after-payload-days")


@dataclass(frozen=True, slots=True)
class StageBudgetPolicy:
    """
    Complete, immutable budget for all approved A2 stage kinds.

    Every kind in :data:`STAGE_SCHEMAS` needs exactly one budget. A missing
    kind would mean "unlimited", so it is refused.
    """

    artifacts: tuple[ArtifactBudget, ...]
    max_entries_per_workset: int
    max_bytes_per_workset: int

    def __post_init__(self) -> None:
        _require_count(self.max_entries_per_workset, "max-entries", 1_000_000)
        _require_count(self.max_bytes_per_workset, "max-workset-bytes", 1 << 40)
        if type(self.artifacts) is not tuple or not all(
            type(budget) is ArtifactBudget for budget in self.artifacts
        ):
            raise A2BudgetConfigError("artifacts-not-budget-tuple")
        kinds = [budget.kind for budget in self.artifacts]
        if len(set(kinds)) != len(kinds):
            raise A2BudgetConfigError("duplicate-kind")
        if set(kinds) != set(STAGE_SCHEMAS):
            raise A2BudgetConfigError("kind-set-not-exact")
        for budget in self.artifacts:
            if budget.max_payload_bytes > self.max_bytes_per_workset:
                raise A2BudgetConfigError("artifact-limit-above-workset-limit")

    def budget_for(self, kind: str) -> ArtifactBudget:
        """Return the budget for ``kind`` or raise :exc:`A2BudgetExceeded`."""
        for budget in self.artifacts:
            if budget.kind == kind:
                return budget
        raise A2BudgetExceeded("unknown-kind")


def _budget(kind: str, max_bytes: int, payload: int, digest: int) -> ArtifactBudget:
    return ArtifactBudget(kind, max_bytes, payload, digest)


#: PROPOSED_NEEDS_OWNER: every number below is a proposal. Payload byte
#: caps reuse existing constants where one exists; the rest are proposals.
DEFAULT_POLICY = StageBudgetPolicy(
    artifacts=(
        _budget("frozen_source_selection", MAX_CANONICAL_BYTES, 30, 365),
        _budget("extracted_components", MAX_PAYLOAD_BYTES, 14, 365),
        _budget("parsed_parts", MAX_PAYLOAD_BYTES, 14, 365),
        _budget("normalized_content", MAX_PAYLOAD_BYTES, 14, 365),
        _budget("zones", 16 * _MIB, 14, 365),
        _budget("native_relations", 16 * _MIB, 14, 365),
        _budget("prepared", MAX_PAYLOAD_BYTES, 30, 365),
        _budget("filter_result", MAX_CANONICAL_BYTES, 30, 365),
        _budget("group_result", MAX_CANONICAL_BYTES, 30, 365),
        _budget("prepared_transitions", 16 * _MIB, 30, 365),
        _budget("a2_input_disposition", MAX_HELD_RECORD_BYTES, 90, 730),
        _budget("a2_result_manifest", MAX_RECEIPT_BYTES, 90, 730),
    ),
    max_entries_per_workset=16384,
    max_bytes_per_workset=512 * _MIB,
)


def _require_measure(value: object, name: str) -> int:
    """Return ``value`` when it is a real int that is zero or more."""
    if type(value) is not int or value < 0:
        raise A2BudgetExceeded(f"{name}-invalid")
    return value


def check_artifact(
    kind: str,
    size_bytes: int,
    entries_in_workset: int,
    bytes_in_workset: int,
    policy: StageBudgetPolicy = DEFAULT_POLICY,
) -> None:
    """
    Raise :exc:`A2BudgetExceeded` unless the new artifact fits the budget.

    ``entries_in_workset`` and ``bytes_in_workset`` count what the workset
    holds *before* this artifact. The check tests the totals after adding
    it: ``entries + 1`` and ``bytes + size_bytes``. Reason codes are
    ``unknown-kind``, ``size-bytes-invalid`` (also zero), ``payload-too-
    large``, ``workset-entries-exceeded`` and ``workset-bytes-exceeded``.
    """
    budget = policy.budget_for(kind)
    size = _require_measure(size_bytes, "size-bytes")
    entries = _require_measure(entries_in_workset, "entries")
    used = _require_measure(bytes_in_workset, "workset-bytes")
    if size < 1:
        raise A2BudgetExceeded("size-bytes-invalid")
    if size > budget.max_payload_bytes:
        raise A2BudgetExceeded("payload-too-large")
    if entries + 1 > policy.max_entries_per_workset:
        raise A2BudgetExceeded("workset-entries-exceeded")
    if used + size > policy.max_bytes_per_workset:
        raise A2BudgetExceeded("workset-bytes-exceeded")


def retention_action(
    kind: str, age_days: int, policy: StageBudgetPolicy = DEFAULT_POLICY
) -> RetentionAction:
    """
    Return the retention action for an artifact of ``kind`` and ``age_days``.

    Below ``payload_days``: KEEP. From ``payload_days`` below
    ``digest_days``: DROP_PAYLOAD_KEEP_DIGEST. From ``digest_days``:
    DELETE. ``age_days`` is whole elapsed days, rounded down by the caller.
    Rounding down delays an action and never brings one forward. A negative
    or non-integer age raises :exc:`A2BudgetExceeded`.
    """
    budget = policy.budget_for(kind)
    age = _require_measure(age_days, "age-days")
    if age < budget.payload_days:
        return RetentionAction.KEEP
    if age < budget.digest_days:
        return RetentionAction.DROP_PAYLOAD_KEEP_DIGEST
    return RetentionAction.DELETE
