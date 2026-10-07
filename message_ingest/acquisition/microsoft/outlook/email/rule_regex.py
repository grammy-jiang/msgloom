"""Bounded privacy-safe regular expressions for Outlook Mail rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import re2

MSGLOOM_REGEX_VERSION = "msgloom-regex-v1"
MAX_REGEX_PATTERNS = 64
MAX_REGEX_PATTERN_CHARS = 4096
RE2_MAX_MEM_BYTES = 4 * 1024 * 1024


class MailRegexSyntaxError(ValueError):
    """A configured pattern is outside the msgloom-regex-v1 contract."""

    def __init__(self) -> None:
        super().__init__("regex pattern is not valid msgloom-regex-v1 syntax")


class MailRegexEvaluationError(RuntimeError):
    """RE2 could not evaluate one already-compiled pattern safely."""

    def __init__(self) -> None:
        super().__init__("regex evaluation failed")


@dataclass(frozen=True, slots=True, repr=False)
class CompiledMailRegex:
    """Opaque compiled RE2 object; configured pattern text is never retained here."""

    _compiled: Any


class MailRegexEngine:
    """Compile and search the fixed msgloom-regex-v1 dialect."""

    @staticmethod
    def compile(pattern: str) -> CompiledMailRegex:
        """Compile one bounded user pattern without rewriting it."""

        if not isinstance(pattern, str) or not pattern:
            raise MailRegexSyntaxError
        if len(pattern) > MAX_REGEX_PATTERN_CHARS:
            raise MailRegexSyntaxError

        options = re2.Options()
        options.case_sensitive = False
        options.log_errors = False
        options.max_mem = RE2_MAX_MEM_BYTES
        try:
            compiled = re2.compile(pattern, options=options)
        except Exception:  # noqa: BLE001 - sanitize the dependency boundary.
            raise MailRegexSyntaxError from None
        return CompiledMailRegex(compiled)

    @staticmethod
    def search(compiled: CompiledMailRegex, text: str) -> bool:
        """Return RE2 search truth with bounded dependency-failure semantics."""

        try:
            return compiled._compiled.search(text) is not None
        except Exception:  # noqa: BLE001 - sanitize the dependency boundary.
            raise MailRegexEvaluationError from None


__all__ = [
    "MAX_REGEX_PATTERNS",
    "MAX_REGEX_PATTERN_CHARS",
    "MSGLOOM_REGEX_VERSION",
    "RE2_MAX_MEM_BYTES",
    "CompiledMailRegex",
    "MailRegexEngine",
    "MailRegexEvaluationError",
    "MailRegexSyntaxError",
]
