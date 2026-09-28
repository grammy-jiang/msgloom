"""Shared request metadata and Graph transport host selection."""

from urllib.parse import urlsplit

from microsoft_graph import GRAPH_ROOT

GRAPH_OPERATION_META_KEY = "microsoft_graph_operation"


def graph_operation(request) -> str:
    """Read neutral operation metadata with legacy callback-purpose fallback."""
    value = request.meta.get(
        GRAPH_OPERATION_META_KEY, request.cb_kwargs.get("purpose", "unknown")
    )
    return str(value) if value else "unknown"


def graph_host(crawler) -> str:
    """Use the crawler's configured service root or its spider's Graph root."""
    root = crawler.settings.get("MS_GRAPH_SERVICE_ROOT") or getattr(
        crawler.spider, "graph_root", GRAPH_ROOT
    )
    host = urlsplit(root).hostname
    if not host:
        raise ValueError("Graph service root must have a hostname")
    return host
