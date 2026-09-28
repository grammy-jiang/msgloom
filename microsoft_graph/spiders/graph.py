"""Graph request construction on native Scrapy spiders and scheduler."""

from __future__ import annotations

from enum import Enum
from typing import Any, ClassVar
from urllib.parse import urlsplit

import scrapy
from scrapy.settings import BaseSettings
from twisted.python.failure import Failure

from microsoft_graph import GRAPH_ROOT
from microsoft_graph.request import GRAPH_OPERATION_META_KEY


class DefaultPrefer(Enum):
    """Distinguish an inherited preference from explicit ``prefer=None``."""

    VALUE = "default"


class MicrosoftGraphSpider(scrapy.Spider):
    """
    Declare Graph scopes and construct requests without application state.

    Authentication remains opt-in. Named bound callbacks and errbacks round
    trip through Scrapy's JOBDIR request serialization. Service-root overrides
    affect transport only, not national-cloud authentication configuration.
    """

    service_root = GRAPH_ROOT
    graph_root = GRAPH_ROOT
    graph_permissions: ClassVar[tuple[str, ...]] = ()
    graph_prefer: ClassVar[str | None] = None

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        root = self.service_root if self.service_root != GRAPH_ROOT else self.graph_root
        self._set_service_root(root)

    def _set_service_root(self, root: str) -> None:
        parsed = urlsplit(root)
        if parsed.scheme not in {"https", "http"} or not parsed.hostname:
            raise ValueError("Graph service root must be an HTTP(S) URL")
        if parsed.query or parsed.fragment or parsed.username or parsed.password:
            raise ValueError("Graph service root must not contain credentials or query")
        self.service_root = self.graph_root = root.rstrip("/")
        self.allowed_domains = [parsed.hostname]

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        if root := crawler.settings.get("MS_GRAPH_SERVICE_ROOT"):
            spider._set_service_root(root)
        return spider

    @classmethod
    def required_graph_permissions(cls, settings: BaseSettings) -> tuple[str, ...]:
        """Declare required scopes for an optional consumer-selected auth layer."""
        return cls.graph_permissions

    @classmethod
    def update_settings(cls, settings: BaseSettings) -> None:
        """Publish scope defaults while preserving explicit consumer settings."""
        super().update_settings(settings)
        if not settings.getlist("MS_GRAPH_SCOPES"):
            settings.set(
                "MS_GRAPH_SCOPES",
                list(cls.required_graph_permissions(settings)),
                priority="default",
            )

    def graph_request(
        self,
        url: str,
        *,
        callback=None,
        errback=None,
        operation: str = "graph",
        cb_kwargs: dict[str, Any] | None = None,
        verbatim_url: bool = False,
        accept: str = "application/json",
        prefer: str | None | DefaultPrefer = DefaultPrefer.VALUE,
        dont_cache: bool = False,
        download_maxsize: int | None = None,
    ) -> scrapy.Request:
        """
        Build a GET request with explicit representation and transport options.

        A leading slash denotes a path relative to the service root. Absolute
        continuation URLs are never joined, decoded, or rebuilt. Callback
        arguments belong to consumers; operation metadata is transport context.
        """
        if url.startswith("/"):
            url = f"{self.graph_root}{url}"
        headers = {"Accept": accept}
        selected_prefer = self.graph_prefer if prefer is DefaultPrefer.VALUE else prefer
        if isinstance(selected_prefer, str):
            headers["Prefer"] = selected_prefer
        meta: dict[str, Any] = {GRAPH_OPERATION_META_KEY: operation}
        if verbatim_url:
            meta["verbatim_url"] = True
        if dont_cache:
            meta["dont_cache"] = True
        if download_maxsize is not None:
            meta["download_maxsize"] = download_maxsize
        return scrapy.Request(
            url,
            callback=callback,
            errback=errback or self.errback,
            headers=headers,
            cb_kwargs=cb_kwargs,
            meta=meta,
        )

    def continuation_request(self, url: str, **kwargs) -> scrapy.Request:
        """Schedule an opaque provider continuation through native Scrapy."""
        return self.graph_request(url, **{**kwargs, "verbatim_url": True})

    def errback(self, failure: Failure) -> Any:
        """Propagate terminal failures; consumers may override this named hook."""
        failure.raiseException()

    @staticmethod
    def _bounded_int(
        raw: str,
        *,
        name: str,
        minimum: int,
        maximum: int | None = None,
    ) -> int:
        """Validate bounded spider arguments before scheduling requests."""
        value = int(raw)
        if value < minimum or (maximum is not None and value > maximum):
            upper = f" and <= {maximum}" if maximum is not None else ""
            raise ValueError(f"{name} must be >= {minimum}{upper}")
        return value
