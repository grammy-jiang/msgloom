"""Publish exact Mail impacts inside the winning authority transaction."""

from datetime import datetime

from sqlalchemy import select

from message_ingest.acquisition.handoff import (
    AcquisitionFactKind as Kind,
)
from message_ingest.acquisition.handoff import (
    AcquisitionStream,
    FactSpec,
    ReleaseEntryKind,
    ReleaseEntrySpec,
    ReleaseGroupSpec,
    ReleaseKind,
    StorageRelation,
    source_state_key,
)
from message_ingest.catalog.models.handoff import AcquisitionFact
from message_ingest.catalog.models.microsoft.outlook.email import (
    MailFolderPresence,
    MailFolderRecord,
    MessageRecord,
)
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore


def stage_presence(
    store,
    session,
    record,
    resource_kind,
    identity,
    is_present,
    run_id,
    observed_at,
    evidence_id,
    reason,
):
    """
    Stage a promotion transition, without bootstrapping unchanged history.
    """
    ledger = AcquisitionHandoffStore(store.catalog)
    scope_kind = "mail_folder" if resource_kind == "mail_folder" else "mailbox"
    spec = FactSpec(
        source_id=store.source_id,
        stream=AcquisitionStream.OUTLOOK_MAIL,
        run_id=run_id,
        spider_name=store.spider_name,
        fact_kind=Kind.SCOPED_STATE_TRANSITION,
        resource_kind=resource_kind,
        resource_identity=identity,
        provider_observed_at=observed_at,
        source_state_key=source_state_key({"is_present": is_present}),
        storage_relation=(
            StorageRelation.CURRENT_EQUIVALENT
            if record is not None and record.is_present == is_present
            else StorageRelation.ADVANCED
        ),
        scope_kind=scope_kind,
        scope_identity=identity if resource_kind == "mail_folder" else store.source_id,
        component_kind="folder_presence"
        if resource_kind == "mail_folder"
        else "mailbox_presence",
        evidence_id=evidence_id,
        transition_reason=reason or "inventory_present",
    )
    ledger.stage_state_fact_in_session(session, spec)


def _staged_winner(session, source_id, fact):
    """Reject pending observations displaced by newer provider state."""
    if fact.resource_kind == "mail_folder":
        record = session.scalar(
            select(MailFolderRecord).filter_by(
                source_id=source_id,
                folder_id=fact.resource_identity,
            )
        )
        if record is not None and datetime.fromisoformat(
            record.latest_observed_at
        ) > datetime.fromisoformat(fact.provider_observed_at):
            return False
        model, identity = MailFolderPresence, MailFolderPresence.folder_id
    elif fact.component_kind == "folder_membership":
        model, identity = MessageRecord, MessageRecord.message_id
    else:
        return False
    row = session.scalar(
        select(model).where(
            model.source_id == source_id, identity == fact.resource_identity
        )
    )
    return row is None or datetime.fromisoformat(fact.provider_observed_at) >= (
        datetime.fromisoformat(row.latest_observed_at)
    )


def release_mail_authority(
    catalog,
    session,
    *,
    source_id,
    run_id,
    committed_at,
    subject,
):
    """
    Bind current run facts to one atomic authority decision.

    The ledger filters released, stale and displaced states. Pending scoped
    observations win only if no newer domain observation displaced them.
    Group input order is stable across retries.
    """
    ledger = AcquisitionHandoffStore(catalog)
    facts = [
        FactSpec.from_json(payload)
        for payload in session.scalars(
            select(AcquisitionFact.payload).where(
                AcquisitionFact.source_id == source_id,
                AcquisitionFact.stream == AcquisitionStream.OUTLOOK_MAIL,
                AcquisitionFact.run_id == run_id,
            )
        )
    ]
    pending = {}
    for fact in facts:
        if fact.storage_relation != StorageRelation.AUTHORITY_STAGED:
            continue
        if not _staged_winner(session, source_id, fact):
            continue
        key = fact.effective_key.digest
        prior = pending.get(key)
        when = datetime.fromisoformat(fact.provider_observed_at)
        previous = datetime.fromisoformat(prior.provider_observed_at) if prior else None
        if prior is not None and when == previous:
            if fact.source_state_key != prior.source_state_key:
                raise ValueError("Ambiguous Mail authority state at one provider time")
            # Equivalent same-time captures have no competing semantic state.
            if fact.fact_id < prior.fact_id:
                pending[key] = fact
        elif previous is None or when > previous:
            pending[key] = fact
    if subject == "folder_delta":
        from message_ingest.catalog.stores.microsoft.outlook._email_release_folders import (
            apply_folder_transitions,
        )

        apply_folder_transitions(session, source_id, pending.values())
    winning = {fact.fact_id for fact in pending.values()}
    entries = []
    roles = {
        Kind.RESOURCE_OBSERVATION: ("primary", ReleaseEntryKind.RESOURCE),
        Kind.COMPONENT_OBSERVATION: ("component", ReleaseEntryKind.COMPONENT),
        Kind.CONTROL_CONTEXT: ("context", ReleaseEntryKind.CONTEXT),
        Kind.SCOPED_STATE_TRANSITION: ("transition", ReleaseEntryKind.TRANSITION),
    }
    impacts = {}
    included = set()
    for fact in sorted(facts, key=lambda value: value.fact_id):
        if fact.storage_relation == StorageRelation.STALE:
            continue
        if (
            fact.storage_relation == StorageRelation.AUTHORITY_STAGED
            and fact.fact_id not in winning
        ):
            continue
        if fact.storage_relation != StorageRelation.AUTHORITY_STAGED:
            # The pending winner replaces this key in the same transaction.
            # An older member would make the entire impact ineligible.
            if fact.effective_key.digest in pending:
                continue
            current = ledger.current_effective_state(session, fact.effective_key)
            expected = fact.revalidated_fact_id or fact.fact_id
            if current is None or current["fact_id"] != expected:
                continue
        role, kind = roles[Kind(fact.fact_kind)]
        effective_id = fact.revalidated_fact_id or fact.fact_id
        if (effective_id, role) in included:
            continue
        included.add((effective_id, role))
        key = (
            fact.resource_kind,
            fact.resource_identity,
            kind,
            fact.parent_resource_kind,
            fact.parent_resource_identity,
            fact.scope_kind,
            fact.scope_identity,
        )
        impacts.setdefault(key, []).append((fact.fact_id, role))
    for key, members in sorted(impacts.items(), key=lambda item: str(item[0])):
        resource, identity, kind, parent, parent_id, scope, scope_id = key
        entries.append(
            ReleaseEntrySpec(
                resource_kind=resource,
                resource_identity=identity,
                entry_kind=kind,
                facts=tuple(members),
                parent_resource_kind=parent,
                parent_resource_identity=parent_id,
                scope_kind=scope,
                scope_identity=scope_id,
            )
        )
    return ledger.release_authority_group_in_session(
        session,
        ReleaseGroupSpec(
            source_id=source_id,
            stream=AcquisitionStream.OUTLOOK_MAIL,
            release_kind=ReleaseKind.AUTHORITY_SCOPE,
            subject_kind=subject,
            subject_identity=source_id,
            owner_run_id=run_id,
            released_at=committed_at,
            coverage_kind="complete",
            scope_kind="mailbox",
            scope_identity=source_id,
            authority_revision=run_id,
        ),
        entries,
        winning_fact_ids=sorted(winning),
    )
