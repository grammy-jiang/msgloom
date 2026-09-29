"""Canonical bounded codecs for filtering and grouping semantic outputs."""

import json

import pytest
from pydantic import ValidationError

from msgloom.contracts import VersionRef
from msgloom.persistence.errors import SemanticDataIntegrityError
from msgloom.persistence.semantic import SemanticDataRegistry
from msgloom.preparation.filtering import (
    AddressNormalization,
    FilterConfig,
    FilterEffect,
    FilterOutcome,
    FilterResult,
    FilterResultCodec,
    MatchedFilterRule,
    apply_filters,
)
from msgloom.preparation.grouping import (
    GroupEvidence,
    GroupMethod,
    GroupResult,
    GroupResultCodec,
    GroupStatus,
    group_records,
)
from tests.prepared_contract_fixtures import prepared_record


def _filter_result() -> FilterResult:
    record = prepared_record()
    config = FilterConfig(
        reference=VersionRef("filter_config", "synthetic", "v1"),
        address_normalization=AddressNormalization.EXACT,
        rules=(),
    )
    return apply_filters(record, config)


def test_filter_and_group_codecs_round_trip_through_registry_contract() -> None:
    record = prepared_record()
    filtered = _filter_result()
    grouped = group_records((record,), (filtered,))[0]
    registry = SemanticDataRegistry((FilterResultCodec(), GroupResultCodec()))

    for data_id, kind, value in (
        ("filter-1", "filter_result", filtered),
        ("group-1", "group_result", grouped),
    ):
        encoded = registry.encode(data_id, kind, "1", value)
        decoded = registry.decode(encoded.reference, encoded.payload)
        if decoded != value:
            pytest.fail(f"{kind} did not round-trip through registry semantics")


@pytest.mark.parametrize(
    ("codec", "value"),
    [
        (FilterResultCodec(), _filter_result()),
        (
            GroupResultCodec(),
            group_records((prepared_record(),), (_filter_result(),))[0],
        ),
    ],
)
def test_codecs_reject_noncanonical_json(codec: object, value: object) -> None:
    payload = codec.encode(value)  # type: ignore[attr-defined]
    data = json.loads(payload)
    noncanonical = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    with pytest.raises(ValueError):
        codec.decode(noncanonical)  # type: ignore[attr-defined]


def test_filter_codec_revalidates_model_construct_bypass() -> None:
    valid = _filter_result()
    bypassed = FilterResult.model_construct(
        input=valid.input,
        configuration_ref=valid.configuration_ref,
        outcome="not-an-outcome",
        matched_rules=(),
    )
    with pytest.raises(TypeError):
        FilterResultCodec().encode(bypassed)


def test_group_codec_revalidates_member_and_filter_integrity() -> None:
    valid = group_records((prepared_record(),), (_filter_result(),))[0]
    bypassed = GroupResult.model_construct(
        status=valid.status,
        members=(VersionRef("outlook_email", "other", "v1"),),
        method=valid.method,
        evidence=valid.evidence,
        reason=valid.reason,
        filters=valid.filters,
    )
    with pytest.raises(TypeError):
        GroupResultCodec().encode(bypassed)


def test_result_models_are_strict_and_immutable() -> None:
    result = _filter_result()
    with pytest.raises((ValidationError, TypeError)):
        result.outcome = "excluded"  # type: ignore[misc]


def test_registry_integrity_rejects_modified_filter_payload() -> None:
    registry = SemanticDataRegistry((FilterResultCodec(),))
    encoded = registry.encode("filter-1", "filter_result", "1", _filter_result())
    modified = encoded.payload.replace(b'"included"', b'"excluded"', 1)
    with pytest.raises(SemanticDataIntegrityError):
        registry.decode(encoded.reference, modified)


@pytest.mark.parametrize("codec", [FilterResultCodec(), GroupResultCodec()])
def test_codec_decode_rejects_payload_above_declared_bound(codec: object) -> None:
    oversized = b" " * (codec.max_bytes + 1)  # type: ignore[attr-defined]
    with pytest.raises(ValueError):
        codec.decode(oversized)  # type: ignore[attr-defined]


