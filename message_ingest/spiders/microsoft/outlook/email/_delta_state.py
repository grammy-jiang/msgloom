"""Serializable Scrapy execution state for Outlook Mail delta."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class MailDeltaCommitMode(StrEnum):
    """Private message-delta promotion ownership mode."""

    IMMEDIATE = "immediate"
    DEFERRED = "deferred"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class MailDeltaExecutionState:
    """Plain execution facts restored independently of provider checkpoints."""

    run_id: str
    seen_folder_ids: frozenset[str]
    started_folder_ids: frozenset[str]
    completed_folder_ids: frozenset[str]
    reconcile_orphan_ids: frozenset[str]
    folder_inventory_pending: int
    folder_inventory_complete: bool
    folder_inventory_failed: bool
    reconcile_complete: bool
    run_failed: bool
    failure_reasons: frozenset[str]
    delta_start_scheduled: bool

    @classmethod
    def restore(
        cls,
        saved: dict[str, Any],
        *,
        default_run_id: str,
    ) -> MailDeltaExecutionState:
        """Restore deterministic execution facts from Scrapy SpiderState."""
        saved_run_id = saved.get("run_id")
        run_id = (
            saved_run_id
            if isinstance(saved_run_id, str) and saved_run_id
            else default_run_id
        )
        return cls(
            run_id=run_id,
            seen_folder_ids=frozenset(saved.get("seen_folder_ids", [])),
            started_folder_ids=frozenset(saved.get("started_folder_ids", [])),
            completed_folder_ids=frozenset(saved.get("completed_folder_ids", [])),
            reconcile_orphan_ids=frozenset(saved.get("reconcile_orphan_ids", [])),
            folder_inventory_pending=int(saved.get("folder_inventory_pending", 0)),
            folder_inventory_complete=bool(
                saved.get("folder_inventory_complete", False)
            ),
            folder_inventory_failed=bool(saved.get("folder_inventory_failed", False)),
            reconcile_complete=bool(saved.get("reconcile_complete", False)),
            run_failed=bool(saved.get("run_failed", False)),
            failure_reasons=frozenset(saved.get("failure_reasons", [])),
            delta_start_scheduled=bool(saved.get("delta_start_scheduled", False)),
        )


def execution_payload(
    *,
    run_id: str,
    seen_folder_ids: set[str],
    started_folder_ids: set[str],
    completed_folder_ids: set[str],
    reconcile_orphan_ids: set[str],
    folder_inventory_pending: int,
    folder_inventory_complete: bool,
    folder_inventory_failed: bool,
    reconcile_complete: bool,
    run_failed: bool,
    failure_reasons: set[str],
    delta_start_scheduled: bool,
) -> dict[str, object]:
    """Create deterministic SpiderState without copying provider cursor URLs."""
    return {
        "run_id": run_id,
        "seen_folder_ids": sorted(seen_folder_ids),
        "started_folder_ids": sorted(started_folder_ids),
        "completed_folder_ids": sorted(completed_folder_ids),
        "reconcile_orphan_ids": sorted(reconcile_orphan_ids),
        "folder_inventory_pending": folder_inventory_pending,
        "folder_inventory_complete": folder_inventory_complete,
        "folder_inventory_failed": folder_inventory_failed,
        "reconcile_complete": reconcile_complete,
        "run_failed": run_failed,
        "failure_reasons": sorted(failure_reasons),
        "delta_start_scheduled": delta_start_scheduled,
    }


__all__ = ["MailDeltaCommitMode", "MailDeltaExecutionState", "execution_payload"]
