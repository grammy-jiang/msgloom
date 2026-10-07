"""Verify privacy-safe Microsoft authentication management commands."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pytest
from scrapy.exceptions import UsageError
from scrapy.settings import Settings

import message_ingest.settings as project_settings
from message_ingest.commands.microsoft import Command as MicrosoftCommand
from microsoft_graph.auth.management import (
    MICROSOFT_GRAPH_CLI_CLIENT_ID,
    inspect_auth_status,
)

_SECRET_TOKEN = "do-not-print-token"
_SECRET_USERNAME = "private-person@example.com"


def _settings(
    tmp_path: Path,
    *,
    client_id: str = "",
    cache: dict | None = None,
) -> Settings:
    settings = Settings()
    settings.setmodule(project_settings, priority="project")
    settings.set("MS_GRAPH_CLIENT_ID", client_id, priority="cmdline")
    path = tmp_path / "token-cache.json"
    settings.set("MS_GRAPH_TOKEN_CACHE", str(path), priority="cmdline")
    if cache is not None:
        path.write_text(json.dumps(cache), encoding="utf-8")
        os.chmod(path, 0o600)
    return settings


def _development_cache() -> dict:
    return {
        "AccessToken": {
            "access": {
                "client_id": MICROSOFT_GRAPH_CLI_CLIENT_ID,
                "target": "Mail.Read openid profile",
                "secret": _SECRET_TOKEN,
            }
        },
        "RefreshToken": {
            "refresh": {
                "client_id": MICROSOFT_GRAPH_CLI_CLIENT_ID,
                "target": "Mail.Read openid profile",
                "secret": _SECRET_TOKEN,
            }
        },
        "Account": {
            "account": {
                "username": _SECRET_USERNAME,
                "home_account_id": "opaque-account-key",
            }
        },
        "AppMetadata": {
            "app": {
                "client_id": MICROSOFT_GRAPH_CLI_CLIENT_ID,
            }
        },
    }


def test_status_recognizes_development_application_and_scopes(tmp_path: Path) -> None:
    status = inspect_auth_status(
        _settings(
            tmp_path,
            client_id=MICROSOFT_GRAPH_CLI_CLIENT_ID,
            cache=_development_cache(),
        )
    )

    if status.status != "configured_cached":
        pytest.fail(f"Unexpected status: {status.status}")
    if status.application_mode != "development":
        pytest.fail("Expected Graph CLI client to be classified as development")
    if status.cached_scopes != ("Mail.Read",):
        pytest.fail(f"Unexpected cached scopes: {status.cached_scopes!r}")
    if not status.cache_matches_configured_application:
        pytest.fail("Expected cache to match the configured development app")
    if not any("consent screens" in value.lower() for value in status.warnings):
        pytest.fail("Expected development consent-name warning")


def test_status_explains_unconfigured_client_with_existing_dev_cache(
    tmp_path: Path,
) -> None:
    status = inspect_auth_status(
        _settings(tmp_path, client_id="", cache=_development_cache())
    )

    if status.status != "unconfigured":
        pytest.fail("Expected missing Client ID to remain unconfigured")
    if status.cached_scopes != ("Mail.Read",):
        pytest.fail("Expected single cached application's scopes to be visible")
    if not any(
        "Microsoft Graph Command Line Tools (development)" == value
        for value in status.cached_applications
    ):
        pytest.fail("Expected cached development application identification")
    if not any("no Client ID" in value for value in status.warnings):
        pytest.fail("Expected cache-without-client configuration warning")


def test_status_marks_cache_for_different_application(tmp_path: Path) -> None:
    status = inspect_auth_status(
        _settings(
            tmp_path,
            client_id="11111111-2222-3333-4444-555555555555",
            cache=_development_cache(),
        )
    )

    if status.status != "configured_cache_mismatch":
        pytest.fail("Expected configured app/cache mismatch")
    if status.cached_scopes:
        pytest.fail("Expected scopes for another app not to imply current consent")
    if not any("different Microsoft application" in value for value in status.warnings):
        pytest.fail("Expected actionable cache mismatch warning")


def test_status_command_never_prints_token_or_username(tmp_path: Path, capsys) -> None:
    command = MicrosoftCommand()
    command.settings = _settings(
        tmp_path,
        client_id=MICROSOFT_GRAPH_CLI_CLIENT_ID,
        cache=_development_cache(),
    )
    command.run([], _command_opts(section="auth", resource_or_action="status"))

    output = capsys.readouterr().out
    if "Microsoft Graph Command Line Tools" not in output:
        pytest.fail("Expected recognizable development application name")
    if "Mail.Read" not in output:
        pytest.fail("Expected cached resource scope")
    if _SECRET_TOKEN in output or _SECRET_USERNAME in output:
        pytest.fail("Authentication status leaked credential/account material")


def test_status_command_json_is_machine_readable(tmp_path: Path, capsys) -> None:
    command = MicrosoftCommand()
    command.settings = _settings(tmp_path)
    command.run(
        [], _command_opts(section="auth", resource_or_action="status", json_output=True)
    )

    payload = json.loads(capsys.readouterr().out)
    if payload["status"] != "unconfigured":
        pytest.fail("Expected JSON status to report unconfigured application")
    if payload["application_mode"] != "unconfigured":
        pytest.fail("Expected JSON application classification")
    if not any("MSGLOOM_MS_CLIENT_ID" in text for text in payload["remediation"]):
        pytest.fail("The product command must explain its environment setting")
    if not any(
        "scrapy microsoft auth status" in text for text in payload["remediation"]
    ):
        pytest.fail("The product command must retain local CLI guidance")


def test_clear_requires_confirmation_and_preserves_cache(tmp_path: Path) -> None:
    settings = _settings(
        tmp_path,
        client_id=MICROSOFT_GRAPH_CLI_CLIENT_ID,
        cache=_development_cache(),
    )
    command = MicrosoftCommand()
    command.settings = settings

    with pytest.raises(UsageError, match="requires --yes"):
        command.run([], _command_opts(section="auth", resource_or_action="clear"))
    if not Path(settings["MS_GRAPH_TOKEN_CACHE"]).exists():
        pytest.fail("Unconfirmed clear must not remove credentials")


def test_clear_removes_only_local_cache(tmp_path: Path, capsys) -> None:
    settings = _settings(
        tmp_path,
        client_id=MICROSOFT_GRAPH_CLI_CLIENT_ID,
        cache=_development_cache(),
    )
    path = Path(settings["MS_GRAPH_TOKEN_CACHE"])
    command = MicrosoftCommand()
    command.settings = settings
    command.run([], _command_opts(section="auth", resource_or_action="clear", yes=True))

    if path.exists():
        pytest.fail("Expected confirmed clear to remove local token cache")
    output = capsys.readouterr().out
    if "consent was not revoked" not in output:
        pytest.fail("Expected clear command to explain remote consent remains")
    if "source-account binding remains" not in output:
        pytest.fail("Expected clear command to explain source binding remains")


def test_status_does_not_treat_app_metadata_as_cached_credentials(
    tmp_path: Path,
) -> None:
    cache = {
        "AppMetadata": {
            "app": {
                "client_id": MICROSOFT_GRAPH_CLI_CLIENT_ID,
            }
        }
    }
    status = inspect_auth_status(
        _settings(
            tmp_path,
            client_id=MICROSOFT_GRAPH_CLI_CLIENT_ID,
            cache=cache,
        )
    )

    if status.status != "configured_no_credentials":
        pytest.fail(f"Unexpected metadata-only status: {status.status}")
    if status.cache_matches_configured_application:
        pytest.fail("App metadata alone must not imply cached credentials")
    if status.cached_scopes:
        pytest.fail("App metadata alone must not imply delegated scopes")


def test_status_reports_invalid_cache_distinctly(tmp_path: Path) -> None:
    settings = _settings(
        tmp_path,
        client_id=MICROSOFT_GRAPH_CLI_CLIENT_ID,
    )
    path = Path(settings["MS_GRAPH_TOKEN_CACHE"])
    path.write_text("not-json", encoding="utf-8")
    os.chmod(path, 0o600)

    status = inspect_auth_status(settings)

    if status.status != "configured_cache_invalid":
        pytest.fail(f"Unexpected invalid-cache status: {status.status}")
    if status.cache_valid is not False:
        pytest.fail("Expected invalid cache validity fact")
    if not any("could not be read" in value for value in status.warnings):
        pytest.fail("Expected invalid-cache warning")


def test_microsoft_command_profile_uses_shared_graph_runner(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    payload = {"id": "user-1", "displayName": "Example User"}

    class FakeStats:
        @staticmethod
        def get_value(key: str, default=0):
            if key == "msgloom/evidence/response_persisted_count":
                return 1
            return default

    class FakeCrawler:
        spider = type("SpiderResult", (), {"profile": payload})()
        stats = FakeStats()

    calls: list[tuple[str, dict]] = []

    def fake_run_graph(command, spider_name, spider_args):
        calls.append((spider_name, spider_args))
        return FakeCrawler()

    import message_ingest.commands.microsoft.profile as profile_command

    monkeypatch.setattr(profile_command, "run_graph", fake_run_graph)
    command = MicrosoftCommand()
    command.exitcode = 0
    command.settings = _settings(tmp_path)
    command.run(
        [],
        _command_opts(section="profile"),
    )

    if calls != [("microsoft_profile", {})]:
        pytest.fail(f"Unexpected Graph runner call: {calls!r}")
    if json.loads(capsys.readouterr().out) != payload:
        pytest.fail("Expected profile JSON from lifecycle-backed crawl")


def _command_opts(
    *,
    section: str,
    resource_or_action: str | None = None,
    action: str | None = None,
    message_ids: list[str] | None = None,
    json_output: bool = False,
    yes: bool = False,
) -> argparse.Namespace:
    return argparse.Namespace(
        section=section,
        resource_or_action=resource_or_action,
        action=action,
        message_ids=message_ids or [],
        json=json_output,
        yes=yes,
        folder=None,
        page_size=None,
        max_pages=None,
        reconcile=None,
        operation=None,
        max_enrich=None,
        acquisition_profile=None,
        start=None,
        end=None,
        calendar=None,
    )
