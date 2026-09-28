"""User-level Microsoft Outlook acquisition workflows composed from Scrapy spiders."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from scrapy.exceptions import UsageError

from message_ingest.acquisition.microsoft.outlook.calendar.planner import (
    pending_full_v1_targets,
)
from message_ingest.acquisition.microsoft.outlook.calendar.profile import (
    FULL_V1 as CALENDAR_FULL_V1,
)
from message_ingest.acquisition.microsoft.outlook.email.planner import (
    pending_full_v1_message_ids,
)
from message_ingest.acquisition.microsoft.outlook.email.profile import (
    FULL_V1 as MAIL_FULL_V1,
)
from message_ingest.catalog import Catalog
from message_ingest.catalog.stores.microsoft.outlook.calendar import (
    OutlookCalendarStore,
)
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
from message_ingest.commands._common import GraphPhase, run_graph_workflow


def _settings(command: Any):
    if command.settings is None:
        raise RuntimeError("Scrapy did not initialize command settings")
    return command.settings


def _planner_limit(value: int | None) -> int | None:
    return None if value in (None, 0) else value


def _reject_shared_jobdir(command: Any) -> None:
    if _settings(command).get("JOBDIR"):
        raise UsageError(
            "multi-phase Microsoft sync does not accept a shared JOBDIR; "
            "use the delta primitive when resumable single-phase execution is required"
        )


def run_mail_sync(command: Any, opts) -> None:
    """Run Mail delta, refresh changed messages, then fill incomplete backlog."""
    _reject_shared_jobdir(command)
    settings = _settings(command)
    database_url = settings["MSGLOOM_DATABASE_URL"]
    source_id = settings["MSGLOOM_SOURCE_ID"]
    max_enrich = _planner_limit(opts.max_enrich)
    reconcile = True if opts.reconcile is None else opts.reconcile

    def after_delta(crawler):
        run_id = getattr(crawler.spider, "run_id", None)
        if not isinstance(run_id, str) or not run_id:
            raise RuntimeError("Mail sync delta phase did not publish a run ID")
        catalog = Catalog(database_url)
        try:
            store = OutlookMailStore(catalog, source_id=source_id)
            changed = tuple(
                store.list_message_ids(
                    run_ids=(run_id,),
                    observation_kinds=("delta", "reconcile"),
                )
            )
            changed_set = set(changed)
            backlog = tuple(
                message_id
                for message_id in pending_full_v1_message_ids(store)
                if message_id not in changed_set
            )
            if max_enrich is not None:
                backlog = backlog[:max_enrich]
        finally:
            catalog.close()

        phases: list[GraphPhase] = []
        if changed:
            phases.append(
                GraphPhase(
                    "outlook_full",
                    {
                        "message_ids": ",".join(changed),
                        "operation": "refresh",
                        "profile": MAIL_FULL_V1,
                    },
                    accepted_final_statuses=frozenset({"completed"}),
                )
            )
        if backlog:
            phases.append(
                GraphPhase(
                    "outlook_full",
                    {
                        "message_ids": ",".join(backlog),
                        "operation": "enrich",
                        "profile": MAIL_FULL_V1,
                    },
                    accepted_final_statuses=frozenset({"completed"}),
                )
            )
        return phases

    run_graph_workflow(
        command,
        [
            GraphPhase(
                "outlook_delta",
                {
                    "page_size": str(opts.page_size or 25),
                    "reconcile_global": "1" if reconcile else "0",
                },
                after=after_delta,
                accepted_final_statuses=frozenset({"completed"}),
            )
        ],
    )


def run_calendar_sync(command: Any, opts) -> None:
    """Discover calendars, collect the fixed window, then enrich changed events."""
    _reject_shared_jobdir(command)
    settings = _settings(command)
    database_url = settings["MSGLOOM_DATABASE_URL"]
    source_id = settings["MSGLOOM_SOURCE_ID"]
    max_enrich = _planner_limit(opts.max_enrich)
    page_size = str(opts.page_size or 100)
    collection_run_ids: list[str] = []

    def enrichment_phases() -> list[GraphPhase]:
        catalog = Catalog(database_url)
        try:
            store = OutlookCalendarStore(catalog, source_id=source_id)
            scoped_event_ids = set(
                store.list_delta_window_event_ids(
                    start_datetime=opts.start,
                    end_datetime=opts.end,
                    calendar_scope="default",
                )
            )
            scoped_event_ids.update(
                event_id
                for event_id, _calendar_id, _version in store.list_event_targets(
                    run_ids=tuple(collection_run_ids)
                )
            )
            targets = pending_full_v1_targets(
                store,
                event_ids=tuple(sorted(scoped_event_ids)),
                limit=max_enrich,
            )
        finally:
            catalog.close()

        grouped: OrderedDict[str, list[str]] = OrderedDict()
        for target in targets:
            grouped.setdefault(target.calendar_id, []).append(target.event_id)
        return [
            GraphPhase(
                "outlook_calendar_full",
                {
                    "event_ids": event_ids,
                    "calendar_id": "" if calendar_id == "default" else calendar_id,
                    "page_size": page_size,
                    "operation": "enrich",
                    "profile": CALENDAR_FULL_V1,
                },
            )
            for calendar_id, event_ids in grouped.items()
        ]

    def capture_collection_run(*, final: bool):
        def after(crawler):
            run_id = getattr(crawler.spider, "run_id", None)
            if not isinstance(run_id, str) or not run_id:
                raise RuntimeError("Calendar collection phase did not publish a run ID")
            collection_run_ids.append(run_id)
            return enrichment_phases() if final else ()

        return after

    def after_discover(_crawler):
        catalog = Catalog(database_url)
        try:
            store = OutlookCalendarStore(catalog, source_id=source_id)
            calendars = store.list_calendars()
        finally:
            catalog.close()

        secondary_ids = [
            calendar_id
            for calendar_id, is_default in calendars
            if is_default is not True
        ]
        phases: list[GraphPhase] = []
        collection_count = 1 + len(secondary_ids)
        phases.append(
            GraphPhase(
                "outlook_calendar_delta",
                {
                    "start_datetime": opts.start,
                    "end_datetime": opts.end,
                    "page_size": page_size,
                },
                after=capture_collection_run(final=collection_count == 1),
            )
        )
        for index, calendar_id in enumerate(secondary_ids, start=2):
            phases.append(
                GraphPhase(
                    "outlook_calendar_window",
                    {
                        "start_datetime": opts.start,
                        "end_datetime": opts.end,
                        "calendar_id": calendar_id,
                        "page_size": page_size,
                    },
                    after=capture_collection_run(final=index == collection_count),
                )
            )
        return phases

    run_graph_workflow(
        command,
        [
            GraphPhase(
                "outlook_calendar_discover",
                {"page_size": page_size},
                after=after_discover,
            )
        ],
    )


__all__ = ["run_calendar_sync", "run_mail_sync"]
