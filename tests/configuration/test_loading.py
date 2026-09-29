"""Settings-source precedence and closed-input tests."""

from __future__ import annotations

import copy
import os
import subprocess
import sys
from pathlib import Path
from typing import cast

import pytest

from msgloom.configuration import (
    ConfigurationError,
    ConfigurationErrorCode,
    load_operator_configuration,
)


def test_precedence_is_command_env_secret_toml(
    minimal_toml: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret_dir = tmp_path / "mounted"
    secret_dir.mkdir()
    (secret_dir / "code_version").write_text("secret-code", encoding="utf-8")
    monkeypatch.setenv("MSGLOOM_CONFIG__CODE_VERSION", "env-code")

    configured = load_operator_configuration(
        minimal_toml,
        command_options={"code_version": "command-code"},
        mounted_secret_dir=secret_dir,
    )
    if configured.code_version != "command-code":
        pytest.fail("command option did not have highest precedence")

    configured = load_operator_configuration(
        minimal_toml, mounted_secret_dir=secret_dir
    )
    if configured.code_version != "env-code":
        pytest.fail("environment did not override mounted settings")

    monkeypatch.delenv("MSGLOOM_CONFIG__CODE_VERSION")
    configured = load_operator_configuration(
        minimal_toml, mounted_secret_dir=secret_dir
    )
    if configured.code_version != "secret-code":
        pytest.fail("mounted settings did not override TOML")

    (secret_dir / "code_version").unlink()
    configured = load_operator_configuration(minimal_toml)
    if configured.code_version != "toml-code":
        pytest.fail("TOML was not used before defaults")


def test_unknown_duplicate_and_oversized_inputs_are_safe(
    minimal_toml: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(ConfigurationError) as caught:
        load_operator_configuration(
            minimal_toml, command_options={"not_a_setting": "value"}
        )
    if caught.value.code is not ConfigurationErrorCode.UNKNOWN_INPUT:
        pytest.fail("unknown command option was not classified safely")

    monkeypatch.setenv("MSGLOOM_CONFIG__NOT_A_SETTING", "value")
    with pytest.raises(ConfigurationError) as caught:
        load_operator_configuration(minimal_toml)
    if caught.value.code is not ConfigurationErrorCode.UNKNOWN_INPUT:
        pytest.fail("unknown environment input was not rejected")
    monkeypatch.delenv("MSGLOOM_CONFIG__NOT_A_SETTING")

    duplicate = tmp_path / "duplicate.toml"
    duplicate.write_text(
        minimal_toml.read_text(encoding="utf-8") + '\ncode_version = "again"\n',
        encoding="utf-8",
    )
    with pytest.raises(ConfigurationError) as caught:
        load_operator_configuration(duplicate)
    if caught.value.code is not ConfigurationErrorCode.INVALID_INPUT:
        pytest.fail("duplicate TOML input was not rejected")

    oversized = tmp_path / "oversized.toml"
    oversized.write_text("x" * (256 * 1024 + 1), encoding="utf-8")
    with pytest.raises(ConfigurationError) as caught:
        load_operator_configuration(oversized)
    if caught.value.code is not ConfigurationErrorCode.INPUT_TOO_LARGE:
        pytest.fail("oversized TOML was not rejected before parsing")


def test_nested_domain_choice_is_strict(
    minimal_toml: Path, full_options: dict[str, object]
) -> None:
    preparation = dict(cast(dict[str, object], full_options["preparation"]))
    filter_config = dict(cast(dict[str, object], preparation["filter_config"]))
    filter_config["address_normalization"] = "invented"
    preparation["filter_config"] = filter_config

    with pytest.raises(ConfigurationError) as caught:
        load_operator_configuration(
            minimal_toml,
            command_options={
                "code_version": "build",
                "preparation": preparation,
            },
        )
    if caught.value.code is not ConfigurationErrorCode.INVALID_INPUT:
        pytest.fail("invalid nested domain choice was not rejected")


def test_errors_do_not_echo_paths(minimal_toml: Path, tmp_path: Path) -> None:
    missing = tmp_path / "private" / "operator.toml"
    with pytest.raises(ConfigurationError) as caught:
        load_operator_configuration(missing)
    if str(missing) in str(caught.value):
        pytest.fail("configuration error exposed a private path")


def test_reusable_operation_contracts_reject_unusable_settings(
    minimal_toml: Path,
    full_options: dict[str, object],
) -> None:
    cases: list[tuple[str, dict[str, object]]] = []

    preparation = copy.deepcopy(full_options)
    prep = cast(dict[str, object], preparation["preparation"])
    prep["execution_timeout_seconds"] = 60.0
    prep["claim_lease_seconds"] = 2.0
    cases.append(("preparation lease", preparation))

    preparation_aggregate = copy.deepcopy(full_options)
    prep = cast(dict[str, object], preparation_aggregate["preparation"])
    prep["max_derived_bytes"] = 1024
    prep["max_total_derived_bytes"] = 512
    cases.append(("preparation aggregate", preparation_aggregate))

    triage_lease = copy.deepcopy(full_options)
    triage = cast(dict[str, object], triage_lease["triage"])
    triage["lease_seconds"] = 1.0
    cases.append(("triage lease", triage_lease))

    triage_attempt = copy.deepcopy(full_options)
    triage = cast(dict[str, object], triage_attempt["triage"])
    limits = cast(dict[str, object], triage["attempt_limits"])
    limits["timeout_seconds"] = 19.0
    cases.append(("triage attempt", triage_attempt))

    triage_cleanup = copy.deepcopy(full_options)
    triage = cast(dict[str, object], triage_cleanup["triage"])
    triage["cleanup_margin_seconds"] = 20.0
    cases.append(("triage cleanup", triage_cleanup))

    report = copy.deepcopy(full_options)
    report_settings = cast(dict[str, object], report["report"])
    report_settings["timeout_seconds"] = 120.0
    report_settings["claim_lease_seconds"] = 2.0
    cases.append(("report lease", report))

    for label, options in cases:
        with pytest.raises(ConfigurationError) as caught:
            load_operator_configuration(minimal_toml, command_options=options)
        if caught.value.code is not ConfigurationErrorCode.INVALID_INPUT:
            pytest.fail(f"{label} was not rejected at configuration load")


def test_parser_profiles_require_reviewed_registry_and_profile(
    minimal_toml: Path,
    full_options: dict[str, object],
) -> None:
    unregistered = copy.deepcopy(full_options)
    preparation = cast(dict[str, object], unregistered["preparation"])
    profiles = cast(list[dict[str, object]], preparation["parser_profiles"])
    profiles[0]["parser"] = {
        "name": "synthetic-unregistered-parser",
        "version": "1",
        "backend": None,
    }
    with pytest.raises(ConfigurationError) as caught:
        load_operator_configuration(minimal_toml, command_options=unregistered)
    if caught.value.code is not ConfigurationErrorCode.INVALID_INPUT:
        pytest.fail("unregistered parser identity was accepted")

    unsupported = copy.deepcopy(full_options)
    preparation = cast(dict[str, object], unsupported["preparation"])
    profiles = cast(list[dict[str, object]], preparation["parser_profiles"])
    profiles[0]["config"] = {"profile": "synthetic-profile", "settings": []}
    with pytest.raises(ConfigurationError) as caught:
        load_operator_configuration(minimal_toml, command_options=unsupported)
    if caught.value.code is not ConfigurationErrorCode.INVALID_INPUT:
        pytest.fail("unsupported production parser profile was accepted")


def test_environment_preflight_matches_case_insensitive_settings(
    minimal_toml: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("msgloom_config__unrecognized", "synthetic")
    with pytest.raises(ConfigurationError) as caught:
        load_operator_configuration(minimal_toml)
    if caught.value.code is not ConfigurationErrorCode.UNKNOWN_INPUT:
        pytest.fail(
            "lower-case unknown configuration environment input bypassed checks"
        )
    monkeypatch.delenv("msgloom_config__unrecognized")

    monkeypatch.setenv("MSGLOOM_CONFIG__CODE_VERSION", "one")
    monkeypatch.setenv("msgloom_config__code_version", "two")
    with pytest.raises(ConfigurationError) as caught:
        load_operator_configuration(minimal_toml)
    if caught.value.code is not ConfigurationErrorCode.INVALID_INPUT:
        pytest.fail("ambiguous environment case aliases were accepted")
    monkeypatch.delenv("MSGLOOM_CONFIG__CODE_VERSION")
    monkeypatch.delenv("msgloom_config__code_version")

    monkeypatch.setenv("msgloom_config__code_version", "x" * (64 * 1024 + 1))
    with pytest.raises(ConfigurationError) as caught:
        load_operator_configuration(minimal_toml)
    if caught.value.code is not ConfigurationErrorCode.INPUT_TOO_LARGE:
        pytest.fail("lower-case oversized environment input bypassed checks")
    monkeypatch.delenv("msgloom_config__code_version")

    monkeypatch.setenv("MSGLOOM_CONFIG__STORAGE", '{"sqlite_path":"state/one.sqlite3"}')
    monkeypatch.setenv("msgloom_config__storage__sqlite_path", "state/two.sqlite3")
    with pytest.raises(ConfigurationError) as caught:
        load_operator_configuration(minimal_toml)
    if caught.value.code is not ConfigurationErrorCode.INVALID_INPUT:
        pytest.fail("overlapping environment source settings were accepted")


def test_bounded_file_sources_reject_special_and_oversized_inputs(
    minimal_toml: Path,
    full_options: dict[str, object],
    tmp_path: Path,
) -> None:
    config_link = tmp_path / "operator-link.toml"
    config_link.symlink_to(minimal_toml)
    with pytest.raises(ConfigurationError) as caught:
        load_operator_configuration(config_link)
    if caught.value.code is not ConfigurationErrorCode.INVALID_INPUT:
        pytest.fail("symlinked operator TOML was accepted")

    prompt = minimal_toml.parent / "policy" / "prompt.md"
    prompt.unlink()
    os.mkfifo(prompt)
    with pytest.raises(ConfigurationError) as caught:
        load_operator_configuration(minimal_toml, command_options=full_options)
    if caught.value.code is not ConfigurationErrorCode.INVALID_INPUT:
        pytest.fail("prompt FIFO was accepted")
    prompt.unlink()
    prompt.write_text("restored prompt", encoding="utf-8")

    schema = minimal_toml.parent / "policy" / "schema.json"
    schema.unlink()
    schema_target = tmp_path / "schema-target.json"
    schema_target.write_text('{"type":"object"}', encoding="utf-8")
    schema.symlink_to(schema_target)
    with pytest.raises(ConfigurationError) as caught:
        load_operator_configuration(minimal_toml, command_options=full_options)
    if caught.value.code is not ConfigurationErrorCode.INVALID_INPUT:
        pytest.fail("symlinked schema was accepted")
    schema.unlink()
    schema.write_text('{"type":"object"}', encoding="utf-8")

    prompt.write_bytes(b"x" * (64 * 1024 + 1))
    with pytest.raises(ConfigurationError) as caught:
        load_operator_configuration(minimal_toml, command_options=full_options)
    if caught.value.code is not ConfigurationErrorCode.INPUT_TOO_LARGE:
        pytest.fail("oversized prompt was not rejected before reading")
    prompt.write_text("restored prompt", encoding="utf-8")

    schema.write_bytes(b"x" * (256 * 1024 + 1))
    with pytest.raises(ConfigurationError) as caught:
        load_operator_configuration(minimal_toml, command_options=full_options)
    if caught.value.code is not ConfigurationErrorCode.INPUT_TOO_LARGE:
        pytest.fail("oversized schema was not rejected before reading")

    mounted = tmp_path / "mounted"
    mounted.mkdir()
    settings_fifo = mounted / "code_version"
    os.mkfifo(settings_fifo)
    with pytest.raises(ConfigurationError) as caught:
        load_operator_configuration(minimal_toml, mounted_secret_dir=mounted)
    if caught.value.code is not ConfigurationErrorCode.INVALID_INPUT:
        pytest.fail("mounted settings FIFO was accepted")
    settings_fifo.unlink()

    target = tmp_path / "code-version-target"
    target.write_text("synthetic", encoding="utf-8")
    settings_fifo.symlink_to(target)
    with pytest.raises(ConfigurationError) as caught:
        load_operator_configuration(minimal_toml, mounted_secret_dir=mounted)
    if caught.value.code is not ConfigurationErrorCode.INVALID_INPUT:
        pytest.fail("symlinked mounted setting was accepted")
    settings_fifo.unlink()

    settings_fifo.write_text("x" * (64 * 1024 + 1), encoding="utf-8")
    with pytest.raises(ConfigurationError) as caught:
        load_operator_configuration(minimal_toml, mounted_secret_dir=mounted)
    if caught.value.code is not ConfigurationErrorCode.INPUT_TOO_LARGE:
        pytest.fail("oversized mounted setting was accepted")


def test_config_fifo_rejection_is_finite_in_owned_subprocess(tmp_path: Path) -> None:
    fifo = tmp_path / "operator.fifo"
    os.mkfifo(fifo)
    code = """
from pathlib import Path
from msgloom.configuration import ConfigurationError, load_operator_configuration
print("READY", flush=True)
try:
    load_operator_configuration(Path(__import__("sys").argv[1]))
except ConfigurationError as error:
    print(error.code.value, flush=True)
"""
    process = subprocess.Popen(
        [sys.executable, "-c", code, str(fifo)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=3.0)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        pytest.fail("configuration FIFO open blocked past the finite subprocess budget")
    if process.returncode != 0:
        pytest.fail(f"configuration FIFO subprocess failed unexpectedly: {stderr!r}")
    if stdout.splitlines() != ["READY", "invalid_input"]:
        pytest.fail("configuration FIFO subprocess did not reach and reject the open")
