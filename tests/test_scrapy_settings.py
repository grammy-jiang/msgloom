from __future__ import annotations

from scrapy.settings import Settings, default_settings

import msgloom.settings as project_settings


def _settings() -> Settings:
    settings = Settings()
    settings.setmodule(project_settings, priority="project")
    return settings


def test_downloader_middleware_order_matches_scrapy_request_response_semantics() -> None:
    settings = _settings()
    middlewares = settings.get_component_priority_dict_with_base("DOWNLOADER_MIDDLEWARES")
    assert middlewares["scrapy.downloadermiddlewares.retry.RetryMiddleware"] == 550
    assert middlewares["msgloom.middlewares.MicrosoftGraphThrottleMiddleware"] == 555
    assert middlewares["scrapy.downloadermiddlewares.stats.DownloaderStats"] == 850
    assert middlewares["msgloom.evidence.CachedEvidenceLinkMiddleware"] == 875
    assert middlewares["scrapy.downloadermiddlewares.httpcache.HttpCacheMiddleware"] == 900
    assert middlewares[
        "msgloom.middlewares.MicrosoftGraphDeviceCodeAuthMiddleware"
    ] == 950
    assert middlewares["msgloom.evidence.RawNetworkEvidenceMiddleware"] == 975


def test_native_http_cache_and_retry_remain_enabled() -> None:
    settings = _settings()
    assert settings.getbool("HTTPCACHE_ENABLED") is True
    ignored = set(settings.getlist("HTTPCACHE_IGNORE_HTTP_CODES"))
    assert set(default_settings.RETRY_HTTP_CODES) <= ignored
    assert {401, 403} <= ignored
    assert settings["HTTPCACHE_STORAGE"] == default_settings.HTTPCACHE_STORAGE
    assert settings["HTTPCACHE_POLICY"] == default_settings.HTTPCACHE_POLICY
    assert settings.getbool("COOKIES_ENABLED") is False
    assert settings.getbool("REFERER_ENABLED") is True
    assert settings["REFERRER_POLICY"] == "no-referrer"
    assert settings.getint("URLLENGTH_LIMIT") == 0
    assert settings.getbool("TELNETCONSOLE_ENABLED") is False
    assert settings.getbool("REMOTE_CONTROL_ENABLED") is False


def test_project_splits_catalog_jsonl_and_checkpoint_components() -> None:
    settings = _settings()
    pipelines = settings.getdict("ITEM_PIPELINES")
    assert pipelines == {
        "msgloom.pipelines.CatalogPipeline": 300,
        "msgloom.pipelines.LocalJsonlPipeline": 400,
    }
    extensions = settings.getdict("EXTENSIONS")
    assert extensions["msgloom.services.CatalogService"] == 100
    assert extensions["msgloom.extensions.OutlookDeltaCheckpointExtension"] == 500
    assert settings.getbool("MSGLOOM_CATALOG_ENABLED") is True
    assert settings.getbool("MSGLOOM_JSONL_ENABLED") is True
    assert settings.getbool("MSGLOOM_RAW_EVIDENCE_ENABLED") is True
    assert settings.getbool("MS_GRAPH_THROTTLE_ENABLED") is True


def test_default_auth_method_is_device_code() -> None:
    assert project_settings.MS_GRAPH_AUTH_METHOD == "device_code"
    assert project_settings.MS_GRAPH_AUTH_MIDDLEWARES["device_code"].endswith(
        "MicrosoftGraphDeviceCodeAuthMiddleware"
    )
    assert project_settings.MS_GRAPH_AUTH_MIDDLEWARES["interactive"].endswith(
        "MicrosoftGraphInteractiveAuthMiddleware"
    )
