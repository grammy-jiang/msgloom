"""
Default Scrapy component contracts and environment-backed project settings.
"""

from __future__ import annotations

import os


def _env_bool(name: str, default: bool = True) -> bool:
    """
    Use the default only when unset; recognize common explicit false values.
    """
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


BOT_NAME = "message_ingest"

SPIDER_MODULES = ["message_ingest.spiders.microsoft"]
NEWSPIDER_MODULE = "message_ingest.spiders.microsoft"
COMMANDS_MODULE = "message_ingest.commands"


# Scrapy's global default is False. The generated project template enables it,
# but Microsoft Graph is an authenticated API rather than a web crawl.
ROBOTSTXT_OBEY = False
COOKIES_ENABLED = False
REFERER_ENABLED = True
REFERRER_POLICY = "no-referrer"
URLLENGTH_LIMIT = 0
TELNETCONSOLE_ENABLED = False
REMOTE_CONTROL_ENABLED = False
METAREFRESH_ENABLED = False

# Real Graph delta testing showed burst throttling at Scrapy defaults.
CONCURRENT_REQUESTS_PER_DOMAIN = 2
# Serialize outputs from each callback so raw evidence finishes before semantic
# items from that response. A separate shared lock serializes cross-response
# SQL writes. Raising this value requires an explicit evidence dependency
# mechanism.
CONCURRENT_ITEMS = 1

REQUEST_FINGERPRINTER_CLASS = "message_ingest.fingerprints.microsoft_graph.RepresentationAwareRequestFingerprinter"
LOG_FORMATTER = "message_ingest.observability.formatter.MessageIngestLogFormatter"

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 0.25
AUTOTHROTTLE_MAX_DELAY = 60.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
AUTOTHROTTLE_DEBUG = False

MS_GRAPH_AUTH_ENABLED = False
MS_GRAPH_ERROR_MIDDLEWARE_ENABLED = _env_bool(
    "MSGLOOM_MS_ERROR_MIDDLEWARE_ENABLED", True
)
MSGLOOM_DELTA_CHECKPOINT_ENABLED = _env_bool("MSGLOOM_DELTA_CHECKPOINT_ENABLED", True)
MSGLOOM_CALENDAR_DELTA_CHECKPOINT_ENABLED = False
MSGLOOM_CRAWL_STATUS_ENABLED = _env_bool("MSGLOOM_CRAWL_STATUS_ENABLED", True)
MSGLOOM_CATALOG_ENABLED = _env_bool("MSGLOOM_CATALOG_ENABLED", True)
MSGLOOM_RAW_EVIDENCE_ENABLED = _env_bool("MSGLOOM_RAW_EVIDENCE_ENABLED", True)

# Use Scrapy's built-in downloader stack. Authentication implementations are
# all registered as components; each uses final crawler settings and disables
# itself with NotConfigured unless selected by MS_GRAPH_AUTH_METHOD.
MS_GRAPH_AUTH_METHOD = (
    os.getenv("MSGLOOM_MS_AUTH_METHOD", "device_code").strip().lower()
)

DOWNLOADER_MIDDLEWARES = {
    # Preserve Scrapy generic retries through a privacy-safe subclass that
    # suppresses Request reprs containing Graph continuation URLs.
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,
    "message_ingest.middlewares.microsoft_graph.errors.PrivacySafeRetryMiddleware": 550,
    # Request hooks run in ascending priority and response hooks in descending
    # priority. Diagnostics therefore sees each Graph response before auth can
    # replace a 401 with a retry Request. Provider retries still run after auth.
    "message_ingest.middlewares.microsoft_graph.errors.MicrosoftGraphErrorMiddleware": 555,
    "microsoft_graph.middlewares.authentication.MicrosoftGraphDeviceCodeAuthMiddleware": 950,
    "microsoft_graph.middlewares.authentication.MicrosoftGraphInteractiveAuthMiddleware": 951,
    "message_ingest.middlewares.microsoft_graph.diagnostics.MicrosoftGraphDiagnosticsMiddleware": 960,
}

EXTENSIONS = {
    "message_ingest.acquisition.source_context.SourceContextExtension": 50,
    # These priorities do not order signal handlers. Checkpoint safety depends
    # on Scrapy's idle condition and explicit completed-work sets.
    "message_ingest.extensions.microsoft_graph.identity.MicrosoftGraphSourceIdentityExtension": 425,
    "message_ingest.extensions.microsoft_graph.integrity.MicrosoftGraphIntegrityExtension": 450,
    "message_ingest.extensions.microsoft.outlook.email.checkpoint.OutlookDeltaCheckpointExtension": 500,
    "message_ingest.extensions.microsoft.outlook.calendar.checkpoint.CalendarDeltaCheckpointExtension": 510,
    "message_ingest.extensions.microsoft_graph.privacy.MicrosoftGraphLogPrivacyExtension": 525,
    "message_ingest.extensions.microsoft.outlook.email.status.OutlookCrawlStatusExtension": 550,
    # PeriodicLog is not in Scrapy 2.19 EXTENSIONS_BASE; enable the native
    # implementation explicitly instead of maintaining another timer.
    "scrapy.extensions.periodic_log.PeriodicLog": 600,
}

