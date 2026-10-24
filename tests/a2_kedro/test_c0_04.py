"""C0-04 ParsedParts: typed parts, byte links and format consistency."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from pydantic import ValidationError

from msgloom.a2_kedro.contracts import parse
from msgloom.a2_kedro.contracts.codec import A2ContractError
from msgloom.a2_kedro.contracts.extract import ExtractedComponents
from msgloom.a2_kedro.contracts.parse import ParsedParts
from tests.a2_kedro.helpers import check, hexd

SENTINEL = "alice.private@example.invalid"


def link(cid: str = "p", sha: str = "a", size: int = 100, **kw: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "component_id": cid,
        "component_sha256": hexd(sha),
        "component_size": size,
        "offset": 0,
        "length": size,
    }
    return {**base, **kw}


def part(pid: str = "p0", fmt: str = "plain_text", **kw: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "part_id": pid,
        "role": "body",
        "declared_format": fmt,
        "detected_format": fmt,
        "link": link(),
    }
    return {**base, **kw}


def values(**kw: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "parts": (part(),),
        "receipt": {
            "worker": "worker-1",
            "worker_version": "1",
            "outcome": "complete",
            "input_bytes": 100,
            "part_count": 1,
        },
    }
    return {**base, **kw}


def build(**kw: Any) -> ParsedParts:
    return ParsedParts.model_validate(values(**kw))


def rich() -> ParsedParts:
    """A PDF with two pages and a workbook with one sheet and two cells."""
    pdf = part("p1", "pdf", role="attachment", link=link("a", "b", 50), page_count=2)
    book = part(
        "p2",
        "xlsx",
        role="attachment",
        link=link("b", "c", 80, offset=10, length=20),
        sheet_count=1,
        parent_part_id="p0",
    )
    return build(
        parts=(part(), pdf, book),
        pages=(
            {"part_id": "p1", "page_index": 0, "char_count": 10},
            {"part_id": "p1", "page_index": 1, "char_count": 0},
        ),
        sheets=({"part_id": "p2", "sheet_index": 0, "row_count": 3, "column_count": 2},),
        cells=(
            {"part_id": "p2", "sheet_index": 0, "row": 0, "column": 0,
             "value_kind": "empty"},
            {"part_id": "p2", "sheet_index": 0, "row": 2, "column": 1,
             "value_kind": "text", "value_sha256": hexd("d")},
        ),
        receipt={
            "worker": "worker-1",
            "worker_version": "1",
            "outcome": "complete",
            "input_bytes": 230,
            "part_count": 3,
        },
    )  # fmt: skip


def extracted(**changes: Any) -> ExtractedComponents:
    def comp(cid: str, role: str, sha: str, **kw: Any) -> dict[str, Any]:
        base = {
            "component_id": cid,
            "role": role,
            "status": "present",
            "reference": "saved/" + cid,
            "sha256": hexd(sha),
        }
        return {**base, **kw}

    items = [
        comp("p", "primary", "a"),
        comp("a", "attachment", "b"),
        comp("b", "attachment", "c"),
    ]
    for item in items:
        if item["component_id"] in changes:
            item.update(changes[item["component_id"]])
    return ExtractedComponents.model_validate({"components": tuple(items)})


def test_round_trip_is_canonical_and_stable() -> None:
    value = rich()
    data = value.encode()
    check(ParsedParts.decode(data) == value, "round trip")
    check(value.encode() == data, "stable bytes")
    check(value.header.kind == parse.KIND == "parsed_parts", "header kind")
    value.validate_against(extracted())


def test_wire_field_names_are_pinned() -> None:
    text = build().encode().decode()
    expected = (
        '{"cells":[],"header":{"kind":"parsed_parts","profile":'
        '"a2-c0-provisional-1","version":"1"},"pages":[],"parts":[{'
        '"declared_format":"plain_text","detected_format":"plain_text",'
        '"link":{"component_id":"p","component_sha256":"' + hexd("a") + '",'
        '"component_size":100,"length":100,"offset":0},"page_count":0,'
        '"parent_part_id":null,"part_id":"p0","role":"body",'
        '"sheet_count":0}],"receipt":{"input_bytes":100,"limit_hit":"none",'
        '"outcome":"complete","part_count":1,"worker":"worker-1",'
        '"worker_version":"1"},"sheets":[]}'
    )
    check(text == expected, "provisional wire form changed")


def test_format_mismatch_is_rejected() -> None:
    bad = part(fmt="pdf", detected_format="html")
    with pytest.raises(ValueError, match="declared format differs"):
        build(parts=(bad,))


@pytest.mark.parametrize("field", ["declared_format", "detected_format", "role"])
def test_enums_are_closed(field: str) -> None:
    with pytest.raises(ValueError):
        build(parts=(part(**{field: "mystery"}),))


def test_pages_and_sheets_need_a_matching_format() -> None:
    with pytest.raises(ValueError, match="no pages"):
        build(parts=(part(page_count=1),))
    with pytest.raises(ValueError, match="no sheets"):
        build(parts=(part("p0", "pdf", sheet_count=1),))


def test_byte_link_must_fit_inside_the_component() -> None:
    with pytest.raises(ValueError, match="outside the component"):
        build(parts=(part(link=link(size=10, offset=5, length=6)),))
    with pytest.raises(ValueError):
        build(parts=(part(link=link(length=0)),))
    with pytest.raises(ValueError):
        build(parts=(part(link=link(offset=-1)),))
    build(parts=(part(link=link(size=10, offset=5, length=5)),))


def test_dangling_or_unusable_byte_links_are_rejected() -> None:
    value = rich()
    with pytest.raises(A2ContractError, match="names no extracted component"):
        value.validate_against(
            ExtractedComponents.model_validate(
                {"components": extracted().components[:2]}
            )
        )
    with pytest.raises(A2ContractError, match="digest differs"):
        value.validate_against(extracted(b={"sha256": hexd("e")}))
    missing = {"status": "missing", "reference": None, "sha256": None}
    with pytest.raises(A2ContractError, match="unusable component"):
        value.validate_against(extracted(a=missing))
    value.validate_against(extracted(a={"status": "partial"}))


def test_part_ids_and_parents() -> None:
    with pytest.raises(ValueError, match="duplicate part id"):
        build(
            parts=(part("x"), part("x")),
            receipt={**values()["receipt"], "part_count": 2},
        )
    with pytest.raises(ValueError, match="own parent"):
        build(parts=(part(parent_part_id="p0"),))
    with pytest.raises(ValueError, match="missing or later"):
        build(parts=(part(parent_part_id="ghost"),))
    with pytest.raises(ValueError, match="at least 1|too_short|out of bounds"):
        build(parts=())


def test_page_index_and_record_rules() -> None:
    data = deepcopy(values())
    data["parts"] = (part("p1", "pdf", page_count=1),)
    page = {"part_id": "p1", "page_index": 1, "char_count": 1}
    with pytest.raises(ValueError, match="page index is out of range"):
        ParsedParts.model_validate({**data, "pages": (page,)})
    ghost = {**page, "part_id": "ghost", "page_index": 0}
    with pytest.raises(ValueError, match="page index is out of range"):
        ParsedParts.model_validate({**data, "pages": (ghost,)})
    ok = {**page, "page_index": 0}
    with pytest.raises(ValueError, match="duplicate page"):
        ParsedParts.model_validate({**data, "pages": (ok, ok)})
    data["parts"] = (part("p1", "pdf", page_count=2),)
    with pytest.raises(ValueError, match="not sorted"):
        ParsedParts.model_validate({**data, "pages": ({**ok, "page_index": 1}, ok)})


def test_sheet_and_cell_ranges() -> None:
    book = part("p1", "xlsx", sheet_count=1)
    sheet = {"part_id": "p1", "sheet_index": 0, "row_count": 2, "column_count": 2}
    cell = {"part_id": "p1", "sheet_index": 0, "row": 1, "column": 1}
    text = {**cell, "value_kind": "number", "value_sha256": hexd("d")}
    base = values(parts=(book,))
    ok = {**base, "sheets": (sheet,), "cells": (text,)}
    ParsedParts.model_validate(ok)
    with pytest.raises(ValueError, match="sheet index is out of range"):
        ParsedParts.model_validate({**base, "sheets": ({**sheet, "sheet_index": 1},)})
    for bad in ({**text, "row": 2}, {**text, "column": 2}):
        with pytest.raises(ValueError, match="cell position is out of range"):
            ParsedParts.model_validate({**ok, "cells": (bad,)})
    with pytest.raises(ValueError, match="names no sheet"):
        ParsedParts.model_validate({**ok, "sheets": (), "cells": (text,)})
    with pytest.raises(ValueError):
        ParsedParts.model_validate({**ok, "cells": ({**text, "row": -1},)})
    with pytest.raises(ValueError, match="duplicate cell"):
        ParsedParts.model_validate({**ok, "cells": (text, text)})


def test_cell_digest_rule_and_kinds() -> None:
    book = part("p1", "csv", sheet_count=1)
    sheet = {"part_id": "p1", "sheet_index": 0, "row_count": 1, "column_count": 1}
    cell = {"part_id": "p1", "sheet_index": 0, "row": 0, "column": 0}
    base = values(parts=(book,), sheets=(sheet,))
    for bad in (
        {**cell, "value_kind": "text"},
        {**cell, "value_kind": "empty", "value_sha256": hexd("d")},
        {**cell, "value_kind": "formula", "value_sha256": hexd("d")},
    ):
        with pytest.raises(ValueError):
            ParsedParts.model_validate({**base, "cells": (bad,)})


def test_receipt_rules() -> None:
    good = values()["receipt"]
    with pytest.raises(ValueError, match="part count differs"):
        build(receipt={**good, "part_count": 2})
    with pytest.raises(ValueError, match="conflicts with limit hit"):
        build(receipt={**good, "limit_hit": "time"})
    with pytest.raises(ValueError, match="conflicts with limit hit"):
        build(receipt={**good, "outcome": "partial"})
    build(receipt={**good, "outcome": "partial", "limit_hit": "time"})
    for bad in ({"outcome": "failed"}, {"limit_hit": "memory"}, {"worker": ""}):
        with pytest.raises(ValueError):
            build(receipt={**good, **bad})


def test_unknown_fields_header_and_mutation_are_rejected() -> None:
    with pytest.raises(ValueError):
        build(extra_field=1)
    with pytest.raises(ValueError):
        build(parts=(part(content="body text"),))
    with pytest.raises(ValueError, match="approved|not parsed_parts"):
        build(header={"kind": "zones", "version": "1"})
    with pytest.raises(ValidationError):
        build().receipt.part_count = 5  # type: ignore[misc]


@pytest.mark.parametrize("char", ["\x00", "\n", "\t", "\x7f", "\x85", " "])
def test_control_characters_are_rejected(char: str) -> None:
    with pytest.raises(ValueError):
        build(parts=(part("p" + char + "0"),))
    with pytest.raises(ValueError):
        build(parts=(part(link=link("c" + char)),))
    good = values()["receipt"]
    with pytest.raises(ValueError):
        build(receipt={**good, "worker": "w" + char})


def test_error_text_carries_no_input_values() -> None:
    cases: list[dict[str, Any]] = [
        {"parts": (part(SENTINEL, "pdf", detected_format="html"),)},
        {"parts": (part(SENTINEL, link=link(SENTINEL, size=1, offset=1)),)},
        {"parts": (part(SENTINEL, parent_part_id=SENTINEL),)},
        {"parts": (part(SENTINEL), part(SENTINEL))},
        {"parts": (part(SENTINEL + "\n"),)},
        {"parts": (part(SENTINEL, role="x" + SENTINEL),)},
    ]
    for case in cases:
        with pytest.raises(ValueError) as caught:
            build(**case)
        check(SENTINEL not in str(caught.value), "input value in error text")
    dangling = build(parts=(part(SENTINEL, link=link(SENTINEL)),))
    with pytest.raises(A2ContractError) as dangling_error:
        dangling.validate_against(extracted())
    check(SENTINEL not in str(dangling_error.value), "id in link error text")


def test_decode_rejects_non_canonical_bytes() -> None:
    data = build().encode()
    with pytest.raises(A2ContractError):
        ParsedParts.decode(data.replace(b'"cells"', b' "cells"'))
    with pytest.raises(A2ContractError):
        ParsedParts.decode(data.replace(b'"parts"', b'"parts2"'))
