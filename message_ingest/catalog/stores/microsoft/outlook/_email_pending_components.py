"""Keep delta components bound to their original provisional primary."""

import json

from sqlalchemy import select

from message_ingest.acquisition.handoff import (
    AcquisitionFactKind as Kind,
)
from message_ingest.acquisition.handoff import (
    AcquisitionStream,
    EffectiveStateKey,
    StorageRelation,
)
from message_ingest.catalog.models.handoff import AcquisitionFact
from message_ingest.catalog.models.microsoft.outlook._email_authority import (
    MailAuthorityDecision as Decision,
)
from message_ingest.catalog.models.microsoft.outlook._email_authority import (
    MailAuthorityObservation as Observation,
)

from ._email_handoff import (
    MailPersistenceOutcome,
    is_stale,
    surface_reason,
    verified_digest,
)
from ._email_observations import (
    accepted_is_newer,
    application_fact,
    capture_key,
    head,
    load_fact,
    local_current,
    require_open,
    retain,
)


def pending_primary(session, source, run, message):
    """Read a run-local primary without falling back to another run's row."""
    key = EffectiveStateKey(
        source_id=source,
        stream=AcquisitionStream.OUTLOOK_MAIL,
        resource_kind="message",
        resource_identity=message,
    ).digest
    return session.scalar(
        select(Observation)
        .join(AcquisitionFact, AcquisitionFact.fact_id == Observation.fact_id)
        .where(
            AcquisitionFact.storage_relation != StorageRelation.STALE,
            Observation.source_id == source,
            Observation.run_id == run,
            Observation.effective_key == key,
        )
        .order_by(Observation.sequence.desc())
        .limit(1)
    )


def selection_is_accepted(session, binding):
    """A pending equivalent pin cannot apply components before its CAS wins."""
    row = session.scalar(
        select(Observation).where(
            Observation.source_id == binding.source_id,
            Observation.fact_id == binding.fact_id,
        )
    )
    if row is None:
        return True
    allowed = session.info.get("mail_authority_applied", set())
    if binding.fact_id in allowed:
        return True
    decision = session.get(Decision, (row.source_id, row.run_id, row.authority_kind))
    return (
        decision is not None
        and binding.fact_id in json.loads(decision.payload)["applied"]
    )


def stage_surface(
    store,
    session,
    parent,
    *,
    run_id,
    message_id,
    surface,
    status,
    evidence_id,
    observed_at,
    profile_version,
    resource_version,
):
    """Retain unselected collection surfaces with an exact primary pin."""
    primary = load_fact(session, parent)
    version = resource_version or primary.source_state_key
    if primary.source_state_key != version:
        raise ValueError("Delta component disagrees with run-local primary")
    key = EffectiveStateKey(
        source_id=store.source_id,
        stream=AcquisitionStream.OUTLOOK_MAIL,
        resource_kind="message_surface",
        resource_identity=message_id,
        component_kind=surface,
        parent_resource_kind="message",
        parent_resource_identity=message_id,
    ).digest
    previous = head(
        session,
        store.source_id,
        run_id,
        parent.authority_kind,
        parent.scope_identity,
        "message_surface",
        message_id,
        effective_key=key,
    )
    data = {
        "surface": surface,
        "status": status,
        "profile_version": profile_version,
        "parent_fact_id": primary.fact_id,
        "resource_version": version,
    }
    capture = capture_key(data, evidence_id, observed_at)
    if previous is not None and previous.capture_key == capture:
        fact = load_fact(session, previous)
        return MailPersistenceOutcome(fact, StorageRelation(fact.storage_relation))
    require_open(session, store.source_id, run_id, parent.authority_kind)
    state = {
        "surface": surface,
        "status": status,
        "profile": profile_version,
        "resource_version": version,
    }
    if status == "acquired":
        if surface == "discovery":
            state["representation"] = version
        else:
            state["content_sha256"] = verified_digest(
                session, store.source_id, evidence_id
            )
    writer = store._facts()
    accepted = writer.effective_fact(
        session, "message_surface", message_id, surface, message_id
    )
    outcome = writer.stage(
        session,
        run_id=run_id,
        resource_id=message_id,
        state=state,
        evidence_id=evidence_id,
        observed_at=observed_at,
        kind=Kind.COMPONENT_OBSERVATION,
        resource_kind="message_surface",
        component=surface,
        parent_id=message_id,
        resource_version=version,
        reason=surface_reason(status, profile_version),
        provisional=True,
        provisional_current=local_current(session, previous, accepted),
        stale=previous is not None
        and is_stale(observed_at, load_fact(session, previous).provider_observed_at),
    )
    retain(
        session,
        outcome.fact,
        authority=parent.authority_kind,
        scope=parent.scope_identity,
        capture=capture,
        payload=data,
    )
    return outcome


def apply_surfaces(store, session, rows, applied):
    """Apply only surfaces whose exact original primary was selected."""
    from message_ingest.catalog.models.microsoft.outlook.email import MessageSurface

    accepted = {fact.fact_id for fact in applied} | session.info.get(
        "mail_authority_applied", set()
    )
    ledger = store._facts().ledger
    for row in rows:
        fact = load_fact(session, row)
        if fact.resource_kind != "message_surface":
            continue
        data = json.loads(row.payload)
        if data["parent_fact_id"] not in accepted:
            continue
        application = application_fact(session, ledger, row, fact)
        if application is None:
            continue
        record = session.scalar(
            select(MessageSurface).filter_by(
                source_id=store.source_id,
                message_id=fact.resource_identity,
                surface=data["surface"],
            )
        )
        if record is not None and accepted_is_newer(
            session,
            fact.effective_key.digest,
            row.authority_kind,
            row.scope_identity,
            fact.provider_observed_at,
            record.observed_at,
        ):
            # Independent/Full component data is newer than this run's
            # provisional capture. Do not rewind the mutable projection OR
            # advance its effective fact pointer/release membership.
            continue
        if record is None:
            record = MessageSurface(
                source_id=store.source_id,
                message_id=fact.resource_identity,
                surface=data["surface"],
            )
            session.add(record)
        record.status = data["status"]
        record.profile_version = data["profile_version"]
        record.evidence_id = fact.evidence_id
        record.observed_at = fact.provider_observed_at
        applied.append(application)
        session.info["mail_authority_applied"].add(fact.fact_id)
