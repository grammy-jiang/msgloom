"""Verify source-scoped request and JOBDIR isolation."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest
from scrapy import Request
from scrapy.extensions.httpcache import FilesystemCacheStorage
from scrapy.http import Response
from scrapy.utils.misc import build_from_crawler
from scrapy.utils.test import get_crawler

from message_ingest.acquisition.source_context import (
    SourceContextExtension,
    SourceContextMismatch,
    ensure_jobdir_context,
    source_catalog_context_digest,
)
from message_ingest.providers.microsoft_graph.fingerprints import (
    RepresentationAwareRequestFingerprinter,
)
from message_ingest.spiders.outlook_discover import OutlookDiscoverSpider

ROOT = Path(__file__).parents[1]


def _crawler(tmp_path: Path, *, source_id: str, jobdir: str = ""):
    return get_crawler(
        OutlookDiscoverSpider,
        settings_dict={
            "MSGLOOM_SOURCE_ID": source_id,
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "JOBDIR": jobdir,
        },
    )


def test_graph_fingerprint_is_isolated_by_logical_source(tmp_path: Path) -> None:
    request = Request("https://graph.microsoft.com/v1.0/me/messages")
    one = RepresentationAwareRequestFingerprinter.from_crawler(
        _crawler(tmp_path, source_id="source-one")
    )
    two = RepresentationAwareRequestFingerprinter.from_crawler(
        _crawler(tmp_path, source_id="source-two")
    )

    if one.fingerprint(request) == two.fingerprint(request):
        pytest.fail("Expected Graph cache/scheduler identity to differ by source")


def test_non_graph_fingerprint_remains_source_neutral(tmp_path: Path) -> None:
    request = Request("https://example.test/resource")
    one = RepresentationAwareRequestFingerprinter.from_crawler(
        _crawler(tmp_path, source_id="source-one")
    )
    two = RepresentationAwareRequestFingerprinter.from_crawler(
        _crawler(tmp_path, source_id="source-two")
    )

    if one.fingerprint(request) != two.fingerprint(request):
        pytest.fail("Expected non-Graph request identity to remain native")


def test_fingerprint_does_not_embed_raw_source_id(tmp_path: Path) -> None:
    source_id = "private-source-label"
    request = Request("https://graph.microsoft.com/v1.0/me/messages")
    fp = RepresentationAwareRequestFingerprinter.from_crawler(
        _crawler(tmp_path, source_id=source_id)
    ).fingerprint(request)

    if source_id.encode() in fp:
        pytest.fail("Expected request fingerprint not to expose raw source ID")


def test_fresh_jobdir_gets_private_source_context_marker(tmp_path: Path) -> None:
    jobdir = tmp_path / "job"
    database_url = f"sqlite:///{tmp_path / 'catalog.sqlite3'}"

    ensure_jobdir_context(str(jobdir), "source-1", database_url)

    marker = jobdir / ".msgloom-source-context-v1"
    if marker.read_text().strip() != source_catalog_context_digest("source-1", database_url):
        pytest.fail("Expected JOBDIR marker to contain only context digest")
    if marker.stat().st_mode & 0o777 != 0o600:
        pytest.fail("Expected JOBDIR context marker mode 0600")
    if jobdir.stat().st_mode & 0o777 != 0o700:
        pytest.fail("Expected JOBDIR mode 0700")


def test_jobdir_marker_rejects_source_or_catalog_change(tmp_path: Path) -> None:
    jobdir = tmp_path / "job"
    database_url = f"sqlite:///{tmp_path / 'one.sqlite3'}"
    ensure_jobdir_context(str(jobdir), "source-1", database_url)

    with pytest.raises(SourceContextMismatch):
        ensure_jobdir_context(str(jobdir), "source-2", database_url)
    with pytest.raises(SourceContextMismatch):
        ensure_jobdir_context(
            str(jobdir),
            "source-1",
            f"sqlite:///{tmp_path / 'two.sqlite3'}",
        )


def test_legacy_nonempty_jobdir_without_marker_is_rejected(tmp_path: Path) -> None:
    jobdir = tmp_path / "job"
    jobdir.mkdir()
    (jobdir / "spider.state").write_bytes(b"legacy")

    with pytest.raises(SourceContextMismatch, match="Legacy non-empty JOBDIR"):
        ensure_jobdir_context(
            str(jobdir),
            "source-1",
            f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
        )


def test_source_context_extension_validates_before_scheduler_use(tmp_path: Path) -> None:
    jobdir = tmp_path / "job"
    crawler = _crawler(tmp_path, source_id="source-1", jobdir=str(jobdir))

    extension = build_from_crawler(SourceContextExtension, crawler)

    if not isinstance(extension, SourceContextExtension):
        pytest.fail("Expected SourceContextExtension to build")
    if crawler.stats.get_value("msgloom/source_context/jobdir_verified") is not True:
        pytest.fail("Expected JOBDIR context verification stat")


def test_context_digest_is_domain_separated_from_plain_source_hash(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'catalog.sqlite3'}"
    digest = source_catalog_context_digest("source-1", database_url)
    plain = hashlib.sha256(b"source-1").hexdigest()

    if digest == plain:
        pytest.fail("Expected JOBDIR digest to be domain separated")


def test_graph_fingerprint_is_isolated_by_catalog_for_same_source(
    tmp_path: Path,
) -> None:
    request = Request("https://graph.microsoft.com/v1.0/me/messages")
    one = get_crawler(
        OutlookDiscoverSpider,
        settings_dict={
            "MSGLOOM_SOURCE_ID": "source-1",
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'one.sqlite3'}",
        },
    )
    two = get_crawler(
        OutlookDiscoverSpider,
        settings_dict={
            "MSGLOOM_SOURCE_ID": "source-1",
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'two.sqlite3'}",
        },
    )
    first = RepresentationAwareRequestFingerprinter.from_crawler(one)
    second = RepresentationAwareRequestFingerprinter.from_crawler(two)

    if first.fingerprint(request) == second.fingerprint(request):
        pytest.fail("Expected Graph cache identity to differ by catalog context")


def test_source_context_rejects_surrounding_whitespace(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="surrounding whitespace"):
        source_catalog_context_digest(
            " source-1 ",
            f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
        )



@pytest.mark.parametrize("change", ["source", "catalog"])
def test_real_cli_rejects_jobdir_from_other_context_before_download(
    tmp_path: Path,
    change: str,
) -> None:
    jobdir = tmp_path / "job"
    first_db = f"sqlite:///{tmp_path / 'one.sqlite3'}"
    ensure_jobdir_context(str(jobdir), "source-one", first_db)

    source_id = "source-two" if change == "source" else "source-one"
    database_url = (
        f"sqlite:///{tmp_path / 'two.sqlite3'}"
        if change == "catalog"
        else first_db
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scrapy",
            "outlook_discover",
            "-s",
            f"JOBDIR={jobdir}",
            "-s",
            f"MSGLOOM_SOURCE_ID={source_id}",
            "-s",
            f"MSGLOOM_DATABASE_URL={database_url}",
            "-s",
            "MS_GRAPH_AUTH_METHOD=none",
            "-L",
            "INFO",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    output = result.stdout + result.stderr
    if result.returncode == 0:
        pytest.fail("Expected mismatched JOBDIR context to fail the command")
    if "different msgloom source/catalog context" not in output:
        pytest.fail("Expected explicit JOBDIR source-context mismatch")
    if "downloader/request_count" in output:
        pytest.fail("Expected JOBDIR rejection before any downloader request")



def test_sqlite_tilde_path_does_not_alias_expanded_home_path(
    tmp_path: Path,
) -> None:
    literal_tilde = source_catalog_context_digest(
        "source-1",
        "sqlite:///~/catalog.sqlite3",
    )
    expanded_home = source_catalog_context_digest(
        "source-1",
        f"sqlite:///{Path.home() / 'catalog.sqlite3'}",
    )

    if literal_tilde == expanded_home:
        pytest.fail(
            "Expected source context to follow SQLAlchemy literal-tilde path semantics"
        )



def test_native_filesystem_cache_does_not_cross_graph_sources(
    tmp_path: Path,
) -> None:
    cache_dir = tmp_path / "shared-cache"
    database_url = f"sqlite:///{tmp_path / 'catalog.sqlite3'}"
    one = get_crawler(
        OutlookDiscoverSpider,
        settings_dict={
            "MSGLOOM_SOURCE_ID": "source-one",
            "MSGLOOM_DATABASE_URL": database_url,
            "HTTPCACHE_DIR": str(cache_dir),
            "REQUEST_FINGERPRINTER_CLASS": (
                "message_ingest.providers.microsoft_graph.fingerprints."
                "RepresentationAwareRequestFingerprinter"
            ),
        },
    )
    two = get_crawler(
        OutlookDiscoverSpider,
        settings_dict={
            "MSGLOOM_SOURCE_ID": "source-two",
            "MSGLOOM_DATABASE_URL": database_url,
            "HTTPCACHE_DIR": str(cache_dir),
            "REQUEST_FINGERPRINTER_CLASS": (
                "message_ingest.providers.microsoft_graph.fingerprints."
                "RepresentationAwareRequestFingerprinter"
            ),
        },
    )
    spider_one = OutlookDiscoverSpider.from_crawler(one)
    spider_two = OutlookDiscoverSpider.from_crawler(two)
    one.spider = spider_one
    two.spider = spider_two
    request_one = Request("https://graph.microsoft.com/v1.0/me/messages")
    request_two = Request("https://graph.microsoft.com/v1.0/me/messages")
    response = Response(
        request_one.url,
        status=200,
        body=b"source-one",
        request=request_one,
    )
    storage_one = FilesystemCacheStorage(one.settings)
    storage_two = FilesystemCacheStorage(two.settings)
    storage_one.open_spider(spider_one)
    storage_two.open_spider(spider_two)

    storage_one.store_response(spider_one, request_one, response)

    cached_for_one = storage_one.retrieve_response(spider_one, request_one)
    cached_for_two = storage_two.retrieve_response(spider_two, request_two)
    if cached_for_one is None or cached_for_one.body != b"source-one":
        pytest.fail("Expected source-one to retrieve its own Graph cache entry")
    if cached_for_two is not None:
        pytest.fail("Expected source-two not to reuse source-one Graph cache entry")
