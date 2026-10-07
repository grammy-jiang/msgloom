"""Lexbor HTML extraction and source-order regressions."""

from __future__ import annotations

import pytest

from msgloom.preparation.contracts import (
    BlockRole,
    DocumentFormat,
    LinkBlock,
    TableBlock,
    TextBlock,
)
from msgloom.preparation.parsers.mime_html import parse
from tests.parser_mime_html.conftest import parser_request

HTML = b"""<!doctype html>
<html><body>
<h2>Heading</h2>
<p>Alpha <a href="https://example.invalid/a">linked text</a> omega.</p>
<table>
  <tr><td>Outer A<table><tr><td>Inner 1</td><td>Inner 2</td></tr></table></td>
      <td>Outer B</td></tr>
</table>
<a href="https://example.invalid/standalone">Standalone</a>
<img src="https://example.invalid/image.png" alt="diagram">
<script>do_not_execute()</script>
</body></html>"""


def test_html_preserves_blocks_inline_text_nested_tables_and_links() -> None:
    """HTML output retains meaningful order without flattening nested tables."""
    output = parse(parser_request(HTML, DocumentFormat.HTML), HTML)

    if not isinstance(output.blocks[0], TextBlock):
        pytest.fail("Expected heading text first")
    heading = output.blocks[0]
    if heading.role is not BlockRole.HEADING or heading.text != "Heading":
        pytest.fail("Expected heading role and text")

    paragraph = output.blocks[1]
    if not isinstance(paragraph, TextBlock):
        pytest.fail("Expected paragraph second")
    if paragraph.text != "Alpha linked text omega.":
        pytest.fail(f"Unexpected inline paragraph text: {paragraph.text!r}")
    if len(paragraph.links) != 1:
        pytest.fail("Expected inline link metadata on paragraph")
    if paragraph.links[0].target != "https://example.invalid/a":
        pytest.fail("Expected exact inline link target as inert data")

    tables = [block for block in output.blocks if isinstance(block, TableBlock)]
    if len(tables) != 2:
        pytest.fail("Expected outer and nested tables as separate ordered blocks")
    outer = tables[0].table
    if tuple((cell.row_index, cell.column_index) for cell in outer.cells) != (
        (1, 1),
        (1, 2),
    ):
        pytest.fail("Expected outer table cells in row/column order")
    if outer.cells[0].text != "Outer A":
        pytest.fail("Nested table text must not flatten into the outer cell")
    inner_text = tuple(cell.text for cell in tables[1].table.cells)
    if inner_text != ("Inner 1", "Inner 2"):
        pytest.fail("Expected nested table cell order")

    standalone = [block for block in output.blocks if isinstance(block, LinkBlock)]
    if len(standalone) != 1:
        pytest.fail("Expected one standalone link block")
    if standalone[0].link.text != "Standalone":
        pytest.fail("Expected standalone link text")


def test_html_skips_active_and_embedded_targets_with_limitations() -> None:
    """Scripts and image targets are never executed or fetched."""
    output = parse(parser_request(HTML, DocumentFormat.HTML), HTML)
    codes = {item.code for item in output.limitations}
    if "html-image-skipped" not in codes:
        pytest.fail("Expected explicit skipped-image limitation")
    if "html-active-content-skipped" not in codes:
        pytest.fail("Expected explicit skipped-script limitation")
    text = "\n".join(
        block.text for block in output.blocks if isinstance(block, TextBlock)
    )
    if "do_not_execute" in text:
        pytest.fail("Script content must not be readable output")


def test_html_invalid_utf8_is_an_explicit_encoding_limitation() -> None:
    """Direct HTML bytes are UTF-8 only at this mechanical parser boundary."""
    content = b"<p>bad \xff text</p>"
    output = parse(parser_request(content, DocumentFormat.HTML), content)
    if output.blocks:
        pytest.fail("Invalid UTF-8 HTML must not produce decoded blocks")
    if "invalid-utf8" not in {item.code for item in output.limitations}:
        pytest.fail("Expected invalid UTF-8 limitation")


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (b"<p>Pay 5<br>10 units</p>", "Pay 5\n10 units"),
        (b"<p>alpha<span>beta</span>gamma</p>", "alphabetagamma"),
        (b"<ul><li>5<br>units</li><li>10 units</li></ul>", "5\nunits"),
        (b"<pre>first\n  second</pre>", "first\n  second"),
    ],
)
def test_html_preserves_semantic_text_boundaries_without_invented_spaces(
    content: bytes,
    expected: str,
) -> None:
    """Breaks and block semantics survive while adjacent inline text stays exact."""
    output = parse(parser_request(content, DocumentFormat.HTML), content)
    texts = [block.text for block in output.blocks if isinstance(block, TextBlock)]
    if not texts or texts[0] != expected:
        pytest.fail(f"Unexpected boundary-preserving text: {texts!r}")


