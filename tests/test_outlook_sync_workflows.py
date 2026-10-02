"""Verify catalog-driven Mail and Calendar sync phase planning."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest
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
            store.set_surface(
                message_id="complete",
                surface=surface,
                status="acquired",
                evidence_id=None,
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


class _Stats:
    def __init__(self, values: dict[str, object] | None = None) -> None:
        self.values = dict(values or {})

    def get_value(self, key: str, default=None):
        return self.values.get(key, default)

    def set_value(self, key: str, value: object) -> None:
        self.values[key] = value


def _enabled_mail_policy():
    return parse_mail_rule_policy(
        {
            "enabled": True,
            "default_profile": "discovery",
            "rules": [
                {
                    "id": "important",
                    "sequence": 10,
                    "profile": "full",
                    "conditions": {"subject_contains": ["important"]},
                }
            ],
        }
    )


def _validated_delta(run_id: str = "delta-run"):
    from message_ingest.sync.microsoft.outlook.email.promotion import (
        ValidatedMailDeltaRun,
    )

    return ValidatedMailDeltaRun(
        run_id=run_id,
        expected_folder_ids=frozenset({"folder-inbox"}),
        reconcile_messages=False,
        candidate_folder_ids=frozenset({"folder-inbox"}),
    )


def _capture_enabled_mail_workflow(
    tmp_path: Path,
    monkeypatch,
    *,
    profiles: tuple[tuple[str, str], ...],
):
    from message_ingest.acquisition.microsoft.outlook.email.profile import (
        DISCOVERY_V1,
        FULL_V1,
    )

    del DISCOVERY_V1, FULL_V1
    command = _command(tmp_path)
    captured: dict[str, object] = {}

    def capture(_command, phases, *, on_success=None):
        captured["phases"] = tuple(phases)
        captured["on_success"] = on_success
        return ()

    monkeypatch.setattr(sync_module, "run_graph_workflow", capture)
    catalog = Catalog(command.settings["MSGLOOM_DATABASE_URL"])
    try:
        store = OutlookMailStore(catalog, source_id="source-1")
        for index, (message_id, _profile) in enumerate(profiles):
            store.record_message(
                run_id="delta-run",
                message={
                    "id": message_id,
                    "changeKey": f"v-{index}",
                    "lastModifiedDateTime": NOW,
                },
                kind="delta",
                evidence_id=None,
                observed_at=NOW,
            )
    finally:
        catalog.close()

    policy = _enabled_mail_policy()
    sync_module.run_mail_sync(
        command,
        _opts(page_size=50, reconcile=False),
        mail_rule_policy=policy,
    )
    phases = captured["phases"]
    assert isinstance(phases, tuple)
    delta = phases[1]
    validated = _validated_delta()
    delta_crawler = SimpleNamespace(
        spider=SimpleNamespace(
            run_id="delta-run",
            mail_rule_profiles=profiles,
            validated_delta_run=validated,
        ),
        stats=_Stats(),
    )
    follow = tuple(delta.after(delta_crawler))
    return command, captured, phases, delta_crawler, validated, follow


def test_rules_enabled_mail_sync_uses_runtime_full_targets_and_skips_legacy_backlog(
    tmp_path: Path, monkeypatch
) -> None:
    from message_ingest.acquisition.microsoft.outlook.email.profile import (
        DISCOVERY_V1,
        FULL_V1,
    )
    from message_ingest.spiders.microsoft.outlook.email._delta_state import (
        MailDeltaCommitMode,
    )

    command = _command(tmp_path)
    catalog = Catalog(command.settings["MSGLOOM_DATABASE_URL"])
    try:
        store = OutlookMailStore(catalog, source_id="source-1")
        store.record_message(
            run_id="old-run",
            message={"id": "historical-backlog", "lastModifiedDateTime": NOW},
            kind="delta",
            evidence_id=None,
            observed_at=NOW,
        )
    finally:
        catalog.close()

    command, captured, phases, _delta_crawler, _validated, follow = (
        _capture_enabled_mail_workflow(
            tmp_path,
            monkeypatch,
            profiles=(
                ("selected-full", FULL_V1),
                ("selected-discovery", DISCOVERY_V1),
            ),
        )
    )

    if [phase.spider_name for phase in phases] != [
        "outlook_folder_delta",
        "outlook_delta",
    ]:
        pytest.fail(f"Rules-enabled collection phases changed: {phases!r}")
    delta = phases[1]
    if (
        delta.spider_args.get("_mail_delta_commit_mode")
        is not MailDeltaCommitMode.DEFERRED
    ):
        pytest.fail("Rules-enabled Mail delta did not use private deferred commit mode")
    if delta.spider_args.get("_mail_rule_policy") != _enabled_mail_policy():
        pytest.fail("Rules-enabled Mail delta lost the frozen policy")
    if len(follow) != 1:
        pytest.fail(
            f"Rules-enabled Mail sync planned wrong Full phase count: {follow!r}"
        )
    full = follow[0]
    if full.spider_name != "outlook_full":
        pytest.fail("Rules-enabled Mail sync did not plan Outlook Full")
    if full.spider_args.get("message_ids") != "selected-full":
        pytest.fail(f"Rule-selected Full targets changed: {full.spider_args!r}")
    if full.spider_args.get("operation") != "refresh":
        pytest.fail("Rule-selected target must use refresh semantics")
    if full.spider_args.get("_authoritative_rule_refresh") is not True:
        pytest.fail("Rule-selected Full target was not authoritative/no-cache")
    if full.completion_validator is None:
        pytest.fail("Rule-selected Full phase lost its current-attempt completion gate")
    if "historical-backlog" in str(full.spider_args):
        pytest.fail("Legacy incomplete-Full backlog bypassed active Mail rules")
    if captured.get("on_success") is None:
        pytest.fail("Rules-enabled workflow did not install the atomic finalizer")
    if command.exitcode:
        pytest.fail("Planning a valid rules-enabled workflow changed exitcode")


def test_rules_enabled_delta_refuses_unprofiled_current_observation(
    tmp_path: Path, monkeypatch
) -> None:
    from message_ingest.acquisition.microsoft.outlook.email.profile import DISCOVERY_V1

    command = _command(tmp_path)
    captured: dict[str, object] = {}

    def capture(_command, phases, *, on_success=None):
        captured["phases"] = tuple(phases)
        captured["on_success"] = on_success
        return ()

    monkeypatch.setattr(sync_module, "run_graph_workflow", capture)
    policy = _enabled_mail_policy()
    sync_module.run_mail_sync(
        command,
        _opts(page_size=50, reconcile=False),
        mail_rule_policy=policy,
    )
    phases = captured["phases"]
    assert isinstance(phases, tuple)
    delta = phases[1]

    catalog = Catalog(command.settings["MSGLOOM_DATABASE_URL"])
    try:
        OutlookMailStore(catalog, source_id="source-1").record_message(
            run_id="delta-run",
            message={
                "id": "observed-but-unprofiled",
                "changeKey": "v1",
                "lastModifiedDateTime": NOW,
            },
            kind="delta",
            evidence_id=None,
            observed_at=NOW,
        )
    finally:
        catalog.close()

    crawler = SimpleNamespace(
        spider=SimpleNamespace(
            run_id="delta-run",
            mail_rule_profiles=(("different-message", DISCOVERY_V1),),
            validated_delta_run=_validated_delta(),
        ),
        stats=_Stats(),
    )
    with pytest.raises(RuntimeError, match="do not cover current observations"):
        tuple(delta.after(crawler))


def test_rules_enabled_zero_full_targets_skips_full_phase_but_keeps_finalizer(
    tmp_path: Path, monkeypatch
) -> None:
    from message_ingest.acquisition.microsoft.outlook.email.profile import DISCOVERY_V1

    _command_obj, captured, _phases, _delta, _validated, follow = (
        _capture_enabled_mail_workflow(
            tmp_path,
            monkeypatch,
            profiles=(("discovery-only-message", DISCOVERY_V1),),
        )
    )

    if follow:
        pytest.fail("Discovery-only rules unexpectedly scheduled a Full crawler")
    if captured.get("on_success") is None:
        pytest.fail("Zero-Full rules workflow lost its checkpoint finalizer")


@pytest.mark.parametrize(
    ("completion", "reason_codes", "expected"),
    (
        (
            (
                "terminal_complete_with_limitations",
                True,
                {"request_failure:message-detail"},
            ),
            ["request_failure:message-detail"],
            True,
        ),
        (
            (
                "terminal_complete_with_limitations",
                True,
                {"request_failure:message-detail"},
            ),
            ["request_failure:message-detail", "item_error"],
            False,
        ),
        (
            ("incomplete", False, set()),
            [],
            False,
        ),
    ),
)
def test_rule_full_phase_gate_requires_current_completion_and_only_waivable_failures(
    tmp_path: Path,
    monkeypatch,
    completion,
    reason_codes: list[str],
    expected: bool,
) -> None:
    from message_ingest.acquisition.microsoft.outlook.email.full_completion import (
        MailFullCompletionResult,
    )
    from message_ingest.acquisition.microsoft.outlook.email.profile import FULL_V1

    reason, complete, waivable = completion
    result = MailFullCompletionResult(
        complete=complete,
        with_limitations=reason == "terminal_complete_with_limitations",
        reason_code=reason,
        waivable_failure_reasons=frozenset(waivable),
    )
    monkeypatch.setattr(sync_module, "verify_current_full_v1", lambda *a, **k: result)

    _command_obj, _captured, _phases, _delta, _validated, follow = (
        _capture_enabled_mail_workflow(
            tmp_path,
            monkeypatch,
            profiles=(("selected-full", FULL_V1),),
        )
    )
    full = follow[0]
    stats = _Stats({"msgloom/final/reason_codes": reason_codes})
    crawler = SimpleNamespace(
        spider=SimpleNamespace(
            run_id="full-run",
            failure_reasons=frozenset(reason_codes),
        ),
        stats=stats,
    )

    actual = full.completion_validator(crawler)

    if actual is not expected:
        pytest.fail(
            f"Rules Full completion gate returned {actual!r}, expected {expected!r}"
        )
    if stats.get_value("msgloom/mail_rules/full_completion") != reason:
        pytest.fail("Full completion gate did not publish its bounded result stat")


def test_rules_enabled_success_finalizer_promotes_exact_validated_delta_run_once(
    tmp_path: Path, monkeypatch
) -> None:
    from message_ingest.acquisition.microsoft.outlook.email.profile import DISCOVERY_V1

    calls: list[tuple[str, object]] = []

    def promote(catalog, *, source_id: str, validated):
        del catalog
        calls.append((source_id, validated))
        return {"committed_folders": 1}

    monkeypatch.setattr(sync_module, "promote_validated_mail_delta", promote)
    _command_obj, captured, _phases, delta_crawler, validated, follow = (
        _capture_enabled_mail_workflow(
            tmp_path,
            monkeypatch,
            profiles=(("discovery-only-message", DISCOVERY_V1),),
        )
    )
    if follow:
        pytest.fail("Zero-Full fixture unexpectedly planned Full work")
    finalizer = captured.get("on_success")
    if not callable(finalizer):
        pytest.fail("Rules-enabled workflow lost success finalizer")

    finalizer((SimpleNamespace(spider=SimpleNamespace()), delta_crawler))

    if calls != [("source-1", validated)]:
        pytest.fail("Finalizer did not promote the exact validated delta run once")
