"""Deterministic bounded triage predicates and rule outcomes."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from msgloom.contracts import VersionRef
from msgloom.preparation import PreparedRecord, PreparedSourceType

from .models import Priority, priority_rank


class _FrozenModel(BaseModel):
    """Reject coercion, mutation, and undeclared deterministic-rule fields."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")


class PredicateKind(StrEnum):
    """Closed predicate vocabulary over already prepared source facts."""

    SENDER_IDENTITY = "sender-identity"
    AUTHOR_IDENTITY = "author-identity"
    RECIPIENT_IDENTITY = "recipient-identity"
    SOURCE_TYPE = "source-type"
    SUBJECT_EXACT = "subject-exact"
    SUBJECT_CONTAINS = "subject-contains"
    BODY_CONTAINS = "body-contains"
    SOURCE_TIME_AT_OR_AFTER = "source-time-at-or-after"
    SOURCE_TIME_BEFORE = "source-time-before"


class RulePredicate(_FrozenModel):
    """One bounded predicate; arbitrary expressions and regex are not accepted."""

    kind: PredicateKind
    text_value: Annotated[str | None, Field(min_length=1, max_length=512)] = None
    source_type: PreparedSourceType | None = None
    time_value: datetime | None = None

    @model_validator(mode="after")
    def _validate_value_shape(self) -> RulePredicate:
        text_kinds = {
            PredicateKind.SENDER_IDENTITY,
            PredicateKind.AUTHOR_IDENTITY,
            PredicateKind.RECIPIENT_IDENTITY,
            PredicateKind.SUBJECT_EXACT,
            PredicateKind.SUBJECT_CONTAINS,
            PredicateKind.BODY_CONTAINS,
        }
        if self.kind in text_kinds:
            if self.text_value is None:
                raise ValueError("text predicate requires text_value")
            if self.source_type is not None or self.time_value is not None:
                raise ValueError("text predicate has incompatible value fields")
            return self
        if self.kind is PredicateKind.SOURCE_TYPE:
            if self.source_type is None:
                raise ValueError("source-type predicate requires source_type")
            if self.text_value is not None or self.time_value is not None:
                raise ValueError("source-type predicate has incompatible value fields")
            return self
        if self.time_value is None:
            raise ValueError("time predicate requires time_value")
        if self.time_value.tzinfo is None or self.time_value.utcoffset() is None:
            raise ValueError("time predicate must be timezone-aware")
        if self.text_value is not None or self.source_type is not None:
            raise ValueError("time predicate has incompatible value fields")
        return self


class RuleEffectKind(StrEnum):
    """Deterministic effects retained separately from semantic interpretation."""

    EXCLUSION = "exclusion"
    REQUIRED_PRIORITY = "required-priority"
    MINIMUM_PRIORITY = "minimum-priority"
    GUIDANCE = "guidance"


class RuleEffect(_FrozenModel):
    """One typed deterministic effect."""

    kind: RuleEffectKind
    priority: Priority | None = None
    guidance: Annotated[str | None, Field(min_length=1, max_length=2_000)] = None

    @model_validator(mode="after")
    def _validate_effect(self) -> RuleEffect:
        if self.kind in {
            RuleEffectKind.REQUIRED_PRIORITY,
            RuleEffectKind.MINIMUM_PRIORITY,
        }:
            if self.priority is None or self.guidance is not None:
                raise ValueError("priority effect requires only priority")
            return self
        if self.kind is RuleEffectKind.GUIDANCE:
            if self.guidance is None or self.priority is not None:
                raise ValueError("guidance effect requires only guidance text")
            return self
        if self.priority is not None or self.guidance is not None:
            raise ValueError("exclusion effect carries no priority or guidance")
        return self


class TriageRule(_FrozenModel):
    """Versioned deterministic rule using AND across its bounded predicates."""

    rule_ref: VersionRef
    predicates: Annotated[tuple[RulePredicate, ...], Field(min_length=1, max_length=16)]
    effects: Annotated[tuple[RuleEffect, ...], Field(min_length=1, max_length=8)]


class TriageRuleConfig(_FrozenModel):
    """Immutable rule set; ordering is not a conflict-resolution mechanism."""

    version: VersionRef
    rules: Annotated[tuple[TriageRule, ...], Field(max_length=256)]

    @model_validator(mode="after")
    def _unique_rule_refs(self) -> TriageRuleConfig:
        refs = tuple(rule.rule_ref for rule in self.rules)
        if len(refs) != len(set(refs)):
            raise ValueError("triage rule references must be unique")
        return self


