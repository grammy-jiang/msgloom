"""Publish exact Mail impacts inside the winning authority transaction."""

from dataclasses import replace

from sqlalchemy import select

from message_ingest.acquisition.handoff import (
    AcquisitionFactKind as Kind,
)
from message_ingest.acquisition.handoff import (
    AcquisitionStream,
    EffectiveStateKey,
    FactSpec,
    ReleaseEntryKind,
    ReleaseEntrySpec,
    ReleaseGroupSpec,
    ReleaseKind,
    StorageRelation,
    source_state_key,
)
from message_ingest.catalog.models.handoff import AcquisitionFact
from message_ingest.catalog.models.microsoft.outlook._email_bindings import (
    MailApplicationBinding,
)
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore


def _component_matches_parent_version(fact: FactSpec, version: str) -> bool:
    """Check the exact original parent even for evidence-free terminal outcomes.

    A terminal unsupported/unavailable Mail surface has no evidence locator.
    The component state hash still includes its original resource_version,
    so reconstruct that bounded producer-owned semantic state before deciding
    whether a later accepted Full primary can serve as its exact parent.
    """
    locator = fact.source_version_locator
    if locator is not None:
        return locator.resource_version == version
    if (
        fact.resource_kind != "message_surface"
        or not fact.component_kind
        or fact.evidence_id is not None
    ):
        return False
    from message_ingest.catalog.stores.microsoft.outlook._email_handoff import (
        decode_surface_reason,
    )

    status, profile = decode_surface_reason(fact.transition_reason)
    state = {
        "surface": fact.component_kind,
        "status": status,
        "profile": profile,
        "resource_version": version,
    }
    if status == "acquired":
        if fact.component_kind != "discovery":
            return False
        state["representation"] = version
    return source_state_key(state) == fact.source_state_key


def _component_matches_primary_application(
    session, fact: FactSpec, primary: str
) -> bool:
    """Exclude stale selected Full components after a semantically equal ABA.

    Selected captures have immutable application bindings to exact primary fact
    IDs, not merely to provider-version hashes. Current-equivalent captures
    publish their revalidated effective fact ID. Unselected Delta/discovery
    surfaces legitimately have no application binding and are version-checked
    separately by the caller.
    """
    effective_id = (
        fact.revalidated_fact_id
        if fact.storage_relation == StorageRelation.CURRENT_EQUIVALENT
        and fact.revalidated_fact_id
        else fact.fact_id
    )
    parents = session.scalars(
        select(MailApplicationBinding.primary_fact_id).where(
            MailApplicationBinding.source_id == fact.source_id,
            MailApplicationBinding.fact_id == effective_id,
            MailApplicationBinding.capture_id.is_not(None),
        )
    ).all()
    return not parents or primary in parents


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
    # A newer collected message or folder may already have toggled the mutable
    # presence projection before authority reconciliation. Existing A1 effective
    # state, not the mutable row alone, decides whether this is real restoration.
    if spec.storage_relation == StorageRelation.CURRENT_EQUIVALENT:
        current = ledger.current_effective_state(session, spec.effective_key)
        if current is not None and current["source_state_key"] != spec.source_state_key:
            spec = replace(spec, storage_relation=StorageRelation.ADVANCED)
    ledger.stage_state_fact_in_session(session, spec)
    if resource_kind == "mail_folder":
        from message_ingest.catalog.stores.microsoft.outlook._email_observations import (
            clear_folder_owner,
        )

        clear_folder_owner(session, store.source_id, identity)


