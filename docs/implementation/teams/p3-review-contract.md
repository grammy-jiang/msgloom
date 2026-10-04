# Teams independent review contract

The nine P3 reviews are required before local implementation completion.
This document defines their inputs and acceptance rules. It records no review
acceptance. Chat, saved-source, and notification integration remain pending.

## Freeze the review input

After production convergence, freeze one clean code candidate. Record its full
Git SHA. Build an immutable archive from tracked files at that commit and a
SHA-256 inventory of its contents. Exclude credentials, live raw evidence,
mutable worker state, and unrelated untracked files.

Provide the design authority, accepted implementation contracts, all 36
fixture mappings, and exact gate records. Each gate record must identify its
command, interpreter, candidate, result, and immutable log hash. A passing gate
on an earlier commit is historical evidence, not final candidate acceptance.

The gate packet must include:

- Python 3.13 normal tests and separate serial exclusive-state tests;
- locked tox Python 3.12, 3.13, and 3.14 results;
- each configured FastMCP compatibility environment;
- Ruff check and format, Pyright, and live Python LSP diagnostics;
- native Scrapy contracts and public CLI fixture crawls;
- changed-file pre-commit checks and the final fixture audit;
- precise live prerequisites and unexecuted tenant acceptance cells.

## Independent lanes

Create a separate real ChatGPT Chat conversation for each row. Pin every send
to ``gpt-5-6-thinking`` with ``max`` effort. Each lane is read-only. It must
inspect the exact archived source and tests through the existing MCP connector.
A coordinator summary does not replace source inspection.

| Lane | Required focus |
| --- | --- |
| Provider/API/permissions | Stable paths, query support, delegated T1/T2 scopes, opaque IDs, provider limitations, and current primary documentation |
| Graph-over-Scrapy ownership | Provider independence, application callbacks, pipeline boundaries, and one native transport |
| Lifecycle/cancellation | Native failure signals, inherited errback, awaited writes, lock drain, JOBDIR, and any idle gates |
| Privacy/security | Trusted subscription/account/tenant/resource binding, arbitrary URL prevention, and secret-safe logs and outputs |
| Evidence/provenance/replay | Raw-before-semantic persistence, canonical linkage, inbound request provenance, and public saved-selection replay |
| Persistence/history/deletion | Immutable observed versions, scoped IDs, failed-readback deletion, multi-event aggregation, and sticky gaps |
| Shared topology | Associated hosts, incoming/shared channels, detail completeness, membership paths, and root/reply identities |
| Fixture completeness | All 36 executed cells, native crawl behavior, failure cases, and truthful optional/live labels |
| Compatibility | Locked interpreter environments, package boundaries, additive schema, exports, and reader imports |

Reviewers must not edit the integration tree, repair code, send messages, or
create subscriptions. Each reviewer receives a unique task ID, full candidate
SHA, inventory digest, required criteria, and a finite JSON response contract.

## Collect and verify

A response must name the exact task, candidate, and inventory digest. It must
state whether hashes were verified, which files were inspected, and the
supporting evidence for every required criterion. A finding must identify its
severity, file and line, concrete behavior, reproduction, and required change.
A limitation must state the missing evidence without inventing a passing result.

The coordinator verifies the actual conversation and final transcript pins.
It rejects unfinished, malformed, stale, or incomplete responses. A PASS with
unresolved blocker or major findings is invalid. A collected response is not
accepted until the coordinator checks its claims against the frozen input.
The writer result validator and the P0 four-cell validator do not implement
this P3 contract and must not be reused unchanged.

## Repair and close

Fix every valid material finding and add or run the required regression test.
Record the failing reproduction, correction, passing result, and changed commit.
Then request a bounded independent re-review.

All nine final closure verdicts must name the same repaired candidate. If a
source repair changes that candidate, earlier verdicts remain historical;
provide the exact new candidate and relevant diff to every closure reviewer.
The coordinator cannot substitute self-review for independent closure.

Local closure does not establish tenant support or authorize a master merge.
The design still requires real T1/T2 acceptance, repeat acquisition, the
applicable webhook flow, post-live gates, and a fresh post-live closure.
