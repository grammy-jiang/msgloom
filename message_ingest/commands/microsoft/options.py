"""Argument definitions for the unified Microsoft command."""

from __future__ import annotations

import argparse
from typing import Any

from message_ingest.acquisition.microsoft.outlook.calendar.profile import (
    FULL_V1 as CALENDAR_FULL_V1,
)
from message_ingest.acquisition.microsoft.outlook.email.profile import (
    FULL_V1 as MAIL_FULL_V1,
)
from message_ingest.commands._common import non_negative_int, page_size
from microsoft_graph.protocol.calendar import parse_calendar_datetime


def aware_datetime(value: str) -> str:
    """Require a timezone-aware ISO-8601 datetime while preserving text."""
    cleaned = value.strip()
    if cleaned != value or not cleaned:
        raise argparse.ArgumentTypeError(
            "datetime must be non-empty with no surrounding whitespace"
        )
    try:
        parse_calendar_datetime(cleaned)
    except ValueError as exc:
        message = (
            str(exc)
            .replace(
                "Calendar window values must be valid ISO-8601 datetimes",
                "datetime must be valid ISO-8601",
            )
            .replace(
                "Calendar window datetimes must include an offset",
                "datetime must include a timezone offset",
            )
        )
        raise argparse.ArgumentTypeError(message) from exc
    return cleaned


def add_microsoft_options(command: Any, parser: argparse.ArgumentParser) -> None:
    """Add hierarchy selectors and resource-specific options."""
    parser.add_argument(
        "section",
        choices=("profile", "auth", "outlook", "todo", "onedrive", "contacts"),
        help="Microsoft account, authentication, or product area",
    )
    parser.add_argument(
        "resource_or_action",
        nargs="?",
        metavar="RESOURCE_OR_ACTION",
        help="auth/To Do/OneDrive/Contacts action or Outlook resource",
    )
    parser.add_argument(
        "action",
        nargs="?",
        metavar="ACTION",
        help="Outlook resource action or first OneDrive content item ID",
    )
    parser.add_argument(
        "message_ids",
        nargs="*",
        metavar="RESOURCE_ID",
        help=(
            "message IDs for 'outlook mail full' or event IDs for "
            "'outlook calendar full', or item IDs for 'onedrive content'"
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
        "--mailbox",
        default=None,
        metavar="USER_ID_OR_UPN",
        help=(
            "target a delegated/shared Outlook mailbox; omitted uses the "
            "signed-in mailbox. Prefer an immutable Entra object ID."
        ),
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
        help="resource-specific full acquisition operation",
    )
    parser.add_argument(
        "--acquisition-profile",
        dest="acquisition_profile",
        choices=(MAIL_FULL_V1, CALENDAR_FULL_V1),
        default=None,
        help="resource-specific full acquisition profile",
    )
    parser.add_argument(
        "--max-enrich",
        type=non_negative_int,
        default=None,
        metavar="N",
        help=(
            "limit planner-selected enrichment backlog; 0 or omitted means unlimited"
        ),
    )
    parser.add_argument(
        "--start",
        type=aware_datetime,
        default=None,
        metavar="ISO_DATETIME",
        help="Calendar window inclusive start with timezone offset",
    )
    parser.add_argument(
        "--end",
        type=aware_datetime,
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


__all__ = ["add_microsoft_options", "aware_datetime"]
