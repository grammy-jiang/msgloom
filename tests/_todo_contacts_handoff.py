"""Local catalog fixtures and explicit Task 4 ledger publication probes."""

from collections.abc import Sequence
from dataclasses import replace

import pytest
from sqlalchemy import select

from message_ingest.acquisition.handoff import (
    AcquisitionFactKind,
    AcquisitionStream,
    FactSpec,
    ReleaseEntryKind,
    ReleaseEntrySpec,
    ReleaseGroupSpec,
    ReleaseKind,
)
from message_ingest.catalog import Catalog
from message_ingest.catalog.models.handoff import AcquisitionFact
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore


def facts(catalog: Catalog, run: str) -> list[FactSpec]:
    """Require real staged facts, avoiding vacuous release assertions."""
    with catalog.Session() as session:
        rows = session.scalars(
            select(AcquisitionFact.payload).where(AcquisitionFact.run_id == run)
        ).all()
    if not rows:
        pytest.fail(f"No acquisition facts staged for {run}")
    return [FactSpec.from_json(row) for row in rows]


def publish(
    catalog: Catalog, run: str, stream: AcquisitionStream, rows: Sequence[FactSpec]
) -> list[dict]:
    """
    Exercise Task 1 freshness/recovery with real provider facts.

    Task 8/9 own automatic completion/authority publication. This probe uses
    their accepted ledger seam explicitly, never implements their lifecycle.
    """
    store = AcquisitionHandoffStore(catalog)
    entries = []
    for row in sorted(
        rows,
        key=lambda fact: fact.fact_kind == AcquisitionFactKind.COMPONENT_OBSERVATION,
    ):
        component = row.fact_kind == AcquisitionFactKind.COMPONENT_OBSERVATION
        context = row.fact_kind == AcquisitionFactKind.CONTROL_CONTEXT
        kind = row.parent_resource_kind if component else row.resource_kind
        identity = row.parent_resource_identity if component else row.resource_identity
        if kind is None or identity is None:
            pytest.fail("Component fact lost its semantic parent")
        entries.append(
            ReleaseEntrySpec(
                resource_kind=kind,
                resource_identity=identity,
                parent_resource_kind=None if component else row.parent_resource_kind,
                parent_resource_identity=None
                if component
                else row.parent_resource_identity,
                scope_kind=row.scope_kind,
                scope_identity=row.scope_identity,
                entry_kind=(
                    ReleaseEntryKind.CONTEXT if context else ReleaseEntryKind.RESOURCE
                ),
                facts=(
                    (
                        row.fact_id,
                        "component"
                        if component
                        else "context"
                        if context
                        else "primary",
                    ),
                ),
            )
        )
    # Child components of one task share a bounded parent impact.
    merged: dict[tuple, ReleaseEntrySpec] = {}

    for entry in entries:
        key = (entry.resource_kind, entry.resource_identity, entry.scope_identity)
        prior = merged.get(key)
        merged[key] = (
            entry if prior is None else replace(prior, facts=prior.facts + entry.facts)
        )
    group = ReleaseGroupSpec(
        source_id="source",
        stream=stream,
        release_kind=ReleaseKind.RESOURCE_SET,
        subject_kind="fixture",
        subject_identity=run,
        owner_run_id=run,
        released_at="2026-10-04T00:00:00Z",
        coverage_kind="complete",
    )
    with catalog.writer_session() as session:
        store.release_effective_group_in_session(session, group, list(merged.values()))
    return store.list_release_entries("source", stream)


def reject_facts(catalog: Catalog) -> None:
    """Inject a real SQLite fact insertion failure without replacing stores."""
    with catalog.writer_session() as session:
        session.connection().exec_driver_sql(
            "CREATE TEMP TRIGGER reject_task4_fact BEFORE INSERT ON acquisition_facts "
            "BEGIN SELECT RAISE(ABORT, 'injected fact failure'); END"
        )
