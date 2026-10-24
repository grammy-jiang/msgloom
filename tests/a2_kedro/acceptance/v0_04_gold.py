"""
Gold access and comparison tools for the V0-04 acceptance test.

The gold files are read only. This module checks their digests against
``MANIFEST.sha256``, loads the cases and compares observed facts with the
gold ``expected`` block. It holds no expected value of its own. The only
tables here are vocabulary maps from implementation limitation codes to
the oracle words of ``t0_05.json``.
"""

from __future__ import annotations

import hashlib
import html
import json
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from msgloom.a2_kedro.normalize import normalize_text
from msgloom.a2_kedro.parsers.docx import DocxResult
from msgloom.a2_kedro.parsers.mime_html import MimeParseResult
from msgloom.a2_kedro.parsers.pdf import PdfParseResult
from msgloom.a2_kedro.parsers.plain_json import ParseResult
from msgloom.a2_kedro.parsers.registry import parser_for
from msgloom.a2_kedro.parsers.spreadsheets import SheetResult
from msgloom.a2_kedro.zones import build_zones

GOLDEN = Path(__file__).resolve().parents[1] / "golden"
GOLD_FILES = ("t0_02.json", "t0_05.json")
CANARY = "CANARY-PII-7731-ZQ"

#: Oracle kind words (t0_05.json) for implementation limitation codes.
#: A code that is not listed maps to the kind ``other``, so an unknown
#: code is always visible in a comparison.
KIND_OF_CODE: dict[str, tuple[str, ...]] = {
    "no_text_layer": ("scanned",),
    "no_text": ("missing",),
    "encrypted": ("encrypted",),
    "password_required": ("encrypted",),
    "password_protected": ("encrypted",),
    # The DOCX lane cannot tell a legacy .doc from an encrypted OLE file.
    "encrypted_or_ole": ("encrypted", "unsupported"),
    "charts": ("unsupported",),
    "drawings": ("unsupported",),
    "images": ("unsupported",),
    "comments": ("unsupported",),
    "unsupported_content": ("unsupported",),
    "unsupported_format": ("unsupported",),
    "format_unsupported": ("unsupported",),
}


def manifest_digests() -> dict[str, str]:
    """Return the file name to SHA-256 table of ``MANIFEST.sha256``."""
    table: dict[str, str] = {}
    for line in (GOLDEN / "MANIFEST.sha256").read_text("utf-8").splitlines():
        digest, _, name = line.partition("  ")
        if name:
            table[name.strip()] = digest.strip()
    return table


def file_digest(name: str) -> str:
    """Return the SHA-256 of one gold file (read only)."""
    return hashlib.sha256((GOLDEN / name).read_bytes()).hexdigest()


def load_cases(name: str) -> dict[str, dict[str, Any]]:
    """Return the cases of one gold file keyed by ``case_id``."""
    data = json.loads((GOLDEN / name).read_text("utf-8"))
    return {case["case_id"]: case for case in data["cases"]}


def all_cases() -> dict[str, dict[str, Any]]:
    """Return the cases of every gold file used by V0-04."""
    cases: dict[str, dict[str, Any]] = {}
    for name in GOLD_FILES:
        cases.update(load_cases(name))
    return cases


def kinds_of(codes: Sequence[str]) -> set[str]:
    """Map implementation codes to oracle kind words."""
    found: set[str] = set()
    for code in codes:
        default = ("unsupported",) if code.startswith("unsupported_") else ("other",)
        found.update(KIND_OF_CODE.get(code, default))
    return found


def oracle_status(raw: str, codes: Sequence[str]) -> str:
    """
    Map an implementation status word to the oracle status word.

    ``complete`` stays ``complete``. ``incomplete`` is ``partial``.
    ``failed`` stays ``failed``, except when every limitation maps to the
    kind ``unsupported`` only: then it is ``unsupported``.
    """
    if raw == "incomplete":
        return "partial"
    if raw == "failed" and codes and kinds_of(codes) == {"unsupported"}:
        return "unsupported"
    return raw


@dataclass
class Seen:
    """Facts that one real parser result shows, in oracle words."""

    status: str
    codes: tuple[str, ...]
    texts: list[str] = field(default_factory=list)
    cells: dict[str, str] = field(default_factory=dict)
    pages: int = 0


