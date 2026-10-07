"""Compact integrity commitments for saved triage-input selection surfaces."""

from __future__ import annotations

from dataclasses import asdict

from msgloom.contracts import SemanticDataRef, VersionRef

from .canonical import digest
from .models import SourceRoleBinding, TrustedInputVersions


def selection_binding_digest(
    *,
    selection_hash: str,
    selected_sources: tuple[SourceRoleBinding, ...],
    prepared_refs: tuple[SemanticDataRef, ...],
    filter_refs: tuple[SemanticDataRef, ...],
    group_refs: tuple[SemanticDataRef, ...],
    rule_ref: SemanticDataRef,
    working_context_ref: VersionRef,
    versions: TrustedInputVersions,
) -> str:
    """Bind saved selection-facing references to the validated selection hash."""
    return digest(
        {
            "selection_hash": selection_hash,
            "selected_sources": [
                item.model_dump(mode="json", round_trip=True)
                for item in selected_sources
            ],
            "prepared_refs": [asdict(item) for item in prepared_refs],
            "filter_refs": [asdict(item) for item in filter_refs],
            "group_refs": [asdict(item) for item in group_refs],
            "rule_ref": asdict(rule_ref),
            "working_context_ref": asdict(working_context_ref),
            "versions": versions.model_dump(mode="json", round_trip=True),
        }
    )
