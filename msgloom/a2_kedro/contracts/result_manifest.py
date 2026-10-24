"""
``a2_result_manifest@1``: the accepted refs of one workset.

The manifest lists accepted stage refs with their metadata digests and
limitations. Each selected occurrence has exactly one terminal entry:
``prepared@2`` or ``a2_input_disposition@1``. A held occurrence has no
filter or group entry. One transition batch entry may exist. The manifest
limitations equal the union of the entry limitations, so a limitation
cannot be dropped on the way up.

CANDIDATE/RESEARCH, PROVISIONAL: names and limits are not frozen.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, ClassVar

from pydantic import model_validator

from msgloom.a2_kedro.contracts.codec import A2ContractError, Digest, Text
from msgloom.a2_kedro.contracts.result_base import (
    MAX_LIMITATIONS,
    Accepted,
    ResultModel,
    ResultPart,
    accepted_ref,
    check_limitations,
    limitation_keys,
    sorted_unique,
)
from msgloom.a2_kedro.contracts.source import Index
from msgloom.contracts import Limitation, ResultRef

MAX_ENTRIES = 4096

TERMINAL_KINDS = frozenset({"prepared", "a2_input_disposition"})
PER_OCCURRENCE_KINDS = TERMINAL_KINDS | {"filter_result", "group_result"}
BATCH_KIND = "prepared_transitions"


class ManifestEntry(ResultPart):
    """One accepted stage ref with its metadata digest and limitations."""

    workset_index: Index | None = None
    ref: ResultRef
    metadata_sha256: Digest
    status: Accepted
    limitations: tuple[Limitation, ...] = ()

    @model_validator(mode="after")
    def _shape(self) -> ManifestEntry:
        kind = self.ref.kind
        if kind not in PER_OCCURRENCE_KINDS | {BATCH_KIND}:
            raise A2ContractError("manifest entry kind is not allowed")
        accepted_ref(self.ref, kind)
        if (self.workset_index is None) != (kind == BATCH_KIND):
            raise A2ContractError("only the batch entry has no occurrence")
        check_limitations(self.status, self.limitations)
        return self

    def sort_key(self) -> tuple[Any, ...]:
        """Return the canonical ordering key."""
        index = -1 if self.workset_index is None else self.workset_index
        return (index, self.ref.kind, self.ref.result_id)


class ResultManifest(ResultModel):
    """``a2_result_manifest@1``: accepted refs, one terminal per root."""

    KIND: ClassVar[str] = "a2_result_manifest"
    workset: ResultRef
    entries: tuple[ManifestEntry, ...]
    configuration_version: Text
    code_version: Text
    policy_version: Text
    limitations: tuple[Limitation, ...] = ()

    @model_validator(mode="after")
    def _covers(self) -> ResultManifest:
        if (self.workset.kind, self.workset.schema_version) != (
            "preparation_intake_workset",
            "1",
        ):
            raise A2ContractError("foreign workset kind or version")
        if not 1 <= len(self.entries) <= MAX_ENTRIES:
            raise A2ContractError("entry count is out of bounds")
        sorted_unique([e.sort_key() for e in self.entries], "entry")
        if len({e.ref for e in self.entries}) != len(self.entries):
            raise A2ContractError("one result appears twice")
        seen = Counter((e.workset_index, e.ref.kind) for e in self.entries)
        if any(count > 1 for count in seen.values()):
            raise A2ContractError("duplicate kind for one occurrence")
        indexes = {e.workset_index for e in self.entries if e.workset_index is not None}
        for index in indexes:
            terminals = sum(seen[(index, kind)] for kind in TERMINAL_KINDS)
            if terminals != 1:
                raise A2ContractError("occurrence needs exactly one terminal")
            if seen[(index, "prepared")] == 0 and (
                seen[(index, "filter_result")] or seen[(index, "group_result")]
            ):
                raise A2ContractError("held occurrence has stage results")
        if len(self.limitations) > MAX_LIMITATIONS:
            raise A2ContractError("limitation count is out of bounds")
        union = sorted(
            {k for e in self.entries for k in limitation_keys(e.limitations)}
        )
        if limitation_keys(self.limitations) != union:
            raise A2ContractError("manifest limitations differ from entries")
        return self
