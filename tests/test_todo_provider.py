"""Pin the standalone To Do read paths and lossless provider projections."""

import subprocess
import sys
from dataclasses import fields

import pytest
from itemadapter import ItemAdapter
from scrapy.settings import Settings

from microsoft_graph.items.todo import (
    TodoChecklistItem,
    TodoLinkedResourceItem,
    TodoTaskItem,
    TodoTaskListItem,
)
from microsoft_graph.spiders.todo import MicrosoftTodoSpider

CASES = [
    (TodoTaskListItem, {}, "list_id"),
    (TodoTaskItem, {"list_id": "list"}, "task_id"),
    (
        TodoChecklistItem,
        {"list_id": "list", "task_id": "task"},
        "checklist_item_id",
    ),
    (
        TodoLinkedResourceItem,
        {"list_id": "list", "task_id": "task"},
        "linked_resource_id",
    ),
]


def test_todo_exact_paths_and_scope():
    spider = MicrosoftTodoSpider(name="provider")
    list_id, task_id = "A/B+=%2F ?é", "T/+%2f=#"
    lists = "/me/todo/lists"
    tasks = lists + "/A%2FB%2B%3D%252F%20%3F%C3%A9/tasks"
    task = tasks + "/T%2F%2B%252f%3D%23"
    cases = [
        (spider.task_lists_path(), lists),
        (spider.task_lists_path(page_size=25), lists + "?%24top=25"),
        (spider.tasks_path(list_id), tasks),
        (spider.tasks_path(list_id, page_size=25), tasks + "?%24top=25"),
        (spider.checklist_items_path(list_id, task_id), task + "/checklistItems"),
        (spider.linked_resources_path(list_id, task_id), task + "/linkedResources"),
    ]
    for actual, expected in cases:
        if actual != expected:
            pytest.fail(f"To Do path bytes changed: {actual!r} != {expected!r}")
    settings = Settings()
    spider.update_settings(settings)
    if spider.required_graph_permissions(settings) != ("Tasks.Read",):
        pytest.fail("To Do reads require Tasks.Read only")
    if settings.getlist("MS_GRAPH_SCOPES") != ["Tasks.Read"]:
        pytest.fail("To Do must not request Tasks.ReadWrite")


@pytest.mark.parametrize("provider,context,id_field", CASES)
def test_provider_defaults_retain_raw_identity_and_exclude_application_state(
    provider, context, id_field
):
    raw = {"id": "resource", "unknown": {"future": [0, False, ""]}}
    item = provider.from_graph(raw, **context)
    if item.raw is not raw or getattr(item, id_field) != "resource":
        pytest.fail("Provider object or identity was changed")
    if ItemAdapter(item).asdict()["raw"] != raw or hasattr(item, "__dict__"):
        pytest.fail("Provider items must be slotted adapter-compatible dataclasses")
    forbidden = {"observed_at", "evidence_id", "run_id", "source_id"}
    if forbidden.intersection(field.name for field in fields(provider)):
        pytest.fail("Application provenance leaked into provider defaults")
    for key, value in context.items():
        if getattr(item, key) != value:
            pytest.fail("Provider parent identity was lost")


@pytest.mark.parametrize("provider,context,id_field", CASES)
@pytest.mark.parametrize("raw", [None, [], {}, {"id": ""}, {"id": False}])
def test_provider_rejects_unstable_object_identity(provider, context, id_field, raw):
    with pytest.raises((TypeError, ValueError)):
        provider.from_graph(raw, **context)


@pytest.mark.parametrize("provider,context,id_field", CASES[1:])
def test_provider_rejects_missing_parent_identity(provider, context, id_field):
    for key in context:
        with pytest.raises(ValueError):
            provider.from_graph({"id": "resource"}, **{**context, key: ""})


