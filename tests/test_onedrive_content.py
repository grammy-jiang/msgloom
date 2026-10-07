"""Pin explicit content requests and URL-free success/failure evidence."""

import asyncio
import json
from hashlib import sha256
from typing import Any

import pytest
from scrapy.http import Response
from scrapy.spidermiddlewares.httperror import HttpError
from scrapy.utils.request import request_from_dict
from scrapy.utils.test import get_crawler
from twisted.python.failure import Failure

from message_ingest.catalog import Catalog
from message_ingest.catalog.stores.microsoft.onedrive import OneDriveStore
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items.acquisition import AcquisitionFailureItem, RawHttpEvidenceItem
from message_ingest.items.microsoft.onedrive import OneDriveContentItem, OneDriveItem
from message_ingest.spiders.microsoft.onedrive.content import (
    MicrosoftOneDriveContentSpider,
)

SECRET = "http://download.test/private-path-secret?token=SECRET-PREAUTHENTICATED"
BODY = b"\x00explicit file evidence\xff"


def spider(**kwargs):
    crawler = get_crawler(
        MicrosoftOneDriveContentSpider, {"MSGLOOM_MAX_RAW_CONTENT_BYTES": 1234}
    )
    return MicrosoftOneDriveContentSpider.from_crawler(
        crawler, item_ids=json.dumps(["item/+%2F", "second", "second"]), **kwargs
    )


def requests(instance):
    async def start():
        return [request async for request in instance.start()]

    return asyncio.run(start())


def downloaded(request, status=200):
    redirected = request.replace(url=SECRET)
    redirected.meta["redirect_urls"] = [request.url]
    return Response(
        SECRET,
        request=redirected,
        status=status,
        headers={
            "Content-Type": "application/octet-stream",
            "Content-Length": str(len(BODY)),
            "ETag": '"version-1"',
            "Location": SECRET,
            "Content-Location": SECRET,
            "Link": f"<{SECRET}>",
            "Refresh": f"0;url={SECRET}",
            "X-Download-Source": SECRET,
        },
        body=BODY,
    )


def test_content_requests_only_explicit_ids_and_use_native_redirect_controls():
    instance = spider()
    captured = requests(instance)
    if len(captured) != 2:
        pytest.fail("Only distinct explicit item IDs should schedule downloads")
    request = captured[0]
    if not request.url.endswith("/me/drive/items/item%2F%2B%252F/content"):
        pytest.fail("Explicit raw item ID must be encoded exactly once")
    if request.meta.get("allow_offsite") is not True:
        pytest.fail("Native redirect must inherit allow_offsite")
    if (
        not request.meta.get("dont_cache")
        or request.meta.get("download_maxsize") != 1234
    ):
        pytest.fail("Content must bypass cache and enforce configured size limit")
    if request.errback != instance.content_errback:
        pytest.fail("Generic errback can expose the preauthenticated URL")
    restored = request_from_dict(request.to_dict(spider=instance), spider=instance)
    if restored.callback != request.callback or restored.errback != request.errback:
        pytest.fail("Content callbacks must use native serializable context")


def test_redirected_binary_evidence_is_first_and_uses_only_safe_graph_source():
    instance = spider()
    request = requests(instance)[0]
    result = list(instance.parse_content(downloaded(request), **request.cb_kwargs))
    evidence, content = result
    if not isinstance(evidence, RawHttpEvidenceItem) or not isinstance(
        content, OneDriveContentItem
    ):
        pytest.fail("Content must emit raw evidence before metadata")
    if evidence.request_url != request.url or evidence.response_url != request.url:
        pytest.fail("Transport download URL must be replaced with safe Graph source")
    if evidence.response_flags != ["preauthenticated_download_url_redacted"]:
        pytest.fail("Evidence must declare download URL redaction")
    if "SECRET" in json.dumps(evidence.response_headers):
        pytest.fail("Response headers can contain preauthenticated URLs")
    if evidence.response_headers.get("Content-Type") != ["application/octet-stream"]:
        pytest.fail("Safe response entity headers should remain evidence")
    if evidence.response_body != BODY:
        pytest.fail("Sanitization must preserve original binary evidence")
    if (content.content_sha256, content.content_bytes, content.evidence_id) != (
        sha256(BODY).hexdigest(),
        len(BODY),
        evidence.evidence_id,
    ):
        pytest.fail("Content metadata must reference exactly one raw capture")
    if content.response_e_tag != '"version-1"':
        pytest.fail("Safe response ETag was not retained for version proof")
    if any(
        hasattr(content, field) for field in ("body", "raw", "url", "response_body")
    ):
        pytest.fail("Semantic content must not duplicate bytes or transport URLs")


