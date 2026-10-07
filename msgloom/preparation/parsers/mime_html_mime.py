"""Standard-library MIME extraction with stable local part references."""

from __future__ import annotations

from email import policy
from email.message import Message
from email.parser import BytesParser

from msgloom.preparation.contracts import (
    BlockRole,
    LimitationKind,
    MimePartLocation,
    MimePartReference,
)
from msgloom.preparation.parsers.mime_html_html import extract_html
from msgloom.preparation.parsers.mime_html_limits import ExtractionState


def _record_defects(
    state: ExtractionState,
    part: Message,
    location: MimePartLocation,
    *,
    decoding: bool,
) -> None:
    """Expose MIME defects without copying source or defect text."""
    if not part.defects:
        return
    state.add_limitation(
        LimitationKind.PARTIAL,
        "mime-decoding-defect" if decoding else "mime-parser-defect",
        "The MIME parser reported malformed transfer or structural data.",
        feature="transfer-decoding" if decoding else "mime-structure",
        location=location,
    )


def _decode_text(
    state: ExtractionState,
    part: Message,
    location: MimePartLocation,
) -> str | None:
    """Decode one readable MIME leaf strictly within decoded-byte limits."""
    try:
        payload = part.get_payload(decode=True)
    except (LookupError, TypeError, ValueError):
        state.add_limitation(
            LimitationKind.PARTIAL,
            "mime-transfer-decoding-failed",
            "A readable MIME part could not be transfer-decoded.",
            feature="transfer-decoding",
            location=location,
        )
        return None
    _record_defects(state, part, location, decoding=True)
    if payload is not None and not isinstance(payload, bytes):
        state.add_limitation(
            LimitationKind.PARTIAL,
            "mime-readable-payload-invalid",
            "A readable MIME part did not expose a byte payload.",
            feature="mime-text",
            location=location,
        )
        return None

    if payload is None:
        raw_payload = part.get_payload()
        if not isinstance(raw_payload, str):
            state.add_limitation(
                LimitationKind.PARTIAL,
                "mime-readable-payload-missing",
                "A readable MIME part had no decodable text payload.",
                feature="mime-text",
                location=location,
            )
            return None
        payload = raw_payload.encode("ascii", errors="surrogateescape")

    if not state.consume_decoded(len(payload), location=location):
        return None
    charset = part.get_content_charset() or "ascii"
    try:
        return payload.decode(charset, errors="strict")
    except LookupError:
        state.add_limitation(
            LimitationKind.UNSUPPORTED,
            "mime-unsupported-charset",
            "A MIME text part declared an unsupported character set.",
            feature="charset",
            location=location,
        )
    except UnicodeDecodeError:
        state.add_limitation(
            LimitationKind.PARTIAL,
            "mime-invalid-charset-bytes",
            "A MIME text part contained bytes invalid for its character set.",
            feature="charset",
            location=location,
        )
    return None


def _part_reference(
    part: Message,
    part_ref: str,
    parent_ref: str | None,
) -> MimePartReference:
    """Build metadata for one MIME node without retaining body bytes."""
    location = MimePartLocation(part_ref=part_ref)
    return MimePartReference(
        part_ref=part_ref,
        parent_ref=parent_ref,
        content_type=part.get_content_type(),
        disposition=part.get_content_disposition(),
        content_id=part.get("Content-ID"),
        location=location,
    )


def _skip_nonbody_leaf(
    state: ExtractionState,
    part: Message,
    location: MimePartLocation,
) -> bool:
    """Record binary embedded parts as metadata-only."""
    if part.get_content_maintype() != "text":
        state.add_limitation(
            LimitationKind.UNSUPPORTED,
            "mime-embedded-content-skipped",
            "Embedded binary MIME content was not decoded as readable body text.",
            feature="embedded-content",
            location=location,
        )
        return True
    return False


def _visit_part(
    state: ExtractionState,
    part: Message,
    part_ref: str,
    parent_ref: str | None,
    *,
    body_allowed: bool = True,
) -> bool:
    """Visit one MIME node while attachment subtrees remain metadata-only."""
    location = MimePartLocation(part_ref=part_ref)
    if not state.consume_member(location=location):
        return False

    reference = _part_reference(part, part_ref, parent_ref)
    if not state.add_mime_part(reference):
        return False
    _record_defects(state, part, location, decoding=False)

    is_attachment = part.get_content_disposition() == "attachment"
    if is_attachment:
        state.add_limitation(
            LimitationKind.UNSUPPORTED,
            "mime-attachment-not-extracted",
            "Attachment structure was retained as MIME metadata but its "
            "readable content was not extracted here.",
            feature="attachment",
            location=location,
        )
        body_allowed = False

    if body_allowed and part.get_content_type() == "multipart/alternative":
        state.add_limitation(
            LimitationKind.PARTIAL,
            "mime-alternative-not-resolved",
            "MIME alternatives were extracted independently; equivalence was "
            "not inferred.",
            feature="multipart-alternative",
            location=location,
        )

    if part.is_multipart():
        payload = part.get_payload()
        if not isinstance(payload, list):
            state.add_limitation(
                LimitationKind.PARTIAL,
                "mime-multipart-payload-missing",
                "A multipart MIME node had no traversable child list.",
                feature="mime-structure",
                location=location,
            )
            return True
        for index, child in enumerate(payload, start=1):
            if not isinstance(child, Message):
                state.add_limitation(
                    LimitationKind.PARTIAL,
                    "mime-child-invalid",
                    "A MIME child could not be represented as a message part.",
                    feature="mime-structure",
                    location=location,
                )
                continue
            if not _visit_part(
                state,
                child,
                f"{part_ref}.{index}",
                part_ref,
                body_allowed=body_allowed,
            ):
                return False
        return True

    if not body_allowed:
        return True
    if _skip_nonbody_leaf(state, part, location):
        return True
    if part.get_content_type() not in {"text/plain", "text/html"}:
        state.add_limitation(
            LimitationKind.UNSUPPORTED,
            "mime-text-subtype-unsupported",
            "A text MIME subtype is not a readable body format in this parser.",
            feature="mime-text",
            location=location,
        )
        return True

    text = _decode_text(state, part, location)
    if text is None:
        return True
    if part.get_content_type() == "text/html":
        extract_html(text, state, part_name=f"mime:{part_ref}")
        return True
    if not text:
        state.add_limitation(
            LimitationKind.MISSING,
            "empty-content",
            "Readable MIME text content was empty.",
            feature="text",
            location=location,
        )
        return True
    state.add_text(BlockRole.TEXT, text, location)
    return True


def extract_mime(content: bytes, state: ExtractionState) -> None:
    """Parse MIME bytes into bounded metadata and readable body blocks."""
    try:
        message = BytesParser(policy=policy.default).parsebytes(content)
    except (TypeError, ValueError):
        state.add_limitation(
            LimitationKind.PARTIAL,
            "invalid-mime",
            "MIME bytes could not be parsed into a message structure.",
            feature="mime",
        )
        return
    _visit_part(state, message, "1", None)
