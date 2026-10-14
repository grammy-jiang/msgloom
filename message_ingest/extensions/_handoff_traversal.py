"""Validate durable additive traversal proof inside the release transaction."""

import json
from datetime import UTC, datetime

from sqlalchemy import select

from message_ingest.acquisition.handoff import (
    AcquisitionStream,
    FactSpec,
    ReleaseEntryKind,
    ReleaseEntrySpec,
    ReleaseGroupSpec,
    ReleaseKind,
)
from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.catalog.models.handoff import AcquisitionFact
from message_ingest.catalog.models.microsoft.contacts import (
    ContactCollectionCompletion,
    ContactFolderSighting,
)
from message_ingest.catalog.models.microsoft.teams.message import TeamsMessageCurrent
from message_ingest.catalog.models.microsoft.todo import (
    TodoTaskListSighting,
    TodoTaskSighting,
    TodoTraversalCompletion,
)
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from message_ingest.catalog.stores.microsoft.teams._common import scope_digest
from message_ingest.extensions._handoff_calendar import calendar_traversal_group
from message_ingest.extensions._handoff_mail import mail_discovery_group
from message_ingest.extensions._handoff_onedrive import onedrive_discovery_group

TRAVERSALS = {
    "microsoft_onedrive_discover": AcquisitionStream.ONEDRIVE,
    "outlook_calendar_discover": AcquisitionStream.OUTLOOK_CALENDAR,
    "outlook_calendar_window": AcquisitionStream.OUTLOOK_CALENDAR,
    "outlook_discover": AcquisitionStream.OUTLOOK_MAIL,
    "microsoft_todo_discover": AcquisitionStream.TODO,
    "microsoft_contacts_discover": AcquisitionStream.CONTACTS,
    "microsoft_teams_chat_discover": AcquisitionStream.TEAMS_CHAT,
    "microsoft_teams_channel_discover": AcquisitionStream.TEAMS_CHANNEL,
}

_TEAMS_STREAMS = {AcquisitionStream.TEAMS_CHAT, AcquisitionStream.TEAMS_CHANNEL}


def _rows(writer, model, source, run):
    return writer.scalars(select(model).filter_by(source_id=source, run_id=run)).all()


def _teams_complete(writer, source, spider):
    """Require successful initial inventory evidence before native idle release."""
    required = (
        {"teams-chat-list"}
        if spider.name == "microsoft_teams_chat_discover"
        else {"teams-associated-teams", "teams-joined-teams"}
    )
    facts = writer.scalars(
        select(AcquisitionFact.payload).where(
            AcquisitionFact.source_id == source,
            AcquisitionFact.run_id == spider.run_id,
        )
    ).all()
    successful = set()
    for payload in facts:
        fact = FactSpec.from_json(payload)
        if fact.resource_kind != "teams_inventory_completion":
            continue
        if fact.scope_kind != "teams_initial_inventory":
            return False
        evidence = writer.get(RawHttpEvidence, fact.evidence_id)
        if (
            evidence is None
            or evidence.source_id != source
            or evidence.response_status != 200
            or evidence.error_type is not None
            or evidence.purpose != fact.scope_identity
            or fact.source_version_locator is None
            or fact.source_version_locator.evidence_id != fact.evidence_id
        ):
            return False
        successful.add(fact.scope_identity)
    return required <= successful


def _complete(writer, source, spider):
    """
    Require current-run completion linked to valid canonical source evidence.

    Cache replay can reuse an older capture. Completion rows own the logical
    run; their exact evidence references retain the original capture run.
    """
    run = spider.run_id
    if spider.name in {
        "microsoft_teams_chat_discover",
        "microsoft_teams_channel_discover",
    }:
        return _teams_complete(writer, source, spider)
    if spider.name == "microsoft_todo_discover":
        completions = _rows(writer, TodoTraversalCompletion, source, run)
        actual = {(r.collection_kind, r.list_id, r.task_id) for r in completions}
        expected = {("task_lists", None, None)}
        expected.update(
            ("tasks", row.list_id, None)
            for row in _rows(writer, TodoTaskListSighting, source, run)
        )
        for row in _rows(writer, TodoTaskSighting, source, run):
            expected.add(("checklist_items", row.list_id, row.task_id))
            expected.add(("linked_resources", row.list_id, row.task_id))
    else:
        completions = _rows(writer, ContactCollectionCompletion, source, run)
        actual = {(r.collection_kind, r.scope_key) for r in completions}
        expected = {("folder_inventory", "root"), ("contacts", "default")}
        for row in _rows(writer, ContactFolderSighting, source, run):
            expected.add(("child_folders", f"folder:{row.folder_id}"))
            expected.add(("contacts", f"folder:{row.folder_id}"))
        if len({row.run_started_at for row in completions}) != 1:
            return False
    if actual != expected:
        return False
    for row in completions:
        if not row.evidence_id:
            return False
        evidence = writer.get(RawHttpEvidence, row.evidence_id)
        if (
            evidence is None
            or evidence.source_id != source
            or evidence.response_status != 200
            or evidence.error_type is not None
        ):
            return False
    return True


