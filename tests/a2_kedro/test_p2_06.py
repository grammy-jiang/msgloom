"""P2-06 attachment inventory: roles, windows, limitations and privacy."""

from __future__ import annotations

import hashlib
import re

import pytest

from msgloom.a2_kedro.contracts.codec import A2ContractError
from msgloom.a2_kedro.parsers import attachments
from msgloom.a2_kedro.parsers.attachments import (
    AttachmentInventory,
    AttachmentRecord,
    inventory_attachments,
    sanitize_filename,
)
from msgloom.a2_kedro.parsers.mime_html import parse_mime
from msgloom.contracts import Limitation, TerminalStatus
from tests.a2_kedro.helpers import check

SENTINEL = "alice.private@example.invalid"
PATH_ONLY = re.compile(r"1(\.[0-9]+)*")
PDF_B64 = b"JVBERi0xLjQgZmFrZQ=="  # base64 of b"%PDF-1.4 fake" (13 bytes)
PDF_SHA = "932d2676c1e461ba50d559bba416fbc6af8da1f74309ae81370c615223d0e349"
PNG_B64 = b"UE5HREFUQS0x"  # base64 of b"PNGDATA-1" (9 bytes)
PNG_SHA = "4629acd4d690d27e3786ea4831e257ed28f6c037ddd0adee9759b9ea765f52c0"
HEAD = b"From: a@example.invalid\r\nSubject: s\r\n"


def lines(*items: bytes | str) -> bytes:
    """Join header or body lines with CRLF; the last line has no CRLF."""
    return b"\r\n".join(i.encode() if isinstance(i, str) else i for i in items)


def mixed(
    boundary: str, *children: bytes, close: bool = True, kind: str = "mixed"
) -> bytes:
    """Build the entity of a multipart; each child is a full entity."""
    out = f"Content-Type: multipart/{kind}; boundary={boundary}\r\n\r\n".encode()
    for child in children:
        out += b"--" + boundary.encode() + b"\r\n" + child + b"\r\n"
    return out + (b"--" + boundary.encode() + b"--\r\n" if close else b"")


TEXT = lines("Content-Type: text/plain", "", "hello")
PDF = lines(
    "Content-Type: application/pdf",
    'Content-Disposition: attachment; filename="report.pdf"',
    "Content-Transfer-Encoding: base64",
    "",
    PDF_B64,
)


def build(*children: bytes, boundary: str = "AAA", kind: str = "mixed") -> bytes:
    return HEAD + mixed(boundary, *children, kind=kind)


def run(
    data: bytes, **kwargs: int | None
) -> tuple[AttachmentInventory, set[tuple[str, str]]]:
    result = parse_mime(data)
    inventory = inventory_attachments(result, data, **kwargs)
    return inventory, {(i.code, i.detail) for i in inventory.limitations}


def only(inventory: AttachmentInventory) -> AttachmentRecord:
    check(len(inventory.records) == 1, "expected exactly one record")
    return inventory.records[0]


def paths(inventory: AttachmentInventory) -> list[str]:
    return [record.path for record in inventory.records]


def nest(levels: int, leaf: bytes) -> bytes:
    """Wrap ``leaf`` in ``levels`` multipart/mixed entities."""
    entity = leaf
    for number in reversed(range(levels)):
        entity = mixed(f"N{number}", entity)
    return HEAD + entity


def test_plain_attachment_has_window_size_hash_and_parent() -> None:
    data = build(TEXT, PDF)
    inventory, limits = run(data)
    record = only(inventory)
    check(inventory.status is TerminalStatus.COMPLETE, "status must be COMPLETE")
    check(limits == set(), "no limitation expected")
    check(record.path == "1.2" and record.parent == "1", "path or parent wrong")
    check(record.message_path is None, "top-level part has no message path")
    check(record.role == "attachment", "role must be attachment")
    check(record.media_type == "application/pdf", "media type wrong")
    check(record.filename == "report.pdf", "filename wrong")
    check(not record.has_content_id, "no Content-ID expected")
    check((record.size, record.sha256) == (13, PDF_SHA), "size or hash wrong")
    check(record.status == "ok" and record.flags == (), "status or flags wrong")
    first = data.index(b"Content-Type: application/pdf")
    last = data.index(b"\r\n--AAA--")
    check((record.start, record.end) == (first, last), "window wrong")
    check(data[record.start : record.end].endswith(PDF_B64), "window misses body")
    check(inventory.seen == 1, "seen must be 1")
    check(inventory.input_size == len(data), "input size wrong")


