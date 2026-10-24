# A2 v2 closed registry factory (C0-21a)

Status: CANDIDATE/RESEARCH. Not wired into the product path.

## What was added

- `msgloom/persistence/a2_registry.py`
- `tests/persistence/test_a2_registry_schema.py`

The module adds two factories. Each call returns a new object.

- `build_a2_result_schema_registry()` returns an `A2ResultSchemaRegistry`.
  It is a subclass of `ResultSchemaRegistry`.
- `build_a2_semantic_registry()` returns an `A2SemanticDataRegistry`.
  It is a subclass of `SemanticDataRegistry`.

## Allowlist

The allowlist is `A2_APPROVED_PAIRS`. It is a `frozenset` of the pairs from
`msgloom.a2_kedro.contracts.header.approved_pairs()` at import time. Today
that is 14 pairs: the 12 `STAGE_SCHEMAS` pairs, `a2_completion_receipt@2`,
and `triage_input@2`.

Every factory call compares the live `approved_pairs()` with the frozen set.
A difference raises `A2RegistryError`. A schema id change cannot widen the
registry without a code change here.

All approved pairs require semantic data. Every A2 v2 payload carries a
header and a canonical body.

## Fail-closed behavior

`A2RegistryError` extends `A2ContractError`. It is raised for:

- a malformed `kind@version` string (strict ASCII, no space, no newline)
- an unknown kind
- an unknown version, or a wrong kind/version pairing
- a duplicate registration
- a registry with a missing pair or an extra pair
- any extension attempt

A lookup on the semantic registry raises `A2UnknownSchemaError`. It extends
both `A2RegistryError` and `UnknownSemanticDataSchemaError`, so existing
store error handling still applies.

Rejected examples: `prepared@1`, `filter_result@1`, `group_result@1`,
`prepared@999`, `zones@2`, `triage_input@1`, and every Phase 1 kind at
version 1 that is not approved.

## Sealing

`ResultSchemaRegistry` is a frozen dataclass. Its `with_schema` method
returns an extended copy. The A2 subclass overrides `with_schema` to raise.
Direct construction with any other pair set raises.

`SemanticDataRegistry` has no extension method. The A2 subclass also
blocks attribute writes and deletes after construction.

## Codec scope (gap)

`A2HeaderCodec` is an envelope codec. It checks that the `header` names the
registered pair, then writes or reads bounded canonical JSON. It does not
validate the body. Body validation stays in the typed contract models.
Typed per-kind codecs are a later step.

`decode` returns a mapping, not a typed model. An arbitrary body next to a
valid header round-trips. Very deep JSON nesting raises `A2RegistryError`.

## Scope limits

- The registry holds only the 14 A2 v2 pairs. It does not hold the intake
  kinds `collected_selection@1` and `preparation_intake_workset@1`. A store
  that calls `supports()` on this registry alone refuses them. Composition
  must decide how to combine the old and the A2 registries.
- The seal stops ordinary use only. In-process code can bypass it with
  `object.__setattr__`, a crafted pickle, or a subclass. That needs code
  execution already.

## Old behavior is unchanged

No old file was edited. `ResultSchemaRegistry.phase1()`,
`SemanticDataRegistry.phase1()`, their codecs, and `ResultSchemaRegistry.
with_schema()` behave as before. Tests snapshot the Phase 1 registries
before and after the factory runs.

## Not done

Composition wiring is a later controlled edit. `msgloom/cli/composition.py`
still uses `ResultSchemaRegistry.phase1()`.
