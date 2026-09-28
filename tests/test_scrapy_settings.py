"""
Protect the enabled native components and ordering needed by the acquisition
contracts.
"""

from __future__ import annotations

import pytest
from scrapy import Spider
from scrapy.crawler import Crawler
from scrapy.extensions.periodic_log import PeriodicLog
from scrapy.settings import Settings, default_settings
from scrapy.utils.misc import build_from_crawler
from scrapy.utils.test import get_crawler

import message_ingest.settings as project_settings
from message_ingest.spiders.microsoft.outlook.email.delta import OutlookDeltaSpider
from message_ingest.spiders.microsoft.outlook.email.discover import (
    OutlookDiscoverSpider,
)
from message_ingest.spiders.microsoft.outlook.email.full import OutlookFullSpider


def _settings() -> Settings:
    settings = Settings()
    settings.setmodule(project_settings, priority="project")
    return settings


def test_downloader_middleware_order_matches_scrapy_request_response_semantics() -> (
    None
):
    settings = _settings()
    middlewares = settings.get_component_priority_dict_with_base(
        "DOWNLOADER_MIDDLEWARES"
    )
    if "scrapy.downloadermiddlewares.retry.RetryMiddleware" in middlewares:
        pytest.fail(
            'Expected: "scrapy.downloadermiddlewares.retry.RetryMiddleware" not in middlewares'
        )
    if (
        middlewares[
            "message_ingest.middlewares.microsoft_graph.errors.PrivacySafeRetryMiddleware"
        ]
        != 550
    ):
        pytest.fail(
            'Expected: middlewares["message_ingest.middlewares.microsoft_graph.errors.PrivacySafeRetryMiddleware"] == 550'
        )
    if (
        middlewares[
            "message_ingest.middlewares.microsoft_graph.errors.MicrosoftGraphErrorMiddleware"
        ]
        != 555
    ):
        pytest.fail(
            'Expected: middlewares["message_ingest.middlewares.microsoft_graph.errors.MicrosoftGraphErrorMiddleware"] == 555'
        )
    if middlewares["scrapy.downloadermiddlewares.stats.DownloaderStats"] != 850:
        pytest.fail(
            'Expected: middlewares["scrapy.downloadermiddlewares.stats.DownloaderStats"] == 850'
        )
    if (
        middlewares[
            "message_ingest.middlewares.microsoft_graph.diagnostics.MicrosoftGraphDiagnosticsMiddleware"
        ]
        != 960
    ):
        pytest.fail(
            'Expected: middlewares["message_ingest.middlewares.microsoft_graph.diagnostics.MicrosoftGraphDiagnosticsMiddleware"] == 960'
        )
    if middlewares["scrapy.downloadermiddlewares.httpcache.HttpCacheMiddleware"] != 900:
        pytest.fail(
            'Expected: middlewares["scrapy.downloadermiddlewares.httpcache.HttpCacheMiddleware"] == 900'
        )
    if (
        middlewares[
            "microsoft_graph.middlewares.authentication.MicrosoftGraphDeviceCodeAuthMiddleware"
        ]
        != 950
    ):
        pytest.fail(
            'Expected: middlewares[ "microsoft_graph.middlewares.authentication.MicrosoftGraphDeviceCodeAuthMiddleware" ] == 950'
        )
    if any("evidence" in key.lower() for key in middlewares):
        pytest.fail(
            'Expected: not any("evidence" in key.lower() for key in middlewares)'
        )


