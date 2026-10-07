"""Synthetic item-pipeline failures for real To Do sync crawl tests."""

from scrapy.exceptions import DropItem
from scrapy.spidermiddlewares.base import BaseSpiderMiddleware

from message_ingest.items.microsoft.todo import TodoTaskItem


class DropTodoTaskPipeline:
    """Drop one task after durable To Do persistence has run."""

    def process_item(self, item):
        if isinstance(item, TodoTaskItem):
            raise DropItem("synthetic To Do task drop")
        return item


class SyntheticPipelineFailure(Exception):
    """Synthetic non-DropItem pipeline failure."""


class FailTodoTaskPipeline:
    """Raise one task error after durable To Do persistence has run."""

    def process_item(self, item):
        if isinstance(item, TodoTaskItem):
            raise SyntheticPipelineFailure("synthetic To Do task pipeline failure")
        return item


class DropChecklistContinuationMiddleware(BaseSpiderMiddleware):
    """Silently remove checklist continuation requests to simulate lost paging."""

    def get_processed_request(self, request, response):
        if response is None or response.request is None:
            return request
        parent = getattr(response.request.callback, "__name__", "")
        child = getattr(request.callback, "__name__", "")
        if parent == "parse_checklist_items" and child == "parse_checklist_items":
            return None
        return request
