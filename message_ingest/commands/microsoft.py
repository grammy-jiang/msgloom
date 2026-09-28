"""Single public namespace for Microsoft acquisition and authentication."""

from __future__ import annotations

import argparse
import json
from datetime import datetime

from scrapy.commands import ScrapyCommand
from scrapy.exceptions import UsageError

from message_ingest.acquisition.microsoft.outlook.email.profile import FULL_V1
from message_ingest.commands._common import (
    non_negative_int,
    page_size,
    require_no_positional_args,
    run_graph,
)
from message_ingest.commands._microsoft_calendar import dispatch_calendar
from microsoft_graph.auth.management import (
    MicrosoftAuthStatus,
    clear_local_token_cache,
    inspect_auth_status,
)


def _aware_datetime(value: str) -> str:
    """Require a timezone-aware ISO-8601 datetime while preserving text."""
    cleaned = value.strip()
    if cleaned != value or not cleaned:
        raise argparse.ArgumentTypeError(
            "datetime must be non-empty with no surrounding whitespace"
        )
    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("datetime must be valid ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("datetime must include a timezone offset")
    return cleaned


class Command(ScrapyCommand):
    """Expose every Microsoft product below one public command namespace."""

    requires_project = True
    requires_crawler_process = True

    def syntax(self) -> str:
        return (
            "{profile,auth,outlook} [RESOURCE_OR_ACTION] [ACTION] "
            "[RESOURCE_ID ...] [options]"
        )

    def short_desc(self) -> str:
        return "Manage Microsoft acquisition and authentication"

    def long_desc(self) -> str:
        return (
            "Use one Microsoft namespace for account profile, authentication "
            "management, and Outlook Mail/Calendar acquisition. Operations that "
            "need Microsoft authentication run through the normal Scrapy Graph "
            "lifecycle."
        )

    def add_options(self, parser: argparse.ArgumentParser) -> None:
        """Add hierarchy selectors and resource-specific options."""
        super().add_options(parser)
        parser.add_argument(
            "section",
            choices=("profile", "auth", "outlook"),
            help="Microsoft account, authentication, or product area",
        )
        parser.add_argument(
            "resource_or_action",
            nargs="?",
            metavar="RESOURCE_OR_ACTION",
            help="auth action or Outlook resource",
        )
        parser.add_argument(
            "action",
            nargs="?",
            metavar="ACTION",
            help="Outlook resource action",
        )
        parser.add_argument(
            "message_ids",
            nargs="*",
            metavar="RESOURCE_ID",
            help=(
                "message IDs for 'outlook mail full' or event IDs for "
                "'outlook calendar full'"
            ),
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="print 'auth status' output as privacy-safe JSON",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="confirm 'auth clear' removal of the local token cache",
        )
        parser.add_argument(
            "--folder",
            default=None,
            metavar="FOLDER_ID",
            help="Mail discovery folder; omitted scans the whole mailbox",
        )
        parser.add_argument(
            "--page-size",
            type=page_size,
            default=None,
            metavar="N",
            help="Graph page size, 1..1000",
        )
        parser.add_argument(
            "--max-pages",
            type=non_negative_int,
            default=None,
            metavar="N",
            help="Mail discovery page limit; 0 means unlimited",
        )
        parser.add_argument(
            "--reconcile",
            action=argparse.BooleanOptionalAction,
            default=None,
            help="enable or disable whole-mailbox delta reconciliation",
        )
        parser.add_argument(
            "--operation",
            choices=("enrich", "refresh"),
            default=None,
            help="Mail full acquisition operation",
        )
        parser.add_argument(
            "--acquisition-profile",
            dest="acquisition_profile",
            choices=(FULL_V1,),
            default=None,
            help="Mail full acquisition profile",
        )
        parser.add_argument(
            "--start",
            type=_aware_datetime,
            default=None,
            metavar="ISO_DATETIME",
            help="Calendar window inclusive start with timezone offset",
        )
        parser.add_argument(
            "--end",
            type=_aware_datetime,
            default=None,
            metavar="ISO_DATETIME",
            help="Calendar window end with timezone offset",
        )
        parser.add_argument(
            "--calendar",
            default=None,
            metavar="CALENDAR_ID",
            help="Calendar ID; omitted selects the default calendar",
        )

    def run(self, args: list[str], opts: argparse.Namespace) -> None:
        """Dispatch the selected Microsoft hierarchy path."""
        require_no_positional_args(args)
        if opts.section == "profile":
            self._profile(opts)
            return
        if opts.section == "auth":
            self._auth(opts)
            return
        if opts.section == "outlook":
            self._outlook(opts)
            return
        raise UsageError("unsupported Microsoft command path")

    def _profile(self, opts: argparse.Namespace) -> None:
        """Run profile acquisition through the shared Scrapy Graph lifecycle."""
        self._require_path_tail(opts, resource=None, action=None)
        self._reject_options(opts, allowed=set())
        crawler = run_graph(self, "microsoft_profile", {})
        if self.exitcode:
            return

        profile = getattr(crawler.spider, "profile", None)
        stats = crawler.stats
        evidence_ready = int(
            stats.get_value("msgloom/evidence/response_persisted_count", 0) or 0
        ) + int(stats.get_value("msgloom/evidence/cache_link_count", 0) or 0)
        if not isinstance(profile, dict) or evidence_ready != 1:
            self.exitcode = 1
            return
        print(json.dumps(profile, ensure_ascii=False, sort_keys=True))

    def _auth(self, opts: argparse.Namespace) -> None:
        """Dispatch offline authentication management actions."""
        action = opts.resource_or_action
        if opts.action is not None or opts.message_ids:
            raise UsageError("use 'microsoft auth {status,clear}'")
        if action == "status":
            self._reject_options(opts, allowed={"json"})
            self._auth_status(opts)
            return
        if action == "clear":
            self._reject_options(opts, allowed={"yes"})
            self._auth_clear(opts)
            return
        raise UsageError("use 'microsoft auth {status,clear}'")

    def _outlook(self, opts: argparse.Namespace) -> None:
        """Dispatch Outlook resource acquisition through the shared runner."""
        resource = opts.resource_or_action
        if resource == "mail":
            self._outlook_mail(opts)
            return
        if resource == "calendar":
            self._outlook_calendar(opts)
            return
        raise UsageError("use 'microsoft outlook {mail,calendar} ACTION'")

    def _outlook_mail(self, opts: argparse.Namespace) -> None:
        """Map Outlook Mail actions to existing spiders."""
        if opts.action == "discover":
            if opts.message_ids:
                raise UsageError("Mail discover does not accept MESSAGE_ID values")
            self._reject_options(
                opts,
                allowed={"folder", "page_size", "max_pages"},
            )
            run_graph(
                self,
                "outlook_discover",
                {
                    "folder": opts.folder or "",
                    "page_size": str(opts.page_size or 25),
                    "max_pages": str(0 if opts.max_pages is None else opts.max_pages),
                },
            )
            return
        if opts.action == "delta":
            if opts.message_ids:
                raise UsageError("Mail delta does not accept MESSAGE_ID values")
            self._reject_options(
                opts,
                allowed={"page_size", "reconcile"},
            )
            reconcile = True if opts.reconcile is None else opts.reconcile
            run_graph(
                self,
                "outlook_delta",
                {
                    "page_size": str(opts.page_size or 25),
                    "reconcile_global": "1" if reconcile else "0",
                },
            )
            return
        if opts.action == "full":
            self._reject_options(
                opts,
                allowed={"operation", "acquisition_profile"},
            )
            message_ids = tuple(
                dict.fromkeys(
                    cleaned for value in opts.message_ids if (cleaned := value.strip())
                )
            )
            if not message_ids:
                raise UsageError("at least one MESSAGE_ID is required")
            run_graph(
                self,
                "outlook_full",
                {
                    "message_ids": ",".join(message_ids),
                    "operation": opts.operation or "refresh",
                    "profile": opts.acquisition_profile or FULL_V1,
                },
            )
            return
        raise UsageError("use 'microsoft outlook mail {discover,delta,full}'")

    def _outlook_calendar(self, opts: argparse.Namespace) -> None:
        """Map Outlook Calendar actions to their resource-specific dispatcher."""
        dispatch_calendar(self, opts, self._reject_options)

    def _auth_status(self, opts: argparse.Namespace) -> None:
        """Print privacy-safe local authentication diagnostics."""
        status = inspect_auth_status(self._settings())
        if opts.json:
            print(json.dumps(status.as_dict(), indent=2, sort_keys=True))
            return
        print(_format_status(status))

    def _auth_clear(self, opts: argparse.Namespace) -> None:
        """Remove only local cached credentials after explicit confirmation."""
        if not opts.yes:
            raise UsageError(
                "microsoft auth clear requires --yes; this removes only local "
                "cached credentials"
            )
        removed = clear_local_token_cache(self._settings())
        if removed:
            print(
                "Local Microsoft credentials cleared. Microsoft-side consent "
                "was not revoked. Any persisted source-account binding remains. "
                "If one exists, the next sign-in must use the same bound account "
                "unless that binding is separately migrated."
            )
            return
        print("No local Microsoft token cache exists; nothing was changed.")

    def _settings(self):
        """Return initialized Scrapy settings for offline management actions."""
        if self.settings is None:
            raise RuntimeError("Scrapy did not initialize command settings")
        return self.settings

    @staticmethod
    def _require_path_tail(
        opts: argparse.Namespace,
        *,
        resource: str | None,
        action: str | None,
    ) -> None:
        """Reject hierarchy segments that do not belong to the selected path."""
        if opts.resource_or_action != resource or opts.action != action:
            raise UsageError("use 'microsoft profile' with no extra path")
        if opts.message_ids:
            raise UsageError("microsoft profile does not accept MESSAGE_ID values")

    @staticmethod
    def _reject_options(
        opts: argparse.Namespace,
        *,
        allowed: set[str],
    ) -> None:
        """Reject options that do not belong to the selected command path."""
        values = {
            "json": opts.json,
            "yes": opts.yes,
            "folder": opts.folder,
            "page_size": opts.page_size,
            "max_pages": opts.max_pages,
            "reconcile": opts.reconcile,
            "operation": opts.operation,
            "acquisition_profile": opts.acquisition_profile,
            "start": opts.start,
            "end": opts.end,
            "calendar": opts.calendar,
        }
        used = [
            name
            for name, value in values.items()
            if name not in allowed and value not in (None, False, "")
        ]
        if used:
            rendered = ", ".join(f"--{name.replace('_', '-')}" for name in used)
            raise UsageError(
                f"option(s) not valid for this Microsoft command: {rendered}"
            )


def _format_status(status: MicrosoftAuthStatus) -> str:
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
