"""
Hand-built synthetic inputs for the V0-04 acceptance test.

Every builder here writes literal bytes. None of them calls a parser or
reads an implementation result. All data is synthetic and uses reserved
example domains. The helpers need no network and no file outside the
``tmp_path`` that the caller supplies (none is needed here).
"""

from __future__ import annotations

import hashlib
import io
import struct
import zipfile
from collections.abc import Mapping, Sequence
from typing import Final

#: Marker for a PDF page that holds only an image (a scanned page).
IMAGE: Final = object()
_PAD = bytes.fromhex("28BF4E5E4E758A4164004E56FFFA01082E2E00B6D0683E802F0CA9FE6453697A")
_OWNER = b"O" * 32
_FILE_ID = b"0123456789abcdef"
CRLF = "\r\n"


# --- MIME ---------------------------------------------------------------


def _children(nodes: Mapping[str, Mapping[str, object]], ref: str) -> list[str]:
    depth = ref.count(".") + 1
    return [r for r in nodes if r.startswith(ref + ".") and r.count(".") == depth]


def _leaf_headers(node: Mapping[str, object]) -> list[str]:
    kind = str(node["type"])
    charset = node.get("charset")
    lines = [f"Content-Type: {kind}" + (f"; charset={charset}" if charset else "")]
    if node.get("transfer_encoding"):
        lines.append(f"Content-Transfer-Encoding: {node['transfer_encoding']}")
    if node.get("disposition"):
        name = node.get("filename")
        extra = f'; filename="{name}"' if name else ""
        lines.append(f"Content-Disposition: {node['disposition']}{extra}")
    return lines


def _render(nodes: Mapping[str, Mapping[str, object]], ref: str) -> str:
    node = nodes[ref]
    kind = str(node["type"])
    kids = _children(nodes, ref)
    if kind.startswith("multipart/"):
        boundary = "BND" + ref.replace(".", "x")
        head = [f'Content-Type: {kind}; boundary="{boundary}"']
        body = "".join(f"--{boundary}{CRLF}{_render(nodes, kid)}{CRLF}" for kid in kids)
        return CRLF.join(head) + CRLF * 2 + body + f"--{boundary}--{CRLF}"
    head = _leaf_headers(node)
    if kind == "message/rfc822":
        body = _render(nodes, kids[0]) if kids else ""
    elif "raw" in node or "text" in node:
        body = str(node.get("raw", node.get("text", "")))
    else:
        # A binary attachment stub. The bytes are a fixed ASCII marker.
        head.append("Content-Transfer-Encoding: base64")
        body = "JVBERi0xLjQgc3R1Yg=="
    return CRLF.join(head) + CRLF * 2 + body


def build_mime(
    parts: Sequence[Mapping[str, object]], message_id: str, sender: str
) -> bytes:
    """
    Render the gold ``parts`` list (ref, type, text or raw) as one message.

    Refs form the tree: ``1.2`` is the second child of ``1``. A multipart
    node gets a boundary from its ref. ``message/rfc822`` holds its first
    child as the inner message. A node with no text is a binary stub.
    """
    nodes = {str(p["ref"]): p for p in parts}
    top = [f"Message-ID: {message_id}", f"From: {sender}", "MIME-Version: 1.0"]
    return (CRLF.join(top) + CRLF + _render(nodes, "1")).encode("ascii")


def plain_message(text: str, message_id: str, charset: str = "utf-8") -> bytes:
    """Return a single-part text/plain message with a UTF-8 body."""
    head = [
        f"Message-ID: {message_id}",
        "MIME-Version: 1.0",
        f"Content-Type: text/plain; charset={charset}",
        "Content-Transfer-Encoding: 8bit",
    ]
    return (CRLF.join(head) + CRLF * 2 + text).encode("utf-8")


# --- PDF ----------------------------------------------------------------


def _rc4(key: bytes, data: bytes) -> bytes:
    state = list(range(256))
    j = 0
    for i in range(256):
        j = (j + state[i] + key[i % len(key)]) % 256
        state[i], state[j] = state[j], state[i]
    out = bytearray()
    i = j = 0
    for byte in data:
        i = (i + 1) % 256
        j = (j + state[i]) % 256
        state[i], state[j] = state[j], state[i]
        out.append(byte ^ state[(state[i] + state[j]) % 256])
    return bytes(out)


def _page_stream(page: object) -> bytes:
    if page is IMAGE:
        return b"q 100 0 0 100 10 10 cm BI /W 1 /H 1 /CS /G /BPC 8 ID \x80 EI Q"
    if isinstance(page, bytes) and page:
        return b"BT /F1 12 Tf 20 100 Td (" + page + b") Tj ET"
    return b""