def test_native_http_cache_and_retry_remain_enabled() -> None:
    settings = _settings()
    if (
        settings["REQUEST_FINGERPRINTER_CLASS"]
        != "message_ingest.fingerprints.microsoft_graph.RepresentationAwareRequestFingerprinter"
    ):
        pytest.fail(
            'Expected: settings["REQUEST_FINGERPRINTER_CLASS"] == ( "message_ingest.fingerprints.microsoft_graph.RepresentationAwareRequestFingerprinter" )'
        )
    if settings.getbool("AUTOTHROTTLE_ENABLED") is not True:
        pytest.fail('Expected: settings.getbool("AUTOTHROTTLE_ENABLED") is True')
    if settings.getfloat("AUTOTHROTTLE_TARGET_CONCURRENCY") != 1.0:
        pytest.fail(
            'Expected: settings.getfloat("AUTOTHROTTLE_TARGET_CONCURRENCY") == 1.0'
        )
    if settings.getbool("HTTPCACHE_ENABLED") is not False:
        pytest.fail('Expected: settings.getbool("HTTPCACHE_ENABLED") is False')
    ignored = set(settings.getlist("HTTPCACHE_IGNORE_HTTP_CODES"))
    if set(default_settings.RETRY_HTTP_CODES) > ignored:
        pytest.fail("Expected: set(default_settings.RETRY_HTTP_CODES) <= ignored")
    if {401, 403} > ignored:
        pytest.fail("Expected: {401, 403} <= ignored")
    if settings["HTTPCACHE_STORAGE"] != default_settings.HTTPCACHE_STORAGE:
        pytest.fail(
            'Expected: settings["HTTPCACHE_STORAGE"] == default_settings.HTTPCACHE_STORAGE'
        )
    if settings["HTTPCACHE_POLICY"] != default_settings.HTTPCACHE_POLICY:
        pytest.fail(
            'Expected: settings["HTTPCACHE_POLICY"] == default_settings.HTTPCACHE_POLICY'
        )
    if settings.getbool("COOKIES_ENABLED") is not False:
        pytest.fail('Expected: settings.getbool("COOKIES_ENABLED") is False')
    if settings.getbool("REFERER_ENABLED") is not True:
        pytest.fail('Expected: settings.getbool("REFERER_ENABLED") is True')
    if settings["REFERRER_POLICY"] != "no-referrer":
        pytest.fail('Expected: settings["REFERRER_POLICY"] == "no-referrer"')
    if settings.getbool("METAREFRESH_ENABLED") is not False:
        pytest.fail('Expected: settings.getbool("METAREFRESH_ENABLED") is False')
    if settings.getint("URLLENGTH_LIMIT") != 0:
        pytest.fail('Expected: settings.getint("URLLENGTH_LIMIT") == 0')
    if settings.getbool("TELNETCONSOLE_ENABLED") is not False:
        pytest.fail('Expected: settings.getbool("TELNETCONSOLE_ENABLED") is False')
    if settings.getbool("REMOTE_CONTROL_ENABLED") is not False:
        pytest.fail('Expected: settings.getbool("REMOTE_CONTROL_ENABLED") is False')


