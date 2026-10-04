# Teams P2 application contract

The persistence worker commit is
`d2bc7f2e223f998545c9d4cc5c93f297c4c765ac`, integrated as
`f578ec00f83c56a7f81b7f61bae2e9ce480655d2`.
The coordinator correction is
`b3b11fb4dc38e8bbff7d1f9c0f7d56f9342b7262`, integrated as
`80f764fe2d33cc870a8cff621f0867f6017ce095`.
The frozen worker manifests identify the exact shared-contract input commit.

## Items and evidence

Application items live in `message_ingest.items.microsoft.teams`.
Provider subclasses keep the provider constructors and add `source_id`,
`observed_at`, `evidence_id`, and `run_id`. Construct each item with the source
and raw-response provenance. Existing `EvidenceLinkPipeline` canonicalizes the
response ID and capture time. A cached response may retain an earlier evidence
run while its semantic observation records the current crawl run.

`TeamsMessageTrigger.from_message(item)` captures source, scoped identity,
evidence ID, and observation time for follow-up callback arguments. The trigger
is immutable and pickle-safe. `TeamsPipeline` resolves its provisional evidence
alias before the store resolves the exact committed message observation.

Hosted metadata uses `TeamsHostedContentItem.from_graph()` with `trigger` and
provenance. Binary content uses `TeamsHostedContentBytesItem.from_bytes()` with
`body`, `message_identity`, `hosted_content_id`, `trigger`, `content_type`, and
provenance. Its digest and byte count must match the linked raw response.
`TeamsHostedContentFailureItem` records retrieval limitations separately.
Hosted observations always have `provider_version_bound=False`.

File references use `TeamsReferenceResolutionItem` with the attachment ordinal,
trigger, explicit state, details, and provenance. The unselected broad file
profile means `not-attempted`; arbitrary attachment URLs are not fetch targets.

## Durable schema

The shared catalog registry automatically imports the Teams model package.
A Catalog-only import creates 11 additive tables:

- `teams_message_observations`, `teams_message_current`;
- `teams_message_deletions`, `teams_message_attachments`;
- `teams_topology_observations`, `teams_topology_current`;
- `teams_reference_resolution_observations` and
  `teams_reference_resolution_current`;
- `teams_hosted_content_observations`;
- `teams_coverage_observations`, `teams_coverage_current`.

Scoped keys hash canonical JSON tuples. Opaque IDs remain separate tuple
components. A message capture is unique by source, scoped identity, and evidence.
Hosted and reference captures also identify the exact triggering capture.
Attachment ordinals preserve repeated or absent attachment IDs.

Stores require committed evidence with the same source and capture time.
Exact replay is idempotent. Changed immutable facts are rejected. Separate
captures with the same etag remain separate observations. Current projections
advance only on strictly later capture times. Stale or tied coverage gaps still
set sticky history uncertainty. Explicit deletion retains older message bodies;
ordinary inventory absence has no deletion or unpin effect.

The pipeline owns type dispatch, bounded stats, and awaited thread writes under
the existing shared catalog lock. Cancellation drains the writer before releasing
the lock and propagates cancellation afterward. No provider parsing or traversal
belongs in the pipeline or stores.

## Shared application base

Use the provider composition class first and
`MicrosoftTeamsBaseSpider` second in each concrete spider's MRO. The base is in
`message_ingest.spiders.microsoft.teams._base`. It retains the application Graph
errback, `run_failed`, and existing integrity extension behavior.

The base selects pipelines 200/250/300 and the shared
`MSGLOOM_TEAMS_SOURCE_ID`, default `microsoft-teams-default`. Explicit command
source selection retains its priority. It requires catalog and raw evidence,
requires `CONCURRENT_ITEMS=1`, rejects JOBDIR, disables unrelated checkpoint
settings, and forces uncached discovery requests through native Graph transport.

`self._teams_provenance(evidence)` supplies item constructor provenance. Each
named callback must yield raw evidence before parsing. Carry explicit `purpose`
in request `cb_kwargs` so inherited failure evidence has the correct purpose.
The concrete spider owns traversal and provider continuation handling. The base
adds no checkpoint, absence promotion, scheduler, or authentication flow.

## Qualification and remaining gates

The worker's original 24 tests and static checks passed. Eleven coordinator
regressions first failed, then passed after the evidence/replay correction.
Integrated persistence, registration, alias, stale/gap, and base tests passed
46 cases. The combined Teams/Graph/evidence/source-identity selection passed
485 tests in 110.25 seconds. Ruff, format, Pyright, and targeted live LSP checks
passed after correcting a test type annotation.

The fresh-process registration test preserves a preexisting source binding and
requires all 11 tables from a Catalog-only import. Chat/channel crawls, public
commands, saved-source integration, notification qualification, complete gates,
compatibility, and independent exact-candidate reviews remain required.
