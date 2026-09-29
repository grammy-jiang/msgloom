# Phase 1 semantic-data handoff

**Scope:** producer/consumer API for durable preparation data.

Phase 1 persistence remains the sole owner of the provider-neutral `phase1_*`
schema in its separate Application database. Schema version 2 adds
`phase1_semantic_data` and the semantic-data reference on stage results.
Opening a version-1, partial, future, or otherwise different neutral schema
fails with `IncompatibleSchemaError`; this lane performs no implicit migration.
A1 `CatalogService` tables and files are not read or changed.

## Producer and consumer sequence

A preparation producer constructs a validated immutable `PreparedRecord`.
The record carries exact `VersionRef` lineage, aware source time, participants,
relationships, attachment `SavedByteReference` values, referenced
`ParserOutput` content, limitations, source locations, and an explicit
filtering disposition. Raw source bytes remain evidence-owned and are never
embedded in semantic data.

The exact handoff is:

```python
persistence = await Phase1Persistence.open(application_database_url)
prepared = PreparedRecord(...)

data_ref = persistence.semantic_reference(
    "prepared-data:synthetic-1",
    "prepared",
    "1",
    prepared,
)
result = StageResult(
    ...,
    kind="prepared",
    schema_version="1",
    semantic_data_ref=data_ref,
    status=TerminalStatus.COMPLETE,
    acceptable=True,
)

await persistence.append_result_with_data(result, prepared)

saved = await persistence.get_result(result.result_id)
if saved is None or saved.semantic_data_ref is None:
    raise RuntimeError("prepared result was not durable")
loaded = await persistence.load_semantic_data(saved.semantic_data_ref)
if not isinstance(loaded, PreparedRecord):
    raise RuntimeError("prepared result schema decoded to an unexpected type")

claim = await persistence.acquire_claim(
    "triage:synthetic-1",
    ClaimKind.TRIAGE,
    execution,
    attempt,
    required_inputs=(
        ResultRef(result.result_id, result.kind, result.schema_version),
    ),
)
```

`prepared@1`, `filter_result@1`, `group_result@1`, `triage@1`, and `report@1`
are semantic product-result
schemas. An acceptable result for any of them must declare a semantic-data
reference and must be written with `append_result_with_data()`; a metadata-only
success marker is rejected. Failed, blocked, cancelled, or otherwise
unacceptable diagnostic results may remain metadata-only, but cannot authorize
dependent work. `report_submission@1` records delivery/effect state rather
than duplicating the saved `report@1` product payload.

`append_result_with_data()` validates the registered codec, canonical size
bound, type, digest, and exact reference, then writes semantic bytes and the
stage result in one `BEGIN IMMEDIATE` transaction. A conflict rolls both back.
Identical replay is idempotent; accepted history is never rewritten. Codec
encoding revalidates the complete typed value rather than trusting an existing
Pydantic instance, including values created through validation-bypass APIs.

`get_result()` rejects stored acceptable product metadata if its required
semantic reference is absent. `acquire_claim()` additionally revalidates the
required semantic reference and bytes for every semantic product input.
Missing references or bytes, a mismatched reference, corrupted content, an
unregistered semantic schema, or an unacceptable result prevents dependent
work from starting. `load_semantic_data()` performs the same payload integrity
and schema validation for consumers.

## Registry boundary

The default registry includes `prepared@1`, `filter_result@1`, and
`group_result@1`. Their codecs round-trip exact typed preparation data. See
[filtering and grouping](preparation-semantics.md) for their contracts. Save
each filter result with its prepared input reference, then each grouping
result with its exact filter input references before admitting dependent work.

The prepared codec round-trips the
typed prepared record, including ordered parser blocks/tables and exact source
locations, through canonical bounded JSON. It does not accept dictionaries as
producer payloads and does not provide a generic arbitrary-JSON store.
Consequently, acceptable `triage@1` and `report@1` writes remain gated until
their later lanes register reviewed semantic codecs; they cannot fall back to
metadata-only success.

Later A3/A5 producers add their own reviewed kind/schema codec to
`SemanticDataRegistry`; they do not create another database or schema owner.
Unknown kinds or versions fail visibly until that registration exists.
`StageResult.exposed_output_ref` remains reserved for exposed AI trace output
and diagnostics and is not a semantic-payload escape hatch.

The existing awaited synchronous SQLAlchemy facade still owns lifecycle
semantics: accepted thread-backed writes drain through cancellation, and
`close()` waits for accepted calls before disposing the engine. Producers must
await the result/data write before attempting dependent claims.
