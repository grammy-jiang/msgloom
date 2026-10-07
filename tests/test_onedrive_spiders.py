"""Verify OneDrive traversal, provenance, source priority, and cursor use."""

import asyncio
import importlib
import json

import pytest
from scrapy import Request
from scrapy.crawler import Crawler
from scrapy.http import TextResponse
from scrapy.settings import Settings
from scrapy.spidermiddlewares.httperror import HttpError
from scrapy.utils.request import request_from_dict
from scrapy.utils.test import get_crawler
from twisted.python.failure import Failure

from message_ingest.items.acquisition import AcquisitionFailureItem, RawHttpEvidenceItem
from message_ingest.items.microsoft.onedrive import (
    OneDriveDeltaCheckpointCandidateItem,
    OneDriveDeltaResyncAttemptItem,
    OneDriveDeltaResyncObservationItem,
    OneDriveDriveItem,
    OneDriveItem,
)
from message_ingest.spiders.microsoft.onedrive._base import OneDriveSpider
from message_ingest.spiders.microsoft.onedrive.content import (
    MicrosoftOneDriveContentSpider,
)
from message_ingest.spiders.microsoft.onedrive.delta import MicrosoftOneDriveDeltaSpider
from message_ingest.spiders.microsoft.onedrive.discover import (
    MicrosoftOneDriveDiscoverSpider,
)
from message_ingest.spiders.microsoft.outlook.email.discover import (
    OutlookDiscoverSpider,
)
from message_ingest.spiders.microsoft.todo.discover import MicrosoftTodoDiscoverSpider

CLASSES = (
    MicrosoftOneDriveDiscoverSpider,
    MicrosoftOneDriveDeltaSpider,
    MicrosoftOneDriveContentSpider,
)
OPAQUE = "https://graph.microsoft.com/v1.0/me/drive/root/delta?z=%2f&x=+&x=%20&token=a%2Bb%252F"


def spider[SpiderT: OneDriveSpider](
    cls: type[SpiderT], settings=None, **kwargs
) -> SpiderT:
    selected = {
        "MSGLOOM_SOURCE_ID": "onedrive-test-source",
        "MSGLOOM_DATABASE_URL": "sqlite:///:memory:",
        **(settings or {}),
    }
    crawler = get_crawler(cls, selected)
    return cls.from_crawler(crawler, **kwargs)


def first(instance):
    async def start():
        return await anext(instance.start())

    return asyncio.run(start())


def response(request, payload):
    return TextResponse(
        request.url,
        request=request,
        body=json.dumps(payload).encode(),
        encoding="utf-8",
    )


def parse(request, payload):
    if request.callback is None:
        pytest.fail("OneDrive request requires a named callback")
    return list(request.callback(response(request, payload), **request.cb_kwargs))


@pytest.mark.parametrize("cls", CLASSES)
@pytest.mark.parametrize("override", [None, "explicit-source"])
def test_onedrive_source_priority_and_product_isolation(cls, override):
    settings = Settings()
    settings.setmodule("message_ingest.settings", priority="project")
    settings.set("MSGLOOM_ONEDRIVE_SOURCE_ID", "onedrive-source", priority="project")
    original = settings["MSGLOOM_SOURCE_ID"]
    if override:
        settings.set("MSGLOOM_SOURCE_ID", override, priority="cmdline")
    crawler = Crawler(cls, settings)
    if crawler.settings["MSGLOOM_SOURCE_ID"] != (override or "onedrive-source"):
        pytest.fail("OneDrive must use its own source and honor cmdline priority")
    if crawler.settings.getlist("MS_GRAPH_SCOPES") != ["Files.Read"]:
        pytest.fail("OneDrive needs Files.Read only")
    outlook = Crawler(OutlookDiscoverSpider, settings)
    todo = Crawler(MicrosoftTodoDiscoverSpider, settings)
    if outlook.settings["MSGLOOM_SOURCE_ID"] != (override or original):
        pytest.fail("OneDrive changed Outlook source selection")
    if todo.settings["MSGLOOM_SOURCE_ID"] != (
        override or settings["MSGLOOM_TODO_SOURCE_ID"]
    ):
        pytest.fail("OneDrive changed To Do source selection")
    for key in ("DOWNLOADER_MIDDLEWARES", "LOG_FORMATTER", "CONCURRENT_ITEMS"):
        if crawler.settings[key] != settings[key]:
            pytest.fail(f"OneDrive replaced a shared framework contract: {key}")
    expected_fingerprinter = (
        "message_ingest.fingerprints.microsoft.onedrive.OneDriveDeltaRequestFingerprinter"
        if cls is MicrosoftOneDriveDeltaSpider
        else settings["REQUEST_FINGERPRINTER_CLASS"]
    )
    if crawler.settings["REQUEST_FINGERPRINTER_CLASS"] != expected_fingerprinter:
        pytest.fail("OneDrive request fingerprinting changed outside delta reset needs")
    if crawler.settings.getdict("ITEM_PIPELINES") != {
        "message_ingest.pipelines.evidence.RawEvidencePipeline": 200,
        "message_ingest.acquisition.evidence_link.EvidenceLinkPipeline": 250,
        "message_ingest.pipelines.microsoft.onedrive.OneDrivePipeline": 300,
    }:
        pytest.fail("OneDrive persistence must follow committed evidence linking")


