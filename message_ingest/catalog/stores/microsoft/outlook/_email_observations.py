"""Retain exact Mail authority inputs without changing accepted state."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import delete, select, true

from message_ingest.acquisition.handoff import (
    AcquisitionStream,
    EffectiveStateKey,
    FactSpec,
    StorageRelation,
)
from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.catalog.models.handoff import AcquisitionFact
from message_ingest.catalog.models.microsoft.outlook._email_authority import (
    MailAuthorityDecision as Decision,
)
from message_ingest.catalog.models.microsoft.outlook._email_authority import (
    MailAuthorityObservation as Observation,
)
from message_ingest.catalog.models.microsoft.outlook._email_authority import (
    MailProjectionOwner as Owner,
)

from ._email_handoff import is_stale, semantic_digest, verified_digest

MESSAGE_FIELDS = {
    "subject": "subject",
    "internetMessageId": "internet_message_id",
    "conversationId": "conversation_id",
    "parentFolderId": "parent_folder_id",
    "receivedDateTime": "received_date_time",
    "lastModifiedDateTime": "last_modified_date_time",
    "isRead": "is_read",
    "hasAttachments": "has_attachments",
}


def head(
    session, source, run, authority, scope, resource, identity, *, effective_key=None
):
    """Read one durable run/scope head, excluding stale local observations."""
    return session.scalar(
        select(Observation)
        .join(AcquisitionFact, AcquisitionFact.fact_id == Observation.fact_id)
        .where(
            Observation.source_id == source,
            Observation.run_id == run,
            Observation.authority_kind == authority,
            Observation.scope_identity == scope,
            Observation.resource_kind == resource,
            Observation.resource_id == identity,
            Observation.effective_key == effective_key if effective_key else true(),
            AcquisitionFact.storage_relation != StorageRelation.STALE,
        )
        .order_by(Observation.sequence.desc())
        .limit(1)
    )


def load_fact(session, row):
    """Load the immutable fact explicitly named by a retained observation."""
    fact = session.get(AcquisitionFact, row.fact_id)
    if fact is None:
        raise ValueError("Mail authority observation has no fact")
    result = FactSpec.from_json(fact.payload)
    if result.fact_id != row.fact_id:
        raise ValueError("Mail authority fact digest mismatch")
    if (
        result.source_id,
        result.run_id,
        result.stream,
        result.resource_kind,
        result.resource_identity,
        result.effective_key.digest,
    ) != (
        row.source_id,
        row.run_id,
        AcquisitionStream.OUTLOOK_MAIL,
        row.resource_kind,
        row.resource_id,
        row.effective_key,
    ):
        raise ValueError("Mail authority observation changed its original ownership")
    return result


def local_current(session, row, accepted):
    """Use a run-local application, preserving exact equivalent pins."""
    fact = load_fact(session, row) if row else accepted
    if fact is None:
        return None
    return {
        "fact_id": fact.revalidated_fact_id
        if fact.storage_relation == StorageRelation.CURRENT_EQUIVALENT
        else fact.fact_id,
        "source_state_key": fact.source_state_key,
    }


def application_fact(session, ledger, row, fact):
    """
    Resolve a local equivalent to its original, still-selected application.

    Only a retained earlier advanced application in the exact same authority
    can be applied provisionally. An equivalent pin to external accepted
    state must still be current; it never follows an ABA semantic return.
    """
    if fact.storage_relation != StorageRelation.CURRENT_EQUIVALENT:
        return fact
    prior = session.scalar(
        select(Observation)
        .where(
            Observation.source_id == row.source_id,
            Observation.run_id == row.run_id,
            Observation.authority_kind == row.authority_kind,
            Observation.scope_identity == row.scope_identity,
            Observation.fact_id == fact.revalidated_fact_id,
            Observation.sequence < row.sequence,
        )
        .order_by(Observation.sequence.desc())
        .limit(1)
    )
    if prior is not None:
        original = load_fact(session, prior)
        if (
            original.storage_relation == StorageRelation.ADVANCED
            and original.source_state_key == fact.source_state_key
        ):
            return original
    current = ledger.current_effective_state(session, fact.effective_key)
    return (
        fact
        if current is not None and current["fact_id"] == fact.revalidated_fact_id
        else None
    )


def retain(session, fact, *, authority, scope, capture, payload):
    """Append local application order; never put it in provider order."""
    row = Observation(
        source_id=fact.source_id,
        run_id=fact.run_id,
        authority_kind=authority,
        scope_identity=scope,
        resource_kind=fact.resource_kind,
        resource_id=fact.resource_identity,
        effective_key=fact.effective_key.digest,
        capture_key=capture,
        fact_id=fact.fact_id,
        payload=json.dumps(payload, sort_keys=True, allow_nan=False),
    )
    session.add(row)
    session.flush()
    return row


def require_open(session, source, run, authority):
    """A sealed promotion may be retried, but cannot acquire new inputs."""
    if session.get(Decision, (source, run, authority)) is not None:
        raise RuntimeError("Mail authority input set is sealed")


def verify_resource(session, source, evidence, resource, *, cache=None):
    """
    Verify the exact resource in its own saved response, once per page.

    Canonical evidence can belong to a prior capture run. Source, bytes and
    resource fields must match; the observation keeps the current logical run.
    """
    if evidence is None:
        return
    if cache is not None and evidence in cache:
        values = cache[evidence]
    else:
        verified_digest(session, source, evidence)
        row = session.get(RawHttpEvidence, evidence)
        payload = json.loads(Path(row.response_body_path).read_bytes())
        values = payload.get("value", [payload]) if isinstance(payload, dict) else []
        if not isinstance(values, list):
            raise ValueError("Invalid Mail authority evidence page")
        indexed = {}
        for value in values:
            if isinstance(value, dict) and "id" in value:
                indexed.setdefault(value["id"], []).append(value)
        values = indexed
        if cache is not None:
            cache[evidence] = values
    if not any(
        all(key in saved and saved[key] == value for key, value in resource.items())
        for saved in values.get(resource["id"], ())
    ):
        raise ValueError("Mail authority resource disagrees with saved evidence")


def accepted_is_newer(session, key, authority, scope, when, observed_at):
    """Keep independent freshness; a cursor lineage does not use wall time."""
    owner = session.get(Owner, key)
    if owner is not None:
        row = session.get(Observation, owner.observation_sequence)
        if row is None:
            raise ValueError("Missing Mail accepted projection owner")
        if (row.authority_kind, row.scope_identity) == (authority, scope):
            return False
    return is_stale(when, observed_at)


def set_owner(session, fact, row=None):
    """Independent observations clear ownership; accepted delta pins it."""
    key = fact.effective_key.digest
    if row is None:
        session.execute(delete(Owner).where(Owner.effective_key == key))
        return
    owner = session.get(Owner, key)
    if owner is None:
        session.add(Owner(effective_key=key, observation_sequence=row.sequence))
    else:
        owner.observation_sequence = row.sequence


def clear_folder_owner(session, source, folder):
    """An independent inventory presence decision ends delta row ownership."""
    key = EffectiveStateKey(
        source_id=source,
        stream=AcquisitionStream.OUTLOOK_MAIL,
        resource_kind="mail_folder",
        resource_identity=folder,
    )
    session.execute(delete(Owner).where(Owner.effective_key == key.digest))


def capture_key(*values):
    """Identify exact intake retries without mutable projection contents."""
    return semantic_digest(values)


def project_message(session, source, message_id, fields, observed_at, evidence):
    """Apply a complete projection resolved from a pinned intake baseline."""
    from message_ingest.catalog.models.microsoft.outlook.email import MessageRecord

    record = session.scalar(
        select(MessageRecord).filter_by(source_id=source, message_id=message_id)
    )
    if record is None:
        record = MessageRecord(source_id=source, message_id=message_id)
        session.add(record)
    for name in MESSAGE_FIELDS.values():
        setattr(record, name, fields[name])
    record.is_removed = False
    record.latest_observed_at = observed_at
    record.latest_evidence_id = evidence
