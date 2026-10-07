"""Lock the unified Microsoft Scrapy command into one public command surface."""

from __future__ import annotations

from pathlib import Path

import pytest

from message_ingest.commands import microsoft


def test_microsoft_command_is_defined_at_public_command_module() -> None:
    if microsoft.__all__ != ["Command"]:
        pytest.fail(f"Unexpected Microsoft command exports: {microsoft.__all__!r}")
    if microsoft.Command.__module__ != "message_ingest.commands.microsoft":
        pytest.fail("Microsoft Scrapy Command must remain at the public command module")


def test_legacy_flat_microsoft_command_modules_are_gone() -> None:
    root = Path(__file__).parents[1] / "message_ingest" / "commands"
    legacy = [root / "microsoft.py", root / "_microsoft_calendar.py"]
    existing = [str(path) for path in legacy if path.exists()]
    if existing:
        pytest.fail(f"Legacy Microsoft command modules must not return: {existing!r}")
