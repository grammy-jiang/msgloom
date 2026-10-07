"""Immutable selected-file working-context capture contracts."""

from msgloom.working_context.capture import capture
from msgloom.working_context.codec import (
    MAX_WORKING_CONTEXT_BYTES,
    WORKING_CONTEXT_KIND,
    WORKING_CONTEXT_SCHEMA_VERSION,
    WorkingContextCodec,
    configuration_ref,
    snapshot_digest,
    snapshot_ref,
)
from msgloom.working_context.models import (
    CapturedMemoryFile,
    CaptureTimePolicy,
    FileCaptureState,
    MemoryFileSelection,
    StalePolicy,
    WorkingContextConfig,
    WorkingContextLimitation,
    WorkingContextSnapshot,
)

__all__ = [
    "MAX_WORKING_CONTEXT_BYTES",
    "WORKING_CONTEXT_KIND",
    "WORKING_CONTEXT_SCHEMA_VERSION",
    "CaptureTimePolicy",
    "CapturedMemoryFile",
    "FileCaptureState",
    "MemoryFileSelection",
    "StalePolicy",
    "WorkingContextCodec",
    "WorkingContextConfig",
    "WorkingContextLimitation",
    "WorkingContextSnapshot",
    "capture",
    "configuration_ref",
    "snapshot_digest",
    "snapshot_ref",
]
