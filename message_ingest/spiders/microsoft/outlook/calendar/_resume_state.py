"""Serializable execution scope shared by resumable Calendar read spiders."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CalendarScopedExecutionState:
    """Run identity/integrity bound to one immutable acquisition scope."""

    run_id: str
    run_failed: bool
    failure_reasons: frozenset[str]

    @classmethod
    def restore(
        cls,
        saved: object,
        *,
        expected_scope: dict[str, object],
        default_run_id: str,
        label: str,
    ) -> tuple[CalendarScopedExecutionState, bool]:
        """Validate one JOBDIR scope before restoring execution facts."""
        if saved is None:
            return (
                cls(
                    run_id=default_run_id,
                    run_failed=False,
                    failure_reasons=frozenset(),
                ),
                False,
            )
        if not isinstance(saved, dict):
            raise TypeError(f"JOBDIR has no valid {label} execution state")
        if saved.get("scope") != expected_scope:
            raise ValueError(f"Calendar JOBDIR belongs to a different {label} scope")
        run_id = saved.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            run_id = default_run_id
        reasons = saved.get("failure_reasons", [])
        if not isinstance(reasons, list):
            raise TypeError(f"Calendar {label} failure reasons must be a list")
        return (
            cls(
                run_id=run_id,
                run_failed=bool(saved.get("run_failed", False)),
                failure_reasons=frozenset(
                    value for value in reasons if isinstance(value, str)
                ),
            ),
            True,
        )


def execution_payload(
    *,
    run_id: str,
    scope: dict[str, object],
    run_failed: bool,
    failure_reasons: set[str],
) -> dict[str, object]:
    """Create deterministic SpiderState with no provider content or cursor data."""
    return {
        "run_id": run_id,
        "scope": scope,
        "run_failed": run_failed,
        "failure_reasons": sorted(failure_reasons),
    }


__all__ = ["CalendarScopedExecutionState", "execution_payload"]
