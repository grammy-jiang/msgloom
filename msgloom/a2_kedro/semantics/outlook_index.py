"""
Outlook ``conversationIndex`` header decoding (P3-04 helper).

MS-OXOMSG gives the 22-byte header this layout: one reserved byte that MUST
be ``0x01``, a 5-byte time stamp and a 16-byte GUID. Child blocks of 5 bytes
may follow. Only the header is used. A header that breaks this layout is
unusable: it never groups messages. Pure and deterministic.

CANDIDATE/RESEARCH, PROVISIONAL.
"""

from __future__ import annotations

import base64
import binascii

#: Outlook conversation header length in bytes.
INDEX_HEADER_BYTES = 22
#: Value of the reserved first header byte.
INDEX_RESERVED_BYTE = 0x01
#: The GUID is the last 16 bytes of the header.
_GUID_START = INDEX_HEADER_BYTES - 16


def index_header(text: str) -> str | None:
    """Return the hex conversation header, or None if it is unusable."""
    try:
        raw = base64.b64decode(text, validate=True)
    except (binascii.Error, ValueError):
        return None
    if len(raw) < INDEX_HEADER_BYTES or raw[0] != INDEX_RESERVED_BYTE:
        return None
    header = raw[:INDEX_HEADER_BYTES]
    if not any(header[_GUID_START:]):
        return None
    return header.hex()