def _entries(catalog, writer, source, spider, stream):
    """Select current run facts and turn each bounded impact into one entry."""
    store = AcquisitionHandoffStore(catalog)
    payloads = writer.scalars(
        select(AcquisitionFact.payload)
        .where(
            AcquisitionFact.source_id == source,
            AcquisitionFact.stream == stream,
            AcquisitionFact.run_id == spider.run_id,
        )
        .order_by(AcquisitionFact.fact_id)
    ).all()
    selected = {}
    for payload in payloads:
        fact = FactSpec.from_json(payload)
        if (
            stream in _TEAMS_STREAMS
            and fact.resource_kind == "teams_inventory_completion"
        ):
            # Run-local completion proof is not an A2 content impact.
            continue
        if stream in _TEAMS_STREAMS and fact.resource_kind in {
            "teams_message",
            "teams_message_presence",
        }:
            try:
                parts = json.loads(fact.resource_identity)
            except (TypeError, ValueError):
                raise ValueError("Invalid Teams deletion release scope") from None
            if not isinstance(parts, list):
                raise ValueError("Invalid Teams deletion release scope")
            _scope, digest = scope_digest(("message", *parts))
            message_current = writer.get(TeamsMessageCurrent, (source, digest))
            if message_current is None:
                continue
            if fact.resource_kind == "teams_message":
                locator = fact.source_version_locator
                if locator is None or locator.observation_id is None:
                    continue
                try:
                    family, observation_id = json.loads(locator.observation_id)
                except (TypeError, ValueError):
                    continue
                if (
                    family != "message"
                    or type(observation_id) is not int
                    or message_current.message_observation_id != observation_id
                    or message_current.latest_evidence_id != fact.evidence_id
                ):
                    # Notification deletion or a newer captured message won.
                    continue
            elif fact.transition_reason == "observed_present":
                if (
                    message_current.is_deleted
                    or message_current.latest_evidence_id != fact.evidence_id
                ):
                    continue
            elif (
                not message_current.is_deleted
                or message_current.latest_evidence_id != fact.evidence_id
            ):
                # The deletion is no longer current at release time.
                continue
        if stream == AcquisitionStream.OUTLOOK_MAIL and (
            fact.fact_kind,
            fact.resource_kind,
        ) not in {
            ("resource_observation", "message"),
            ("control_context", "mail_folder"),
        }:
            continue
        if fact.storage_relation not in {"advanced", "current_equivalent"}:
            continue
        current = store.current_effective_state(writer, fact.effective_key)
        expected = (
            fact.revalidated_fact_id
            if fact.storage_relation == "current_equivalent"
            else fact.fact_id
        )
        if current is None or current["fact_id"] != expected:
            continue
        selected[fact.effective_key.digest] = fact
    entries = []
    for fact in selected.values():
        context = fact.fact_kind == "control_context"
        component = fact.fact_kind == "component_observation"
        transition = fact.fact_kind == "scoped_state_transition"
        entries.append(
            ReleaseEntrySpec(
                resource_kind=fact.resource_kind,
                resource_identity=fact.resource_identity,
                parent_resource_kind=fact.parent_resource_kind,
                parent_resource_identity=fact.parent_resource_identity,
                scope_kind=fact.scope_kind,
                scope_identity=fact.scope_identity,
                entry_kind=(
                    ReleaseEntryKind.CONTEXT
                    if context
                    else ReleaseEntryKind.COMPONENT
                    if component
                    else ReleaseEntryKind.TRANSITION
                    if transition
                    else ReleaseEntryKind.RESOURCE
                ),
                facts=(
                    (
                        fact.fact_id,
                        "context"
                        if context
                        else "component"
                        if component
                        else "transition"
                        if transition
                        else "primary",
                    ),
                ),
            )
        )
    return entries


def _release_stream(catalog, writer, source, spider, stream, group):
    store = AcquisitionHandoffStore(catalog)
    store.release_effective_group_in_session(
        writer, group, _entries(catalog, writer, source, spider, stream)
    )


def _default_group(source, spider, stream):
    subject = {
        AcquisitionStream.TODO: "todo_discovery",
        AcquisitionStream.CONTACTS: "contacts_discovery",
        AcquisitionStream.TEAMS_CHAT: "teams_chat_discovery",
        AcquisitionStream.TEAMS_CHANNEL: "teams_channel_discovery",
    }.get(stream)
    if subject is None:
        raise ValueError("Traversal release requires an explicit group")
    return ReleaseGroupSpec(
        source_id=source,
        stream=stream,
        release_kind=ReleaseKind.RESOURCE_SET,
        subject_kind=subject,
        subject_identity="source",
        owner_run_id=spider.run_id,
        released_at=datetime.now(UTC).isoformat(),
        coverage_kind="complete",
    )


def release_traversal(catalog, writer, source, spider):
    """Publish one positive-only group after durable completion proof agrees."""
    group = None
    if spider.name == "outlook_discover":
        group = mail_discovery_group(writer, source, spider)
        if group is None:
            return
    elif spider.name in {"outlook_calendar_discover", "outlook_calendar_window"}:
        group = calendar_traversal_group(writer, source, spider)
        if group is None:
            return
    elif spider.name == "microsoft_onedrive_discover":
        group = onedrive_discovery_group(writer, source, spider)
        if group is None:
            return
    elif not _complete(writer, source, spider):
        return
    stream = TRAVERSALS[spider.name]
    _release_stream(
        catalog,
        writer,
        source,
        spider,
        stream,
        group or _default_group(source, spider, stream),
    )


def release_teams_notifications(catalog, writer, source, spider):
    """Publish both Teams cursor families atomically for one reconciled delivery run."""
    for stream in (AcquisitionStream.TEAMS_CHAT, AcquisitionStream.TEAMS_CHANNEL):
        group = ReleaseGroupSpec(
            source_id=source,
            stream=stream,
            release_kind=ReleaseKind.RESOURCE_SET,
            subject_kind="teams_notification_reconcile",
            subject_identity=stream.value,
            owner_run_id=spider.run_id,
            released_at=datetime.now(UTC).isoformat(),
            coverage_kind="complete",
        )
        _release_stream(catalog, writer, source, spider, stream, group)
