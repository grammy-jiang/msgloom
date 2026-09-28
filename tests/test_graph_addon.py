"""Verify optional Graph defaults at Scrapy's add-on settings boundary."""

import pytest
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.exceptions import NotConfigured
from scrapy.http import Request, Response
from scrapy.settings import Settings
from scrapy.utils.misc import build_from_crawler, load_object
from scrapy.utils.test import get_crawler

from microsoft_graph.addon import MicrosoftGraphAddon
from microsoft_graph.extensions.privacy import MicrosoftGraphLogPrivacyExtension
from microsoft_graph.middlewares import (
    MicrosoftGraphDiagnosticsMiddleware,
    MicrosoftGraphErrorMiddleware,
)
from microsoft_graph.middlewares.retry import PrivacySafeRetryMiddleware
from microsoft_graph.spiders import GraphCollectionSpider


class CustomRetryMiddleware(RetryMiddleware):
    """Represent a consumer's selected generic retry implementation."""


def enabled_components(settings):
    return {
        load_object(key): priority
        for key, priority in settings.get_component_priority_dict_with_base(
            "DOWNLOADER_MIDDLEWARES"
        ).items()
    }


def test_addon_sets_only_provider_transport_and_privacy_defaults():
    settings = Settings()
    before = settings.copy_to_dict()
    addon = MicrosoftGraphAddon()
    addon.update_settings(settings)
    defaults = settings.copy_to_dict()
    addon.update_settings(settings)
    if settings.copy_to_dict() != defaults:
        pytest.fail("Repeated add-on configuration must not change defaults")
    changed = {
        key
        for key, value in settings.copy_to_dict().items()
        if value != before.get(key)
    }
    if changed != {
        "DOWNLOADER_MIDDLEWARES",
        "REQUEST_FINGERPRINTER_CLASS",
        "LOG_FORMATTER",
        "EXTENSIONS",
    }:
        pytest.fail(f"Unexpected global add-on policies: {changed}")
    components = settings.getdict("DOWNLOADER_MIDDLEWARES")
    if components != {
        RetryMiddleware: None,
        PrivacySafeRetryMiddleware: 550,
        MicrosoftGraphErrorMiddleware: 555,
        MicrosoftGraphDiagnosticsMiddleware: 960,
    }:
        pytest.fail(
            "Add-on must install transport components at established priorities"
        )
    enabled = enabled_components(settings)
    if RetryMiddleware in enabled or enabled.get(PrivacySafeRetryMiddleware) != 550:
        pytest.fail("Native and safe generic retries must not both be enabled")
    if settings.getpriority("REQUEST_FINGERPRINTER_CLASS") != 15:
        pytest.fail("Fingerprint default must have add-on priority")
    if settings.getpriority("LOG_FORMATTER") != 15:
        pytest.fail("Safe Graph log formatting must have add-on priority")
    if settings.getdict("EXTENSIONS") != {MicrosoftGraphLogPrivacyExtension: 100}:
        pytest.fail("Add-on must install only the reusable Graph privacy extension")
    if settings.getpriority("EXTENSIONS") != 15:
        pytest.fail("Graph privacy extension default must have add-on priority")


def test_consumer_can_disable_or_reprioritize_components_and_fingerprint():
    settings = Settings(
        {
            "DOWNLOADER_MIDDLEWARES": {
                RetryMiddleware: None,
                "microsoft_graph.middlewares.errors.MicrosoftGraphErrorMiddleware": None,
                MicrosoftGraphDiagnosticsMiddleware: 999,
            },
            "REQUEST_FINGERPRINTER_CLASS": "scrapy.utils.request.RequestFingerprinter",
            "LOG_FORMATTER": "scrapy.logformatter.LogFormatter",
            "EXTENSIONS": {MicrosoftGraphLogPrivacyExtension: None},
        }
    )
    before = settings.copy_to_dict()
    MicrosoftGraphAddon().update_settings(settings)
    if settings.copy_to_dict() != before:
        pytest.fail("Consumer component and fingerprint choices must take precedence")


