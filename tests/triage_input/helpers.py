"""Synthetic helpers for the pure triage-input lane."""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from msgloom.contracts import ResultRef, SemanticDataRef, VersionRef
from msgloom.preparation import (
    DocumentLocation,
    MimePartLocation,
    MimePartReference,
    NativeRelationship,
    ParsedLink,
    PreparedSourceType,
)
from msgloom.preparation.codec import PreparedDataCodec
from msgloom.preparation.filtering import (
    AddressNormalization,
    FilterConfig,
    FilterEffect,
    FilterResultCodec,
    FilterRule,
    SubjectMatchMode,
    SubjectPattern,
    apply_filters,
)
from msgloom.preparation.grouping import GroupResultCodec, group_records
from msgloom.triage import (
    PredicateKind,
    RuleEffect,
    RuleEffectKind,
    RulePredicate,
    TriageRule,
    TriageRuleConfig,
    TriageRuleEvaluationCodec,
    evaluate_rule_set,
)
from msgloom.triage_input import (
    RepetitionPolicy,
    SavedFilterBinding,
    SavedGroupBinding,
    SavedPreparedBinding,
    SavedRuleBinding,
    SourceRole,
    SourceRoleBinding,
    SplitBudget,
    TriageInputConfig,
    TriageSelection,
    TrustedInputVersions,
)
from tests.prepared_contract_fixtures import prepared_record


class _Codec(Protocol):
    kind: str
    schema_version: str

    def encode(self, value: object) -> bytes:
        """Encode one semantic value."""
        ...


def _result_ref(kind: str, identity: str) -> ResultRef:
    return ResultRef(result_id=identity, kind=kind, schema_version="1")


def _data_ref(codec: _Codec, identity: str, value: object) -> SemanticDataRef:
    payload = codec.encode(value)
    from hashlib import sha256

    return SemanticDataRef(
        data_id=identity,
        kind=codec.kind,
        schema_version=codec.schema_version,
        sha256=sha256(payload).hexdigest(),
        byte_count=len(payload),
    )


def record(
    identity: str,
    *,
    body: str | None = None,
    source_type: PreparedSourceType = PreparedSourceType.OUTLOOK_EMAIL,
    relationships: tuple[NativeRelationship, ...] = (),
):
    """Return a distinct synthetic prepared record."""
    base = prepared_record(body=body or f"Synthetic body {identity}")
    scope = NativeRelationship(
        kind="source_scope",
        target=VersionRef("source_scope", "synthetic-scope", "v1"),
    )
    return base.model_copy(
        update={
            "source": VersionRef(source_type.value, identity, "v1"),
            "source_type": source_type,
            "subject": "Shared synthetic subject",
            "relationships": (scope, *relationships),
        }
    )


def with_large_cell(source, text: str):
    """Replace the synthetic table cell text while preserving structure."""
    parsed = source.parsed_contents[0]
    output = parsed.output
    table_block = output.blocks[1]
    table = table_block.table
    cell = replace(table.cells[0], text=text, formula="=SUM(A1:A2)", cached_value="42")
    new_table = replace(table, cells=(cell,))
    new_block = replace(table_block, table=new_table)
    new_output = replace(output, blocks=(output.blocks[0], new_block, output.blocks[2]))
    new_parsed = parsed.model_copy(update={"output": new_output})
    return source.model_copy(update={"parsed_contents": (new_parsed,)})


def with_link_and_mime(source):
    """Add synthetic retained link and MIME relationship facts."""
    parsed = source.parsed_contents[0]
    output = parsed.output
    link = ParsedLink(
        target="https://example.invalid/synthetic",
        text="Synthetic link",
        location=DocumentLocation("workbook", 0),
    )
    first = replace(output.blocks[0], links=(link,))
    mime = MimePartReference(
        part_ref="1",
        parent_ref=None,
        content_type="text/plain",
        disposition="inline",
        content_id="synthetic-content-id",
        location=MimePartLocation("1"),
    )
    new_output = replace(
        output,
        blocks=(first, *output.blocks[1:]),
        mime_parts=(mime,),
    )
    new_parsed = parsed.model_copy(update={"output": new_output})
    return source.model_copy(update={"parsed_contents": (new_parsed,)})


