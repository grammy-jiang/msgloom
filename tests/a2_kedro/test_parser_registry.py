"""P2-11 static parser registry: dispatch, refusal, immutability, no import."""

from __future__ import annotations

import ast
import builtins
import dataclasses
import importlib
import inspect
import sys
from collections.abc import Callable
from enum import StrEnum
from typing import Any, get_args

import pytest

from msgloom.a2_kedro.contracts.codec import A2ContractError
from msgloom.a2_kedro.contracts.parse import PartFormat
from msgloom.a2_kedro.parsers import registry
from msgloom.a2_kedro.parsers.docx import DocxResult, parse_docx
from msgloom.a2_kedro.parsers.mime_html import MimeParseResult, parse_mime
from msgloom.a2_kedro.parsers.pdf import PdfParseResult, parse_pdf
from msgloom.a2_kedro.parsers.plain_json import (
    ParseResult,
    parse_json,
    parse_plain_text,
)
from msgloom.a2_kedro.parsers.registry import (
    ALLOWED_KEYS,
    MAX_KEY_CHARS,
    REGISTRY,
    ParserEntry,
    ParserRefusal,
    ParserRefusedError,
    RegistryError,
    build_registry,
    parser_for,
    registered_keys,
    resolve,
)
from msgloom.a2_kedro.parsers.spreadsheets import SheetResult, parse_spreadsheet
from msgloom.contracts import TerminalStatus
from tests.a2_kedro.helpers import check

SENTINEL = "alice.private@example.invalid"
EXPECTED_KEYS = ("rfc822", "plain_text", "json", "pdf", "docx", "xlsx")
UNSUPPORTED = ("html", "pptx", "csv", "image")
MESSAGE = b"From: a@example.invalid\r\nSubject: s\r\n\r\nhello"
HOSTILE = (
    "os.system",
    "../x",
    "..\\x",
    "msgloom.a2_kedro.parsers.pdf.parse_pdf",
    "msgloom.a2_kedro.parsers.pdf:parse_pdf",
    "__import__('os')",
    "subprocess",
    "builtins.eval",
    "pdf.parse_pdf",
    "pdf\x00",
    "pdf\n",
    " pdf",
    "pdf ",
    "PDF",
    "Pdf",
    "",
    SENTINEL,
    "x" * 100_000,
)
SAMPLES: dict[str, tuple[bytes, type]] = {
    "rfc822": (MESSAGE, MimeParseResult),
    "plain_text": (b"hello\n", ParseResult),
    "json": (b'{"a": "b"}', ParseResult),
    "pdf": (b"not a pdf", PdfParseResult),
    "docx": (b"not a package", DocxResult),
    "xlsx": (b"not a workbook", SheetResult),
}
PARSERS: dict[str, Callable[..., Any]] = {
    "rfc822": parse_mime,
    "plain_text": parse_plain_text,
    "json": parse_json,
    "pdf": parse_pdf,
    "docx": parse_docx,
    "xlsx": parse_spreadsheet,
}


class Fmt(StrEnum):
    """A str-compatible enum whose members equal and hash like the keys."""

    PDF = "pdf"
    DOCX = "docx"


class AlwaysEqual(str):
    """A hostile ``str`` subclass that claims to equal every key."""

    __slots__ = ()

    def __eq__(self, other: object) -> bool:
        return True

    def __hash__(self) -> int:
        return hash("pdf")


def refuses_all_hostile(lookup: Callable[[object], object]) -> bool:
    """Return whether ``lookup`` refuses every hostile or wrong-type key."""
    keys: list[object] = [*HOSTILE, None, 1, b"pdf", ["pdf"], ("pdf",), {}, object()]
    keys += [Fmt.PDF, AlwaysEqual("zzz"), AlwaysEqual("pdf")]
    return all(isinstance(lookup(key), ParserRefusal) for key in keys)


# --- positive dispatch ------------------------------------------------------


def test_registered_keys_are_exactly_the_closed_set() -> None:
    check(registered_keys() == EXPECTED_KEYS, "registered keys changed")
    check(tuple(REGISTRY) == EXPECTED_KEYS, "table keys changed")
    check(
        ALLOWED_KEYS == frozenset(EXPECTED_KEYS) | frozenset(UNSUPPORTED),
        "allowlist is not the closed set",
    )
    check(all(type(k) is str for k in ALLOWED_KEYS), "allowlist holds a non-str key")


def test_every_part_format_is_registered_or_known_unsupported() -> None:
    formats = set(get_args(PartFormat))
    covered = (set(EXPECTED_KEYS) | set(UNSUPPORTED)) - {"json"}
    check(formats == covered, "PartFormat and registry coverage differ")
    check("json" not in formats, "json became a PartFormat; review the registry")