@pytest.mark.parametrize("priority", ["project", "spider", "cmdline"])
@pytest.mark.parametrize("extension_priority", [None, 250])
@pytest.mark.parametrize(
    "key",
    [
        MicrosoftGraphLogPrivacyExtension,
        "microsoft_graph.extensions.privacy.MicrosoftGraphLogPrivacyExtension",
    ],
)
def test_explicit_privacy_extension_choice_is_preserved_without_duplicates(
    priority, extension_priority, key
):
    settings = Settings()
    settings.set("EXTENSIONS", {key: extension_priority}, priority)
    original_priority = settings.getpriority("EXTENSIONS")
    addon = MicrosoftGraphAddon()
    addon.update_settings(settings)
    addon.update_settings(settings)
    if settings.getdict("EXTENSIONS") != {key: extension_priority}:
        pytest.fail("Add-on changed or duplicated the consumer's privacy extension")
    if settings.getpriority("EXTENSIONS") != original_priority:
        pytest.fail("Add-on changed the consumer's extension settings priority")
    enabled = {
        load_object(component): value
        for component, value in settings.get_component_priority_dict_with_base(
            "EXTENSIONS"
        ).items()
    }
    if extension_priority is None:
        if MicrosoftGraphLogPrivacyExtension in enabled:
            pytest.fail("Explicitly disabled privacy extension was re-enabled")
        return
    if enabled.get(MicrosoftGraphLogPrivacyExtension) != extension_priority:
        pytest.fail("Privacy extension did not retain the consumer's priority")


def test_retry_enabled_false_keeps_native_constructor_gate():
    crawler = get_crawler(
        settings_dict={
            "ADDONS": {MicrosoftGraphAddon: 100},
            "RETRY_ENABLED": False,
        }
    )
    if crawler.settings.getbool("RETRY_ENABLED"):
        pytest.fail("Add-on must not enable disabled retries")
    with pytest.raises(NotConfigured):
        build_from_crawler(PrivacySafeRetryMiddleware, crawler)


def test_addon_retry_preserves_native_http_code_limit_and_stats_settings():
    crawler = get_crawler(
        GraphCollectionSpider,
        settings_dict={
            "ADDONS": {MicrosoftGraphAddon: 100},
            "RETRY_HTTP_CODES": [418],
            "RETRY_TIMES": 1,
            "RETRY_PRIORITY_ADJUST": -3,
        },
    )
    crawler.spider = GraphCollectionSpider.from_crawler(
        crawler, name="retry_settings", endpoint="/contacts"
    )
    middleware = build_from_crawler(PrivacySafeRetryMiddleware, crawler)
    request = Request("https://graph.microsoft.com/v1.0/contacts")
    ignored = Response(request.url, status=500)
    if middleware.process_response(request, ignored) is not ignored:
        pytest.fail("Safe retries ignored RETRY_HTTP_CODES")
    response = Response(request.url, status=418)
    retry = middleware.process_response(request, response)
    if not isinstance(retry, Request) or retry.priority != request.priority - 3:
        pytest.fail("Safe retry did not preserve native request priority adjustment")
    if middleware.process_response(retry, response) is not response:
        pytest.fail("Safe retries ignored RETRY_TIMES")
    if (
        crawler.stats.get_value("retry/count") != 1
        or crawler.stats.get_value("retry/max_reached") != 1
    ):
        pytest.fail("Safe retries changed native count/limit stats")


