"""
``a2_input_disposition@1``: an A2-owned held record for one occurrence.

A held record says A2 could not prepare an exact selected occurrence. It
carries a closed reason and an explicit ``repair_class``. It never carries
fabricated content. Intake-held entries (``workset.held``) are frozen by
Intake and A2 cannot write them back; only the receipt counts them.

The record is built from a verified :class:`FrozenRoot` so its source
fields cannot drift from the root. Held-only, context-only and baseline
worksets do not force a body: a held record is a legal terminal.

CANDIDATE/RESEARCH: not wired into any writer.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import model_validator

from msgloom.a2_kedro.contracts.codec import A2ContractError, A2Model, Digest, Text
from msgloom.a2_kedro.contracts.source import FrozenRoot, Index
from msgloom.contracts import ResultRef, VersionRef
from msgloom.sources.handoff_models import ReleaseEntryRef

KIND = "a2_input_disposition"
VERSION = "1"


class HeldReason(StrEnum):
    """Closed, content-free reasons that A2 holds an occurrence."""

    ROLE_UNVERIFIABLE = "role_unverifiable"
    SOURCE_EVIDENCE_UNAVAILABLE = "source_evidence_unavailable"
    PARSER_UNSUPPORTED = "parser_unsupported"
    INPUT_LIMIT = "input_limit"
    PROOF_MISSING = "proof_missing"


class InputDisposition(A2Model):
    """Held record for one exact incremental or baseline occurrence."""

    selected: ResultRef
    workset_index: Index
    selection_sha256: Digest
    reason: HeldReason
    configuration_version: Text
    code_version: Text
    repair_class: Literal["operator_repair"] = "operator_repair"
    entry: ReleaseEntryRef | None = None
    baseline_source: VersionRef | None = None
    baseline_approval: Text | None = None

    @model_validator(mode="after")
    def _exclusive_source(self) -> InputDisposition:
        if (self.selected.kind, self.selected.schema_version) != (
            "collected_selection",
            "1",
        ):
            raise A2ContractError("held record needs collected_selection@1")
        baseline = (self.baseline_source, self.baseline_approval)
        if self.entry is not None:
            if any(v is not None for v in baseline):
                raise A2ContractError("incremental held cannot be baseline")
            return self
        if any(v is None for v in baseline):
            raise A2ContractError("baseline held needs approved source")
        return self

    @classmethod
    def from_root(
        cls,
        root: FrozenRoot,
        reason: HeldReason,
        *,
        configuration_version: str,
        code_version: str,
    ) -> InputDisposition:
        """Build the record from a verified root; source fields are copied."""
        return cls(
            selected=root.selected,
            workset_index=root.workset_index,
            selection_sha256=root.selection_sha256,
            reason=reason,
            configuration_version=configuration_version,
            code_version=code_version,
            entry=root.entry,
            baseline_source=root.baseline_source,
            baseline_approval=root.baseline_approval,
        )