@pytest.mark.parametrize("key", EXPECTED_KEYS)
def test_resolve_returns_the_shipped_parser(key: str) -> None:
    entry = resolve(key)
    check(isinstance(entry, ParserEntry), "key did not resolve")
    if not isinstance(entry, ParserEntry):
        return
    check(entry.key == key, "entry key differs")
    check(entry.parse is PARSERS[key], "entry is not the shipped parser")
    check(entry is REGISTRY[key], "resolve did not return the table entry")
    check(parser_for(key) is entry, "parser_for differs from resolve")
    check(entry.worker.startswith("msgloom."), "worker name is not set")


@pytest.mark.parametrize("key", EXPECTED_KEYS)
def test_dispatch_runs_the_parser_and_returns_its_result_type(key: str) -> None:
    data, kind = SAMPLES[key]
    entry = parser_for(key)
    result = entry.parse(data)
    check(isinstance(result, kind), "parser returned another result type")
    check(result == PARSERS[key](data), "dispatch result differs from direct call")


def test_json_and_plain_text_share_a_worker_but_not_a_parser() -> None:
    check(
        parser_for("json").worker == parser_for("plain_text").worker,
        "P2-02 worker name differs",
    )
    check(parser_for("json").parse is not parser_for("plain_text").parse, "same fn")
    check(parser_for("json").parse(b"{").format == "json", "json profile lost")  # type: ignore[union-attr]


def test_entry_signature_matches_a_bytes_parser() -> None:
    for entry in REGISTRY.values():
        params = list(inspect.signature(entry.parse).parameters.values())
        check(params[0].kind is params[0].POSITIONAL_OR_KEYWORD, "first arg kind")
        required = [p for p in params if p.default is p.empty]
        check(len(required) == 1, "a parser needs more than the component bytes")


# --- refusal ----------------------------------------------------------------


@pytest.mark.parametrize("key", UNSUPPORTED)
def test_known_unsupported_format_is_refused_as_unsupported(key: str) -> None:
    refusal = resolve(key)
    check(isinstance(refusal, ParserRefusal), "unsupported format resolved")
    if not isinstance(refusal, ParserRefusal):
        return
    check(refusal.status is TerminalStatus.FAILED, "refusal status")
    check(refusal.limitation.code == "format_unsupported", "refusal code")
    check(key not in refusal.limitation.detail, "detail echoes the key")


def test_unknown_key_is_refused_as_unknown() -> None:
    refusal = resolve("telnet")
    check(isinstance(refusal, ParserRefusal), "unknown key resolved")
    if not isinstance(refusal, ParserRefusal):
        return
    check(refusal.status is TerminalStatus.FAILED, "refusal status")
    check(refusal.limitation.code == "format_unknown", "refusal code")
    check(refusal.limitation.detail != "", "refusal detail is empty")


@pytest.mark.parametrize(
    "key",
    [None, 1, 1.5, True, b"pdf", bytearray(b"pdf"), ["pdf"], ("pdf",), {}, object()],
)
def test_wrong_type_key_is_refused(key: object) -> None:
    refusal = resolve(key)
    check(isinstance(refusal, ParserRefusal), "wrong type key resolved")
    if isinstance(refusal, ParserRefusal):
        check(refusal.limitation.code == "format_unknown", "refusal code")


def test_str_subclass_and_enum_keys_are_refused() -> None:
    check(Fmt.PDF == "pdf" and hash(Fmt.PDF) == hash("pdf"), "enum is not str-like")
    check(isinstance(resolve(Fmt.PDF), ParserRefusal), "enum member resolved")
    check(isinstance(resolve(Fmt.DOCX), ParserRefusal), "enum member resolved")
    check(isinstance(resolve(AlwaysEqual("pdf")), ParserRefusal), "subclass")
    check(isinstance(resolve(AlwaysEqual("zzz")), ParserRefusal), "subclass")
    check(isinstance(resolve(AlwaysEqual("html")), ParserRefusal), "subclass")
    check(
        resolve(AlwaysEqual("html")).limitation.code == "format_unknown",  # type: ignore[union-attr]
        "subclass reached the unsupported branch",
    )


@pytest.mark.parametrize("key", HOSTILE)
def test_hostile_key_is_refused_without_an_exception(key: str) -> None:
    check(isinstance(resolve(key), ParserRefusal), "hostile key resolved")
    with pytest.raises(ParserRefusedError):
        parser_for(key)


@pytest.mark.parametrize(
    "key", ["pdf\x00", "pdf\n", " pdf", "pdf ", "PDF", "pdf.", "pdf/", "xlsx\u200b"]
)
def test_near_miss_keys_do_not_match(key: str) -> None:
    check(isinstance(resolve(key), ParserRefusal), "near miss resolved")


