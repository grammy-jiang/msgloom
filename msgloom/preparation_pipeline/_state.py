"""Internal run state shared by A2 producer steps."""

from dataclasses import dataclass

from msgloom.contracts import Limitation, ResultRef
from msgloom.sources import CollectedSelection

from .models import SelectionPlan


@dataclass(slots=True)
class RunState:
    """Mutable state owned by one awaited handler invocation."""

    refs: list[ResultRef]
    limitations: list[Limitation]
    selected_bytes: int = 0
    derived_bytes: int = 0


@dataclass(frozen=True, slots=True)
class CapturedSelection:
    """One exact selection plus its already-durable result reference."""

    plan: SelectionPlan
    selection: CollectedSelection
    result_ref: ResultRef