def test_onedrive_source_default_and_environment(monkeypatch):
    import message_ingest.settings as settings_module

    monkeypatch.delenv("MSGLOOM_ONEDRIVE_SOURCE_ID", raising=False)
    try:
        importlib.reload(settings_module)
        if settings_module.MSGLOOM_ONEDRIVE_SOURCE_ID != "microsoft-onedrive-default":
            pytest.fail("OneDrive requires an isolated default source")
        monkeypatch.setenv("MSGLOOM_ONEDRIVE_SOURCE_ID", "environment-drive")
        importlib.reload(settings_module)
        if settings_module.MSGLOOM_ONEDRIVE_SOURCE_ID != "environment-drive":
            pytest.fail("OneDrive source must read its dedicated environment value")
    finally:
        monkeypatch.undo()
        importlib.reload(settings_module)


def test_discovery_emits_drive_then_root_children_without_recursion():
    instance = spider(MicrosoftOneDriveDiscoverSpider)
    request = first(instance)
    if request.url != "https://graph.microsoft.com/v1.0/me/drive":
        pytest.fail("Discovery must fetch signed-in drive metadata first")
    output = parse(request, {"id": "drive", "name": "", "quota": {"used": 0}})
    if not isinstance(output[0], RawHttpEvidenceItem) or not isinstance(
        output[1], OneDriveDriveItem
    ):
        pytest.fail("Drive evidence must precede its projection")
    if output[1].evidence_id != output[0].evidence_id:
        pytest.fail("Drive observation lost its evidence link")
    children = output[2]
    if (
        children.url
        != "https://graph.microsoft.com/v1.0/me/drive/root/children?%24top=100"
    ):
        pytest.fail("Discovery must fetch only root children")
    page = parse(children, {"value": [{"id": "folder", "folder": {"childCount": 10}}]})
    if len(page) != 2 or not isinstance(page[1], OneDriveItem):
        pytest.fail("Root discovery must not recurse or fetch file content")
    if page[1].run_id != instance.run_id or page[1].evidence_id != page[0].evidence_id:
        pytest.fail("Drive item observation lost provenance")


def test_discovery_follows_opaque_pagination_and_is_evidence_first_on_error():
    instance = spider(MicrosoftOneDriveDiscoverSpider)
    request = parse(first(instance), {"id": "drive"})[2]
    output = parse(request, {"value": [], "@odata.nextLink": OPAQUE})
    if output[1].url != OPAQUE or not output[1].meta.get("verbatim_url"):
        pytest.fail("Opaque nextLink bytes changed")
    restored = request_from_dict(output[1].to_dict(spider=instance), spider=instance)
    if restored.callback != request.callback or restored.errback != instance.errback:
        pytest.fail("Callbacks must remain native and serializable")
    callback = request.callback
    if callback is None:
        pytest.fail("Expected callback")
    stream = callback(response(request, {"value": None}), **request.cb_kwargs)
    if not isinstance(next(stream), RawHttpEvidenceItem):
        pytest.fail("Malformed pages must still emit evidence first")
    with pytest.raises(ValueError):
        next(stream)


