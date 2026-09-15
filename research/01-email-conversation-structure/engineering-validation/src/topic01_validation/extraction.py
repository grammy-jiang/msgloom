"""Deterministic body extraction and structural quote detection baselines.

These functions are intentionally small research baselines, not production MIME or
HTML parsers. Their known limitations are part of E2's experiment output.
"""
from __future__ import annotations

from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser
from typing import Iterable

from .models import Span


@dataclass(frozen=True)
class ExtractedBody:
    text: str
    quote_spans: tuple[Span, ...]
    content_type: str
    warnings: tuple[str, ...] = ()


class _HTMLTextExtractor(HTMLParser):
    BLOCK_BREAKS = {"p", "div", "br", "tr", "li", "table", "blockquote"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.quote_depth = 0
        self._quote_starts: list[int] = []
        self.quote_ranges: list[tuple[int, int]] = []

    @property
    def pos(self) -> int:
        return len("".join(self.parts))

    def _newline(self) -> None:
        if self.parts and not self.parts[-1].endswith("\n"):
            self.parts.append("\n")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "blockquote":
            self._newline()
            self._quote_starts.append(self.pos)
            self.quote_depth += 1
        elif tag in self.BLOCK_BREAKS:
            self._newline()
        elif tag in {"td", "th"}:
            if self.parts and not self.parts[-1].endswith(("\n", " | ")):
                self.parts.append(" | ")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "blockquote":
            self._newline()
            if self._quote_starts:
                start = self._quote_starts.pop()
                self.quote_ranges.append((start, self.pos))
            self.quote_depth = max(0, self.quote_depth - 1)
        elif tag in self.BLOCK_BREAKS:
            self._newline()

    def handle_data(self, data: str) -> None:
        # Preserve textual evidence; collapse runs inside each HTML text node only.
        text = " ".join(data.split())
        if not text:
            return
        if self.parts and not self.parts[-1].endswith(("\n", " ", " | ")):
            self.parts.append(" ")
        self.parts.append(text)

    def result(self) -> ExtractedBody:
        text = "".join(self.parts)
        # Normalize excessive blank lines without changing non-newline characters.
        while "\n\n\n" in text:
            text = text.replace("\n\n\n", "\n\n")
        text = text.strip("\n")
        ranges: list[Span] = []
        # Ranges were measured before final strip; our fixtures do not start with a
        # blockquote, but guard against any leading newlines if they do.
        for start, end in self.quote_ranges:
            start = min(start, len(text))
            end = min(end, len(text))
            if end > start:
                ranges.append(Span(start, end))
        return ExtractedBody(text=text, quote_spans=tuple(sorted(ranges)), content_type="text/html")


def _quote_spans_plain(text: str) -> tuple[Span, ...]:
    """Detect contiguous RFC-style `>` quoted line blocks."""
    spans: list[Span] = []
    cursor = 0
    block_start: int | None = None
    block_end: int | None = None
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip(" ")
        is_quote = stripped.startswith(">")
        if is_quote:
            if block_start is None:
                block_start = cursor
            block_end = cursor + len(line.rstrip("\r\n"))
        elif block_start is not None:
            spans.append(Span(block_start, block_end if block_end is not None else cursor))
            block_start = block_end = None
        cursor += len(line)
    if block_start is not None:
        spans.append(Span(block_start, block_end if block_end is not None else len(text)))
    return tuple(spans)


def unquote_plain(text: str) -> str:
    """Remove one or more leading quote markers from each line for matching."""
    out: list[str] = []
    for line in text.splitlines():
        s = line.lstrip(" ")
        while s.startswith(">"):
            s = s[1:]
            if s.startswith(" "):
                s = s[1:]
        out.append(s)
    return "\n".join(out).strip()


def _flowed_normalize(text: str, *, delsp: bool) -> str:
    """Small RFC 3676-oriented baseline for quote-aware flowed text.

    It preserves quote markers for structural detection. This is intentionally not
    a full standards implementation; synthetic cases exercise space-stuffing and
    flowed joins and record any limitations.
    """
    logical: list[str] = []
    pending: str | None = None
    pending_prefix = ""
    for raw in text.splitlines():
        line = raw
        # Space-stuffing is removed after quote-depth parsing in the RFC. Here we
        # keep quote markers and unstuff only the content after them.
        prefix = ""
        rest = line
        while rest.startswith(">"):
            prefix += ">"
            rest = rest[1:]
        if rest.startswith(" "):
            rest = rest[1:]
        soft = rest.endswith(" ") and rest != "-- "
        if soft:
            rest = rest[:-1] if delsp else rest
        current = prefix + (" " if prefix and rest else "") + rest
        if pending is None:
            pending = current
            pending_prefix = prefix
        elif prefix == pending_prefix:
            # Join flowed physical lines at same quote depth.
            pending += current[len(prefix) + (1 if prefix and rest else 0) :]
        else:
            logical.append(pending)
            pending = current
            pending_prefix = prefix
        if not soft:
            logical.append(pending)
            pending = None
            pending_prefix = ""
    if pending is not None:
        logical.append(pending)
    return "\n".join(logical)


def extract_body(raw_rfc822: bytes) -> ExtractedBody:
    msg = BytesParser(policy=policy.default).parsebytes(raw_rfc822)
    warnings: list[str] = []

    def decode_part(part) -> tuple[str, str]:
        ctype = part.get_content_type()
        try:
            content = part.get_content()
        except Exception as exc:  # pragma: no cover - defensive research harness
            payload = part.get_payload(decode=True) or b""
            content = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
            warnings.append(f"content decode fallback: {exc}")
        return str(content), ctype

    chosen_text = ""
    chosen_type = ""
    if msg.is_multipart():
        plain = None
        html = None
        for part in msg.walk():
            if part.is_multipart():
                continue
            text, ctype = decode_part(part)
            if ctype == "text/plain" and plain is None:
                plain = (text, part)
            elif ctype == "text/html" and html is None:
                html = (text, part)
        if plain is not None:
            chosen_text, part = plain
            chosen_type = "text/plain"
            params = {k.lower(): v for k, v in part.get_params()[1:]}
            if str(params.get("format", "")).lower() == "flowed":
                chosen_text = _flowed_normalize(
                    chosen_text,
                    delsp=str(params.get("delsp", "no")).lower() == "yes",
                )
        elif html is not None:
            chosen_text, _ = html
            chosen_type = "text/html"
        else:
            warnings.append("no text/plain or text/html body")
    else:
        chosen_text, chosen_type = decode_part(msg)
        params = {k.lower(): v for k, v in msg.get_params()[1:]}
        if chosen_type == "text/plain" and str(params.get("format", "")).lower() == "flowed":
            chosen_text = _flowed_normalize(
                chosen_text,
                delsp=str(params.get("delsp", "no")).lower() == "yes",
            )

    chosen_text = chosen_text.replace("\r\n", "\n").rstrip("\n")
    if chosen_type == "text/html":
        parser = _HTMLTextExtractor()
        parser.feed(chosen_text)
        result = parser.result()
        return ExtractedBody(result.text, result.quote_spans, result.content_type, tuple(warnings))
    return ExtractedBody(chosen_text, _quote_spans_plain(chosen_text), chosen_type or "unknown", tuple(warnings))


def quote_texts(body: ExtractedBody) -> tuple[str, ...]:
    out: list[str] = []
    for span in body.quote_spans:
        text = span.extract(body.text)
        out.append(unquote_plain(text) if body.content_type == "text/plain" else text.strip())
    return tuple(out)