@pytest.mark.parametrize("priority", ["project", "spider", "cmdline"])
@pytest.mark.parametrize("native_priority", [None, 543])
@pytest.mark.parametrize(
    "key", [RetryMiddleware, "scrapy.downloadermiddlewares.retry.RetryMiddleware"]
)
def test_explicit_native_choice_opts_out(priority, native_priority, key):
    settings = Settings()
    settings.set("DOWNLOADER_MIDDLEWARES", {key: native_priority}, priority)
    MicrosoftGraphAddon().update_settings(settings)
    actual = settings.getdict("DOWNLOADER_MIDDLEWARES")
    if (
        key not in actual
        or actual[key] != native_priority
        or PrivacySafeRetryMiddleware in actual
    ):
        pytest.fail("Add-on replaced an explicit native retry choice")
    if native_priority is None and RetryMiddleware in enabled_components(settings):
        pytest.fail("Explicitly disabled native retry was re-enabled")
    if (
        settings.getpriority("DOWNLOADER_MIDDLEWARES")
        != {"project": 20, "spider": 30, "cmdline": 40}[priority]
    ):
        pytest.fail("Add-on changed the consumer's settings priority")


@pytest.mark.parametrize("priority", [None, 549])
@pytest.mark.parametrize(
    "key",
    [
        PrivacySafeRetryMiddleware,
        "microsoft_graph.middlewares.retry.PrivacySafeRetryMiddleware",
    ],
)
def test_explicit_safe_retry_choice_is_preserved_without_duplicates(priority, key):
    settings = Settings({"DOWNLOADER_MIDDLEWARES": {key: priority}})
    addon = MicrosoftGraphAddon()
    addon.update_settings(settings)
    addon.update_settings(settings)
    entries = settings.getdict("DOWNLOADER_MIDDLEWARES")
    if entries[key] != priority:
        pytest.fail("Safe retry override changed")
    if sum(load_object(entry) is PrivacySafeRetryMiddleware for entry in entries) != 1:
        pytest.fail("Class/path aliases introduced a duplicate retry component")
    enabled = enabled_components(settings)
    if priority is not None and RetryMiddleware in enabled:
        pytest.fail("Explicit safe retry must disable the implicit native default")


@pytest.mark.parametrize("disable_native", [False, True])
def test_consumer_custom_retry_is_not_replaced(disable_native):
    entries: dict[type[RetryMiddleware], int | None] = {CustomRetryMiddleware: 550}
    if disable_native:
        entries[RetryMiddleware] = None
    settings = Settings({"DOWNLOADER_MIDDLEWARES": entries})
    MicrosoftGraphAddon().update_settings(settings)
    actual = settings.getdict("DOWNLOADER_MIDDLEWARES")
    if actual[CustomRetryMiddleware] != 550 or PrivacySafeRetryMiddleware in actual:
        pytest.fail("Add-on must preserve custom retry implementation")
    for key, value in entries.items():
        if actual[key] != value:
            pytest.fail("Explicit retry choice changed")


def test_custom_middleware_base_is_not_replaced():
    settings = Settings({"DOWNLOADER_MIDDLEWARES_BASE": {RetryMiddleware: None}})
    MicrosoftGraphAddon().update_settings(settings)
    if PrivacySafeRetryMiddleware in enabled_components(settings):
        pytest.fail("Consumer base settings must not re-enable generic retries")


def test_native_addon_manager_loads_components_without_persistence():
    class Contacts(GraphCollectionSpider):
        name = "addon_contacts"
        endpoint = "/me/contacts"
        graph_permissions = ("Contacts.Read",)

    crawler = get_crawler(
        Contacts,
        settings_dict={
            "ADDONS": {"microsoft_graph.addon.MicrosoftGraphAddon": 100},
        },
    )
    if len(crawler.addons.addons) != 1:
        pytest.fail("Native Scrapy add-on manager must load the framework add-on")
    if crawler.settings.getdict("ITEM_PIPELINES") or crawler.settings.getdict(
        "EXTENSIONS"
    ) != {MicrosoftGraphLogPrivacyExtension: 100}:
        pytest.fail("Graph add-on must not install application lifecycle components")
    if crawler.settings.getbool("MS_GRAPH_AUTH_ENABLED"):
        pytest.fail("Authentication remains explicitly consumer-selected")
