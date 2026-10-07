# A1 Microsoft collection closeout

**Status:** closed
**Closeout date:** 2026-10-03
**Implementation head before closeout documentation:**
`d1c703d4c93e966b8c025d0ec77c2929c2ac9a77`
**Runtime:** Python 3.13.5, Scrapy 2.19.0

## Scope

This closes the Microsoft-source expansion work defined by Part I of
`docs/plans/msgloom-next-implementation-program.md`. It does not freeze A1
against future bug fixes or evidence-backed maintenance. It means downstream
work can treat the current A1 acquisition contract as the stable input boundary
instead of continuing to add Microsoft products or redesigning the working
Graph-over-Scrapy architecture.

## Capability status

| Capability | Closeout status |
| --- | --- |
| Outlook Mail | Read-only discovery, delta, full acquisition, attachments, lifecycle reconciliation, rule-selected acquisition, and atomic promotion are accepted. |
| Outlook Calendar | Read-only discovery, bounded window, delta, full acquisition, attachments, fixed-window state, and qualified resume paths are accepted. |
| Microsoft To Do | Read-only authoritative snapshot synchronization and absence reconciliation are accepted; two personal-account runs were completed on 2026-09-29. |
| OneDrive | Read-only discovery, delta, explicit content, expired-cursor recovery, atomic resync, and content-freshness classification are accepted. A synthetic 410 remains the safe acceptance mechanism unless Graph naturally returns one. |
| Contacts | Read-only discovery and authoritative snapshot synchronization are accepted; personal-account `Contacts.Read` live acceptance completed on 2026-10-03. |
| User/Profile | The signed-in user read primitive remains available through `User.Read`. |
| Teams | Real acceptance remains blocked by the available personal-account capability. Synthetic fixtures may preserve shared contracts, but A1 does not claim live Teams support. |

Microsoft source expansion stops after Contacts for this program.

## Contacts personal-account acceptance

The 2026-10-03 acceptance used the documented Microsoft Graph Command Line
Tools development public client and an isolated temporary catalog/evidence
root. The resource scope was exactly `Contacts.Read`.

The live discovery run completed two Graph requests with HTTP 200 responses,
covering the default Contacts collection and top-level contact-folder inventory.
It persisted both raw network responses and both terminal collection-completion
items, and the source-identity gate bound the empty isolated source.

The following authoritative sync reused the saved consent and source binding.
It again completed two HTTP 200 Graph requests and committed the clean snapshot
promotion. The account contained zero contacts and zero custom contact folders.
The live evidence therefore validates authorization, transport, evidence
persistence, terminal traversal, source identity, and an empty authoritative
snapshot. Synthetic integration tests remain the acceptance evidence for
non-empty recursive folders, pagination, removals, competing runs, and failure
gates.

No provider data was mutated and no write scope was requested. After acceptance,
the local MSAL cache reported `Contacts.Read` alongside the previously granted
read scopes.

## Fresh closeout validation

The implementation head above was unchanged while the live Contacts acceptance
and these gates were run.

- A1-focused regression selection: **2003 passed**.
- Full normal Python 3.13 suite: **2250 passed**.
- Serial `exclusive_state` suite: **1 passed**.
- FastMCP 4 opt-in compatibility suite: **1 passed**.
- Total tracked tests across the project-defined groups: **2252 passed**.
- Ruff check: PASS.
- Ruff format check: PASS; 681 files already formatted.
- Pyright: **0 errors, 0 warnings, 0 informations**.
- Scrapy contracts: **4 passed**.
- `microsoft_graph/` reverse-dependency scan for `message_ingest` or
  `msgloom` imports: zero matches.
- Production Graph scope audit: `Mail.Read`, `Mail.Read.Shared`,
  `Calendars.Read`, `Calendars.Read.Shared`, `Tasks.Read`, `Files.Read`,
  `Contacts.Read`, and `User.Read`; no A1 write permission is declared.

The Python 3.12/3.13/3.14 compatibility matrix had already been qualified on
this same implementation head during the immediately preceding Outlook Mail
rule-engine closeout. This A1 closeout changed no Python source or dependency
lock before the fresh validation above.

## A1-to-A2 boundary

A1 owns authorized acquisition, raw evidence, provider projections, source
identity, current-state and presence semantics, provider checkpoints, and
clean-promotion correctness. Its externally useful result is durable saved
source state and evidence, not a live Scrapy crawler object.

A2 must consume committed A1 data through an explicit read boundary. It must
not depend on active Spider, Request, Response, Crawler, middleware, Scheduler,
or in-flight item-pipeline state. A1 may continue collecting while a downstream
stage processes an already selected durable source version.

The asynchronous application contract remains unchanged: public operations are
awaitable and must not block the caller event loop. A1 uses Scrapy's async
runtime and awaits bounded worker execution for blocking persistence where
required. Downstream implementation choices must preserve that application
contract without requiring A1 to be redesigned.

## Additive durable handoff extension

