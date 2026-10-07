"""Small synthetic parser acceptance fixtures with no third-party dependency."""

from __future__ import annotations

from email.message import EmailMessage
from io import BytesIO
from typing import cast
from zipfile import ZIP_DEFLATED, ZipFile

HTML_BODY = """\
<html><body>
<p>Alpha <a href="https://example.invalid/reference">reference</a> omega.</p>
<table><tr><th>Item</th><th>Value</th></tr>
<tr><td>First</td><td>7</td></tr></table>
<p>Tail.</p>
</body></html>
"""


def build_mime_fixture() -> bytes:
    """Return MIME bytes with explicit encodings, HTML, and an attachment."""
    message = EmailMessage()
    message["From"] = "sender@example.invalid"
    message["To"] = "owner@example.invalid"
    message["Subject"] = "Synthetic parser fixture"
    message.set_content("Plain café body.", charset="utf-8", cte="quoted-printable")
    message.add_alternative(
        HTML_BODY,
        subtype="html",
        charset="utf-8",
        cte="quoted-printable",
    )
    alternatives = cast(list[EmailMessage], message.get_payload())
    if not alternatives:
        raise RuntimeError("synthetic MIME alternative payload is empty")
    alternatives[0].set_boundary("msgloom-alternative")
    message.set_boundary("msgloom-mixed")
    message.add_attachment(
        b"synthetic attachment bytes",
        maintype="application",
        subtype="octet-stream",
        filename="fixture.bin",
        cte="base64",
    )
    return message.as_bytes()


def _xlsx_parts() -> dict[str, bytes]:
    content_types = """\
<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>"""
    root_rels = """\
<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""
    workbook = """\
<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets>
<sheet name="Visible" sheetId="1" r:id="rId1"/>
<sheet name="Hidden" sheetId="2" state="hidden" r:id="rId2"/>
</sheets>
</workbook>"""
    workbook_rels = """\
<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""
    styles = """\
<?xml version="1.0" encoding="UTF-8"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>
<fills count="1"><fill><patternFill patternType="none"/></fill></fills>
<borders count="1"><border/></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="2">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="14" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
</cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""
    sheet1 = """\
<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<dimension ref="B3:E5"/>
<sheetData>
<row r="3">
<c r="B3" t="n"><v>1</v></c>
<c r="C3" t="inlineStr"><is><t>alpha</t></is></c>
<c r="D3" t="b"><v>1</v></c>
</row>
<row r="4">
<c r="B4" s="1" t="n"><v>45567</v></c>
<c r="C4"><f>SUM(B3,2)</f><v>3</v></c>
</row>
<row r="5"><c r="B5" t="inlineStr"><is><t>tail</t></is></c></row>
</sheetData>
<mergeCells count="1"><mergeCell ref="D3:E3"/></mergeCells>
</worksheet>"""
    sheet2 = """\
<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>hidden value</t></is></c></row></sheetData>
</worksheet>"""
    return {
        "[Content_Types].xml": content_types.encode(),
        "_rels/.rels": root_rels.encode(),
        "xl/workbook.xml": workbook.encode(),
        "xl/_rels/workbook.xml.rels": workbook_rels.encode(),
        "xl/styles.xml": styles.encode(),
        "xl/worksheets/sheet1.xml": sheet1.encode(),
        "xl/worksheets/sheet2.xml": sheet2.encode(),
    }


def build_xlsx_fixture() -> bytes:
    """Return an XLSX with leading blanks, types, formula, merge, and hidden sheet."""
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for name, content in _xlsx_parts().items():
            archive.writestr(name, content)
    return buffer.getvalue()


def _pdf_object(number: int, body: bytes) -> tuple[int, bytes]:
    return number, f"{number} 0 obj\n".encode() + body + b"\nendobj\n"


def build_pdf_fixture() -> bytes:
    """Return a two-page PDF with text on page one and image-only page two."""
    text_stream = b"BT /F1 12 Tf 72 720 Td (First line) Tj 0 -20 Td (Second line) Tj ET"
    image_stream = b"\x80"
    image_draw = b"q 100 0 0 100 72 600 cm /Im0 Do Q"
    objects = [
        _pdf_object(1, b"<< /Type /Catalog /Pages 2 0 R >>"),
        _pdf_object(2, b"<< /Type /Pages /Kids [3 0 R 6 0 R] /Count 2 >>"),
        _pdf_object(
            3,
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        ),
        _pdf_object(4, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"),
        _pdf_object(
            5,
            f"<< /Length {len(text_stream)} >>\nstream\n".encode()
            + text_stream
            + b"\nendstream",
        ),
        _pdf_object(
            6,
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /XObject << /Im0 7 0 R >> >> /Contents 8 0 R >>",
        ),
        _pdf_object(
            7,
            b"<< /Type /XObject /Subtype /Image /Width 1 /Height 1 "
            b"/ColorSpace /DeviceGray /BitsPerComponent 8 /Length 1 >>\nstream\n"
            + image_stream
            + b"\nendstream",
        ),
        _pdf_object(
            8,
            f"<< /Length {len(image_draw)} >>\nstream\n".encode()
            + image_draw
            + b"\nendstream",
        ),
    ]
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in objects:
        if number != len(offsets):
            raise RuntimeError("PDF fixture objects must be sequential")
        offsets.append(len(output))
        output.extend(obj)
    xref = len(output)
    output.extend(f"xref\n0 {len(offsets)}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        (
            f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n"
        ).encode()
    )
    return bytes(output)


def _docx_parts() -> dict[str, bytes]:
    content_types = """\
<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Default Extension="bin" ContentType="application/vnd.openxmlformats-officedocument.oleObject"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""
    root_rels = """\
<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""
    document = """\
<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:o="urn:schemas-microsoft-com:office:office">
<w:body>
<w:p><w:r><w:t>Before table</w:t></w:r></w:p>
<w:tbl>
<w:tr><w:tc><w:p><w:r><w:t>A1</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>B1</w:t></w:r></w:p></w:tc></w:tr>
<w:tr><w:tc><w:p><w:r><w:t>A2</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>B2</w:t></w:r></w:p></w:tc></w:tr>
</w:tbl>
<w:p><w:r><w:t>After table</w:t></w:r></w:p>
<w:p><w:r><w:object><o:OLEObject Type="Embed" ProgID="Synthetic.Object" r:id="rId2"/></w:object></w:r></w:p>
<w:sectPr/>
</w:body>
</w:document>"""
    document_rels = """\
<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/oleObject" Target="embeddings/oleObject1.bin"/>
</Relationships>"""
    return {
        "[Content_Types].xml": content_types.encode(),
        "_rels/.rels": root_rels.encode(),
        "word/document.xml": document.encode(),
        "word/_rels/document.xml.rels": document_rels.encode(),
        "word/embeddings/oleObject1.bin": b"synthetic embedded object",
    }


def build_docx_fixture() -> bytes:
    """Return DOCX bytes with paragraph/table order and an embedded object."""
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for name, content in _docx_parts().items():
            archive.writestr(name, content)
    return buffer.getvalue()
