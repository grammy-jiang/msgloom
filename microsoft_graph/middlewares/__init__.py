"""Scrapy downloader middleware for Microsoft Graph transport and auth."""

from .authentication import (
    MicrosoftGraphDelegatedAuthMiddleware,
    MicrosoftGraphDeviceCodeAuthMiddleware,
    MicrosoftGraphInteractiveAuthMiddleware,
)
from .diagnostics import MicrosoftGraphDiagnosticsMiddleware
from .errors import MicrosoftGraphErrorMiddleware
from .retry import PrivacySafeRetryMiddleware

__all__ = [
    "MicrosoftGraphDelegatedAuthMiddleware",
    "MicrosoftGraphDeviceCodeAuthMiddleware",
    "MicrosoftGraphDiagnosticsMiddleware",
    "MicrosoftGraphErrorMiddleware",
    "MicrosoftGraphInteractiveAuthMiddleware",
    "PrivacySafeRetryMiddleware",
]
