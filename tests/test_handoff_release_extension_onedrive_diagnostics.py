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


def test_run_rejects_injected_text_without_fixture_event(tmp_path, monkeypatch):
    """Exception text alone must not prove the selected fixture raised it."""
    monkeypatch.setattr(
        crawl.subprocess,
        "run",
        lambda *args, **kwargs: completed(stderr="injected callback failure"),
    )
    with pytest.raises(pytest.fail.Exception, match="Missing injected failure"):
        crawl.run(
            tmp_path,
            "http://graph.invalid",
            "discover",
            failure="injected callback failure",
        )


def test_run_rejects_stale_fixture_event(tmp_path, monkeypatch):
    """A previous subprocess event must not admit a later failed startup."""
    event_path = tmp_path / "onedrive-discover-injections.jsonl"
    event_path.write_text(
        json.dumps({"mode": "discover", "failure": "injected callback failure"}) + "\n"
    )
    monkeypatch.setattr(
        crawl.subprocess,
        "run",
        lambda *args, **kwargs: completed(stderr="injected callback failure"),
    )
    with pytest.raises(pytest.fail.Exception, match="Missing injected failure"):
        crawl.run(
            tmp_path,
            "http://graph.invalid",
            "discover",
            failure="injected callback failure",
        )


@pytest.mark.parametrize("mode", ["discover", "content"])
def test_injected_callbacks_support_native_source_inspection(
    mode, tmp_path, monkeypatch
):
    """Native generator warnings must reach file-backed callback wrappers."""
    from onedrive_handoff_failure_helpers import install_failure
    from scrapy.settings import Settings
    from scrapy.utils.misc import warn_on_generator_with_return_value

    from message_ingest import settings
    from message_ingest.spiders.microsoft.onedrive.content import (
        MicrosoftOneDriveContentSpider,
    )
    from message_ingest.spiders.microsoft.onedrive.discover import (
        MicrosoftOneDriveDiscoverSpider,
    )

    spider_type, name = (
        (MicrosoftOneDriveDiscoverSpider, "parse_children")
        if mode == "discover"
        else (MicrosoftOneDriveContentSpider, "parse_content")
    )
    monkeypatch.setattr(spider_type, name, getattr(spider_type, name))
    monkeypatch.setattr(settings, "EXTENSIONS", dict(settings.EXTENSIONS))
    install_failure(mode, "injected callback failure", tmp_path / "events.jsonl")
    spider = (
        MicrosoftOneDriveDiscoverSpider()
        if mode == "discover"
        else MicrosoftOneDriveContentSpider(item_ids='["two"]')
    )
    spider.settings = Settings()
    warn_on_generator_with_return_value(spider, getattr(spider, name))


@pytest.mark.parametrize("kind", ["callback", "item"])
def test_native_signal_records_exact_failure_with_sanitized_logs(
    kind, tmp_path, monkeypatch
):
    """Native failure proof survives omitted exception text in child stderr."""
    import logging

    from onedrive_handoff_failure_helpers import InjectedFailure, InjectionRecorder
    from scrapy import signals
    from scrapy.crawler import Crawler
    from twisted.python.failure import Failure

    from message_ingest.spiders.microsoft.onedrive.content import (
        MicrosoftOneDriveContentSpider,
    )
    from microsoft_graph.extensions._logfilters import MicrosoftGraphScrapyPrivacyFilter

    crawler = Crawler(MicrosoftOneDriveContentSpider)
    crawler.spider = MicrosoftOneDriveContentSpider(item_ids='["two"]')
    recorder = InjectionRecorder.from_crawler(crawler)
    event_path = tmp_path / "onedrive-content-injections.jsonl"
    failure_text = f"injected {kind} failure"
    signal = signals.spider_error if kind == "callback" else signals.item_error

    def child(*args, **kwargs):
        crawler.signals.send_catch_log(
            signal,
            failure=Failure(ValueError(failure_text)),
        )
        if event_path.exists():
            pytest.fail("An unrelated exception wrote fixture proof")
        crawler.signals.send_catch_log(
            signal,
            failure=Failure(
                InjectedFailure("content", failure_text, "two", event_path)
            ),
        )
        error = InjectedFailure("content", failure_text, "two", event_path)
        record = logging.LogRecord(
            "scrapy.core.scraper",
            logging.ERROR,
            __file__,
            1,
            "Spider error processing request",
            (),
            (type(error), error, None),
        )
        MicrosoftGraphScrapyPrivacyFilter(crawler).filter(record)
        stderr = logging.Formatter().format(record)
        if failure_text in stderr or record.exc_info is not None:
            pytest.fail("The production filter exposed fixture exception text")
        return completed(returncode=1, stderr=stderr)

    monkeypatch.setattr(crawl.subprocess, "run", child)
    crawl.run(tmp_path, "http://graph.invalid", "content", failure=failure_text)
    if not recorder or not event_path.is_file():
        pytest.fail("The native error signal did not retain fixture proof")


@pytest.mark.parametrize("wrong_field", ["mode", "failure", "target", "exception_type"])
def test_run_rejects_wrong_fixture_identity(wrong_field, tmp_path, monkeypatch):
    """A different native fault cannot satisfy the requested injection."""
    event = {
        "mode": "content",
        "failure": "injected callback failure",
        "target": "two",
        "exception_type": "InjectedFailure",
    }
    event[wrong_field] = "unrelated"

    def child(*args, **kwargs):
        (tmp_path / "onedrive-content-injections.jsonl").write_text(
            json.dumps(event) + "\n"
        )
        return completed(stderr="spider_error")

    monkeypatch.setattr(crawl.subprocess, "run", child)
    with pytest.raises(pytest.fail.Exception, match="Missing injected failure"):
        crawl.run(
            tmp_path,
            "http://graph.invalid",
            "content",
            failure="injected callback failure",
        )
