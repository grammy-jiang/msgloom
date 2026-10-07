"""Help, configuration, and read-only saved-status CLI coverage."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from msgloom.contracts import (
    ExecutionIdentity,
    OperationOutcome,
    PhaseCapability,
    ResultRef,
    TerminalStatus,
)
from msgloom.persistence import Phase1Persistence
from tests.application_cli.helpers import invoke, minimal_config


def _default_config_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    config_home = tmp_path / "xdg"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    path = config_home / "msgloom" / "msgloom.toml"
    path.parent.mkdir(parents=True)
    return path


def _mail_only_config(path: Path, *, private_subject: str = "approval") -> Path:
    path.write_text(
        "\n".join(
            (
                "[acquisition.microsoft.outlook.mail]",
                "enabled = true",
                'default_profile = "discovery"',
                "",
                "[[acquisition.microsoft.outlook.mail.rules]]",
                'id = "finance-01"',
                "sequence = 10",
                'profile = "full"',
                "",
                "[acquisition.microsoft.outlook.mail.rules.conditions]",
                f'subject_contains = ["{private_subject}"]',
                "",
            )
        ),
        encoding="utf-8",
    )
    return path


def _private_regex_toml() -> str:
    return """[acquisition.microsoft.outlook.mail]
enabled=true
[[acquisition.microsoft.outlook.mail.rules]]
id="r1"
sequence=1
profile="full"
[acquisition.microsoft.outlook.mail.rules.conditions]
subject_regex=["PRIVATE_REGEX(?="]
"""


def _unknown_key_toml() -> str:
    return """[acquisition.microsoft.outlook.mail]
enabled=true
[[acquisition.microsoft.outlook.mail.rules]]
id="r1"
sequence=1
profile="full"
[acquisition.microsoft.outlook.mail.rules.conditions]
PRIVATE_CLIENT_NAME=["secret"]
"""


def test_help_and_default_config_commands_do_not_create_storage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Config management uses the XDG default without runtime construction."""
    root = Path(__file__).parents[2]
    config = _default_config_path(tmp_path, monkeypatch)
    minimal_config(config)

    help_result = invoke(root, "--help")
    if help_result.returncode != 0 or "report" not in help_result.stdout:
        pytest.fail("installed command surface help was not ready")

    result = invoke(root, "config", "validate")
    if result.returncode != 0:
        pytest.fail(f"default config validation failed: {result.stdout}")
    payload = json.loads(result.stdout)
    if payload.get("status") != "ok" or "configuration_version" not in payload:
        pytest.fail("default legacy config validation lost its safe version")
    if (config.parent / "state" / "phase1.sqlite3").exists():
        pytest.fail("config validation constructed persistence")

    inspected = invoke(root, "config", "inspect")
    if inspected.returncode != 0:
        pytest.fail(f"default redacted config inspection failed: {inspected.stdout}")
    if str(tmp_path) in inspected.stdout:
        pytest.fail("config inspection exposed a private filesystem path")


def test_config_commands_accept_only_optional_whole_file_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = Path(__file__).parents[2]
    default = _default_config_path(tmp_path, monkeypatch)
    minimal_config(default)
    explicit = minimal_config(tmp_path / "explicit.toml")

    result = invoke(root, "config", "validate", "--config", str(explicit))
    if result.returncode != 0:
        pytest.fail(f"explicit --config override failed: {result.stdout}")

    positional = invoke(root, "config", "validate", str(explicit))
    if positional.returncode != 2:
        pytest.fail("legacy positional config path remained accepted")


