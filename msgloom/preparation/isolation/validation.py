"""Input validation performed before any format parser is imported."""

from __future__ import annotations

import hashlib
import stat
from io import BytesIO
from pathlib import PurePosixPath
from zipfile import BadZipFile, ZipFile

from msgloom.preparation.contracts import DocumentFormat, ParserRequest

_ZIP_FORMATS = {
    DocumentFormat.XLSX,
    DocumentFormat.XLSM,
    DocumentFormat.XLSB,
    DocumentFormat.ODS,
    DocumentFormat.DOCX,
}
_OLE_FORMATS = {DocumentFormat.XLS, DocumentFormat.DOC}
_OLE_MAGIC = bytes.fromhex("d0cf11e0a1b11ae1")
_REQUIRED_ZIP_MEMBERS = {
    DocumentFormat.XLSX: {"[Content_Types].xml", "xl/workbook.xml"},
    DocumentFormat.XLSM: {"[Content_Types].xml", "xl/workbook.xml"},
    DocumentFormat.XLSB: {"[Content_Types].xml", "xl/workbook.bin"},
    DocumentFormat.ODS: {"mimetype", "content.xml"},
    DocumentFormat.DOCX: {"[Content_Types].xml", "word/document.xml"},
}
_CHUNK_BYTES = 64 * 1024


class InputValidationError(ValueError):
    """Raised when saved bytes do not satisfy their declared parse contract."""


def verify_saved_bytes(request: ParserRequest, content: bytes) -> None:
    """Verify immutable saved-byte identity before a process is launched."""
    if not isinstance(content, bytes):
        raise TypeError("parser content must be immutable bytes")
    if len(content) != request.source.byte_count:
        raise InputValidationError("saved byte count does not match parser content")
    digest = hashlib.sha256(content).hexdigest()
    if digest.lower() != request.source.sha256.lower():
        raise InputValidationError("saved byte hash does not match parser content")
    if len(content) > request.limits.decompressed_bytes:
        raise InputValidationError("parser input exceeds the decoded-byte ceiling")


def validate_format_content(
    request: ParserRequest, content: bytes, *, deep: bool = True
) -> None:
    """Validate signatures and bounded containers before parser import.

    Parent preflight may skip decompression; the sandbox always performs
    the full streaming pass before importing native parsers.
    """
    format_ = request.detected_format
    if format_ is DocumentFormat.PDF:
        if b"%PDF-" not in content[:1024]:
            raise InputValidationError("PDF signature is missing")
        return
    if format_ in _OLE_FORMATS:
        if not content.startswith(_OLE_MAGIC):
            raise InputValidationError("OLE compound-file signature is missing")
        return
    if format_ in _ZIP_FORMATS:
        _validate_zip(request, content, deep=deep)


def _validate_zip(request: ParserRequest, content: bytes, *, deep: bool) -> None:
    try:
        with ZipFile(BytesIO(content)) as archive:
            members = archive.infolist()
            if len(members) > request.limits.container_members:
                raise InputValidationError("container member ceiling exceeded")
            names: set[str] = set()
            declared_total = 0
            for member in members:
                _validate_member(member.filename, member.external_attr)
                if member.filename in names:
                    raise InputValidationError("duplicate container member")
                names.add(member.filename)
                if member.flag_bits & 0x1:
                    raise InputValidationError(
                        "encrypted container member is unsupported"
                    )
                declared_total += member.file_size
                if declared_total > request.limits.decompressed_bytes:
                    raise InputValidationError(
                        "container decoded-byte ceiling exceeded"
                    )
            required = _REQUIRED_ZIP_MEMBERS[request.detected_format]
            if not required.issubset(names):
                raise InputValidationError("container structure does not match format")
            if deep:
                _read_bounded_members(archive, request.limits.decompressed_bytes)
    except (BadZipFile, EOFError, OSError) as exc:
        raise InputValidationError("invalid document container") from exc


def _validate_member(name: str, external_attr: int) -> None:
    path = PurePosixPath(name)
    if (
        not name
        or "\\" in name
        or path.is_absolute()
        or ".." in path.parts
        or "." in path.parts
    ):
        raise InputValidationError("unsafe container member path")
    mode = (external_attr >> 16) & 0o170000
    if mode == stat.S_IFLNK:
        raise InputValidationError("container symlink member is forbidden")


def _read_bounded_members(archive: ZipFile, limit: int) -> None:
    total = 0
    for member in archive.infolist():
        if member.is_dir():
            continue
        with archive.open(member, "r") as stream:
            while chunk := stream.read(_CHUNK_BYTES):
                total += len(chunk)
                if total > limit:
                    raise InputValidationError(
                        "container decoded-byte ceiling exceeded"
                    )
