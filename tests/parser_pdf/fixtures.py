"""Synthetic PDF byte builders for the PDF parser lane."""

from __future__ import annotations


def _object(number: int, body: bytes) -> tuple[int, bytes]:
    return number, f"{number} 0 obj\n".encode() + body + b"\nendobj\n"


def _serialize(objects: list[tuple[int, bytes]], trailer_extra: bytes = b"") -> bytes:
    output = bytearray(b"%PDF-1.7\n")
    offsets = [0]
    for number, obj in objects:
        if number != len(offsets):
            raise RuntimeError("synthetic PDF objects must be sequential")
        offsets.append(len(output))
        output.extend(obj)
    xref = len(output)
    output.extend(f"xref\n0 {len(offsets)}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        b"trailer\n<< /Size "
        + str(len(offsets)).encode()
        + b" /Root 1 0 R "
        + trailer_extra
        + b">>\nstartxref\n"
        + str(xref).encode()
        + b"\n%%EOF\n"
    )
    return bytes(output)


def build_text_pdf(text: bytes) -> bytes:
    """Build a one-page PDF using a standard Type1 font."""
    stream = b"BT /F1 12 Tf 72 720 Td (" + text + b") Tj ET"
    return _serialize(
        [
            _object(1, b"<< /Type /Catalog /Pages 2 0 R >>"),
            _object(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"),
            _object(
                3,
                b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
            ),
            _object(4, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"),
            _object(
                5,
                f"<< /Length {len(stream)} >>\nstream\n".encode()
                + stream
                + b"\nendstream",
            ),
        ]
    )


def build_unicode_pdf() -> bytes:
    """Build a PDF whose ToUnicode map includes BMP and astral text."""
    cmap = b"""begincmap
/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def
/CMapName /Synthetic def
/CMapType 2 def
1 begincodespacerange
<0000> <FFFF>
endcodespacerange
5 beginbfchar
<0001> <0041>
<0002> <00E9>
<0003> <03A9>
<0004> <6F22>
<0005> <D83DDE00>
endbfchar
endcmap"""
    stream = b"BT /F1 12 Tf 72 720 Td <00010002000300040005> Tj ET"
    return _serialize(
        [
            _object(1, b"<< /Type /Catalog /Pages 2 0 R >>"),
            _object(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"),
            _object(
                3,
                b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 8 0 R >>",
            ),
            _object(
                4,
                b"<< /Type /Font /Subtype /Type0 /BaseFont /Synthetic /Encoding /Identity-H /DescendantFonts [5 0 R] /ToUnicode 7 0 R >>",
            ),
            _object(
                5,
                b"<< /Type /Font /Subtype /CIDFontType2 /BaseFont /Synthetic /CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> /FontDescriptor 6 0 R /CIDToGIDMap /Identity >>",
            ),
            _object(
                6,
                b"<< /Type /FontDescriptor /FontName /Synthetic /Flags 4 /FontBBox [0 0 1000 1000] /ItalicAngle 0 /Ascent 800 /Descent -200 /CapHeight 700 /StemV 80 >>",
            ),
            _object(
                7,
                f"<< /Length {len(cmap)} >>\nstream\n".encode() + cmap + b"\nendstream",
            ),
            _object(
                8,
                f"<< /Length {len(stream)} >>\nstream\n".encode()
                + stream
                + b"\nendstream",
            ),
        ]
    )


def build_mixed_pdf() -> bytes:
    """Build one page containing both extractable text and an image."""
    text = b"BT /F1 12 Tf 72 720 Td (Mixed page) Tj ET"
    draw = b"q 100 0 0 100 72 500 cm /Im0 Do Q"
    return _serialize(
        [
            _object(1, b"<< /Type /Catalog /Pages 2 0 R >>"),
            _object(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"),
            _object(
                3,
                b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> /XObject << /Im0 6 0 R >> >> /Contents [5 0 R 7 0 R] >>",
            ),
            _object(4, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"),
            _object(
                5,
                f"<< /Length {len(text)} >>\nstream\n".encode() + text + b"\nendstream",
            ),
            _object(
                6,
                b"<< /Type /XObject /Subtype /Image /Width 1 /Height 1 /ColorSpace /DeviceGray /BitsPerComponent 8 /Length 1 >>\nstream\nX\nendstream",
            ),
            _object(
                7,
                f"<< /Length {len(draw)} >>\nstream\n".encode() + draw + b"\nendstream",
            ),
        ]
    )


def build_empty_page_pdf() -> bytes:
    """Build a valid one-page PDF with no content objects."""
    return _serialize(
        [
            _object(1, b"<< /Type /Catalog /Pages 2 0 R >>"),
            _object(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"),
            _object(3, b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>"),
        ]
    )


def build_encrypted_pdf() -> bytes:
    """Build a Standard Security Handler document requiring a key."""
    encryption = (
        b"<< /Filter /Standard /V 1 /R 2 /O <"
        + b"00" * 32
        + b"> /U <"
        + b"11" * 32
        + b"> /P -4 >>"
    )
    file_id = b"22" * 16
    return _serialize(
        [
            _object(1, b"<< /Type /Catalog /Pages 2 0 R >>"),
            _object(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"),
            _object(3, b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>"),
            _object(4, encryption),
        ],
        b"/Encrypt 4 0 R /ID [<" + file_id + b"> <" + file_id + b">] ",
    )