class RuleMatch(_FrozenModel):
    """One matched rule effect retained independently of rule order."""

    rule_ref: VersionRef
    source_ref: VersionRef
    effect: RuleEffect


class RuleReviewItem(_FrozenModel):
    """Safe deterministic-policy conflict requiring explicit review."""

    code: Annotated[str, Field(min_length=1, max_length=64)]
    rule_refs: Annotated[tuple[VersionRef, ...], Field(min_length=1, max_length=256)]
    reason: Annotated[str, Field(min_length=1, max_length=512)]


class RuleOutcome(_FrozenModel):
    """All deterministic matches and derived constraints for one source."""

    source_ref: VersionRef
    matches: Annotated[tuple[RuleMatch, ...], Field(max_length=2_048)]
    excluded: bool
    required_priority: Priority | None
    minimum_priority: Priority | None
    guidance: Annotated[tuple[str, ...], Field(max_length=256)]
    review_items: Annotated[tuple[RuleReviewItem, ...], Field(max_length=32)]

    @model_validator(mode="after")
    def _derived_fields_match(self) -> RuleOutcome:
        if any(match.source_ref != self.source_ref for match in self.matches):
            raise ValueError("rule match source must equal outcome source")
        if self.matches != tuple(sorted(self.matches, key=_match_key)):
            raise ValueError("rule matches must use canonical order")
        if len(self.matches) != len(set(self.matches)):
            raise ValueError("rule matches must be unique")
        summary = _summarize(self.matches)
        actual = (
            self.excluded,
            self.required_priority,
            self.minimum_priority,
            self.guidance,
            self.review_items,
        )
        if actual != summary:
            raise ValueError("rule outcome summary does not match saved matches")
        return self


class TriageRuleEvaluation(_FrozenModel):
    """Persist one exact rule configuration together with derived outcomes."""

    schema_version: Literal["1"] = "1"
    config: TriageRuleConfig
    outcomes: Annotated[tuple[RuleOutcome, ...], Field(max_length=2_048)]

    @model_validator(mode="after")
    def _validate_binding(self) -> TriageRuleEvaluation:
        refs = tuple(outcome.source_ref for outcome in self.outcomes)
        if len(refs) != len(set(refs)):
            raise ValueError("rule evaluation source references must be unique")
        if self.outcomes != tuple(
            sorted(self.outcomes, key=lambda x: _ref_key(x.source_ref))
        ):
            raise ValueError("rule evaluation outcomes must use canonical source order")
        rules = {rule.rule_ref: rule for rule in self.config.rules}
        for outcome in self.outcomes:
            for match in outcome.matches:
                rule = rules.get(match.rule_ref)
                if rule is None or match.effect not in rule.effects:
                    raise ValueError("saved rule match is not present in configuration")
        return self


def evaluate_rules(
    records: tuple[PreparedRecord, ...],
    config: TriageRuleConfig,
) -> tuple[RuleOutcome, ...]:
    """Evaluate rules with canonical output independent of input ordering."""
    source_refs = tuple(record.source for record in records)
    if len(source_refs) != len(set(source_refs)):
        raise ValueError("selected prepared source references must be unique")
    outcomes = [_evaluate_record(record, config.rules) for record in records]
    return tuple(sorted(outcomes, key=lambda item: _ref_key(item.source_ref)))


def evaluate_rule_set(
    records: tuple[PreparedRecord, ...],
    config: TriageRuleConfig,
) -> TriageRuleEvaluation:
    """Return the persistable deterministic evaluation/configuration binding."""
    return TriageRuleEvaluation(config=config, outcomes=evaluate_rules(records, config))


def _evaluate_record(
    record: PreparedRecord,
    rules: tuple[TriageRule, ...],
) -> RuleOutcome:
    matches: list[RuleMatch] = []
    for rule in sorted(rules, key=lambda item: _ref_key(item.rule_ref)):
        if all(_matches(predicate, record) for predicate in rule.predicates):
            for effect in rule.effects:
                matches.append(
                    RuleMatch(
                        rule_ref=rule.rule_ref,
                        source_ref=record.source,
                        effect=effect,
                    )
                )
    ordered = tuple(sorted(matches, key=_match_key))
    excluded, required, minimum, guidance, review = _summarize(ordered)
    return RuleOutcome(
        source_ref=record.source,
        matches=ordered,
        excluded=excluded,
        required_priority=required,
        minimum_priority=minimum,
        guidance=guidance,
        review_items=review,
    )


