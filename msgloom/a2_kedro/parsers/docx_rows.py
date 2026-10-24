"""
XML name and table-row helpers for the DOCX parser (P2-04).

These helpers hold no parser state. They answer structural questions about
one element: its prefixed name, whether it is a harmless marker, whether a
table row or cell is a tracked deletion, and how many grid columns a cell
spans. :mod:`msgloom.a2_kedro.parsers.docx` records the outcome.
"""

from __future__ import annotations

from functools import lru_cache
from xml.etree.ElementTree import Element

MAX_GRID_SPAN = 1000

NS = {
    "http://schemas.openxmlformats.org/wordprocessingml/2006/main": "w",
    "http://purl.oclc.org/ooxml/wordprocessingml/main": "w",
    "http://schemas.openxmlformats.org/officeDocument/2006/math": "m",
    "http://schemas.openxmlformats.org/markup-compatibility/2006": "mc",
}
#: Block-level elements that hold no content. Skipping them is not a loss.
MARKERS = frozenset(
    "w:sectPr w:bookmarkStart w:bookmarkEnd w:proofErr w:permStart w:permEnd "  # noqa: SIM905
    "w:tblPr w:tblGrid w:trPr w:tcPr w:tblPrEx w:sdtEndPr w:sdtPr".split()
)


@lru_cache(maxsize=4096)
def qname(tag: str) -> str:
    """Return ``prefix:local``; unknown namespaces use the prefix ``x``."""
    uri, _, local = tag[1:].partition("}") if tag.startswith("{") else ("", "", tag)
    return f"{NS.get(uri, 'x')}:{local}"


def is_marker(name: str) -> bool:
    """Return ``True`` for a name that holds no content."""
    return name in MARKERS or name.endswith(("RangeStart", "RangeEnd"))


def _has_child(parent: Element, props: str, mark: str) -> bool:
    return any(qname(m.tag) == mark for p in parent if qname(p.tag) == props for m in p)


def row_deleted(row: Element) -> bool:
    """Return ``True`` if ``w:trPr`` marks the row as a tracked deletion."""
    return _has_child(row, "w:trPr", "w:del")


def cell_deleted(cell: Element) -> bool:
    """Return ``True`` if ``w:tcPr`` marks the cell as a tracked deletion."""
    return _has_child(cell, "w:tcPr", "w:cellDel")


def grid_span(cell: Element) -> tuple[int, bool]:
    """Return ``(columns, malformed)``. A bad span counts as one column."""
    malformed = False
    for props in (p for p in cell if qname(p.tag) == "w:tcPr"):
        for item in (i for i in props if qname(i.tag) == "w:gridSpan"):
            raw = item.get(item.tag.partition("}")[0] + "}val", "")
            if raw.isascii() and raw.isdigit() and 1 <= int(raw) <= MAX_GRID_SPAN:
                return int(raw), malformed
            malformed = True
    return 1, malformed