# PeriodicLog reads the normal Stats Collector and logs JSON snapshots.
# Every included stat key must remain identifier-free; provider IDs belong in
# persisted records, never in stat-key labels. Periodic filters match
# substrings, so the explicit Graph retry family is listed even though
# "retry/" also overlaps it.
LOGSTATS_INTERVAL = 60.0
PERIODIC_LOG_STATS = {
    "include": [
        "msgloom/crawl/",
        "msgloom/checkpoint/",
        "msgloom/evidence/",
        "msgloom/catalog/",
        "msgloom/graph/",
        "msgloom/graph_error/",
        "msgloom/graph_error_retry/",
        "msgloom/auth/",
        "msgloom/source_identity/",
        "msgloom/source_context/",
        "msgloom/persistence/",
        "msgloom/lifecycle/",
        "msgloom/final/",
        "downloader/request_count",
        "downloader/response_count",
        "downloader/response_status_count/",
        "response_received_count",
        "item_scraped_count",
        "item_dropped_count",
        "spider_exceptions/",
        "retry/",
        "scheduler/enqueued",
        "scheduler/dequeued",
        "httpcache/",
    ]
}
PERIODIC_LOG_DELTA = {
    "include": [
        "downloader/request_count",
        "downloader/response_count",
        "item_scraped_count",
        "item_dropped_count",
        "msgloom/graph/request_count",
        "msgloom/graph/response_count",
        "msgloom/crawl/failure_count",
        "msgloom/crawl/discovery/page_count",
        "msgloom/crawl/discovery/message_count",
        "msgloom/crawl/delta/folder_page_count",
        "msgloom/crawl/delta/message_page_count",
        "msgloom/crawl/delta/message_upsert_count",
        "msgloom/crawl/delta/message_removed_count",
        "msgloom/crawl/reconcile/message_count",
        "msgloom/crawl/reconcile/message_recovered_count",
        "msgloom/crawl/enrichment/message_detail_count",
        "msgloom/crawl/enrichment/message_mime_count",
        "msgloom/crawl/enrichment/attachment_page_count",
        "msgloom/crawl/enrichment/attachment_count",
        "msgloom/crawl/enrichment/attachment_raw_count",
        "msgloom/crawl/enrichment/item_attachment_detail_count",
        "msgloom/evidence/response_persisted_count",
        "msgloom/graph_error_retry/count",
        "msgloom/auth/401_retry_count",
        "msgloom/persistence/item_error_count",
        "msgloom/lifecycle/close_error_count",
        "spider_exceptions/count",
    ]
}
# Avoid PeriodicLog's start_time dependency at spider_opened; native LogStats
# already reports elapsed rates, and signal handler order is not a contract.
PERIODIC_LOG_TIMING_ENABLED = False

ITEM_PIPELINES = {
    # Per-item stage order is independent of concurrency between callbacks.
    "message_ingest.pipelines.evidence.RawEvidencePipeline": 200,
    "message_ingest.acquisition.evidence_link.EvidenceLinkPipeline": 250,
    "message_ingest.pipelines.microsoft.outlook.email.OutlookMailPipeline": 300,
}

# Development-only cache. Scrapy's default is disabled, which is also the
# msgloom production default. Enable explicitly when replaying HTTP fixtures.
HTTPCACHE_ENABLED = _env_bool("MSGLOOM_HTTP_CACHE_ENABLED", False)
HTTPCACHE_IGNORE_HTTP_CODES = [
    401,
    403,
    409,
    500,
    502,
    503,
    504,
    509,
    522,
    524,
    408,
    429,
]

MSGLOOM_DATA_DIR = os.getenv("MSGLOOM_DATA_DIR", "var/acquisition")
MSGLOOM_DATABASE_URL = os.getenv(
    "MSGLOOM_DATABASE_URL", "sqlite:///var/msgloom.sqlite3"
)
MSGLOOM_RAW_EVIDENCE_DIR = os.getenv("MSGLOOM_RAW_EVIDENCE_DIR", "var/acquisition/raw")
MSGLOOM_SOURCE_ID = os.getenv("MSGLOOM_SOURCE_ID", "microsoft-outlook-default")
MSGLOOM_SOURCE_IDENTITY_REQUIRED = True
# Legacy identity bootstrap must be an explicit invocation-scoped Scrapy
# setting (for example ``-s ...``), never a sticky environment default.
MSGLOOM_SOURCE_IDENTITY_BOOTSTRAP_CONFIRM = ""

MS_GRAPH_CLIENT_ID = os.getenv("MSGLOOM_MS_CLIENT_ID", "")
MS_GRAPH_AUTHORITY = os.getenv(
    "MSGLOOM_MS_AUTHORITY", "https://login.microsoftonline.com/common"
)
# Resource spiders declare least-privilege Graph scopes with custom_settings.
MS_GRAPH_SCOPES: list[str] = []
MS_GRAPH_ACCOUNT_USERNAME = os.getenv("MSGLOOM_MS_USERNAME", "")
MS_GRAPH_AUTH_ALLOW_INTERACTIVE = _env_bool("MSGLOOM_MS_ALLOW_INTERACTIVE_AUTH", True)
MS_GRAPH_ERROR_MAX_RETRIES = int(os.getenv("MSGLOOM_MS_ERROR_MAX_RETRIES", "8"))
MS_GRAPH_ERROR_FALLBACK_BASE_SECONDS = int(
    os.getenv("MSGLOOM_MS_ERROR_FALLBACK_BASE_SECONDS", "1")
)
MS_GRAPH_ERROR_FALLBACK_MAX_SECONDS = int(
    os.getenv("MSGLOOM_MS_ERROR_FALLBACK_MAX_SECONDS", "60")
)

MS_GRAPH_TOKEN_CACHE = os.getenv(
    "MSGLOOM_MS_TOKEN_CACHE", "var/auth/msal-token-cache.json"
)
