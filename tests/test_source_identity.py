"""Verify logical source IDs cannot silently switch external provider accounts."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from scrapy.utils.test import get_crawler

from message_ingest.acquisition.source_identity import (
    SourceIdentity,
    SourceIdentityBootstrapRequired,
    SourceIdentityMismatch,
    SourceIdentityService,
)
from message_ingest.catalog import MessageRecord, SourceBinding
from message_ingest.extensions.catalog import CatalogService


def _crawler(
    tmp_path: Path,
    *,
    source_id: str = "source-1",
    bootstrap_confirm: str = "",
):
    return get_crawler(
        settings_dict={
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "MSGLOOM_SOURCE_ID": source_id,
            "MSGLOOM_SOURCE_IDENTITY_BOOTSTRAP_CONFIRM": bootstrap_confirm,
        }
    )


def _identity(
    account_key: str = "opaque-home-account-id",
    *,
    provider: str = "microsoft_graph",
    key_scheme: str = "msal_home_account_id/sha256-v1",
) -> SourceIdentity:
    return SourceIdentity(
        provider=provider,
        key_scheme=key_scheme,
        account_key=account_key,
    )


def _binding(crawler, source_id: str = "source-1") -> SourceBinding | None:
    service = CatalogService.from_crawler(crawler)
    with service.catalog.Session() as session:
        return session.get(SourceBinding, source_id)


def _insert_legacy_message(crawler, source_id: str) -> None:
    service = CatalogService.from_crawler(crawler)
    with service.catalog.Session() as session, session.begin():
        session.add(
            MessageRecord(
                source_id=source_id,
                message_id="legacy-message",
                is_removed=False,
                latest_observed_at="2026-09-26T00:00:00+00:00",
            )
        )


def _close(crawler) -> None:
    CatalogService.from_crawler(crawler).spider_closed(None, "test-finished")


def test_new_source_auto_binds_hashed_provider_identity(tmp_path: Path) -> None:
    crawler = _crawler(tmp_path)
    service = SourceIdentityService.from_crawler(crawler)
    raw_account_key = "opaque-home-account-id"

    outcome = service.bind_or_verify(_identity(raw_account_key))

    if outcome != "bound":
        pytest.fail('Expected: outcome == "bound"')
    binding = _binding(crawler)
    if binding is None:
        pytest.fail("Expected source binding row")
    material = (
        b"msgloom-source-binding-v1\0"
        b"microsoft_graph\0"
        b"msal_home_account_id/sha256-v1\0"
        + raw_account_key.encode()
    )
    expected_digest = hashlib.sha256(material).hexdigest()
    if binding.provider != "microsoft_graph":
        pytest.fail('Expected: binding.provider == "microsoft_graph"')
    if binding.key_scheme != "msal_home_account_id/sha256-v1":
        pytest.fail("Expected explicit provider key scheme")
    if binding.account_key_sha256 != expected_digest:
        pytest.fail("Expected domain-separated SHA-256 provider-account binding")
    if binding.binding_method != "auto_empty":
        pytest.fail("Expected empty source to auto-bind")
    if binding.account_key_sha256 == raw_account_key:
        pytest.fail("Expected raw provider account key not to be stored")
    if crawler.stats.get_value("msgloom/source_identity/state") != "bound":
        pytest.fail('Expected source identity state "bound"')
    if crawler.stats.get_value("msgloom/source_identity/bound_count") != 1:
        pytest.fail("Expected one source identity binding")
    _close(crawler)

    if raw_account_key.encode() in (tmp_path / "catalog.sqlite3").read_bytes():
        pytest.fail("Expected raw provider account key absent from catalog bytes")


def test_existing_binding_verifies_without_rewriting_it(tmp_path: Path) -> None:
    crawler = _crawler(tmp_path)
    service = SourceIdentityService.from_crawler(crawler)
    service.bind_or_verify(_identity())
    first = _binding(crawler)
    if first is None:
        pytest.fail("Expected initial binding")
    bound_at = first.bound_at

    outcome = service.bind_or_verify(_identity())

    if outcome != "verified":
        pytest.fail('Expected: outcome == "verified"')
    second = _binding(crawler)
    if second is None or second.bound_at != bound_at:
        pytest.fail("Expected verification not to rewrite the binding")
    if crawler.stats.get_value("msgloom/source_identity/verified_count") != 1:
        pytest.fail("Expected one source identity verification")
    _close(crawler)


@pytest.mark.parametrize(
    "identity",
    [
        _identity("different-account"),
        _identity(provider="google"),
    ],
)
def test_existing_binding_rejects_provider_or_account_change(
    tmp_path: Path,
    identity: SourceIdentity,
) -> None:
    crawler = _crawler(tmp_path)
    service = SourceIdentityService.from_crawler(crawler)
    service.bind_or_verify(_identity())
    original = _binding(crawler)
    if original is None:
        pytest.fail("Expected initial binding")

    with pytest.raises(SourceIdentityMismatch):
        service.bind_or_verify(identity)

    current = _binding(crawler)
    if current is None:
        pytest.fail("Expected existing binding to remain")
    if current.provider != original.provider:
        pytest.fail("Expected mismatch not to change provider")
    if current.account_key_sha256 != original.account_key_sha256:
        pytest.fail("Expected mismatch not to change provider account hash")
    if crawler.stats.get_value("msgloom/source_identity/mismatch_count") != 1:
        pytest.fail("Expected one source identity mismatch")
    _close(crawler)


def test_legacy_source_with_data_requires_explicit_bootstrap(tmp_path: Path) -> None:
    crawler = _crawler(tmp_path, source_id="legacy-source")
    _insert_legacy_message(crawler, "legacy-source")
    service = SourceIdentityService.from_crawler(crawler)

    with pytest.raises(
        SourceIdentityBootstrapRequired,
        match="MSGLOOM_SOURCE_IDENTITY_BOOTSTRAP_CONFIRM",
    ):
        service.bind_or_verify(_identity())

    if _binding(crawler, "legacy-source") is not None:
        pytest.fail("Expected no implicit binding for legacy persisted data")
    if (
        crawler.stats.get_value(
            "msgloom/source_identity/bootstrap_required_count"
        )
        != 1
    ):
        pytest.fail("Expected one bootstrap-required counter")
    _close(crawler)


def test_explicit_bootstrap_binds_legacy_source_once(tmp_path: Path) -> None:
    first = _crawler(
        tmp_path,
        source_id="legacy-source",
        bootstrap_confirm="legacy-source",
    )
    _insert_legacy_message(first, "legacy-source")
    service = SourceIdentityService.from_crawler(first)

    if service.bind_or_verify(_identity()) != "bound":
        pytest.fail("Expected explicit legacy bootstrap to create binding")
    _close(first)

    later = _crawler(tmp_path, source_id="legacy-source")
    later_service = SourceIdentityService.from_crawler(later)
    if later_service.bind_or_verify(_identity()) != "verified":
        pytest.fail("Expected later crawl to verify without bootstrap override")
    _close(later)


def test_bootstrap_confirmation_must_match_exact_source_id(tmp_path: Path) -> None:
    crawler = _crawler(
        tmp_path,
        source_id="legacy-source",
        bootstrap_confirm="different-source",
    )
    _insert_legacy_message(crawler, "legacy-source")
    service = SourceIdentityService.from_crawler(crawler)

    with pytest.raises(SourceIdentityBootstrapRequired):
        service.bind_or_verify(_identity())

    if _binding(crawler, "legacy-source") is not None:
        pytest.fail("Expected wrong-source confirmation not to create binding")
    _close(crawler)


def test_bootstrap_attestation_is_recorded_but_cannot_override_binding(
    tmp_path: Path,
) -> None:
    first = _crawler(
        tmp_path,
        source_id="legacy-source",
        bootstrap_confirm="legacy-source",
    )
    _insert_legacy_message(first, "legacy-source")
    service = SourceIdentityService.from_crawler(first)
    service.bind_or_verify(_identity())
    binding = _binding(first, "legacy-source")
    if binding is None or binding.binding_method != "bootstrap_attested":
        pytest.fail("Expected legacy bootstrap attestation to be persisted")
    _close(first)

    later = _crawler(
        tmp_path,
        source_id="legacy-source",
        bootstrap_confirm="legacy-source",
    )
    with pytest.raises(SourceIdentityMismatch):
        SourceIdentityService.from_crawler(later).bind_or_verify(
            _identity("other-account")
        )
    _close(later)


@pytest.mark.parametrize(
    "identity",
    [
        SourceIdentity(
            provider="",
            key_scheme="msal_home_account_id/sha256-v1",
            account_key="key",
        ),
        SourceIdentity(
            provider="microsoft_graph",
            key_scheme="",
            account_key="key",
        ),
        SourceIdentity(
            provider="microsoft_graph",
            key_scheme="msal_home_account_id/sha256-v1",
            account_key="",
        ),
    ],
)
def test_invalid_identity_metadata_fails_before_binding(
    tmp_path: Path,
    identity: SourceIdentity,
) -> None:
    crawler = _crawler(tmp_path)
    service = SourceIdentityService.from_crawler(crawler)

    with pytest.raises(ValueError):
        service.bind_or_verify(identity)

    if _binding(crawler) is not None:
        pytest.fail("Expected invalid identity not to create binding")
    _close(crawler)


def test_unrelated_source_rows_do_not_block_auto_binding(tmp_path: Path) -> None:
    crawler = _crawler(tmp_path, source_id="source-1")
    _insert_legacy_message(crawler, "other-source")
    service = SourceIdentityService.from_crawler(crawler)

    if service.bind_or_verify(_identity()) != "bound":
        pytest.fail("Expected unrelated source data not to require bootstrap")
    _close(crawler)


def test_binding_snapshot_matches_without_exposing_raw_account_key(
    tmp_path: Path,
) -> None:
    crawler = _crawler(tmp_path)
    service = SourceIdentityService.from_crawler(crawler)
    identity = _identity()
    service.bind_or_verify(identity)

    snapshot = service.get_binding()
    if snapshot is None:
        pytest.fail("Expected persisted source binding snapshot")
    if not service.matches_binding(identity, snapshot):
        pytest.fail("Expected persisted snapshot to match provider identity")
    if service.matches_binding(_identity("different-account"), snapshot):
        pytest.fail("Expected different account not to match binding snapshot")
    if "opaque-home-account-id" in repr(snapshot):
        pytest.fail("Expected binding snapshot not to expose raw account key")
    _close(crawler)


def test_source_id_with_surrounding_whitespace_is_rejected(tmp_path: Path) -> None:
    crawler = _crawler(tmp_path, source_id=" source-1 ")

    with pytest.raises(ValueError, match="surrounding whitespace"):
        SourceIdentityService.from_crawler(crawler)