def selection(
    records,
    *,
    filter_config: FilterConfig | None = None,
    triage_config: TriageRuleConfig | None = None,
    roles: tuple[SourceRole, ...] | None = None,
):
    """Build exact saved bindings from real preparation/group/rule contracts."""
    records = tuple(records)
    filter_config = filter_config or FilterConfig(
        reference=VersionRef("filter_config", "synthetic", "v1"),
        address_normalization=AddressNormalization.EXACT,
        rules=(),
    )
    filters = tuple(apply_filters(item, filter_config) for item in records)
    groups = group_records(records, filters)
    triage_config = triage_config or TriageRuleConfig(
        version=VersionRef("triage_rule_config", "synthetic", "v1"),
        rules=(),
    )
    evaluation = evaluate_rule_set(records, triage_config)
    prepared_codec = PreparedDataCodec()
    filter_codec = FilterResultCodec()
    group_codec = GroupResultCodec()
    rule_codec = TriageRuleEvaluationCodec()
    prepared_bindings = tuple(
        SavedPreparedBinding(
            result_ref=_result_ref("prepared", f"prepared-{item.source.identity}"),
            data_ref=_data_ref(
                prepared_codec, f"prepared-data-{item.source.identity}", item
            ),
            record=item,
        )
        for item in records
    )
    filter_bindings = tuple(
        SavedFilterBinding(
            result_ref=_result_ref("filter_result", f"filter-{item.input.identity}"),
            data_ref=_data_ref(
                filter_codec, f"filter-data-{item.input.identity}", item
            ),
            result=item,
        )
        for item in filters
    )
    group_bindings = tuple(
        SavedGroupBinding(
            result_ref=_result_ref("group_result", f"group-{index}"),
            data_ref=_data_ref(group_codec, f"group-data-{index}", item),
            result=item,
        )
        for index, item in enumerate(groups)
    )
    role_values = roles or tuple(SourceRole.NEW_SOURCE for _ in records)
    role_bindings = tuple(
        SourceRoleBinding(source_ref=item.source, role=role)
        for item, role in zip(records, role_values, strict=True)
    )
    return TriageSelection(
        prepared=prepared_bindings,
        filter_config=filter_config,
        filters=filter_bindings,
        groups=group_bindings,
        rules=SavedRuleBinding(
            result_ref=_result_ref("triage_rules", "rules-1"),
            data_ref=_data_ref(rule_codec, "rules-data-1", evaluation),
            evaluation=evaluation,
        ),
        roles=role_bindings,
        working_context_ref=VersionRef("working_context", "snapshot-1", "v1"),
        versions=TrustedInputVersions(
            prompt=VersionRef("prompt", "triage", "v1"),
            model=VersionRef("model", "synthetic", "v1"),
            output_schema=VersionRef("schema", "triage-candidate", "v1"),
            configuration=VersionRef("triage_input_config", "synthetic", "v1"),
        ),
    )


def config(
    *,
    max_part_bytes: int = 4096,
    max_parts: int = 128,
    dedup: bool = False,
    max_snapshot_bytes: int = 8 * 1024 * 1024,
) -> TriageInputConfig:
    """Return explicit finite synthetic input limits."""
    return TriageInputConfig(
        version=VersionRef("triage_input_config", "synthetic", "v1"),
        repetition=RepetitionPolicy(remove_exact_text_repetitions=dedup),
        split=SplitBudget(
            max_part_bytes=max_part_bytes,
            max_parts_per_unit=max_parts,
        ),
        max_snapshot_bytes=max_snapshot_bytes,
    )


def exclusion_filter(source_identity: str) -> FilterConfig:
    """Return one exact deterministic exclusion filter."""
    return FilterConfig(
        reference=VersionRef("filter_config", "exclude", "v1"),
        address_normalization=AddressNormalization.EXACT,
        rules=(
            FilterRule(
                reference=VersionRef("filter_rule", "exclude", "v1"),
                effect=FilterEffect.EXCLUDE,
                subject_patterns=(
                    SubjectPattern(
                        mode=SubjectMatchMode.EXACT,
                        value="Shared synthetic subject",
                    ),
                ),
            ),
        ),
    )


def exclusion_triage_rule(source_type: PreparedSourceType) -> TriageRuleConfig:
    """Return one deterministic triage exclusion rule."""
    return TriageRuleConfig(
        version=VersionRef("triage_rule_config", "exclude", "v1"),
        rules=(
            TriageRule(
                rule_ref=VersionRef("triage_rule", "exclude", "v1"),
                predicates=(
                    RulePredicate(
                        kind=PredicateKind.SOURCE_TYPE,
                        source_type=source_type,
                    ),
                ),
                effects=(RuleEffect(kind=RuleEffectKind.EXCLUSION),),
            ),
        ),
    )
