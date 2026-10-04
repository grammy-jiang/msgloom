"""Validate Microsoft Outlook Mail CLI mapping through one public namespace."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import cast
from unittest.mock import patch

import pytest
from scrapy.crawler import CrawlerProcessBase
from scrapy.exceptions import UsageError

from message_ingest.acquisition.microsoft.outlook.email.profile import FULL_V1
from message_ingest.commands.microsoft import Command as MicrosoftCommand


class FakeStats:
    def __init__(self, final_status: str | None = None) -> None:
        self.final_status = final_status

    def get_value(self, key: str, default=None):
        if key == "msgloom/final/status":
            return self.final_status
        return default


class FakeCrawler:
    def __init__(
        self,
        spider_name: str,
        final_status: str | None = None,
        *,
        run_failed: bool = False,
    ) -> None:
        self.spider_name = spider_name
        self.stats = FakeStats(final_status)
        self.spider = SimpleNamespace(run_failed=run_failed)


class FakeCrawlerProcess:
    def __init__(
        self,
        *,
        final_status: str | None = None,
        run_failed: bool = False,
    ) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.started = False
        self.bootstrap_failed = False
        self.final_status = final_status
        self.run_failed = run_failed

    def create_crawler(self, spider_name: str) -> FakeCrawler:
        return FakeCrawler(
            spider_name,
            self.final_status,
            run_failed=self.run_failed,
        )

    def crawl(self, crawler: FakeCrawler, **kwargs):
        self.calls.append((crawler.spider_name, kwargs))

    def start(self) -> None:
        self.started = True


def _opts(
    *,
    action: str,
    message_ids: list[str] | None = None,
    folder: str | None = None,
    page_size: int | None = None,
    max_pages: int | None = None,
    reconcile: bool | None = None,
    operation: str | None = None,
    acquisition_profile: str | None = None,
    config: Path | None = None,
    max_enrich: int | None = None,
) -> argparse.Namespace:
    return argparse.Namespace(
        section="outlook",
        resource_or_action="mail",
        action=action,
        message_ids=message_ids or [],
        json=False,
        yes=False,
        folder=folder,
        page_size=page_size,
        max_pages=max_pages,
        reconcile=reconcile,
        operation=operation,
        max_enrich=max_enrich,
        acquisition_profile=acquisition_profile,
        config=config,
        start=None,
        end=None,
        calendar=None,
    )


def _run(opts: argparse.Namespace) -> FakeCrawlerProcess:
    command = MicrosoftCommand()
    process = FakeCrawlerProcess()
    command.crawler_process = cast(CrawlerProcessBase, process)
    with (
        TemporaryDirectory() as config_home,
        patch.dict(
            "os.environ",
            {"XDG_CONFIG_HOME": config_home},
        ),
    ):
        command.run([], opts)
    return process


def _public_calls(process: FakeCrawlerProcess):
    return [
        (
            name,
            {key: value for key, value in kwargs.items() if key != "_mail_rule_policy"},
        )
        for name, kwargs in process.calls
    ]


def _mail_config(tmp_path: Path, *, enabled: bool, private: str = "approval") -> Path:
    path = tmp_path / "msgloom.toml"
    lines = [
        "[acquisition.microsoft.outlook.mail]",
        f"enabled = {'true' if enabled else 'false'}",
    ]
    if enabled:
        lines.extend(
            (
                'default_profile = "discovery"',
                "",
                "[[acquisition.microsoft.outlook.mail.rules]]",
                'id = "finance-01"',
                "sequence = 10",
                'profile = "full"',
                "",
                "[acquisition.microsoft.outlook.mail.rules.conditions]",
                f'subject_contains = ["{private}"]',
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_discover_maps_cli_options_to_spider_arguments() -> None:
    process = _run(
        _opts(
            action="discover",
            folder="archive",
            page_size=100,
            max_pages=3,
        )
    )
    if _public_calls(process) != [
        (
            "outlook_discover",
            {"folder": "archive", "page_size": "100", "max_pages": "3"},
        )
    ]:
        pytest.fail(f"Unexpected Mail discover mapping: {process.calls!r}")


def test_delta_maps_page_size_and_reconciliation() -> None:
    process = _run(_opts(action="delta", page_size=50, reconcile=False))
    if _public_calls(process) != [
        ("outlook_delta", {"page_size": "50", "reconcile_global": "0"})
    ]:
        pytest.fail(f"Unexpected Mail delta mapping: {process.calls!r}")


def test_full_accepts_multiple_ids_and_deduplicates_them() -> None:
    process = _run(
        _opts(
            action="full",
            message_ids=["message-1", "message-2", "message-1"],
            operation="enrich",
            acquisition_profile=FULL_V1,
        )
    )
    if process.calls != [
        (
            "outlook_full",
            {
                "message_ids": "message-1,message-2",
                "operation": "enrich",
                "profile": FULL_V1,
            },
        )
    ]:
        pytest.fail(f"Unexpected Mail full mapping: {process.calls!r}")


def test_full_requires_at_least_one_message_id() -> None:
    command = MicrosoftCommand()
    command.crawler_process = cast(CrawlerProcessBase, FakeCrawlerProcess())
    with pytest.raises(UsageError, match="at least one MESSAGE_ID"):
        command.run([], _opts(action="full"))


def test_command_sets_exitcode_when_crawler_bootstrap_fails() -> None:
    command = MicrosoftCommand()
    process = FakeCrawlerProcess()
    process.bootstrap_failed = True
    command.crawler_process = cast(CrawlerProcessBase, process)

    command.run([], _opts(action="delta"))

    if command.exitcode != 1:
        pytest.fail("Expected crawler bootstrap failure to set exit code 1")


def test_command_sets_exitcode_when_spider_integrity_failed() -> None:
    command = MicrosoftCommand()
    process = FakeCrawlerProcess(run_failed=True)
    command.crawler_process = cast(CrawlerProcessBase, process)

    command.run([], _opts(action="delta"))

    if command.exitcode != 1:
        pytest.fail("Expected spider integrity failure to set exit code 1")


def test_command_sets_exitcode_when_final_crawl_status_failed() -> None:
    command = MicrosoftCommand()
    process = FakeCrawlerProcess(final_status="failed")
    command.crawler_process = cast(CrawlerProcessBase, process)

    command.run([], _opts(action="delta"))

    if command.exitcode != 1:
        pytest.fail("Expected final failed status to set exit code 1")


@pytest.mark.parametrize(
    "path",
    [
        ["outlook_discover"],
        ["outlook_delta"],
        ["outlook_full"],
    ],
)
def test_legacy_top_level_commands_are_not_public(path: list[str]) -> None:
    root = Path(__file__).parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "scrapy", *path],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if result.returncode != 2:
        pytest.fail(f"Expected legacy command rejection: {result.stderr}")


def test_identity_gate_failure_uses_microsoft_namespace(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scrapy",
            "microsoft",
            "outlook",
            "mail",
            "discover",
            "-s",
            "MS_GRAPH_AUTH_METHOD=none",
            "-s",
            f"MSGLOOM_DATABASE_URL=sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "-s",
            f"MSGLOOM_RAW_EVIDENCE_DIR={tmp_path / 'raw'}",
            "-L",
            "INFO",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if result.returncode != 1:
        pytest.fail(
            f"Expected identity gate failure, got {result.returncode}:\n"
            + result.stderr
        )
    if "source_identity_failed" not in result.stderr:
        pytest.fail("Expected source identity failure close reason")


def test_mail_sync_dispatches_user_level_workflow(monkeypatch) -> None:
    calls = []

    def fake_sync(command, opts, *, mail_rule_policy) -> None:
        calls.append(
            (
                command,
                opts.page_size,
                opts.reconcile,
                opts.max_enrich,
                mail_rule_policy,
            )
        )

    import message_ingest.commands.microsoft.outlook.mail as mail_command

    monkeypatch.setattr(mail_command, "run_mail_sync", fake_sync)
    command = MicrosoftCommand()
    command.crawler_process = cast(CrawlerProcessBase, FakeCrawlerProcess())
    opts = _opts(action="sync", page_size=40, reconcile=False)
    opts.max_enrich = 12
    command.run([], opts)

    if len(calls) != 1 or calls[0][1:4] != (40, False, 12):
        pytest.fail(f"Unexpected Mail sync dispatch: {calls!r}")
    if calls[0][4].enabled:
        pytest.fail("Rules-disabled default config did not remain disabled")


def test_mail_discover_accepts_config_and_passes_frozen_enabled_policy(
    tmp_path: Path,
) -> None:
    config = _mail_config(tmp_path, enabled=True, private="PRIVATE_DISCOVER_POLICY")
    process = _run(_opts(action="discover", config=config))

    if len(process.calls) != 1:
        pytest.fail(f"Mail discover did not schedule one crawler: {process.calls!r}")
    policy = process.calls[0][1].get("_mail_rule_policy")
    if policy is None or policy.enabled is not True:
        pytest.fail("Mail discover did not pass the enabled frozen policy")
    if "PRIVATE_DISCOVER_POLICY" in repr(_public_calls(process)):
        pytest.fail("Public crawler args exposed private policy content")


def test_mail_delta_accepts_config_but_rejects_enabled_policy_before_crawl(
    tmp_path: Path,
) -> None:
    config = _mail_config(tmp_path, enabled=True)
    command = MicrosoftCommand()
    process = FakeCrawlerProcess()
    command.crawler_process = cast(CrawlerProcessBase, process)

    with pytest.raises(UsageError, match="mail sync"):
        command.run([], _opts(action="delta", config=config))

    if process.calls or process.started:
        pytest.fail("Enabled-policy standalone delta started a crawl")


def test_enabled_mail_sync_rejects_explicit_max_enrich_before_crawl(
    tmp_path: Path,
) -> None:
    config = _mail_config(tmp_path, enabled=True)
    command = MicrosoftCommand()
    process = FakeCrawlerProcess()
    command.crawler_process = cast(CrawlerProcessBase, process)

    with pytest.raises(UsageError, match="max-enrich"):
        command.run([], _opts(action="sync", config=config, max_enrich=5))

    if process.calls or process.started:
        pytest.fail("Enabled-policy sync with max-enrich started a crawl")


def test_enabled_mail_sync_dispatches_rules_aware_planner(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config = _mail_config(tmp_path, enabled=True)
    command = MicrosoftCommand()
    process = FakeCrawlerProcess()
    command.crawler_process = cast(CrawlerProcessBase, process)
    captured: list[object] = []

    import message_ingest.commands.microsoft.outlook.mail as mail_command

    def fake_sync(_command, _opts, *, mail_rule_policy) -> None:
        captured.append(mail_rule_policy)

    monkeypatch.setattr(mail_command, "run_mail_sync", fake_sync)

    command.run([], _opts(action="sync", config=config))

    if len(captured) != 1 or getattr(captured[0], "enabled", False) is not True:
        pytest.fail("Enabled Mail sync did not reach the rules-aware planner")
    if process.calls or process.started:
        pytest.fail("Rules-aware planner dispatch unexpectedly started a direct crawl")


@pytest.mark.parametrize(
    ("section", "resource", "action"),
    (
        ("outlook", "mail", "full"),
        ("outlook", "mail", "folder-delta"),
        ("outlook", "calendar", "discover"),
        ("todo", "discover", None),
        ("onedrive", "discover", None),
        ("contacts", "sync", None),
        ("profile", None, None),
        ("auth", "status", None),
    ),
)
def test_config_is_rejected_outside_mail_policy_paths(
    tmp_path: Path,
    section: str,
    resource: str | None,
    action: str | None,
) -> None:
    config = _mail_config(tmp_path, enabled=False)
    opts = _opts(action=action or "discover", config=config)
    opts.section = section
    opts.resource_or_action = resource
    opts.action = action
    command = MicrosoftCommand()
    command.crawler_process = cast(CrawlerProcessBase, FakeCrawlerProcess())

    with pytest.raises(UsageError, match="--config"):
        command.run([], opts)


def test_mail_config_error_is_privacy_safe_at_scrapy_command_boundary(
    tmp_path: Path,
) -> None:
    private = "PRIVATE_REGEX_771"
    config = tmp_path / "private-customer.toml"
    config.write_text(
        """[acquisition.microsoft.outlook.mail]
