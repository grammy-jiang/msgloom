"""Trusted immutable configuration for the finite A3 producer."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from msgloom.ai import AttemptLimits, TrustedPolicy
from msgloom.contracts import ResultRef, VersionRef
from msgloom.preparation.filtering import FilterConfig
from msgloom.triage import TopicAllocation, TriageRuleConfig
from msgloom.triage_input import (
    SourceRoleBinding,
    TriageInputConfig,
    TrustedInputVersions,
)
from msgloom.working_context import WorkingContextConfig


class TriageMode(StrEnum):
    """Choose live context capture or exact saved replay."""

    LIVE = "live"
    REPLAY = "replay"


@dataclass(frozen=True, slots=True)
class TriageReplayPlan:
    """Freeze every saved input and identity choice for one A3 execution."""

    expected_targets: tuple[VersionRef, ...]
    prepared_results: tuple[ResultRef, ...]
    filter_results: tuple[ResultRef, ...]
    group_results: tuple[ResultRef, ...]
    prior_triage_results: tuple[ResultRef, ...]
    roles: tuple[SourceRoleBinding, ...]
    topic_allocations: tuple[TopicAllocation, ...]
    mode: TriageMode
    replay_context_result: ResultRef | None = None

    def __post_init__(self) -> None:
        if not self.expected_targets:
            raise ValueError("triage plan requires exact target references")
        for values, name in (
            (self.expected_targets, "target"),
            (self.prepared_results, "prepared result"),
            (self.filter_results, "filter result"),
            (self.group_results, "group result"),
            (self.roles, "source role"),
        ):
            if not values:
                raise ValueError(f"triage plan requires {name} bindings")
            if len(values) != len(set(values)):
                raise ValueError(f"triage plan {name} bindings must be unique")
        if len(self.topic_allocations) != len(set(self.topic_allocations)):
            raise ValueError("triage plan topic allocations must be unique")
        all_results = (
            *self.prepared_results,
            *self.filter_results,
            *self.group_results,
            *self.prior_triage_results,
        )
        ids = tuple(item.result_id for item in all_results)
        if len(ids) != len(set(ids)):
            raise ValueError("triage plan result identities must be unique")
        if self.mode is TriageMode.REPLAY and self.replay_context_result is None:
            raise ValueError("replay requires an exact saved context result")
        if self.mode is TriageMode.LIVE and self.replay_context_result is not None:
            raise ValueError("live mode cannot name a replay context result")


@dataclass(frozen=True, slots=True)
class TriageProducerConfig:
    """Bind trusted policy, versions, budgets, and one finite replay plan."""

    plan: TriageReplayPlan
    filter_config: FilterConfig
    rule_config: TriageRuleConfig
    input_config: TriageInputConfig
    versions: TrustedInputVersions
    working_context_config: WorkingContextConfig | None
    capture_time: datetime | None
    prompt_text: str
    trusted_policy: TrustedPolicy
    attempt_limits: AttemptLimits
    expected_parameters: tuple[tuple[str, str], ...]
    claim_key: str
    configuration_version: str
    code_version: str
    lease_seconds: float
    max_upstream_results: int
    max_upstream_bytes: int
    max_parts: int
    max_attempts_per_part: int = 1

    def __post_init__(self) -> None:
        if not self.claim_key.strip():
            raise ValueError("claim key must be non-empty")
        if not self.configuration_version.strip() or not self.code_version.strip():
            raise ValueError("producer versions must be non-empty")
        if not self.prompt_text.strip():
            raise ValueError("prompt text must be non-empty")
        keys = tuple(key for key, _value in self.expected_parameters)
        if len(keys) != len(set(keys)):
            raise ValueError("trusted parameters must not contain duplicate keys")
        for value, name in (
            (self.max_upstream_results, "upstream result"),
            (self.max_upstream_bytes, "upstream byte"),
            (self.max_parts, "part"),
            (self.max_attempts_per_part, "attempt"),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"maximum {name} budget must be positive")
        if self.max_attempts_per_part != 1:
            raise ValueError("automatic AI retries are not supported")
        if not math.isfinite(self.lease_seconds) or self.lease_seconds <= 0:
            raise ValueError("claim lease must be finite and positive")
        required_lease = self.max_parts * self.attempt_limits.timeout_seconds
        if self.lease_seconds < required_lease:
            raise ValueError("claim lease is shorter than the finite AI budget")
        if self.input_config.version != self.versions.configuration:
            raise ValueError("input configuration version binding is invalid")
        if self.plan.mode is TriageMode.LIVE:
            if self.working_context_config is None or self.capture_time is None:
                raise ValueError("live mode requires configured context capture")
            if (
                self.capture_time.tzinfo is None
                or self.capture_time.utcoffset() is None
            ):
                raise ValueError("capture time must be timezone-aware")
        elif self.working_context_config is not None or self.capture_time is not None:
            raise ValueError("replay mode cannot recapture working context")
