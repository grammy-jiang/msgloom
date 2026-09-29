"""Saved report selection, rendering, codec, and build handler."""

from typing import TYPE_CHECKING

from .build import ReportBuildError, validate_semantic_coverage
from .codec import MAX_REPORT_BYTES, REPORT_KIND, REPORT_SCHEMA_VERSION, ReportCodec
from .config import ReportHandlerConfig
from .history import ReportHistoryEvidence, ReportHistoryMetadata, ReportHistoryResolver
from .models import (
    AssessmentSelection,
    DueMode,
    FrozenRendererConfig,
    FrozenReportHistory,
    FrozenReportInput,
    FrozenReportSelection,
    PendingAssessmentWarning,
    PriorReportState,
    ReminderMode,
    RepeatMode,
    ReportDestination,
    ReportOverviewItem,
    ReportPart,
    ReportPolicy,
    ReportSelectionPlan,
    ReportTopic,
    SavedReport,
    SourceLink,
)
from .renderer import RENDERER_VERSION, RendererConfig, render_report
from .selection import ReportSelectionError, select_topics
from .selection_codec import (
    REPORT_SELECTION_KIND,
    REPORT_SELECTION_SCHEMA_VERSION,
    ReportSelectionCodec,
)

if TYPE_CHECKING:
    from .handler import ReportBuildHandler

__all__ = [
    "MAX_REPORT_BYTES",
    "RENDERER_VERSION",
    "REPORT_KIND",
    "REPORT_SCHEMA_VERSION",
    "REPORT_SELECTION_KIND",
    "REPORT_SELECTION_SCHEMA_VERSION",
    "AssessmentSelection",
    "DueMode",
    "FrozenRendererConfig",
    "FrozenReportHistory",
    "FrozenReportInput",
    "FrozenReportSelection",
    "PendingAssessmentWarning",
    "PriorReportState",
    "ReminderMode",
    "RendererConfig",
    "RepeatMode",
    "ReportBuildError",
    "ReportBuildHandler",
    "ReportCodec",
    "ReportDestination",
    "ReportHandlerConfig",
    "ReportHistoryEvidence",
    "ReportHistoryMetadata",
    "ReportHistoryResolver",
    "ReportOverviewItem",
    "ReportPart",
    "ReportPolicy",
    "ReportSelectionCodec",
    "ReportSelectionError",
    "ReportSelectionPlan",
    "ReportTopic",
    "SavedReport",
    "SourceLink",
    "render_report",
    "select_topics",
    "validate_semantic_coverage",
]


def __getattr__(name: str) -> object:
    """Load persistence-backed handler types only when explicitly requested."""
    if name in {"ReportBuildHandler", "ReportHandlerConfig"}:
        from .handler import ReportBuildHandler

        return {
            "ReportBuildHandler": ReportBuildHandler,
            "ReportHandlerConfig": ReportHandlerConfig,
        }[name]
    raise AttributeError(name)
