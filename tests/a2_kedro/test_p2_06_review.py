"""P2-06 review follow-up: unexpanded nested messages and related parts."""

from __future__ import annotations

import base64

import pytest

from tests.a2_kedro.helpers import check
from tests.a2_kedro.test_p2_06 import HEAD, PDF, TEXT, build, lines, mixed, run

BLOB = lines("Content-Type: application/octet-stream", "", "rawbytes")


def encoded_message() -> bytes:
    return base64.encodebytes(HEAD + mixed("INN", TEXT, PDF)).replace(b"\n", b"\r\n")


@pytest.mark.parametrize(
    "kind, extra",
    [
        ("message/rfc822", "Content-Transfer-Encoding: base64"),
        ("message/global", "Content-Transfer-Encoding: 7bit"),
    ],
)
def test_unexpanded_nested_message_is_reported_never_dropped(
    kind: str, extra: str
) -> None:
    body = encoded_message() if "base64" in extra else HEAD + mixed("INN", TEXT, PDF)
    part = lines(f"Content-Type: {kind}", extra, "", body)
    inventory, limits = run(build(TEXT, part, boundary="OUT"))
    check(("attachment_nested_unexpanded", "1.2") in limits, "gap not reported")
    check(inventory.status.name == "INCOMPLETE", "status must be INCOMPLETE")
    check(inventory.seen >= 1, "the message part itself must be counted")
    check(
        [r.path for r in inventory.records if r.role == "embedded_message"] == ["1.2"],
        "message part must stay in the inventory",
    )


def test_expanded_nested_message_has_no_unexpanded_limitation() -> None:
    part = lines("Content-Type: message/rfc822", "", HEAD + mixed("INN", TEXT, PDF))
    inventory, limits = run(build(TEXT, part, boundary="OUT"))
    check(limits == set(), "expanded message must be complete")
    check(inventory.status.name == "COMPLETE", "status must be COMPLETE")


def test_non_text_part_without_cid_is_inline_only_in_related() -> None:
    related, _ = run(build(TEXT, BLOB, kind="related"))
    plain, _ = run(build(TEXT, BLOB, kind="mixed"))
    check([r.role for r in related.records] == ["inline"], "related must be inline")
    check([r.role for r in plain.records] == ["attachment"], "mixed must be attachment")
