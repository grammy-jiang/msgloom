"""Verify optional Graph defaults at Scrapy's add-on settings boundary."""

import pytest
from scrapy.settings import Settings
from scrapy.utils.test import get_crawler

from microsoft_graph.scrapy import GraphCollectionSpider, MicrosoftGraphAddon
from microsoft_graph.scrapy.middlewares import (
    MicrosoftGraphDiagnosticsMiddleware,
    MicrosoftGraphErrorMiddleware,
)


def test_addon_sets_only_provider_transport_defaults():
    settings = Settings()
    before = settings.copy_to_dict()
    MicrosoftGraphAddon().update_settings(settings)
    changed = {
        key
        for key, value in settings.copy_to_dict().items()
        if value != before.get(key)
    }
    if changed != {"DOWNLOADER_MIDDLEWARES", "REQUEST_FINGERPRINTER_CLASS"}:
        pytest.fail(f"Unexpected global add-on policies: {changed}")
    components = settings.getdict("DOWNLOADER_MIDDLEWARES")
    if components != {
        MicrosoftGraphErrorMiddleware: 555,
        MicrosoftGraphDiagnosticsMiddleware: 960,
    }:
        pytest.fail(
            "Add-on must install transport components at established priorities"
        )
    if settings.getpriority("REQUEST_FINGERPRINTER_CLASS") != 15:
        pytest.fail("Fingerprint default must have add-on priority")


def test_consumer_can_disable_or_reprioritize_components_and_fingerprint():
    settings = Settings(
        {
            "DOWNLOADER_MIDDLEWARES": {
                "microsoft_graph.scrapy.middlewares.errors.MicrosoftGraphErrorMiddleware": None,
                MicrosoftGraphDiagnosticsMiddleware: 999,
            },
            "REQUEST_FINGERPRINTER_CLASS": "scrapy.utils.request.RequestFingerprinter",
        }
    )
    before = settings.copy_to_dict()
    MicrosoftGraphAddon().update_settings(settings)
    if settings.copy_to_dict() != before:
        pytest.fail("Consumer component and fingerprint choices must take precedence")


def test_native_addon_manager_loads_components_without_persistence():
    class Contacts(GraphCollectionSpider):
        name = "addon_contacts"
        endpoint = "/me/contacts"
        graph_permissions = ("Contacts.Read",)

    crawler = get_crawler(
        Contacts,
        settings_dict={
            "ADDONS": {"microsoft_graph.scrapy.MicrosoftGraphAddon": 100},
        },
    )
    if len(crawler.addons.addons) != 1:
        pytest.fail("Native Scrapy add-on manager must load the framework add-on")
    if crawler.settings.getdict("ITEM_PIPELINES") or crawler.settings.getdict(
        "EXTENSIONS"
    ):
        pytest.fail("Graph add-on must not install application lifecycle components")
    if crawler.settings.getbool("MS_GRAPH_AUTH_ENABLED"):
        pytest.fail("Authentication remains explicitly consumer-selected")
