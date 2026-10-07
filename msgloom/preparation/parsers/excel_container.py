"""Preflight spreadsheet containers before native parser code sees bytes."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import PurePosixPath
from zipfile import ZIP_STORED, BadZipFile, ZipFile

from defusedxml.ElementTree import fromstring

from msgloom.preparation.contracts import (
    DocumentFormat,
    LimitationKind,
    ParserLimitation,
    ParserRequest,
)

_ZIP_FORMATS = {
    DocumentFormat.XLSX,
    DocumentFormat.XLSM,
    DocumentFormat.XLSB,
    DocumentFormat.ODS,
}
_OLE_MAGIC = bytes.fromhex("d0cf11e0a1b11ae1")
_ZIP_MAGIC = b"PK\x03\x04"


@dataclass(frozen=True, slots=True)
class ContainerFacts:
    """Bounded package facts used to disclose unsupported workbook features."""

    members: frozenset[str] = frozenset()
    fatal_limitation: ParserLimitation | None = None
    limitations: tuple[ParserLimitation, ...] = ()


def _limitation(
    kind: LimitationKind, code: str, detail: str, feature: str
) -> ParserLimitation:
    return ParserLimitation(kind=kind, code=code, detail=detail, feature=feature)


def _validate_source(request: ParserRequest, content: bytes) -> None:
    if len(content) != request.source.byte_count:
        raise ValueError("spreadsheet byte count does not match saved source reference")
    if sha256(content).hexdigest() != request.source.sha256.lower():
        raise ValueError("spreadsheet digest does not match saved source reference")
    if len(content) > request.limits.decompressed_bytes:
        raise ValueError("spreadsheet bytes exceed decompression ceiling")


def _safe_member_name(name: str) -> bool:
    path = PurePosixPath(name)
    return (
        bool(name)
        and not name.startswith(("/", "\\"))
        and "\\" not in name
        and ".." not in path.parts
    )


def _required_members(fmt: DocumentFormat) -> frozenset[str]:
    if fmt in {DocumentFormat.XLSX, DocumentFormat.XLSM}:
        return frozenset({"[Content_Types].xml", "_rels/.rels", "xl/workbook.xml"})
    if fmt is DocumentFormat.XLSB:
        return frozenset({"[Content_Types].xml", "_rels/.rels", "xl/workbook.bin"})
    if fmt is DocumentFormat.ODS:
        return frozenset({"mimetype", "content.xml", "META-INF/manifest.xml"})
    return frozenset()


_WORKBOOK_CONTENT_TYPES = {
    DocumentFormat.XLSX: (
        "/xl/workbook.xml",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml",
    ),
    DocumentFormat.XLSM: (
        "/xl/workbook.xml",
        "application/vnd.ms-excel.sheet.macroEnabled.main+xml",
    ),
    DocumentFormat.XLSB: (
        "/xl/workbook.bin",
        "application/vnd.ms-excel.sheet.binary.macroEnabled.main",
    ),
}


def _validate_package_format(request: ParserRequest, content: bytes) -> None:
    expected = _WORKBOOK_CONTENT_TYPES.get(request.detected_format)
    if expected is None:
        return
    with ZipFile(BytesIO(content)) as archive:
        root = fromstring(archive.read("[Content_Types].xml"))
    part_name, content_type = expected
    matches = {
        (item.get("PartName"), item.get("ContentType"))
        for item in root
        if item.tag.endswith("Override")
    }
    if (part_name, content_type) not in matches:
        raise ValueError(
            "spreadsheet package type does not match detected spreadsheet format"
        )


def _feature_limitations(
    fmt: DocumentFormat, members: frozenset[str]
) -> tuple[ParserLimitation, ...]:
    limitations: list[ParserLimitation] = []
    if any(name.lower().endswith("vbaproject.bin") for name in members):
        limitations.append(
            _limitation(
                LimitationKind.UNSUPPORTED,
                "excel-macros-not-executed",
                "VBA project bytes are retained in the source but are not "
                "executed or extracted.",
                "macros",
            )
        )
    if any(name.startswith("xl/embeddings/") for name in members):
        limitations.append(
            _limitation(
                LimitationKind.UNSUPPORTED,
                "excel-embedded-content-not-extracted",
                "Embedded workbook objects are not parsed by this extraction lane.",
                "embedded-content",
            )
        )
    if any(name.startswith("xl/externalLinks/") for name in members):
        limitations.append(
            _limitation(
                LimitationKind.PARTIAL,
                "excel-external-links-not-accessed",
                "External workbook links are retained as source metadata only "
                "and are never fetched.",
                "external-links",
            )
        )
    if fmt is DocumentFormat.ODS:
        if any(name.startswith("Scripts/") for name in members):
            limitations.append(
                _limitation(
                    LimitationKind.UNSUPPORTED,
                    "excel-macros-not-executed",
                    "OpenDocument script members are not executed or extracted.",
                    "macros",
                )
            )
        if any(name.startswith(("Object ", "ObjectReplacements/")) for name in members):
            limitations.append(
                _limitation(
                    LimitationKind.UNSUPPORTED,
                    "excel-embedded-content-not-extracted",
                    "OpenDocument embedded objects are not parsed by this lane.",
                    "embedded-content",
                )
            )
    if fmt in {DocumentFormat.XLSB, DocumentFormat.ODS}:
        limitations.append(
            _limitation(
                LimitationKind.PARTIAL,
                "excel-detailed-metadata-unavailable",
                "Formula, row/column visibility, hyperlink, and formatting "
                "metadata are unavailable for this format in the selected "
                "metadata backend.",
                "metadata",
            )
        )
        limitations.append(
            _limitation(
                LimitationKind.PARTIAL,
                "excel-cell-presence-unavailable",
                "The value backend cannot distinguish padded absent cells from "
                "explicit empty strings; ambiguous empty values are omitted.",
                "cell-presence",
            )
        )
    if fmt is DocumentFormat.XLSB:
        limitations.append(
            _limitation(
                LimitationKind.PARTIAL,
                "excel-xlsb-value-coverage-unverified",
                "The pinned value backend is not qualified for complete XLSB "
                "cell coverage; valid numeric cells may be omitted.",
                "value-coverage",
            )
        )
    return tuple(limitations)


def _preflight_zip(request: ParserRequest, content: bytes) -> ContainerFacts:
    if not content.startswith(_ZIP_MAGIC):
        if content.startswith(_OLE_MAGIC):
            raise ValueError(
                "compound spreadsheet container does not match detected ZIP format"
            )
        raise ValueError("spreadsheet signature does not match the detected ZIP format")
    try:
        with ZipFile(BytesIO(content)) as archive:
            infos = archive.infolist()
    except BadZipFile as exc:
        raise ValueError("malformed spreadsheet ZIP container") from exc
    if len(infos) > request.limits.container_members:
        raise ValueError("spreadsheet container member ceiling exceeded")
    names = [info.filename for info in infos]
    if len(names) != len(set(names)):
        raise ValueError("spreadsheet container has duplicate member names")
    if any(not _safe_member_name(name) for name in names):
        raise ValueError("spreadsheet container has an unsafe member name")
    if any(info.flag_bits & 0x1 for info in infos):
        return ContainerFacts(
            members=frozenset(names),
            fatal_limitation=_limitation(
                LimitationKind.ENCRYPTED,
                "excel-encrypted-member",
                "The spreadsheet package contains an encrypted ZIP member.",
                "encryption",
            ),
        )
    expanded = sum(info.file_size for info in infos)
    if expanded > request.limits.decompressed_bytes:
        raise ValueError("spreadsheet decompressed member ceiling exceeded")
    members = frozenset(names)
    missing = _required_members(request.detected_format) - members
    if missing:
        raise ValueError(
            "spreadsheet container is missing required members: "
            + ", ".join(sorted(missing))
        )
    if request.detected_format is DocumentFormat.ODS:
        first = infos[0]
        if first.filename != "mimetype" or first.compress_type != ZIP_STORED:
            raise ValueError("ODS mimetype member must be first and uncompressed")
        if first.extra:
            raise ValueError("ODS mimetype member must not use an extra field")
        with ZipFile(BytesIO(content)) as archive:
            media_type = archive.read("mimetype")
        if media_type != b"application/vnd.oasis.opendocument.spreadsheet":
            raise ValueError("ODS package has an unexpected media type")
    return ContainerFacts(
        members=members,
        limitations=_feature_limitations(request.detected_format, members),
    )


def preflight_container(request: ParserRequest, content: bytes) -> ContainerFacts:
    """Verify source integrity, signature, structure, and finite limits."""
    _validate_source(request, content)
    if request.detected_format in _ZIP_FORMATS:
        facts = _preflight_zip(request, content)
        if facts.members and facts.fatal_limitation is None:
            _validate_package_format(request, content)
        return facts
    if request.detected_format is DocumentFormat.XLS:
        if not content.startswith(_OLE_MAGIC):
            raise ValueError("XLS signature does not match an OLE compound document")
        return ContainerFacts(
            limitations=(
                _limitation(
                    LimitationKind.PARTIAL,
                    "excel-detailed-metadata-unavailable",
                    "Formula, row/column visibility, hyperlink, and formatting "
                    "metadata are unavailable for XLS in the selected metadata "
                    "backend.",
                    "metadata",
                ),
                _limitation(
                    LimitationKind.PARTIAL,
                    "excel-cell-presence-unavailable",
                    "The value backend cannot distinguish padded absent cells "
                    "from explicit empty strings; ambiguous empty values are "
                    "omitted.",
                    "cell-presence",
                ),
            )
        )
    raise ValueError(f"unsupported spreadsheet format: {request.detected_format.value}")