@dataclass
class Cmp:
    """Compare observed facts with ``case['expected']`` and record the keys."""

    case: Mapping[str, Any]
    checked: set[str] = field(default_factory=set)
    bad: list[str] = field(default_factory=list)

    @property
    def expected(self) -> Mapping[str, Any]:
        """Return the gold expected block."""
        return self.case["expected"]  # type: ignore[no-any-return]

    def has(self, key: str) -> bool:
        """Return True when the gold block holds ``key``."""
        return key in self.expected

    def eq(self, key: str, actual: object) -> None:
        """Compare ``actual`` with the gold value of ``key``."""
        self.checked.add(key)
        if actual != self.expected[key]:
            self.bad.append(key)

    def flag(self, key: str, ok: bool) -> None:
        """Record ``key`` as checked; it is a mismatch when ``ok`` is false."""
        self.checked.add(key)
        if not ok:
            self.bad.append(key)

    def eq_map(self, key: str, actual: Mapping[str, object]) -> None:
        """Compare a gold mapping entry by entry; label each bad entry."""
        self.checked.add(key)
        for sub, want in self.expected[key].items():
            if actual.get(sub) != want:
                self.bad.append(f"{key}[{sub}]")

    def kinds(
        self, key: str, codes: Sequence[str], extra_ok: Collection[str] = ()
    ) -> None:
        """
        Compare the gold kind list with the kinds of ``codes``.

        Every gold kind must be present. Another kind is a mismatch unless
        the caller names it in ``extra_ok`` (a documented consequence).
        """
        self.checked.add(key)
        want = set(self.expected[key])
        got = kinds_of(codes)
        if not want <= got or (got - want - set(extra_ok)):
            self.bad.append(key)

    def common(self, seen: Seen, extra_ok: Sequence[str] = ()) -> None:
        """Compare the keys that most ``t0_05`` cases share."""
        if self.has("status"):
            self.eq("status", seen.status)
        if self.has("status_is_complete"):
            self.eq("status_is_complete", seen.status == "complete")
        if self.has("error_visible"):
            self.eq("error_visible", bool(seen.codes) and seen.status != "complete")
        if self.has("pages"):
            self.eq("pages", seen.pages)
        if self.has("text_present"):
            want, joined = self.expected["text_present"], "\n".join(seen.texts)
            ok = all(w in joined for w in want) if want else not joined.strip()
            self.flag("text_present", ok)
        if self.has("content_loss_limitations"):
            self.eq("content_loss_limitations", list(seen.codes))
        if self.has("limitations"):
            self.kinds("limitations", seen.codes, extra_ok)
        if self.has("cells_present"):
            refs = self.expected["cells_present"]
            self.eq_map("cells_present", {r: seen.cells.get(f"s0!{r}") for r in refs})
        if self.has("partial_content_published_as_full"):
            full = seen.status == "complete" and bool(seen.texts or seen.cells)
            self.eq("partial_content_published_as_full", full)
        if self.has("empty_text_reported_as_complete"):
            self.eq(
                "empty_text_reported_as_complete",
                seen.status == "complete" and not seen.texts,
            )


def observe(key: str, data: bytes) -> Seen:
    """Run the registry parser for ``key`` and reduce the result to ``Seen``."""
    result = parser_for(key).parse(data)
    if isinstance(result, PdfParseResult):
        codes = result.codes
        status = oracle_status(result.status.value, codes)
        texts = [page.text for page in result.pages]
        return Seen(status, codes, texts, {}, len(result.pages))
    if isinstance(result, DocxResult):
        codes = tuple(lim.code for lim in result.to_contract_limitations())
        status = oracle_status(result.status.value, codes)
        return Seen(status, codes, [block.text for block in result.blocks])
    if isinstance(result, SheetResult):
        codes = tuple(str(lim) for lim in result.limitations)
        cells = {c.block_id: str(c.value) for c in result.cells}
        return Seen(oracle_status(result.outcome.value, codes), codes, [], cells)
    pytest.fail("unexpected parser result type")


def parse_text(key: str, data: bytes) -> ParseResult:
    """Run the registry parser for ``json`` or ``plain_text``."""
    result = parser_for(key).parse(data)
    if not isinstance(result, ParseResult):
        pytest.fail(f"{key} must return ParseResult")
    return result


def parse_msg(data: bytes) -> MimeParseResult:
    """Run the registry parser for ``rfc822``."""
    result = parser_for("rfc822").parse(data)
    if not isinstance(result, MimeParseResult):
        pytest.fail("rfc822 must return MimeParseResult")
    return result


def text_parts(res: MimeParseResult, roles: tuple[str, ...]) -> dict[str, str]:
    """Return path to text of the parts with a role in ``roles``."""
    return {p.path: p.text for p in res.parts if p.role in roles and p.text}


def zone_facts(text: str, author: str) -> tuple[str, str, str]:
    """Return contributed text, quoted text and attribution lines (P2-08 zones)."""
    norm = normalize_text(text)
    res = build_zones(text, norm, part_id="1", author=author)
    data = norm.text.encode("utf-8")
    own: list[str] = []
    quoted: list[str] = []
    attribution: list[str] = []
    for zone in res.zones.zones if res.zones else ():
        piece = data[zone.normalized.start : zone.normalized.end].decode("utf-8")
        if zone.kind == "authored":
            own.append(piece)
            continue
        for line in piece.splitlines():
            if line.startswith(">"):
                quoted.append(line.lstrip(">").strip())
            else:
                attribution.append(line)
    return "".join(own).strip(), "\n".join(quoted), "\n".join(attribution)


def region_quote(res: MimeParseResult) -> str:
    """Return the quoted lines from the P2-01 ``QuotedRegion`` records."""
    lines: list[str] = []
    for part in res.parts:
        for region in part.quoted:
            piece = (part.text or "")[region.start : region.end]
            lines += [ln.lstrip(">").strip() for ln in piece.splitlines()]
    return "\n".join(lines)


def leaks(res: MimeParseResult, source_lines: list[str]) -> bool:
    """Return True when a limitation holds a word of a source body line."""
    blob = " ".join(f"{lim.code} {lim.detail}" for lim in res.limitations)
    words = [w for ln in source_lines for w in ln.split() if len(w) >= 4]
    return any(word in blob for word in words)


def span_problems(res: MimeParseResult, path: str, body: str) -> list[str]:
    """Return structural faults of the text map of part ``path``."""
    part = {p.path: p for p in res.parts}[path]
    text = part.text or ""
    out: list[str] = []
    last_t = last_s = 0
    for sp in part.text_map:
        if not last_t <= sp.text_start <= sp.text_end <= len(text):
            out.append("text range")
        if not last_s <= sp.source_start <= sp.source_end <= len(body):
            out.append("source range")
        piece = text[sp.text_start : sp.text_end]
        source = html.unescape(body[sp.source_start : sp.source_end])
        if piece.strip() and source != piece:
            out.append("source slice differs from text slice")
        last_t, last_s = sp.text_end, sp.source_end
    return out or ([] if part.text_map else ["no span"])