def test_inline_image_with_content_id_is_inline() -> None:
    html = lines("Content-Type: text/html", "", "<img src=cid:logo>")
    image = lines(
        "Content-Type: image/png",
        "Content-ID: <logo@example.invalid>",
        "Content-Disposition: inline",
        "Content-Transfer-Encoding: base64",
        "",
        PNG_B64,
    )
    bare = lines("Content-Type: image/gif", "Content-ID: <b>", "", "GIF89a")
    inventory, limits = run(build(html, image, bare, kind="related", boundary="RRR"))
    check(limits == set(), "no limitation expected")
    check(paths(inventory) == ["1.2", "1.3"], "paths wrong")
    first, second = inventory.records
    check(first.role == "inline" and first.has_content_id, "first must be inline")
    check((first.size, first.sha256) == (9, PNG_SHA), "inline payload wrong")
    check(first.filename is None, "inline image has no filename")
    check(second.role == "inline" and second.size == 6, "second must be inline")


def test_nested_message_rfc822_lists_message_and_inner_attachment() -> None:
    inner = HEAD + mixed("INN", TEXT, PDF)
    outer_part = lines(
        "Content-Type: message/rfc822",
        'Content-Disposition: attachment; filename="fwd.eml"',
        "",
        inner,
    )
    data = build(TEXT, outer_part, boundary="OUT")
    inventory, limits = run(data)
    check(limits == set(), "no limitation expected")
    check(paths(inventory) == ["1.2", "1.2.1.2"], "paths wrong")
    message, nested = inventory.records
    check(message.role == "embedded_message", "message role wrong")
    check(message.filename == "fwd.eml", "message filename wrong")
    check(message.size == len(inner), "message size must be the inner byte count")
    check(message.sha256 == hashlib.sha256(inner).hexdigest(), "message hash wrong")
    check(message.message_path is None, "outer message has no message path")
    check(nested.role == "attachment" and nested.parent == "1.2.1", "nested wrong")
    check(nested.message_path == "1.2", "nested part must name its message")
    check((nested.size, nested.sha256) == (13, PDF_SHA), "nested payload wrong")
    check(inventory.seen == 2, "seen must be 2")


def test_attachment_in_mixed_inside_related() -> None:
    html = lines("Content-Type: text/html", "", "<p>x</p>")
    png = lines("Content-Type: image/png", "", "PNGDATA-1")
    data = build(html, mixed("MIX", PDF, png), kind="related", boundary="REL")
    inventory, limits = run(data)
    check(limits == set(), "no limitation expected")
    check(paths(inventory) == ["1.2.1", "1.2.2"], "paths wrong")
    check([r.parent for r in inventory.records] == ["1.2", "1.2"], "parents wrong")
    # The parent is the mixed group, so the bare image is not inline.
    check([r.role for r in inventory.records] == ["attachment", "attachment"], "roles")


def test_duplicate_filenames_keep_every_record_and_flag_them() -> None:
    def named(name: str, body: bytes) -> bytes:
        return lines(
            "Content-Type: application/octet-stream",
            f'Content-Disposition: attachment; filename="{name}"',
            "Content-Transfer-Encoding: base64",
            "",
            body,
        )

    data = build(
        TEXT,
        named("dup.bin", b"ZHVwLW9uZQ=="),
        named("DUP.bin", b"ZHVwLXR3bw=="),
        named("other.bin", b"ZHVwLW9uZQ=="),
    )
    inventory, limits = run(data)
    check(limits == set(), "duplicates are not a limitation")
    check(paths(inventory) == ["1.2", "1.3", "1.4"], "every record must stay")
    one = "e062dcf4581c10e3eeaa787c65f958f0c8dcef24d4343782dffd89ed63e069c1"
    two = "1341262f821e6f60af7f694f51dffb87f1c981a203227acbdb272da2436b2c52"
    check([r.sha256 for r in inventory.records][:2] == [one, two], "hashes")
    flags = [r.flags for r in inventory.records]
    check(flags[0] == flags[1] == ("filename_duplicate",), "duplicates not flagged")
    check(flags[2] == (), "unique name must not be flagged")


