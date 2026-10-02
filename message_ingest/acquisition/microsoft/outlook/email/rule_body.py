"""Deterministic bounded logical BODY projection for Outlook Mail rules."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

from selectolax.lexbor import LexborHTMLParser, LexborNode

MAX_LOGICAL_BODY_BYTES = 8 * 1024 * 1024

_ACTIVE_TAGS = frozenset(
    {"script", "style", "noscript", "template", "iframe", "object", "embed"}
)
_BOUNDARY_TAGS = frozenset(
    {
        "address",
        "article",
        "aside",
        "blockquote",
        "caption",
        "dd",
        "div",
        "dl",
        "dt",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "li",
        "main",
        "nav",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "tbody",
        "td",
        "tfoot",
        "th",
        "thead",
        "tr",
        "ul",
    }
)
_WHITESPACE = re.compile(r"\s+")


class MailBodyUnavailable(ValueError):
    """BODY could not be represented under the fixed V1 logical-text contract."""

    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__("Outlook Mail rule body is unavailable")


def logical_mail_body(body: object) -> str:
    """Return one bounded logical text body without leaking source on failure."""

    if not isinstance(body, Mapping):
        raise MailBodyUnavailable("invalid_body_representation")
    content_type = body.get("contentType")
    content = body.get("content")
    if not isinstance(content_type, str) or not isinstance(content, str):
        raise MailBodyUnavailable("invalid_body_representation")

    kind = content_type.casefold()
    if kind == "text":
        _check_size(content)
        return content
    if kind != "html":
        raise MailBodyUnavailable("unsupported_body_content_type")

    try:
        parser = LexborHTMLParser(content)
        root = parser.body or parser.root
        if root is None:
            raise MailBodyUnavailable("html_projection_failed")
        rendered = _render(_text_pieces(root))
    except MailBodyUnavailable:
        raise
    except Exception:  # noqa: BLE001 - sanitize the parser dependency boundary.
        raise MailBodyUnavailable("html_projection_failed") from None
    _check_size(rendered)
    return rendered


def _check_size(value: str) -> None:
    if len(value.encode("utf-8")) > MAX_LOGICAL_BODY_BYTES:
        raise MailBodyUnavailable("body_too_large")


def _normal_text(value: str) -> str:
    return _WHITESPACE.sub(" ", value)


def _text_pieces(
    node: LexborNode,
    *,
    preformatted: bool = False,
) -> Iterable[tuple[str, str | None]]:
    child = node.child
    while child is not None:
        next_child = child.next
        tag = child.tag
        if tag in _ACTIVE_TAGS:
            child = next_child
            continue
        if tag == "-text":
            value = child.text(deep=False)
            yield (
                "pre" if preformatted else "normal",
                value if preformatted else _normal_text(value),
            )
            child = next_child
            continue
        if tag == "br":
            yield ("boundary", None)
            child = next_child
            continue

        is_boundary = tag in _BOUNDARY_TAGS
        if is_boundary:
            yield ("boundary", None)
        yield from _text_pieces(
            child,
            preformatted=preformatted or tag == "pre",
        )
        if is_boundary:
            yield ("boundary", None)
        child = next_child


def _render(pieces: Iterable[tuple[str, str | None]]) -> str:
    rendered: list[str] = []
    pending_boundary = False
    last_kind: str | None = None

    for kind, value in pieces:
        if kind == "boundary":
            pending_boundary = bool(rendered)
            continue
        assert value is not None
        if kind == "normal" and not value:
            continue

        if pending_boundary and rendered:
            if last_kind == "normal":
                rendered[-1] = rendered[-1].rstrip(" ")
            if rendered[-1] and not rendered[-1].endswith("\n"):
                rendered.append("\n")
            pending_boundary = False

        if kind == "normal":
            if not rendered or rendered[-1].endswith("\n"):
                value = value.lstrip(" ")
            if not value:
                continue
        rendered.append(value)
        last_kind = kind

    if rendered and last_kind == "normal":
        rendered[-1] = rendered[-1].rstrip(" ")
    return "".join(rendered)


__all__ = [
    "MAX_LOGICAL_BODY_BYTES",
    "MailBodyUnavailable",
    "logical_mail_body",
]
