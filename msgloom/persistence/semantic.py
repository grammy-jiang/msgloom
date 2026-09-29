"""Registered codecs and integrity references for semantic result data."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Protocol

from msgloom.ai_evidence.codecs import AI_EVIDENCE_CODECS
from msgloom.contracts import SemanticDataRef
from msgloom.delivery.codec import ReportSubmissionCodec
from msgloom.persistence.errors import (
    SemanticDataIntegrityError,
    SemanticDataReferenceError,
    SemanticDataTooLargeError,
    SemanticDataTypeError,
    UnknownSemanticDataSchemaError,
)
from msgloom.preparation.codec import PreparedDataCodec
from msgloom.preparation.filtering import FilterResultCodec
from msgloom.preparation.grouping import GroupResultCodec
from msgloom.preparation_pipeline.codec import DerivedByteArtifactCodec
from msgloom.reporting.codec import ReportCodec
from msgloom.reporting.selection_codec import ReportSelectionCodec
from msgloom.sources import CollectedSelectionCodec
from msgloom.triage.codec import TriageDataCodec
from msgloom.triage.rule_codec import TriageRuleEvaluationCodec
from msgloom.triage_input.codec import TriageInputCodec
from msgloom.triage_pipeline.codecs import InputPartCodec, TriagePartStateCodec
from msgloom.working_context.codec import WorkingContextCodec


class _SemanticCodec(Protocol):
    """Minimal contract implemented by each reviewed semantic schema."""

    kind: str
    schema_version: str
    max_bytes: int

    def encode(self, value: object) -> bytes:
        """Encode validated data canonically."""
        ...

    def decode(self, payload: bytes) -> object:
        """Decode and validate canonical data."""
        ...


@dataclass(frozen=True, slots=True)
class EncodedSemanticData:
    """Validated canonical bytes paired with their integrity reference."""

    reference: SemanticDataRef
    payload: bytes


class SemanticDataRegistry:
    """Exact allowlist of semantic kind/schema codecs used by persistence."""

    def __init__(self, codecs: tuple[_SemanticCodec, ...]) -> None:
        keys = tuple((codec.kind, codec.schema_version) for codec in codecs)
        if len(keys) != len(set(keys)):
            raise ValueError("semantic codec kind/schema registrations must be unique")
        self._codecs = codecs

    @classmethod
    def phase1(cls) -> SemanticDataRegistry:
        """Register only semantic schemas with implemented consumers."""
        return cls(
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

    def reference(
        self,
        data_id: str,
        kind: str,
        schema_version: str,
        value: object,
    ) -> SemanticDataRef:
        """Build the exact integrity reference for validated canonical data."""
        return self.encode(data_id, kind, schema_version, value).reference

    def encode(
        self,
        data_id: str,
        kind: str,
        schema_version: str,
        value: object,
    ) -> EncodedSemanticData:
        """Validate and encode one registered semantic payload."""
        codec = self._codec(kind, schema_version)
        try:
            payload = codec.encode(value)
        except TypeError as exc:
            raise SemanticDataTypeError(str(exc)) from exc
        if len(payload) > codec.max_bytes:
            raise SemanticDataTooLargeError(
                f"{kind}@{schema_version} semantic data exceeds {codec.max_bytes} bytes"
            )
        reference = SemanticDataRef(
            data_id=data_id,
            kind=kind,
            schema_version=schema_version,
            sha256=sha256(payload).hexdigest(),
            byte_count=len(payload),
        )
        return EncodedSemanticData(reference=reference, payload=payload)

    def encode_for_reference(
        self, reference: SemanticDataRef, value: object
    ) -> EncodedSemanticData:
        """Validate data and require its exact predeclared reference."""
        encoded = self.encode(
            reference.data_id, reference.kind, reference.schema_version, value
        )
        if encoded.reference != reference:
            raise SemanticDataReferenceError(
                "semantic data does not match the declared integrity reference"
            )
        return encoded

    def decode(self, reference: SemanticDataRef, payload: bytes) -> object:
        """Verify integrity, schema, canonical form, and decoded contract."""
        codec = self._codec(reference.kind, reference.schema_version)
        if len(payload) != reference.byte_count:
            raise SemanticDataIntegrityError("semantic data byte count is corrupted")
        if sha256(payload).hexdigest() != reference.sha256:
            raise SemanticDataIntegrityError("semantic data digest is corrupted")
        try:
            value = codec.decode(payload)
        except (TypeError, ValueError) as exc:
            raise SemanticDataIntegrityError(str(exc)) from exc
        encoded = self.encode_for_reference(reference, value)
        if encoded.payload != payload:
            raise SemanticDataIntegrityError("semantic data is not canonical")
        return value

    def _codec(self, kind: str, schema_version: str) -> _SemanticCodec:
        for codec in self._codecs:
            if codec.kind == kind and codec.schema_version == schema_version:
                return codec
        raise UnknownSemanticDataSchemaError(
            f"unregistered semantic data schema: {kind!r} version {schema_version!r}"
        )
