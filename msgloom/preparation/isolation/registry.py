"""Closed trusted parser registry for isolated process dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from msgloom.preparation.contracts import DocumentFormat, ParserIdentity


@dataclass(frozen=True, slots=True)
class RegistryEntry:
    """One code-reviewed parser target, never supplied by a parse request."""

    formats: tuple[DocumentFormat, ...]
    module: str
    identity: ParserIdentity
    fixture_file: Path | None = None


class TrustedRegistry:
    """Immutable registry used by production and explicit synthetic tests."""

    def __init__(self, entries: tuple[RegistryEntry, ...]) -> None:
        by_format: dict[DocumentFormat, RegistryEntry] = {}
        for entry in entries:
            if not entry.formats:
                raise ValueError("registry entry must own at least one format")
            for format_ in entry.formats:
                if format_ in by_format:
                    raise ValueError("parser format is registered more than once")
                by_format[format_] = entry
        self._by_format = by_format

    def resolve(self, format_: DocumentFormat) -> RegistryEntry:
        """Return the trusted implementation for a detected format."""
        try:
            return self._by_format[format_]
        except KeyError:
            raise ValueError("detected format has no trusted parser") from None


PRODUCTION_REGISTRY = TrustedRegistry(
    (
        RegistryEntry(
            formats=(
                DocumentFormat.MIME,
                DocumentFormat.HTML,
                DocumentFormat.TEXT,
                DocumentFormat.JSON,
            ),
            module="msgloom.preparation.parsers.mime_html",
            identity=ParserIdentity(
                "msgloom.mime-html",
                "1",
                "stdlib-email+selectolax-0.4.12",
            ),
        ),
        RegistryEntry(
            formats=(
                DocumentFormat.XLSX,
                DocumentFormat.XLSM,
                DocumentFormat.XLS,
                DocumentFormat.XLSB,
                DocumentFormat.ODS,
            ),
            module="msgloom.preparation.parsers.excel",
            identity=ParserIdentity(
                "msgloom.excel",
                "1",
                "python-calamine-0.8.2+openpyxl-3.1.5",
            ),
        ),
        RegistryEntry(
            formats=(DocumentFormat.PDF,),
            module="msgloom.preparation.parsers.pdf",
            identity=ParserIdentity(
                "msgloom.pdf",
                "1",
                "pypdfium2-5.13.0",
            ),
        ),
        RegistryEntry(
            formats=(DocumentFormat.DOCX, DocumentFormat.DOC),
            module="msgloom.preparation.parsers.word",
            identity=ParserIdentity(
                "msgloom.word",
                "1",
                "python-docx-1.2.0+lxml-6.1.3",
            ),
        ),
    )
)
