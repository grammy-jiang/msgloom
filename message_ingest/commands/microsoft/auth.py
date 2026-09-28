"""Offline Microsoft authentication management command dispatch."""

from __future__ import annotations

import argparse
import json
from typing import Any

from scrapy.exceptions import UsageError

from message_ingest.commands.microsoft.validation import reject_options
from microsoft_graph.auth.management import (
    MicrosoftAuthStatus,
    clear_local_token_cache,
    inspect_auth_status,
)


def dispatch_auth(command: Any, opts: argparse.Namespace) -> None:
    """Dispatch offline authentication management actions."""
    action = opts.resource_or_action
    if opts.action is not None or opts.message_ids:
        raise UsageError("use 'microsoft auth {status,clear}'")
    if action == "status":
        reject_options(opts, allowed={"json"})
        _auth_status(command, opts)
        return
    if action == "clear":
        reject_options(opts, allowed={"yes"})
        _auth_clear(command, opts)
        return
    raise UsageError("use 'microsoft auth {status,clear}'")


def _auth_status(command: Any, opts: argparse.Namespace) -> None:
    status = inspect_auth_status(_settings(command))
    if opts.json:
        print(json.dumps(status.as_dict(), indent=2, sort_keys=True))
        return
    print(format_status(status))


def _auth_clear(command: Any, opts: argparse.Namespace) -> None:
    if not opts.yes:
        raise UsageError(
            "microsoft auth clear requires --yes; this removes only local "
            "cached credentials"
        )
    removed = clear_local_token_cache(_settings(command))
    if removed:
        print(
            "Local Microsoft credentials cleared. Microsoft-side consent "
            "was not revoked. Any persisted source-account binding remains. "
            "If one exists, the next sign-in must use the same bound account "
            "unless that binding is separately migrated."
        )
        return
    print("No local Microsoft token cache exists; nothing was changed.")


def _settings(command: Any):
    if command.settings is None:
        raise RuntimeError("Scrapy did not initialize command settings")
    return command.settings


def format_status(status: MicrosoftAuthStatus) -> str:
    """Render concise operator-facing diagnostics without secret material."""
    scopes = ", ".join(status.cached_scopes) if status.cached_scopes else "none"
    applications = (
        ", ".join(status.cached_applications) if status.cached_applications else "none"
    )
    lines = [
        "Microsoft authentication status",
        f"Status: {status.status}",
        f"Application mode: {status.application_mode}",
        f"Application: {status.application_name}",
        f"Client ID: {status.client_id or 'not configured'}",
        f"Authentication method: {status.auth_method}",
        f"Authority: {status.authority}",
        f"Token cache: {status.token_cache}",
        f"Token cache exists: {'yes' if status.cache_exists else 'no'}",
        (
            "Token cache valid: "
            + (
                "unknown"
                if status.cache_valid is None
                else ("yes" if status.cache_valid else "no")
            )
        ),
        (
            "Cache matches configured application: "
            f"{'yes' if status.cache_matches_configured_application else 'no'}"
        ),
        f"Cached accounts: {status.cached_account_count}",
        f"Cached applications: {applications}",
        f"Cached resource scopes: {scopes}",
    ]
    if status.warnings:
        lines.append("")
        lines.append("Warnings:")
        lines.extend(f"- {message}" for message in status.warnings)
    if status.remediation:
        lines.append("")
        lines.append("What to do:")
        lines.extend(f"- {message}" for message in status.remediation)
    return "\n".join(lines)


__all__ = ["dispatch_auth", "format_status"]
