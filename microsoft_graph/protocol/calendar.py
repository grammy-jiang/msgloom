"""Pure Calendar window and recurring-series resource validation."""

from datetime import datetime
from typing import Any

from . import graph_object


def parse_calendar_datetime(value: str) -> datetime:
    """Parse an ISO-8601 boundary with an offset or ``Z`` suffix."""
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            "Calendar window values must be valid ISO-8601 datetimes"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Calendar window datetimes must include an offset")
    return parsed


def calendar_window(start_datetime: str, end_datetime: str) -> tuple[str, str]:
    """
    Require increasing timezone-aware bounds and preserve their exact text.

    Compare instants across offsets. Do not normalize caller text: consumers
    may use it as scope identity, and paths must retain the supplied offsets.
    """
    parsed = []
    for name, raw in (
        ("start_datetime", start_datetime),
        ("end_datetime", end_datetime),
    ):
        value = raw.strip()
        if not value:
            raise ValueError(f"{name} is required")
        if raw != value:
            raise ValueError(f"{name} must not contain surrounding whitespace")
        parsed.append(parse_calendar_datetime(value))
    if parsed[0] >= parsed[1]:
        raise ValueError("start_datetime must be earlier than end_datetime")
    return start_datetime, end_datetime


def series_master_id(payload: dict[str, Any], event_id: str) -> str | None:
    """Resolve the master relation only for Graph recurring event types."""
    event_type = payload.get("type")
    if event_type == "seriesMaster":
        return event_id
    if event_type not in {"occurrence", "exception"}:
        return None
    master_id = payload.get("seriesMasterId")
    return master_id if isinstance(master_id, str) and master_id else None


def calendar_series_master(payload: Any, *, expected_id: str) -> dict[str, Any]:
    """
    Validate a master response and its optional occurrence lists.

    Missing lists are valid; explicit null and entries of the wrong type are
    rejected. Preserve the object without interpreting deletion, freshness,
    or completeness. The expected ID binds the response to its requested ID.
    """
    raw = graph_object(payload, context="Calendar series master")
    if raw.get("id") != expected_id:
        raise ValueError("Calendar series master ID changed in flight")
    cancelled = raw.get("cancelledOccurrences", [])
    exceptions = raw.get("exceptionOccurrences", [])
    if not isinstance(cancelled, list) or not all(
        isinstance(value, str) for value in cancelled
    ):
        raise TypeError("Calendar cancelledOccurrences must be a string list")
    if not isinstance(exceptions, list) or not all(
        isinstance(value, dict) for value in exceptions
    ):
        raise TypeError("Calendar exceptionOccurrences must be an object list")
    return raw
