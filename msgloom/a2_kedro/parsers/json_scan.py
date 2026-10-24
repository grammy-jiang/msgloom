"""
Linear nesting-depth scan for JSON text (P2-02 helper).

One forward pass. Every step moves the position forward, so the cost is
O(n). The scan never rescans: an unterminated string or a trailing lone
backslash ends the input. It does not validate JSON.
"""

from __future__ import annotations

import re
from typing import Any

_OUTSIDE = re.compile(r'["\[\]{}]')
_INSIDE = re.compile(r'["\\]')


def exceeds_depth(text: str, limit: int) -> bool:
    """Return ``True`` when bracket nesting outside strings passes ``limit``."""
    depth = 0
    pos = 0
    size = len(text)
    while pos < size:
        hit = _OUTSIDE.search(text, pos)
        if hit is None:
            return False
        char = hit.group()
        pos = hit.end()
        if char == '"':
            pos = _string_end(text, pos)
        elif char in "[{":
            depth += 1
            if depth > limit:
                return True
        else:
            depth = max(depth - 1, 0)
    return False


def _string_end(text: str, pos: int) -> int:
    """Return the position after the string that starts before ``pos``."""
    size = len(text)
    while pos < size:
        hit = _INSIDE.search(text, pos)
        if hit is None:
            return size
        if hit.group() == '"':
            return hit.end()
        pos = hit.end() + 1  # skip the escaped character
    return size


def clean_surrogates(node: Any) -> Any:
    """Replace lone surrogates in a string with ``?``. Other nodes pass."""
    if isinstance(node, str) and not node.isascii():
        return node.encode("utf-8", "replace").decode("utf-8")
    return node