def test_project_persists_scraped_data_through_item_pipelines() -> None:
    settings = _settings()
    pipelines = settings.getdict("ITEM_PIPELINES")
    if pipelines != {
        "message_ingest.pipelines.evidence.RawEvidencePipeline": 200,
        "message_ingest.acquisition.evidence_link.EvidenceLinkPipeline": 250,
        "message_ingest.pipelines.microsoft.outlook.email.OutlookMailPipeline": 300,
    }:
        pytest.fail("Expected raw, evidence-link, then Mail catalog pipelines")
    if settings.getint("CONCURRENT_ITEMS") != 1:
        pytest.fail('Expected: settings.getint("CONCURRENT_ITEMS") == 1')
    extensions = settings.getdict("EXTENSIONS")
    if (
        extensions["message_ingest.acquisition.source_context.SourceContextExtension"]
        != 50
    ):
        pytest.fail("Expected source-context extension priority == 50")
    if (
        extensions[
            "message_ingest.extensions.microsoft_graph.identity.MicrosoftGraphSourceIdentityExtension"
        ]
        != 425
    ):
        pytest.fail("Expected Graph source-identity gate priority == 425")
    if (
        extensions[
            "message_ingest.extensions.microsoft_graph.integrity.MicrosoftGraphIntegrityExtension"
        ]
        != 450
    ):
        pytest.fail("Expected: Graph integrity extension priority == 450")
    if (
        extensions[
            "message_ingest.extensions.microsoft.outlook.email.checkpoint.OutlookDeltaCheckpointExtension"
        ]
        != 500
    ):
        pytest.fail(
            'Expected: extensions["message_ingest.extensions.microsoft.outlook.email.checkpoint.OutlookDeltaCheckpointExtension"] == 500'
        )
    if (
        extensions[
            "message_ingest.extensions.microsoft_graph.privacy.MicrosoftGraphLogPrivacyExtension"
        ]
        != 525
    ):
        pytest.fail(
            'Expected: extensions["message_ingest.extensions.microsoft_graph.privacy.MicrosoftGraphLogPrivacyExtension"] == 525'
        )
    if (
        extensions["message_ingest.extensions.status.OutlookCrawlStatusExtension"]
        != 550
    ):
        pytest.fail(
            'Expected: extensions["message_ingest.extensions.status.OutlookCrawlStatusExtension"] == 550'
        )
    if extensions["scrapy.extensions.periodic_log.PeriodicLog"] != 600:
        pytest.fail(
            'Expected: extensions["scrapy.extensions.periodic_log.PeriodicLog"] == 600'
        )
    if settings.getbool("MSGLOOM_CATALOG_ENABLED") is not True:
        pytest.fail('Expected: settings.getbool("MSGLOOM_CATALOG_ENABLED") is True')
    if settings.getbool("MSGLOOM_RAW_EVIDENCE_ENABLED") is not True:
        pytest.fail(
            'Expected: settings.getbool("MSGLOOM_RAW_EVIDENCE_ENABLED") is True'
        )
    if settings.getbool("MS_GRAPH_ERROR_MIDDLEWARE_ENABLED") is not True:
        pytest.fail(
            'Expected: settings.getbool("MS_GRAPH_ERROR_MIDDLEWARE_ENABLED") is True'
        )
    if settings.getbool("MSGLOOM_CRAWL_STATUS_ENABLED") is not True:
        pytest.fail(
            'Expected: settings.getbool("MSGLOOM_CRAWL_STATUS_ENABLED") is True'
        )


def test_project_registers_custom_outlook_commands() -> None:
    settings = _settings()
    if settings["COMMANDS_MODULE"] != "message_ingest.commands":
        pytest.fail(
            'Expected: settings["COMMANDS_MODULE"] == "message_ingest.commands"'
        )


@pytest.mark.parametrize(
    "spider_cls",
    [OutlookDiscoverSpider, OutlookDeltaSpider, OutlookFullSpider],
)
def test_outlook_mail_resource_owns_graph_scope(spider_cls) -> None:
    if project_settings.MS_GRAPH_AUTH_ENABLED is not False:
        pytest.fail("Expected project-wide Graph auth to be disabled")
    if project_settings.MS_GRAPH_SCOPES != []:
        pytest.fail("Expected project-wide MS_GRAPH_SCOPES to be empty")
    if project_settings.MSGLOOM_SOURCE_IDENTITY_REQUIRED is not True:
        pytest.fail("Expected source identity required by default")
    if project_settings.MSGLOOM_SOURCE_IDENTITY_BOOTSTRAP_CONFIRM != "":
        pytest.fail("Expected source identity bootstrap confirmation default empty")
    if project_settings.MS_GRAPH_AUTH_ALLOW_INTERACTIVE is not True:
        pytest.fail("Expected interactive auth allowed by default for manual crawls")
    crawler = get_crawler(spider_cls)
    if crawler.settings.getbool("MS_GRAPH_AUTH_ENABLED") is not True:
        pytest.fail("Expected Outlook Mail spider to enable Graph auth")
    if crawler.settings.getlist("MS_GRAPH_SCOPES") != ["Mail.Read"]:
        pytest.fail('Expected Outlook Mail spider to own MS_GRAPH_SCOPES=["Mail.Read"]')


class NonGraphSpider(Spider):
    """Fixture resource that must not inherit Microsoft Graph auth."""

    name = "non_graph"


def test_non_graph_resource_does_not_inherit_microsoft_auth() -> None:
    crawler = Crawler(NonGraphSpider, _settings())
    if crawler.settings.getbool("MS_GRAPH_AUTH_ENABLED") is not False:
        pytest.fail("Expected non-Graph resource to leave Graph auth disabled")
    if crawler.settings.getlist("MS_GRAPH_SCOPES") != []:
        pytest.fail("Expected non-Graph resource to have no Graph scopes")


