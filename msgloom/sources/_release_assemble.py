"""Reconstruct every released effect without mutable projection fallback."""

from msgloom.sources._release_components import component, enrich, validate_components
from msgloom.sources._release_content_parent import content_parent
from msgloom.sources._release_evidence import ReleaseEvidence
from msgloom.sources._release_records import record
from msgloom.sources._release_validation import validate_fact
from msgloom.sources._snapshot import capture_selection, encode_selection
from msgloom.sources.handoff_models import ReleasedFact, ReleaseEntry
from msgloom.sources.models import SourceReferenceError
from msgloom.sources.release_models import ReleasedInput, ScopedTransition


def reconstruct(
    entry: ReleaseEntry, facts: tuple[ReleasedFact, ...], evidence: ReleaseEvidence
) -> ReleasedInput:
    """Materialize exact sources, context, components, and transitions."""
    for fact in facts:
        validate_fact(fact)
    primary_facts = [
        fact
        for fact in facts
        if fact.fact_kind == "resource_observation" and fact.role != "proof"
    ]
    validate_components(
        primary_facts[0] if len(primary_facts) == 1 else None, facts, evidence
    )
    scope = evidence.catalog.source_scope(entry.source_id)
    primary = []
    components = []
    contexts = []
    transitions = []
    attachments = []
    for fact in facts:
        if fact.fact_kind == "scoped_state_transition":
            saved = None
            if fact.evidence_id:
                _, saved = evidence.load(fact.evidence_id, fact.source_id)
            if (
                not fact.scope_kind
                or not fact.scope_identity
                or not fact.transition_reason
            ):
                raise SourceReferenceError("Incomplete scoped transition")
            transitions.append(
                ScopedTransition(
                    fact_id=fact.fact_id,
                    source_id=fact.source_id,
                    stream=fact.stream,
                    resource_kind=fact.resource_kind,
                    resource_identity=fact.resource_identity,
                    parent_resource_kind=fact.parent_resource_kind,
                    parent_resource_identity=fact.parent_resource_identity,
                    scope_kind=fact.scope_kind,
                    scope_identity=fact.scope_identity,
                    reason=fact.transition_reason,
                    authority_revision=fact.authority_revision,
                    provider_order=fact.provider_order,
                    evidence=saved,
                )
            )
            continue
        if fact.role == "proof":
            if fact.source_version_locator is not None:
                evidence.object(fact)
            elif fact.evidence_id:
                evidence.load(fact.evidence_id, fact.source_id)
            continue
        if fact.fact_kind == "component_observation":
            value, attachment = component(fact, evidence, scope)
            components.append(value)
            if attachment is not None:
                attachments.append(attachment)
            continue
        raw, saved = evidence.object(fact)
        value = record(fact, raw, saved, scope)
        if fact.fact_kind == "control_context":
            contexts.append(capture_selection(value))
        else:
            primary.append(value)
    if not primary and entry.stream == "onedrive":
        content = [
            f for f in facts if f.component_kind == "item_content" and f.role != "proof"
        ]
        if len(content) == 1:
            primary.append(content_parent(content[0], evidence, scope))
    if len(primary) > 1:
        raise SourceReferenceError("Ambiguous released primary representation")
    selection = (
        capture_selection(
            enrich(
                primary[0],
                components,
                attachments,
                [
                    f
                    for f in facts
                    if f.fact_kind == "component_observation" and f.role != "proof"
                ],
            )
        )
        if primary
        else None
    )
    result = ReleasedInput(
        reference=entry.reference,
        selection=selection,
        facts=facts,
        components=tuple(capture_selection(value) for value in components),
        contexts=tuple(contexts),
        transitions=tuple(transitions),
    )
    remaining = evidence.catalog.limits.max_snapshot_bytes
    for item in (
        *result.components,
        *result.contexts,
        *((selection,) if selection else ()),
    ):
        remaining -= len(
            encode_selection(item, evidence.catalog.limits.max_snapshot_bytes)
        )
        if remaining < 0:
            raise SourceReferenceError("Release selections exceed byte budget")
    return result