def test_html_table_cell_blocks_do_not_merge_values() -> None:
    """Block descendants in one cell retain a semantic line boundary."""
    content = b"<table><tr><td><p>5</p>\n  <p>10</p></td></tr></table>"
    output = parse(parser_request(content, DocumentFormat.HTML), content)
    tables = [block.table for block in output.blocks if isinstance(block, TableBlock)]
    if len(tables) != 1 or tables[0].cells[0].text != "5\n10":
        pytest.fail("Table cell block boundaries must not merge values")


def test_html_rowspan_and_colspan_map_to_stable_grid_coordinates() -> None:
    """Common HTML spans reserve occupied grid coordinates deterministically."""
    content = (
        b'<table><tr><td rowspan="2">Owner</td><td colspan="2">A</td></tr>'
        b"<tr><td>B</td><td>C</td></tr></table>"
    )
    output = parse(parser_request(content, DocumentFormat.HTML), content)
    tables = [block.table for block in output.blocks if isinstance(block, TableBlock)]
    if len(tables) != 1:
        pytest.fail("Expected one spanned table")
    table = tables[0]
    actual = tuple(
        (cell.text, cell.row_index, cell.column_index, cell.merged_range)
        for cell in table.cells
    )
    expected = (
        ("Owner", 1, 1, "R1C1:R2C1"),
        ("A", 1, 2, "R1C2:R1C3"),
        ("B", 2, 2, None),
        ("C", 2, 3, None),
    )
    if actual != expected or (table.row_count, table.column_count) != (2, 3):
        pytest.fail(f"Unexpected spanned table grid: {actual!r}")


@pytest.mark.parametrize("span", [b"0", b"-1", b"many"])
def test_html_malformed_or_unsupported_span_skips_table_safely(span: bytes) -> None:
    """Invalid spans never produce plausible but misleading coordinates."""
    content = b'<table><tr><td rowspan="' + span + b'">A</td><td>B</td></tr></table>'
    output = parse(parser_request(content, DocumentFormat.HTML), content)
    if any(isinstance(block, TableBlock) for block in output.blocks):
        pytest.fail("Unsafe table spans must skip the affected table")
    if "html-table-span-unsupported" not in {x.code for x in output.limitations}:
        pytest.fail("Expected explicit unsupported-span limitation")


def test_nested_table_exposes_flat_reading_order_gap() -> None:
    """Nested table position cannot be fully represented by the flat table block."""
    content = b"<table><tr><td>before<table><tr><td>inside</td></tr></table>after</td></tr></table>"
    output = parse(parser_request(content, DocumentFormat.HTML), content)
    tables = [block.table for block in output.blocks if isinstance(block, TableBlock)]
    if len(tables) != 2 or tables[0].cells[0].text != "beforeafter":
        pytest.fail("Expected outer and nested table mappings without flattening")
    if "html-nested-table-order-partial" not in {
        item.code for item in output.limitations
    }:
        pytest.fail("Expected explicit nested-table reading-order limitation")


def test_html_missing_or_only_skipped_content_is_visible() -> None:
    """Nonempty HTML never returns an unexplained empty semantic result."""
    missing = b"<div></div>"
    output = parse(parser_request(missing, DocumentFormat.HTML), missing)
    if "html-no-readable-content" not in {x.code for x in output.limitations}:
        pytest.fail("Expected explicit no-readable-content limitation")

    skipped = b"<object data='https://provider.invalid/private'>hidden</object>"
    skipped_output = parse(parser_request(skipped, DocumentFormat.HTML), skipped)
    if "html-active-content-skipped" not in {
        x.code for x in skipped_output.limitations
    }:
        pytest.fail("Expected explicit active/embedded subtree limitation")
    details = " ".join(item.detail for item in skipped_output.limitations)
    if "provider.invalid" in details or "private" in details:
        pytest.fail("Skipped-source URLs must not leak into limitation details")