@pytest.mark.parametrize("wellknown", ["defaultList", "flaggedEmails", "none"])
def test_task_list_preserves_built_in_kind_and_falsey_fields(wellknown):
    raw = {
        "id": "list",
        "displayName": "",
        "isOwner": False,
        "isShared": False,
        "wellknownListName": wellknown,
    }
    item = TodoTaskListItem.from_graph(raw)
    if (item.display_name, item.is_owner, item.is_shared, item.wellknown_list_name) != (
        "",
        False,
        False,
        wellknown,
    ):
        pytest.fail("List values were normalized")


def test_task_preserves_all_provider_fields_and_nested_identity():
    raw = {
        "id": "task",
        "title": "",
        "status": "notStarted",
        "importance": "low",
        "body": {"contentType": "html", "content": ""},
        "categories": [],
        "createdDateTime": "created",
        "lastModifiedDateTime": "modified",
        "bodyLastModifiedDateTime": "body-modified",
        "dueDateTime": {"dateTime": "2026-10-01T00:00:00", "timeZone": "UTC"},
        "startDateTime": {},
        "completedDateTime": None,
        "reminderDateTime": {},
        "isReminderOn": False,
        "recurrence": {"pattern": {}, "range": {}},
    }
    item = TodoTaskItem.from_graph(raw, list_id="list")
    mapping = {
        "title": "title",
        "status": "status",
        "importance": "importance",
        "body": "body",
        "categories": "categories",
        "created_date_time": "createdDateTime",
        "last_modified_date_time": "lastModifiedDateTime",
        "body_last_modified_date_time": "bodyLastModifiedDateTime",
        "due_date_time": "dueDateTime",
        "start_date_time": "startDateTime",
        "completed_date_time": "completedDateTime",
        "reminder_date_time": "reminderDateTime",
        "is_reminder_on": "isReminderOn",
        "recurrence": "recurrence",
    }
    for name, key in mapping.items():
        if getattr(item, name) is not raw[key]:
            pytest.fail(f"Provider field {key} was transformed or copied")


def test_checklist_and_linked_resource_falsey_optional_fields():
    checklist = TodoChecklistItem.from_graph(
        {
            "id": "check",
            "displayName": "",
            "isChecked": False,
            "createdDateTime": "created",
            "checkedDateTime": "",
        },
        list_id="list",
        task_id="task",
    )
    if (
        checklist.display_name,
        checklist.is_checked,
        checklist.created_date_time,
        checklist.checked_date_time,
    ) != ("", False, "created", ""):
        pytest.fail("Checklist projection lost provider values")
    resource = TodoLinkedResourceItem.from_graph(
        {"id": "link", "applicationName": "", "displayName": "", "externalId": ""},
        list_id="list",
        task_id="task",
    )
    if (
        resource.web_url,
        resource.application_name,
        resource.display_name,
        resource.external_id,
    ) != (None, "", "", ""):
        pytest.fail("Missing webUrl must remain valid; empty strings must survive")


def test_todo_works_with_consumer_and_sqlalchemy_forbidden():
    code = """
import importlib.abc
import sys
class ForbidConsumer(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"message_ingest", "sqlalchemy"}:
            raise ImportError(f"Forbidden dependency: {fullname}")
sys.meta_path.insert(0, ForbidConsumer())
from microsoft_graph.spiders.todo import MicrosoftTodoSpider
from microsoft_graph.items.todo import (
    TodoTaskListItem, TodoTaskItem, TodoChecklistItem, TodoLinkedResourceItem,
)
spider = MicrosoftTodoSpider(name="standalone")
spider.graph_request(spider.task_lists_path())
TodoTaskListItem.from_graph({"id": "list"})
TodoTaskItem.from_graph({"id": "task"}, list_id="list")
TodoChecklistItem.from_graph({"id": "check"}, list_id="list", task_id="task")
TodoLinkedResourceItem.from_graph({"id": "link"}, list_id="list", task_id="task")
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if result.returncode:
        pytest.fail(result.stderr)