def test_delta_emits_deleted_entries_then_terminal_candidate_and_opaque_requests():
    instance = spider(MicrosoftOneDriveDeltaSpider, page_size="2")
    request = first(instance)
    if not request.url.endswith("/me/drive/root/delta?%24top=2"):
        pytest.fail("Initial delta must enumerate hierarchy metadata")
    if request.meta.get("dont_cache") is not True:
        pytest.fail("Delta requests must bypass HTTP cache")
    output = parse(
        request,
        {"value": [{"id": "deleted-id", "deleted": {}}], "@odata.nextLink": OPAQUE},
    )
    if not isinstance(output[0], RawHttpEvidenceItem) or output[1].deleted != {}:
        pytest.fail("Delta must retain deletion facets after evidence")
    next_request = output[2]
    if not isinstance(next_request, Request) or next_request.url != OPAQUE:
        pytest.fail("Delta continuation must remain opaque")
    if not next_request.meta.get("dont_cache") or not next_request.meta.get(
        "verbatim_url"
    ):
        pytest.fail("Continuation must bypass cache and preserve URL bytes")
    terminal = parse(
        next_request, {"value": [], "@odata.deltaLink": OPAQUE + "&final=1"}
    )
    candidate = terminal[1]
    if len(terminal) != 2 or not isinstance(
        candidate, OneDriveDeltaCheckpointCandidateItem
    ):
        pytest.fail("Terminal delta must emit exactly one checkpoint candidate")
    if (
        candidate.delta_link != OPAQUE + "&final=1"
        or candidate.evidence_id != terminal[0].evidence_id
        or candidate.run_id != instance.run_id
        or candidate.base_revision is not None
        or not instance.terminal_delta_seen
    ):
        pytest.fail("Terminal candidate lost exact cursor or durable-run context")
    for key in instance.crawler.stats.get_stats():
        if "deleted-id" in key:
            pytest.fail("OneDrive stat keys must not contain provider IDs")


@pytest.mark.parametrize(
    "payload",
    [
        {"value": []},
        {"value": [], "@odata.nextLink": OPAQUE, "@odata.deltaLink": OPAQUE},
        {"value": [], "@odata.deltaLink": ""},
    ],
)
def test_invalid_delta_cannot_produce_candidate(payload):
    instance = spider(MicrosoftOneDriveDeltaSpider)
    request = first(instance)
    stream = instance.parse_delta(response(request, payload), **request.cb_kwargs)
    if not isinstance(next(stream), RawHttpEvidenceItem):
        pytest.fail("Invalid delta still requires evidence first")
    with pytest.raises(ValueError):
        list(stream)
    if instance.terminal_delta_seen:
        pytest.fail("Invalid delta must not mark terminal completion")


@pytest.mark.parametrize("cls", CLASSES)
def test_onedrive_refuses_unvalidated_jobdir(cls, tmp_path):
    crawler = get_crawler(
        cls,
        {
            "JOBDIR": str(tmp_path / "job"),
            "MSGLOOM_SOURCE_ID": "onedrive-test-source",
            "MSGLOOM_DATABASE_URL": "sqlite:///:memory:",
        },
    )
    with pytest.raises(ValueError, match="does not support JOBDIR"):
        cls.from_crawler(crawler, item_ids='["item"]')


@pytest.mark.parametrize("cls", CLASSES[:2])
@pytest.mark.parametrize("size", ["0", "1001", "invalid"])
def test_onedrive_rejects_invalid_page_sizes(cls, size):
    with pytest.raises(ValueError):
        cls(page_size=size)


class _RequestFailure(Failure):
    """Carry the request that Scrapy attaches to downloader failures."""

    request: Request


def _http_failure(request, *, location=None):
    headers = {"Location": location} if location is not None else {}
    failed = TextResponse(
        request.url,
        request=request,
        status=410,
        headers=headers,
        body=b'{"error":{"code":"resyncChangesApplyDifferences"}}',
        encoding="utf-8",
    )
    failure = _RequestFailure(HttpError(failed, "synthetic gone"))
    failure.request = request
    return failure