def test_missing_default_config_is_valid_builtin_empty_document(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = Path(__file__).parents[2]
    _default_config_path(tmp_path, monkeypatch)

    validated = invoke(root, "config", "validate")
    inspected = invoke(root, "config", "inspect")

    if validated.returncode != 0 or json.loads(validated.stdout) != {"status": "ok"}:
        pytest.fail(f"builtin empty config did not validate: {validated.stdout}")
    if inspected.returncode != 0 or json.loads(inspected.stdout) != {"status": "ok"}:
        pytest.fail(f"builtin empty config did not inspect safely: {inspected.stdout}")


def test_mail_only_config_validates_without_legacy_operator_roots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = Path(__file__).parents[2]
    config = _mail_only_config(_default_config_path(tmp_path, monkeypatch))

    result = invoke(root, "config", "validate")
    if result.returncode != 0:
        pytest.fail(f"Mail-only universal config failed validation: {result.stdout}")

    inspected = invoke(root, "config", "inspect")
    payload = json.loads(inspected.stdout)
    expected_mail = {
        "enabled": True,
        "policy_family": "outlook-mail-acquisition-rules-v1",
        "rule_count": 1,
        "enabled_rule_count": 1,
    }
    if payload.get("mail") != expected_mail:
        pytest.fail(f"Mail inspection was not the safe metadata contract: {payload!r}")
    if "configuration_version" in payload or "code_version" in payload:
        pytest.fail("Mail-only inspection fabricated legacy operator metadata")
    if str(config) in inspected.stdout:
        pytest.fail("Mail-only inspection exposed the config path")


def test_universal_config_validates_legacy_and_mail_projections_together(
    tmp_path: Path,
) -> None:
    root = Path(__file__).parents[2]
    config = minimal_config(tmp_path / "universal.toml")
    config.write_text(
        config.read_text(encoding="utf-8")
        + "\n[acquisition.microsoft.outlook.mail]\nenabled = true\n",
        encoding="utf-8",
    )

    result = invoke(root, "config", "validate", "--config", str(config))
    if result.returncode != 0:
        pytest.fail(f"combined universal config failed: {result.stdout}")
    if "configuration_version" not in json.loads(result.stdout):
        pytest.fail("combined validation lost legacy snapshot identity")


def test_config_inspect_never_exposes_mail_policy_values_or_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = Path(__file__).parents[2]
    private_subject = "PRIVATE_CUSTOMER_SUBJECT_442"
    config = _mail_only_config(
        _default_config_path(tmp_path, monkeypatch),
        private_subject=private_subject,
    )

    inspected = invoke(root, "config", "inspect")
    if inspected.returncode != 0:
        pytest.fail(f"Mail config inspection failed: {inspected.stdout}")
    exposed = inspected.stdout
    if (
        private_subject in exposed
        or str(config) in exposed
        or "digest" in exposed.casefold()
    ):
        pytest.fail("Config inspection exposed policy content/path/private digest")


@pytest.mark.parametrize(
    ("body", "expected_field", "expected_reason", "private_value"),
    (
        (
            '[acquisition.microsoft.outlook.mail]\nenabled=true\ndefault_profile="PRIVATE_PROFILE"\n',
            "acquisition.microsoft.outlook.mail.default_profile",
            "unsupported_profile",
            "PRIVATE_PROFILE",
        ),
        (
            _private_regex_toml(),
            "acquisition.microsoft.outlook.mail.rules[0].conditions.subject_regex",
            "invalid_regex",
            "PRIVATE_REGEX",
        ),
        (
            _unknown_key_toml(),
            "acquisition.microsoft.outlook.mail.rules[0].conditions.<unknown>",
            "unknown_field",
            "PRIVATE_CLIENT_NAME",
        ),
    ),
)
def test_config_validation_reports_only_safe_mail_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    body: str,
    expected_field: str,
    expected_reason: str,
    private_value: str,
) -> None:
    root = Path(__file__).parents[2]
    config = _default_config_path(tmp_path, monkeypatch)
    config.write_text(body, encoding="utf-8")

    result = invoke(root, "config", "validate")
    payload = json.loads(result.stdout)

    if result.returncode != 2:
        pytest.fail("Invalid Mail policy did not fail config validation")
    if (
        payload.get("field") != expected_field
        or payload.get("reason") != expected_reason
    ):
        pytest.fail(f"Mail diagnostic lost its safe location/reason: {payload!r}")
    if payload.get("source") != "default":
        pytest.fail("Default config diagnostic lost safe source provenance")
    if private_value in result.stdout or str(config) in result.stdout:
        pytest.fail("Mail diagnostic exposed private input/path")


