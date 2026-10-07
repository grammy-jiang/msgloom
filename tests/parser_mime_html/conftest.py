"""Synthetic request helpers for the MIME/HTML parser lane."""

from __future__ import annotations

from hashlib import sha256

from msgloom.preparation.contracts import (
    DocumentFormat,
    ParserConfig,
    ParserIdentity,
    ParserLimits,
    ParserRequest,
    SavedByteReference,
)

PARSER_NAME = "msgloom.mime-html"
PARSER_VERSION = "1"
BACKEND = "stdlib-email+selectolax-0.4.12"


def parser_request(
    content: bytes,
    detected_format: DocumentFormat,
    *,
    decompressed_bytes: int = 1_000_000,
    output_bytes: int = 1_000_000,
    container_members: int = 100,
) -> ParserRequest:
    """Build one exact synthetic parser request."""
    return ParserRequest(
        source=SavedByteReference(
            reference="saved:synthetic",
            sha256=sha256(content).hexdigest(),
            byte_count=len(content),
        ),
        detected_format=detected_format,
        parser=ParserIdentity(
            name=PARSER_NAME,
            version=PARSER_VERSION,
            backend=BACKEND,
        ),
        config=ParserConfig(profile="mime-html-v1"),
        limits=ParserLimits(
            wall_time_seconds=5,
            memory_bytes=64 * 1024 * 1024,
            decompressed_bytes=decompressed_bytes,
            output_bytes=output_bytes,
            container_members=container_members,
        ),
    )
