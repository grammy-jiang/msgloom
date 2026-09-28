"""Optional transport defaults at Scrapy's add-on priority."""

from scrapy.settings import BaseSettings

from .middlewares import (
    MicrosoftGraphDiagnosticsMiddleware,
    MicrosoftGraphErrorMiddleware,
)


class MicrosoftGraphAddon:
    """
    Install Graph transport diagnostics, retries, and representation identity.

    Authentication, pipelines, extensions, concurrency, cache, and throttle
    policy remain consumer choices. Explicit component entries, including
    ``None``, win whether expressed as classes or import paths.
    """

    def update_settings(self, settings: BaseSettings) -> None:
        """Merge defaults with Scrapy's public component settings helpers."""
        settings.set(
            "DOWNLOADER_MIDDLEWARES",
            settings.getdict("DOWNLOADER_MIDDLEWARES"),
            priority="addon",
        )
        settings.setdefault_in_component_priority_dict(
            "DOWNLOADER_MIDDLEWARES", MicrosoftGraphErrorMiddleware, 555
        )
        settings.setdefault_in_component_priority_dict(
            "DOWNLOADER_MIDDLEWARES", MicrosoftGraphDiagnosticsMiddleware, 960
        )
        settings.set(
            "REQUEST_FINGERPRINTER_CLASS",
            "microsoft_graph.fingerprints.GraphRequestFingerprinter",
            priority="addon",
        )
