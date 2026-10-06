"""Reject impossible provider ownership before resolving saved evidence."""

import json

from msgloom.sources.handoff_models import ReleasedFact
from msgloom.sources.models import SourceReferenceError

_KINDS = {
    "outlook_mail": {"message", "message_surface", "attachment", "mail_folder"},
    "todo": {
        "todo_task_list",
        "todo_task",
        "todo_checklist_item",
        "todo_linked_resource",
    },
    "contacts": {"contact", "contact_folder"},
    "onedrive": {"onedrive_item", "onedrive_drive", "onedrive_content"},
    "outlook_calendar": {
        "calendar",
        "calendar_event",
        "calendar_attachment",
        "calendar_series",
        "calendar_event_surface",
    },
}


def validate_fact(fact: ReleasedFact) -> None:
    """Validate hierarchy while keeping authority transition scope distinct."""
    if fact.resource_kind not in _KINDS.get(fact.stream, set()):
        raise SourceReferenceError("Unsupported resource kind for release stream")
    if fact.stream != "todo":
        return
    parts = json.loads(fact.resource_identity)
    size = {
        "todo_task_list": 1,
        "todo_task": 2,
        "todo_checklist_item": 3,
        "todo_linked_resource": 3,
    }[fact.resource_kind]
    if (
        not isinstance(parts, list)
        or len(parts) != size
        or any(not isinstance(part, str) or not part for part in parts)
    ):
        raise SourceReferenceError("Invalid To Do hierarchy")
    if fact.fact_kind == "scoped_state_transition":
        if fact.scope_kind != "todo_source" or fact.scope_identity != fact.source_id:
            raise SourceReferenceError("Invalid To Do authority scope")
    elif size > 1 and (
        fact.scope_kind != "todo_list" or fact.scope_identity != parts[0]
    ):
        raise SourceReferenceError("Invalid To Do list scope")
    if fact.parent_resource_identity is not None:
        expected = json.dumps(parts[:-1], separators=(",", ":"), ensure_ascii=False)
        kind = "todo_task" if size == 3 else "todo_task_list"
        if (
            fact.parent_resource_identity != expected
            or fact.parent_resource_kind != kind
        ):
            raise SourceReferenceError("Invalid To Do parent ownership")
