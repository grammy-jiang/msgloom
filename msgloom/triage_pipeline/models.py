"""Trusted immutable configuration for the finite A3 producer."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from hashlib import sha256

from pydantic import BaseModel, ValidationError

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


def _revalidate[T: BaseModel](value: T, expected: type[T]) -> T:
    """Return a detached strict copy, rejecting model-copy corruption."""
    try:
        payload = value.model_dump_json(round_trip=True, warnings="error")
        return expected.model_validate_json(payload, strict=True)
    except (AttributeError, TypeError, ValueError, ValidationError):
        raise ValueError("trusted triage configuration failed validation") from None


def _version_ref(value: VersionRef) -> VersionRef:
    if not isinstance(value, VersionRef):
        raise TypeError("trusted version reference failed validation")
    return VersionRef(str(value.kind), str(value.identity), str(value.version))


def _result_ref(value: ResultRef) -> ResultRef:
    if not isinstance(value, ResultRef):
        raise TypeError("trusted result reference failed validation")
    return ResultRef(str(value.result_id), str(value.kind), str(value.schema_version))


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

    def validated(self) -> TriageReplayPlan:
        """Reconstruct all nested strict models at the operation boundary."""
        checked = TriageReplayPlan(
            expected_targets=tuple(
                _version_ref(item) for item in self.expected_targets
            ),
            prepared_results=tuple(_result_ref(item) for item in self.prepared_results),
            filter_results=tuple(_result_ref(item) for item in self.filter_results),
            group_results=tuple(_result_ref(item) for item in self.group_results),
            prior_triage_results=tuple(
                _result_ref(item) for item in self.prior_triage_results
            ),
            roles=tuple(_revalidate(item, SourceRoleBinding) for item in self.roles),
            topic_allocations=tuple(
                _revalidate(item, TopicAllocation) for item in self.topic_allocations
            ),
            mode=TriageMode(self.mode),
            replay_context_result=(
                None
                if self.replay_context_result is None
                else _result_ref(self.replay_context_result)
            ),
        )
        if {item.source_ref for item in checked.roles} != set(checked.expected_targets):
            raise ValueError("source roles must exactly cover request targets")
        keys = tuple(item.allocation_key for item in checked.topic_allocations)
        topics = tuple(item.topic_ref for item in checked.topic_allocations)
        assessments = tuple(item.assessment_ref for item in checked.topic_allocations)
        if len(keys) != len(set(keys)):
            raise ValueError("topic allocation keys must be unique")
        if len(topics) != len(set(topics)) or len(assessments) != len(set(assessments)):
            raise ValueError("topic and assessment identities must be unique")
        if any(item.kind != "topic-assessment" for item in assessments):
            raise ValueError("assessment references must use topic-assessment kind")
        return checked


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
    operation_timeout_seconds: float
    cleanup_margin_seconds: float
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
        for value, name in (
            (self.lease_seconds, "claim lease"),
            (self.operation_timeout_seconds, "operation timeout"),
            (self.cleanup_margin_seconds, "cleanup margin"),
        ):
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        acceptance = self.operation_timeout_seconds - self.cleanup_margin_seconds
        if acceptance <= 0:
            raise ValueError("operation timeout must leave a cleanup margin")
        if self.attempt_limits.timeout_seconds > acceptance:
            raise ValueError("attempt timeout exceeds operation acceptance budget")
        if self.lease_seconds < self.operation_timeout_seconds:
            raise ValueError("claim lease must cover the total operation budget")
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

    def semantic_fingerprint(self) -> str:
        """Hash all validated semantic choices that can affect A3 output."""
        schema = self.trusted_policy.schema_for(self.versions.output_schema)
        payload = {
            "filter": self.filter_config.model_dump(mode="json"),
            "rule": self.rule_config.model_dump(mode="json"),
            "input": self.input_config.model_dump(mode="json"),
            "versions": self.versions.model_dump(mode="json"),
            "roles": [item.model_dump(mode="json") for item in self.plan.roles],
            "allocations": [
                item.model_dump(mode="json") for item in self.plan.topic_allocations
            ],
            "prompt_text": self.prompt_text,
            "schema": schema,
            "model": self.trusted_policy.models[self.versions.model],
            "limits": {
                "timeout_seconds": self.attempt_limits.timeout_seconds,
                "max_input_bytes": self.attempt_limits.max_input_bytes,
                "max_context_bytes": self.attempt_limits.max_context_bytes,
                "max_prompt_bytes": self.attempt_limits.max_prompt_bytes,
                "max_output_bytes": self.attempt_limits.max_output_bytes,
                "max_trace_events": self.attempt_limits.max_trace_events,
                "max_trace_event_bytes": self.attempt_limits.max_trace_event_bytes,
                "max_turns": self.attempt_limits.max_turns,
                "max_tokens": self.attempt_limits.max_tokens,
            },
        }
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return sha256(encoded).hexdigest()

    def validated(self) -> TriageProducerConfig:
        """Return a detached, fully revalidated operation configuration."""
        plan = self.plan.validated()
        versions = _revalidate(self.versions, TrustedInputVersions)
        expected_kinds = (
            (versions.prompt, "prompt"),
            (versions.model, "model"),
            (versions.output_schema, "schema"),
            (versions.configuration, "triage_input_config"),
        )
        if any(ref.kind != kind for ref, kind in expected_kinds):
            raise ValueError("trusted semantic version kind is invalid")
        schemas = {}
        for ref in self.trusted_policy.schemas:
            schema = self.trusted_policy.schema_for(ref)
            if schema is None:
                raise ValueError("trusted policy schema snapshot is invalid")
            schemas[ref] = schema
        policy = TrustedPolicy(
            schemas=schemas,
            models=dict(self.trusted_policy.models),
        )
        if policy.schema_for(versions.output_schema) is None:
            raise ValueError("trusted policy does not contain the output schema")
        if versions.model not in policy.models:
            raise ValueError("trusted policy does not contain the selected model")
        limits = AttemptLimits(
            timeout_seconds=self.attempt_limits.timeout_seconds,
            max_input_bytes=self.attempt_limits.max_input_bytes,
            max_context_bytes=self.attempt_limits.max_context_bytes,
            max_prompt_bytes=self.attempt_limits.max_prompt_bytes,
            max_output_bytes=self.attempt_limits.max_output_bytes,
            max_trace_events=self.attempt_limits.max_trace_events,
            max_trace_event_bytes=self.attempt_limits.max_trace_event_bytes,
            max_turns=self.attempt_limits.max_turns,
            max_tokens=self.attempt_limits.max_tokens,
        )
        context = (
            None
            if self.working_context_config is None
            else _revalidate(self.working_context_config, WorkingContextConfig)
        )
        return TriageProducerConfig(
            plan=plan,
            filter_config=_revalidate(self.filter_config, FilterConfig),
            rule_config=_revalidate(self.rule_config, TriageRuleConfig),
            input_config=_revalidate(self.input_config, TriageInputConfig),
            versions=versions,
            working_context_config=context,
            capture_time=self.capture_time,
            prompt_text=str(self.prompt_text),
            trusted_policy=policy,
            attempt_limits=limits,
            expected_parameters=tuple(
                (str(key), str(value)) for key, value in self.expected_parameters
            ),
            claim_key=str(self.claim_key),
            configuration_version=str(self.configuration_version),
            code_version=str(self.code_version),
            lease_seconds=float(self.lease_seconds),
            operation_timeout_seconds=float(self.operation_timeout_seconds),
            cleanup_margin_seconds=float(self.cleanup_margin_seconds),
            max_upstream_results=self.max_upstream_results,
            max_upstream_bytes=self.max_upstream_bytes,
            max_parts=self.max_parts,
            max_attempts_per_part=self.max_attempts_per_part,
        )
