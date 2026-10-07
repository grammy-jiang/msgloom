"""Lexbor HTML extraction without target fetching or active execution."""

from __future__ import annotations

import re
from collections.abc import Iterable

from selectolax.lexbor import LexborHTMLParser, LexborNode

from msgloom.preparation.contracts import (
    BlockRole,
    DocumentLocation,
    LimitationKind,
    ParsedCell,
    ParsedLink,
    ParsedTable,
)
from msgloom.preparation.parsers.mime_html_limits import ExtractionState

_HEADING_TAGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
_TEXT_BLOCK_TAGS = frozenset({"p", "li", "pre", "blockquote"}) | _HEADING_TAGS
_BOUNDARY_TAGS = (
    frozenset(
        {
            "address",
            "article",
            "aside",
            "blockquote",
            "dd",
            "div",
            "dl",
            "dt",
            "footer",
            "header",
            "li",
            "main",
            "nav",
            "ol",
            "p",
            "pre",
            "section",
            "ul",
        }
    )
    | _HEADING_TAGS
)
_ACTIVE_TAGS = frozenset(
    {"script", "style", "noscript", "template", "iframe", "object", "embed"}
)
_EMBEDDED_TAGS = frozenset({"img", "video", "audio", "canvas", "svg"})
_WHITESPACE = re.compile(r"\s+")


def _normalise_text(value: str) -> str:
    """Collapse source whitespace for a normal-flow text node."""
    return _WHITESPACE.sub(" ", value)


def _nearest_ancestor(
    node: LexborNode,
    tags: frozenset[str],
) -> LexborNode | None:
    """Return the closest element ancestor whose tag is selected."""
    parent = node.parent
    while parent is not None:
        if parent.tag in tags:
            return parent
        parent = parent.parent
    return None


def _text_pieces(
    node: LexborNode,
    *,
    preformatted: bool = False,
) -> Iterable[str | None]:
    """Yield direct text and explicit semantic-boundary markers."""
    child = node.child
    while child is not None:
        next_child = child.next
        tag = child.tag
        if tag == "table" or tag in _ACTIVE_TAGS:
            child = next_child
            continue
        if tag == "-text":
            value = child.text(deep=False)
            yield value if preformatted else _normalise_text(value)
            child = next_child
            continue
        if tag == "br":
            yield None
            child = next_child
            continue

        is_boundary = tag in _BOUNDARY_TAGS
        if is_boundary:
            yield None
        yield from _text_pieces(
            child,
            preformatted=preformatted or tag == "pre",
        )
        if is_boundary:
            yield None
        child = next_child


def _text_without_nested_tables(node: LexborNode) -> str:
    """Collect text while retaining line/block boundaries and inline joins."""
    pieces = list(_text_pieces(node, preformatted=node.tag == "pre"))
    rendered: list[str] = []
    previous_boundary = False
    for piece in pieces:
        if piece is None:
            if rendered and not previous_boundary:
                rendered.append("\n")
            previous_boundary = True
            continue
        if piece:
            if previous_boundary and not piece.strip():
                continue
            rendered.append(piece)
            previous_boundary = False
    return "".join(rendered).strip()


def _node_text(node: LexborNode) -> str:
    """Return meaningful descendant text with active content excluded."""
    return _text_without_nested_tables(node)


def _links_for(
    node: LexborNode,
    location: DocumentLocation,
    *,
    table: LexborNode | None = None,
) -> tuple[ParsedLink, ...]:
    """Return inert links belonging to this block or table scope."""
    links: list[ParsedLink] = []
    for anchor in node.css("a[href]"):
        nearest_table = _nearest_ancestor(anchor, frozenset({"table"}))
        if table is not None and nearest_table != table:
            continue
        target = anchor.attributes.get("href")
        if not target or not target.strip():
            continue
        links.append(
            ParsedLink(
                target=target,
                text=_node_text(anchor) or None,
                location=location,
            )
        )
    return tuple(links)


