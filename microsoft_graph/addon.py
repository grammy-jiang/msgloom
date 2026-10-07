"""Optional transport and logging defaults at Scrapy's add-on priority."""

from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.settings import BaseSettings
from scrapy.utils.misc import load_object

from .extensions.privacy import MicrosoftGraphLogPrivacyExtension
from .middlewares import (
    MicrosoftGraphDiagnosticsMiddleware,
    MicrosoftGraphErrorMiddleware,
)
from .middlewares.retry import PrivacySafeRetryMiddleware


def _safe_retry_defaults(settings: BaseSettings) -> None:
    """
    Replace only the unmodified native retry default.

    Explicit native entries (including ``None``) opt out. A selected safe
    retry disables the native base entry unless that entry was also explicit.
    Other RetryMiddleware subclasses and custom base dictionaries are consumer
    choices. Independent retry implementations should disable native retry in
    the usual Scrapy way; no name-based guess can identify their contract.
    """
    name = "DOWNLOADER_MIDDLEWARES"
    explicit = {
        load_object(key): value for key, value in settings.getdict(name).items()
    }
    if RetryMiddleware in explicit or not settings.getbool("RETRY_ENABLED", True):
        return
    if PrivacySafeRetryMiddleware in explicit:
        if explicit[PrivacySafeRetryMiddleware] is not None:
            settings.setdefault_in_component_priority_dict(name, RetryMiddleware, None)
        return
    if (settings.getpriority(f"{name}_BASE") or 0) > 0:
        return
    components = settings.get_component_priority_dict_with_base(name)
    for component in components:
        cls = load_object(component)
        if (
            isinstance(cls, type)
            and issubclass(cls, RetryMiddleware)
            and cls is not RetryMiddleware
        ):
            return
    settings.setdefault_in_component_priority_dict(name, RetryMiddleware, None)
    settings.setdefault_in_component_priority_dict(
        name, PrivacySafeRetryMiddleware, 550
    )


class MicrosoftGraphAddon:
    """
    Install Graph transport, privacy, and representation identity defaults.

    Authentication, pipelines, application extensions, concurrency, cache, and
    throttle policy remain consumer choices. Explicit component entries,
    including ``None``, win whether expressed as classes or import paths.
    """

    def update_settings(self, settings: BaseSettings) -> None:
        """Merge defaults with Scrapy's public component settings helpers."""
        settings.set(
            "DOWNLOADER_MIDDLEWARES",
            settings.getdict("DOWNLOADER_MIDDLEWARES"),
            priority="addon",
        )
        _safe_retry_defaults(settings)
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
        settings.set(
            "LOG_FORMATTER",
            "microsoft_graph.logformatter.MicrosoftGraphLogFormatter",
            priority="addon",
        )
        settings.set("EXTENSIONS", settings.getdict("EXTENSIONS"), priority="addon")
        # A consumer subclass supplies the complete Graph privacy contract.
        # Even a disabled entry is an explicit choice, just like the base
        # class. Resolve class/path aliases without changing entry priorities.
        privacy_selected = any(
            isinstance(cls := load_object(component), type)
            and issubclass(cls, MicrosoftGraphLogPrivacyExtension)
            for component in settings.getdict("EXTENSIONS")
        )
        if not privacy_selected:
            settings.setdefault_in_component_priority_dict(
                "EXTENSIONS", MicrosoftGraphLogPrivacyExtension, 100
            )
