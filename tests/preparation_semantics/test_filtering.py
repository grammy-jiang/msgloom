"""Deterministic filtering semantics over immutable prepared records."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from msgloom.contracts import VersionRef
from msgloom.preparation.filtering import (
    AddressNormalization,
    FilterConfig,
    FilterEffect,
    FilterOutcome,
    FilterRule,
    SubjectMatchMode,
    SubjectPattern,
    apply_filters,
)
from msgloom.preparation.records import PreparedSourceType
from tests.prepared_contract_fixtures import prepared_record


def _ref(name: str) -> VersionRef:
    return VersionRef("filter_rule", name, "v1")


def _rule(name: str, effect: FilterEffect, **kwargs: object) -> FilterRule:
    return FilterRule(
        reference=_ref(name),
        effect=effect,
        **kwargs,  # pyright: ignore[reportArgumentType]
    )


def _config(*rules: FilterRule) -> FilterConfig:
    return FilterConfig(
        reference=VersionRef("filter_config", "synthetic", "v1"),
        address_normalization=AddressNormalization.CASEFOLD,
        rules=rules,
    )


def test_filtering_preserves_all_matches_and_exposes_conflict() -> None:
    record = prepared_record()
    original = record.model_dump(mode="json")
    config = _config(
        _rule(
            "include",
            FilterEffect.INCLUDE,
            sender_addresses=("SENDER-1",),
        ),
        _rule(
            "exclude",
            FilterEffect.EXCLUDE,
            subject_patterns=(
                SubjectPattern(
                    mode=SubjectMatchMode.CONTAINS,
                    value="budget",
                    case_sensitive=False,
                ),
            ),
        ),
        _rule(
            "guide",
            FilterEffect.GUIDANCE,
            source_types=(PreparedSourceType.OUTLOOK_EMAIL,),
            guidance="Review the synthetic budget context.",
        ),
    )

    result = apply_filters(record, config)

    if result.outcome is not FilterOutcome.CONFLICT:
        pytest.fail(f"expected explicit conflict, got {result.outcome}")
    if tuple(match.rule_ref.identity for match in result.matched_rules) != (
        "exclude",
        "guide",
        "include",
    ):
        pytest.fail("all matched rules must be retained in canonical order")
    if record.model_dump(mode="json") != original:
        pytest.fail("filtering must not mutate the replayable prepared input")


def test_filtering_is_independent_of_rule_order() -> None:
    record = prepared_record()
    rules = (
        _rule("z", FilterEffect.EXCLUDE, sender_addresses=("sender-1",)),
        _rule("a", FilterEffect.INCLUDE, sender_addresses=("sender-1",)),
    )

    first = apply_filters(record, _config(*rules))
    second = apply_filters(record, _config(*reversed(rules)))

    if first.matched_rules != second.matched_rules or first.outcome != second.outcome:
        pytest.fail("rule declaration order must not resolve or reorder conflicts")


def test_time_boundaries_compare_aware_instants() -> None:
    record = prepared_record()
    same_in_sydney = datetime(2026, 9, 29, 7, 15, tzinfo=UTC)
    start = same_in_sydney.astimezone(timezone(timedelta(hours=10)))
    rule = _rule(
        "time",
        FilterEffect.EXCLUDE,
        not_before=start,
        before=start + timedelta(minutes=1),
    )

    result = apply_filters(
        record.model_copy(update={"source_time": same_in_sydney}), _config(rule)
    )
    if result.outcome is not FilterOutcome.EXCLUDED:
        pytest.fail("aware timestamps representing the same instant must match")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"not_before": datetime(2026, 1, 1)},  # noqa: DTZ001
        {"before": datetime(2026, 1, 1)},  # noqa: DTZ001
        {"sender_addresses": (" sender-1",)},
        {"sender_addresses": ("sender-1", "sender-1")},
    ],
)
def test_invalid_filter_configuration_is_rejected(kwargs: dict[str, object]) -> None:
    with pytest.raises((ValidationError, ValueError)):
        _rule("invalid", FilterEffect.EXCLUDE, **kwargs)


def test_filter_requires_at_least_one_predicate_and_guidance_text() -> None:
    with pytest.raises(ValidationError):
        _rule("empty", FilterEffect.EXCLUDE)
    with pytest.raises(ValidationError):
        _rule(
            "guidance",
            FilterEffect.GUIDANCE,
            sender_addresses=("sender-1",),
        )


def test_subject_pattern_bound_is_rejected() -> None:
    with pytest.raises(ValidationError):
        SubjectPattern(mode=SubjectMatchMode.CONTAINS, value="x" * 257)


def test_source_scope_predicate_uses_exact_explicit_scope_relationship() -> None:
    from msgloom.preparation.filtering import SOURCE_SCOPE_RELATIONSHIP
    from msgloom.preparation.records import NativeRelationship

    scope = VersionRef("source_scope", "mailbox:synthetic-a", "v1")
    record = prepared_record().model_copy(
        update={
            "relationships": (
                NativeRelationship(kind=SOURCE_SCOPE_RELATIONSHIP, target=scope),
            )
        }
    )
    rule = _rule(
        "scope",
        FilterEffect.EXCLUDE,
        source_scopes=(scope,),
    )
    result = apply_filters(record, _config(rule))
    if result.outcome is not FilterOutcome.EXCLUDED:
        pytest.fail("exact declared source scope should satisfy the predicate")
