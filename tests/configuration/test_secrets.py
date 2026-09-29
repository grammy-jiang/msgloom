"""Credential isolation and explicit execution-time resolution tests."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from msgloom.configuration import (
    ConfigurationError,
    ConfigurationErrorCode,
    SecretResolver,
    load_operator_configuration,
)


def test_inspection_does_not_resolve_credentials(
    minimal_toml: Path,
    full_options: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = "synthetic-private-credential"
    monkeypatch.setenv("SYNTHETIC_AI_REGION", sentinel)
    configured = load_operator_configuration(minimal_toml, command_options=full_options)

    payload = configured.snapshot().payload
    if sentinel in payload or "SYNTHETIC_AI_REGION" in payload:
        pytest.fail("configuration inspection exposed credential material")

    binding = configured.secret_binding("ai-region")
    resolver = SecretResolver(
        allowed_environment={"SYNTHETIC_AI_REGION"},
        allowed_files=set(),
        mounted_secret_dir=None,
    )
    resolved = resolver.resolve(binding)
    if resolved.get_secret_value() != sentinel:
        pytest.fail("explicit execution-time environment resolution failed")
    if sentinel in repr(resolved):
        pytest.fail("resolved secret representation is not redacted")


def test_mounted_secret_is_bounded_private_and_whitelisted(
    minimal_toml: Path,
    full_options: dict[str, object],
    tmp_path: Path,
) -> None:
    secret_dir = tmp_path / "mounted"
    secret_dir.mkdir()
    value = "synthetic-report-credential"
    (secret_dir / "report-token").write_text(value + "\n", encoding="utf-8")

    configured = load_operator_configuration(
        minimal_toml,
        command_options=full_options,
        mounted_secret_dir=secret_dir,
    )
    binding = configured.secret_binding("report-credential")

    denied = SecretResolver(
        allowed_environment=set(),
        allowed_files=set(),
        mounted_secret_dir=secret_dir,
    )
    with pytest.raises(ConfigurationError) as caught:
        denied.resolve(binding)
    if caught.value.code is not ConfigurationErrorCode.SECRET_NOT_APPROVED:
        pytest.fail("unapproved mounted secret was not denied")

    resolver = SecretResolver(
        allowed_environment=set(),
        allowed_files={"report-token"},
        mounted_secret_dir=secret_dir,
    )
    secret = resolver.resolve(binding)
    if secret.get_secret_value() != value:
        pytest.fail("approved mounted secret was not resolved exactly")
    if value in configured.snapshot().payload:
        pytest.fail("mounted credential leaked into configuration snapshot")


def test_secret_purpose_mismatch_rejects_configuration(
    minimal_toml: Path,
    full_options: dict[str, object],
) -> None:
    triage = dict(cast(dict[str, object], full_options["triage"]))
    triage["secret_binding_ids"] = ["report-credential"]
    options = dict(full_options)
    options["triage"] = triage

    with pytest.raises(ConfigurationError) as caught:
        load_operator_configuration(minimal_toml, command_options=options)
    if caught.value.code is not ConfigurationErrorCode.INVALID_INPUT:
        pytest.fail("cross-purpose credential binding was not rejected")
