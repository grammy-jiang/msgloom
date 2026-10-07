"""Outlook Mail policy JOBDIR bootstrap and mismatch tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from scrapy.utils.test import get_crawler

from message_ingest.spiders.microsoft.outlook.email._base import OutlookMailSpider
from message_ingest.spiders.microsoft.outlook.email.delta import OutlookDeltaSpider


def _crawler(
    tmp_path: Path,
    spider_cls: type[OutlookMailSpider] = OutlookDeltaSpider,
):
    return get_crawler(
        spider_cls,
        settings_dict={
            "JOBDIR": str(tmp_path / "job"),
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "MSGLOOM_SOURCE_ID": "test-source",
        },
    )


def _mail_policy_for_jobdir(*, enabled: bool):
    from message_ingest.acquisition.microsoft.outlook.email.rule_config import (
        parse_mail_rule_policy,
    )

    raw: dict[str, object] = {"enabled": enabled}
    if enabled:
        raw.update(
            {
                "rules": [
                    {
                        "id": "r1",
                        "sequence": 1,
                        "profile": "full",
                        "conditions": {"subject_contains": ["approval"]},
                    }
                ]
            }
        )
    return parse_mail_rule_policy(raw, source_label="explicit")


def _build_policy_extension(crawler):
    from scrapy.utils.misc import build_from_crawler

    from message_ingest.acquisition.microsoft.outlook.email.policy_context import (
        OutlookMailPolicyContextExtension,
    )

    return build_from_crawler(OutlookMailPolicyContextExtension, crawler)


def test_markerless_source_only_jobdir_accepts_enabled_policy_before_scheduler(
    tmp_path: Path,
) -> None:
    from message_ingest.acquisition.source_context import ensure_jobdir_context

    crawler = _crawler(tmp_path, OutlookDeltaSpider)
    ensure_jobdir_context(
        crawler.settings["JOBDIR"],
        crawler.settings["MSGLOOM_SOURCE_ID"],
        crawler.settings["MSGLOOM_DATABASE_URL"],
    )
    spider = OutlookDeltaSpider.from_crawler(
        crawler,
        _mail_rule_policy=_mail_policy_for_jobdir(enabled=True),
    )
    crawler.spider = spider

    _build_policy_extension(crawler)

    marker = Path(crawler.settings["JOBDIR"]) / ".msgloom-mail-policy-context-v1"
    if not marker.exists():
        pytest.fail("Fresh source-only JOBDIR did not create enabled policy marker")


def test_markerless_legacy_jobdir_bootstraps_disabled_policy(
    tmp_path: Path,
) -> None:
    from message_ingest.acquisition.source_context import ensure_jobdir_context

    crawler = _crawler(tmp_path, OutlookDeltaSpider)
    jobdir = Path(crawler.settings["JOBDIR"])
    ensure_jobdir_context(
        str(jobdir),
        crawler.settings["MSGLOOM_SOURCE_ID"],
        crawler.settings["MSGLOOM_DATABASE_URL"],
    )
    (jobdir / "spider.state").write_bytes(b"legacy")
    spider = OutlookDeltaSpider.from_crawler(
        crawler,
        _mail_rule_policy=_mail_policy_for_jobdir(enabled=False),
    )
    crawler.spider = spider

    _build_policy_extension(crawler)

    if not (jobdir / ".msgloom-mail-policy-context-v1").exists():
        pytest.fail("Legacy no-rules JOBDIR did not bootstrap disabled marker")


def test_markerless_legacy_jobdir_rejects_enabled_policy(
    tmp_path: Path,
) -> None:
    from message_ingest.acquisition.microsoft.outlook.email.policy_context import (
        MailPolicyContextMismatch,
    )
    from message_ingest.acquisition.source_context import ensure_jobdir_context

    crawler = _crawler(tmp_path, OutlookDeltaSpider)
    jobdir = Path(crawler.settings["JOBDIR"])
    ensure_jobdir_context(
        str(jobdir),
        crawler.settings["MSGLOOM_SOURCE_ID"],
        crawler.settings["MSGLOOM_DATABASE_URL"],
    )
    (jobdir / "spider.state").write_bytes(b"legacy")
    spider = OutlookDeltaSpider.from_crawler(
        crawler,
        _mail_rule_policy=_mail_policy_for_jobdir(enabled=True),
    )
    crawler.spider = spider

    with pytest.raises(MailPolicyContextMismatch):
        _build_policy_extension(crawler)
