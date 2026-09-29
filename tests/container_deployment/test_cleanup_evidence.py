"""Cleanup evidence regression tests for container qualification."""

import pytest


def test_successful_command_with_cleanup_error_is_failed_evidence() -> None:
    from deployment.process import CommandResult
    from deployment.target import _check_result

    check = _check_result(
        "synthetic",
        CommandResult(
            0,
            "ok",
            cleanup_errors=("container cleanup failed: synthetic",),
        ),
    )
    if check.status != "fail":
        pytest.fail(f"cleanup failure was reported as success: {check!r}")
    if "primary: ok" not in check.detail or "cleanup:" not in check.detail:
        pytest.fail(f"primary and cleanup evidence were not separated: {check!r}")
