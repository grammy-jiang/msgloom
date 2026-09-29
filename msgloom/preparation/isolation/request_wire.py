"""Strict request codec for the finite parser IPC boundary."""

from __future__ import annotations

from msgloom.preparation.contracts import (
    DocumentFormat,
    ParserLimits,
    ParserRequest,
)
from msgloom.preparation.isolation.wire import (
    _config,
    _dumps,
    _identity,
    _integer,
    _loads,
    _number,
    _object,
    _source,
    _text,
)


def _limits(value: object) -> ParserLimits:
    data = _object(
        value,
        {
            "wall_time_seconds",
            "memory_bytes",
            "decompressed_bytes",
            "output_bytes",
            "container_members",
        },
    )
    return ParserLimits(
        wall_time_seconds=_number(data["wall_time_seconds"]),
        memory_bytes=_integer(data["memory_bytes"]),
        decompressed_bytes=_integer(data["decompressed_bytes"]),
        output_bytes=_integer(data["output_bytes"]),
        container_members=_integer(data["container_members"]),
    )


def encode_request(request: ParserRequest) -> bytes:
    """Encode a validated request without executable identifiers."""
    return _dumps(
        {
            "source": {
                "reference": request.source.reference,
                "sha256": request.source.sha256,
                "byte_count": request.source.byte_count,
            },
            "detected_format": request.detected_format.value,
            "parser": {
                "name": request.parser.name,
                "version": request.parser.version,
                "backend": request.parser.backend,
            },
            "config": {
                "profile": request.config.profile,
                "settings": [list(item) for item in request.config.settings],
            },
            "limits": {
                "wall_time_seconds": request.limits.wall_time_seconds,
                "memory_bytes": request.limits.memory_bytes,
                "decompressed_bytes": request.limits.decompressed_bytes,
                "output_bytes": request.limits.output_bytes,
                "container_members": request.limits.container_members,
            },
        }
    )


def decode_request(payload: bytes) -> ParserRequest:
    """Decode a request with exact fields and contract validation."""
    data = _object(
        _loads(payload),
        {"source", "detected_format", "parser", "config", "limits"},
    )
    return ParserRequest(
        source=_source(data["source"]),
        detected_format=DocumentFormat(_text(data["detected_format"])),
        parser=_identity(data["parser"]),
        config=_config(data["config"]),
        limits=_limits(data["limits"]),
    )