def _span_value(
    state: ExtractionState,
    cell: LexborNode,
    attribute: str,
    location: DocumentLocation,
) -> int | None:
    """Return a bounded positive HTML span or expose unsafe structure."""
    raw = cell.attributes.get(attribute)
    if raw is None:
        return 1
    if not raw.isascii() or not raw.isdecimal():
        state.add_limitation(
            LimitationKind.PARTIAL,
            "html-table-span-unsupported",
            "A table span was malformed; the affected table was skipped.",
            feature="table-span",
            location=location,
        )
        return None
    value = int(raw)
    if value < 1 or value > state.limits.container_members:
        state.add_limitation(
            LimitationKind.PARTIAL,
            "html-table-span-unsupported",
            "A table span was unsupported or exceeded structural bounds; "
            "the affected table was skipped.",
            feature="table-span",
            location=location,
        )
        return None
    return value


def _merged_range(
    row: int,
    column: int,
    rowspan: int,
    colspan: int,
) -> str | None:
    """Represent an HTML merged cell with stable one-based grid coordinates."""
    if rowspan == 1 and colspan == 1:
        return None
    return f"R{row}C{column}:R{row + rowspan - 1}C{column + colspan - 1}"


def _table_cells(
    state: ExtractionState,
    table: LexborNode,
    location: DocumentLocation,
) -> tuple[tuple[ParsedCell, ...], int, int] | None:
    """Map source cells onto a bounded grid honoring rowspan and colspan."""
    rows = [
        row
        for row in table.css("tr")
        if _nearest_ancestor(row, frozenset({"table"})) == table
    ]
    cells: list[ParsedCell] = []
    occupied_until: dict[int, int] = {}
    max_row = len(rows)
    max_column = 0

    for row_index, row in enumerate(rows, start=1):
        owned = [
            cell
            for cell in row.css("th, td")
            if _nearest_ancestor(cell, frozenset({"table"})) == table
        ]
        column = 1
        for cell in owned:
            rowspan = _span_value(state, cell, "rowspan", location)
            colspan = _span_value(state, cell, "colspan", location)
            if rowspan is None or colspan is None:
                return None

            while any(
                occupied_until.get(candidate, 0) >= row_index
                for candidate in range(column, column + colspan)
            ):
                column += 1
                if column > state.limits.container_members:
                    state.add_limitation(
                        LimitationKind.PARTIAL,
                        "html-table-grid-limit",
                        "A table grid exceeded structural bounds and was skipped.",
                        feature="table-grid",
                        location=location,
                    )
                    return None

            end_row = row_index + rowspan - 1
            end_column = column + colspan - 1
            if end_column > state.limits.container_members:
                state.add_limitation(
                    LimitationKind.PARTIAL,
                    "html-table-grid-limit",
                    "A table grid exceeded structural bounds and was skipped.",
                    feature="table-grid",
                    location=location,
                )
                return None
            for occupied_column in range(column, end_column + 1):
                occupied_until[occupied_column] = end_row

            cells.append(
                ParsedCell(
                    row_index=row_index,
                    column_index=column,
                    text=_text_without_nested_tables(cell) or None,
                    value_type="text",
                    location=location,
                    merged_range=_merged_range(
                        row_index,
                        column,
                        rowspan,
                        colspan,
                    ),
                    links=_links_for(cell, location, table=table),
                )
            )
            max_row = max(max_row, end_row)
            max_column = max(max_column, end_column)
            column = end_column + 1

    return tuple(cells), max_row, max_column


def _has_nested_table(table: LexborNode) -> bool:
    """Return whether this table owns a descendant nested table."""
    return any(
        _nearest_ancestor(candidate, frozenset({"table"})) == table
        for candidate in table.css("table")
    )


