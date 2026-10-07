"""Verify fixed-window Microsoft Calendar delta acquisition."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from scrapy import Request
from scrapy.dupefilters import RFPDupeFilter
from scrapy.http import Response, TextResponse
from scrapy.spidermiddlewares.httperror import HttpError
from scrapy.utils.test import get_crawler
from twisted.python.failure import Failure

from message_ingest.items.acquisition import (
    AcquisitionFailureItem,
    RawHttpEvidenceItem,
)
from message_ingest.items.microsoft.outlook.calendar import (
    OutlookCalendarDeltaCheckpointCandidateItem,
    OutlookCalendarDeltaObservationItem,
    OutlookCalendarEventItem,
)
from message_ingest.spiders.microsoft.outlook.calendar.delta import (
    OutlookCalendarDeltaSpider,
)
from message_ingest.sync.microsoft.outlook.calendar.checkpoints import (
    CalendarDeltaCheckpointStore,
)
from microsoft_graph.protocol import GraphProtocolError

START = "2026-09-27T00:00:00+10:00"
END = "2026-10-04T00:00:00+10:00"


@pytest.mark.parametrize("marker", [False, 0, "deleted", []])
def test_invalid_tombstone_preserves_evidence_before_protocol_failure(
    tmp_path: Path, marker: object
) -> None:
    spider = _spider(tmp_path)
    request = spider._initial_delta_request(reset_count=0)
    output = spider.parse_delta(
        _response(request, {"value": [{"id": "event-1", "@removed": marker}]}),
        **request.cb_kwargs,
    )
    if not isinstance(next(output), RawHttpEvidenceItem):
        pytest.fail("Raw evidence must precede invalid tombstone failure")
    with pytest.raises(
        GraphProtocolError, match="^Calendar @removed value must be an object$"
    ):
        list(output)


@pytest.mark.parametrize(
    ("marker", "kind", "reason"),
    [
        (None, "upsert", None),
        ({}, "removed", None),
        ({"reason": "deleted"}, "removed", "deleted"),
        ({"reason": "changed"}, "removed", "changed"),
        ({"reason": 42}, "removed", None),
    ],
)
def test_tombstone_reason_remains_calendar_policy(
    tmp_path: Path, marker: object, kind: str, reason: str | None
) -> None:
    spider = _spider(tmp_path)
    request = spider._initial_delta_request(reset_count=0)
    output = list(
        spider.parse_delta(
            _response(
                request,
                {
                    "value": [{"id": "event-1", "@removed": marker}],
                    "@odata.deltaLink": "https://graph.microsoft.com/v1.0/state",
                },
            ),
            **request.cb_kwargs,
        )
    )
    observation = next(
        value
        for value in output
        if isinstance(value, OutlookCalendarDeltaObservationItem)
    )
    if (observation.kind, observation.removed_reason) != (kind, reason):
        pytest.fail("Calendar must retain its removal and reason interpretation")
    projected = [
        value for value in output if isinstance(value, OutlookCalendarEventItem)
    ]
    if bool(projected) != (kind == "upsert"):
        pytest.fail("Only Calendar upserts may update the source-wide event")


def _crawler(tmp_path: Path):
    return get_crawler(
        OutlookCalendarDeltaSpider,
        settings_dict={
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "MSGLOOM_SOURCE_ID": "source-1",
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_SOURCE_IDENTITY_REQUIRED": False,
        },
    )


def _spider(tmp_path: Path) -> OutlookCalendarDeltaSpider:
    crawler = _crawler(tmp_path)
    spider = OutlookCalendarDeltaSpider.from_crawler(
        crawler,
        start_datetime=START,
        end_datetime=END,
        page_size="2",
    )
    crawler.spider = spider
    return spider


async def _collect_start(spider: OutlookCalendarDeltaSpider):
    return [value async for value in spider.start()]


def _response(request: Request, payload: dict, *, status: int = 200) -> TextResponse:
    return TextResponse(
        request.url,
        status=status,
        request=request,
        body=json.dumps(payload).encode(),
        encoding="utf-8",
        headers={"Content-Type": "application/json"},
    )


def _http_failure(request: Request, status: int) -> Failure:
    response = Response(request.url, status=status, request=request)
    failure = Failure(HttpError(response, "filtered"))
    failure.__dict__["request"] = request
    return failure


def test_initial_delta_request_uses_fixed_window_and_prefer_page_size(
    tmp_path: Path,
) -> None:
    spider = _spider(tmp_path)
    request = asyncio.run(_collect_start(spider))[0]
    parsed = urlsplit(request.url)
    query = parse_qs(parsed.query)

    if parsed.path != "/v1.0/me/calendarView/delta":
        pytest.fail(f"Unexpected Calendar delta path: {parsed.path}")
    if query.get("startDateTime") != [START] or query.get("endDateTime") != [END]:
        pytest.fail(f"Unexpected Calendar delta scope: {query!r}")
    if "$top" in query:
        pytest.fail("Calendar delta must use Prefer, not $top, for page size")
    prefer = request.headers.get("Prefer", b"").decode()
    if prefer != 'IdType="ImmutableId", odata.maxpagesize=2':
        pytest.fail(f"Unexpected Calendar delta Prefer header: {prefer!r}")
    if request.meta.get("dont_cache") is not True:
        pytest.fail("Expected Calendar delta requests to bypass HTTP cache")
    if spider.base_revision is not None:
        pytest.fail("Expected first Calendar delta round to have no base revision")


def test_committed_checkpoint_resumes_verbatim_and_sets_base_revision(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'catalog.sqlite3'}"
    store = CalendarDeltaCheckpointStore(
        database_url,
        source_id="source-1",
        start_datetime=START,
        end_datetime=END,
    )
    try:
        delta_link = (
            "https://graph.microsoft.com/v1.0/me/calendarView/delta?"
            "$deltatoken=opaque%2Fstate"
        )
        store.write_candidate(
            run_id="seed",
            attempt=0,
            base_revision=None,
            delta_link=delta_link,
            evidence_id="seed-evidence",
            observed_at="2026-09-27T00:00:00+00:00",
        )
        state = store.commit(run_id="seed", attempt=0)
    finally:
        store.close()

    spider = _spider(tmp_path)
    request = asyncio.run(_collect_start(spider))[0]
    if request.url != delta_link:
        pytest.fail(f"Expected opaque committed deltaLink, got {request.url!r}")
    if request.cb_kwargs["from_checkpoint"] is not True:
        pytest.fail("Expected resumed Calendar delta request")
    if request.meta.get("verbatim_url") is not True:
        pytest.fail("Expected committed Calendar deltaLink to remain opaque")
    if spider.base_revision != state.revision:
        pytest.fail("Expected committed revision to become CAS base revision")


def test_delta_page_emits_ordered_changes_upserts_and_opaque_continuation(
    tmp_path: Path,
) -> None:
    spider = _spider(tmp_path)
    request = spider._initial_delta_request(reset_count=0)
    next_link = (
        "https://graph.microsoft.com/v1.0/me/calendarView/delta?"
        "$skiptoken=opaque%2Fpage"
    )
    response = _response(
        request,
        {
            "value": [
                {
                    "id": "event-1",
                    "changeKey": "v2",
                    "subject": "Changed meeting",
                    "start": {"dateTime": "2026-09-28T09:00:00", "timeZone": "UTC"},
                    "end": {"dateTime": "2026-09-28T10:00:00", "timeZone": "UTC"},
                    "type": "singleInstance",
                },
                {
                    "id": "event-2",
                    "@removed": {"reason": "deleted"},
                },
            ],
            "@odata.nextLink": next_link,
        },
    )
    output = list(
        spider.parse_delta(
            response,
            **request.cb_kwargs,
        )
    )

    if not isinstance(output[0], RawHttpEvidenceItem):
        pytest.fail("Expected raw evidence before Calendar delta semantic items")
    observations = [
        value
        for value in output
        if isinstance(value, OutlookCalendarDeltaObservationItem)
    ]
    if [(value.event_id, value.kind) for value in observations] != [
        ("event-1", "upsert"),
        ("event-2", "removed"),
    ]:
        pytest.fail(f"Unexpected Calendar delta observations: {observations!r}")
    if observations[1].removed_reason != "deleted":
        pytest.fail("Expected removed reason to be retained")
    events = [value for value in output if isinstance(value, OutlookCalendarEventItem)]
    if [value.event_id for value in events] != ["event-1"]:
        pytest.fail("Expected only upserts to update global event state")
    continuation = next(value for value in output if isinstance(value, Request))
    if continuation.url != next_link:
        pytest.fail("Expected opaque Calendar delta continuation")
    if continuation.cb_kwargs["page_number"] != 2:
        pytest.fail("Expected Calendar delta page number to advance")


def test_terminal_page_stages_candidate_without_committing(
    tmp_path: Path,
) -> None:
    spider = _spider(tmp_path)
    request = spider._initial_delta_request(reset_count=0)
    delta_link = (
        "https://graph.microsoft.com/v1.0/me/calendarView/delta?$deltatoken=terminal"
    )
    output = list(
        spider.parse_delta(
            _response(request, {"value": [], "@odata.deltaLink": delta_link}),
            **request.cb_kwargs,
        )
    )
    candidate = next(
        value
        for value in output
        if isinstance(value, OutlookCalendarDeltaCheckpointCandidateItem)
    )
    if candidate.delta_link != delta_link or candidate.base_revision is not None:
        pytest.fail(f"Unexpected Calendar delta candidate: {candidate!r}")
    if spider.delta_execution_snapshot()["terminal_delta_seen"] is not True:
        pytest.fail("Expected terminal Calendar delta execution fact")


def test_missing_state_is_integrity_failure(tmp_path: Path) -> None:
    spider = _spider(tmp_path)
    request = spider._initial_delta_request(reset_count=0)
    output = list(
        spider.parse_delta(
            _response(request, {"value": []}),
            **request.cb_kwargs,
        )
    )
    failure = next(
        value for value in output if isinstance(value, AcquisitionFailureItem)
    )
    if failure.error_type != "DeltaStateMissing":
        pytest.fail(f"Unexpected Calendar delta failure: {failure!r}")
    if spider.run_failed is not True:
        pytest.fail("Expected malformed Calendar delta state to fail the run")


def test_expired_checkpoint_restarts_fixed_window_once(tmp_path: Path) -> None:
    spider = _spider(tmp_path)
    request = spider._delta_request(
        "https://graph.microsoft.com/v1.0/me/calendarView/delta?$deltatoken=old",
        page_number=1,
        from_checkpoint=True,
        reset_count=0,
    )
    output = list(spider.errback(_http_failure(request, 410)))

    if not isinstance(output[0], RawHttpEvidenceItem):
        pytest.fail("Expected expired cursor response evidence")
    restarted = next(value for value in output if isinstance(value, Request))
    if "$deltatoken=" in restarted.url:
        pytest.fail("Expected expired Calendar cursor to restart initial delta")
    query = parse_qs(urlsplit(restarted.url).query)
    if query.get("startDateTime") != [START] or query.get("endDateTime") != [END]:
        pytest.fail("Expected reset to preserve exact Calendar window")
    if restarted.cb_kwargs["reset_count"] != 1 or spider.attempt != 1:
        pytest.fail("Expected one new Calendar delta attempt after reset")
    if spider.run_failed:
        pytest.fail("Expected first 410 reset to remain recoverable")


def test_reset_replays_initial_and_continuation_with_native_dupefilter(
    tmp_path: Path,
) -> None:
    spider = _spider(tmp_path)
    dupefilter = RFPDupeFilter(fingerprinter=spider.crawler.request_fingerprinter)
    for reset_count in (0, 1):
        requests = [
            spider._initial_delta_request(reset_count=reset_count),
            spider._delta_request(
                "https://graph.microsoft.com/v1.0/me/calendarView/delta?"
                "$skiptoken=same%2fopaque%2Fpage",
                page_number=2,
                from_checkpoint=False,
                reset_count=reset_count,
            ),
        ]
        for request in requests:
            if dupefilter.request_seen(request):
                pytest.fail("A new reset attempt must replay the entire chain")
            if not dupefilter.request_seen(request):
                pytest.fail("Repeated links within one attempt must be filtered")


def test_repeated_event_keeps_all_entries_and_projects_last_upsert(
    tmp_path: Path,
) -> None:
    spider = _spider(tmp_path)
    request = spider._initial_delta_request(reset_count=0)
    output = list(
        spider.parse_delta(
            _response(
                request,
                {
                    "value": [
                        {"id": "event-1", "changeKey": "v1", "subject": "First"},
                        {"id": "event-1", "changeKey": "v2", "subject": "Last"},
                    ],
                    "@odata.deltaLink": "https://graph.microsoft.com/delta/terminal",
                },
            ),
            **request.cb_kwargs,
        )
    )
    observations = [
        item for item in output if isinstance(item, OutlookCalendarDeltaObservationItem)
    ]
    events = [item for item in output if isinstance(item, OutlookCalendarEventItem)]
    if len(observations) != 2 or len(events) != 1:
        pytest.fail("Expected both delta entries and one current event")
    if events[0].raw["subject"] != "Last":
        pytest.fail("Expected the final upsert from the page")
