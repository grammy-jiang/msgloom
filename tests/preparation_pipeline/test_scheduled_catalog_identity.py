"""Exercise real scheduled/intake/store logic with a memory-only A1 seam."""

import asyncio
from types import SimpleNamespace
from typing import cast
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool

from msgloom.configuration import PreparationOperationData
from msgloom.configuration.models import PreparationIntakeTarget
from msgloom.contracts import (
    AttemptIdentity,
    ExecutionIdentity,
    OperationRequest,
    PhaseCapability,
    ResultSchemaRegistry,
)
from msgloom.persistence import Phase1Persistence, SemanticDataRegistry
from msgloom.persistence.intake_records import scope_values
from msgloom.persistence.records import INTAKE_CURSORS
from msgloom.persistence.schema_store import initialize_schema
from msgloom.persistence.store import Phase1Store
from msgloom.preparation_pipeline.intake_models import IntakeScope
from msgloom.preparation_pipeline.scheduled import ScheduledPreparationHandler
from msgloom.sources import SavedSourceReaderConfig
from msgloom.sources.handoff_models import A1CatalogIdentity
from tests.preparation_pipeline.helpers import filter_config


class MemoryCatalog:
    def __init__(self, identity, anchor_ok):
        self.identity = A1CatalogIdentity(catalog_identity=identity, schema_version=1)
        self.anchor_ok = anchor_ok
        self.queries = []

    async def catalog_identity(self):
        self.queries.append("catalog_identity")
        return self.identity

    async def get_release_entry(self, seq):
        self.queries.append("anchor:" + str(seq))
        if not self.anchor_ok:
            return None
        return SimpleNamespace(
            catalog=self.identity,
            source_id="source",
            stream="todo",
            entry_digest="a" * 64,
        )

    async def max_release_entry_seq(self, source, stream):
        self.queries.append("ceiling")
        return 9 if self.anchor_ok else 0

    async def list_release_entries(self, *args, **kwargs):
        self.queries.append("page:" + str(kwargs["after_seq"]))
        return SimpleNamespace(entries=())


class MemoryReader:
    def __init__(self, catalog):
        self.catalog = catalog
        self.closed = False

    async def close(self):
        self.closed = True


async def scenario(
    name,
    *,
    seed,
    catalog_identity,
    anchor_ok,
    expected="old",
    consumer="consumer",
    stream="todo",
    source="source",
):
    # Provision the unchanged real store owner in memory. Bypass only its
    # filesystem-opening constructor; no store, claim, cursor, or handler
    # method is patched. The A1 read boundary is the sole behavioral seam.
    store = Phase1Store.__new__(Phase1Store)
    store.registry = ResultSchemaRegistry.phase1()
    store.semantic_registry = SemanticDataRegistry.phase1()
    store.engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"autocommit": True, "check_same_thread": False},
    )
    initialize_schema(store.engine)
    if seed:
        scope = IntakeScope(
            catalog=A1CatalogIdentity(catalog_identity="old", schema_version=1),
            source_id="source",
            stream="todo",
            consumer_id="consumer",
        )
        with store.engine.connect() as connection:
            connection.execute(
                INTAKE_CURSORS.insert().values(
                    **scope_values(scope),
                    last_release_entry_seq=9,
                    last_release_entry_digest="a" * 64,
                )
            )
    persistence = Phase1Persistence(store)
    # Isolate the runtime guard from configuration validation, tested separately.
    target = PreparationIntakeTarget.model_construct(
        source_id=source,
        stream=stream,
        consumer_id=consumer,
        max_pending_worksets=1,
        expected_catalog=A1CatalogIdentity(catalog_identity=expected, schema_version=1),
    )
    operation = PreparationOperationData(
        filter_config=filter_config(),
        parser_profiles=(),
        configuration_version="config",
        code_version="code",
        execution_timeout_seconds=5.0,
        claim_lease_seconds=10.0,
        max_records=100,
        max_total_selected_bytes=1048576,
        max_derived_bytes=1024,
        max_total_derived_bytes=1024,
        max_total_parser_output_bytes=1024,
        intake_targets=(target,),
    )
    catalog = MemoryCatalog(catalog_identity, anchor_ok)
    reader = MemoryReader(catalog)
    request = OperationRequest(
        ExecutionIdentity(name), "operator", PhaseCapability.PREPARE
    )
    sql = []
    event.listen(
        store.engine, "before_cursor_execute", lambda *args: sql.append(args[2])
    )
    try:
        with patch(
            "msgloom.preparation_pipeline.scheduled.ReleaseSourceReader",
            return_value=reader,
        ):
            handler = ScheduledPreparationHandler(
                persistence,
                cast(SavedSourceReaderConfig, object()),
                operation,
                AttemptIdentity(name),
            )
            outcome = await handler.run(request)
        if not reader.closed:
            raise RuntimeError("Scheduled handler did not close reader")
        return {
            "name": name,
            "status": outcome.status.value,
            "limitations": [x.code for x in outcome.limitations],
            "queries": catalog.queries,
            "reader_closed": reader.closed,
            "sql": sql,
        }
    finally:
        await persistence.close()


def test_replacement_rejects_before_pending_or_source_work():
    """Catch silent adoption of a replacement into an automatic fresh scope."""
    row = asyncio.run(
        scenario(
            "replacement", seed=True, catalog_identity="replacement", anchor_ok=False
        )
    )
    if row["status"] != "incomplete" or row["sql"]:
        pytest.fail("Replacement must fail before neutral-store work")
    if row["queries"] != ["catalog_identity"]:
        pytest.fail("Replacement performed source work beyond identity check")


@pytest.mark.parametrize(
    "options,status",
    [
        ({"seed": False, "catalog_identity": "old", "anchor_ok": False}, "complete"),
        ({"seed": True, "catalog_identity": "old", "anchor_ok": True}, "complete"),
        ({"seed": True, "catalog_identity": "old", "anchor_ok": False}, "incomplete"),
        (
            {
                "seed": True,
                "catalog_identity": "old",
                "anchor_ok": False,
                "consumer": "other",
            },
            "complete",
        ),
        (
            {
                "seed": True,
                "catalog_identity": "old",
                "anchor_ok": False,
                "source": "other",
            },
            "complete",
        ),
        (
            {
                "seed": True,
                "catalog_identity": "old",
                "anchor_ok": False,
                "stream": "outlook_calendar",
            },
            "complete",
        ),
        (
            {
                "seed": True,
                "catalog_identity": "old",
                "anchor_ok": False,
                "stream": "outlook_mail",
            },
            "complete",
        ),
        (
            {
                "seed": True,
                "catalog_identity": "approved-new",
                "expected": "approved-new",
                "anchor_ok": False,
            },
            "complete",
        ),
    ],
)
def test_explicit_catalog_scopes_and_restore_controls(options, status):
    """Retain matching genesis, restore rejection, and independent scopes."""
    row = asyncio.run(scenario("control", **options))
    if row["status"] != status or not row["reader_closed"]:
        pytest.fail(f"Catalog scope control failed: {row}")