def test_toml_syntax_error_reports_safe_source_line_column_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = Path(__file__).parents[2]
    config = _default_config_path(tmp_path, monkeypatch)
    private = "PRIVATE_TOML_VALUE_32"
    config.write_text(f"[acquisition\n# {private}\n", encoding="utf-8")

    result = invoke(root, "config", "validate")
    payload = json.loads(result.stdout)

    if result.returncode != 2:
        pytest.fail("Invalid TOML did not fail validation")
    if payload.get("source") != "default" or payload.get("reason") != "invalid_toml":
        pytest.fail(f"TOML diagnostic lost safe classification: {payload!r}")
    if payload.get("line") != 1 or payload.get("column") != 13:
        pytest.fail(f"TOML diagnostic lost numeric location: {payload!r}")
    if (
        private in result.stdout
        or str(config) in result.stdout
        or "Expected ']'" in result.stdout
    ):
        pytest.fail("TOML diagnostic exposed parser/private source text")


def test_status_is_read_only_and_reports_exact_saved_refs(tmp_path: Path) -> None:
    """Status never creates missing storage and reads exact terminal references."""
    root = Path(__file__).parents[2]
    config = minimal_config(tmp_path / "operator.toml")
    database = tmp_path / "state" / "phase1.sqlite3"

    missing = invoke(root, "status", str(config), "execution-one")
    if missing.returncode != 2:
        pytest.fail("missing status storage did not fail closed")
    if database.exists():
        pytest.fail("status silently created a missing database")

    async def seed() -> None:
        persistence = await Phase1Persistence.open(f"sqlite:///{database}")
        try:
            await persistence.save_outcome(
                OperationOutcome(
                    execution=ExecutionIdentity("execution-one"),
                    capability=PhaseCapability.PREPARE,
                    status=TerminalStatus.COMPLETE,
                    result_refs=(ResultRef("prepared-one", "prepared", "1"),),
                )
            )
        finally:
            await persistence.close()

    asyncio.run(seed())
    before = database.stat().st_mtime_ns
    result = invoke(root, "status", str(config), "execution-one")
    after = database.stat().st_mtime_ns
    if result.returncode != 0:
        pytest.fail(f"saved status failed: {result.stdout}")
    payload = json.loads(result.stdout)["saved"]
    if payload["execution"] != "execution-one":
        pytest.fail("status returned the wrong execution")
    if payload["result_refs"][0]["result_id"] != "prepared-one":
        pytest.fail("status did not preserve the exact saved result reference")
    if before != after:
        pytest.fail("read-only status rewrote the SQLite database")


def test_status_refuses_legacy_schema_without_migrating(tmp_path: Path) -> None:
    """Legacy storage is reported incompatible and remains byte-for-byte v2."""
    import sqlite3

    root = Path(__file__).parents[2]
    config = minimal_config(tmp_path / "operator.toml")
    database = tmp_path / "state" / "phase1.sqlite3"
    database.parent.mkdir()
    connection = sqlite3.connect(database)
    try:
        connection.execute(
            "CREATE TABLE phase1_schema_metadata "
            "(key VARCHAR PRIMARY KEY, value VARCHAR NOT NULL)"
        )
        connection.execute(
            "INSERT INTO phase1_schema_metadata(key, value) VALUES(?, ?)",
            ("schema_version", "2"),
        )
        connection.commit()
    finally:
        connection.close()
    before = database.read_bytes()
    result = invoke(root, "status", str(config), "execution-one")
    after = database.read_bytes()
    if result.returncode != 2:
        pytest.fail("legacy status schema did not fail closed")
    if json.loads(result.stdout).get("code") != "status_store_incompatible":
        pytest.fail("legacy schema used the wrong fixed failure code")
    if before != after:
        pytest.fail("status migrated or rewrote legacy storage")
