"""Lock the public Microsoft spider package layout."""

from __future__ import annotations

from pathlib import Path

import pytest
from scrapy.utils.project import get_project_settings

from message_ingest import spiders
from message_ingest.spiders import microsoft
from message_ingest.spiders.microsoft import outlook
from message_ingest.spiders.microsoft.outlook import calendar, email


def test_spider_packages_expose_only_declared_public_surfaces() -> None:
    if spiders.__all__ != ["microsoft"]:
        pytest.fail(f"Unexpected top-level spider exports: {spiders.__all__!r}")
    if microsoft.__all__ != ["MicrosoftProfileSpider", "outlook", "teams"]:
        pytest.fail(f"Unexpected Microsoft spider exports: {microsoft.__all__!r}")
    if outlook.__all__ != ["calendar", "email"]:
        pytest.fail(f"Unexpected Outlook spider exports: {outlook.__all__!r}")
    if email.__all__ != [
        "OutlookDeltaSpider",
        "OutlookDiscoverSpider",
        "OutlookFolderDeltaSpider",
        "OutlookFullSpider",
    ]:
        pytest.fail(f"Unexpected Outlook email exports: {email.__all__!r}")
    if calendar.__all__ != [
        "OutlookCalendarDeltaSpider",
        "OutlookCalendarDiscoverSpider",
        "OutlookCalendarFullSpider",
        "OutlookCalendarWindowSpider",
    ]:
        pytest.fail(f"Unexpected Outlook Calendar exports: {calendar.__all__!r}")


def test_top_level_spiders_directory_contains_no_feature_modules() -> None:
    spider_root = Path(__file__).parents[1] / "message_ingest" / "spiders"
    root_modules = sorted(path.name for path in spider_root.glob("*.py"))
    if root_modules != ["__init__.py"]:
        pytest.fail(f"Top-level spiders directory is cluttered: {root_modules!r}")


def test_scrapy_discovers_from_microsoft_package() -> None:
    settings = get_project_settings()
    if settings.getlist("SPIDER_MODULES") != ["message_ingest.spiders.microsoft"]:
        pytest.fail(
            f"Unexpected SPIDER_MODULES: {settings.getlist('SPIDER_MODULES')!r}"
        )
    if settings.get("NEWSPIDER_MODULE") != "message_ingest.spiders.microsoft":
        pytest.fail(
            f"Unexpected NEWSPIDER_MODULE: {settings.get('NEWSPIDER_MODULE')!r}"
        )