def test_delta_410_valid_location_starts_one_verbatim_staged_resync():
    instance = spider(MicrosoftOneDriveDeltaSpider)
    instance.base_revision = 3
    expired = instance._delta_request(
        OPAQUE, page_number=1, reset_attempt=0, verbatim=True
    )
    output = list(instance.errback(_http_failure(expired, location=OPAQUE)))
    if len(output) != 3:
        pytest.fail("Valid 410 must emit evidence, durable attempt, and one request")
    evidence, attempt, reset = output
    if not isinstance(evidence, RawHttpEvidenceItem) or not isinstance(
        attempt, OneDriveDeltaResyncAttemptItem
    ):
        pytest.fail("410 reset lost evidence-first durable attempt ordering")
    if any(name.lower() == "location" for name in evidence.response_headers):
        pytest.fail("Opaque reset Location leaked into retained response headers")
    if "onedrive_delta_resync_location_redacted" not in evidence.response_flags:
        pytest.fail("410 evidence did not declare Location redaction")
    if (
        not isinstance(reset, Request)
        or reset.url != OPAQUE
        or not reset.meta.get("verbatim_url")
        or not reset.meta.get("dont_cache")
        or reset.cb_kwargs.get("reset_attempt") != 1
        or reset.cb_kwargs.get("page_number") != 1
    ):
        pytest.fail("Fresh resync did not preserve the allowed Location verbatim")
    if instance.crawler.request_fingerprinter.fingerprint(expired) == (
        instance.crawler.request_fingerprinter.fingerprint(reset)
    ):
        pytest.fail("Same-URL reset was not separated from the expired chain")

    terminal = parse(
        reset,
        {
            "value": [{"id": "synthetic", "name": "server"}],
            "@odata.deltaLink": OPAQUE + "&reset=done",
        },
    )
    if not isinstance(terminal[1], OneDriveDeltaResyncObservationItem):
        pytest.fail("Reset enumeration updated current items instead of staging")
    if not isinstance(terminal[2], OneDriveDeltaCheckpointCandidateItem):
        pytest.fail("Reset terminal page did not stage a checkpoint candidate")
    staged = terminal[1]
    if staged.base_revision != 3 or staged.page_number != 1 or staged.entry_index != 0:
        pytest.fail("Reset sighting lost base revision or durable ordering")


@pytest.mark.parametrize(
    "location",
    [None, "/v1.0/me/drive/root/delta", "https://off-host.invalid/v1.0/delta"],
)
def test_delta_410_missing_invalid_or_offhost_location_fails_closed(location):
    instance = spider(MicrosoftOneDriveDeltaSpider)
    instance.base_revision = 1
    expired = instance._delta_request(
        OPAQUE, page_number=1, reset_attempt=0, verbatim=True
    )
    output = list(instance.errback(_http_failure(expired, location=location)))
    if len(output) != 2 or not isinstance(output[1], AcquisitionFailureItem):
        pytest.fail("Unsafe 410 Location must become one terminal acquisition failure")
    if any(isinstance(value, Request) for value in output) or not instance.run_failed:
        pytest.fail("Unsafe 410 Location scheduled work or preserved clean integrity")


def test_delta_second_410_in_reset_attempt_fails_closed():
    instance = spider(MicrosoftOneDriveDeltaSpider)
    instance.base_revision = 1
    expired = instance._delta_request(
        OPAQUE, page_number=1, reset_attempt=0, verbatim=True
    )
    first = list(instance.errback(_http_failure(expired, location=OPAQUE)))
    reset = first[-1]
    if not isinstance(reset, Request):
        pytest.fail("Fixture failed to start reset")
    second = list(instance.errback(_http_failure(reset, location=OPAQUE)))
    if len(second) != 2 or not isinstance(second[1], AcquisitionFailureItem):
        pytest.fail("Second 410 must fail instead of starting another reset")
    if any(isinstance(value, OneDriveDeltaResyncAttemptItem) for value in second):
        pytest.fail("Second 410 created a second reset attempt")