def test_long_key_is_refused_before_lookup() -> None:
    key = "p" * (MAX_KEY_CHARS + 1)
    check(isinstance(resolve(key), ParserRefusal), "long key resolved")
    check(max(len(k) for k in ALLOWED_KEYS) <= MAX_KEY_CHARS, "limit below a key")


def test_refusal_and_error_never_carry_the_key() -> None:
    for key in (SENTINEL, "os.system", "../x"):
        refusal = resolve(key)
        check(isinstance(refusal, ParserRefusal), "hostile key resolved")
        if not isinstance(refusal, ParserRefusal):
            return
        with pytest.raises(ParserRefusedError) as raised:
            parser_for(key)
        texts = [
            repr(refusal),
            str(refusal.limitation),
            str(raised.value),
            repr(raised.value),
            repr(raised.value.args),
            repr(raised.value.refusal),
        ]
        for text in texts:
            check(key not in text, "output echoes the key")
            check("alice" not in text, "output echoes key content")
        check(str(raised.value) == "format_unknown", "error is not the fixed code")
        check(isinstance(raised.value, A2ContractError), "error base type")


def test_refusal_text_is_fixed_for_every_unknown_key() -> None:
    texts = {repr(resolve(key)) for key in HOSTILE if len(key) <= MAX_KEY_CHARS}
    check(len(texts) == 1, "refusal text depends on the key")


# --- no dynamic import ------------------------------------------------------


def test_hostile_keys_import_nothing() -> None:
    def forbidden(*args: object, **kwargs: object) -> object:
        raise RuntimeError("import attempted")

    names = ("__import__", "eval", "exec", "getattr")
    saved = {name: getattr(builtins, name) for name in names}
    real_import_module = importlib.import_module
    keys = (*HOSTILE, None, Fmt.PDF, *EXPECTED_KEYS, *UNSUPPORTED)
    before = set(sys.modules)
    results: list[object] = []
    failure: BaseException | None = None
    # Patch by hand: monkeypatch itself imports modules while it runs.
    importlib.import_module = forbidden  # type: ignore[assignment]
    for name in names:
        setattr(builtins, name, forbidden)
    try:
        for key in keys:
            results.append(resolve(key))
    except BaseException as error:  # noqa: BLE001 - reported below
        failure = error
    finally:
        for name, original in saved.items():
            setattr(builtins, name, original)
        importlib.import_module = real_import_module
    check(failure is None, "a lookup used a forbidden call")
    check(set(sys.modules) == before, "a lookup changed sys.modules")
    check(len(results) == len(keys), "a lookup was skipped")
    check(
        sum(isinstance(r, ParserEntry) for r in results) == len(EXPECTED_KEYS),
        "registered keys did not resolve under the patch",
    )