def test_hostile_filenames_are_sanitized() -> None:
    def named(disposition: str) -> bytes:
        return lines(
            "Content-Type: application/octet-stream",
            f"Content-Disposition: attachment; {disposition}",
            "",
            "xyz",
        )

    data = build(
        TEXT,
        named('filename="../../etc/passwd"'),
        named("filename*=utf-8''evil%0D%0ABcc%3A%20x.txt%07"),
        named('filename="..\\\\..\\\\win.ini"'),
        named('filename=".."'),
    )
    inventory, limits = run(data)
    check(limits == set(), "no limitation expected")
    names = [r.filename for r in inventory.records]
    check(names == ["passwd", "evil__Bcc: x.txt_", "win.ini", None], f"names {names}")
    for record in inventory.records:
        check(record.flags == ("filename_sanitized",), "sanitized flag missing")
        label = record.filename or ""
        check("/" not in label and "\\" not in label, "separator left in label")
        check(all(ord(c) >= 32 and ord(c) != 127 for c in label), "control char")


def test_attachment_only_message_has_complete_inventory() -> None:
    data = build(PDF)
    result = parse_mime(data)
    check(result.body_status == "missing", "fixture must have no body")
    inventory = inventory_attachments(result, data)
    check(inventory.status is TerminalStatus.COMPLETE, "body gap is not ours")
    check(paths(inventory) == ["1.1"], "attachment missing")
    root_only = lines("Content-Type: application/pdf", "", "RAW")
    inventory, limits = run(root_only)
    check(limits == set() and paths(inventory) == ["1"], "root attachment missing")
    check(only(inventory).parent is None, "root has no parent")


def test_no_attachment_message_is_complete_and_empty() -> None:
    data = lines("Content-Type: text/plain", "", "just text")
    inventory, limits = run(data)
    check(inventory.status is TerminalStatus.COMPLETE, "must be COMPLETE")
    check(inventory.records == () and inventory.limitations == (), "must be empty")
    check(inventory.seen == 0 and limits == set(), "seen must be 0")
    inventory, _ = run(b"")
    check(inventory.status is TerminalStatus.COMPLETE and inventory.seen == 0, "empty")


def test_calendar_csv_and_other_roles() -> None:
    cal = lines("Content-Type: text/calendar; method=REQUEST", "", "BEGIN:VCALENDAR")
    csv = lines("Content-Type: text/csv", "", "a,b")
    dsn = lines("Content-Type: message/delivery-status", "", "Status: 5.0.0")
    inventory, limits = run(build(TEXT, cal, csv, dsn))
    check(limits == set(), "no limitation expected")
    check(
        [r.role for r in inventory.records] == ["calendar", "attachment", "attachment"],
        "roles wrong",
    )
    csv_sha = "1eb7c54d52831bbfe8942af0b1c56b7409523a59ed6ca99c1174fef7eb32c1b5"
    check(inventory.records[1].sha256 == csv_sha, "csv hash wrong")


def test_bodies_and_containers_are_not_attachments() -> None:
    inline_text = lines(
        "Content-Type: text/plain", "Content-Disposition: inline", "", "t"
    )
    html_cid = lines("Content-Type: text/html", "Content-ID: <h>", "", "<p>h</p>")
    group = lines(
        "Content-Type: multipart/mixed; boundary=IN",
        "Content-Disposition: attachment",
        "",
        "--IN",
        "",
        "plain",
        "--IN--",
    )
    inventory, limits = run(build(inline_text, html_cid, group))
    check(inventory.records == () and inventory.seen == 0, "no attachment expected")
    check(limits == set(), "no limitation expected")


def test_missing_or_empty_payload_gives_record_and_limitation() -> None:
    no_blank = lines(
        "Content-Type: application/pdf",
        f'Content-Disposition: attachment; filename="{SENTINEL}.pdf"',
    )
    blank = lines("Content-Type: image/png", "Content-Disposition: attachment", "", "")
    inventory, limits = run(build(TEXT, no_blank, blank))
    check(inventory.status is TerminalStatus.INCOMPLETE, "must be INCOMPLETE")
    check(paths(inventory) == ["1.2", "1.3"], "records must stay")
    check(all(r.status == "empty" for r in inventory.records), "status must be empty")
    check(all(r.size is None and r.sha256 is None for r in inventory.records), "none")
    check(
        {("attachment_empty", "1.2"), ("attachment_empty", "1.3")} <= limits,
        f"limitations {limits}",
    )
    check(SENTINEL not in repr(inventory.limitations), "limitation leaks a name")


def test_bad_base64_is_undecodable_not_dropped() -> None:
    bad = lines(
        "Content-Type: application/pdf",
        "Content-Disposition: attachment; filename=x.pdf",
        "Content-Transfer-Encoding: base64",
        "",
        "@@@@ not base64 !!!",
    )
    unknown = lines(
        "Content-Type: application/pdf",
        "Content-Transfer-Encoding: uuencode",
        "",
        "begin 644 x",
    )
    inventory, limits = run(build(TEXT, bad, unknown))
    check(inventory.status is TerminalStatus.INCOMPLETE, "must be INCOMPLETE")
    check([r.status for r in inventory.records] == ["undecodable"] * 2, "status")
    check(
        {("attachment_undecodable", "1.2"), ("attachment_undecodable", "1.3")}
        <= limits,
        "limitations missing",
    )
    check(all(r.sha256 is None for r in inventory.records), "no hash for a guess")


