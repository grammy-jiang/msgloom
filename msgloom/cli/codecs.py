"""Bounded strict decoding for CLI-local invocation envelopes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from msgloom.delivery import (
    ReportReconciliationPlanCodec,
    ReportSubmissionPlanCodec,
)

from .models import (
    PrepareInvocation,
    ReportBuildInvocation,
    ReportReconcileInvocation,
    ReportSubmitInvocation,
    StageName,
    TriageInvocation,
)

MAX_INVOCATION_BYTES = 2 * 1024 * 1024


class InvocationError(ValueError):
    """Expose one fixed safe invocation failure code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def load_invocation(path: Path, stage: StageName) -> BaseModel:
    """Load one bounded JSON file and strictly reconstruct its exact stage model."""
    payload = _read(path)
    model: type[BaseModel]
    if stage is StageName.PREPARE:
        model = PrepareInvocation
    elif stage is StageName.TRIAGE:
        model = TriageInvocation
    elif stage is StageName.REPORT_BUILD:
        model = ReportBuildInvocation
    elif stage is StageName.REPORT_SUBMIT:
        model = ReportSubmitInvocation
    else:
        model = ReportReconcileInvocation
    value = _decode_model(payload, model)
    _reviewed_codec_gate(value)
    return value


def _read(path: Path) -> bytes:
    try:
        info = path.stat()
        if not path.is_file() or info.st_size > MAX_INVOCATION_BYTES:
            raise InvocationError("invocation_too_large")
        payload = path.read_bytes()
    except InvocationError:
        raise
    except OSError:
        raise InvocationError("invocation_unavailable") from None
    if not payload or len(payload) > MAX_INVOCATION_BYTES:
        raise InvocationError("invocation_too_large")
    return payload


def _decode_model[T: BaseModel](payload: bytes, model: type[T]) -> T:
    try:
        raw = json.loads(
            payload,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
        canonical = json.dumps(
            raw,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return model.model_validate_json(canonical, strict=True)
    except InvocationError:
        raise
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValidationError,
        TypeError,
        ValueError,
    ):
        raise InvocationError("invocation_invalid") from None


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InvocationError("invocation_duplicate_key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    del value
    raise InvocationError("invocation_invalid")


def _reviewed_codec_gate(value: BaseModel) -> None:
    try:
        if isinstance(value, ReportSubmitInvocation):
            codec = ReportSubmissionPlanCodec()
            codec.decode(codec.encode(value.plan))
        elif isinstance(value, ReportReconcileInvocation):
            codec = ReportReconciliationPlanCodec()
            codec.decode(codec.encode(value.plan))
    except (TypeError, ValueError):
        raise InvocationError("invocation_invalid") from None
