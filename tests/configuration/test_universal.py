"""Universal msgloom user-configuration document tests."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from msgloom.configuration import ConfigurationError, ConfigurationErrorCode


def _universal_module():
    return importlib.import_module("msgloom.configuration.universal")


def _errors_module():
    return importlib.import_module("msgloom.configuration.errors")


def _mail_toml(*, enabled: bool = False) -> str:
    return (
        "[acquisition.microsoft.outlook.mail]\n"
        f"enabled = {'true' if enabled else 'false'}\n"
    )


def test_missing_default_config_returns_builtin_empty_document(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)

    document = _universal_module().load_universal_config()

    if document.source != "builtin":
        pytest.fail(
            f"Missing default config used unexpected source: {document.source!r}"
        )
    if document.path is not None or dict(document.values):
        pytest.fail("Missing default config must produce the empty builtin document")


def test_xdg_config_home_selects_msgloom_toml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_home = tmp_path / "xdg"
    config = config_home / "msgloom" / "msgloom.toml"
    config.parent.mkdir(parents=True)
    config.write_text(_mail_toml(enabled=True), encoding="utf-8")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

    document = _universal_module().load_universal_config()

    if document.source != "default" or document.path != config:
        pytest.fail("Absolute XDG_CONFIG_HOME did not select msgloom/msgloom.toml")
    if document.outlook_mail_values() != {"enabled": True}:
        pytest.fail("Default XDG Mail policy was not decoded")


def test_relative_xdg_config_home_falls_back_to_home_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    config = home / ".config" / "msgloom" / "msgloom.toml"
    config.parent.mkdir(parents=True)
    config.write_text(_mail_toml(enabled=True), encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", "relative-config-home")

    document = _universal_module().load_universal_config()

    if document.path != config or document.source != "default":
        pytest.fail("Relative XDG_CONFIG_HOME did not fall back to ~/.config")


def test_explicit_missing_config_fails_without_default_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    default = tmp_path / "xdg" / "msgloom" / "msgloom.toml"
    default.parent.mkdir(parents=True)
    default.write_text(_mail_toml(enabled=True), encoding="utf-8")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    missing = tmp_path / "private-client" / "missing.toml"

    with pytest.raises(ConfigurationError) as caught:
        _universal_module().load_universal_config(missing)

    if caught.value.code is not ConfigurationErrorCode.INVALID_INPUT:
        pytest.fail(
            "Explicit missing config did not fail with bounded invalid-input code"
        )
    if str(missing) in str(caught.value):
        pytest.fail("Explicit missing config error exposed the private path")


def test_empty_comment_only_default_file_is_valid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_home = tmp_path / "xdg"
    config = config_home / "msgloom" / "msgloom.toml"
    config.parent.mkdir(parents=True)
    config.write_text("# intentionally empty\n\n", encoding="utf-8")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

    document = _universal_module().load_universal_config()

    if document.source != "default" or document.path != config:
        pytest.fail("Existing empty default config lost default-file provenance")
    if dict(document.values):
        pytest.fail("Comment-only config must decode as the empty universal document")


def test_universal_reader_rejects_unknown_top_level_and_nonregular_file(
    tmp_path: Path,
) -> None:
    unknown = tmp_path / "unknown.toml"
    private_key = "PRIVATE_CLIENT_NAME"
    unknown.write_text(f'{private_key} = "private-value"\n', encoding="utf-8")

    with pytest.raises(ConfigurationError) as caught:
        _universal_module().load_universal_config(unknown)

    if caught.value.code is not ConfigurationErrorCode.UNKNOWN_INPUT:
        pytest.fail("Unknown universal top-level field used the wrong error code")
    diagnostic = getattr(caught.value, "diagnostic", None)
    if diagnostic is None or diagnostic.field_path != "<unknown>":
        pytest.fail(
            "Unknown user key was not replaced by the safe <unknown> field path"
        )
    if private_key in str(caught.value):
        pytest.fail("Unknown private key leaked through the configuration error")

    directory = tmp_path / "directory.toml"
    directory.mkdir()
    with pytest.raises(ConfigurationError) as caught:
        _universal_module().load_universal_config(directory)
    if caught.value.code is not ConfigurationErrorCode.INVALID_INPUT:
        pytest.fail("Non-regular universal config did not fail as invalid input")


def test_operator_projection_ignores_known_acquisition_section(
    minimal_toml: Path, tmp_path: Path
) -> None:
    path = tmp_path / "universal.toml"
    path.write_text(
        minimal_toml.read_text(encoding="utf-8") + "\n" + _mail_toml(),
        encoding="utf-8",
    )

    module = _universal_module()
    document = module.load_universal_config(path)
    operator = document.operator_values()

    if operator is None or "acquisition" in operator:
        pytest.fail("Legacy operator projection retained the acquisition subtree")
    if document.outlook_mail_values() != {"enabled": False}:
        pytest.fail("Mail projection changed while isolating legacy operator fields")
    configured = module.load_operator_configuration_from_document(document)
    if configured.code_version != "toml-code":
        pytest.fail(
            "Legacy operator configuration no longer composes from one document"
        )


def test_mail_only_document_has_no_operator_projection(tmp_path: Path) -> None:
    path = tmp_path / "mail-only.toml"
    path.write_text(_mail_toml(enabled=True), encoding="utf-8")

    document = _universal_module().load_universal_config(path)

    if document.operator_values() is not None:
        pytest.fail(
            "Mail-only universal config fabricated a legacy operator projection"
        )
    if document.outlook_mail_values() != {"enabled": True}:
        pytest.fail("Mail-only universal config lost its Mail policy")


def test_reader_decodes_file_only_once_for_projection_consumers(
    minimal_toml: Path, tmp_path: Path
) -> None:
    path = tmp_path / "snapshot.toml"
    path.write_text(
        minimal_toml.read_text(encoding="utf-8") + "\n" + _mail_toml(),
        encoding="utf-8",
    )
    document = _universal_module().load_universal_config(path)

    path.write_text("[broken\nPRIVATE_VALUE = 'changed'\n", encoding="utf-8")
    first_mail = document.outlook_mail_values()
    if first_mail is None:
        pytest.fail("Loaded document unexpectedly lost Mail projection")
    first_mail["enabled"] = True

    if document.outlook_mail_values() != {"enabled": False}:
        pytest.fail(
            "Mail projection was not detached from the frozen document snapshot"
        )
    operator = document.operator_values()
    if operator is None or operator.get("code_version") != "toml-code":
        pytest.fail("Projection consumer re-read the mutated file")


def test_toml_syntax_error_reports_only_safe_source_line_and_column(
    tmp_path: Path,
) -> None:
    path = tmp_path / "private-customer-config.toml"
    private_value = "PRIVATE_CUSTOMER_VALUE_93"
    path.write_text(f"[acquisition\n# {private_value}\n", encoding="utf-8")

    with pytest.raises(ConfigurationError) as caught:
        _universal_module().load_universal_config(path)

    diagnostic = getattr(caught.value, "diagnostic", None)
    if diagnostic is None:
        pytest.fail("TOML syntax failure did not attach a safe diagnostic")
    if (
        diagnostic.source_label != "explicit"
        or diagnostic.line != 1
        or diagnostic.column != 13
        or diagnostic.reason_code != "invalid_toml"
    ):
        pytest.fail(f"Unexpected safe TOML diagnostic: {diagnostic!r}")
    rendered = str(caught.value)
    if str(path) in rendered or private_value in rendered:
        pytest.fail("TOML syntax failure exposed private path/content")


def test_configuration_error_string_never_echoes_explicit_path_or_private_value(
    tmp_path: Path,
) -> None:
    path = tmp_path / "private" / "customer-secret.toml"
    private_value = "PRIVATE_REGEX_OR_KEYWORD_71"
    path.parent.mkdir()
    path.write_text(f"[acquisition\n# {private_value}\n", encoding="utf-8")

    with pytest.raises(ConfigurationError) as caught:
        _universal_module().load_universal_config(path)

    errors = _errors_module()
    payload = errors.configuration_error_payload(caught.value)
    formatted = errors.format_configuration_error(caught.value)
    exposed = f"{caught.value}\n{payload!r}\n{formatted}"
    if str(path) in exposed or private_value in exposed:
        pytest.fail("Safe configuration diagnostics exposed private source material")


def test_mail_projection_can_ignore_incomplete_known_legacy_section(
    tmp_path: Path,
) -> None:
    from message_ingest.acquisition.microsoft.outlook.email.rule_config import (
        parse_mail_rule_policy,
    )
    from msgloom.configuration import load_operator_configuration_from_document

    path = tmp_path / "mixed-incomplete.toml"
    path.write_text(
        """
[acquisition.microsoft.outlook.mail]
enabled = true

[triage]
lease_seconds = 10
""".strip()
        + "\n",
        encoding="utf-8",
    )
    document = _universal_module().load_universal_config(path)

    policy = parse_mail_rule_policy(
        document.outlook_mail_values(),
        source_label=document.source,
    )
    if not policy.enabled:
        pytest.fail("Mail projection was blocked by unrelated incomplete triage config")

    with pytest.raises(ConfigurationError):
        load_operator_configuration_from_document(document)
