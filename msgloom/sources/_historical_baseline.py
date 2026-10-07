"""Resolve approved baseline versions without manufacturing release entries."""

import json
import sqlite3
from contextlib import closing

from msgloom.contracts import VersionRef
from msgloom.sources._catalog import _unpack
from msgloom.sources._release_evidence import ReleaseEvidence, digest, fact_reference
from msgloom.sources._release_records import record
from msgloom.sources._release_validation import validate_fact
from msgloom.sources._snapshot import capture_selection, encode_selection
from msgloom.sources.handoff_catalog import _Snapshot
from msgloom.sources.handoff_models import (
    FactPayload,
    ReleasedFact,
    SourceVersionLocator,
)
from msgloom.sources.models import CollectedSelection, SourceReferenceError


def selection(source: VersionRef, evidence: ReleaseEvidence) -> CollectedSelection:
    """
    Freeze one approved primary representation through existing evidence checks.

    Calendar references use source/event identity and immutable observation ID.
    Release-aware references resolve immutable facts, including unreleased and
    historical facts. Neither path discovers current projections or creates a
    release. The source version fixes one representation. This path never expands
    it using mutable full-profile projections.
    """
    fact = (
        _calendar_observation(source, evidence)
        if source.kind == "outlook_calendar"
        else _exact_fact(source, evidence)
    )
    validate_fact(fact)
    raw, saved = evidence.object(fact)
    if "@removed" in raw:
        raise SourceReferenceError("Baseline observation is a removal")
    value = record(fact, raw, saved, evidence.catalog.source_scope(fact.source_id))
    value = value.model_copy(
        update={"source": source, "semantic_identity": source.identity}
    )
    result = capture_selection(value)
    encode_selection(result, evidence.catalog.limits.max_snapshot_bytes)
    return result


def _calendar_observation(
    source: VersionRef, evidence: ReleaseEvidence
) -> ReleasedFact:
    """
    Adapt one saved association for the shared object mapper, without A1 writes.

    The temporary fact-shaped value is only an in-memory mapping input. It does
    not assert ledger membership or completion and is never saved as a release.
    Both full and window observations retain their exact evidence association.
    """
    source_id, event_id = _unpack(source.identity, 2)
    found = []
    with closing(evidence.catalog._connect()) as connection:
        connection.setlimit(
            sqlite3.SQLITE_LIMIT_LENGTH, evidence.catalog.limits.max_evidence_bytes
        )
        for table in ("calendar_event_observations", "calendar_delta_observations"):
            rows = connection.execute(
                f"SELECT * FROM {table} WHERE observation_id=? "
                "AND source_id=? AND event_id=? LIMIT 2",
                (source.version, source_id, event_id),
            ).fetchall()
            found.extend(dict(row) for row in rows)
    if len(found) != 1 or not found[0]["evidence_id"]:
        raise SourceReferenceError("Exact Calendar observation is unavailable")
    row = found[0]
    if row.get("kind") in {"removed", "deleted"}:
        raise SourceReferenceError("Baseline observation is a removal")
    scope_kind = None
    scope_identity = None
    if "calendar_scope" in row:
        scope_kind = "calendar_window"
        scope_identity = json.dumps(
            [row["calendar_scope"], row["start_datetime"], row["end_datetime"]],
            separators=(",", ":"),
        )
    return ReleasedFact(
        source_id=source_id,
        stream="outlook_calendar",
        run_id=row["run_id"] or "historical-observation",
        spider_name="historical-baseline",
        fact_kind="resource_observation",
        resource_kind="calendar_event",
        resource_identity=event_id,
        provider_observed_at=row["observed_at"],
        evidence_id=row["evidence_id"],
        source_version_locator=SourceVersionLocator(
            kind="observation",
            observation_id=source.version,
            evidence_id=row["evidence_id"],
            resource_identity=event_id,
        ),
        storage_relation="advanced",
        fact_id=digest([source.kind, source.identity, source.version]),
        role="primary",
        ordinal=0,
        scope_kind=scope_kind,
        scope_identity=scope_identity,
    )


def _exact_fact(source: VersionRef, evidence: ReleaseEvidence) -> ReleasedFact:
    """Resolve a bounded immutable fact inventory; never consult freshness."""
    source_id, stream, resource_kind, resource_identity, *_ = _unpack(
        source.identity, 8
    )
    catalog = evidence.catalog
    with closing(catalog._connect()) as connection:
        connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 256 * 1024)
        snapshot = _Snapshot(connection, catalog.limits)
        rows = connection.execute(
            "SELECT fact_id, source_id, stream, run_id, source_state_key, "
            "storage_relation, payload FROM acquisition_facts "
            "WHERE source_id=? AND stream=? "
            "AND json_extract(payload, '$.resource_kind')=? "
            "AND json_extract(payload, '$.resource_identity')=? "
            "ORDER BY rowid LIMIT ?",
            (
                source_id,
                stream,
                resource_kind,
                resource_identity,
                catalog.limits.max_query_rows + 1,
            ),
        ).fetchall()
        if len(rows) > catalog.limits.max_query_rows:
            raise SourceReferenceError("Baseline fact inventory exceeds query bound")
        for row in rows:
            value = snapshot.payload(row["payload"], FactPayload)
            material = value.model_dump(mode="json")
            if material["revalidated_fact_id"] is None:
                material.pop("revalidated_fact_id")
            if digest(material) != row["fact_id"] or any(
                row[key] != getattr(value, key)
                for key in (
                    "source_id",
                    "stream",
                    "run_id",
                    "source_state_key",
                    "storage_relation",
                )
            ):
                raise SourceReferenceError("Baseline immutable fact mismatch")
            if value.fact_kind not in {"resource_observation", "control_context"}:
                continue
            fact = ReleasedFact(
                **value.model_dump(), fact_id=row["fact_id"], role="primary", ordinal=0
            )
            if fact_reference(fact) == source:
                return fact
    raise SourceReferenceError("Exact baseline fact is unavailable")