def test_oversize_part_keeps_record_without_decoding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    big = lines("Content-Type: application/zip", "", b"Z" * 20)
    data = build(TEXT, big)
    monkeypatch.setattr(attachments, "MAX_ATTACHMENT_BYTES", 10)
    inventory, limits = run(data)
    check(only(inventory).status == "oversize", "status must be oversize")
    check(limits == {("attachment_too_large", "1.2")}, f"limitations {limits}")
    check(inventory.status is TerminalStatus.INCOMPLETE, "must be INCOMPLETE")
    monkeypatch.undo()
    inventory, limits = run(data)
    check(only(inventory).status == "ok" and limits == set(), "bound must apply")


def test_oversize_by_parser_limit_is_oversize() -> None:
    body = b"QUFB" * (2 * 1024 * 1024 + 1)  # just over the 8 MiB part cap
    big = lines(
        "Content-Type: application/pdf", "Content-Transfer-Encoding: base64", "", body
    )
    inventory, limits = run(build(TEXT, big))
    check(only(inventory).status == "oversize", "status must be oversize")
    check(("attachment_too_large", "1.2") in limits, f"limitations {limits}")


def test_nesting_over_bound_is_a_limitation() -> None:
    data = nest(10, PDF)  # the attachment path has 11 components (bound is 8)
    inventory, limits = run(data)
    deep_path = "1" + ".1" * 10
    check(inventory.records == (), "too deep part must not be a record")
    check(limits == {("attachment_depth_limit", deep_path)}, f"limits {limits}")
    check(inventory.seen == 1, "the part must still be counted")
    check(inventory.status is TerminalStatus.INCOMPLETE, "must be INCOMPLETE")
    inventory, limits = run(nest(6, PDF))
    check(limits == set() and paths(inventory) == ["1" + ".1" * 6], "bound too low")


def test_parser_depth_limit_is_a_limitation() -> None:
    data = nest(30, PDF)  # P2-01 stops expanding below depth 16
    inventory, limits = run(data)
    check(inventory.records == (), "no record expected")
    check(("attachment_depth_limit", "1" + ".1" * 16) in limits, f"limits {limits}")
    check(inventory.status is TerminalStatus.INCOMPLETE, "must be INCOMPLETE")


def test_declared_count_mismatch() -> None:
    data = build(TEXT, PDF)
    inventory, limits = run(data, declared_count=2)
    check(limits == {("attachment_count_mismatch", "1")}, f"limits {limits}")
    check(inventory.status is TerminalStatus.INCOMPLETE, "must be INCOMPLETE")
    check(len(inventory.records) == 1, "the found attachment must stay")
    inventory, limits = run(data, declared_count=1)
    check(limits == set(), "matching count must pass")
    inventory, limits = run(build(TEXT), declared_count=0)
    check(limits == set(), "zero equals zero")
    claim = HEAD + b"X-MS-Has-Attach: yes\r\n" + TEXT
    _, limits = run(claim)
    check(limits == {("attachment_count_mismatch", "1")}, "header claim ignored")
    _, limits = run(HEAD + b"X-MS-Has-Attach: yes\r\n" + build(PDF)[len(HEAD) :])
    check(limits == set(), "header claim with an attachment must pass")


def test_truncated_structure_is_reported() -> None:
    data = HEAD + mixed("AAA", TEXT, PDF, close=False)
    inventory, limits = run(data)
    check(("structure_incomplete", "1") in limits, f"limits {limits}")
    check(paths(inventory) == ["1.2"], "found attachment must stay")
    check(inventory.status is TerminalStatus.INCOMPLETE, "must be INCOMPLETE")


def test_source_mismatch_is_a_limitation() -> None:
    data = build(TEXT, PDF)
    result = parse_mime(data)
    inventory = inventory_attachments(result, data + b"x")
    check(inventory.records == (), "mismatched source gives no record")
    check(
        inventory.limitations == (Limitation("source_mismatch", "1"),),
        "source mismatch not reported",
    )
    check(inventory.status is TerminalStatus.INCOMPLETE, "must be INCOMPLETE")


