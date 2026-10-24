"""
Bounded leaf collection for parsed JSON (P2-02 helper).

The walk is lazy. Each open container holds one iterator, so the stack
size follows the nesting depth, not the number of children. A path is a
linked tuple ``(parent, escaped_token)`` that shares each key string with
its children. A JSON Pointer string is built only for a leaf that the
walk keeps. The byte size of a pointer comes from the path, so a pointer
that is too large is never built.

Order of checks for a leaf: the field bound first, then the size of its
pointer. No work on a key or an index happens before the field bound.
The walk stops at the first bound it hits. The result says which bound
stopped it. Lone surrogates in keys and values become ``?``.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from msgloom.a2_kedro.parsers.json_scan import clean_surrogates

#: A path: ``None`` for the root, else ``(parent path, escaped token)``.
Path = tuple[Any, str] | None


@dataclass(frozen=True, slots=True)
class Leaves:
    """Result of :func:`collect_leaves`."""

    items: tuple[tuple[str, str | None], ...]
    field_limit: bool
    pointer_limit: bool
    surrogate: bool


def collect_leaves(
    document: Any, max_fields: int, max_pointer: int, max_total: int
) -> Leaves:
    """
    Return string and ``null`` leaves of ``document`` in document order.

    ``max_fields`` bounds the leaf count. ``max_pointer`` bounds the UTF-8
    size of one JSON Pointer. ``max_total`` bounds the summed size of all
    kept pointers. The walk stops at the first bound it hits.
    """
    items: list[tuple[str, str | None]] = []
    total = 0
    surrogate = False
    if not isinstance(document, (dict, list)):
        if document is None or isinstance(document, str):
            value = clean_surrogates(document)
            items.append(("", value))
            surrogate = value != document
        return Leaves(tuple(items), False, False, surrogate)
    stack: list[tuple[Path, int, Iterator[tuple[Any, Any]]]] = [
        (None, 0, _children(document))
    ]
    while stack:
        path, size, children = stack[-1]
        entry = next(children, None)
        if entry is None:
            stack.pop()
            continue
        token, child = entry
        is_container = isinstance(child, (dict, list))
        if not is_container and child is not None and not isinstance(child, str):
            continue
        if not is_container and len(items) >= max_fields:
            return Leaves(tuple(items), True, False, surrogate)
        text, dirty = _token(token)
        surrogate = surrogate or dirty
        step = size + 1 + _byte_len(text)
        here: Path = (path, text)
        if is_container:
            stack.append((here, step, _children(child)))
            continue
        if step > max_pointer or total + step > max_total:
            return Leaves(tuple(items), False, True, surrogate)
        total += step
        value = clean_surrogates(child)
        surrogate = surrogate or value != child
        items.append((_pointer(here), value))
    return Leaves(tuple(items), False, False, surrogate)


def find_key(mapping: dict[str, Any], token: str) -> str | None:
    """
    Return the key of ``mapping`` that ``token`` names, else ``None``.

    An exact key wins. Else a key whose cleaned form equals ``token``
    matches, so a pointer from :func:`collect_leaves` finds its key.
    """
    if token in mapping:
        return token
    for key in mapping:
        if not key.isascii() and clean_surrogates(key) == token:
            return key
    return None


def _children(node: Any) -> Iterator[tuple[Any, Any]]:
    return iter(node.items()) if isinstance(node, dict) else enumerate(node)


def _token(token: Any) -> tuple[str, bool]:
    """Return the escaped token text and whether a surrogate was cleaned."""
    if isinstance(token, int):
        return str(token), False
    cleaned = clean_surrogates(token)
    return cleaned.replace("~", "~0").replace("/", "~1"), cleaned != token


def _byte_len(text: str) -> int:
    return len(text) if text.isascii() else len(text.encode("utf-8"))


def _pointer(path: Path) -> str:
    tokens: list[str] = []
    while path is not None:
        path, token = path
        tokens.append(token)
    return "".join(f"/{token}" for token in reversed(tokens))