def test_registry_source_has_no_dynamic_dispatch() -> None:
    source = inspect.getsource(registry)
    tree = ast.parse(source)
    banned = {"importlib", "__import__", "eval", "exec", "getattr", "setattr"}
    banned |= {"import_module", "entry_points", "compile", "globals", "locals"}
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    check(not (names | attrs) & banned, "dynamic dispatch name in registry.py")
    modules = {
        alias.name
        for n in ast.walk(tree)
        if isinstance(n, ast.Import)
        for alias in n.names
    }
    modules |= {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    check(
        all(
            m.split(".")[0]
            in {"__future__", "collections", "dataclasses", "types", "msgloom"}
            for m in modules
        ),
        "registry imports a module outside the expected set",
    )


# --- immutability and build-time rules --------------------------------------


def test_table_cannot_be_changed() -> None:
    entry = REGISTRY["pdf"]
    with pytest.raises(TypeError):
        REGISTRY["os.system"] = entry  # type: ignore[index]
    with pytest.raises(TypeError):
        REGISTRY["pdf"] = parser_for("docx")  # type: ignore[index]
    with pytest.raises(TypeError):
        del REGISTRY["pdf"]  # type: ignore[attr-defined]
    with pytest.raises(AttributeError):
        REGISTRY.update({})  # type: ignore[attr-defined]
    check(registered_keys() == EXPECTED_KEYS, "table changed")
    check(REGISTRY["pdf"] is entry, "entry changed")


def test_entry_and_refusal_are_frozen() -> None:
    entry = parser_for("pdf")
    with pytest.raises(dataclasses.FrozenInstanceError):
        entry.parse = parse_docx  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        entry.key = "os.system"  # type: ignore[misc]
    refusal = resolve("telnet")
    with pytest.raises(dataclasses.FrozenInstanceError):
        refusal.status = TerminalStatus.COMPLETE  # type: ignore[misc, union-attr]


def test_registered_keys_returns_a_copy() -> None:
    keys = registered_keys()
    check(isinstance(keys, tuple), "keys are not a tuple")
    check(registered_keys() == keys, "keys differ between calls")


def test_build_registry_returns_a_read_only_table() -> None:
    table = build_registry([ParserEntry("pdf", "w", parse_pdf)])
    check(list(table) == ["pdf"], "builder key set")
    with pytest.raises(TypeError):
        table["docx"] = ParserEntry("docx", "w", parse_docx)  # type: ignore[index]


def test_build_registry_rejects_a_duplicate_key() -> None:
    entries = [ParserEntry("pdf", "a", parse_pdf), ParserEntry("pdf", "b", parse_pdf)]
    with pytest.raises(RegistryError) as raised:
        build_registry(entries)
    check("pdf" not in str(raised.value), "duplicate message echoes the key")
    check(isinstance(raised.value, A2ContractError), "error base type")


@pytest.mark.parametrize("key", ["os.system", "../x", "PDF", "", "telnet", SENTINEL])
def test_build_registry_rejects_a_key_outside_the_allowlist(key: str) -> None:
    with pytest.raises(RegistryError) as raised:
        build_registry([ParserEntry(key, "w", parse_pdf)])
    check(key not in str(raised.value) or key == "", "build message echoes the key")
    check("alice" not in str(raised.value), "build message echoes key content")


def test_build_registry_rejects_a_non_str_key_and_a_bad_parser() -> None:
    with pytest.raises(RegistryError):
        build_registry([ParserEntry(Fmt.PDF, "w", parse_pdf)])
    with pytest.raises(RegistryError):
        build_registry([ParserEntry(AlwaysEqual("pdf"), "w", parse_pdf)])
    with pytest.raises(RegistryError):
        build_registry([ParserEntry(None, "w", parse_pdf)])  # type: ignore[arg-type]
    with pytest.raises(RegistryError):
        build_registry([ParserEntry("pdf", "w", "os.system")])  # type: ignore[arg-type]


def test_build_registry_accepts_an_unsupported_key_only_if_allowed() -> None:
    # An allowed key may be registered by a later task. The allowlist decides.
    table = build_registry([ParserEntry("csv", "w", parse_spreadsheet)])
    check(list(table) == ["csv"], "allowed key was not accepted")
    check(build_registry([]) == {}, "empty table")


# --- mutation checks: the tests above must catch a widened registry ---------


def test_hostile_battery_passes_the_real_lookup() -> None:
    check(refuses_all_hostile(resolve), "real lookup accepts a hostile key")


def test_mutant_that_accepts_any_str_is_caught() -> None:
    def any_str(key: object) -> object:
        if isinstance(key, str):
            return REGISTRY["pdf"]
        return resolve(key)

    check(not refuses_all_hostile(any_str), "battery missed an any-str mutant")


def test_mutant_that_accepts_str_subclasses_is_caught() -> None:
    def isinstance_lookup(key: object) -> object:
        if isinstance(key, str) and key in REGISTRY:
            return REGISTRY[key]
        return resolve(key)

    check(not refuses_all_hostile(isinstance_lookup), "battery missed subclass")


def test_mutant_that_resolves_dotted_names_is_caught() -> None:
    def dotted(key: object) -> object:
        if isinstance(key, str) and "." in key:
            return REGISTRY["pdf"]
        return resolve(key)

    check(not refuses_all_hostile(dotted), "battery missed a dotted-name mutant")


def test_widened_allowlist_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    widened = ALLOWED_KEYS | {"os.system"}
    monkeypatch.setattr(registry, "ALLOWED_KEYS", widened)
    table = registry.build_registry([ParserEntry("os.system", "w", parse_pdf)])
    check(list(table) == ["os.system"], "mutant did not widen the builder")
    monkeypatch.undo()
    check(ALLOWED_KEYS != widened, "allowlist stayed widened")
    check(
        ALLOWED_KEYS == frozenset(EXPECTED_KEYS) | frozenset(UNSUPPORTED),
        "exact-allowlist test would not fail on a widened allowlist",
    )
    with pytest.raises(RegistryError):
        build_registry([ParserEntry("os.system", "w", parse_pdf)])


def test_mutant_that_drops_the_length_bound_still_refuses_long_keys() -> None:
    # The bound is an optimization. The table must refuse a long key anyway.
    key = "x" * 100_000
    check(key not in REGISTRY, "long key is in the table")
    check(isinstance(resolve(key), ParserRefusal), "long key resolved")
