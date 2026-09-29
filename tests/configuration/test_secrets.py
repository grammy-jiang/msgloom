"""Credential isolation and explicit execution-time resolution tests."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import cast

import pytest

from msgloom.configuration import (
    ConfigurationError,
    ConfigurationErrorCode,
    SecretBinding,
    SecretPurpose,
    SecretResolver,
    SecretSource,
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


def test_secret_special_files_are_rejected_without_blocking(tmp_path: Path) -> None:
    secret_dir = tmp_path / "mounted"
    secret_dir.mkdir()
    fifo = secret_dir / "fifo-secret"
    os.mkfifo(fifo)
    code = """
from pathlib import Path
from msgloom.configuration import (
    ConfigurationError,
    SecretBinding,
    SecretPurpose,
    SecretResolver,
    SecretSource,
)
binding = SecretBinding(
    binding_id="fifo",
    purpose=SecretPurpose.REPORT,
    logical_name="transport",
    source=SecretSource.MOUNTED_FILE,
    locator="fifo-secret",
)
resolver = SecretResolver(
    allowed_environment=set(),
    allowed_files={"fifo-secret"},
    mounted_secret_dir=Path(__import__("sys").argv[1]),
)
print("READY", flush=True)
try:
    resolver.resolve(binding)
except ConfigurationError as error:
    print(error.code.value, flush=True)
"""
    process = subprocess.Popen(
        [sys.executable, "-c", code, str(secret_dir)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=3.0)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        pytest.fail("secret FIFO open blocked past the finite subprocess budget")
    if process.returncode != 0:
        pytest.fail(f"secret FIFO subprocess failed unexpectedly: {stderr!r}")
    if stdout.splitlines() != ["READY", "secret_unavailable"]:
        pytest.fail("secret FIFO subprocess did not reach and reject the open")

    fifo.unlink()
    target = tmp_path / "secret-target"
    target.write_text("synthetic-private", encoding="utf-8")
    fifo.symlink_to(target)
    binding = SecretBinding(
        binding_id="symlink",
        purpose=SecretPurpose.REPORT,
        logical_name="transport",
        source=SecretSource.MOUNTED_FILE,
        locator="fifo-secret",
    )
    resolver = SecretResolver(
        allowed_environment=set(),
        allowed_files={"fifo-secret"},
        mounted_secret_dir=secret_dir,
    )
    with pytest.raises(ConfigurationError) as caught:
        resolver.resolve(binding)
    if caught.value.code is not ConfigurationErrorCode.SECRET_UNAVAILABLE:
        pytest.fail("symlinked secret was not rejected safely")

    fifo.unlink()
    fifo.write_bytes(b"x" * (16 * 1024 + 1))
    with pytest.raises(ConfigurationError) as caught:
        resolver.resolve(binding)
    if caught.value.code is not ConfigurationErrorCode.SECRET_UNAVAILABLE:
        pytest.fail("oversized secret was not rejected safely")
