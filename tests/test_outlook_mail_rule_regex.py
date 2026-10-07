"""Compatibility, resource, and privacy tests for msgloom-regex-v1."""

from __future__ import annotations

import importlib
import logging
from typing import Any, cast

import pytest


def _module():
    return importlib.import_module(
        "message_ingest.acquisition.microsoft.outlook.email.rule_regex"
    )


def _engine():
    return _module().MailRegexEngine()


def test_regex_search_matches_substrings_not_only_whole_fields() -> None:
    engine = _engine()
    compiled = engine.compile("invoice")

    if not engine.search(compiled, "monthly INVOICE approval"):
        pytest.fail("msgloom-regex-v1 must use case-insensitive search semantics")


def test_regex_anchors_require_field_boundaries() -> None:
    engine = _engine()
    compiled = engine.compile("^invoice$")

    if not engine.search(compiled, "INVOICE"):
        pytest.fail("Anchored regex did not match the complete case-insensitive field")
    if engine.search(compiled, "monthly invoice"):
        pytest.fail("Anchored regex unexpectedly matched a substring")


def test_regex_default_is_case_insensitive() -> None:
    engine = _engine()
    compiled = engine.compile("urgent")

    if not engine.search(compiled, "URGENT: approval"):
        pytest.fail("Default regex matching must be case-insensitive")


def test_regex_inline_flag_can_restore_case_sensitive_region() -> None:
    engine = _engine()
    compiled = engine.compile("(?-i:URGENT)")

    if not engine.search(compiled, "URGENT"):
        pytest.fail("Explicit case-sensitive RE2 region did not match exact case")
    if engine.search(compiled, "urgent"):
        pytest.fail("Explicit case-sensitive RE2 region ignored its inline flag")


@pytest.mark.parametrize(
    "pattern",
    (
        "(?=secret)",
        "(?<=secret)",
        r"(secret)\1",
    ),
)
def test_regex_rejects_non_re2_language_constructs(pattern: str) -> None:
    module = _module()

    with pytest.raises(module.MailRegexSyntaxError):
        module.MailRegexEngine().compile(pattern)


def test_regex_rejects_empty_pattern() -> None:
    module = _module()

    with pytest.raises(module.MailRegexSyntaxError):
        module.MailRegexEngine().compile("")


def test_regex_rejects_pattern_over_4096_characters_before_compile() -> None:
    module = _module()

    with pytest.raises(module.MailRegexSyntaxError):
        module.MailRegexEngine().compile("a" * (module.MAX_REGEX_PATTERN_CHARS + 1))


def test_invalid_private_pattern_never_reaches_exception_stderr_or_logs(
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    module = _module()
    private = "PRIVATE_CUSTOMER_TOKEN_93"
    pattern = f"{private}(?="

    with (
        caplog.at_level(logging.DEBUG),
        pytest.raises(module.MailRegexSyntaxError) as caught,
    ):
        module.MailRegexEngine().compile(pattern)

    captured = capsys.readouterr()
    exposed = "\n".join(
        (
            str(caught.value),
            captured.out,
            captured.err,
            *(record.getMessage() for record in caplog.records),
        )
    )
    if private in exposed or pattern in exposed:
        pytest.fail("Invalid regex leaked private pattern material")


class _ExplodingCompiled:
    def search(self, _text: str) -> bool:
        raise RuntimeError("PRIVATE_RUNTIME_PATTERN_FAILURE_48")


def test_runtime_engine_exception_becomes_bounded_evaluation_error() -> None:
    module = _module()
    compiled = module.CompiledMailRegex(cast(Any, _ExplodingCompiled()))

    with pytest.raises(module.MailRegexEvaluationError) as caught:
        module.MailRegexEngine().search(compiled, "ordinary text")

    if "PRIVATE_RUNTIME_PATTERN_FAILURE_48" in str(caught.value):
        pytest.fail("Runtime regex failure leaked dependency exception text")


def test_regex_contract_constants_are_fixed() -> None:
    module = _module()

    if module.MSGLOOM_REGEX_VERSION != "msgloom-regex-v1":
        pytest.fail("Public regex contract version changed")
    if module.MAX_REGEX_PATTERNS != 64:
        pytest.fail("Configured regex-entry bound changed")
    if module.MAX_REGEX_PATTERN_CHARS != 4096:
        pytest.fail("Regex pattern length bound changed")
    if module.RE2_MAX_MEM_BYTES != 4 * 1024 * 1024:
        pytest.fail("RE2 per-pattern memory budget changed")