def _summarize(
    matches: tuple[RuleMatch, ...],
) -> tuple[
    bool,
    Priority | None,
    Priority | None,
    tuple[str, ...],
    tuple[RuleReviewItem, ...],
]:
    exclusions = tuple(
        match for match in matches if match.effect.kind is RuleEffectKind.EXCLUSION
    )
    required = tuple(
        match
        for match in matches
        if match.effect.kind is RuleEffectKind.REQUIRED_PRIORITY
    )
    minimum = tuple(
        match
        for match in matches
        if match.effect.kind is RuleEffectKind.MINIMUM_PRIORITY
    )
    guidance = tuple(
        match.effect.guidance
        for match in matches
        if match.effect.kind is RuleEffectKind.GUIDANCE
        and match.effect.guidance is not None
    )
    review: list[RuleReviewItem] = []
    required_values = {
        match.effect.priority for match in required if match.effect.priority is not None
    }
    required_priority = (
        next(iter(required_values)) if len(required_values) == 1 else None
    )
    minimum_priority = _strongest_minimum(minimum)
    if len(required_values) > 1:
        review.append(
            _review(
                "conflicting-required-priorities",
                required,
                "deterministic rules require incompatible priorities",
            )
        )
    priority_work = required + minimum
    if exclusions and priority_work:
        review.append(
            _review(
                "exclusion-required-work-conflict",
                exclusions + priority_work,
                "exclusion conflicts with deterministic priority work",
            )
        )
    if (
        len(required_values) == 1
        and required_priority is not None
        and minimum_priority is not None
        and priority_rank(required_priority) < priority_rank(minimum_priority)
    ):
        review.append(
            _review(
                "required-below-minimum",
                required + minimum,
                "required priority is below a stronger minimum priority",
            )
        )
    if review:
        required_priority = None
    return (
        bool(exclusions),
        required_priority,
        minimum_priority,
        guidance,
        tuple(review),
    )


def _matches(predicate: RulePredicate, record: PreparedRecord) -> bool:
    value = predicate.text_value
    if predicate.kind is PredicateKind.SENDER_IDENTITY:
        return record.sender is not None and record.sender.identity == value
    if predicate.kind is PredicateKind.AUTHOR_IDENTITY:
        return record.author is not None and record.author.identity == value
    if predicate.kind is PredicateKind.RECIPIENT_IDENTITY:
        return any(item.party.identity == value for item in record.recipients)
    if predicate.kind is PredicateKind.SOURCE_TYPE:
        return record.source_type is predicate.source_type
    if predicate.kind is PredicateKind.SUBJECT_EXACT:
        return record.subject is not None and record.subject == value
    if predicate.kind is PredicateKind.SUBJECT_CONTAINS:
        return (
            record.subject is not None and value is not None and value in record.subject
        )
    if predicate.kind is PredicateKind.BODY_CONTAINS:
        return record.body is not None and value is not None and value in record.body
    if predicate.time_value is None:
        return False
    if predicate.kind is PredicateKind.SOURCE_TIME_AT_OR_AFTER:
        return record.source_time >= predicate.time_value
    return record.source_time < predicate.time_value


def _strongest_minimum(matches: tuple[RuleMatch, ...]) -> Priority | None:
    concrete = [
        match.effect.priority for match in matches if match.effect.priority is not None
    ]
    if not concrete:
        return None
    return max(concrete, key=priority_rank)


def _review(
    code: str,
    matches: tuple[RuleMatch, ...],
    reason: str,
) -> RuleReviewItem:
    refs = tuple(sorted({match.rule_ref for match in matches}, key=_ref_key))
    return RuleReviewItem(code=code, rule_refs=refs, reason=reason)


def _ref_key(ref: VersionRef) -> tuple[str, str, str]:
    return (ref.kind, ref.identity, ref.version)


def _match_key(match: RuleMatch) -> tuple[str, str, str, str, str, str]:
    priority = match.effect.priority.value if match.effect.priority is not None else ""
    guidance = match.effect.guidance or ""
    return (*_ref_key(match.rule_ref), match.effect.kind.value, priority, guidance)