def _emit_table(
    state: ExtractionState,
    node: LexborNode,
    location: DocumentLocation,
) -> None:
    """Emit a complete HTML table with stable grid source metadata."""
    if _has_nested_table(node):
        state.add_limitation(
            LimitationKind.PARTIAL,
            "html-nested-table-order-partial",
            "A nested table is emitted separately; the flat table contract "
            "cannot represent its exact position within the outer cell text.",
            feature="table-order",
            location=location,
        )
    result = _table_cells(state, node, location)
    if result is None:
        return
    cells, row_count, column_count = result
    if not cells:
        state.add_limitation(
            LimitationKind.PARTIAL,
            "html-empty-table",
            "A table had no extractable cells.",
            feature="table",
            location=location,
        )
        return
    state.add_table(
        ParsedTable(
            row_count=row_count,
            column_count=column_count,
            cells=cells,
            location=location,
        )
    )


def extract_html(
    text: str,
    state: ExtractionState,
    *,
    part_name: str,
) -> None:
    """
    Extract ordered HTML blocks into the shared state.

    Lexbor receives text already decoded by the caller. Traversal is local
    only: links, images, scripts, frames, and embedded targets are never
    opened, executed, or fetched.
    """
    parser = LexborHTMLParser(text)
    root = parser.body or parser.root
    if root is None:
        state.add_limitation(
            LimitationKind.MISSING,
            "html-no-root",
            "HTML parser produced no document root.",
            feature="html",
        )
        return

    initial_blocks = len(state.blocks)
    initial_limitations = len(state.limitations)
    semantic_ancestors = _TEXT_BLOCK_TAGS | frozenset({"table", "a"})
    skipped_ancestors = semantic_ancestors | _ACTIVE_TAGS
    for source_index, node in enumerate(
        root.traverse(include_text=True, skip_empty=True)
    ):
        location = DocumentLocation(part=part_name, block_index=source_index)
        if not state.consume_member(location=location):
            return
        tag = node.tag

        if tag in _ACTIVE_TAGS:
            state.add_limitation(
                LimitationKind.UNSUPPORTED,
                "html-active-content-skipped",
                "Active or executable HTML content was skipped.",
                feature=tag,
                location=location,
            )
            continue
        if tag in _EMBEDDED_TAGS:
            state.add_limitation(
                LimitationKind.UNSUPPORTED,
                "html-image-skipped"
                if tag == "img"
                else "html-embedded-content-skipped",
                "Embedded HTML content was not fetched or decoded.",
                feature=tag,
                location=location,
            )
            continue

        if tag in _TEXT_BLOCK_TAGS:
            if _nearest_ancestor(node, frozenset({"table"})) is not None:
                continue
            if _nearest_ancestor(node, _TEXT_BLOCK_TAGS) is not None:
                continue
            text_value = _node_text(node)
            if not text_value:
                continue
            role = BlockRole.HEADING if tag in _HEADING_TAGS else BlockRole.PARAGRAPH
            state.add_text(
                role,
                text_value,
                location,
                links=_links_for(node, location),
            )
            continue

        if tag == "table":
            _emit_table(state, node, location)
            continue

        if tag == "a":
            if _nearest_ancestor(node, semantic_ancestors) is not None:
                continue
            target = node.attributes.get("href")
            if not target or not target.strip():
                state.add_limitation(
                    LimitationKind.PARTIAL,
                    "html-link-without-target",
                    "A link without a usable target was skipped.",
                    feature="link",
                    location=location,
                )
                continue
            state.add_link(
                ParsedLink(
                    target=target,
                    text=_node_text(node) or None,
                    location=location,
                )
            )
            continue

        if tag != "-text":
            continue
        if _nearest_ancestor(node, skipped_ancestors) is not None:
            continue
        text_value = _normalise_text(node.text(deep=False)).strip()
        if text_value:
            state.add_text(BlockRole.TEXT, text_value, location)

    if (
        len(state.blocks) == initial_blocks
        and len(state.limitations) == initial_limitations
    ):
        state.add_limitation(
            LimitationKind.MISSING,
            "html-no-readable-content",
            "HTML contained no readable content represented by this parser.",
            feature="html",
            location=DocumentLocation(part=part_name, block_index=0),
        )
