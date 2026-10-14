"""Causal, source-scoped identity of committed Microsoft Graph delta cursors.

Tokens remain in the private catalog. Only SHA-256 identity tags may enter
Scrapy JOBDIR state, pipeline items, or the candidate-baseline ledger.
"""

from __future__ import annotations

import hashlib
import json
import re

from message_ingest.catalog.models.microsoft.outlook.email import (
    DeltaCheckpoint,
)

_BASELINE = re.compile(r"^(?:a|p):[0-9a-f]{64}$")


def validate_baseline(value: str | None) -> str:
    """Missing proof is never equivalent to an explicitly absent checkpoint."""
    if not isinstance(value, str) or not _BASELINE.fullmatch(value):
        raise ValueError("Invalid Mail delta causal baseline")
    return value


def _digest(parts: list[str]) -> str:
    raw = json.dumps(parts, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def absent_baseline(source_id: str, folder_id: str, *, generation: int = 0) -> str:
    """Scope an absent checkpoint to its durable post-removal epoch."""
    if type(generation) is not int or generation < 0:
        raise ValueError("Invalid Mail delta absence generation")
    return "a:" + _digest(
        [
            "mail-delta-baseline-v1",
            source_id,
            folder_id,
            "absent",
            str(generation),
        ]
    )


def committed_baseline(
    source_id: str,
    folder_id: str,
    *,
    delta_link: str,
    run_id: str,
    committed_at: str,
) -> str:
    """Bind exact opaque cursor bytes AND its committed generation/owner."""
    return "p:" + _digest(
        [
            "mail-delta-baseline-v1",
            source_id,
            folder_id,
            run_id,
            committed_at,
            delta_link,
        ]
    )


def current_baseline(
    source_id: str,
    folder_id: str,
    checkpoint: DeltaCheckpoint | None,
    *,
    absence_generation: int = 0,
) -> str:
    if checkpoint is None:
        return absent_baseline(source_id, folder_id, generation=absence_generation)
    return committed_baseline(
        source_id,
        folder_id,
        delta_link=checkpoint.delta_link,
        run_id=checkpoint.run_id,
        committed_at=checkpoint.committed_at,
    )


__all__ = [
    "absent_baseline",
    "committed_baseline",
    "current_baseline",
    "validate_baseline",
]
