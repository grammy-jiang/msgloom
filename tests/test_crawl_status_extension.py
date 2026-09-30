"""Verify mode-specific terminal status without replacing Scrapy lifecycle."""

from __future__ import annotations

import logging

import pytest
from scrapy.utils.misc import build_from_crawler
from scrapy.utils.test import get_crawler

from message_ingest.extensions.microsoft.outlook.email.status import (
    OutlookCrawlStatusExtension,
)
from message_ingest.spiders.microsoft.outlook.email.delta import OutlookDeltaSpider
from message_ingest.spiders.microsoft.outlook.email.discover import (
    OutlookDiscoverSpider,
)
from message_ingest.spiders.microsoft.outlook.email.full import OutlookFullSpider


def _extension(
    spider_cls,
    *,
    checkpoint_enabled: bool = True,
    **spider_kwargs,
):
    crawler = get_crawler(
        spider_cls,
        settings_dict={
            "MSGLOOM_CRAWL_STATUS_ENABLED": True,
            "MSGLOOM_DELTA_CHECKPOINT_ENABLED": checkpoint_enabled,
        },
    )
    spider = spider_cls.from_crawler(crawler, **spider_kwargs)
    crawler.spider = spider
    extension = build_from_crawler(OutlookCrawlStatusExtension, crawler)
    extension.spider_opened(spider)
    return crawler, spider, extension


def test_discovery_finished_after_pagination_exhaustion_is_completed(caplog) -> None:
    crawler, spider, extension = _extension(OutlookDiscoverSpider)
    crawler.stats.set_value("msgloom/crawl/discovery/pagination_exhausted", True)
    crawler.stats.set_value("msgloom/crawl/discovery/scope", "mailbox")
    crawler.stats.set_value("msgloom/crawl/discovery/page_count", 2)
    crawler.stats.set_value("msgloom/crawl/discovery/message_count", 3)
    crawler.stats.set_value("msgloom/catalog/message_item_processed_count", 3)
    caplog.set_level(
        logging.INFO, logger="message_ingest.extensions.microsoft.outlook.email.status"
    )

    extension.spider_closed(spider, "finished")

    if crawler.stats.get_value("msgloom/final/status") != "completed":
        pytest.fail(
            'Expected: crawler.stats.get_value("msgloom/final/status") == "completed"'
        )
    if crawler.stats.get_value("msgloom/final/pagination_outcome") != "exhausted":
        pytest.fail(
            'Expected: crawler.stats.get_value("msgloom/final/pagination_outcome") == "exhausted"'
        )
    if "Outlook discovery final summary: status=completed" not in caplog.text:
        pytest.fail(
            'Expected: "Outlook discovery final summary: status=completed" in caplog.text'
        )


def test_discovery_explicit_limit_is_truncated_not_completed() -> None:
    crawler, spider, extension = _extension(OutlookDiscoverSpider)
    crawler.stats.set_value("msgloom/crawl/discovery/truncated_count", 1)
    crawler.stats.set_value("msgloom/crawl/discovery/pagination_exhausted", False)

    extension.spider_closed(spider, "finished")

    if crawler.stats.get_value("msgloom/final/status") != "truncated":
        pytest.fail(
            'Expected: crawler.stats.get_value("msgloom/final/status") == "truncated"'
        )
    if crawler.stats.get_value("msgloom/final/pagination_outcome") != "truncated":
        pytest.fail(
            'Expected: crawler.stats.get_value("msgloom/final/pagination_outcome") == "truncated"'
        )


def test_discovery_finished_without_terminal_page_is_unverified() -> None:
    crawler, spider, extension = _extension(OutlookDiscoverSpider)
    crawler.stats.set_value("msgloom/crawl/discovery/pagination_exhausted", False)

    extension.spider_closed(spider, "finished")

    if crawler.stats.get_value("msgloom/final/status") != "unverified":
        pytest.fail(
            'Expected: crawler.stats.get_value("msgloom/final/status") == "unverified"'
        )