def build_pdf(
    pages: Sequence[object], *, password: bytes | None = None, trailer: bool = True
) -> tuple[bytes, int]:
    """
    Build a tiny PDF 1.4 file. A page is text bytes or ``IMAGE``.

    ``password`` encrypts with RC4 40-bit (revision 2) and that user
    password. Return the bytes and the offset of the ``xref`` keyword, so
    that a test can cut the file inside the cross-reference table.
    """
    key = b""
    if password is not None:
        seed = (password + _PAD)[:32] + _OWNER + struct.pack("<i", -4) + _FILE_ID
        key = hashlib.md5(seed).digest()[:5]
    kids = b" ".join(b"%d 0 R" % (4 + 2 * i) for i in range(len(pages)))
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [" + kids + b"] /Count %d >>" % len(pages),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    for i, page in enumerate(pages):
        num = 5 + 2 * i
        objs.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] "
            b"/Contents %d 0 R /Resources << /Font << /F1 3 0 R >> >> >>" % num
        )
        body = _page_stream(page)
        if password is not None:
            seed_key = key + struct.pack("<I", num)[:3] + b"\0\0"
            body = _rc4(hashlib.md5(seed_key).digest()[:10], body)
        objs.append(b"<< /Length %d >>\nstream\n" % len(body) + body + b"\nendstream")
    extra = b""
    if password is not None:
        objs.append(
            b"<< /Filter /Standard /V 1 /R 2 /P -4 /O <"
            + _OWNER.hex().encode()
            + b"> /U <"
            + _rc4(key, _PAD).hex().encode()
            + b"> >>"
        )
        fid = _FILE_ID.hex().encode()
        extra = b" /Encrypt %d 0 R /ID [<%s> <%s>]" % (len(objs), fid, fid)
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, obj in enumerate(objs, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + obj + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R%s >>\n" % (len(objs) + 1, extra)
    if trailer:
        out += b"startxref\n%d\n%%%%EOF\n" % xref
    return bytes(out), xref


# --- DOCX ---------------------------------------------------------------

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_OLE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/oleObject"


def docx_paragraph(text: str, style: str | None = None) -> str:
    """Return one ``w:p`` with one run, optionally with a style name."""
    props = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f"<w:p>{props}<w:r><w:t>{text}</w:t></w:r></w:p>"


def build_docx(body: str, extra: Mapping[str, bytes] | None = None) -> bytes:
    """Zip a minimal Word package around the ``w:body`` XML in ``body``."""
    document = (
        f'<?xml version="1.0"?><w:document xmlns:w="{_W}"><w:body>{body}'
        "</w:body></w:document>"
    )
    types = (
        '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/'
        'package/2006/content-types"><Default Extension="xml" ContentType='
        '"application/xml"/></Types>'
    )
    rels = (
        f'<?xml version="1.0"?><Relationships xmlns="{_REL}"><Relationship '
        'Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
        'relationships/officeDocument" Target="word/document.xml"/>'
        "</Relationships>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("word/document.xml", document)
        for name, data in (extra or {}).items():
            archive.writestr(name, data)
    return buffer.getvalue()


def ole_relationships() -> bytes:
    """Return a document relationships part that names one OLE object."""
    return (
        f'<?xml version="1.0"?><Relationships xmlns="{_REL}"><Relationship '
        f'Id="rId9" Type="{_OLE}" Target="embeddings/oleObject1.bin"/>'
        "</Relationships>"
    ).encode()


def damaged_central_directory(data: bytes) -> bytes:
    """Keep the ZIP signature and local data, but cut the central directory."""
    cut = data.rfind(b"PK\x01\x02")
    return data[: cut + 10]


# --- XLSX ---------------------------------------------------------------

_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_OFFDOC = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_SHEET_CT = "application/vnd.openxmlformats-officedocument.spreadsheetml"


def _cell_xml(ref: str, value: str | int) -> str:
    if isinstance(value, int):
        return f'<c r="{ref}"><v>{value}</v></c>'
    return f'<c r="{ref}" t="inlineStr"><is><t>{value}</t></is></c>'


def build_xlsx(
    rows: Sequence[Mapping[str, str | int]],
    *,
    extra: Mapping[str, bytes] | None = None,
    chart_sheet: bool = False,
) -> bytes:
    """
    Zip a minimal one-worksheet workbook. ``rows[i]`` maps A1 refs to values.

    ``chart_sheet`` adds a second sheet that is a chart sheet with a chart.
    ``extra`` adds raw package members.
    """
    data = "".join(
        f'<row r="{i}">' + "".join(_cell_xml(r, v) for r, v in row.items()) + "</row>"
        for i, row in enumerate(rows, start=1)
    )
    sheet = f'<?xml version="1.0"?><worksheet xmlns="{_MAIN}"><sheetData>{data}</sheetData></worksheet>'
    sheets = '<sheet name="Sheet1" sheetId="1" r:id="rId1"/>'
    wb_rels = f'<Relationship Id="rId1" Type="{_OFFDOC}/worksheet" Target="worksheets/sheet1.xml"/>'
    over = f'<Override PartName="/xl/worksheets/sheet1.xml" ContentType="{_SHEET_CT}.worksheet+xml"/>'
    members: dict[str, bytes] = {}
    if chart_sheet:
        sheets += '<sheet name="Chart1" sheetId="2" r:id="rId2"/>'
        wb_rels += f'<Relationship Id="rId2" Type="{_OFFDOC}/chartsheet" Target="chartsheets/sheet1.xml"/>'
        over += f'<Override PartName="/xl/chartsheets/sheet1.xml" ContentType="{_SHEET_CT}.chartsheet+xml"/>'
        over += '<Override PartName="/xl/charts/chart1.xml" ContentType="application/vnd.openxmlformats-officedocument.drawingml.chart+xml"/>'
        members["xl/chartsheets/sheet1.xml"] = (
            f'<?xml version="1.0"?><chartsheet xmlns="{_MAIN}" xmlns:r="{_OFFDOC}">'
            '<drawing r:id="rId1"/></chartsheet>'
        ).encode()
        members["xl/charts/chart1.xml"] = (
            b'<?xml version="1.0"?><c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart"/>'
        )
        members["xl/chartsheets/_rels/sheet1.xml.rels"] = (
            f'<?xml version="1.0"?><Relationships xmlns="{_REL}"><Relationship Id="rId1" '
            f'Type="{_OFFDOC}/chart" Target="../charts/chart1.xml"/></Relationships>'
        ).encode()
    members["[Content_Types].xml"] = (
        '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        f'<Override PartName="/xl/workbook.xml" ContentType="{_SHEET_CT}.sheet.main+xml"/>{over}</Types>'
    ).encode()
    members["_rels/.rels"] = (
        f'<?xml version="1.0"?><Relationships xmlns="{_REL}"><Relationship Id="rId1" '
        f'Type="{_OFFDOC}/officeDocument" Target="xl/workbook.xml"/></Relationships>'
    ).encode()
    members["xl/workbook.xml"] = (
        f'<?xml version="1.0"?><workbook xmlns="{_MAIN}" xmlns:r="{_OFFDOC}">'
        f"<sheets>{sheets}</sheets></workbook>"
    ).encode()
    members["xl/_rels/workbook.xml.rels"] = (
        f'<?xml version="1.0"?><Relationships xmlns="{_REL}">{wb_rels}</Relationships>'
    ).encode()
    members["xl/worksheets/sheet1.xml"] = sheet.encode()
    members.update(extra or {})
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, body in members.items():
            archive.writestr(name, body)
    return buffer.getvalue()


def zip_with_large_member(size: int) -> bytes:
    """Return a small workbook that holds one member of ``size`` zero bytes."""
    return build_xlsx([{"A1": "x"}], extra={"xl/media/bomb.bin": bytes(size)})


# --- whole-file inputs for the t0_05 cases ------------------------------------

#: The OLE compound file signature that opens a Word 97 ``.doc`` file.
OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


def legacy_doc() -> bytes:
    """Return bytes that look like a binary Word 97 file (signature only)."""
    return OLE_MAGIC + bytes(600)


def notes_docx() -> bytes:
    """Return a Word file with a heading and two paragraphs."""
    body = docx_paragraph("Notes", "Heading1")
    return build_docx(
        body + docx_paragraph("First note.") + docx_paragraph("Second note.")
    )


def items_xlsx(chart: bool = False) -> bytes:
    """Return the Sheet1 workbook of ``T0-05-P03``, with a chart sheet if asked."""
    rows = [{"A1": "Item", "B1": "Count"}, {"A2": "Pens", "B2": 3}]
    return build_xlsx(rows, chart_sheet=chart)


def pdf_cut_in_xref() -> bytes:
    """Return a two-page PDF cut inside its cross-reference table."""
    data, xref = build_pdf([b"page one", b"page two"])
    return data[: xref + 8]


def docx_with_ole() -> bytes:
    """Return a Word file with body text and one embedded OLE object."""
    body = docx_paragraph("Body text.") + "<w:p><w:r><w:object/></w:r></w:p>"
    extra = {
        "word/_rels/document.xml.rels": ole_relationships(),
        "word/embeddings/oleObject1.bin": b"stub",
    }
    return build_docx(body, extra)


def pdf_5000_pages() -> bytes:
    """Return a PDF with 5000 short text pages (about 1.3 MB)."""
    return build_pdf([b"page %d" % i for i in range(5000)])[0]
