"""Explicit pointer application after provider-owned authority validation."""

from message_ingest.acquisition.handoff import StorageRelation


def apply_authority_facts_in_session(ledger, writer, *, source_id, stream, fact_ids):
    """
    Apply an exact, validated set without changing immutable facts.

    The caller must validate provider CAS and mutable-state applicability in
    the same writer transaction. Equivalent recovery retains its original
    pin; advanced reapplication selects itself, including equal-state ABA.
    Ordinary publication retains the ledger's existing eligibility rules.
    """
    facts = [ledger._fact(writer, fact_id) for fact_id in fact_ids]
    seen = set()
    for fact in facts:
        if (fact.source_id, fact.stream) != (source_id, stream):
            raise ValueError("Authority application crosses source/stream")
        key = fact.effective_key.digest
        if key in seen:
            raise ValueError("Ambiguous winning effective state")
        seen.add(key)
        if fact.storage_relation == StorageRelation.STALE:
            raise ValueError("Stale fact cannot win authority")
        if fact.storage_relation == StorageRelation.CURRENT_EQUIVALENT:
            current = ledger.current_effective_state(writer, fact.effective_key)
            if current is None or current["fact_id"] != fact.revalidated_fact_id:
                raise ValueError("Displaced equivalent authority application")
    for fact in facts:
        if fact.storage_relation == StorageRelation.CURRENT_EQUIVALENT:
            continue
        ledger._make_effective(
            writer, fact, exact=fact.storage_relation == StorageRelation.ADVANCED
        )