def test_delta_requires_confirmed_checkpoint_outcome_for_completed() -> None:
    crawler, spider, extension = _extension(OutlookDeltaSpider)
    crawler.stats.set_value("msgloom/checkpoint/outcome", "committed")
    crawler.stats.set_value("msgloom/checkpoint/committed_folder_count", 0)

    extension.spider_closed(spider, "finished")

    if crawler.stats.get_value("msgloom/final/status") != "completed":
        pytest.fail(
            'Expected: crawler.stats.get_value("msgloom/final/status") == "completed"'
        )
    if crawler.stats.get_value("msgloom/final/checkpoint_outcome") != "committed":
        pytest.fail(
            'Expected: crawler.stats.get_value("msgloom/final/checkpoint_outcome") == "committed"'
        )


def test_delta_without_checkpoint_owner_is_unverified() -> None:
    crawler, spider, extension = _extension(
        OutlookDeltaSpider,
        checkpoint_enabled=False,
    )

    extension.spider_closed(spider, "finished")

    if crawler.stats.get_value("msgloom/final/status") != "unverified":
        pytest.fail(
            'Expected: crawler.stats.get_value("msgloom/final/status") == "unverified"'
        )
    if crawler.stats.get_value("msgloom/final/checkpoint_outcome") != "disabled":
        pytest.fail(
            'Expected: crawler.stats.get_value("msgloom/final/checkpoint_outcome") == "disabled"'
        )


def test_delta_incomplete_close_reason_is_incomplete_without_other_failure() -> None:
    crawler, spider, extension = _extension(OutlookDeltaSpider)

    extension.spider_closed(spider, "delta_incomplete")

    if crawler.stats.get_value("msgloom/final/status") != "incomplete":
        pytest.fail(
            'Expected: crawler.stats.get_value("msgloom/final/status") == "incomplete"'
        )


def test_pipeline_error_marks_any_outlook_mode_failed() -> None:
    crawler, spider, extension = _extension(OutlookDiscoverSpider)
    extension.item_error(spider=spider)

    extension.spider_closed(spider, "finished")

    if crawler.stats.get_value("msgloom/final/status") != "failed":
        pytest.fail(
            'Expected: crawler.stats.get_value("msgloom/final/status") == "failed"'
        )
    if "item_error" not in crawler.stats.get_value("msgloom/final/reason_codes"):
        pytest.fail(
            'Expected: "item_error" in crawler.stats.get_value("msgloom/final/reason_codes")'
        )


def test_shutdown_is_interrupted() -> None:
    crawler, spider, extension = _extension(OutlookDiscoverSpider)

    extension.spider_closed(spider, "shutdown")

    if crawler.stats.get_value("msgloom/final/status") != "interrupted":
        pytest.fail(
            'Expected: crawler.stats.get_value("msgloom/final/status") == "interrupted"'
        )


def test_full_completed_reports_execution_not_profile_completeness(caplog) -> None:
    crawler, spider, extension = _extension(
        OutlookFullSpider,
        message_ids="one",
        operation="refresh",
    )
    crawler.stats.set_value("msgloom/crawl/enrichment/operation", "refresh")
    crawler.stats.set_value("msgloom/crawl/enrichment/profile", spider.profile)
    crawler.stats.set_value("msgloom/crawl/enrichment/target_message_count", 1)
    caplog.set_level(
        logging.INFO, logger="message_ingest.extensions.microsoft.outlook.email.status"
    )

    extension.spider_closed(spider, "finished")

    if crawler.stats.get_value("msgloom/final/status") != "completed":
        pytest.fail(
            'Expected: crawler.stats.get_value("msgloom/final/status") == "completed"'
        )
    if crawler.stats.get_value("msgloom/final/profile_completeness") != "not_evaluated":
        pytest.fail(
            'Expected: crawler.stats.get_value("msgloom/final/profile_completeness") == "not_evaluated"'
        )
    if "profile_completeness=not_evaluated" not in caplog.text:
        pytest.fail('Expected: "profile_completeness=not_evaluated" in caplog.text')


def test_delta_stuck_in_checkpoint_evaluation_is_failed() -> None:
    crawler, spider, extension = _extension(OutlookDeltaSpider)
    crawler.stats.set_value("msgloom/checkpoint/outcome", "evaluating")

    extension.spider_closed(spider, "finished")

    if crawler.stats.get_value("msgloom/final/status") != "failed":
        pytest.fail(
            'Expected: crawler.stats.get_value("msgloom/final/status") == "failed"'
        )
    if "checkpoint_evaluation_incomplete" not in crawler.stats.get_value(
        "msgloom/final/reason_codes"
    ):
        pytest.fail(
            'Expected: "checkpoint_evaluation_incomplete" in final reason codes'
        )


