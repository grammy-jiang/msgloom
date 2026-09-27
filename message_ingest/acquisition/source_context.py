"""Stable source context for request identity and JOBDIR isolation."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from scrapy.exceptions import NotConfigured
from sqlalchemy.engine import make_url

_SOURCE_DOMAIN = b"msgloom-source-context-v1\0"
_JOB_DOMAIN = b"msgloom-job-context-v1\0"
_JOB_MARKER = ".msgloom-source-context-v1"


class SourceContextMismatch(RuntimeError):
    """Persisted execution/cache context belongs to another logical source."""


def source_context_digest(source_id: str) -> bytes:
    """Return a domain-separated digest without exposing the source ID."""
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError("MSGLOOM_SOURCE_ID must not be empty")
    if source_id != source_id.strip():
        raise ValueError(
            "MSGLOOM_SOURCE_ID must not contain surrounding whitespace"
        )
    return hashlib.sha256(_SOURCE_DOMAIN + source_id.encode("utf-8")).digest()


def source_catalog_context_digest(source_id: str, database_url: str) -> str:
    """Hash source plus normalized catalog identity for persistent context."""
    source_digest = source_context_digest(source_id)
    catalog_key = _catalog_context_key(database_url)
    material = (
        _JOB_DOMAIN + source_digest + b"\0" + catalog_key.encode("utf-8")
    )
    return hashlib.sha256(material).hexdigest()


def ensure_jobdir_context(
    jobdir: str, source_id: str, database_url: str
) -> None:
    """
    Create or verify a private JOBDIR ownership marker before Scheduler opens.

    A non-empty legacy JOBDIR without a marker is refused because queued
    requests cannot be proven to belong to the current source/catalog.
    """
    if not jobdir:
        return
    directory = Path(jobdir)
    marker = directory / _JOB_MARKER
    expected = source_catalog_context_digest(source_id, database_url)

    if marker.exists():
        actual = marker.read_text(encoding="ascii").strip()
        if actual != expected:
            raise SourceContextMismatch(
                "JOBDIR belongs to a different msgloom source/catalog context"
            )
        return

    if directory.exists():
        entries = list(directory.iterdir())
        if entries:
            raise SourceContextMismatch(
                "Legacy non-empty JOBDIR has no msgloom source-context "
                "marker; "
                "refusing unsafe resume"
            )
    else:
        directory.mkdir(parents=True, mode=0o700)
    os.chmod(directory, 0o700)

    try:
        fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        actual = marker.read_text(encoding="ascii").strip()
        if actual != expected:
            raise SourceContextMismatch(
                "JOBDIR source-context marker changed during initialization"
            )
        return
    with os.fdopen(fd, "w", encoding="ascii") as handle:
        handle.write(expected + "\n")
    os.chmod(marker, 0o600)


class SourceContextExtension:
    """Validate JOBDIR ownership before Scrapy constructs the Scheduler."""

    @classmethod
    def from_crawler(cls, crawler):
        """Apply the guard only when JOBDIR persistence is configured."""
        jobdir = crawler.settings.get("JOBDIR") or ""
        if not jobdir:
            raise NotConfigured("JOBDIR source-context guard not needed")
        ensure_jobdir_context(
            jobdir,
            crawler.settings["MSGLOOM_SOURCE_ID"],
            crawler.settings["MSGLOOM_DATABASE_URL"],
        )
        crawler.stats.set_value("msgloom/source_context/jobdir_verified", True)
        return cls()


def _catalog_context_key(database_url: str) -> str:
    """Normalize the currently supported SQLite catalog location."""
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite":
        return url.render_as_string(hide_password=True)
    database = url.database
    if not database or database == ":memory:":
        return "sqlite::memory:"
    return f"sqlite:{Path(database).resolve()}"
