"""Portable, fail-closed checks for the CI docs-only fast path."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.quality import ci_change_scope


@pytest.mark.parametrize(
    "paths",
    [
        ["docs/notes/review.md"],
        ["docs/design.rst", "docs/subdir/requirements.txt"],
        ["docs\\plans\\safety.md"],
        ["docs/notes/read me.md", "docs/notes/spec.rst"],
    ],
)
def test_only_documentation_files_are_eligible(paths: list[str]) -> None:
    """Strictly scoped documentation commits may avoid runtime test jobs."""
    if not ci_change_scope.docs_only(paths):
        pytest.fail("safe documentation changes were not recognized")


@pytest.mark.parametrize(
    "paths",
    [
        [],
        ["docs/notes/design.md", "tests/test_contract.py"],
        ["docs/notes/design.md", "pyproject.toml"],
        [".github/workflows/ci.yml"],
        ["msgloom/prompts/readme.md"],
        ["research/topic/research.md"],
        ["docs/code/example.py"],
        ["docs/notes/report.json"],
        ["docs/../msgloom/entry.py"],
        ["README.md"],
        ["docs/"],
    ],
)
def test_code_configuration_and_ambiguous_changes_force_full_ci(
    paths: list[str],
) -> None:
    """Never infer docs-only intent from extensions or partial file lists."""
    if ci_change_scope.docs_only(paths):
        pytest.fail(f"runtime-relevant or ambiguous change skipped tests: {paths}")


def test_changed_paths_uses_exact_git_diff_without_rename_hiding(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Git supplies both rename endpoints and raw null-delimited paths."""
    before, head = "a" * 40, "b" * 40
    captured: list[list[str]] = []

    def fake_git(
        command: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[bytes]:
        captured.append(command)
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=b"docs/one.md\0docs/two.rst\0",
            stderr=b"",
        )

    monkeypatch.setattr(ci_change_scope.subprocess, "run", fake_git)
    result = ci_change_scope.changed_paths(tmp_path, before, head)
    if result != ["docs/one.md", "docs/two.rst"]:
        pytest.fail(f"lossy or incorrect Git path parsing: {result}")
    if not captured or "--no-renames" not in captured[0]:
        pytest.fail("Git rename detection could hide a changed production source")
    if "-z" not in captured[0] or captured[0][-1] != "--":
        pytest.fail("Git diff must use unambiguous file delimiters")


@pytest.mark.parametrize("failure", ["command_failed", "git_missing", "invalid_sha"])
def test_uncertain_diff_keeps_full_tests(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    failure: str,
) -> None:
    """Unavailable history or Git may never result in a green skipped suite."""
    before, head = "a" * 40, "b" * 40
    if failure == "invalid_sha":
        before = "unknown"
    else:

        def fake_git(command: list[str], **kwargs: object) -> object:
            if failure == "git_missing":
                raise FileNotFoundError("git unavailable")
            return subprocess.CompletedProcess(
                command, returncode=128, stdout=b"", stderr=b"history missing"
            )

        monkeypatch.setattr(ci_change_scope.subprocess, "run", fake_git)

    if ci_change_scope.classify("pull_request", before, head, tmp_path):
        pytest.fail("uncertain repository state omitted the test matrix")


def test_manual_runs_always_execute_full_ci(tmp_path: Path) -> None:
    """Manual and unknown events never qualify for the docs-only fast path."""
    if ci_change_scope.classify("workflow_dispatch", "a" * 40, "b" * 40, tmp_path):
        pytest.fail("manual dispatch skipped required validation")
    if ci_change_scope.classify("unexpected", "a" * 40, "b" * 40, tmp_path):
        pytest.fail("unknown event skipped required validation")


def test_empty_git_diff_cannot_skip_tests(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A missing/no-op diff must not be treated as trusted docs-only evidence."""

    def fake_git(command: list[str], **kwargs: object) -> object:
        return subprocess.CompletedProcess(command, returncode=0, stdout=b"")

    monkeypatch.setattr(ci_change_scope.subprocess, "run", fake_git)
    if ci_change_scope.classify("push", "a" * 40, "b" * 40, tmp_path):
        pytest.fail("empty diff claimed documentation-only evidence")
