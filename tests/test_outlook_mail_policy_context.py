"""Pre-Scheduler JOBDIR binding for Outlook Mail policy identity."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from scrapy.crawler import Crawler
from scrapy.utils.test import get_crawler, get_reactor_settings

from message_ingest.acquisition import source_context
from message_ingest.acquisition.microsoft.outlook.email.rule_config import (
    effective_mail_policy_digest,
    parse_mail_rule_policy,
)
from message_ingest.acquisition.source_context import (
    SourceContextExtension,
    ensure_jobdir_context,
)
from message_ingest.spiders.microsoft.outlook.email.discover import (
    OutlookDiscoverSpider,
)

SOURCE_MARKER = ".msgloom-source-context-v1"


def _module():
    from message_ingest.acquisition.microsoft.outlook.email import policy_context

    return policy_context


def _policy(*, enabled: bool, private: str = "approval"):
    raw: dict[str, object] = {"enabled": enabled}
    if enabled:
        raw.update(
            {
                "default_profile": "discovery",
                "rules": [
                    {
                        "id": "finance-01",
                        "sequence": 10,
                        "profile": "full",
                        "conditions": {"subject_contains": [private]},
                    }
                ],
            }
        )
    return parse_mail_rule_policy(raw, source_label="explicit")


def _source_marker(tmp_path: Path) -> tuple[Path, str]:
    jobdir = tmp_path / "job"
    database_url = f"sqlite:///{tmp_path / 'catalog.sqlite3'}"
    ensure_jobdir_context(str(jobdir), "source-1", database_url)
    return jobdir, database_url


def _ensure(jobdir: Path, policy) -> None:
    _module().ensure_mail_policy_jobdir_context(
        str(jobdir),
        policy_digest=effective_mail_policy_digest(policy),
        policy_enabled=policy.enabled,
    )


def test_fresh_source_bound_jobdir_gets_private_policy_marker(
    tmp_path: Path,
) -> None:
    module = _module()
    jobdir, _database_url = _source_marker(tmp_path)
    policy = _policy(enabled=True)

    _ensure(jobdir, policy)

    marker = jobdir / module.MAIL_POLICY_JOB_MARKER
    payload = json.loads(marker.read_text(encoding="ascii"))
    if payload != {
        "contract": "outlook-mail-acquisition-rules-v1",
        "digest": effective_mail_policy_digest(policy),
        "enabled": True,
        "version": 1,
    }:
        pytest.fail(f"Unexpected private policy marker payload: {payload!r}")
    if marker.stat().st_mode & 0o777 != 0o600:
        pytest.fail("Mail policy marker must be owner-only 0600")
    if jobdir.stat().st_mode & 0o777 != 0o700:
        pytest.fail("Mail policy guard must preserve JOBDIR mode 0700")


def test_matching_existing_policy_marker_is_idempotent(tmp_path: Path) -> None:
    jobdir, _database_url = _source_marker(tmp_path)
    policy = _policy(enabled=True)

    _ensure(jobdir, policy)
    before = (jobdir / _module().MAIL_POLICY_JOB_MARKER).read_bytes()
    _ensure(jobdir, policy)
    after = (jobdir / _module().MAIL_POLICY_JOB_MARKER).read_bytes()

    if before != after:
        pytest.fail("Matching policy marker was rewritten")


def test_racing_matching_policy_marker_creation_is_accepted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    jobdir, _database_url = _source_marker(tmp_path)
    policy = _policy(enabled=True)
    digest = effective_mail_policy_digest(policy)
    marker_path = jobdir / module.MAIL_POLICY_JOB_MARKER
    expected = (
        json.dumps(
            {
                "contract": "outlook-mail-acquisition-rules-v1",
                "digest": digest,
                "enabled": True,
                "version": 1,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("ascii")
    original_open = module.os.open
    raced = False

    def racing_open(path, flags, mode=0o777):
        nonlocal raced
        if Path(path) == marker_path and flags & module.os.O_CREAT and not raced:
            raced = True
            fd = original_open(
                path,
                module.os.O_WRONLY | module.os.O_CREAT | module.os.O_EXCL,
                0o600,
            )
            module.os.write(fd, expected)
            module.os.close(fd)
            raise FileExistsError
        return original_open(path, flags, mode)

    monkeypatch.setattr(module.os, "open", racing_open)

    _ensure(jobdir, policy)

    if not raced:
        pytest.fail("Policy marker race fixture did not execute")
    if marker_path.read_bytes() != expected:
        pytest.fail("Matching raced policy marker was not accepted")


@pytest.mark.parametrize(
    ("first_enabled", "second_enabled"),
    ((False, True), (True, False)),
)
def test_existing_policy_marker_rejects_enabled_state_change(
    tmp_path: Path,
    first_enabled: bool,
    second_enabled: bool,
) -> None:
    module = _module()
    jobdir, _database_url = _source_marker(tmp_path)
    _ensure(jobdir, _policy(enabled=first_enabled))

    with pytest.raises(module.MailPolicyContextMismatch):
        _ensure(jobdir, _policy(enabled=second_enabled))


def test_existing_policy_marker_rejects_different_enabled_policy_digest(
    tmp_path: Path,
) -> None:
    module = _module()
    jobdir, _database_url = _source_marker(tmp_path)
    _ensure(jobdir, _policy(enabled=True, private="one"))

    with pytest.raises(module.MailPolicyContextMismatch):
        _ensure(jobdir, _policy(enabled=True, private="two"))


def test_policy_mismatch_error_does_not_expose_digest_path_or_policy_value(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    module = _module()
    jobdir, _database_url = _source_marker(tmp_path)
    first = _policy(enabled=True, private="PRIVATE_POLICY_VALUE_71")
    second = _policy(enabled=True, private="PRIVATE_POLICY_VALUE_72")
    first_digest = effective_mail_policy_digest(first)
    second_digest = effective_mail_policy_digest(second)
    _ensure(jobdir, first)

    with pytest.raises(module.MailPolicyContextMismatch) as caught:
        _ensure(jobdir, second)

    exposed = "\n".join(
        (
            str(caught.value),
            *(record.getMessage() for record in caplog.records),
        )
    )
    for secret in (
        str(jobdir),
        first_digest,
        second_digest,
        "PRIVATE_POLICY_VALUE_71",
        "PRIVATE_POLICY_VALUE_72",
    ):
        if secret in exposed:
            pytest.fail("Policy-context mismatch leaked private control material")


def test_source_marker_only_allows_first_enabled_policy_bootstrap(
    tmp_path: Path,
) -> None:
    jobdir, _database_url = _source_marker(tmp_path)
    if {entry.name for entry in jobdir.iterdir()} != {SOURCE_MARKER}:
        pytest.fail("Source-bound fresh JOBDIR fixture is not fresh")

    _ensure(jobdir, _policy(enabled=True))

    if not (jobdir / _module().MAIL_POLICY_JOB_MARKER).exists():
        pytest.fail("Fresh source-bound JOBDIR did not create policy marker")


def test_legacy_persisted_state_allows_one_time_disabled_policy_bootstrap(
    tmp_path: Path,
) -> None:
    jobdir, _database_url = _source_marker(tmp_path)
    (jobdir / "spider.state").write_bytes(b"legacy")

    _ensure(jobdir, _policy(enabled=False))

    marker = jobdir / _module().MAIL_POLICY_JOB_MARKER
    if not marker.exists():
        pytest.fail("Legacy no-rules JOBDIR did not bootstrap disabled policy marker")


def test_legacy_persisted_state_rejects_first_enabled_policy(
    tmp_path: Path,
) -> None:
    module = _module()
    jobdir, _database_url = _source_marker(tmp_path)
    (jobdir / "spider.state").write_bytes(b"legacy")

    with pytest.raises(module.MailPolicyContextMismatch, match="legacy"):
        _ensure(jobdir, _policy(enabled=True))

    if (jobdir / module.MAIL_POLICY_JOB_MARKER).exists():
        pytest.fail("Rejected legacy enabled-policy resume created a marker")


def test_policy_guard_requires_prior_source_context_verification(
    tmp_path: Path,
) -> None:
    module = _module()
    jobdir = tmp_path / "job"
    jobdir.mkdir(mode=0o700)

    with pytest.raises(module.MailPolicyContextMismatch, match="source"):
        _ensure(jobdir, _policy(enabled=False))


def test_malformed_existing_policy_marker_fails_closed(tmp_path: Path) -> None:
    module = _module()
    jobdir, _database_url = _source_marker(tmp_path)
    marker = jobdir / module.MAIL_POLICY_JOB_MARKER
    marker.write_text("PRIVATE_MALFORMED_MARKER", encoding="ascii")

    with pytest.raises(module.MailPolicyContextMismatch):
        _ensure(jobdir, _policy(enabled=False))


def _raw_crawler(tmp_path: Path, *, policy):
    jobdir = tmp_path / "job"
    settings = {
        **get_reactor_settings(),
        "REMOTE_CONTROL_ENABLED": False,
        "TELNETCONSOLE_ENABLED": False,
        "JOBDIR": str(jobdir),
        "MSGLOOM_SOURCE_ID": "source-1",
        "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
        "MSGLOOM_SOURCE_IDENTITY_REQUIRED": False,
        "EXTENSIONS": {SourceContextExtension: 50},
    }
    crawler = Crawler(OutlookDiscoverSpider, settings)
    spider = OutlookDiscoverSpider.from_crawler(
        crawler,
        _mail_rule_policy=policy,
    )
    crawler.spider = spider
    return crawler, spider


def test_real_extension_manager_constructs_source_guard_before_policy_guard(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    trace: list[str] = []
    original_source = source_context.ensure_jobdir_context
    original_policy = module.ensure_mail_policy_jobdir_context

    def source_wrapper(*args, **kwargs):
        trace.append("source")
        return original_source(*args, **kwargs)

    def policy_wrapper(*args, **kwargs):
        trace.append("policy")
        return original_policy(*args, **kwargs)

    monkeypatch.setattr(source_context, "ensure_jobdir_context", source_wrapper)
    monkeypatch.setattr(module, "ensure_mail_policy_jobdir_context", policy_wrapper)
    crawler, _spider = _raw_crawler(tmp_path, policy=_policy(enabled=True))

    crawler._apply_settings()
    manager = crawler.extensions

    if manager is None:
        pytest.fail("Real ExtensionManager did not construct")
    if trace[:2] != ["source", "policy"]:
        pytest.fail(f"Source/policy guards constructed in wrong order: {trace!r}")
    extensions = cast(
        dict[Any, int | None],
        crawler.settings.getwithbase("EXTENSIONS"),
    )
    if extensions.get(SourceContextExtension) != 50:
        pytest.fail("SourceContextExtension priority drifted from 50")
    if extensions.get(module.OutlookMailPolicyContextExtension) != 60:
        pytest.fail("Mail policy-context extension priority drifted from 60")


def test_policy_mismatch_aborts_extension_construction_before_engine_scheduler(
    tmp_path: Path,
) -> None:
    module = _module()
    crawler1, _spider1 = _raw_crawler(
        tmp_path, policy=_policy(enabled=True, private="one")
    )
    crawler1._apply_settings()

    crawler2, _spider2 = _raw_crawler(
        tmp_path, policy=_policy(enabled=True, private="two")
    )
    with pytest.raises(module.MailPolicyContextMismatch):
        crawler2._apply_settings()

    if crawler2._engine is not None:
        pytest.fail("Policy mismatch occurred after Engine/Scheduler construction")


def test_policy_extension_is_not_configured_without_jobdir(tmp_path: Path) -> None:
    module = _module()
    crawler = get_crawler(
        OutlookDiscoverSpider,
        settings_dict={
            "JOBDIR": None,
            "MSGLOOM_SOURCE_ID": "source-1",
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
        },
    )
    spider = OutlookDiscoverSpider.from_crawler(
        crawler,
        _mail_rule_policy=_policy(enabled=False),
    )
    crawler.spider = spider

    from scrapy.exceptions import NotConfigured

    with pytest.raises(NotConfigured):
        module.OutlookMailPolicyContextExtension.from_crawler(crawler)