def test_command_line_scope_override_wins_over_mail_default() -> None:
    settings = _settings()
    settings.set(
        "MS_GRAPH_SCOPES",
        "User.Read,Mail.ReadBasic",
        priority="cmdline",
    )
    crawler = Crawler(OutlookDiscoverSpider, settings)
    if crawler.settings.getlist("MS_GRAPH_SCOPES") != [
        "User.Read",
        "Mail.ReadBasic",
    ]:
        pytest.fail("Expected command-line scope setting to override spider default")


def test_default_auth_method_is_device_code_and_both_components_are_registered() -> (
    None
):
    if project_settings.MS_GRAPH_AUTH_METHOD != "device_code":
        pytest.fail('Expected: project_settings.MS_GRAPH_AUTH_METHOD == "device_code"')
    settings = _settings()
    middlewares = settings.getdict("DOWNLOADER_MIDDLEWARES")
    if (
        middlewares[
            "microsoft_graph.middlewares.authentication.MicrosoftGraphDeviceCodeAuthMiddleware"
        ]
        != 950
    ):
        pytest.fail(
            'Expected: middlewares["microsoft_graph.middlewares.authentication.MicrosoftGraphDeviceCodeAuthMiddleware"] == 950'
        )
    if (
        middlewares[
            "microsoft_graph.middlewares.authentication.MicrosoftGraphInteractiveAuthMiddleware"
        ]
        != 951
    ):
        pytest.fail(
            'Expected: middlewares["microsoft_graph.middlewares.authentication.MicrosoftGraphInteractiveAuthMiddleware"] == 951'
        )


def test_periodic_log_uses_native_extension_with_safe_filters() -> None:
    """Build Scrapy 2.19 PeriodicLog with both dict settings enabled."""
    crawler = get_crawler(
        OutlookDiscoverSpider,
        settings_dict={
            "LOGSTATS_INTERVAL": project_settings.LOGSTATS_INTERVAL,
            "PERIODIC_LOG_STATS": project_settings.PERIODIC_LOG_STATS,
            "PERIODIC_LOG_DELTA": project_settings.PERIODIC_LOG_DELTA,
            "PERIODIC_LOG_TIMING_ENABLED": (
                project_settings.PERIODIC_LOG_TIMING_ENABLED
            ),
        },
    )
    extension = build_from_crawler(PeriodicLog, crawler)
    if not isinstance(extension, PeriodicLog):
        pytest.fail("Expected: isinstance(extension, PeriodicLog)")
    stats_include = set(project_settings.PERIODIC_LOG_STATS["include"])
    if "msgloom/catalog/" not in stats_include:
        pytest.fail('Expected: "msgloom/catalog/" in stats_include')
    if "msgloom/graph_error_retry/" not in stats_include:
        pytest.fail('Expected: "msgloom/graph_error_retry/" in stats_include')
    if "msgloom/final/" not in stats_include:
        pytest.fail('Expected: "msgloom/final/" in stats_include')

    crawler.stats.set_value(
        "msgloom/catalog/surface_item_processed_count/attachment_raw/acquired",
        1,
    )
    crawler.stats.set_value("msgloom/graph_error_retry/count", 2)
    crawler.stats.set_value("private/provider-id-secret", 1)
    selected = extension.log_crawler_stats()["stats"]
    if (
        "msgloom/catalog/surface_item_processed_count/attachment_raw/acquired"
        not in selected
    ):
        pytest.fail("Expected: normalized catalog surface stat in PeriodicLog")
    if "msgloom/graph_error_retry/count" not in selected:
        pytest.fail("Expected: Graph retry helper stat in PeriodicLog")
    if "private/provider-id-secret" in selected:
        pytest.fail("Expected: unreviewed stat excluded from PeriodicLog")

    if project_settings.PERIODIC_LOG_TIMING_ENABLED is not False:
        pytest.fail("Expected: project_settings.PERIODIC_LOG_TIMING_ENABLED is False")
