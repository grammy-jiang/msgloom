"""CLI-local explicit semantic registry composition."""

from msgloom.ai_evidence.codecs import AI_EVIDENCE_CODECS
from msgloom.delivery import ReportSubmissionCodec
from msgloom.persistence import SemanticDataRegistry
from msgloom.preparation.codec import PreparedDataCodec
from msgloom.preparation.filtering import FilterResultCodec
from msgloom.preparation.grouping import GroupResultCodec
from msgloom.preparation_pipeline import DerivedByteArtifactCodec
from msgloom.reporting import ReportCodec, ReportSelectionCodec
from msgloom.sources import CollectedSelectionCodec
from msgloom.triage import TriageDataCodec
from msgloom.triage.rule_codec import TriageRuleEvaluationCodec
from msgloom.triage_input.codec import TriageInputCodec
from msgloom.triage_pipeline import InputPartCodec, TriagePartStateCodec
from msgloom.working_context.codec import WorkingContextCodec


def full_semantic_registry() -> SemanticDataRegistry:
    """Compose reviewed Phase 1 codecs plus opt-in delivery semantic data."""
    return SemanticDataRegistry(
        (
            CollectedSelectionCodec(),
            DerivedByteArtifactCodec(),
            ReportSelectionCodec(),
            ReportCodec(),
            ReportSubmissionCodec(),
            InputPartCodec(),
            TriagePartStateCodec(),
            PreparedDataCodec(),
            FilterResultCodec(),
            GroupResultCodec(),
            WorkingContextCodec(),
            TriageRuleEvaluationCodec(),
            TriageInputCodec(),
            TriageDataCodec(),
            *AI_EVIDENCE_CODECS,
        )
    )
