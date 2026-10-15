"""Capture message-delta projections in their original folder authority."""

import json
from dataclasses import replace
from uuid import uuid4

from sqlalchemy import select

from message_ingest.acquisition.handoff import (
    AcquisitionStream,
    EffectiveStateKey,
    StorageRelation,
)
from message_ingest.catalog.models.microsoft.outlook.email import (
    MessageObservation,
    MessageRecord,
)

from ._email_handoff import MailPersistenceOutcome, is_stale, primary_projection
from ._email_observations import (
    MESSAGE_FIELDS,
    capture_key,
    head,
    load_fact,
    local_current,
    require_open,
    retain,
    verify_resource,
)


def record_pending_message(
    store,
    session,
    *,
    run_id,
    message,
    kind,
    evidence_id,
    observed_at,
    selection_id,
    authority_scope,
):
    """
    Pin omitted fields to accepted state or this scope's prior input.

    Explicit null, false and empty values remain explicit. A new application
    after A/B/A receives its own fact identity. An exact current retry reuses
    its observation and fact, including when no evidence was supplied.
    """
    scope = authority_scope or message.get("parentFolderId")
    if not isinstance(scope, str) or not scope or not run_id:
        raise ValueError("Message delta requires original run and folder scope")
    identity = message["id"]
    key = EffectiveStateKey(
        source_id=store.source_id,
        stream=AcquisitionStream.OUTLOOK_MAIL,
        resource_kind="message",
        resource_identity=identity,
    ).digest
    previous = head(
        session,
        store.source_id,
        run_id,
        "message_delta",
        scope,
        "message",
        identity,
        effective_key=key,
    )
    capture = capture_key(message, kind, evidence_id, observed_at, selection_id)
    if previous is not None and previous.capture_key == capture:
        fact = load_fact(session, previous)
        return MailPersistenceOutcome(
            fact, StorageRelation(fact.storage_relation), selection_id=selection_id
        )
    require_open(session, store.source_id, run_id, "message_delta")
    verify_resource(session, store.source_id, evidence_id, message)
    record = session.scalar(
        select(MessageRecord).filter_by(source_id=store.source_id, message_id=identity)
    )
    fields = (
        json.loads(previous.payload)["projection"]
        if previous
        else {name: getattr(record, name, None) for name in MESSAGE_FIELDS.values()}
    )
    fields = {
        **fields,
        **{
            column: message[key]
            for key, column in MESSAGE_FIELDS.items()
            if key in message
        },
    }
    writer = store._facts()
    accepted = writer.effective_fact(session, "message", identity)
    current = local_current(session, previous, accepted)
    stale = previous is not None and is_stale(
        observed_at, load_fact(session, previous).provider_observed_at
    )
    observation, created = store._add_observation(
        session,
        MessageObservation(
            observation_id=uuid4().hex,
            source_id=store.source_id,
            message_id=identity,
            run_id=run_id,
            kind=kind,
            evidence_id=evidence_id,
            observed_at=observed_at,
            parent_folder_id=message.get("parentFolderId"),
            last_modified_date_time=message.get("lastModifiedDateTime"),
            removed_reason=None,
        ),
    )
    outcome = writer.stage(
        session,
        run_id=run_id,
        resource_id=identity,
        state=primary_projection(message),
        evidence_id=evidence_id,
        observed_at=observed_at,
        observation_id=observation.observation_id,
        resource_version=message.get("changeKey") or None,
        stale=stale,
        provisional=True,
        provisional_current=current,
    )
    retain(
        session,
        outcome.fact,
        authority="message_delta",
        scope=scope,
        capture=capture,
        payload={
            "resource": message,
            "projection": fields,
            "selection_id": selection_id,
        },
    )
    if selection_id is not None:
        from ._email_associations import MailAssociations

        MailAssociations(store).bind_primary(
            session, selection_id, outcome, evidence_id
        )
    return replace(outcome, observation_created=created, selection_id=selection_id)
