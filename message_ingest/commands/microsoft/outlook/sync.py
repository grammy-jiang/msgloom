"""User-level Microsoft Outlook acquisition workflows composed from Scrapy spiders."""

from __future__ import annotations

import logging
from collections import OrderedDict
from typing import Any

from scrapy.exceptions import UsageError

from message_ingest.acquisition.microsoft.outlook.calendar.planner import (
    pending_full_v1_targets,
)
from message_ingest.acquisition.microsoft.outlook.calendar.profile import (
    FULL_V1 as CALENDAR_FULL_V1,
)
from message_ingest.acquisition.microsoft.outlook.email.full_completion import (
    verify_current_full_v1,
)
from message_ingest.acquisition.microsoft.outlook.email.planner import (
    pending_full_v1_message_ids,
)
from message_ingest.acquisition.microsoft.outlook.email.profile import (
    DISCOVERY_V1 as MAIL_DISCOVERY_V1,
)
from message_ingest.acquisition.microsoft.outlook.email.profile import (
    FULL_V1 as MAIL_FULL_V1,
)
from message_ingest.acquisition.microsoft.outlook.email.rule_config import (
    MailRulePolicy,
)
from message_ingest.catalog import Catalog
from message_ingest.catalog.stores.microsoft.outlook.calendar import (
    OutlookCalendarStore,
)
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
from message_ingest.commands._common import GraphPhase, run_graph_workflow
from message_ingest.spiders.microsoft.outlook.email._delta_state import (
    MailDeltaCommitMode,
)
from message_ingest.sync.microsoft.outlook.email.promotion import (
    ValidatedMailDeltaRun,
    promote_validated_mail_delta,
)

logger = logging.getLogger(__name__)


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


def run_mail_sync(
    command: Any,
    opts,
    *,
    mail_rule_policy: MailRulePolicy,
) -> None:
    """Run legacy or rules-enabled Mail sync with separate correctness paths."""
    _reject_shared_jobdir(command)
    settings = _settings(command)
    database_url = settings["MSGLOOM_DATABASE_URL"]
    source_id = settings["MSGLOOM_SOURCE_ID"]
    reconcile = True if opts.reconcile is None else opts.reconcile

    if mail_rule_policy.enabled:
        _run_rules_enabled_mail_sync(
            command,
            opts,
            mail_rule_policy=mail_rule_policy,
            database_url=database_url,
            source_id=source_id,
            reconcile=reconcile,
        )
        return

    _run_rules_disabled_mail_sync(
        command,
        opts,
        mail_rule_policy=mail_rule_policy,
        database_url=database_url,
        source_id=source_id,
        reconcile=reconcile,
    )


def _run_rules_disabled_mail_sync(
    command: Any,
    opts,
    *,
    mail_rule_policy: MailRulePolicy,
    database_url: str,
    source_id: str,
    reconcile: bool,
) -> None:
    """Preserve the pre-rules changed-refresh plus historical-backlog workflow."""
    max_enrich = _planner_limit(opts.max_enrich)

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
                "outlook_folder_delta",
                {"page_size": str(opts.page_size or 25)},
            ),
            GraphPhase(
                "outlook_delta",
                {
                    "page_size": str(opts.page_size or 25),
                    "reconcile_global": "1" if reconcile else "0",
                    "_mail_rule_policy": mail_rule_policy,
                },
                after=after_delta,
                accepted_final_statuses=frozenset({"completed"}),
            ),
        ],
    )


