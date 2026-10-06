"""Validate durable additive traversal proof inside the release transaction."""

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
from message_ingest.catalog.models.microsoft.todo import (
    TodoTaskListSighting,
    TodoTaskSighting,
    TodoTraversalCompletion,
)
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
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
}


def _rows(writer, model, source, run):
    return writer.scalars(select(model).filter_by(source_id=source, run_id=run)).all()


def _complete(writer, source, spider):
    """
    Require current-run completion linked to valid canonical source evidence.

    Cache replay can reuse an older capture. Completion rows own the logical
    run; their exact evidence references retain the original capture run.
    """
    run = spider.run_id
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


def release_traversal(catalog, writer, source, spider):
    """
    Publish one positive-only group after all durable child proofs agree.

    Completion rows remain provider control state. They do not become A2
    entries, presence changes, snapshot candidates, or authority revisions.
    Entry selection and freshness revalidation share the caller's writer.
    """
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
        # One direct impact per effective resource/component scope. The parent
        # stays explicit for A2 task refresh routing without unbounded entries.
        selected[fact.effective_key.digest] = fact
    entries = []
    for fact in selected.values():
        context = fact.fact_kind == "control_context"
        component = fact.fact_kind == "component_observation"
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
                    else ReleaseEntryKind.RESOURCE
                ),
                facts=(
                    (
                        fact.fact_id,
                        "context"
                        if context
                        else "component"
                        if component
                        else "primary",
                    ),
                ),
            )
        )
    group = group or ReleaseGroupSpec(
        source_id=source,
        stream=stream,
        release_kind=ReleaseKind.RESOURCE_SET,
        subject_kind="todo_discovery"
        if stream == AcquisitionStream.TODO
        else "contacts_discovery",
        subject_identity="source",
        owner_run_id=spider.run_id,
        released_at=datetime.now(UTC).isoformat(),
        coverage_kind="complete",
    )
    store.release_effective_group_in_session(writer, group, entries)