@pytest.mark.parametrize("http_error", [False, True])
def test_failed_download_redacts_urls_headers_and_exception_text(http_error, caplog):
    instance = spider()
    request = requests(instance)[0]
    final = downloaded(request, status=403)
    error = (
        HttpError(final, f"Failure at {SECRET}") if http_error else RuntimeError(SECRET)
    )
    failure: Any = Failure(error)
    failure.request = final.request
    evidence, item = list(instance.content_errback(failure))
    if not isinstance(evidence, RawHttpEvidenceItem) or not isinstance(
        item, AcquisitionFailureItem
    ):
        pytest.fail("Failure evidence must precede failure metadata")
    public_fields = json.dumps(
        {
            "request_url": evidence.request_url,
            "response_url": evidence.response_url,
            "headers": evidence.response_headers,
            "error_message": evidence.error_message,
            "failure_url": item.url,
            "failure_error": item.error_message,
        }
    )
    if (
        "SECRET" in public_fields
        or "private-path-secret" in public_fields
        or "SECRET" in caplog.text
    ):
        pytest.fail("Content errback leaked a preauthenticated transport URL")
    if evidence.request_url != request.url or item.url != request.url:
        pytest.fail("Failure metadata must identify the safe Graph source")
    if not instance.run_failed or item.evidence_id != evidence.evidence_id:
        pytest.fail("Failed download must mark run integrity and retain evidence")
    if http_error and evidence.response_body != BODY:
        pytest.fail("HTTP failure evidence must retain the received bytes")


@pytest.mark.parametrize(
    "item_ids", ["[]", "null", "{}", '[""]', "[1]", '[" item"]', "not-json"]
)
def test_invalid_explicit_item_ids_are_rejected(item_ids):
    with pytest.raises(ValueError):
        MicrosoftOneDriveContentSpider(item_ids=item_ids)


def test_content_request_planning_binds_known_metadata_version(tmp_path):
    database = f"sqlite:///{tmp_path / 'catalog.sqlite3'}"
    catalog = Catalog(database)
    try:
        OneDriveStore(catalog, source_id="source").persist_item(
            OneDriveItem.from_graph(
                {"id": "item", "eTag": '"etag-1"', "cTag": '"ctag-1"', "file": {}},
                observed_at="2026-09-29T00:00:00+00:00",
                evidence_id="metadata-evidence",
                run_id="metadata-run",
            )
        )
    finally:
        catalog.close()
    crawler = get_crawler(
        MicrosoftOneDriveContentSpider,
        {
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_DATABASE_URL": database,
            "MSGLOOM_ONEDRIVE_SOURCE_ID": "source",
            "MSGLOOM_MAX_RAW_CONTENT_BYTES": 1234,
        },
    )
    instance = MicrosoftOneDriveContentSpider.from_crawler(crawler, item_ids='["item"]')
    try:
        request = requests(instance)[0]
        if request.cb_kwargs.get("planned_e_tag") != '"etag-1"':
            pytest.fail("Content request did not bind the current metadata eTag")
        if request.cb_kwargs.get("planned_c_tag") != '"ctag-1"':
            pytest.fail("Documented file-content cTag was not retained")
        if request.cb_kwargs.get("planned_metadata_evidence_id") != "metadata-evidence":
            pytest.fail("Content planning lost the exact metadata observation")
    finally:
        CatalogService.from_crawler(crawler).close()