def _run_rules_enabled_mail_sync(
    command: Any,
    opts,
    *,
    mail_rule_policy: MailRulePolicy,
    database_url: str,
    source_id: str,
    reconcile: bool,
) -> None:
    """Plan Full only from attempt-local rule targets and defer delta promotion."""
    validated_delta: ValidatedMailDeltaRun | None = None
    delta_crawler = None

    def full_completion_validator(message_ids: tuple[str, ...]):
        def validate(crawler) -> bool:
            run_id = getattr(crawler.spider, "run_id", None)
            if not isinstance(run_id, str) or not run_id:
                return False
            catalog = Catalog(database_url)
            try:
                result = verify_current_full_v1(
                    catalog,
                    source_id=source_id,
                    run_id=run_id,
                    message_ids=message_ids,
                )
            finally:
                catalog.close()

            crawler.stats.set_value(
                "msgloom/mail_rules/full_completion",
                result.reason_code,
            )
            crawler.stats.set_value(
                "msgloom/mail_rules/full_completion_with_limitations",
                result.with_limitations,
            )
            if not result.complete:
                logger.error(
                    "Rules-selected Outlook Mail Full did not reach terminal "
                    "completeness: reason=%s",
                    result.reason_code,
                )
                return False

            reason_codes = _crawler_reason_codes(crawler)
            nonwaivable = reason_codes - result.waivable_failure_reasons
            if nonwaivable:
                logger.error(
                    "Rules-selected Outlook Mail Full has non-waivable failures: "
                    "reason_count=%s",
                    len(nonwaivable),
                )
                return False

            logger.info(
                "Rules-selected Outlook Mail Full completion: reason=%s "
                "with_limitations=%s failure_reason_count=%s",
                result.reason_code,
                str(result.with_limitations).lower(),
                len(reason_codes),
            )
            return True

        return validate

    def after_delta(crawler):
        nonlocal validated_delta, delta_crawler
        spider = crawler.spider
        run_id = getattr(spider, "run_id", None)
        validated = getattr(spider, "validated_delta_run", None)
        profiles = getattr(spider, "mail_rule_profiles", None)
        if not isinstance(run_id, str) or not run_id:
            raise RuntimeError("Mail sync delta phase did not publish a run ID")
        if not isinstance(validated, ValidatedMailDeltaRun):
            raise TypeError("Mail sync delta phase did not publish a validated run")
        if validated.run_id != run_id:
            raise RuntimeError(
                "Mail sync delta validated run does not match Spider run"
            )
        if not isinstance(profiles, tuple):
            raise TypeError("Mail sync delta phase did not publish rule profiles")

        profile_map: dict[str, str] = {}
        targets: list[str] = []
        for value in profiles:
            if (
                not isinstance(value, tuple)
                or len(value) != 2
                or not all(isinstance(item, str) for item in value)
            ):
                raise RuntimeError("Mail sync delta rule profile state is invalid")
            message_id, profile = value
            if message_id in profile_map:
                raise RuntimeError("Mail sync delta published duplicate rule profiles")
            profile_map[message_id] = profile
            if profile == MAIL_FULL_V1:
                targets.append(message_id)
            elif profile != MAIL_DISCOVERY_V1:
                raise RuntimeError("Mail sync delta published an unknown rule profile")

        catalog = Catalog(database_url)
        try:
            observed = set(
                OutlookMailStore(catalog, source_id=source_id).list_message_ids(
                    run_ids=(run_id,),
                    observation_kinds=("delta", "reconcile"),
                )
            )
        finally:
            catalog.close()
        if set(profile_map) != observed:
            raise RuntimeError(
                "Mail sync delta rule profiles do not cover current observations"
            )

        validated_delta = validated
        delta_crawler = crawler
        unique_targets = tuple(dict.fromkeys(targets))
        if not unique_targets:
            return ()

        return (
            GraphPhase(
                "outlook_full",
                {
                    "message_ids": ",".join(unique_targets),
                    "operation": "refresh",
                    "profile": MAIL_FULL_V1,
                    "_authoritative_rule_refresh": True,
                },
                completion_validator=full_completion_validator(unique_targets),
            ),
        )

    def finalize(_completed_crawlers) -> None:
        if validated_delta is None or delta_crawler is None:
            raise RuntimeError("Mail sync finalizer lost validated delta state")
        catalog = Catalog(database_url)
        try:
            outcome = promote_validated_mail_delta(
                catalog,
                source_id=source_id,
                validated=validated_delta,
            )
        finally:
            catalog.close()
        delta_crawler.stats.set_value(
            "msgloom/mail_rules/final_promotion",
            "committed",
        )
        delta_crawler.stats.set_value(
            "msgloom/mail_rules/final_committed_folder_count",
            outcome["committed_folders"],
        )
        logger.info(
            "Rules-enabled Outlook Mail delta promotion committed: folders=%s",
            outcome["committed_folders"],
        )

    run_graph_workflow(
        command,
        [
            GraphPhase(
                "outlook_folder_delta",
                {"page_size": str(opts.page_size or 25)},
            ),
            GraphPhase(
                "outlook_delta",
                {
                    "page_size": str(opts.page_size or 25),
                    "reconcile_global": "1" if reconcile else "0",
                    "_mail_rule_policy": mail_rule_policy,
                    "_mail_delta_commit_mode": MailDeltaCommitMode.DEFERRED,
                },
                after=after_delta,
                accepted_final_statuses=frozenset({"completed"}),
            ),
        ],
        on_success=finalize,
    )


def _crawler_reason_codes(crawler) -> frozenset[str]:
    values = crawler.stats.get_value("msgloom/final/reason_codes", ())
    reasons = (
        {value for value in values if isinstance(value, str)}
        if isinstance(values, (list, tuple, set, frozenset))
        else set()
    )
    spider_reasons = getattr(crawler.spider, "failure_reasons", ())
    if isinstance(spider_reasons, (list, tuple, set, frozenset)):
        reasons.update(value for value in spider_reasons if isinstance(value, str))
    return frozenset(reasons)


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
