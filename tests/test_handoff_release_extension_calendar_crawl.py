"""Exercise Calendar release through native crawls and persistent JOBDIR."""

import json
import pickle
import subprocess
import sys

import pytest
from sqlalchemy import select
from test_calendar_crawls import (
    DISCOVER_COMMAND,
    END,
    ROOT,
    START,
    WINDOW_COMMAND,
    _settings,
    calendar_server,
)
from test_calendar_read_resume_crawl import WINDOW_PAUSE_SETUP

from message_ingest.acquisition.handoff import AcquisitionStream
from message_ingest.catalog import Catalog
from message_ingest.catalog.models.handoff import AcquisitionReleaseGroup
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore

__all__ = ["calendar_server"]
ENABLE = """
import message_ingest.settings as settings
settings.EXTENSIONS["message_ingest.extensions.handoff.HandoffReleaseExtension"] = 70
"""


def run(tmp_path, root, *, window=True, direct=False, pause=False, job=False):
    code = WINDOW_COMMAND if window else DISCOVER_COMMAND
    setup = ENABLE + (WINDOW_PAUSE_SETUP if pause else "")
    code = code.replace("execute([", setup + "\nexecute([")
    args = ["--start", START, "--end", END] if window else []
    if direct:
        mode = "window" if window else "discover"
        code = code.replace(
            '"microsoft", "outlook", "calendar", "' + mode + '"',
            '"crawl", "outlook_calendar_' + mode + '"',
        )
        args = (
            ["-a", f"start_datetime={START}", "-a", f"end_datetime={END}"]
            if window
            else []
        )
    if job:
        args += ["-s", f"JOBDIR={tmp_path / 'job'}", "-s", "SCHEDULER_DEBUG=True"]
    result = subprocess.run(
        [sys.executable, "-c", code, root, *args, *_settings(tmp_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if (
        result.returncode
        or "ERROR" in result.stderr
        or "scheduler/unserializable" in result.stderr
    ):
        pytest.fail(result.stderr)


def read(tmp_path):
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        with catalog.Session() as session:
            groups = [
                json.loads(row)
                for row in session.scalars(
                    select(AcquisitionReleaseGroup.payload)
                ).all()
            ]
        entries = AcquisitionHandoffStore(catalog).list_release_entries(
            "calendar-fixture", AcquisitionStream.OUTLOOK_CALENDAR
        )
        return groups, entries
    finally:
        catalog.close()


@pytest.mark.parametrize("window", [False, True])
@pytest.mark.parametrize("direct", [False, True])
def test_calendar_native_release(tmp_path, calendar_server, window, direct):
    root, _ = calendar_server
    run(tmp_path, root, window=window, direct=direct)
    groups, entries = read(tmp_path)
    if len(groups) != 1 or len(entries) != 3:
        pytest.fail("Calendar native crawl lost its one group or three entries")
    expected = "resource" if window else "context"
    if {json.loads(row["payload"])["entry_kind"] for row in entries} != {expected}:
        pytest.fail("Calendar traversal published the wrong entry kind")


def test_calendar_jobdir_pause_resume_releases_one_group(tmp_path, calendar_server):
    root, seen = calendar_server
    run(tmp_path, root, pause=True, job=True)
    if read(tmp_path)[0] or len(seen) != 1:
        pytest.fail("Clean pause released an unfinished Calendar window")
    with (tmp_path / "job" / "spider.state").open("rb") as handle:
        run_id = pickle.load(handle)["msgloom_calendar_window"]["run_id"]
    run(tmp_path, root, job=True)
    groups, entries = read(tmp_path)
    if len(groups) != 1 or len(entries) != 3 or groups[0]["owner_run_id"] != run_id:
        pytest.fail("Resumed window lost one-group logical-run publication")
    if len(seen) != 2 or "$skiptoken=window-page-2" not in seen[-1]:
        pytest.fail("Resume did not use the native saved continuation")
    run(tmp_path, root, job=True)
    if read(tmp_path) != (groups, entries) or len(seen) != 2:
        pytest.fail("Completed JOBDIR replay changed the release or refetched pages")


@pytest.mark.parametrize("window", [False, True])
@pytest.mark.parametrize("failure", ["callback", "item"])
def test_calendar_native_failure_blocks_release(
    tmp_path, calendar_server, window, failure
):
    root, _ = calendar_server
    code = WINDOW_COMMAND if window else DISCOVER_COMMAND
    cls = "OutlookCalendarWindowSpider" if window else "OutlookCalendarDiscoverSpider"
    method = "parse_events" if window else "parse_calendars"
    if failure == "callback":
        setup = f"""
original_callback = {cls}.{method}
def failed_callback(self, response, **kwargs):
    yield from original_callback(self, response, **kwargs)
    raise ValueError("injected Calendar callback failure")
{cls}.{method} = failed_callback
"""
    else:
        setup = """
from message_ingest.pipelines.microsoft.outlook.calendar import OutlookCalendarPipeline
from message_ingest.items.microsoft.outlook.calendar import OutlookCalendarEventItem, OutlookCalendarItem
original_process = OutlookCalendarPipeline.process_item
async def failed_item(self, item):
    if isinstance(item, (OutlookCalendarEventItem, OutlookCalendarItem)):
        raise ValueError("injected Calendar item failure")
    return await original_process(self, item)
OutlookCalendarPipeline.process_item = failed_item
"""
    code = code.replace("execute([", ENABLE + setup + "\nexecute([")
    args = ["--start", START, "--end", END] if window else []
    result = subprocess.run(
        [sys.executable, "-c", code, root, *args, *_settings(tmp_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    expected = "spider_error" if failure == "callback" else "item_error"
    if expected not in result.stderr:
        pytest.fail(
            "Native failure injection did not reach the framework: " + result.stderr
        )
    if read(tmp_path)[0]:
        pytest.fail("Calendar native failure published a traversal release")
