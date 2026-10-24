# A2 v2 parser P2-11: static parser registry (PROVISIONAL)

Code: `msgloom/a2_kedro/parsers/registry.py`.
Tests: `tests/a2_kedro/test_parser_registry.py`.
No new dependency and no new wire name. All names are PROVISIONAL.

## Entry points

- `resolve(key: object) -> ParserEntry | ParserRefusal`. Never raises.
- `parser_for(key: object) -> ParserEntry`. Raises `ParserRefusedError`
  (an `A2ContractError`). The message is the fixed refusal code.
- `registered_keys() -> tuple[str, ...]` and `REGISTRY` (read-only).
- `build_registry(entries)`: the only builder. Raises `RegistryError` for a
  duplicate key, a key outside `ALLOWED_KEYS` or a parser that is not
  callable.

`ParserEntry(key, worker, parse)`. `parse` is the shipped function and takes
the saved component bytes. The registry does not call it.

## Keys

Registered: `rfc822` (`parse_mime`), `plain_text` (`parse_plain_text`),
`json` (`parse_json`), `pdf`, `docx`, `xlsx`. `json` is a P2-02 profile and
is not a `PartFormat`.

Known, no parser: `html`, `pptx`, `csv`, `image`. Refusal code
`format_unsupported`. Any other value: `format_unknown`. Both refusals have
status `failed` and a fixed detail. Neither holds the key.

Only an exact `str` of at most 16 characters is looked up. An enum member,
a `str` subclass, `bytes` and `None` are `format_unknown`.

## Safety

No `importlib`, `__import__`, `eval`, `exec`, entry point or `getattr` on a
name. A test walks the module AST for these names. Another test patches
them to fail and checks `sys.modules` after hostile keys.

## Open points for P1-05

- `attachments.inventory_attachments` takes a `MimeParseResult`, so it is
  not a bytes parser and is not in this table.
- A bare `html` part has no parser here. P2-01 reads HTML inside a message.
- `csv` has no parser yet (P2-05 admits XLSX and XLSM only).
- The return types differ per parser. `ParsedOutput` is their union.
