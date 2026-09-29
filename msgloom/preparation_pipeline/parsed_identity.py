"""Stable parsed-content identity construction."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable
from typing import Any

from msgloom.contracts import VersionRef
from msgloom.preparation import ParserOutput, SavedByteReference
from msgloom.preparation.isolation.wire import encode_output

from ._state import CapturedSelection
from .models import ParserProfile


async def parsed_version(
    run_sync_owned: Callable[..., Awaitable[Any]],
    captured: CapturedSelection,
    component: str,
    profile: ParserProfile,
    saved: SavedByteReference,
    output: ParserOutput,
) -> VersionRef:
    """Fingerprint selected lineage, parser policy, bytes, and output."""
    output_bytes = await run_sync_owned(encode_output, output)
    limits = profile.limits
    material = {
        "selection": {
            "kind": captured.selection.selection.kind,
            "identity": captured.selection.selection.identity,
            "version": captured.selection.selection.version,
        },
        "source": {
            "kind": captured.selection.source.kind,
            "identity": captured.selection.source.identity,
            "version": captured.selection.source.version,
        },
        "component": component,
        "saved": {
            "reference": saved.reference,
            "sha256": saved.sha256,
            "byte_count": saved.byte_count,
        },
        "format": profile.format.value,
        "parser": {
            "name": profile.parser.name,
            "version": profile.parser.version,
            "backend": profile.parser.backend,
        },
        "config": {
            "profile": profile.config.profile,
            "settings": [list(item) for item in profile.config.settings],
        },
        "limits": {
            "wall_time_seconds": limits.wall_time_seconds,
            "memory_bytes": limits.memory_bytes,
            "decompressed_bytes": limits.decompressed_bytes,
            "output_bytes": limits.output_bytes,
            "container_members": limits.container_members,
        },
        "output_sha256": hashlib.sha256(output_bytes).hexdigest(),
    }
    payload = json.dumps(
        material,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    identity = hashlib.sha256(
        (
            f"{captured.selection.source.kind}\0"
            f"{captured.selection.source.identity}\0{component}"
        ).encode()
    ).hexdigest()
    return VersionRef("parsed_content", identity, hashlib.sha256(payload).hexdigest())
