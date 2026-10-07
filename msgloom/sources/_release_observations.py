"""Resolve immutable observation and content-capture associations only."""

import json
import sqlite3
from contextlib import closing
from typing import Any

from msgloom.sources._catalog import ReadOnlyCatalog
from msgloom.sources.handoff_models import ReleasedFact
from msgloom.sources.models import SourceReferenceError


def row(catalog: ReadOnlyCatalog, sql: str, values: tuple) -> dict[str, Any]:
    """Execute a single bounded immutable-association lookup."""
    with closing(catalog._connect()) as connection:
        connection.setlimit(
            sqlite3.SQLITE_LIMIT_LENGTH, catalog.limits.max_evidence_bytes
        )
        found = connection.execute(sql + " LIMIT 1", values).fetchone()
    if found is None:
        raise SourceReferenceError("Exact immutable association is unavailable")
    return dict(found)


def observation(catalog: ReadOnlyCatalog, fact: ReleasedFact) -> dict[str, Any]:
    """Validate exact source, resource, and evidence scope."""
    locator = fact.source_version_locator
    if locator is None:
        raise SourceReferenceError("Missing observation locator")
    identity = locator.observation_id
    if fact.stream == "outlook_mail":
        return row(
            catalog,
            "SELECT * FROM message_observations WHERE observation_id=? "
            "AND source_id=? AND message_id=? AND evidence_id=?",
            (identity, fact.source_id, fact.resource_identity, fact.evidence_id),
        )
    if fact.stream == "outlook_calendar":
        delta = fact.scope_kind == "calendar_window"
        table = (
            "calendar_delta_observations" if delta else "calendar_event_observations"
        )
        found = row(
            catalog,
            f"SELECT * FROM {table} WHERE observation_id=? AND source_id=? "
            "AND event_id=? AND evidence_id=?",
            (identity, fact.source_id, fact.resource_identity, fact.evidence_id),
        )
        if delta:
            scope = json.loads(fact.scope_identity or "null")
            if scope != [
                found["calendar_scope"],
                found["start_datetime"],
                found["end_datetime"],
            ]:
                raise SourceReferenceError("Calendar observation scope mismatch")
        return found
    if fact.stream == "contacts":
        parts = json.loads(identity or "null")
        if (
            not isinstance(parts, list)
            or len(parts) != 4
            or parts[0] != fact.source_id
            or parts[1] != fact.scope_identity
            or not isinstance(parts[2], str)
            or type(parts[3]) is not int
            or not 0 <= parts[3] < 2**63
            or not str(parts[1]).startswith("folder:")
        ):
            raise SourceReferenceError("Invalid Contacts observation locator")
        return row(
            catalog,
            "SELECT * FROM contact_delta_observations WHERE source_id=? "
            "AND folder_id=? AND run_id=? AND ordinal=? AND contact_id=? "
            "AND evidence_id=?",
            (
                fact.source_id,
                parts[1][7:],
                parts[2],
                parts[3],
                fact.resource_identity,
                fact.evidence_id,
            ),
        )
    if fact.stream == "onedrive":
        if (
            not identity
            or not identity.isascii()
            or not identity.isdecimal()
            or len(identity) > 19
            or int(identity) >= 2**63
        ):
            raise SourceReferenceError("Invalid OneDrive observation locator")
        return row(
            catalog,
            "SELECT * FROM onedrive_delta_resync_observations "
            "WHERE observation_id=? AND source_id=? AND item_id=? AND evidence_id=?",
            (int(identity), fact.source_id, fact.resource_identity, fact.evidence_id),
        )
    raise SourceReferenceError("Unsupported immutable observation family")


def content_capture(catalog: ReadOnlyCatalog, fact: ReleasedFact) -> dict[str, Any]:
    """Resolve one named OneDrive capture, never search for latest content."""
    locator = fact.source_version_locator
    if locator is None or locator.capture_id != fact.evidence_id:
        raise SourceReferenceError("Content capture identity mismatch")
    found = row(
        catalog,
        "SELECT * FROM onedrive_content_captures WHERE source_id=? "
        "AND evidence_id=? AND item_id=?",
        (fact.source_id, locator.capture_id, fact.resource_identity),
    )
    if (
        not found["planned_metadata_evidence_id"]
        or not found["planned_e_tag"]
        or found["planned_e_tag"] != found["response_e_tag"]
        or locator.resource_version != found["planned_e_tag"]
    ):
        raise SourceReferenceError("Content capture lacks exact metadata binding")
    return found
