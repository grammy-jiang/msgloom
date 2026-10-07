"""Deterministic, replay-safe filtering for immutable prepared records."""

from __future__ import annotations

import json
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from msgloom.contracts import VersionRef
from msgloom.preparation.records import PreparedRecord, PreparedSourceType

FILTER_RESULT_KIND = "filter_result"
FILTER_RESULT_SCHEMA_VERSION = "1"
MAX_FILTER_RESULT_BYTES = 1024 * 1024
MAX_RULES = 256
MAX_ADDRESSES = 128
MAX_PATTERNS = 64
MAX_PATTERN_CHARS = 256
MAX_GUIDANCE_CHARS = 4096
MAX_SOURCE_SCOPES = 32
SOURCE_SCOPE_RELATIONSHIP = "source_scope"


class _FrozenModel(BaseModel):
    """Reject coercion, unknown fields, and mutation at the semantics boundary."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")


class AddressNormalization(StrEnum):
    """Explicit normalization applied before exact address comparison."""

    EXACT = "exact"
    CASEFOLD = "casefold"


class SubjectMatchMode(StrEnum):
    """Linear-time subject operations; regular expressions are not accepted."""

    EXACT = "exact"
    PREFIX = "prefix"
    SUFFIX = "suffix"
    CONTAINS = "contains"


class FilterEffect(StrEnum):
    """Mechanical effect produced by a matching filter rule."""

    INCLUDE = "include"
    EXCLUDE = "exclude"
    GUIDANCE = "guidance"


class FilterOutcome(StrEnum):
    """Visible aggregate outcome without order-based conflict resolution."""

    INCLUDED = "included"
    EXCLUDED = "excluded"
    GUIDANCE = "guidance"
    CONFLICT = "conflict"


class SubjectPattern(_FrozenModel):
    """Bounded subject pattern evaluated with a non-regex string operation."""

    mode: SubjectMatchMode
    value: str
    case_sensitive: bool = False

    @field_validator("value")
    @classmethod
    def _bounded_value(cls, value: str) -> str:
        if not value:
            raise ValueError("subject pattern must be non-empty")
        if len(value) > MAX_PATTERN_CHARS:
            raise ValueError(f"subject pattern exceeds {MAX_PATTERN_CHARS} characters")
        return value


class FilterRule(_FrozenModel):
    """One versioned rule whose populated predicate categories are ANDed."""

    reference: VersionRef
    effect: FilterEffect
    sender_addresses: tuple[str, ...] = ()
    recipient_addresses: tuple[str, ...] = ()
    subject_patterns: tuple[SubjectPattern, ...] = ()
    source_types: tuple[PreparedSourceType, ...] = ()
    source_scopes: tuple[VersionRef, ...] = ()
    not_before: datetime | None = None
    before: datetime | None = None
    guidance: str | None = None

    @field_validator("sender_addresses", "recipient_addresses")
    @classmethod
    def _addresses(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(values) > MAX_ADDRESSES:
            raise ValueError(f"address predicate exceeds {MAX_ADDRESSES} values")
        if len(values) != len(set(values)):
            raise ValueError("address predicates must not contain duplicates")
        for value in values:
            if not value or value != value.strip():
                raise ValueError(
                    "address predicates must be non-empty without outer whitespace"
                )
        return values

    @field_validator("subject_patterns")
    @classmethod
    def _patterns(
        cls, values: tuple[SubjectPattern, ...]
    ) -> tuple[SubjectPattern, ...]:
        if len(values) > MAX_PATTERNS:
            raise ValueError(f"subject predicate exceeds {MAX_PATTERNS} patterns")
        if len(values) != len(set(values)):
            raise ValueError("subject patterns must not contain duplicates")
        return values

    @field_validator("source_types")
    @classmethod
    def _source_types(
        cls, values: tuple[PreparedSourceType, ...]
    ) -> tuple[PreparedSourceType, ...]:
        if len(values) != len(set(values)):
            raise ValueError("source type predicates must not contain duplicates")
        return values

    @field_validator("source_scopes")
    @classmethod
    def _source_scopes(cls, values: tuple[VersionRef, ...]) -> tuple[VersionRef, ...]:
        if len(values) > MAX_SOURCE_SCOPES:
            raise ValueError(
                f"source scope predicate exceeds {MAX_SOURCE_SCOPES} values"
            )
        if len(values) != len(set(values)):
            raise ValueError("source scope predicates must not contain duplicates")
        if any(value.kind != SOURCE_SCOPE_RELATIONSHIP for value in values):
            raise ValueError("source scope references must use kind 'source_scope'")
        return values

    @field_validator("not_before", "before")
    @classmethod
    def _aware_time(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("filter time boundaries must be timezone-aware")
        return value

    @model_validator(mode="after")
    def _complete_rule(self) -> FilterRule:
        predicates = (
            self.sender_addresses,
            self.recipient_addresses,
            self.subject_patterns,
            self.source_types,
            self.source_scopes,
            self.not_before,
            self.before,
        )
        if not any(value for value in predicates):
            raise ValueError("filter rule must declare at least one predicate")
        if (
            self.not_before is not None
            and self.before is not None
            and self.before <= self.not_before
        ):
            raise ValueError("filter before boundary must follow not_before")
        if self.effect is FilterEffect.GUIDANCE:
            if not self.guidance or not self.guidance.strip():
                raise ValueError("guidance rules require non-empty guidance")
            if len(self.guidance) > MAX_GUIDANCE_CHARS:
                raise ValueError(f"guidance exceeds {MAX_GUIDANCE_CHARS} characters")
        elif self.guidance is not None:
            raise ValueError("only guidance rules may carry guidance text")
        return self


class FilterConfig(_FrozenModel):
    """Versioned immutable filter configuration with finite rule bounds."""

    reference: VersionRef
    address_normalization: AddressNormalization
    rules: tuple[FilterRule, ...] = ()

    @model_validator(mode="after")
    def _validate_rules(self) -> FilterConfig:
        if len(self.rules) > MAX_RULES:
            raise ValueError(f"filter configuration exceeds {MAX_RULES} rules")
        refs = tuple(rule.reference for rule in self.rules)
        if len(refs) != len(set(refs)):
            raise ValueError("filter rule references must be unique")
        if self.address_normalization is AddressNormalization.CASEFOLD:
            for rule in self.rules:
                for values in (rule.sender_addresses, rule.recipient_addresses):
                    normalized = tuple(value.casefold() for value in values)
                    if len(normalized) != len(set(normalized)):
                        raise ValueError(
                            "address predicates collide after casefold normalization"
                        )
        return self


class MatchedFilterRule(_FrozenModel):
    """Exact matched rule version and its visible mechanical effect."""

    rule_ref: VersionRef
    effect: FilterEffect
    guidance: str | None = None

    @model_validator(mode="after")
    def _guidance_matches_effect(self) -> MatchedFilterRule:
        if self.effect is FilterEffect.GUIDANCE:
            if not self.guidance or not self.guidance.strip():
                raise ValueError("matched guidance rule requires guidance text")
            if len(self.guidance) > MAX_GUIDANCE_CHARS:
                raise ValueError("matched guidance text exceeds configured bound")
        elif self.guidance is not None:
            raise ValueError("non-guidance match cannot carry guidance text")
        return self


class FilterResult(_FrozenModel):
    """Immutable deterministic result for one exact prepared source version."""

    input: VersionRef
    configuration_ref: VersionRef
    outcome: FilterOutcome
    matched_rules: tuple[MatchedFilterRule, ...]

    @model_validator(mode="after")
    def _consistent_result(self) -> FilterResult:
        if len(self.matched_rules) > MAX_RULES:
            raise ValueError("matched filter rules exceed configured bound")
        refs = tuple(match.rule_ref for match in self.matched_rules)
        if len(refs) != len(set(refs)):
            raise ValueError("matched filter rule references must be unique")
        expected_order = tuple(sorted(self.matched_rules, key=_match_key))
        if self.matched_rules != expected_order:
            raise ValueError("matched filter rules must use canonical order")
        expected = _outcome(self.matched_rules)
        if self.outcome is not expected:
            raise ValueError("filter outcome does not match retained rule effects")
        return self


def _version_key(reference: VersionRef) -> tuple[str, str, str]:
    return (reference.kind, reference.identity, reference.version)


def _match_key(match: MatchedFilterRule) -> tuple[str, str, str, str]:
    return (*_version_key(match.rule_ref), match.effect.value)


def _normalize(value: str, policy: AddressNormalization) -> str:
    if policy is AddressNormalization.CASEFOLD:
        return value.casefold()
    return value


def _subject_matches(subject: str, pattern: SubjectPattern) -> bool:
    candidate = subject if pattern.case_sensitive else subject.casefold()
    expected = pattern.value if pattern.case_sensitive else pattern.value.casefold()
    if pattern.mode is SubjectMatchMode.EXACT:
        return candidate == expected
    if pattern.mode is SubjectMatchMode.PREFIX:
        return candidate.startswith(expected)
    if pattern.mode is SubjectMatchMode.SUFFIX:
        return candidate.endswith(expected)
    return expected in candidate


def _rule_matches(
    record: PreparedRecord, rule: FilterRule, policy: AddressNormalization
) -> bool:
    if rule.sender_addresses:
        if record.sender is None:
            return False
        sender = _normalize(record.sender.identity, policy)
        allowed = {_normalize(value, policy) for value in rule.sender_addresses}
        if sender not in allowed:
            return False
    if rule.recipient_addresses:
        recipients = {
            _normalize(item.party.identity, policy) for item in record.recipients
        }
        required = {_normalize(value, policy) for value in rule.recipient_addresses}
        if recipients.isdisjoint(required):
            return False
    if rule.subject_patterns:
        if record.subject is None:
            return False
        if not any(
            _subject_matches(record.subject, pattern)
            for pattern in rule.subject_patterns
        ):
            return False
    if rule.source_types and record.source_type not in rule.source_types:
        return False
    if rule.source_scopes:
        scopes = {
            item.target
            for item in record.relationships
            if item.kind == SOURCE_SCOPE_RELATIONSHIP
        }
        if scopes.isdisjoint(rule.source_scopes):
            return False
    if rule.not_before is not None and record.source_time < rule.not_before:
        return False
    return rule.before is None or record.source_time < rule.before


def _outcome(matches: tuple[MatchedFilterRule, ...]) -> FilterOutcome:
    effects = {match.effect for match in matches}
    if FilterEffect.INCLUDE in effects and FilterEffect.EXCLUDE in effects:
        return FilterOutcome.CONFLICT
    if FilterEffect.EXCLUDE in effects:
        return FilterOutcome.EXCLUDED
    if FilterEffect.INCLUDE in effects:
        return FilterOutcome.INCLUDED
    if FilterEffect.GUIDANCE in effects:
        return FilterOutcome.GUIDANCE
    return FilterOutcome.INCLUDED


def apply_filters(record: PreparedRecord, config: FilterConfig) -> FilterResult:
    """Evaluate every rule and retain all matches in canonical order."""
    matches = tuple(
        sorted(
            (
                MatchedFilterRule(
                    rule_ref=rule.reference,
                    effect=rule.effect,
                    guidance=rule.guidance,
                )
                for rule in config.rules
                if _rule_matches(record, rule, config.address_normalization)
            ),
            key=_match_key,
        )
    )
    return FilterResult(
        input=record.source,
        configuration_ref=config.reference,
        outcome=_outcome(matches),
        matched_rules=matches,
    )


class FilterResultCodec:
    """Canonical bounded codec compatible with the semantic-data registry."""

    kind = FILTER_RESULT_KIND
    schema_version = FILTER_RESULT_SCHEMA_VERSION
    python_type = FilterResult
    max_bytes = MAX_FILTER_RESULT_BYTES

    def encode(self, value: object) -> bytes:
        """Revalidate a filter result and encode deterministic UTF-8 JSON."""
        if not isinstance(value, FilterResult):
            raise TypeError("filter_result@1 data must be a FilterResult")
        try:
            payload = json.dumps(
                value.model_dump(mode="json", round_trip=True, warnings="error"),
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            FilterResult.model_validate_json(payload, strict=True)
        except (TypeError, ValueError):
            raise TypeError("filter_result@1 data failed validation") from None
        return payload

    def decode(self, payload: bytes) -> FilterResult:
        """Decode canonical bytes and reject bypassed or noncanonical data."""
        if len(payload) > self.max_bytes:
            raise ValueError("stored filter_result@1 data exceeds size bound")
        try:
            result = FilterResult.model_validate_json(payload, strict=True)
        except ValueError:
            raise ValueError("stored filter_result@1 data failed validation") from None
        if self.encode(result) != payload:
            raise ValueError("stored filter_result@1 data is not canonical")
        return result
