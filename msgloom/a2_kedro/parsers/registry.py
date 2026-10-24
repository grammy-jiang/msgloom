"""
Static parser registry (P2-11): closed format key to trusted parser.

:func:`resolve` maps one format key to the parser that this repository
ships for it. The key is data from a provider or from a saved record, so
it is never trusted. The registry is a fixed table that is built once at
import time. A key either matches an entry of the table or it is refused.

No dynamic dispatch: the module does not use ``importlib``, ``__import__``,
``eval``, ``exec``, entry points or ``getattr`` on a name. The parser
callables are imported by name at the top of this module. A hostile key
such as ``"os.system"`` is only a string that is not in the table.

Keys: the registered keys are ``rfc822``, ``plain_text``, ``json``, ``pdf``,
``docx`` and ``xlsx``. ``json`` is a profile of the P2-02 parser and is not
a :data:`~msgloom.a2_kedro.contracts.parse.PartFormat`. The formats
``html``, ``pptx``, ``csv`` and ``image`` are known but have no parser
here. They get the ``format_unsupported`` refusal. Any other value gets the
``format_unknown`` refusal. ``html`` is read inside a message by the P2-01
parser, so a bare ``html`` part is not routed to a parser by this table.

Key rule: only an exact :class:`str` matches. A subclass of ``str`` (for
example an enum member), ``bytes``, ``None`` and any other type get
``format_unknown``. A subclass could change ``__eq__`` or ``__hash__``.
A key longer than :data:`MAX_KEY_CHARS` is refused before any lookup.

Failure handling: :func:`resolve` never raises. A refusal is a frozen
:class:`ParserRefusal` with a ``failed`` status and a fixed
:class:`~msgloom.contracts.Limitation`. The refusal never holds the key or
any part of it. :func:`parser_for` raises :exc:`ParserRefusedError` for a
caller that prefers an exception. Its message is the fixed refusal code.

Immutability: ``REGISTRY`` is a :class:`~types.MappingProxyType` over a
dict that :func:`build_registry` made from a tuple of frozen entries. The
builder rejects a duplicate key, a key outside :data:`ALLOWED_KEYS` and a
parser that is not callable. No module name holds the dict itself.

The registry does not call a parser. The caller passes the saved bytes to
``entry.parse`` and keeps the format rule of ``parse.py``: the declared and
the detected format must match before a key is resolved.

CANDIDATE/RESEARCH, PROVISIONAL: see ``docs/notes/a2-v2-parser-p2-11.md``.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from msgloom.a2_kedro.contracts.codec import A2ContractError
from msgloom.a2_kedro.parsers import docx, mime_html, pdf, plain_json, spreadsheets
from msgloom.a2_kedro.parsers.docx import DocxResult, parse_docx
from msgloom.a2_kedro.parsers.mime_html import MimeParseResult, parse_mime
from msgloom.a2_kedro.parsers.pdf import PdfParseResult, parse_pdf
from msgloom.a2_kedro.parsers.plain_json import (
    ParseResult,
    parse_json,
    parse_plain_text,
)
from msgloom.a2_kedro.parsers.spreadsheets import SheetResult, parse_spreadsheet
from msgloom.contracts import Limitation, TerminalStatus

#: Result of any registered parser. Each type has its own module contract.
ParsedOutput = MimeParseResult | ParseResult | PdfParseResult | DocxResult | SheetResult
#: Every registered parser takes the saved component bytes.
ParserFn = Callable[[bytes], ParsedOutput]

#: Registered keys: the ``PartFormat`` values with a parser, plus ``json``.
REGISTERED_KEYS: tuple[str, ...] = (
    "rfc822",
    "plain_text",
    "json",
    "pdf",
    "docx",
    "xlsx",
)
#: ``PartFormat`` values that are known but have no parser in this table.
UNSUPPORTED_KEYS: frozenset[str] = frozenset({"html", "pptx", "csv", "image"})
#: The closed allowlist. A table entry must use one of these keys.
ALLOWED_KEYS: frozenset[str] = frozenset(REGISTERED_KEYS) | UNSUPPORTED_KEYS
#: Longest allowed key. A longer value cannot match and is not hashed.
MAX_KEY_CHARS = 16

UNKNOWN_CODE = "format_unknown"
UNSUPPORTED_CODE = "format_unsupported"
_DETAIL = {
    UNKNOWN_CODE: "The format key is not in the parser registry.",
    UNSUPPORTED_CODE: "The format is known, but no parser is registered for it.",
}


class RegistryError(A2ContractError):
    """Raised at build time for a bad table. The message is fixed text."""


class ParserRefusedError(A2ContractError):
    """Raised by :func:`parser_for`. The message is the refusal code."""

    def __init__(self, refusal: ParserRefusal) -> None:
        super().__init__(refusal.limitation.code)
        self.refusal = refusal


@dataclass(frozen=True, slots=True)
class ParserEntry:
    """One trusted table row: a key, a worker name and a parser callable."""

    key: str
    worker: str
    parse: ParserFn


@dataclass(frozen=True, slots=True)
class ParserRefusal:
    """
    Typed refusal of one key. It holds no part of the key.

    ``status`` is always ``failed``: no parser ran and no result exists.
    """

    status: TerminalStatus
    limitation: Limitation


def build_registry(entries: Iterable[ParserEntry]) -> Mapping[str, ParserEntry]:
    """
    Return a read-only table of ``entries`` keyed by ``entry.key``.

    Raise :exc:`RegistryError` for a key outside :data:`ALLOWED_KEYS`, a
    key that is not an exact ``str``, a duplicate key or a parser that is
    not callable. The messages are fixed and never contain a key.
    """
    table: dict[str, ParserEntry] = {}
    for entry in entries:
        if type(entry.key) is not str or entry.key not in ALLOWED_KEYS:
            raise RegistryError("registry key is not in the allowlist")
        if entry.key in table:
            raise RegistryError("registry key is registered twice")
        if not callable(entry.parse):
            raise RegistryError("registry parser is not callable")
        table[entry.key] = entry
    return MappingProxyType(table)


#: The only table. Entries name functions that this module imports above.
REGISTRY: Mapping[str, ParserEntry] = build_registry(
    (
        ParserEntry("rfc822", mime_html.WORKER, parse_mime),
        ParserEntry("plain_text", plain_json.WORKER, parse_plain_text),
        ParserEntry("json", plain_json.WORKER, parse_json),
        ParserEntry("pdf", pdf.WORKER, parse_pdf),
        ParserEntry("docx", docx.WORKER, parse_docx),
        ParserEntry("xlsx", spreadsheets.WORKER, parse_spreadsheet),
    )
)


def registered_keys() -> tuple[str, ...]:
    """Return the registered keys in table order."""
    return tuple(REGISTRY)


def _refuse(code: str) -> ParserRefusal:
    return ParserRefusal(TerminalStatus.FAILED, Limitation(code, _DETAIL[code]))


def resolve(key: object) -> ParserEntry | ParserRefusal:
    """
    Return the entry for ``key``, or a :class:`ParserRefusal`.

    Never raises, for any value of ``key``. Only an exact ``str`` of
    at most :data:`MAX_KEY_CHARS` characters is looked up.
    """
    if type(key) is not str or len(key) > MAX_KEY_CHARS:
        return _refuse(UNKNOWN_CODE)
    if (entry := REGISTRY.get(key)) is not None:
        return entry
    return _refuse(UNSUPPORTED_CODE if key in UNSUPPORTED_KEYS else UNKNOWN_CODE)


def parser_for(key: object) -> ParserEntry:
    """Return the entry for ``key`` or raise :exc:`ParserRefusedError`."""
    found = resolve(key)
    if isinstance(found, ParserRefusal):
        raise ParserRefusedError(found)
    return found
