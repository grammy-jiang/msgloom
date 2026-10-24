"""
Result vocabulary for the DOCX parser (P2-04).

This module holds the closed enums and the frozen block records. The
parser module re-exports them, so ``msgloom.a2_kedro.parsers.docx`` stays
the public import path. See that module for the status rules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

from msgloom.a2_kedro.contracts.codec import A2ContractError

__all__ = [
    "Block",
    "DocxInputError",
    "DocxLimit",
    "UnsupportedItem",
    "UnsupportedKind",
]


class DocxInputError(A2ContractError):
    """Raised for caller misuse. The message is fixed and has no content."""


#: Closed, content-free reasons that a result is not complete. Each value
#: is the lower-case member name. The first nine members fail the parse.
DocxLimit = StrEnum(
    "DocxLimit",
    "EMPTY_INPUT NOT_A_ZIP ENCRYPTED_OR_OLE ENCRYPTED_MEMBER CORRUPT_PACKAGE "
    "DUPLICATE_MEMBER NOT_DOCX XML_FORBIDDEN INVALID_XML SIZE_LIMIT MEMBER_LIMIT "
    "MEMBER_SIZE_LIMIT TOTAL_SIZE_LIMIT XML_LIMIT PARAGRAPH_LIMIT TEXT_LIMIT "
    "TABLE_DEPTH_LIMIT MALFORMED_TABLE EMPTY_DOCUMENT UNSUPPORTED_CONTENT "
    "UNSUPPORTED_OVERFLOW",
)
#: Closed kinds of content that the parser skips (lower-case values).
UnsupportedKind = StrEnum(
    "UnsupportedKind",
    "IMAGE CHART DIAGRAM TEXTBOX DRAWING OLE_OBJECT FORM_CONTROL MACRO "
    "EQUATION COMMENT HEADER FOOTER FOOTNOTE ENDNOTE ALT_CHUNK "
    "TRACKED_DELETION UNKNOWN_BLOCK",
)


@dataclass(frozen=True, slots=True)
class Block:
    """One paragraph or table cell. ``repr`` hides the text."""

    source_block_id: str
    kind: Literal["paragraph", "table_cell"]
    body_index: int
    text: str = field(repr=False)
    row: int | None = None
    col: int | None = None


@dataclass(frozen=True, slots=True)
class UnsupportedItem:
    """Skipped content. ``source_block_id`` is ``None`` for package members."""

    kind: UnsupportedKind
    source_block_id: str | None = None
