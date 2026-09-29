"""Settings-source precedence and closed-input tests."""

from __future__ import annotations

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
