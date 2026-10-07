"""Awaited process isolation for provider-neutral attachment parsers."""

from msgloom.preparation.isolation.runner import (
    ParserIsolationError,
    ParserIsolationUnavailable,
    ParserOutputError,
    ParserTimeoutError,
    parse_isolated,
)

__all__ = [
    "ParserIsolationError",
    "ParserIsolationUnavailable",
    "ParserOutputError",
    "ParserTimeoutError",
    "parse_isolated",
]
