# Exact release reader API

Task12 adds the following public imports from `msgloom.sources`:

- `ReleaseSourceReader`
- `ReleasedInput`
- `ScopedTransition`
- `SupportingContext`

## Construction and ownership

Construct `ReleaseSourceReader(SavedSourceReaderConfig(...))` with an absolute
existing catalog path, explicit evidence roots, and finite reader limits.
The reader owns its read-only catalog handles and bounded workers. Always
await `close()`; cancellation drains accepted reads before propagating.

The `catalog` attribute exposes the unchanged Task6 `HandoffCatalog` API.
Task13 selects its bounded entry cut through that API, then calls
`await reader.read_entry(entry.reference)` for each exact entry.
Passing a `ReleaseEntry` also works; its reference is reloaded and validated.
Caller-supplied payload fields never override committed facts.

This API has no dependency on Task11 persistence types. The caller owns claims,
cursors, held-entry dispositions, and workset persistence.

## Reconstruction result

`read_entry(ReleaseEntryRef | ReleaseEntry) -> ReleasedInput` returns:

| Field | Meaning |
| --- | --- |
| `reference` | Exact catalog, entry sequence, and digest admission anchor. |
| `selection` | Optional parent/resource `CollectedSelection`. |
| `components` | Exact component selections, including terminal limitations. |
| `contexts` | Inventory/control selections; never promoted to primary input. |
| `transitions` | Typed scoped authority effects, without fabricated bodies. |
| `facts` | Exact ordered immutable facts, preserving logical-run provenance. |

A single entry can contain a readable source and scoped transitions.
Consumers must preserve every field rather than discard non-primary effects.

Component-only To Do entries retain the released child's exact selection and
parent identity in `components` and `facts`. They do not invent a parent task
version. A OneDrive content-only entry can reconstruct its parent metadata
through the named immutable content capture's exact metadata association.

`ScopedTransition` preserves source, stream, resource, parent, scope,
authority revision, provider order, exact bounded reason, and verified evidence
reference when present. Scope is never widened to global deletion. Policy
interpretation remains downstream.

## Exactness and replay

Source versions use the exact immutable locator, independently of admission
sequence and logical run. Components without provider bytes use the immutable
terminal state key and bounded reason; they have no invented evidence.
The complete selection also binds component references and limitations.

Persist selections with the existing `CollectedSelectionCodec` or inherited
`encode_selection()`. Decode them for downstream REPLAY without consulting A1
current projections. Use `load_saved_bytes()` to verify referenced bytes.

Calendar observations resolve their immutable observation rows, including
fixed-window scope and exact page positions. Contacts delta resolves its
source/folder/run/ordinal association. OneDrive reset resolves its observation
ID and page position; ordinary metadata uses sanitized exact-state matching.
Content resolves only the named capture and its metadata binding.

No scheduled path calls `list_versions()`, scans current projections, searches
for a newest component, or uses OneDrive's manual current pseudoversion.
The inherited manual LIVE/REPLAY methods retain their existing semantics.

## Explicit supporting context

`read_supporting_context(reference) -> SupportingContext` pins an explicitly
named historical released source or one inventory context selection.
`primary` is always false. The operation neither enumerates nor admits more
entries. Component-only and transition-only entries without a parent selection
cannot masquerade as a readable historical parent.

## Failure and limits

Missing, corrupt, mismatched, ambiguous, unsupported, or oversized required
input raises a privacy-safe `SourceReaderError` subtype. Task13 must persist
the exact entry reference with a held disposition before advancing its cursor.
No repair, recollection, current fallback, or cursor mutation occurs here.

Evidence reads use per-file and aggregate byte bounds, pinned safe paths,
digest verification, finite query deadlines, and bounded worker admission.
Exact immutable metadata is required even when mutable projections look usable.

Mail reconstruction uses exact message observations and named component facts.
Canonical immutable status/profile metadata describes all six terminal outcomes.
Legacy missing or noncanonical metadata fails closed. Acquired components require
verified saved evidence. MIME remains raw bytes in an alternate body; attachment
metadata and raw bytes are joined only within the named inventory and parent.
Selected captures use retained application bindings and explicit inventory page
predecessors. Direct captures must prove their immutable parent and state digest.
Folder membership and mailbox presence remain separate typed scopes.

This provisional Mail implementation still requires the full version matrix,
source/test LSP checks, contracts, hooks, and independent exact-candidate review.
Existing manual Mail reading is unchanged.
