# Decision ADR-A2-20261023: Kedro is the primary A2 ETL framework

**Decision status:** USER-CONFIRMED architecture intent, reconfirmed 2026-10-23 after review of the 2026-10-03 and 2026-10-07 msgloom conversations.
**Code status:** DESIGN ONLY. No Kedro A2 production implementation is authorized by this record.
**Scope:** A2 after accepted A1 collection and durable A1→A2 handoff.
**Historical A1 qualification:** `34057c6c9f85688fd2bd1868d90302ab5a61205f`, Task 15 28/28 automated gates and independent acceptance.
**Current planning base:** `895fc40a0ec889bd96f620df8c62491787218217` (master after PR #67).

## Historical instructions (requirements, not alternatives)

User decisions on 2026-10-03 and 2026-10-07 established:

1. **Fresh A2 implementation using Kedro as the principal ETL orchestration framework**. Do not merely wrap the old `PreparationHandler`, preserve its decomposition, or embed a token two-node Kedro "pure" subgraph into a predominantly custom A2 pipeline.
2. **Deprecate prior A2 implementation**. Treat its working features, tests, evidence, and failures as *research/acceptance inputs*, not a code-design constraint, compatibility promise for its private methods, or the canonical algorithm. At accepted cutover, delete redundant obsolete runtime implementation; retain immutable git/QA evidence and negative tests.
3. **A1 was deliberately made handoff-ready before A2**. A1 owns raw provider capture/evidence, immutable acquisition facts, source identity/version/relationships/scopes/limitations/completeness, atomic release groups/entries and checkpoint authority. Accepted reader/intake freeze a bounded exact workset and cursor, including held and pending work, scoped transitions, historical context and restart/replay.
4. **A2 only consumes committed, exact A1 releases**. Do not scan all SQLite rows to infer today's work, silently include history, mutate A1 current state, collect from Graph, depend on active Scrapy objects, invent missing bytes, or advance the intake cursor without durable admission.
5. **Fully asynchronous application contract**. Public A1/A2 APIs are awaitable, nonblocking and cancellation-safe. Kedro Core runs synchronous nodes/runner inside a specifically owned, bounded execution boundary, not on the Application event loop. Do not assume an asyncio-native Kedro runner.

These decisions were reiterated on 2026-10-13 when the user requested completion of A1, followed by new Kedro A2 development. They outrank unaccepted engineering assumptions in the 2026-09-29 local Kedro migration plan and later 2026-10-23 draft.

## Required role of Kedro and the outside boundaries

**Kedro owns A2's main ETL dependency graph** from *pinned handoff inputs* to *persisted, versioned A2 results*. This includes:

- admission of exact frozen input into the DAG (not ownership of cursor/admission transaction);
- content extraction/format parsing via trusted bounded parser adapters;
- content/metadata normalization and zoning with source-offset provenance;
- interpretation of *source-native* relationships, including uncertainty and exact scope, without semantic cross-source joining;
- deterministic filters and bounded communication grouping;
- organization of stage-result load/save dependencies through programmatic DataCatalog adapters;
- canonical output/result manifest construction for A3.

**msgloom—not Kedro—owns** upstream A1 and Scrapy, immutable fact publication, intake/consumer cursor, raw saved bytes, parser sandbox/process and security policy, ClaimToken and deadlines, SQLAlchemy transactions, semantic IDs/version codecs, acceptance/terminal outcomes, retries and external scheduling. Kedro can order these operations through *trusted* dataset/node adapters but cannot replace their authority or establish a second checkpoint/version state.

A correct design may use `SequentialRunner`, `Pipeline`, `DataCatalog`, closed `AbstractDataset` adapters and bounded `MemoryDataset` implementations **provided the complete A2 ETL DAG genuinely depends on them**. A workflow in which an external `PreparationHandler` does all loading/parsing/persistence and Kedro executes only filter/group calculations fails this decision. Conversely, putting raw A1 database access or unfenced writes in arbitrary Kedro nodes also fails.

## Contract stability vs legacy deprecation

**Stable / must not redesign in A2:** `ReleaseSourceReader` release reconstruction and digest validation; durable `PreparationIntakeWorkset`, bounded selection, consumer cursor, pending fairness, held classification, scoped transitions, explicit historical baseline, and exact A1 Task 15 invariants. Some of these types live in `msgloom/preparation_pipeline/`, but their accepted handoff role is determined by semantics, not the directory name.

**Not stable merely because old A2 wrote it:** `PreparationHandler` inheritance, `RecordSteps`, `StageSteps`, private helper methods, legacy node ordering, pure-grouping algorithm implementation, internal batch granularity, old prepared serialization schema or old stage result layout. Proposed replacements must demonstrate product-correct replay/lineage, and adapt A3/A5 consumers with typed version handling where required. Differences from legacy should be explicitly tested and justified; they are not automatically regressions.

**No unapproved feature expansion:** new semantic NLP topic joining, external provider reads, automatic OCR or AI invocation, and changing A1 source authority remain out of this A2 scope. Zoning/normalization preserves what the content says and distinguishes known from unknown; do not fabricate source relations.

## Corrected review baseline

- The local 2026-09-29 branch `program/kedro-a2-plan` (commit `c7dcb41`) described a *narrow legacy migration*, so it is historical only.
- The 2026-10-23 draft commits `37f5886` and `c1ac6cf` still assigned parser sequencing and persistence ordering to outer custom controller and made Kedro a pair of pure subgraphs. **That was inconsistent with the user's original architectural instruction** even before the R1/R2 technical review findings.
- Two read-only independent reviews of these superseded drafts returned **REVISE**; neither is A2 design approval. Keep the original reports unchanged and review this corrected design anew.
- All project CI and Task 15 evidence qualifies its exact historical SHA, not any future Kedro implementation.

**Design admission:** author a Kedro-primary architecture and implementation plan with explicit async/runner/dataset bridge, fail-closed claim-fenced persistence, hard resource and deadline bounds, end-to-end ETL stage ownership and an independent fresh design review. Begin only read-only framework/source-security investigation before design approval; no code, dependency lock, or runtime changes.
