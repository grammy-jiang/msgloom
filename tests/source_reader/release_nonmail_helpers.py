"""Synthetic immutable releases using the accepted A1 ledger writer."""

import importlib
from dataclasses import replace

import pytest

from message_ingest.acquisition.handoff import (
    AcquisitionFactKind,
    AcquisitionStream,
    FactSpec,
    ReleaseEntryKind,
    ReleaseEntrySpec,
    ReleaseGroupSpec,
    ReleaseKind,
    SourceVersionLocator,
    source_state_key,
)
from message_ingest.catalog import Catalog
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from msgloom.sources import SavedSourceReaderConfig

SOURCE = "synthetic-source"
WHEN = "2026-09-29T00:00:00+00:00"


def reader_api(saved, **limits):
    """Demand the actual public implementation without import-error RED."""
    module = importlib.import_module("msgloom.sources")
    if not hasattr(module, "ReleaseSourceReader"):
        pytest.fail("Task12 ReleaseSourceReader is missing")
    from msgloom.sources import SourceReaderLimits

    return module.ReleaseSourceReader(
        SavedSourceReaderConfig(
            catalog_path=saved["database"],
            evidence_roots=(saved["evidence_root"],),
            limits=SourceReaderLimits(**limits),
        )
    )


def fact(stream, kind, identity, evidence, **kwargs):
    """Build an exact fixture fact with explicit immutable ownership."""
    component = kwargs.get("component_kind")
    return FactSpec(
        source_id=SOURCE,
        stream=AcquisitionStream(stream),
        run_id="current-acquisition-run",
        spider_name="synthetic-release",
        fact_kind=AcquisitionFactKind.RESOURCE_OBSERVATION,
        resource_kind=kind,
        resource_identity=identity,
        provider_observed_at=WHEN,
        evidence_id=evidence,
        source_state_key=source_state_key({"identity": identity}),
        source_version_locator=SourceVersionLocator(
            kind="evidence",
            evidence_id=evidence,
            resource_identity=identity,
            component_kind=component,
        ),
        **kwargs,
    )


def publish(
    saved, facts, *, roles=None, entry_kind="resource", scope=None, authority=False
):
    """Commit a bounded exact entry; never mutate a prior release."""
    catalog = Catalog(f"sqlite:///{saved['database']}")
    ledger = AcquisitionHandoffStore(catalog)
    first = facts[0]
    roles = roles or ("primary",) * len(facts)
    try:
        with catalog.writer_session() as session:
            staged = [
                (
                    ledger.stage_authority_fact_in_session(session, item)
                    if authority
                    else ledger.stage_state_fact_in_session(session, item)
                )
                for item in facts
            ]
            entry = ReleaseEntrySpec(
                resource_kind=first.resource_kind,
                resource_identity=first.resource_identity,
                parent_resource_kind=first.parent_resource_kind,
                parent_resource_identity=first.parent_resource_identity,
                scope_kind=first.scope_kind,
                scope_identity=first.scope_identity,
                entry_kind=ReleaseEntryKind(entry_kind),
                facts=tuple(
                    (item.fact_id, role)
                    for item, role in zip(staged, roles, strict=True)
                ),
            )
            if scope:
                entry = replace(entry, **scope)
            release = (
                ledger.release_authority_group_in_session
                if authority
                else ledger.release_effective_group_in_session
            )
            release(
                session,
                ReleaseGroupSpec(
                    source_id=SOURCE,
                    stream=first.stream,
                    release_kind=(
                        ReleaseKind.AUTHORITY_SCOPE
                        if authority
                        else ReleaseKind.RESOURCE_SET
                    ),
                    subject_kind="fixture",
                    subject_identity=staged[0].fact_id,
                    owner_run_id=first.run_id,
                    released_at=WHEN,
                    coverage_kind="complete",
                ),
                (entry,),
                **(
                    {"winning_fact_ids": [f.fact_id for f in staged]}
                    if authority
                    else {}
                ),
            )
        return ledger.list_release_entries(
            source_id=SOURCE, stream=first.stream, after_seq=0, limit=100
        )[-1]["release_entry_seq"]
    finally:
        catalog.close()


def save_evidence(saved, evidence_id, body, purpose="synthetic"):
    """Persist local Graph bytes through the existing authentic test helper."""
    from tests.source_reader.conftest import _evidence

    catalog = Catalog(f"sqlite:///{saved['database']}")
    try:
        with catalog.writer_session() as session:
            _evidence(
                session,
                saved["evidence_root"],
                evidence_id,
                body,
                purpose=purpose,
                observed_at=WHEN,
            )
    finally:
        catalog.close()