def release_mail_authority(
    catalog,
    session,
    *,
    source_id,
    run_id,
    committed_at,
    subject,
    applied=None,
):
    """
    Bind current run facts to one atomic authority decision.

    The ledger filters released, stale and displaced states. Retained inputs
    require explicit selection by the validated authority application. That
    application also preserves newer independent observations. Group input
    order is stable across retries.
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
    from message_ingest.catalog.models.microsoft.outlook._email_authority import (
        MailAuthorityObservation,
    )

    retained = set(
        session.scalars(
            select(MailAuthorityObservation.fact_id).where(
                MailAuthorityObservation.source_id == source_id,
                MailAuthorityObservation.run_id == run_id,
            )
        )
    )
    pending = applied or {}
    winning = {fact.fact_id for fact in pending.values()}
    entries = []
    roles = {
        Kind.RESOURCE_OBSERVATION: ("primary", ReleaseEntryKind.RESOURCE),
        Kind.COMPONENT_OBSERVATION: ("component", ReleaseEntryKind.COMPONENT),
        Kind.CONTROL_CONTEXT: ("context", ReleaseEntryKind.CONTEXT),
        Kind.SCOPED_STATE_TRANSITION: ("transition", ReleaseEntryKind.TRANSITION),
    }
    impacts = {}
    run_facts = {fact.fact_id: fact for fact in facts}
    included = set()
    for fact in sorted(facts, key=lambda value: value.fact_id):
        if fact.fact_id in retained and fact.fact_id not in winning:
            continue
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
            if fact.effective_key.digest in pending and fact.fact_id not in winning:
                continue
            current = ledger.current_effective_state(session, fact.effective_key)
            expected = (
                fact.revalidated_fact_id
                if fact.storage_relation == StorageRelation.CURRENT_EQUIVALENT
                else fact.fact_id
            )
            if current is None or current["fact_id"] != expected:
                continue
        role, kind = roles[Kind(fact.fact_kind)]
        effective_id = (
            fact.revalidated_fact_id
            if fact.storage_relation == StorageRelation.CURRENT_EQUIVALENT
            else fact.fact_id
        )
        if (effective_id, role) in included:
            continue
        included.add((effective_id, role))
        # A Mail component changes the exact message it belongs to. Releasing
        # a stand-alone message_surface entry would force the A2 Reader to
        # reconstruct a component without the immutable primary it requires.
        # Preserve other direct impacts (folders, presence and transitions).
        if (
            kind == ReleaseEntryKind.COMPONENT
            and fact.parent_resource_kind == "message"
        ):
            if not fact.parent_resource_identity:
                raise ValueError("Mail component has no original message parent")
            key = (
                "message",
                fact.parent_resource_identity,
                ReleaseEntryKind.RESOURCE,
                None,
                None,
                None,
                None,
            )
        else:
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
        if resource == "message" and kind == ReleaseEntryKind.RESOURCE:
            primary_ids = [fact_id for fact_id, role in members if role == "primary"]
            if len(primary_ids) > 1:
                raise ValueError("Mail impact has ambiguous primary")
            primary_key = EffectiveStateKey(
                source_id=source_id,
                stream=AcquisitionStream.OUTLOOK_MAIL,
                resource_kind="message",
                resource_identity=identity,
            )
            if primary_ids:
                # Even a same-run Full primary cannot acquire a component
                # captured against an earlier version of the message.
                accepted = run_facts.get(primary_ids[0])
                if accepted is None or accepted.effective_key != primary_key:
                    raise ValueError("Mail impact primary identity is invalid")
            else:
                # A later independently accepted Full can provide the exact
                # same-version primary for a pending Delta component.
                current = ledger.current_effective_state(session, primary_key)
                if current is None:
                    # Pre-ledger history may have no effective fact. Do not
                    # fabricate a primary or veto the provider cursor.
                    continue
                row = session.get(AcquisitionFact, current["fact_id"])
                if row is None:
                    raise ValueError("Mail component accepted primary is missing")
                accepted = FactSpec.from_json(row.payload)
                if (
                    accepted.fact_id != current["fact_id"]
                    or accepted.effective_key != primary_key
                    or accepted.source_state_key != current["source_state_key"]
                ):
                    raise ValueError("Mail component accepted primary is invalid")

            version = accepted.source_state_key
            if version is None:
                raise ValueError("Mail accepted primary has no semantic version")
            selected = []
            for member_id, role in members:
                if role != "component":
                    selected.append((member_id, role))
                    continue
                component = run_facts.get(member_id)
                if component is None:
                    raise ValueError("Mail component member is not retained")
                if _component_matches_parent_version(
                    component, version
                ) and _component_matches_primary_application(
                    session, component, accepted.fact_id
                ):
                    selected.append((member_id, role))
                # A stale component from either this run or a displaced run
                # does not suppress legitimate cursor or primary publication.
            if not primary_ids:
                if not selected:
                    continue
                selected.insert(0, (accepted.fact_id, "primary"))
            members = selected
            # Fact iteration is hash ordered. Preserve primary-first membership
            # independent of callback completion order.
            members.sort(key=lambda item: (item[1] != "primary", item[0]))
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
