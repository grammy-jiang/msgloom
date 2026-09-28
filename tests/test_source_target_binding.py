"""Verify logical sources cannot switch Outlook mailbox targets."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from message_ingest.acquisition.source_target import (
    SELF_MAILBOX_KEY,
    SourceTargetBindingService,
    SourceTargetIdentity,
    SourceTargetMismatch,
)
from message_ingest.catalog import Catalog
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore

NOW = "2026-09-28T00:00:00+00:00"


def _service(catalog: Catalog, source_id: str) -> SourceTargetBindingService:
    return SourceTargetBindingService(
        service=SimpleNamespace(catalog=catalog),  # type: ignore[arg-type]
        source_id=source_id,
    )


def _identity(target: str) -> SourceTargetIdentity:
    return SourceTargetIdentity(
        provider="microsoft_graph",
        resource_kind="outlook_mailbox",
        key_scheme="graph-mailbox-locator/sha256-v1",
        target_key=target,
    )


def test_empty_source_can_bind_shared_mailbox_without_persisting_locator(
    tmp_path: Path,
) -> None:
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    try:
        service = _service(catalog, "shared-source")
        if (
            service.bind_or_verify(_identity("00000000-0000-0000-0000-000000000123"))
            != "bound"
        ):
            pytest.fail("Expected empty source to bind delegated mailbox")
        binding = service.get_binding()
        if binding is None or binding.binding_method != "auto_empty":
            pytest.fail("Expected persisted target binding metadata")
        if (
            service.bind_or_verify(_identity("00000000-0000-0000-0000-000000000123"))
            != "verified"
        ):
            pytest.fail("Expected stable target to verify")
        with pytest.raises(SourceTargetMismatch):
            service.bind_or_verify(_identity("other@example.test"))
    finally:
        catalog.close()


def test_legacy_data_auto_binds_self_but_refuses_shared_target(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'catalog.sqlite3'}"
    catalog = Catalog(database_url)
    try:
        store = OutlookMailStore(catalog, source_id="legacy")
        store.record_message(
            run_id="run-1",
            message={"id": "m1"},
            kind="discovery",
            evidence_id=None,
            observed_at=NOW,
        )
        self_service = _service(catalog, "legacy")
        if self_service.bind_or_verify(_identity(SELF_MAILBOX_KEY)) != "bound":
            pytest.fail("Expected historical /me source to auto-bind safely")
        binding = self_service.get_binding()
        if binding is None or binding.binding_method != "legacy_self_mailbox":
            pytest.fail("Expected explicit legacy-self binding method")
    finally:
        catalog.close()

    other = Catalog(f"sqlite:///{tmp_path / 'other.sqlite3'}")
    try:
        store = OutlookMailStore(other, source_id="legacy-shared")
        store.record_message(
            run_id="run-1",
            message={"id": "m1"},
            kind="discovery",
            evidence_id=None,
            observed_at=NOW,
        )
        with pytest.raises(SourceTargetMismatch, match="new MSGLOOM_SOURCE_ID"):
            _service(other, "legacy-shared").bind_or_verify(
                _identity("shared@example.test")
            )
    finally:
        other.close()


def test_legacy_profile_evidence_alone_does_not_claim_self_mailbox(
    tmp_path: Path,
) -> None:
    from message_ingest.catalog.models.acquisition import RawHttpEvidence

    catalog = Catalog(f"sqlite:///{tmp_path / 'profile.sqlite3'}")
    try:
        with catalog.Session() as session, session.begin():
            session.add(
                RawHttpEvidence(
                    evidence_id="e1",
                    source_id="profile-only",
                    run_id="r1",
                    purpose="user-profile",
                    observed_at=NOW,
                    origin="network",
                    request_fingerprint="f" * 64,
                    request_url="https://graph.microsoft.com/v1.0/me",
                    request_method="GET",
                    request_headers={},
                    request_body_sha256="0" * 64,
                    request_body_path="",
                    request_body_bytes=0,
                    response_url="https://graph.microsoft.com/v1.0/me",
                    response_status=200,
                    response_headers={},
                    response_body_sha256="1" * 64,
                    response_body_path="",
                    response_body_bytes=0,
                    response_flags=[],
                    error_type=None,
                    error_message=None,
                )
            )
        outcome = _service(catalog, "profile-only").bind_or_verify(
            _identity("shared@example.test")
        )
        if outcome != "bound":
            pytest.fail("Profile-only evidence must not force self-mailbox target")
    finally:
        catalog.close()
