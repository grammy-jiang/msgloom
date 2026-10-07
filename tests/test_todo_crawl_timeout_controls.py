"""Keep larger To Do fixture budgets finite and reap stalled crawlers."""

import os
import re
import subprocess

import pytest

from tests import test_todo_crawl as todo
from tests.handoff_qualification.feed import authority

graph_server = todo.graph_server


def test_todo_crawl_timeout_reaps_stalled_request_without_publication(
    tmp_path, graph_server
):
    """A stalled continuation must time out without publishing authority."""
    origin, _state, seen, _pages = graph_server
    with pytest.raises(subprocess.TimeoutExpired) as caught:
        todo._crawl(
            tmp_path,
            origin,
            action="sync",
            timeout=10,
            extra_settings={
                "DOWNLOAD_DELAY": "60",
                "RANDOMIZE_DOWNLOAD_DELAY": "False",
                "LOG_FORMAT": "%(process)d %(message)s",
            },
        )
    if caught.value.timeout != 10:
        pytest.fail("Crawler ignored the requested timeout")
    if not seen:
        pytest.fail("Crawler timed out before reaching the local Graph server")
    stderr = caught.value.stderr or b""
    match = re.search(rb"^(\d+) Scrapy ", stderr, re.MULTILINE)
    if match is None:
        pytest.fail("Timed-out crawler did not report its process identity")
    pid = int(match.group(1))
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)
    with pytest.raises(ChildProcessError):
        os.waitpid(pid, os.WNOHANG)
    if any(authority(tmp_path, "todo").values()):
        pytest.fail("Stalled traversal published snapshot authority")
