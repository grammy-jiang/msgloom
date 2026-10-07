"""Per-target completion must bind exact effective Calendar facts."""

from __future__ import annotations

import importlib
from dataclasses import asdict

import pytest
from _full_completion_fixtures import seed_target, set_surface
from sqlalchemy import select

from message_ingest.catalog import Catalog
from message_ingest.catalog.models.handoff import AcquisitionFact


def verify(catalog, target="one", *, run="run", current=True):
    """Exercise the public per-target proof once it exists."""
    name = "message_ingest.acquisition.microsoft.outlook.calendar.full_completion"
    try:
        module = importlib.import_module(name)
    except ModuleNotFoundError:
        pytest.fail("Calendar per-target Full-v1 verifier is missing")
    return module.verify_full_v1_target(
        catalog,
        source_id="source",
        run_id=run,
        event_id=target,
        require_current_attempt=current,
    )


@pytest.fixture
def catalog(tmp_path):
    value = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    yield value
    value.close()


def test_complete_event_is_independent_of_failed_target(catalog):
    seed_target(catalog, "calendar")
    other = seed_target(catalog, "calendar", "two")
    set_surface(
        other,
        "calendar",
        "two",
        "attachments",
        "calendar-two-run-attachments",
        status="failed",
    )
    complete = verify(catalog)
    failed = verify(catalog, "two")
    if not complete.complete or failed.complete:
        pytest.fail("One failed event blocked or completed an independent target")
    if complete.resource_identity != "one" or complete.terminal_with_limitations:
        pytest.fail("Target identity/coverage was not retained")
    with catalog.Session() as session:
        identities = set(session.scalars(select(AcquisitionFact.fact_id)))
    if len(complete.required_facts) != 3:
        pytest.fail("Expected primary plus two exact base surface facts")
    if any(
        f.fact_id not in identities or f.source_version_locator is None
        for f in complete.required_facts
    ):
        pytest.fail("Completion did not bind immutable existing locators")
    if "subject" in str(asdict(complete)):
        pytest.fail("Completion copied provider payload")


@pytest.mark.parametrize(
    "status",
    [
        "unsupported",
        "not_applicable",
        "omitted_size_limit",
        "unauthorized",
        "unavailable",
    ],
)
def test_terminal_limitations_require_complete_profile(catalog, status):
    store = seed_target(catalog, "calendar")
    set_surface(
        store,
        "calendar",
        "one",
        "attachments",
        "calendar-one-run-attachments",
        status=status,
    )
    result = verify(catalog)
    if not result.complete or not result.terminal_with_limitations:
        pytest.fail("Terminal profile limitation did not complete target")
    if result.limitation_codes != (status,):
        pytest.fail("Limitation codes must be bounded status vocabulary")
    set_surface(
        store, "calendar", "one", "detail", "calendar-one-run-detail", status="failed"
    )
    result = verify(catalog)
    if result.complete or result.terminal_with_limitations or result.required_facts:
        pytest.fail("Incomplete profile leaked a usable completion proof")


@pytest.mark.parametrize(
    "field,value",
    [
        ("profile", "older-profile"),
        ("version", "other-version"),
        ("status", "failed"),
        ("status", "pending"),
    ],
)
def test_wrong_profile_version_or_unfinished_surface_fails(catalog, field, value):
    store = seed_target(catalog, "calendar")
    set_surface(
        store, "calendar", "one", "detail", "calendar-one-run-detail", **{field: value}
    )
    if verify(catalog).complete:
        pytest.fail("Invalid surface satisfied Full-v1")


def test_old_facts_need_explicit_no_work_revalidation(catalog):
    seed_target(catalog, "calendar")
    if verify(catalog, run="new").complete:
        pytest.fail("Old attempt satisfied required current-attempt proof")
    result = verify(catalog, run="new", current=False)
    if not result.complete:
        pytest.fail("No-work revalidation could not bind effective older facts")
    if any(f.run_id != "run" for f in result.required_facts):
        pytest.fail("No-work revalidation fabricated new acquisition provenance")
