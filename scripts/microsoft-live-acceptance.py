#!/usr/bin/env python3
"""Run a bounded, read-only Microsoft Graph live acceptance workflow."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import func, select

from message_ingest.acquisition.microsoft.outlook.calendar.planner import (
    pending_full_v1_targets,
)
from message_ingest.acquisition.microsoft.outlook.email.profile import (
    surface_is_complete as mail_surface_is_complete,
)
from message_ingest.catalog import Catalog, RawHttpEvidence
from message_ingest.catalog.stores.microsoft.outlook.calendar import (
    OutlookCalendarStore,
)
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore


@dataclass(slots=True)
class PhaseResult:
    name: str
    status: str
    returncode: int | None = None
    detail: str | None = None


@dataclass(slots=True)
class AcceptanceSummary:
    schema_version: int
    started_at: str
    finished_at: str
    output_dir: str
    source_id: str
    dry_run: bool
    delegated_target: bool
    phases: list[PhaseResult]
    checks: dict[str, bool | int | str]
    overall: str


def _aware(value: str) -> str:
    cleaned = value.strip()
    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be valid ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("must include a timezone offset")
    return cleaned


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run bounded read-only Microsoft Graph acceptance against an isolated "
            "local catalog. This script is operator-only and is not a CI test."
        )
    )
    parser.add_argument("--calendar-start", type=_aware, required=True)
    parser.add_argument("--calendar-end", type=_aware, required=True)
    parser.add_argument("--confirm-live", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--source-id", default="microsoft-live-acceptance")
    parser.add_argument(
        "--mailbox",
        default=None,
        metavar="USER_ID_OR_UPN",
        help="optional delegated/shared Outlook mailbox; prefer an Entra object ID",
    )
    parser.add_argument("--mail-page-size", type=int, default=10)
    parser.add_argument("--calendar-page-size", type=int, default=50)
    parser.add_argument("--require-mail-message", action="store_true")
    parser.add_argument("--require-calendar-event", action="store_true")
    return parser


def _output_dir(value: Path | None) -> Path:
    if value is not None:
        return value.resolve()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return (ROOT / "var" / "live-acceptance" / stamp).resolve()


def _settings(output_dir: Path, source_id: str) -> list[str]:
    return [
        "-s",
        f"MSGLOOM_DATABASE_URL=sqlite:///{output_dir / 'catalog.sqlite3'}",
        "-s",
        f"MSGLOOM_RAW_EVIDENCE_DIR={output_dir / 'raw-evidence'}",
        "-s",
        f"MSGLOOM_SOURCE_ID={source_id}",
        "-s",
        "MSGLOOM_CATALOG_ENABLED=True",
        "-s",
        "MSGLOOM_RAW_EVIDENCE_ENABLED=True",
        "-s",
        "HTTPCACHE_ENABLED=False",
    ]


def _command(*args: str, settings: list[str]) -> list[str]:
    return [sys.executable, "-m", "scrapy", "microsoft", *args, *settings]


def _run_phase(
    phases: list[PhaseResult],
    name: str,
    command: list[str],
    *,
    dry_run: bool,
) -> bool:
    if dry_run:
        phases.append(PhaseResult(name=name, status="planned"))
        print(f"PLAN {name}")
        return True
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        phases.append(
            PhaseResult(
                name=name,
                status="failed",
                returncode=result.returncode,
                detail="command exited non-zero; inspect operator stderr",
            )
        )
        sys.stderr.write(result.stderr)
        return False
    phases.append(PhaseResult(name=name, status="passed", returncode=0))
    return True


def _database_url(output_dir: Path) -> str:
    return f"sqlite:///{output_dir / 'catalog.sqlite3'}"


def _first_mail_message(output_dir: Path, source_id: str) -> str | None:
    catalog = Catalog(_database_url(output_dir))
    try:
        ids = OutlookMailStore(catalog, source_id=source_id).list_message_ids()
        return ids[0] if ids else None
    finally:
        catalog.close()


def _first_calendar_event(output_dir: Path, source_id: str) -> tuple[str, str] | None:
    catalog = Catalog(_database_url(output_dir))
    try:
        targets = OutlookCalendarStore(
            catalog, source_id=source_id
        ).list_event_targets()
        if not targets:
            return None
        event_id, calendar_id, _version = targets[0]
        return event_id, calendar_id
    finally:
        catalog.close()


def _validate(
    output_dir: Path,
    source_id: str,
    *,
    mail_message_id: str | None,
    calendar_event: tuple[str, str] | None,
) -> dict[str, bool | int | str]:
    catalog = Catalog(_database_url(output_dir))
    try:
        checks: dict[str, bool | int | str] = {}
        with catalog.Session() as session:
            checks["raw_evidence_count"] = int(
                session.scalar(select(func.count()).select_from(RawHttpEvidence)) or 0
            )
        mail = OutlookMailStore(catalog, source_id=source_id)
        checks["mail_message_selected"] = mail_message_id is not None
        if mail_message_id is not None:
            surfaces = mail.get_surfaces(message_id=mail_message_id)
            checks["mail_full_v1_complete"] = all(
                mail_surface_is_complete(surfaces, surface)
                for surface in ("detail", "mime", "attachments")
            )
        else:
            checks["mail_full_v1_complete"] = False

        calendar = OutlookCalendarStore(catalog, source_id=source_id)
        checks["calendar_event_selected"] = calendar_event is not None
        if calendar_event is not None:
            event_id, _calendar_id = calendar_event
            checks["calendar_full_v1_complete"] = not bool(
                pending_full_v1_targets(calendar, event_ids=(event_id,))
            )
        else:
            checks["calendar_full_v1_complete"] = False
        return checks
    finally:
        catalog.close()


def _finish(
    output_dir: Path,
    args: argparse.Namespace,
    started: datetime,
    phases: list[PhaseResult],
    checks: dict[str, bool | int | str],
    *,
    overall: str,
) -> int:
    summary = AcceptanceSummary(
        schema_version=1,
        started_at=started.isoformat(),
        finished_at=datetime.now(UTC).isoformat(),
        output_dir=str(output_dir),
        source_id=args.source_id,
        dry_run=bool(args.dry_run),
        delegated_target=bool(args.mailbox),
        phases=phases,
        checks=checks,
        overall=overall,
    )
    payload: dict[str, Any] = asdict(summary)
    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "acceptance.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n"
        )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if overall in {"passed", "planned"} else 1


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if datetime.fromisoformat(args.calendar_start) >= datetime.fromisoformat(
        args.calendar_end
    ):
        raise SystemExit("--calendar-start must be earlier than --calendar-end")
    if not args.dry_run and not args.confirm_live:
        raise SystemExit("live execution requires --confirm-live")
    if not 1 <= args.mail_page_size <= 1000:
        raise SystemExit("--mail-page-size must be between 1 and 1000")
    if not 1 <= args.calendar_page_size <= 1000:
        raise SystemExit("--calendar-page-size must be between 1 and 1000")
    if args.mailbox is not None and (
        not args.mailbox or args.mailbox != args.mailbox.strip()
    ):
        raise SystemExit("--mailbox must be non-empty without surrounding whitespace")

    mailbox_args = ["--mailbox", args.mailbox] if args.mailbox else []
    started = datetime.now(UTC)
    output_dir = _output_dir(args.output_dir)
    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=False)
    settings = _settings(output_dir, args.source_id)
    phases: list[PhaseResult] = []

    for name, command in [
        ("profile", _command("profile", settings=settings)),
        (
            "mail-discover",
            _command(
                "outlook",
                "mail",
                "discover",
                "--page-size",
                str(args.mail_page_size),
                "--max-pages",
                "1",
                *mailbox_args,
                settings=settings,
            ),
        ),
    ]:
        if not _run_phase(phases, name, command, dry_run=args.dry_run):
            return _finish(output_dir, args, started, phases, {}, overall="failed")

    mail_message_id = (
        None if args.dry_run else _first_mail_message(output_dir, args.source_id)
    )
    if mail_message_id is None:
        phases.append(
            PhaseResult("mail-full", "skipped", detail="no discovered message")
        )
        if args.require_mail_message and not args.dry_run:
            return _finish(
                output_dir,
                args,
                started,
                phases,
                {"mail_message_selected": False},
                overall="failed",
            )
    elif not _run_phase(
        phases,
        "mail-full",
        _command(
            "outlook",
            "mail",
            "full",
            mail_message_id,
            "--operation",
            "refresh",
            *mailbox_args,
            settings=settings,
        ),
        dry_run=args.dry_run,
    ):
        return _finish(output_dir, args, started, phases, {}, overall="failed")

    for name, command in [
        (
            "calendar-discover",
            _command(
                "outlook",
                "calendar",
                "discover",
                "--page-size",
                str(args.calendar_page_size),
                *mailbox_args,
                settings=settings,
            ),
        ),
        (
            "calendar-window",
            _command(
                "outlook",
                "calendar",
                "window",
                "--start",
                args.calendar_start,
                "--end",
                args.calendar_end,
                "--page-size",
                str(args.calendar_page_size),
                *mailbox_args,
                settings=settings,
            ),
        ),
    ]:
        if not _run_phase(phases, name, command, dry_run=args.dry_run):
            return _finish(output_dir, args, started, phases, {}, overall="failed")

    calendar_event = (
        None if args.dry_run else _first_calendar_event(output_dir, args.source_id)
    )
    if calendar_event is None:
        phases.append(
            PhaseResult(
                "calendar-full", "skipped", detail="no event in selected window"
            )
        )
        if args.require_calendar_event and not args.dry_run:
            return _finish(
                output_dir,
                args,
                started,
                phases,
                {"calendar_event_selected": False},
                overall="failed",
            )
    else:
        event_id, calendar_id = calendar_event
        full_args = ["outlook", "calendar", "full", event_id]
        if calendar_id and calendar_id != "default":
            full_args.extend(["--calendar", calendar_id])
        full_args.extend(["--operation", "refresh", *mailbox_args])
        if not _run_phase(
            phases,
            "calendar-full",
            _command(*full_args, settings=settings),
            dry_run=args.dry_run,
        ):
            return _finish(output_dir, args, started, phases, {}, overall="failed")

    checks = (
        {}
        if args.dry_run
        else _validate(
            output_dir,
            args.source_id,
            mail_message_id=mail_message_id,
            calendar_event=calendar_event,
        )
    )
    overall = "planned" if args.dry_run else "passed"
    if not args.dry_run:
        mandatory = [bool(checks.get("raw_evidence_count", 0))]
        if mail_message_id is not None:
            mandatory.append(bool(checks.get("mail_full_v1_complete")))
        if calendar_event is not None:
            mandatory.append(bool(checks.get("calendar_full_v1_complete")))
        if not all(mandatory):
            overall = "failed"
    return _finish(output_dir, args, started, phases, checks, overall=overall)


if __name__ == "__main__":
    raise SystemExit(main())
