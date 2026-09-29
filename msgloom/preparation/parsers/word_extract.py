"""Structured DOCX extraction with explicit OOXML coverage gaps."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from docx.document import Document as DocumentObject
from docx.oxml.ns import qn
from docx.parts.hdrftr import FooterPart, HeaderPart
from docx.table import Table, _Cell  # pyright: ignore[reportPrivateUsage]
from docx.text.hyperlink import Hyperlink
from docx.text.paragraph import Paragraph

from msgloom.preparation import (
    BlockRole,
    DocumentLocation,
    LimitationKind,
    ParsedCell,
    ParsedLink,
    ParsedTable,
    ParserLimitation,
    TableBlock,
    TextBlock,
)
from msgloom.preparation.parsers.word_package import PackageScan

_FEATURE_DETAILS = {
    "comments": (
        LimitationKind.UNSUPPORTED,
        "Word comments are present but their content is not extracted.",
    ),
    "embedded-objects": (
        LimitationKind.UNSUPPORTED,
        "Embedded object payloads are not interpreted or executed.",
    ),
    "footnotes": (
        LimitationKind.UNSUPPORTED,
        "Footnotes or endnotes are present but are not extracted.",
    ),
    "images": (
        LimitationKind.PARTIAL,
        "Image payloads are not interpreted by the native Word text path.",
    ),
    "revisions": (
        LimitationKind.PARTIAL,
        "Tracked revisions are not resolved into an accepted document view.",
    ),
    "text-boxes": (
        LimitationKind.PARTIAL,
        "Text-box content is outside the supported block traversal.",
    ),
    "unsupported-relationships": (
        LimitationKind.UNSUPPORTED,
        (
            "One or more OOXML relationships are outside the supported native "
            "Word relationship set and are not resolved or fetched."
        ),
    ),
}


def _paragraph_links(
    paragraph: Paragraph, location: DocumentLocation
) -> tuple[ParsedLink, ...]:
    links: list[ParsedLink] = []
    for item in paragraph.iter_inner_content():
        if not isinstance(item, Hyperlink):
            continue
        target = item.url
        if not target:
            continue
        links.append(
            ParsedLink(
                target=target,
                text=item.text or None,
                location=location,
            )
        )
    return tuple(links)


def _paragraph_block(
    paragraph: Paragraph,
    *,
    order: int,
    part: str,
    block_index: int,
) -> TextBlock:
    location = DocumentLocation(part=part, block_index=block_index)
    role = BlockRole.PARAGRAPH
    try:
        style = paragraph.style
        style_name = (style.name or "") if style is not None else ""
    except KeyError:
        style_name = ""
    if style_name.lower().startswith("heading"):
        role = BlockRole.HEADING
    return TextBlock(
        order=order,
        role=role,
        text=paragraph.text,
        location=location,
        links=_paragraph_links(paragraph, location),
    )


def _grid_omission(tr: Any, name: str) -> int:
    tr_pr = tr.trPr
    if tr_pr is None:
        return 0
    element = tr_pr.find(qn(f"w:{name}"))
    if element is None:
        return 0
    raw = element.get(qn("w:val"))
    try:
        value = int(raw) if raw is not None else 0
    except ValueError as exc:
        raise ValueError("malformed Word table grid omission") from exc
    if value < 0:
        raise ValueError("malformed Word table grid omission")
    return value


def _row_grid_cells(tr: Any, column_count: int) -> list[tuple[int, int, Any]]:
    column = 1 + _grid_omission(tr, "gridBefore")
    cells: list[tuple[int, int, Any]] = []
    for tc in tr.tc_lst:
        span = int(tc.grid_span)
        if span < 1 or column + span - 1 > column_count:
            raise ValueError("malformed Word table grid/merge layout")
        cells.append((column, span, tc))
        column += span
    column += _grid_omission(tr, "gridAfter")
    if column != column_count + 1:
        raise ValueError("malformed Word table grid/merge layout")
    return cells


def _vertical_span(
    rows: list[list[tuple[int, int, Any]]],
    row_index: int,
    column: int,
    horizontal_span: int,
) -> int:
    span = 1
    for row in rows[row_index + 1 :]:
        continuation = next(
            (
                tc
                for start, width, tc in row
                if start == column and width == horizontal_span
            ),
            None,
        )
        if continuation is None or continuation.vMerge != "continue":
            break
        span += 1
    return span


def _validate_vertical_merges(rows: list[list[tuple[int, int, Any]]]) -> None:
    for row_index, row in enumerate(rows):
        previous = rows[row_index - 1] if row_index else []
        for column, width, tc in row:
            if tc.vMerge != "continue":
                continue
            owner = next(
                (
                    prior
                    for start, prior_width, prior in previous
                    if start == column and prior_width == width
                ),
                None,
            )
            if owner is None or owner.vMerge not in ("restart", "continue"):
                raise ValueError("malformed Word table vertical merge layout")


def _table_block(
    table: Table,
    *,
    order: int,
    part: str,
    block_index: int,
) -> tuple[TableBlock, bool]:
    location = DocumentLocation(part=part, block_index=block_index)
    column_count = len(table.columns)
    raw_rows = list(table._tbl.tr_lst)  # pyright: ignore[reportPrivateUsage]
    grid_rows = [_row_grid_cells(tr, column_count) for tr in raw_rows]
    _validate_vertical_merges(grid_rows)
    cells: list[ParsedCell] = []
    nested_table = False

    for row_offset, row in enumerate(grid_rows):
        for column, horizontal_span, tc in row:
            vertical_state = tc.vMerge
            if vertical_state == "continue":
                continue
            cell = _Cell(tc, table)
            if cell.tables:
                nested_table = True
            vertical_span = (
                _vertical_span(grid_rows, row_offset, column, horizontal_span)
                if vertical_state == "restart"
                else 1
            )
            end_row = row_offset + vertical_span
            end_column = column + horizontal_span - 1
            merged_range = None
            if horizontal_span > 1 or vertical_span > 1:
                merged_range = f"R{row_offset + 1}C{column}:R{end_row}C{end_column}"
            links: list[ParsedLink] = []
            for paragraph in cell.paragraphs:
                links.extend(_paragraph_links(paragraph, location))
            cells.append(
                ParsedCell(
                    row_index=row_offset + 1,
                    column_index=column,
                    text=cell.text,
                    value_type="text",
                    location=location,
                    merged_range=merged_range,
                    links=tuple(links),
                )
            )

    parsed = ParsedTable(
        row_count=len(raw_rows),
        column_count=column_count,
        cells=tuple(cells),
        location=location,
    )
    return TableBlock(order=order, table=parsed), nested_table


def _part_blocks(
    content: Iterable[Paragraph | Table],
    *,
    part: str,
    start_order: int,
) -> tuple[list[TextBlock | TableBlock], bool]:
    blocks: list[TextBlock | TableBlock] = []
    nested_table = False
    for block_index, item in enumerate(content):
        order = start_order + len(blocks)
        if isinstance(item, Paragraph):
            blocks.append(
                _paragraph_block(
                    item,
                    order=order,
                    part=part,
                    block_index=block_index,
                )
            )
            continue
        table_block, has_nested = _table_block(
            item,
            order=order,
            part=part,
            block_index=block_index,
        )
        nested_table = nested_table or has_nested
        blocks.append(table_block)
    return blocks, nested_table


def _header_footer_content(
    part: HeaderPart | FooterPart,
) -> Iterable[Paragraph | Table]:
    for child in part.element:
        local_name = child.tag.rsplit("}", 1)[-1]
        if local_name == "p":
            yield Paragraph(child, part)
        elif local_name == "tbl":
            yield Table(child, part)


def _feature_limitations(scan: PackageScan) -> list[ParserLimitation]:
    limitations: list[ParserLimitation] = []
    for feature in scan.features:
        kind, detail = _FEATURE_DETAILS[feature]
        limitations.append(
            ParserLimitation(
                kind=kind,
                code=feature,
                detail=detail,
                feature=feature,
            )
        )
    return limitations


def extract_docx(
    document: DocumentObject, scan: PackageScan
) -> tuple[tuple[TextBlock | TableBlock, ...], tuple[ParserLimitation, ...]]:
    """Extract supported stories and disclose every detected coverage gap."""
    blocks, nested_table = _part_blocks(
        document.iter_inner_content(),
        part="word/document.xml",
        start_order=0,
    )

    package = document.part.package
    if package is None:
        raise ValueError("DOCX document part is detached from its package")
    story_parts = [
        part for part in package.parts if isinstance(part, (HeaderPart, FooterPart))
    ]
    story_parts.sort(key=lambda part: str(part.partname))
    for part in story_parts:
        part_name = str(part.partname).lstrip("/")
        story_blocks, has_nested = _part_blocks(
            _header_footer_content(part),
            part=part_name,
            start_order=len(blocks),
        )
        nested_table = nested_table or has_nested
        blocks.extend(story_blocks)

    limitations = _feature_limitations(scan)
    if nested_table:
        limitations.append(
            ParserLimitation(
                kind=LimitationKind.PARTIAL,
                code="nested-tables",
                detail=(
                    "Nested table structure inside a cell is not emitted as a "
                    "separate ordered table block."
                ),
                feature="nested-tables",
            )
        )
    limitations.append(
        ParserLimitation(
            kind=LimitationKind.PARTIAL,
            code="word-feature-coverage",
            detail=(
                "Successful native extraction covers paragraphs, tables, "
                "headers, footers, and hyperlinks only; it does not prove full "
                "OOXML document understanding."
            ),
            feature="feature-coverage",
        )
    )
    return tuple(blocks), tuple(limitations)
