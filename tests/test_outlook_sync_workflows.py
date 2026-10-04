"""Verify catalog-driven Mail and Calendar sync phase planning."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest
from outlook_mail_handoff_fixtures import saved_mail_evidence
from scrapy.settings import Settings

import message_ingest.commands.microsoft.outlook.sync as sync_module
from message_ingest.acquisition.microsoft.outlook.email.profile import (
    FULL_V1 as MAIL_FULL_V1,
)
from message_ingest.acquisition.microsoft.outlook.email.rule_config import (
    parse_mail_rule_policy,
)
from message_ingest.catalog import Catalog
from message_ingest.catalog.stores.microsoft.outlook.calendar import (
    OutlookCalendarStore,
)
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
from message_ingest.items.microsoft.outlook.calendar import (
    OutlookCalendarEventItem,
    OutlookCalendarItem,
)

NOW = "2026-09-28T00:00:00+00:00"
START = "2026-09-27T00:00:00+10:00"
END = "2026-10-04T00:00:00+10:00"


def _command(tmp_path: Path):
    settings = Settings(
        {
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "MSGLOOM_SOURCE_ID": "source-1",
            "JOBDIR": None,
        }
    )
    return SimpleNamespace(settings=settings, crawler_process=object(), exitcode=0)


def _opts(**kwargs) -> Namespace:
    values = {
        "page_size": None,
        "reconcile": None,
        "max_enrich": None,
        "start": START,
        "end": END,
    }
    values.update(kwargs)
    return Namespace(**values)


def test_mail_sync_refreshes_changed_messages_then_enriches_backlog(
    tmp_path: Path, monkeypatch
) -> None:
    command = _command(tmp_path)
    catalog = Catalog(command.settings["MSGLOOM_DATABASE_URL"])
    try:
        store = OutlookMailStore(catalog, source_id="source-1")
        store.record_message(
            run_id="delta-run",
            message={"id": "changed", "lastModifiedDateTime": NOW},
            kind="delta",
            evidence_id=None,
            observed_at=NOW,
        )
        store.record_message(
            run_id="older-run",
            message={"id": "backlog", "lastModifiedDateTime": NOW},
            kind="delta",
            evidence_id=None,
            observed_at=NOW,
        )
        store.record_message(
            run_id="older-run",
            message={"id": "complete", "lastModifiedDateTime": NOW},
            kind="delta",
            evidence_id=None,
            observed_at=NOW,
        )
        for surface in ("detail", "mime", "attachments"):
            evidence_id = saved_mail_evidence(
                catalog,
                evidence_id=f"complete-{surface}",
                run_id="older-run",
            )
            store.set_surface(
                run_id="older-run",
                message_id="complete",
                surface=surface,
                status="acquired",
                evidence_id=evidence_id,
                observed_at=NOW,
                profile_version=MAIL_FULL_V1,
            )
    finally:
        catalog.close()

    captured = []
    monkeypatch.setattr(
        sync_module,
        "run_graph_workflow",
        lambda _command, phases: captured.extend(phases),
    )
    sync_module.run_mail_sync(
        command,
        _opts(page_size=50, reconcile=False),
        mail_rule_policy=parse_mail_rule_policy(None),
    )

    if [phase.spider_name for phase in captured] != [
        "outlook_folder_delta",
        "outlook_delta",
    ]:
        pytest.fail(f"Unexpected Mail sync collection phases: {captured!r}")
    follow = list(
        captured[1].after(SimpleNamespace(spider=SimpleNamespace(run_id="delta-run")))
    )
    if [(phase.spider_name, phase.spider_args["operation"]) for phase in follow] != [
        ("outlook_full", "refresh"),
        ("outlook_full", "enrich"),
    ]:
        pytest.fail(f"Unexpected Mail sync enrichment phases: {follow!r}")
    if follow[0].spider_args["message_ids"] != "changed":
        pytest.fail("Expected changed delta message to be refreshed")
    if follow[1].spider_args["message_ids"] != "backlog":
        pytest.fail("Expected incomplete historical Mail backlog to be enriched")


def test_calendar_sync_collects_primary_and_secondary_then_groups_enrichment(
    tmp_path: Path, monkeypatch
) -> None:
    command = _command(tmp_path)
    catalog = Catalog(command.settings["MSGLOOM_DATABASE_URL"])
    try:
        store = OutlookCalendarStore(catalog, source_id="source-1")
        store.persist_calendar(
            OutlookCalendarItem(
                calendar_id="calendar-primary",
                raw={"id": "calendar-primary", "isDefaultCalendar": True},
                observed_at=NOW,
                evidence_id=None,
                run_id="discover-run",
            )
        )
        store.persist_calendar(
            OutlookCalendarItem(
                calendar_id="calendar-secondary",
                raw={"id": "calendar-secondary", "isDefaultCalendar": False},
                observed_at=NOW,
                evidence_id=None,
                run_id="discover-run",
            )
        )
        store.persist_event(
            OutlookCalendarEventItem(
                event_id="primary-event",
                raw={"id": "primary-event", "changeKey": "p1"},
                observed_at=NOW,
                evidence_id=None,
                run_id="delta-run",
                calendar_id="calendar-primary",
            )
        )
        store.persist_event(
            OutlookCalendarEventItem(
                event_id="secondary-event",
                raw={"id": "secondary-event", "changeKey": "s1"},
                observed_at=NOW,
                evidence_id=None,
                run_id="window-run",
                calendar_id="calendar-secondary",
            )
        )
    finally:
        catalog.close()

    captured = []
    monkeypatch.setattr(
        sync_module,
        "run_graph_workflow",
        lambda _command, phases: captured.extend(phases),
    )
    sync_module.run_calendar_sync(command, _opts(page_size=25))

    discover = captured[0]
    collection = list(
        discover.after(SimpleNamespace(spider=SimpleNamespace(run_id="discover-run")))
    )
    if [phase.spider_name for phase in collection] != [
        "outlook_calendar_delta",
        "outlook_calendar_window",
    ]:
        pytest.fail(f"Unexpected Calendar collection plan: {collection!r}")
    if list(
        collection[0].after(SimpleNamespace(spider=SimpleNamespace(run_id="delta-run")))
    ):
        pytest.fail("Expected enrichment planning only after final collection phase")
    full = list(
        collection[1].after(
            SimpleNamespace(spider=SimpleNamespace(run_id="window-run"))
        )
    )
    if [phase.spider_args["calendar_id"] for phase in full] != [
        "calendar-primary",
        "calendar-secondary",
    ]:
        pytest.fail(f"Expected full phases grouped by Calendar: {full!r}")
    if [phase.spider_args["event_ids"] for phase in full] != [
        ["primary-event"],
        ["secondary-event"],
    ]:
        pytest.fail("Expected current-run Calendar events to become enrichment targets")
    if any(phase.spider_args["operation"] != "enrich" for phase in full):
        pytest.fail("Calendar sync must use planner-driven enrich mode")


def test_multi_phase_sync_rejects_shared_jobdir(tmp_path: Path) -> None:
    command = _command(tmp_path)
    command.settings.set("JOBDIR", str(tmp_path / "job"), priority="cmdline")
    with pytest.raises(Exception, match="shared JOBDIR"):
        sync_module.run_mail_sync(
            command,
            _opts(),
            mail_rule_policy=parse_mail_rule_policy(None),
        )
