"""Saved report selection, rendering, codec, and build handler."""

from .build import ReportBuildError, validate_semantic_coverage
from .codec import MAX_REPORT_BYTES, REPORT_KIND, REPORT_SCHEMA_VERSION, ReportCodec
from .handler import ReportBuildHandler, ReportHandlerConfig
from .models import (
    AssessmentSelection,
    DueMode,
    FrozenRendererConfig,
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
