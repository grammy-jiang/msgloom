"""Outlook command dispatch below the unified Microsoft namespace."""

from __future__ import annotations

import argparse
from typing import Any

from scrapy.exceptions import UsageError

from .calendar import dispatch_calendar
from .mail import dispatch_mail


def dispatch_outlook(command: Any, opts: argparse.Namespace) -> None:
    """Dispatch Outlook resources without exposing additional top-level commands."""
    resource = opts.resource_or_action
    if resource == "mail":
        dispatch_mail(command, opts)
        return
    if resource == "calendar":
        dispatch_calendar(command, opts)
        return
    raise UsageError("use 'microsoft outlook {mail,calendar} ACTION'")


__all__ = ["dispatch_outlook"]
