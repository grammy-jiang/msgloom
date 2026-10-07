"""Private JOBDIR binding for effective Outlook Mail policy identity."""

from __future__ import annotations

import json
import os
import re
import stat
from pathlib import Path

from scrapy.exceptions import NotConfigured

from .rule_config import MAIL_RULE_POLICY_FAMILY

MAIL_POLICY_JOB_MARKER = ".msgloom-mail-policy-context-v1"
_SOURCE_JOB_MARKER = ".msgloom-source-context-v1"
_MARKER_VERSION = 1
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class MailPolicyContextMismatch(RuntimeError):
    """Persisted JOBDIR policy identity is unsafe for the current Mail policy."""


def ensure_mail_policy_jobdir_context(
    jobdir: str,
    *,
    policy_digest: str,
    policy_enabled: bool,
) -> None:
    """Create or verify the private policy marker after source-context binding."""

    if not jobdir:
        return
    if _SHA256.fullmatch(policy_digest) is None:
        raise ValueError("policy_digest must be lowercase SHA-256 hex")
    if not isinstance(policy_enabled, bool):
        raise TypeError("policy_enabled must be bool")

    directory = Path(jobdir)
    source_marker = directory / _SOURCE_JOB_MARKER
    marker = directory / MAIL_POLICY_JOB_MARKER
    expected = _marker_bytes(
        policy_digest=policy_digest,
        policy_enabled=policy_enabled,
    )

    if not source_marker.is_file():
        raise MailPolicyContextMismatch(
            "source context must be verified before Outlook Mail policy context"
        )

    os.chmod(directory, 0o700)

    if marker.exists():
        _verify_existing_marker(marker, expected)
        return

    other_entries = {
        entry.name
        for entry in directory.iterdir()
        if entry.name not in {_SOURCE_JOB_MARKER, MAIL_POLICY_JOB_MARKER}
    }
    if other_entries and policy_enabled:
        raise MailPolicyContextMismatch(
            "legacy JOBDIR has persisted state but no Outlook Mail policy marker; "
            "enabled policy cannot resume safely"
        )

    _create_marker(marker, expected)


class OutlookMailPolicyContextExtension:
    """Verify Mail policy identity before Scrapy constructs the Scheduler."""

    @classmethod
    def from_crawler(cls, crawler):
        """Bind only resumable Mail collection crawlers with JOBDIR enabled."""

        jobdir = crawler.settings.get("JOBDIR") or ""
        if not jobdir:
            raise NotConfigured

        spider = crawler.spider
        if spider is None:
            # scrapy.utils.test.get_crawler() applies settings before creating a
            # Spider. Real crawl_async creates the Spider before this extension.
            raise NotConfigured
        digest = getattr(spider, "mail_rule_policy_digest", None)
        enabled = getattr(spider, "mail_rule_policy_enabled", None)
        if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None:
            raise MailPolicyContextMismatch(
                "Outlook Mail collection spider has no valid policy identity"
            )
        if not isinstance(enabled, bool):
            raise MailPolicyContextMismatch(
                "Outlook Mail collection spider has no valid policy state"
            )

        ensure_mail_policy_jobdir_context(
            jobdir,
            policy_digest=digest,
            policy_enabled=enabled,
        )
        crawler.stats.set_value(
            "msgloom/source_context/mail_policy_jobdir_verified",
            True,
        )
        return cls()


def _marker_bytes(*, policy_digest: str, policy_enabled: bool) -> bytes:
    payload = {
        "contract": MAIL_RULE_POLICY_FAMILY,
        "digest": policy_digest,
        "enabled": policy_enabled,
        "version": _MARKER_VERSION,
    }
    return (
        json.dumps(
            payload,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("ascii")


def _verify_existing_marker(marker: Path, expected: bytes) -> None:
    try:
        fd = os.open(marker, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        raise MailPolicyContextMismatch(
            "Outlook Mail policy marker is unavailable or unsafe"
        ) from None
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > 512:
            raise MailPolicyContextMismatch("Outlook Mail policy marker is invalid")
        actual = os.read(fd, 513)
    except MailPolicyContextMismatch:
        raise
    except OSError:
        raise MailPolicyContextMismatch(
            "Outlook Mail policy marker is unreadable"
        ) from None
    finally:
        os.close(fd)

    if actual != expected:
        raise MailPolicyContextMismatch(
            "JOBDIR belongs to a different Outlook Mail policy context"
        )
    os.chmod(marker, 0o600)


def _create_marker(marker: Path, expected: bytes) -> None:
    try:
        fd = os.open(
            marker,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
        )
    except FileExistsError:
        _verify_existing_marker(marker, expected)
        return
    except OSError:
        raise MailPolicyContextMismatch(
            "Outlook Mail policy marker could not be created"
        ) from None

    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(expected)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError:
        try:
            marker.unlink()
        except OSError:
            pass
        raise MailPolicyContextMismatch(
            "Outlook Mail policy marker could not be persisted"
        ) from None
    os.chmod(marker, 0o600)


__all__ = [
    "MAIL_POLICY_JOB_MARKER",
    "MailPolicyContextMismatch",
    "OutlookMailPolicyContextExtension",
    "ensure_mail_policy_jobdir_context",
]