The A1 source-capability closeout above remains closed. The integrated
handoff extension adds a release ledger to the existing catalog. It does not
add a Microsoft product or change the read-only acquisition boundary. The
runtime is implemented and qualified; Tasks 1–14 have PRIMARY acceptance.
Task 15 documentation review and final independent acceptance remain pending.
The closeout counts above are historical A1 evidence, not handoff gate results.

A1 records immutable acquisition facts with the state they describe. Eligible
completion publishes release groups and ordered release entries. Authority
publication stays in the transaction that promotes its provider checkpoint
and lifecycle state. Staged authority facts do not become downstream work
before that gate succeeds.

A2 reads committed entries through `ReleaseSourceReader`. It saves exact
selections and a bounded workset in its separate Phase 1 store. Cursor
advancement records durable admission, not successful parsing. Pending
worksets remain available for a later finite scheduled invocation. A1 can
continue collecting while A2 prepares the saved selections.

See [scheduled preparation configuration](operator-configuration.md#scheduled-preparation)
and the [collection/preparation boundary](../phase-1/architecture.md#durable-incremental-handoff)
for operation and recovery. Existing pre-ledger records are not automatically
admitted by future-only intake. The integrated
[historical baseline service](operator-configuration.md#explicit-historical-baseline)
admits caller-approved exact versions for a new consumer scope without
creating release entries. Its immutable starting workset uses the normal
pending preparation path. See the handoff qualification record below.

### Handoff qualification record — 2026-10-07

The runtime candidate is `d0c764f37c3ad511fadd671e603bdb7c86def63b`.
The original runtime and static gates retain their qualified scopes below.
The focused production repair has independent approval and closes finding R1.
PRIMARY acceptance of Tasks 1–14 is recorded in `wave245-task-readiness.json`.
This documentation update does not claim a new full-suite run or final Task 15
acceptance.

The durable evidence directory is the sibling `a1-a2-execution/` worktree
under `msgloom-worktrees/`. `wave244-gate-evidence.json` records the qualified
gates and supporting result hashes. The original candidate and invocation
identities remain attached to each result:

| Gate | Original candidate | Original invocation | Qualified result |
| --- | --- | --- | --- |
| Normal Python 3.13 | `4d92349ab13e3c552479c20dd983e246a5ec9c63` | `86e5cfbe341c4c1b937fcb8d622d499b` | 4033 passed |
| Private pre-commit | `4d92349ab13e3c552479c20dd983e246a5ec9c63` | `1f20628b2cf1448c81a2a07348835239` | 13 hooks passed |
| Python 3.13 serial / FastMCP | `4d92349ab13e3c552479c20dd983e246a5ec9c63` | `1951101a4e0644f7b5d5f599c08e3148` | 1 / 1 passed |
| Static gates | `35fb4ee5a8a1a926ff6fc0dcad9614ec58c5a2b2` | `5f44ec9bf6b34c0fb709a138ec7c2faa` | 7 gates; 4 Scrapy contracts; 328 LSP paths |
| A1 / 13 end-to-end scenarios | `359f8abc4f765092449e733f54262f81a1b2aa56` | `d8e52194f1e643cdaeb72cf10c026ab7` | 2627 / 48 passed |
| Python 3.12 normal / serial / FastMCP | `359f8abc4f765092449e733f54262f81a1b2aa56` | `e7c6171d3c624003a7ef6d13d3576f2e` | 4034 / 1 / 1 passed |
| Python 3.14 normal / serial / FastMCP | `359f8abc4f765092449e733f54262f81a1b2aa56` | `e04e5e6332104536aec749791cd3ad2d` | 4034 / 1 / 1 passed |

`wave241-evidence-scope.json` and `wave244-closeout-preparation.json` record
the earlier test-only repair through candidate `359f8ab`: the exceptional
large-fixture To Do test deadline and a stalled-request negative control.
That repair retained the default deadline and authority checks and did not
change production code. Its focused regressions and scoped Ruff, Pyright, and
live LSP checks supplement the original static evidence.

The subsequent `d0c764f` repair changes production intake. It maps Mail
`inventory_present` to presence in the exact folder and Calendar
`rebaseline_absence` to absence in the exact calendar window. The focused
evidence in `native-transition_repair244-result.json` records four expected
failures before repair and 34 passing tests after repair, plus scoped static
and live LSP checks. `native-transition_review245-result.json` independently
approves that repair and its evidence scope. `wave245-evidence-scope.json`
retains the unaffected broad gates with their original candidate and invocation
identities. Producer traversal, persistence transactions, dependencies,
transport, and execution machinery are unchanged by this production repair.
The retained gates are not newly executed full-suite, matrix, hook, contract,
or broad LSP passes on `d0c764f`.

Historical failures remain preserved, including B0/145, normal138, and
A1/scenarios238. The failed A1 invocation
`af5897ab11ac4fb9a6a76522f73ec510` on `4d92349` had 2625 passes and one
failure; its 13-scenario gate did not run. Later passes do not erase or relabel
these records.

Final approval still requires the changed-document review, the independent
Astra/MAX review of the full diff from the original plan base to the exact final
candidate, and PRIMARY acceptance of all 15 tasks. The historical Task 15
preparation checklist remains a preparation record. It does not replace the
current gate evidence or claim those remaining approvals.
