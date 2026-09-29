"""Fail-closed DOCX package validation before python-docx traversal."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePosixPath
from xml.parsers import expat
from zipfile import BadZipFile, ZipFile

from lxml import etree  # pyright: ignore[reportAttributeAccessIssue]

from msgloom.preparation import ParserLimits

_XML_SUFFIXES = (".xml", ".rels")
_MACRO_MARKERS = (b"macroenabled", b"vbaproject")
_FEATURE_TAGS = {
    "txbxContent": "text-boxes",
    "ins": "revisions",
    "del": "revisions",
    "moveFrom": "revisions",
    "moveTo": "revisions",
    "commentReference": "comments",
    "footnoteReference": "footnotes",
    "endnoteReference": "footnotes",
    "object": "embedded-objects",
    "OLEObject": "embedded-objects",
    "drawing": "images",
    "pict": "images",
}
_FEATURE_MEMBERS = {
    "word/comments.xml": "comments",
    "word/footnotes.xml": "footnotes",
    "word/endnotes.xml": "footnotes",
}
_REQUIRED_MEMBERS = {
    "[Content_Types].xml",
    "_rels/.rels",
    "word/document.xml",
}
_SUPPORTED_RELATIONSHIPS = {
    "core-properties",
    "custom-properties",
    "extended-properties",
    "fontTable",
    "footer",
    "header",
    "hyperlink",
    "numbering",
    "officeDocument",
    "settings",
    "styles",
    "theme",
    "webSettings",
}
_RELATIONSHIP_FEATURES = {
    "comments": "comments",
    "endnotes": "footnotes",
    "footnotes": "footnotes",
    "image": "images",
    "oleObject": "embedded-objects",
}


@dataclass(frozen=True, slots=True)
class PackageScan:
    """Bounded package inventory used to disclose unsupported Word features."""

    features: tuple[str, ...]


def _reject_dtd(payload: bytes) -> None:
    """Reject DTD markup using Expat's encoding-aware XML tokenizer."""
    parser = expat.ParserCreate()

    def reject(*_args: object) -> None:
        raise ValueError("DOCX XML must not contain a DTD or entity declaration")

    parser.StartDoctypeDeclHandler = reject
    parser.EntityDeclHandler = reject
    parser.ExternalEntityRefHandler = lambda *_args: 0
    try:
        parser.Parse(payload, True)
    except expat.ExpatError:
        # lxml below remains authoritative for ordinary XML well-formedness.
        pass


def _safe_member_name(name: str) -> bool:
    path = PurePosixPath(name)
    return (
        bool(name)
        and not path.is_absolute()
        and ".." not in path.parts
        and "\\" not in name
    )


def _scan_xml(payload: bytes, features: set[str]) -> None:
    _reject_dtd(payload)
    parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        huge_tree=False,
        recover=False,
    )
    try:
        root = etree.fromstring(payload, parser=parser)
    except etree.XMLSyntaxError as exc:
        raise ValueError("malformed DOCX XML member") from exc
    if root.getroottree().docinfo.doctype:
        raise ValueError("DOCX XML must not contain a DTD or entity declaration")
    for element in root.iter():
        if not isinstance(element.tag, str):
            continue
        local_name = etree.QName(element).localname
        feature = _FEATURE_TAGS.get(local_name)
        if feature is not None:
            features.add(feature)
        if local_name != "Relationship":
            continue
        rel_type = element.get("Type", "").rsplit("/", 1)[-1]
        rel_feature = _RELATIONSHIP_FEATURES.get(rel_type)
        if rel_feature is not None:
            features.add(rel_feature)
        elif rel_type not in _SUPPORTED_RELATIONSHIPS:
            features.add("unsupported-relationships")
        if element.get("TargetMode") == "External" and rel_type != "hyperlink":
            features.add("unsupported-relationships")


def validate_docx_package(content: bytes, limits: ParserLimits) -> PackageScan:
    """Validate finite ZIP/XML structure without resolving external resources."""
    if not content.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        raise ValueError("content does not match a DOCX ZIP container")

    features: set[str] = set()
    try:
        with ZipFile(BytesIO(content)) as archive:
            infos = archive.infolist()
            if len(infos) > limits.container_members:
                raise ValueError("DOCX container member limit exceeded")
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                raise ValueError("DOCX ZIP contains duplicate member names")
            if any(not _safe_member_name(name) for name in names):
                raise ValueError("DOCX ZIP contains an unsafe member path")
            if any(info.flag_bits & 0x1 for info in infos):
                raise ValueError("encrypted DOCX ZIP members are unsupported")
            total = sum(info.file_size for info in infos)
            if total > limits.decompressed_bytes:
                raise ValueError("DOCX decompressed byte limit exceeded")
            missing = sorted(_REQUIRED_MEMBERS.difference(names))
            if missing:
                raise ValueError(
                    "DOCX container is missing required members: " + ", ".join(missing)
                )
            lowered_names = tuple(name.lower() for name in names)
            if any("vbaproject" in name for name in lowered_names):
                raise ValueError("DOCX macro content is not permitted")

            for info in infos:
                name = info.filename
                payload = archive.read(info)
                lower_payload = payload.lower()
                if name == "[Content_Types].xml" and any(
                    marker in lower_payload for marker in _MACRO_MARKERS
                ):
                    raise ValueError("DOCX macro-enabled content is not permitted")
                feature = _FEATURE_MEMBERS.get(name)
                if feature is not None:
                    features.add(feature)
                if name.startswith("word/embeddings/"):
                    features.add("embedded-objects")
                if name.startswith("word/media/"):
                    features.add("images")
                if name.lower().endswith(_XML_SUFFIXES):
                    _scan_xml(payload, features)
    except BadZipFile as exc:
        raise ValueError("content does not match a valid DOCX ZIP container") from exc

    return PackageScan(features=tuple(sorted(features)))
