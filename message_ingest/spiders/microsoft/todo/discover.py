"""Discover To Do lists, tasks, checklist state, and linked evidence."""

from collections.abc import AsyncIterator, Iterator
from typing import Any, ClassVar

from scrapy.http import TextResponse
from scrapy.settings import BaseSettings

from message_ingest.items.microsoft.todo import (
    TodoChecklistItem,
    TodoLinkedResourceItem,
    TodoTaskItem,
    TodoTaskListItem,
    TodoTraversalCompleteItem,
)
from message_ingest.spiders.microsoft._graph import MicrosoftGraphSpider
from microsoft_graph.protocol import GraphCollectionPage
from microsoft_graph.spiders.todo import MicrosoftTodoSpider


class MicrosoftTodoDiscoverSpider(MicrosoftTodoSpider, MicrosoftGraphSpider):
    """
    Acquire read-only task state through the shared Graph evidence contract.

    Each callback emits evidence before parsing semantic items. Explicit
    relation collections supply relation records, even when tasks embed links.
    Missing resources never imply removal. JOBDIR is refused until application
    resume behavior is validated; named callbacks still use native requests.
    """

    name = "microsoft_todo_discover"
    failure_context_keys: ClassVar[tuple[str, ...]] = ("list_id", "task_id")
    authoritative_snapshot: ClassVar[bool] = False

    def __init__(self, *args, page_size: str = "100", **kwargs) -> None:
        """Validate collection page size before scheduling any requests."""
        super().__init__(*args, **kwargs)
        self.page_size = self._bounded_int(
            page_size, name="page_size", minimum=1, maximum=1000
        )

    @classmethod
    def update_settings(cls, settings: BaseSettings) -> None:
        """Select To Do source and storage; preserve cmdline priority."""
        settings.set(
            "MSGLOOM_SOURCE_ID",
            settings.get("MSGLOOM_TODO_SOURCE_ID", "microsoft-todo-default"),
            priority="spider",
        )
        for key in (
            "MSGLOOM_DELTA_CHECKPOINT_ENABLED",
            "MSGLOOM_FOLDER_DELTA_CHECKPOINT_ENABLED",
            "MSGLOOM_CALENDAR_DELTA_CHECKPOINT_ENABLED",
            "MSGLOOM_CRAWL_STATUS_ENABLED",
        ):
            settings.set(key, False, priority="spider")
        settings.set(
            "ITEM_PIPELINES",
            {
                "message_ingest.pipelines.evidence.RawEvidencePipeline": 200,
                "message_ingest.acquisition.evidence_link.EvidenceLinkPipeline": 250,
                "message_ingest.pipelines.microsoft.todo.TodoPipeline": 300,
            },
            priority="spider",
        )
        super().update_settings(settings)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """Fail closed on unvalidated persistent-scheduler resume."""
        if crawler.settings.get("JOBDIR"):
            raise ValueError("To Do discovery does not support JOBDIR yet")
        return super().from_crawler(crawler, *args, **kwargs)

    def _todo_request(self, url: str, **kwargs):
        """Use uncached Graph reads only for authoritative snapshot traversal."""
        return self._request(url, dont_cache=self.authoritative_snapshot, **kwargs)

    def _completion_item(
        self,
        collection_kind: str,
        evidence,
        *,
        list_id: str | None = None,
        task_id: str | None = None,
    ) -> TodoTraversalCompleteItem | None:
        """Build terminal traversal proof only for authoritative sync runs."""
        if not self.authoritative_snapshot:
            return None
        return TodoTraversalCompleteItem(
            collection_kind=collection_kind,
            list_id=list_id,
            task_id=task_id,
            observed_at=evidence.observed_at,
            evidence_id=evidence.evidence_id,
            run_id=self.run_id,
        )

    async def start(self) -> AsyncIterator[Any]:
        """Schedule task-list inventory for the signed-in account."""
        yield self._todo_request(
            self.task_lists_path(page_size=self.page_size),
            callback=self.parse_task_lists,
            purpose="todo-task-lists-page",
            cb_kwargs={},
        )

    def parse_task_lists(
        self, response: TextResponse, *, purpose: str
    ) -> Iterator[Any]:
        """Emit list observations and schedule tasks for every list kind."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        page = GraphCollectionPage.from_payload(
            response.json(), context="To Do task lists", validate_links=False
        )
        self.crawler.stats.inc_value("msgloom/crawl/todo/task_list_page_count")
        for raw in page.values:
            item = TodoTaskListItem.from_graph(
                raw,
                observed_at=evidence.observed_at,
                evidence_id=evidence.evidence_id,
                run_id=self.run_id,
            )
            self.crawler.stats.inc_value("msgloom/crawl/todo/task_list_count")
            yield item
            yield self._todo_request(
                self.tasks_path(item.list_id, page_size=self.page_size),
                callback=self.parse_tasks,
                purpose="todo-tasks-page",
                cb_kwargs={"list_id": item.list_id},
            )
        if next_link := page.next_link:
            yield self._todo_request(
                next_link,
                callback=self.parse_task_lists,
                purpose=purpose,
                cb_kwargs={},
                verbatim_url=True,
            )
        elif completion := self._completion_item("task_lists", evidence):
            yield completion

    def parse_tasks(
        self, response: TextResponse, *, purpose: str, list_id: str
    ) -> Iterator[Any]:
        """Emit tasks, then request both authoritative relation collections."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        page = GraphCollectionPage.from_payload(
            response.json(), context="To Do tasks", validate_links=False
        )
        self.crawler.stats.inc_value("msgloom/crawl/todo/task_page_count")
        for raw in page.values:
            item = TodoTaskItem.from_graph(
                raw,
                list_id=list_id,
                observed_at=evidence.observed_at,
                evidence_id=evidence.evidence_id,
                run_id=self.run_id,
            )
            self.crawler.stats.inc_value("msgloom/crawl/todo/task_count")
            yield item
            context = {"list_id": list_id, "task_id": item.task_id}
            yield self._todo_request(
                self.checklist_items_path(list_id, item.task_id),
                callback=self.parse_checklist_items,
                purpose="todo-checklist-items-page",
                cb_kwargs=context,
            )
            yield self._todo_request(
                self.linked_resources_path(list_id, item.task_id),
                callback=self.parse_linked_resources,
                purpose="todo-linked-resources-page",
                cb_kwargs=context,
            )
        if next_link := page.next_link:
            yield self._todo_request(
                next_link,
                callback=self.parse_tasks,
                purpose=purpose,
                cb_kwargs={"list_id": list_id},
                verbatim_url=True,
            )
        elif completion := self._completion_item("tasks", evidence, list_id=list_id):
            yield completion

    def parse_checklist_items(
        self, response: TextResponse, *, purpose: str, list_id: str, task_id: str
    ) -> Iterator[Any]:
        """Emit checklist state after evidence and follow opaque links."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        page = GraphCollectionPage.from_payload(
            response.json(), context="To Do checklist items", validate_links=False
        )
        self.crawler.stats.inc_value("msgloom/crawl/todo/checklist_item_page_count")
        for raw in page.values:
            item = TodoChecklistItem.from_graph(
                raw,
                list_id=list_id,
                task_id=task_id,
                observed_at=evidence.observed_at,
                evidence_id=evidence.evidence_id,
                run_id=self.run_id,
            )
            self.crawler.stats.inc_value("msgloom/crawl/todo/checklist_item_count")
            yield item
        if next_link := page.next_link:
            yield self._todo_request(
                next_link,
                callback=self.parse_checklist_items,
                purpose=purpose,
                cb_kwargs={"list_id": list_id, "task_id": task_id},
                verbatim_url=True,
            )
        elif completion := self._completion_item(
            "checklist_items", evidence, list_id=list_id, task_id=task_id
        ):
            yield completion

    def parse_linked_resources(
        self, response: TextResponse, *, purpose: str, list_id: str, task_id: str
    ) -> Iterator[Any]:
        """Emit explicit evidence links, including entries without URLs."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        page = GraphCollectionPage.from_payload(
            response.json(), context="To Do linked resources", validate_links=False
        )
        self.crawler.stats.inc_value("msgloom/crawl/todo/linked_resource_page_count")
        for raw in page.values:
            item = TodoLinkedResourceItem.from_graph(
                raw,
                list_id=list_id,
                task_id=task_id,
                observed_at=evidence.observed_at,
                evidence_id=evidence.evidence_id,
                run_id=self.run_id,
            )
            self.crawler.stats.inc_value("msgloom/crawl/todo/linked_resource_count")
            yield item
        if next_link := page.next_link:
            yield self._todo_request(
                next_link,
                callback=self.parse_linked_resources,
                purpose=purpose,
                cb_kwargs={"list_id": list_id, "task_id": task_id},
                verbatim_url=True,
            )
        elif completion := self._completion_item(
            "linked_resources", evidence, list_id=list_id, task_id=task_id
        ):
            yield completion
