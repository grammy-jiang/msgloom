"""Select and apply Mail-owned inputs inside the original CAS transaction."""

import json

from sqlalchemy import select

from message_ingest.acquisition.handoff import AcquisitionStream, StorageRelation
from message_ingest.catalog.models.handoff import AcquisitionFact
from message_ingest.catalog.models.microsoft.outlook._email_authority import (
    MailAuthorityObservation as Observation,
)
from message_ingest.catalog.models.microsoft.outlook.email import (
    MailFolderPresence,
    MailFolderRecord,
    MessageObservation,
    MessageRecord,
)

from ._email_observations import (
    accepted_is_newer,
    application_fact,
    load_fact,
    project_message,
    set_owner,
    verify_resource,
)


def selected_observations(session, source, run, authority, scopes):
    """Choose local heads, never another run's speculative mutable state."""
    rows = session.scalars(
        select(Observation)
        .where(
            Observation.source_id == source,
            Observation.run_id == run,
            Observation.authority_kind == authority,
        )
        .order_by(Observation.sequence)
    ).all()
    selected = {}
    for row in rows:
        if row.scope_identity not in scopes:
            raise ValueError("Mail observation is outside validated authority scope")
        fact = load_fact(session, row)
        if fact.storage_relation == StorageRelation.STALE:
            continue
        prior = selected.get(row.effective_key)
        if (
            prior is not None
            and prior.scope_identity != row.scope_identity
            and load_fact(session, prior).source_state_key != fact.source_state_key
        ):
            raise ValueError("Unordered competing Mail authority scopes")
        selected[row.effective_key] = row
    return list(selected.values())


def apply_mail_observations(store, session, *, run_id, authority, scopes):
    """
    Apply only selected projections, pointers and exact bound components.

    Caller validates the cursor generations before entering here. Every
    mutation remains in that caller's writer transaction and rolls back with
    cursor, release, or projection failure. Legacy delta facts without retained
    projections are unknown and require reacquisition.
    """
    ledger = store._facts().ledger
    rows = selected_observations(session, store.source_id, run_id, authority, scopes)
    retained = set(
        session.scalars(
            select(Observation.fact_id).where(
                Observation.source_id == store.source_id,
                Observation.run_id == run_id,
            )
        )
    )
    legacy_messages = set(
        session.scalars(
            select(MessageObservation.message_id).where(
                MessageObservation.source_id == store.source_id,
                MessageObservation.run_id == run_id,
                MessageObservation.kind == "delta",
            )
        )
    )
    from message_ingest.acquisition.handoff import FactSpec

    for payload in session.scalars(
        select(AcquisitionFact.payload).where(
            AcquisitionFact.source_id == store.source_id,
            AcquisitionFact.stream == AcquisitionStream.OUTLOOK_MAIL,
            AcquisitionFact.run_id == run_id,
        )
    ):
        fact = FactSpec.from_json(payload)
        if fact.fact_id not in retained and (
            fact.storage_relation == StorageRelation.AUTHORITY_STAGED
            or (
                fact.resource_kind == "message"
                and fact.component_kind is None
                and fact.resource_identity in legacy_messages
            )
        ):
            raise RuntimeError(
                "Legacy Mail authority observation requires reacquisition"
            )
    applied, messages, cache = [], [], {}
    selected_ids = set()
    facts = {row.sequence: load_fact(session, row) for row in rows}
    contexts = {
        (row.resource_kind, row.resource_id): facts[row.sequence]
        for row in rows
        if facts[row.sequence].component_kind is None
    }
    for row in rows:
        fact, data = facts[row.sequence], json.loads(row.payload)
        if fact.resource_kind == "message":
            model, query = MessageRecord, {"message_id": fact.resource_identity}
        elif fact.resource_kind == "mail_folder":
            model, query = MailFolderRecord, {"folder_id": fact.resource_identity}
        else:
            continue
        record = session.scalar(
            select(model).filter_by(source_id=store.source_id, **query)
        )
        # Presence and metadata can have separate independent observations.
        times = [record.latest_observed_at] if record is not None else []
        if model is MailFolderRecord:
            presence = session.scalar(
                select(MailFolderPresence).filter_by(source_id=store.source_id, **query)
            )
            if presence is not None:
                times.append(presence.latest_observed_at)
        # All folder facts use the context ownership for their shared row.
        context = contexts.get((row.resource_kind, row.resource_id), fact)
        if any(
            accepted_is_newer(
                session,
                context.effective_key.digest,
                authority,
                row.scope_identity,
                fact.provider_observed_at,
                time,
            )
            for time in times
        ):
            continue
        application = application_fact(session, ledger, row, fact)
        if application is None:
            continue
        if data["resource"].get("id") != fact.resource_identity:
            raise ValueError("Mail authority projection changed its resource identity")
        verify_resource(
            session, store.source_id, fact.evidence_id, data["resource"], cache=cache
        )
        if model is MessageRecord and fact.component_kind is None:
            project_message(
                session,
                store.source_id,
                fact.resource_identity,
                data["projection"],
                fact.provider_observed_at,
                fact.evidence_id,
            )
            store.mark_message_present_in_session(
                session,
                message_id=fact.resource_identity,
                run_id=run_id,
                observed_at=fact.provider_observed_at,
                evidence_id=fact.evidence_id,
            )
            messages.append(fact.resource_identity)
        elif (
            model is MailFolderRecord
            and data["present"]
            and fact.component_kind is None
        ):
            if record is None:
                record = MailFolderRecord(source_id=store.source_id, **query)
                session.add(record)
            for name, value in data["projection"].items():
                setattr(record, name, value)
            record.latest_observed_at = fact.provider_observed_at
            record.latest_evidence_id = fact.evidence_id
        set_owner(session, fact, row)
        applied.append(application)
        selected_ids.update((fact.fact_id, application.fact_id))
    from ._email_pending_components import apply_surfaces

    session.info["mail_authority_applied"] = selected_ids
    apply_surfaces(store, session, rows, applied)
    ledger.apply_authority_facts_in_session(
        session,
        source_id=store.source_id,
        stream=AcquisitionStream.OUTLOOK_MAIL,
        fact_ids=[fact.fact_id for fact in applied],
    )
    if authority == "folder_delta":
        from ._email_release_folders import apply_folder_transitions

        apply_folder_transitions(session, store.source_id, applied)
    from ._email_associations import MailAssociations

    session.info["mail_authority_applied"].update(fact.fact_id for fact in applied)
    for message in messages:
        MailAssociations(store).reconcile(session, message)
    return {fact.effective_key.digest: fact for fact in applied}