def test_confirmed_group_constructor_requires_supported_connected_evidence() -> None:
    base = _filter_result()
    refs = tuple(
        VersionRef("outlook_email", identity, "v1") for identity in ("a", "b", "c")
    )
    filters = tuple(base.model_copy(update={"input": ref}) for ref in refs)
    disconnected = (
        GroupEvidence(
            source=refs[0],
            relationship_kind="in_reply_to",
            target=refs[1],
        ),
        GroupEvidence(
            source=refs[1],
            relationship_kind="in_reply_to",
            target=refs[0],
        ),
    )
    with pytest.raises(ValidationError):
        GroupResult(
            status=GroupStatus.CONFIRMED,
            members=refs,
            method=GroupMethod.OUTLOOK_REPLY,
            evidence=disconnected,
            reason="synthetic disconnected claim",
            filters=filters,
        )

    with pytest.raises(ValidationError):
        GroupResult(
            status=GroupStatus.CONFIRMED,
            members=refs[:2],
            method=GroupMethod.OUTLOOK_REPLY,
            evidence=(
                GroupEvidence(
                    source=refs[0],
                    relationship_kind="teams_chat_reply_to",
                    target=refs[1],
                ),
            ),
            reason="synthetic method mismatch",
            filters=filters[:2],
        )

    with pytest.raises(ValidationError):
        GroupResult(
            status=GroupStatus.UNCERTAIN,
            members=refs[:2],
            method=GroupMethod.OUTLOOK_CONVERSATION,
            evidence=tuple(
                GroupEvidence(
                    source=source,
                    relationship_kind="outlook_conversation",
                    target=VersionRef("outlook_conversation", target, "v1"),
                )
                for source, target in zip(refs[:2], ("conv-a", "conv-b"), strict=True)
            ),
            reason="synthetic mixed conversation targets",
            filters=filters[:2],
        )


def test_confirmed_singleton_claim_is_rejected_by_constructor_and_codec_bypasses() -> (
    None
):
    valid = group_records((prepared_record(),), (_filter_result(),))[0]
    with pytest.raises(ValidationError):
        GroupResult(
            status=GroupStatus.CONFIRMED,
            members=valid.members,
            method=GroupMethod.OUTLOOK_REPLY,
            evidence=(),
            filters=valid.filters,
            reason="synthetic unsupported claim",
        )

    copied = valid.model_copy(
        update={
            "status": GroupStatus.CONFIRMED,
            "method": GroupMethod.OUTLOOK_REPLY,
            "reason": "synthetic copied claim",
        }
    )
    constructed = GroupResult.model_construct(
        status=GroupStatus.CONFIRMED,
        members=valid.members,
        method=GroupMethod.OUTLOOK_REPLY,
        evidence=(),
        filters=valid.filters,
        reason="synthetic constructed claim",
    )
    for bypassed in (copied, constructed):
        with pytest.raises(TypeError):
            GroupResultCodec().encode(bypassed)


def test_held_filter_cannot_be_used_to_construct_grouped_claim() -> None:
    base = _filter_result()
    held = FilterResult(
        input=base.input,
        configuration_ref=base.configuration_ref,
        outcome=FilterOutcome.EXCLUDED,
        matched_rules=(
            MatchedFilterRule(
                rule_ref=VersionRef("filter_rule", "hold", "v1"),
                effect=FilterEffect.EXCLUDE,
            ),
        ),
    )
    with pytest.raises(ValidationError):
        GroupResult(
            status=GroupStatus.UNCERTAIN,
            members=(held.input,),
            method=GroupMethod.OUTLOOK_REPLY,
            evidence=(
                GroupEvidence(
                    source=held.input,
                    relationship_kind="in_reply_to",
                    target=VersionRef("outlook_email", "external", "v1"),
                ),
            ),
            filters=(held,),
            reason="synthetic held claim",
        )
