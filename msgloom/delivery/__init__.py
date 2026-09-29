"""Finite owner-only saved report delivery and reconciliation."""

from typing import TYPE_CHECKING

from .codec import (
    MAX_SUBMISSION_BYTES,
    REPORT_SUBMISSION_KIND,
    REPORT_SUBMISSION_SCHEMA_VERSION,
    ReportReconciliationPlanCodec,
    ReportSubmissionCodec,
    ReportSubmissionPlanCodec,
    SubmissionAttemptCodec,
    SubmissionReceiptCodec,
)
from .mime import build_mime, validate_owner_address
from .models import (
    ProviderEvidence,
    ReconciliationEvidence,
    ReportReconciliationPlan,
    ReportSubmissionPlan,
    SubmissionAttempt,
    SubmissionHandlerConfig,
    SubmissionHistory,
    SubmissionPartPlan,
    SubmissionReceipt,
)
from .transport import (
    GraphSendMailTransport,
    HttpResponse,
    OneShotHttpTransport,
    ReportTransport,
    TransportReceipt,
)

if TYPE_CHECKING:
    from .handler import ReportSubmissionHandler
    from .history import DeliveryReportHistoryResolver
    from .reconciliation import ReportReconciler, submission_claim_key

__all__ = [
    "MAX_SUBMISSION_BYTES",
    "REPORT_SUBMISSION_KIND",
    "REPORT_SUBMISSION_SCHEMA_VERSION",
    "DeliveryReportHistoryResolver",
    "GraphSendMailTransport",
    "HttpResponse",
    "OneShotHttpTransport",
    "ProviderEvidence",
    "ReconciliationEvidence",
    "ReportReconciler",
    "ReportReconciliationPlan",
    "ReportReconciliationPlanCodec",
    "ReportSubmissionCodec",
    "ReportSubmissionHandler",
    "ReportSubmissionPlan",
    "ReportSubmissionPlanCodec",
    "ReportTransport",
    "SubmissionAttempt",
    "SubmissionAttemptCodec",
    "SubmissionHandlerConfig",
    "SubmissionHistory",
    "SubmissionPartPlan",
    "SubmissionReceipt",
    "SubmissionReceiptCodec",
    "TransportReceipt",
    "build_mime",
    "submission_claim_key",
    "validate_owner_address",
]


def __getattr__(name: str) -> object:
    """Load persistence-backed delivery only after codec composition."""
    if name == "ReportSubmissionHandler":
        from .handler import ReportSubmissionHandler

        return ReportSubmissionHandler
    if name == "DeliveryReportHistoryResolver":
        from .history import DeliveryReportHistoryResolver

        return DeliveryReportHistoryResolver
    if name in {"ReportReconciler", "submission_claim_key"}:
        from .reconciliation import ReportReconciler, submission_claim_key

        return {
            "ReportReconciler": ReportReconciler,
            "submission_claim_key": submission_claim_key,
        }[name]
    raise AttributeError(name)
