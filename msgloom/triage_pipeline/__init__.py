"""Finite awaited A3 producer composition."""

from typing import TYPE_CHECKING

from .codecs import (
    TRIAGE_PART_STATE_KIND,
    TRIAGE_PART_STATE_SCHEMA_VERSION,
    TRIAGE_PIPELINE_CODECS,
    TRIAGE_PIPELINE_RESULT_SCHEMAS,
    InputPartCodec,
    TriagePartState,
    TriagePartStateCodec,
)
from .models import TriageMode, TriageProducerConfig, TriageReplayPlan

if TYPE_CHECKING:
    from .handler import TriageHandler, TriageRunner

__all__ = [
    "TRIAGE_PART_STATE_KIND",
    "TRIAGE_PART_STATE_SCHEMA_VERSION",
    "TRIAGE_PIPELINE_CODECS",
    "TRIAGE_PIPELINE_RESULT_SCHEMAS",
    "InputPartCodec",
    "TriageHandler",
    "TriageMode",
    "TriagePartState",
    "TriagePartStateCodec",
    "TriageProducerConfig",
    "TriageReplayPlan",
    "TriageRunner",
]


def __getattr__(name: str) -> object:
    """Load persistence-backed execution only after codec composition."""
    if name in {"TriageHandler", "TriageRunner"}:
        from .handler import TriageHandler, TriageRunner

        return {"TriageHandler": TriageHandler, "TriageRunner": TriageRunner}[name]
    raise AttributeError(name)
