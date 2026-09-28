"""Serializable Scrapy execution state for fixed-window Calendar delta."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class CalendarDeltaExecutionState:
    """Plain execution facts restored independently of provider checkpoints."""

    run_id: str
    attempt: int
    base_revision: int | None
    terminal_delta_seen: bool
    run_failed: bool
    failure_reasons: frozenset[str]
    delta_start_scheduled: bool

    @classmethod
    def restore(
        cls,
        saved: dict[str, Any],
        *,
        start_datetime: str,
        end_datetime: str,
        calendar_scope: str,
        default_run_id: str,
    ) -> CalendarDeltaExecutionState:
        """Validate fixed scope before accepting persisted SpiderState."""
        saved_scope = (
            saved.get("start_datetime"),
            saved.get("end_datetime"),
            saved.get("calendar_scope"),
        )
        current_scope = (
            start_datetime,
            end_datetime,
            calendar_scope,
        )
        if saved_scope != current_scope:
            raise ValueError(
                "Calendar delta JOBDIR belongs to a different fixed window"
            )

        saved_run_id = saved.get("run_id")
        run_id = (
            saved_run_id
            if isinstance(saved_run_id, str) and saved_run_id
            else default_run_id
        )
        saved_revision = saved.get("base_revision")
        base_revision = (
            int(saved_revision)
            if isinstance(saved_revision, int) and saved_revision > 0
            else None
        )
        reasons = saved.get("failure_reasons", [])
        return cls(
            run_id=run_id,
            attempt=max(0, int(saved.get("attempt", 0))),
            base_revision=base_revision,
            terminal_delta_seen=bool(saved.get("terminal_delta_seen", False)),
            run_failed=bool(saved.get("run_failed", False)),
            failure_reasons=frozenset(
                value for value in reasons if isinstance(value, str)
            ),
            delta_start_scheduled=bool(saved.get("delta_start_scheduled", False)),
        )


def execution_payload(
    *,
    run_id: str,
    start_datetime: str,
    end_datetime: str,
    calendar_scope: str,
    attempt: int,
    base_revision: int | None,
    terminal_delta_seen: bool,
    run_failed: bool,
    failure_reasons: set[str],
    delta_start_scheduled: bool,
) -> dict[str, object]:
    """Create deterministic SpiderState without copying provider cursor URLs."""
    return {
        "run_id": run_id,
        "start_datetime": start_datetime,
        "end_datetime": end_datetime,
        "calendar_scope": calendar_scope,
        "attempt": attempt,
        "base_revision": base_revision,
        "terminal_delta_seen": terminal_delta_seen,
        "run_failed": run_failed,
        "failure_reasons": sorted(failure_reasons),
        "delta_start_scheduled": delta_start_scheduled,
    }