def test_late_signal_handler_failure_overrides_completed_final_stats() -> None:
    import sys

    from message_ingest.extensions.microsoft_graph._logfilters import (
        MicrosoftGraphScrapyPrivacyFilter,
    )

    crawler, spider, extension = _extension(OutlookDiscoverSpider)
    crawler.stats.set_value("msgloom/crawl/discovery/pagination_exhausted", True)
    extension.spider_closed(spider, "finished")
    if crawler.stats.get_value("msgloom/final/status") != "completed":
        pytest.fail("Expected: status completed before later signal failure")

    try:
        raise RuntimeError(
            "private signal failure at "
            "https://graph.microsoft.com/v1.0/me/messages?$skiptoken=secret"
        )
    except RuntimeError:
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="scrapy.utils.signal",
        level=logging.ERROR,
        pathname=__file__,
        lineno=0,
        msg="Error caught on signal handler: %(receiver)s",
        args=({"receiver": extension.spider_closed},),
        exc_info=exc_info,
    )
    privacy_filter = MicrosoftGraphScrapyPrivacyFilter(crawler)
    privacy_filter.filter(record)

    if crawler.stats.get_value("msgloom/final/status") != "failed":
        pytest.fail(
            'Expected: crawler.stats.get_value("msgloom/final/status") == "failed"'
        )
    reasons = crawler.stats.get_value("msgloom/final/reason_codes")
    if "signal_handler_error" not in reasons:
        pytest.fail('Expected: "signal_handler_error" in final reason codes')
    if record.exc_info is not None:
        pytest.fail("Expected: record.exc_info is None")
    rendered = record.getMessage()
    if "secret" in rendered or "graph.microsoft.com" in rendered:
        pytest.fail("Expected: signal error log is privacy-safe")


def test_rule_summary_logs_aggregate_counts_when_rule_evaluation_ran(
    caplog,
) -> None:
    crawler, spider, extension = _extension(OutlookDiscoverSpider)
    crawler.stats.set_value("msgloom/crawl/discovery/pagination_exhausted", True)
    values = {
        "msgloom/crawl/mail_rules/evaluated_count": 7,
        "msgloom/crawl/mail_rules/matched_count": 3,
        "msgloom/crawl/mail_rules/default_count": 2,
        "msgloom/crawl/mail_rules/unresolved_count": 2,
        "msgloom/crawl/mail_rules/probe_scheduled_count": 2,
        "msgloom/crawl/mail_rules/probe_completed_count": 1,
        "msgloom/crawl/mail_rules/probe_failed_count": 1,
        "msgloom/crawl/mail_rules/stop_processing_count": 1,
        "msgloom/crawl/mail_rules/fallback_count": 2,
        "msgloom/crawl/mail_rules/evaluation_error_count": 1,
    }
    for key, value in values.items():
        crawler.stats.set_value(key, value)
    caplog.set_level(
        logging.INFO,
        logger="message_ingest.extensions.microsoft.outlook.email.status",
    )

    extension.spider_closed(spider, "finished")

    records = [
        record
        for record in caplog.records
        if "event=outlook_mail_rule_summary" in record.getMessage()
    ]
    if len(records) != 1 or records[0].levelno != logging.INFO:
        pytest.fail("Rule-enabled collection must emit one INFO aggregate summary")
    rendered = records[0].getMessage()
    for expected in (
        "evaluated=7",
        "matched=3",
        "default=2",
        "unresolved=2",
        "probe_scheduled=2",
        "probe_completed=1",
        "probe_failed=1",
        "stop_processing=1",
        "fallback=2",
        "errors=1",
    ):
        if expected not in rendered:
            pytest.fail(f"Rule summary lost aggregate field: {expected}")
    for private in ("message-secret", "rule-secret", "person@example.test"):
        if private in rendered:
            pytest.fail("Rule crawl summary must not contain identifiers")


def test_rule_summary_is_absent_when_rule_evaluation_did_not_run(caplog) -> None:
    _crawler, spider, extension = _extension(OutlookDiscoverSpider)
    caplog.set_level(
        logging.INFO,
        logger="message_ingest.extensions.microsoft.outlook.email.status",
    )

    extension.spider_closed(spider, "finished")

    if "event=outlook_mail_rule_summary" in caplog.text:
        pytest.fail("No-rules collection must not emit a Mail rule summary")
