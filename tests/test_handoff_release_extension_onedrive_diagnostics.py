"""Check retained diagnostics for the OneDrive crawl subprocess helper."""

import json
import subprocess

import pytest
import test_handoff_release_extension_onedrive_crawl as crawl


def completed(*, returncode=0, stdout="crawl stdout", stderr="crawl stderr"):
    """Return a deterministic stand-in for a completed child process."""
    return subprocess.CompletedProcess(
        args=["scrapy"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def test_run_retains_completed_subprocess_evidence(tmp_path, monkeypatch):
    """A later release assertion must not discard child diagnostics."""
    monkeypatch.setattr(crawl.subprocess, "run", lambda *args, **kwargs: completed())

    crawl.run(tmp_path, "http://graph.invalid", "discover")

    evidence_path = tmp_path / "onedrive-discover-subprocess.json"
    if not evidence_path.is_file():
        pytest.fail("Completed subprocess evidence was not retained")
    evidence = json.loads(evidence_path.read_text())
    if evidence["exit_code"] != 0:
        pytest.fail("Completed subprocess exit status was not retained")
    if evidence["stdout"] != "crawl stdout":
        pytest.fail("Completed subprocess stdout was not retained")
    if evidence["stderr"] != "crawl stderr":
        pytest.fail("Completed subprocess stderr was not retained")
    if evidence["argv"][-2:] != ["-s", "LOG_LEVEL=DEBUG"]:
        pytest.fail("Completed subprocess argv was not retained")


def test_run_rejects_unrelated_generic_failure_marker(tmp_path, monkeypatch):
    """A generic Scrapy error must not prove an injected fault ran."""
    monkeypatch.setattr(
        crawl.subprocess,
        "run",
        lambda *args, **kwargs: completed(
            returncode=1,
            stderr="spider_error from an unrelated startup failure",
        ),
    )

    try:
        crawl.run(
            tmp_path,
            "http://graph.invalid",
            "discover",
            failure="injected callback failure",
        )
    except pytest.fail.Exception as exc:
        if "injected callback failure" not in str(exc):
            pytest.fail("Failure did not name the missing injected fault")
    else:
        pytest.fail("Generic spider_error falsely admitted the injected fault")


def test_run_retains_timeout_evidence(tmp_path, monkeypatch):
    """A timed-out child must retain partial output and its argv."""

    def timeout(argv, **kwargs):
        raise subprocess.TimeoutExpired(
            argv,
            timeout=30,
            output="partial stdout",
            stderr="partial stderr",
        )

    monkeypatch.setattr(crawl.subprocess, "run", timeout)

    try:
        crawl.run(tmp_path, "http://graph.invalid", "content")
    except pytest.fail.Exception:
        pass
    else:
        pytest.fail("Timed-out subprocess was not reported as a test failure")

    evidence_path = tmp_path / "onedrive-content-subprocess.json"
    if not evidence_path.is_file():
        pytest.fail("Timed-out subprocess evidence was not retained")
    evidence = json.loads(evidence_path.read_text())
    expected = {
        "exit_code": None,
        "stdout": "partial stdout",
        "stderr": "partial stderr",
        "timeout_seconds": 30,
    }
    for key, value in expected.items():
        if evidence[key] != value:
            pytest.fail(f"Timed-out subprocess lost {key}")
    if not isinstance(evidence["argv"], list):
        pytest.fail("Timed-out subprocess argv was not retained")
