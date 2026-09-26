from __future__ import annotations

import os


def _env_bool(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}

BOT_NAME = "msgloom"

SPIDER_MODULES = ["msgloom.spiders"]
NEWSPIDER_MODULE = "msgloom.spiders"

# Scrapy's global default is False. The generated project template enables it,
# but Microsoft Graph is an authenticated API rather than a web crawl.
ROBOTSTXT_OBEY = False
COOKIES_ENABLED = False
REFERER_ENABLED = True
REFERRER_POLICY = "no-referrer"
URLLENGTH_LIMIT = 0
TELNETCONSOLE_ENABLED = False
REMOTE_CONTROL_ENABLED = False

# Real Graph delta testing showed burst throttling at Scrapy defaults.
CONCURRENT_REQUESTS_PER_DOMAIN = 2

MS_GRAPH_THROTTLE_ENABLED = _env_bool("MSGLOOM_MS_THROTTLE_ENABLED", True)
MSGLOOM_RAW_EVIDENCE_ENABLED = _env_bool("MSGLOOM_RAW_EVIDENCE_ENABLED", True)
MSGLOOM_DELTA_CHECKPOINT_ENABLED = _env_bool("MSGLOOM_DELTA_CHECKPOINT_ENABLED", True)
MSGLOOM_CATALOG_ENABLED = _env_bool("MSGLOOM_CATALOG_ENABLED", True)
MSGLOOM_JSONL_ENABLED = _env_bool("MSGLOOM_JSONL_ENABLED", True)

# Use Scrapy's built-in downloader stack. Exactly one Microsoft Graph
# authentication middleware is enabled according to MSGLOOM_MS_AUTH_METHOD.
MS_GRAPH_AUTH_METHOD = os.getenv("MSGLOOM_MS_AUTH_METHOD", "device_code").strip().lower()
MS_GRAPH_AUTH_MIDDLEWARES = {
    "device_code": "msgloom.middlewares.MicrosoftGraphDeviceCodeAuthMiddleware",
    "interactive": "msgloom.middlewares.MicrosoftGraphInteractiveAuthMiddleware",
}
try:
    _MS_GRAPH_AUTH_MIDDLEWARE = MS_GRAPH_AUTH_MIDDLEWARES[MS_GRAPH_AUTH_METHOD]
except KeyError as exc:
    raise RuntimeError(
        "Unsupported MSGLOOM_MS_AUTH_METHOD. Expected one of: "
        + ", ".join(sorted(MS_GRAPH_AUTH_MIDDLEWARES))
    ) from exc

# Priority 950 places authentication after Scrapy's built-in
# HttpCacheMiddleware (900) on the request path.
DOWNLOADER_MIDDLEWARES = {
    "msgloom.middlewares.MicrosoftGraphThrottleMiddleware": 555,
    "msgloom.evidence.CachedEvidenceLinkMiddleware": 875,
    _MS_GRAPH_AUTH_MIDDLEWARE: 950,
    "msgloom.evidence.RawNetworkEvidenceMiddleware": 975,
}

EXTENSIONS = {
    "msgloom.services.CatalogService": 100,
    "msgloom.extensions.OutlookDeltaCheckpointExtension": 500,
}

ITEM_PIPELINES = {
    "msgloom.pipelines.CatalogPipeline": 300,
    "msgloom.pipelines.LocalJsonlPipeline": 400,
}

# Development cache: use Scrapy's native cache policy and filesystem storage.
# Scrapy explicitly recommends excluding the same status codes that Retry uses.
HTTPCACHE_ENABLED = True
HTTPCACHE_IGNORE_HTTP_CODES = [401, 403, 500, 502, 503, 504, 522, 524, 408, 429]

MSGLOOM_DATA_DIR = os.getenv("MSGLOOM_DATA_DIR", "var/acquisition")
MSGLOOM_DATABASE_URL = os.getenv(
    "MSGLOOM_DATABASE_URL", "sqlite:///var/msgloom.sqlite3"
)
MSGLOOM_RAW_EVIDENCE_DIR = os.getenv(
    "MSGLOOM_RAW_EVIDENCE_DIR", "var/acquisition/raw"
)
MSGLOOM_SOURCE_ID = os.getenv("MSGLOOM_SOURCE_ID", "microsoft-outlook-default")
MS_GRAPH_CLIENT_ID = os.getenv("MSGLOOM_MS_CLIENT_ID", "")
MS_GRAPH_AUTHORITY = os.getenv(
    "MSGLOOM_MS_AUTHORITY", "https://login.microsoftonline.com/common"
)
MS_GRAPH_SCOPES = ["Mail.Read"]
MS_GRAPH_ACCOUNT_USERNAME = os.getenv("MSGLOOM_MS_USERNAME", "")
MS_GRAPH_THROTTLE_MAX_RETRIES = int(
    os.getenv("MSGLOOM_MS_THROTTLE_MAX_RETRIES", "8")
)
MS_GRAPH_THROTTLE_FALLBACK_BASE_SECONDS = int(
    os.getenv("MSGLOOM_MS_THROTTLE_FALLBACK_BASE_SECONDS", "1")
)
MS_GRAPH_THROTTLE_FALLBACK_MAX_SECONDS = int(
    os.getenv("MSGLOOM_MS_THROTTLE_FALLBACK_MAX_SECONDS", "60")
)

MS_GRAPH_TOKEN_CACHE = os.getenv(
    "MSGLOOM_MS_TOKEN_CACHE", "var/auth/msal-token-cache.json"
)

FEED_EXPORT_ENCODING = "utf-8"
