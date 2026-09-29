"""Selection validation against exact saved preparation and rule contracts."""

from __future__ import annotations

from hashlib import sha256
from typing import Never

from pydantic import ValidationError

from msgloom.contracts import ResultRef, SemanticDataRef
from msgloom.preparation.codec import PreparedDataCodec
from msgloom.preparation.filtering import (
    FilterOutcome,
    FilterResultCodec,
    apply_filters,
)
from msgloom.preparation.grouping import GroupResultCodec, group_records
from msgloom.triage.rule_codec import TriageRuleEvaluationCodec
from msgloom.triage.rules import evaluate_rule_set

from .canonical import canonical_json
from .models import (
    HeldReason,
    HeldSource,
    SavedFilterBinding,
    SavedGroupBinding,
    SavedPreparedBinding,
    SavedRuleBinding,
    TriageSelection,
)


class TriageInputValidationError(ValueError):
    """Expose a fixed safe input-validation classification."""


def _fail() -> Never:
    raise TriageInputValidationError("triage input selection failed validation")


def _verify_data_ref(
    ref: SemanticDataRef, payload: bytes, kind: str, version: str
) -> None:
    try:
        matches = (
            ref.kind == kind
            and ref.schema_version == version
            and ref.byte_count == len(payload)
            and ref.sha256 == sha256(payload).hexdigest()
        )
    except AttributeError:
        _fail()
    if not matches:
        _fail()


def _verify_result_ref(ref: ResultRef, kind: str, version: str) -> None:
    try:
        matches = ref.kind == kind and ref.schema_version == version
    except AttributeError:
        _fail()
    if not matches:
        _fail()


def _prepared(binding: SavedPreparedBinding) -> SavedPreparedBinding:
    codec = PreparedDataCodec()
    try:
        payload = codec.encode(binding.record)
        value = codec.decode(payload)
    except (TypeError, ValueError):
        _fail()
    _verify_result_ref(binding.result_ref, codec.kind, codec.schema_version)
    _verify_data_ref(binding.data_ref, payload, codec.kind, codec.schema_version)
    return binding.model_copy(update={"record": value})


def _filter(binding: SavedFilterBinding) -> SavedFilterBinding:
    codec = FilterResultCodec()
    try:
        payload = codec.encode(binding.result)
        value = codec.decode(payload)
    except (TypeError, ValueError):
        _fail()
    _verify_result_ref(binding.result_ref, codec.kind, codec.schema_version)
    _verify_data_ref(binding.data_ref, payload, codec.kind, codec.schema_version)
    return binding.model_copy(update={"result": value})


def _group(binding: SavedGroupBinding) -> SavedGroupBinding:
    codec = GroupResultCodec()
    try:
        payload = codec.encode(binding.result)
        value = codec.decode(payload)
    except (TypeError, ValueError):
        _fail()
    _verify_result_ref(binding.result_ref, codec.kind, codec.schema_version)
    _verify_data_ref(binding.data_ref, payload, codec.kind, codec.schema_version)
    return binding.model_copy(update={"result": value})


def _rules(binding: SavedRuleBinding) -> SavedRuleBinding:
    codec = TriageRuleEvaluationCodec()
    try:
        payload = codec.encode(binding.evaluation)
        value = codec.decode(payload)
    except (TypeError, ValueError):
        _fail()
    _verify_result_ref(binding.result_ref, codec.kind, codec.schema_version)
    _verify_data_ref(binding.data_ref, payload, codec.kind, codec.schema_version)
    return binding.model_copy(update={"evaluation": value})


def validate_selection(selection: TriageSelection) -> TriageSelection:
    """Fully revalidate saved values, integrity refs, and deterministic replay."""
    try:
        checked = TriageSelection.model_validate_json(
            canonical_json(selection), strict=True
        )
        prepared = tuple(_prepared(item) for item in checked.prepared)
        filters = tuple(_filter(item) for item in checked.filters)
        groups = tuple(_group(item) for item in checked.groups)
        rules = _rules(checked.rules)
    except (ValidationError, TypeError, ValueError):
        _fail()

    records = tuple(item.record for item in prepared)
    filter_values = tuple(item.result for item in filters)
    refs = {record.source for record in records}
    if {item.input for item in filter_values} != refs:
        _fail()
    if {item.configuration_ref for item in filter_values} != {
        checked.filter_config.reference
    }:
        _fail()
    try:
        replayed_filters = tuple(
            apply_filters(record, checked.filter_config) for record in records
        )
    except (TypeError, ValueError):
        _fail()
    if set(replayed_filters) != set(filter_values):
        _fail()

    group_key = lambda item: tuple(
        (ref.kind, ref.identity, ref.version) for ref in item.members
    )
    supplied_groups = tuple(sorted((item.result for item in groups), key=group_key))
    try:
        replayed_groups = group_records(records, filter_values)
    except (TypeError, ValueError):
        _fail()
    if supplied_groups != replayed_groups:
        _fail()

    if {item.source_ref for item in checked.roles} != refs:
        _fail()

    try:
        replayed_rules = evaluate_rule_set(records, rules.evaluation.config)
    except (TypeError, ValueError):
        _fail()
    if replayed_rules != rules.evaluation:
        _fail()

    ref_key = lambda ref: (ref.kind, ref.identity, ref.version)
    prepared = tuple(sorted(prepared, key=lambda item: ref_key(item.record.source)))
    filters = tuple(sorted(filters, key=lambda item: ref_key(item.result.input)))
    groups = tuple(sorted(groups, key=lambda item: group_key(item.result)))
    roles = tuple(sorted(checked.roles, key=lambda item: ref_key(item.source_ref)))
    return checked.model_copy(
        update={
            "prepared": prepared,
            "filters": filters,
            "groups": groups,
            "rules": rules,
            "roles": roles,
        }
    )


def held_sources(selection: TriageSelection) -> tuple[HeldSource, ...]:
    """Return canonical explicit held dispositions for deterministic blockers."""
    filters = {item.result.input: item for item in selection.filters}
    outcomes = {item.source_ref: item for item in selection.rules.evaluation.outcomes}
    roles = {item.source_ref: item.role for item in selection.roles}
    held: list[HeldSource] = []
    key = lambda x: (x.kind, x.identity, x.version)
    for source_ref in sorted(roles, key=key):
        reasons: list[HeldReason] = []
        outcome = filters[source_ref].result.outcome
        if outcome is FilterOutcome.EXCLUDED:
            reasons.append(HeldReason.FILTER_EXCLUDED)
        elif outcome is FilterOutcome.CONFLICT:
            reasons.append(HeldReason.FILTER_CONFLICT)
        rule = outcomes[source_ref]
        if rule.excluded:
            reasons.append(HeldReason.RULE_EXCLUDED)
        if rule.review_items:
            reasons.append(HeldReason.RULE_CONFLICT)
        if reasons:
            held.append(
                HeldSource(
                    source_ref=source_ref,
                    role=roles[source_ref],
                    reasons=tuple(reasons),
                    filter_ref=filters[source_ref].data_ref,
                    rule_ref=selection.rules.data_ref,
                )
            )
    return tuple(held)


def selection_digest(selection: TriageSelection) -> str:
    """Hash every validated meaning-bearing selection value and exact reference."""
    return sha256(canonical_json(selection)).hexdigest()
