"""Namespace transport counters without binding them to an application."""


def stats_prefix(settings, *, default: str = "microsoft_graph") -> str:
    """Return the configured namespace plus its optional path separator."""
    prefix = settings.get("MS_GRAPH_STATS_PREFIX", default)
    if not isinstance(prefix, str):
        raise TypeError("MS_GRAPH_STATS_PREFIX must be a string")
    return prefix.rstrip("/") + "/" if prefix else ""
