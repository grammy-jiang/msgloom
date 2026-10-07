"""Exact To Do fact projection within caller-owned provider transactions."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Literal

from sqlalchemy.orm import Session

from message_ingest.acquisition.handoff import (
    AcquisitionFactKind,
    AcquisitionStream,
    FactSpec,
    SourceVersionLocator,
    StorageRelation,
    canonical_json,
)
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from message_ingest.items.microsoft.todo import (
    TodoChecklistItem,
    TodoLinkedResourceItem,
    TodoTaskItem,
    TodoTaskListItem,
)

if TYPE_CHECKING:
    from .todo import TodoItem


_TRANSPORT_FIELDS = frozenset(
    {
        "@odata.context",
        "@odata.nextLink",
        "@odata.deltaLink",
        "@microsoft.graph.downloadUrl",
    }
)


def stage_todo_fact(
    writer: Session,
    handoff: AcquisitionHandoffStore,
    *,
    source_id: str,
    spider_name: str,
    item: TodoItem,
    outcome: Literal["created", "changed", "unchanged", "stale"],
) -> None:
    """
    Bind immutable evidence and semantic hierarchy, without copying content.

    Primary task state excludes embedded child collections: explicitly fetched
    checklist/link entries own their independent component keys. Capture and
    transport metadata never changes a semantic key. Provider JSON may exceed
    the ledger's metadata budget; only its canonical digest enters the ledger.
    An unchanged pre-ledger row remains equivalent, not a fabricated advance.
    """
    if not item.run_id:
        raise ValueError("To Do handoff requires a logical run ID")
    component = None
    parent_kind = None
    parent_identity = None
    scope_kind = None
    scope_identity = None
    fact_kind = AcquisitionFactKind.RESOURCE_OBSERVATION
    if isinstance(item, TodoTaskListItem):
        kind = "todo_task_list"
        identity = canonical_json([item.list_id])
        fact_kind = AcquisitionFactKind.CONTROL_CONTEXT
    else:
        scope_kind, scope_identity = "todo_list", item.list_id
        task_identity = canonical_json([item.list_id, item.task_id])
        if isinstance(item, TodoTaskItem):
            kind, identity = "todo_task", task_identity
            parent_kind = "todo_task_list"
            parent_identity = canonical_json([item.list_id])
        else:
            fact_kind = AcquisitionFactKind.COMPONENT_OBSERVATION
            parent_kind, parent_identity = "todo_task", task_identity
            if isinstance(item, TodoChecklistItem):
                component, child_id = "checklist_item", item.checklist_item_id
            elif isinstance(item, TodoLinkedResourceItem):
                component, child_id = "linked_resource", item.linked_resource_id
            else:
                raise TypeError("Unsupported To Do handoff item")
            kind = f"todo_{component}"
            identity = canonical_json([item.list_id, item.task_id, child_id])
    excluded = _TRANSPORT_FIELDS
    if isinstance(item, TodoTaskItem):
        excluded = excluded | {"checklistItems", "linkedResources"}
    projection = {
        "identity": identity,
        "resource_kind": kind,
        "raw": {key: value for key, value in item.raw.items() if key not in excluded},
    }
    key = hashlib.sha256(
        json.dumps(
            projection,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
    ).hexdigest()
    relation = (
        StorageRelation.STALE
        if outcome == "stale"
        else StorageRelation.CURRENT_EQUIVALENT
        if outcome == "unchanged"
        else StorageRelation.ADVANCED
    )
    handoff.stage_state_fact_in_session(
        writer,
        FactSpec(
            source_id=source_id,
            stream=AcquisitionStream.TODO,
            run_id=item.run_id,
            spider_name=spider_name,
            fact_kind=fact_kind,
            resource_kind=kind,
            resource_identity=identity,
            parent_resource_kind=parent_kind,
            parent_resource_identity=parent_identity,
            scope_kind=scope_kind,
            scope_identity=scope_identity,
            component_kind=component,
            provider_observed_at=item.observed_at,
            evidence_id=item.evidence_id,
            source_state_key=key,
            storage_relation=relation,
            source_version_locator=(
                SourceVersionLocator(
                    kind="evidence",
                    evidence_id=item.evidence_id,
                    resource_identity=identity,
                    component_kind=component,
                )
                if item.evidence_id
                else None
            ),
        ),
    )