enabled = true
[[acquisition.microsoft.outlook.mail.rules]]
id = "r1"
sequence = 1
profile = "full"
[acquisition.microsoft.outlook.mail.rules.conditions]
subject_regex = ["PRIVATE_REGEX_771(?="]
""",
        encoding="utf-8",
    )
    command = MicrosoftCommand()
    command.crawler_process = cast(CrawlerProcessBase, FakeCrawlerProcess())

    with pytest.raises(UsageError) as caught:
        command.run([], _opts(action="discover", config=config))

    rendered = str(caught.value)
    if private in rendered or str(config) in rendered:
        pytest.fail("Scrapy command boundary leaked private config material")
    if "subject_regex" not in rendered or "msgloom-regex-v1" not in rendered:
        pytest.fail(f"Safe Mail config diagnostic lost useful context: {rendered!r}")


@pytest.mark.parametrize("action", ["discover", "full"])
def test_mail_unqualified_actions_reject_jobdir_before_dispatch(action):
    """Reject shared queue state at the public command boundary."""
    from scrapy.settings import Settings

    command = MicrosoftCommand()
    command.settings = Settings({"JOBDIR": "/tmp/mail-unqualified"})
    process = FakeCrawlerProcess()
    command.crawler_process = cast(CrawlerProcessBase, process)
    with pytest.raises(UsageError, match="does not support JOBDIR"):
        command.run(
            [], _opts(action=action, message_ids=["m1"] if action == "full" else [])
        )
    if process.calls:
        pytest.fail("JOBDIR rejection happened after scheduling a crawler")
