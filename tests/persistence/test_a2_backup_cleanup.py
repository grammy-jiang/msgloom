"""
Backup cleanup and restore-target checks for the A2 migration tool.

Covers two review findings: a failed backup copy must not leave a stub file
that blocks the retry, and a restore must never create a missing target.
Every database lives in ``tmp_path``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import msgloom.persistence.a2_schema_migration as tool
from msgloom.persistence.a2_schema import A2SchemaError
from msgloom.persistence.a2_schema_migration import (
    create_backup,
    file_sha256,
    restore_backup,
)
from tests.a2_kedro.helpers import check
from tests.persistence.test_a2_schema_fixtures import build_schema4


class CopyStopped(BaseException):
    """A BaseException that is not an Exception, like KeyboardInterrupt."""


@pytest.fixture
def schema4(tmp_path: Path) -> Path:
    return build_schema4(tmp_path / "live.sqlite")


@pytest.fixture
def backups(tmp_path: Path) -> Path:
    directory = tmp_path / "backups"
    directory.mkdir()
    return directory


@pytest.mark.parametrize("error", [CopyStopped(), KeyboardInterrupt()])
def test_failed_copy_removes_stub_and_allows_retry(
    schema4: Path,
    backups: Path,
    monkeypatch: pytest.MonkeyPatch,
    error: BaseException,
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise error

    before = schema4.read_bytes()
    with monkeypatch.context() as patch:
        patch.setattr(tool, "_copy", fail)
        with pytest.raises(type(error)):
            create_backup(schema4, backups)
    check(list(backups.iterdir()) == [], "no stub backup may stay on disk")
    check(schema4.read_bytes() == before, "source must stay byte-identical")
    path, digest = create_backup(schema4, backups)
    check(digest == file_sha256(path), "the retry must produce a verified backup")


def test_existing_backup_is_never_removed_on_collision(
    schema4: Path, backups: Path
) -> None:
    path, _ = create_backup(schema4, backups)
    kept = path.read_bytes()
    with pytest.raises(A2SchemaError) as caught:
        create_backup(schema4, backups)
    check(caught.value.reason == "backup-exists", "reason")
    check(path.read_bytes() == kept, "the earlier backup must survive")


def test_restore_refuses_a_missing_target(schema4: Path, backups: Path) -> None:
    path, digest = create_backup(schema4, backups)
    missing = schema4.parent / "typo.sqlite"
    with pytest.raises(A2SchemaError) as caught:
        restore_backup(path, missing, digest, confirm=True)
    check(caught.value.reason == "restore-target-missing", "reason")
    check(not missing.exists(), "restore must not create the target")
