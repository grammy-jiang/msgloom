# Raw-evidence cancellation repair

The independent R3 lifecycle reviewer found `LC-R3-RAW-EVIDENCE-CANCEL-001`
at candidate `9b56fbfe5a68225b945ec8eeaf1d54e8b6ec2c7e`.
The raw pipeline awaited an unshielded thread under the shared catalog lock.
Cancellation released that lock while the thread could still write files or
SQL. Its synchronous close hook could also dispose the catalog during a write.

Three bounded failing regressions reproduced those behaviors. Earlier test
attempts also exposed a fixture setup error involving frozen Scrapy settings;
that error was corrected before the three behavioral failures were recorded.
No production expectation was removed or relaxed.

`CatalogService.write` now owns the existing Teams shield-and-drain contract.
Raw evidence and Teams semantic persistence both use that operation. It holds
the shared lock until the thread finishes, restores repeated cancellation
requests, and chains a concurrent worker error to cancellation. A cancelled raw
item does not publish a successful alias or increment success counters. Any
completed raw capture remains available in the append-only evidence store.
The raw pipeline's async close hook waits on the same lock before disposal.

Four raw regressions cover successful and failed worker drain, repeated
cancellation, real file/SQL completion, and native parallel pipeline close with
and without cancellation. Existing Teams cancellation tests continue to check
the shared contract. The focused gate passed 21 tests. Integrated and complete
exact-candidate gates remain required, followed by all nine independent closure
reviews. A passing repair test does not establish final program acceptance.

The implementation uses native Scrapy 2.19.0 async pipeline hooks. The installed
`ItemPipelineManager` awaits close hooks concurrently, so hook priority cannot
replace shared lock ownership. Python's
[cancellation contract](https://docs.python.org/3.13/library/asyncio-task.html#task-cancellation)
requires propagation after cleanup; cancelling a waiter does not stop an
already running worker thread. No new transport, scheduler, or retry path is
introduced.

Reproduction and validation receipts are retained under
`.superpowers/teams-a1/`, including `logs/p3-r3-raw-cancel-red-r3.log`,
`logs/p3-r3-raw-cancel-focused.log`, and `p3-r3-raw-cancel-lsp.json`.