def test_attachment_count_bound_keeps_every_part_accounted_for() -> None:
    items = [lines("Content-Type: application/pdf", "", f"p{n}") for n in range(130)]
    inventory, limits = run(build(TEXT, *items))
    check(len(inventory.records) == attachments.MAX_ATTACHMENTS, "record cap wrong")
    check(inventory.seen == 130, "every part must be counted")
    over = {d for c, d in limits if c == "attachment_limit"}
    check(len(over) == 2, "excess parts must have limitations")
    seen_paths = set(paths(inventory)) | over
    check(seen_paths == {f"1.{n}" for n in range(2, 132)}, "a part is unaccounted")


def test_inventory_and_limitations_cover_every_attachment_like_part() -> None:
    bad = lines(
        "Content-Type: application/pdf", "Content-Transfer-Encoding: base64", "", "@@@@"
    )
    empty = lines("Content-Type: image/png", "Content-Disposition: attachment")
    image = lines("Content-Type: image/png", "Content-ID: <i>", "", "PNG")
    forwarded = lines(
        "Content-Type: message/rfc822", "", HEAD + mixed("INN", TEXT, PDF, bad)
    )
    related = mixed(
        "REL", lines("Content-Type: text/html", "", "<p>x</p>"), image, kind="related"
    )
    data = build(TEXT, PDF, bad, empty, forwarded, related, boundary="OUT")
    inventory, limits = run(data)
    expected = {"1.2", "1.3", "1.4", "1.5", "1.5.1.2", "1.5.1.3", "1.6.2"}
    covered = set(paths(inventory)) | {d for _, d in limits}
    check(covered == expected, f"covered {sorted(covered)}")
    check(inventory.seen == len(expected), "seen must match the expected count")
    bad_paths = {"1.3", "1.4", "1.5.1.3"}
    check({d for _, d in limits} == bad_paths, "only the bad parts need a limit")
    for record in inventory.records:
        check((record.path in bad_paths) == (record.status != "ok"), "status")


def test_same_input_gives_equal_result() -> None:
    data = build(TEXT, PDF, PDF)
    first = inventory_attachments(parse_mime(data), data)
    second = inventory_attachments(parse_mime(bytes(bytearray(data))), bytearray(data))  # type: ignore[arg-type]
    check(first == second, "results must be equal")
    check(first.limitations == tuple(sorted(first.limitations, key=repr)), "order")


def test_wrong_argument_types_raise_fixed_errors() -> None:
    data = build(TEXT, PDF)
    result = parse_mime(data)
    secret = SENTINEL
    cases: list[tuple[object, object, object]] = [
        (secret, data, None),
        (None, data, None),
        (result, secret, None),
        (result, 12, None),
        (result, data, secret),
        (result, data, True),
        (result, data, -1),
        (result, data, 1.5),
    ]
    for res, raw, count in cases:
        with pytest.raises(A2ContractError) as info:
            inventory_attachments(res, raw, declared_count=count)  # type: ignore[arg-type]
        text = str(info.value)
        check(SENTINEL not in text and "report.pdf" not in text, "error leaks input")
        check(len(text) < 60, "error text must be a short fixed message")


def test_limitations_and_repr_hold_paths_only() -> None:
    hostile = lines(
        "Content-Type: application/pdf",
        f'Content-Disposition: attachment; filename="{SENTINEL}\x01.pdf"'.encode(),
        "Content-Transfer-Encoding: base64",
        "",
        f"@@@@ {SENTINEL}",
    )
    inventory, limits = run(build(TEXT, hostile))
    check(limits != set(), "limitation expected")
    for item in inventory.limitations:
        check(PATH_ONLY.fullmatch(item.detail) is not None, "detail is not a path")
        check(SENTINEL not in item.code + item.detail, "limitation leaks content")
    label = only(inventory).filename or ""
    check(label == f"{SENTINEL}_.pdf", f"label {label!r}")


def test_sanitize_filename_cases() -> None:
    check(sanitize_filename("a.txt") == "a.txt", "plain name changed")
    check(sanitize_filename("dir/sub\\b.txt") == "b.txt", "last segment only")
    check(sanitize_filename("") is None and sanitize_filename("/") is None, "empty")
    check(sanitize_filename("..") is None and sanitize_filename(" . ") is None, "dots")
    check(sanitize_filename("a\x00b\u202ec") == "a_b_c", "format and control chars")
    check(sanitize_filename("a\udcffb") == "a_b", "surrogate must not survive")
    long = sanitize_filename("x" * 500 + ".txt")
    check(long == "x" * attachments.MAX_FILENAME_CHARS, "length bound wrong")
