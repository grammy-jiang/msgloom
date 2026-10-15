"""Validate exact release entry member, scope and parent relationships."""

from msgloom.sources.handoff_models import FactPayload, ReleaseEntry
from msgloom.sources.models import SourceReferenceError


def validate_impact(entry: ReleaseEntry, fact: FactPayload, role: str) -> None:
    scope = (entry.scope_kind, entry.scope_identity)
    fact_scope = (fact.scope_kind, fact.scope_identity)
    if fact.fact_kind == "scoped_state_transition" and scope != fact_scope:
        raise SourceReferenceError("Released transition scope mismatch")
    if role == "proof":
        return
    target = (entry.resource_kind, entry.resource_identity)
    own = (fact.resource_kind, fact.resource_identity)
    parent = (fact.parent_resource_kind, fact.parent_resource_identity)
    if target not in (own, parent):
        raise SourceReferenceError("Released fact resource mismatch")
    if target == own and (
        scope != fact_scope
        or (entry.parent_resource_kind, entry.parent_resource_identity) != parent
    ):
        raise SourceReferenceError("Released fact scope or parent mismatch")
