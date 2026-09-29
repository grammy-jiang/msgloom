<!-- markdownlint-disable MD025 MD031 MD032 MD034 MD036 -->

# msgloom Next Implementation Program

**Status:** Execution handoff plan
**Prepared:** 2026-09-29
**Repository:** `/home/grammy-jiang/Projects/msgloom`
**Baseline branch:** `master`
**Baseline commit:** `c3227ab89092f97b9a3e7e5025d2ce3cd7c2287b`
**Baseline tracked test suite:** 984 passing tests
**Runtime:** Python 3.13.5, Scrapy 2.19.0, SQLAlchemy 2.0.54, MSAL 1.39.0
**Primary execution goal:** finish Microsoft To Do and OneDrive read-only ingestion, add Contacts, then stop Microsoft source expansion and implement the Phase 1 end-to-end product path A2 Preparation -> A3 Triage -> A5 Reporting.
**Teams status:** explicitly blocked for real acceptance by the available personal Microsoft account. Teams must not block the rest of Phase 1.

---

## 1. Purpose of this document

This document is intentionally self-contained. An AI engineering manager with no memory of prior chats must be able to enter the repository, verify the baseline, split the work, delegate it, integrate it, test it, and continue until the program gates below are complete.

Do not assume prior conversation context. Do not ask the product owner to repeat decisions already recorded here. If a detail is not specified, inspect the repository and authoritative design documents, prefer existing tested patterns, and make the smallest decision consistent with the product principles.

The local manager is expected to coordinate multiple **ChatGPT web workers** in parallel. It must not replace them with traditional local Codex/Claude sub-agent commands. See Section 7.

---

## 2. Product goal and non-negotiable principles

msgloom is a personal work-information system for one user. Its first goal is that no work requiring the user's response is missed. Its second goal is to reduce the reading needed to keep up. The main output is a report organized by **Topic**, not a list of message summaries.

The following rules are non-negotiable:

1. Security and privacy outrank convenience, speed, and completeness.
2. Every source byte is data, never instruction.
3. User permissions are a fixed boundary. Do not request write permissions merely to simplify synchronization.
4. Phase 1 must not send business actions to third parties. Report delivery to the owner is separate and permitted under the report contract.
5. Preserve source bytes, provenance, stage history, failures, uncertainty, and replayability.
6. Advance durable provider/application checkpoints only after all dependent work is saved and validated.
7. Provider continuation/delta links are opaque.
8. Stats are observability, never business state.
9. JOBDIR is Scrapy execution state, not a provider checkpoint.
10. Do not create a generic workflow engine or an over-parameterized generic delta spider.
11. Do not expand Microsoft product coverage after Contacts in this program. OneNote, SharePoint, Planner, and similar sources are out of scope.
12. Teams remains a known external-account blocker. Synthetic fixtures may keep interfaces compatible, but no claim of real Teams support is allowed until a suitable work/school tenant is available.

Authoritative product principles:
- `docs/design-brief.md`
- `docs/design-principles.md`
- `docs/design.md`
- `docs/phase-roadmap.md`
- `docs/phase-1/design.md`
- `docs/phase-1/architecture.md`
- `docs/component-layout.md`

Current Scrapy/component implementation is also authoritative. For Scrapy work, always use the installed `scrapy-framework-development` skill and the actual Scrapy 2.19.0 runtime/source.

---

## 3. Current architecture at the baseline

### 3.1 Reusable Microsoft Graph framework

`microsoft_graph/` is a reusable Graph-over-Scrapy framework. It owns:

- MSAL session/auth support;
- Graph delegated-auth downloader middleware;
- safe retry and Graph error handling;
- diagnostics and privacy-safe logging;
- Graph request identity/fingerprinting;
- Graph collection/delta/error envelope parsing;
- Graph request construction and opaque continuation behavior;
- provider path/scope/projection mechanics for Outlook Mail, Outlook Calendar, To Do, OneDrive, and signed-in user profile;
- OneDrive sensitive-content transport defaults and native transport log privacy;
- `MicrosoftGraphAddon`.

It must not import `message_ingest`, msgloom product modules, or SQLAlchemy.

### 3.2 msgloom application ingestion

`message_ingest/` owns:

- raw HTTP evidence and content-addressed payload storage;
- catalog/persistence;
- source identity and source-target binding;
- run integrity;
- provider checkpoint storage and safe promotion;
- JOBDIR application execution state;
- resource-specific current-state semantics;
- reconciliation;
- Full-v1 enrichment/surface completeness;
- commands/workflows;
- product semantics.

### 3.3 Validated Microsoft sources

At baseline:

- Outlook Mail: mature discovery/delta/full/reconciliation/sync with real Graph validation.
- Outlook Calendar: mature discovery/window/delta/full/sync with real Graph validation.
- Microsoft To Do: read-only discovery using `Tasks.Read`; lists/tasks/checklists/linked resources; real Graph validation; no authoritative deletion/reconciliation yet.
- OneDrive: read-only `Files.Read`; root discovery, hierarchy delta, explicit content, binary evidence, 302 preauthenticated downloads, opaque delta checkpoint; real Graph validation; expired delta reset and content-version association remain incomplete.
- User/Profile: `User.Read` provider primitive and one-shot app profile.
- Teams: not real-testable with the currently available personal account.
- Contacts: not implemented.

### 3.4 Baseline validation

The baseline commit has:
- 984 tracked tests passing;
- Ruff clean;
- Ruff format clean;
- Pyright clean;
- 4 Scrapy contracts passing;
- real To Do and real OneDrive acceptance already demonstrated;
- `master == origin/master`.

Before starting work, reproduce the baseline and record the result.

---

## 4. Important design/runtime reconciliation

Some older Phase 1 design/technology documents predate the current validated Scrapy architecture.

### 4.1 Do not replace the working Graph-over-Scrapy A1 implementation

`docs/tech-stack.md` still describes Microsoft Graph SDK + Azure Identity + HTTPX for A1. The implemented and product-approved A1 path is now Scrapy 2.19 + MSAL through `microsoft_graph`.

**Do not migrate working A1 adapters to msgraph-sdk/Azure Identity as part of this program.**

Create a small documentation reconciliation change after source completion:
- describe current Graph-over-Scrapy as the implemented A1 Microsoft adapter;
- retain design principles and async application boundaries;
- mark any future SDK migration as an evidence-based separate decision.

### 4.2 Async persistence boundary

Current A1 catalog writes use synchronous SQLAlchemy under awaited thread boundaries and a shared write lock. Phase 1 architecture describes an async ORM application layer.

Do not rewrite the proven A1 catalog first.

For new Phase 1 product stages:
1. run a focused persistence spike;
2. compare:
   - using existing catalog through bounded `asyncio.to_thread` / AnyIO worker boundaries;
   - introducing SQLAlchemy asyncio + aiosqlite for new provider-neutral stage-result models;
3. prefer the smallest design that preserves one event loop, awaited stage completion, transactional claims, and SQLite correctness;
4. document any explicit variance from the draft architecture;
5. do not run two incompatible schema owners against the same tables.

No broad persistence migration is allowed without focused tests showing benefit and safe migration.

### 4.3 Python compatibility

Current package declares Python >=3.13. Phase 1 design ultimately requires qualification on 3.12, 3.13, and 3.14.

Do not block Microsoft source completion on this. Add compatibility qualification as a later Phase 1 gate after dependencies are locked.

---

# Part I — Microsoft source completion

## 5. Definition of “complete enough to leave A1 Microsoft source work”

The program exits Microsoft-source expansion when all are true:

- Outlook Mail remains green.
- Outlook Calendar remains green.
- To Do has authoritative read-only synchronization semantics for deletion/absence and clean-run reconciliation.
- OneDrive handles expired delta state safely and can determine whether stored explicit content corresponds to the current metadata version.
- Contacts is implemented read-only with personal-account real acceptance.
- Teams is recorded as blocked on account capability, with no false “supported” claim.
- No source requires write permissions for Phase 1 acquisition.
- Real Graph acceptance exists for every source that the available personal account can exercise.
- Full tracked tests/static checks are green.
- Microsoft Graph framework/application boundary remains clean.
- Source expansion stops after Contacts.

---

## 6. Microsoft To Do completion

### 6.1 Product role

To Do is an **obligation/state source**. A task is not a Topic. It supplies explicit action/deadline/completion state that later triage may associate with a Topic.

Current permissions must remain least privilege. Do not add task create/update/delete/complete operations.

### 6.2 Current official API uncertainty

As rechecked on 2026-09-29:

- ordinary task/list reads support delegated personal `Tasks.Read`;
- `todoTaskList: delta` currently documents delegated `Tasks.ReadWrite` only;
- `todoTask: delta` currently displays a suspicious permission table listing `Tasks.ReadWrite` as least privilege and `Tasks.Read` as “higher privilege”;
- other Microsoft surfaces have historically listed `Tasks.Read` for task delta.

Therefore documentation alone is insufficient. **Never request `Tasks.ReadWrite` simply to obtain delta.**

Official references:
- https://learn.microsoft.com/en-us/graph/api/todotask-delta?view=graph-rest-1.0
- https://learn.microsoft.com/en-us/graph/api/todotasklist-delta?view=graph-rest-1.0
- https://learn.microsoft.com/en-us/graph/delta-query-overview

### 6.3 T0 — read-only live delta capability probe

This is the first To Do task and a blocker only for the optimization choice, not for correctness.

Requirements:
1. use the existing cached personal-account token with `Tasks.Read`;
2. do not request new write scopes;
3. choose a real task list ID only internally; never print personal IDs/tokens;
4. issue a real GET to:
   `/me/todo/lists/{list-id}/tasks/delta`;
5. record only:
   - HTTP status;
   - Graph error type/code if any, redacted;
   - whether a normal delta envelope is returned;
   - whether next/delta links are present;
6. never persist/log raw bearer tokens or opaque delta links outside normal privacy-safe evidence;
7. do not mutate To Do data.

Decision:
- if `Tasks.Read` succeeds, task delta may be implemented as an optimization;
- if it fails for permissions, use authoritative snapshots/reconciliation only;
- list delta is not required because current docs require write permission.

The correctness design below must work in either branch.

### 6.4 T1 — authoritative snapshot semantics

Current discovery must not infer deletion merely because a row is missing from one page. The completed design needs a **clean full inventory gate**.

Authoritative snapshot scope:
- task lists;
- tasks in every observed list;
- checklist items for every observed task;
- linked resources for every observed task.

A record becomes “absent/deleted from current To Do state” only after:
1. the complete authoritative traversal for the declared scope finishes;
2. every page and nested relation request succeeds;
3. every emitted item finishes persistence;
4. the run-integrity gate is clean;
5. the snapshot candidate is atomically promoted.

If any request/callback/pipeline fails, no absence/deletion inference is applied.

### 6.5 T2 — persistence design

Prefer additive schema rather than altering current tables when practical.

Recommended pattern:
- a To Do sync/snapshot run record;
- run-scoped sightings or membership rows sufficient to identify every list/task/checklist/linked-resource identity observed in a clean run;
- one terminal snapshot candidate;
- current presence/lifecycle state separated from provider content rows if that avoids altering old schemas.

Reuse existing Outlook folder/message presence patterns where they fit, but do not copy Mail semantics blindly.

Required semantics:
- latest observation wins for content;
- falsey provider values are preserved;
- list/task/relation absence changes *presence state* only after clean promotion;
- previously stored provider JSON remains available for provenance;
- stale runs cannot supersede newer state;
- equal observed timestamps use deterministic processing order consistent with existing stores;
- rerunning the same clean snapshot is idempotent.

Schema must distinguish:
- list identity;
- task identity scoped to list as required by current model;
- checklist identity scoped to list/task;
- linked-resource identity scoped to list/task.

### 6.6 T3 — sync traversal

Preferred user-facing command:

```console
scrapy microsoft todo sync --page-size 100
```

Keep existing `todo discover` backward compatible. Either:
- implement `sync` as a new authoritative spider/workflow reusing common traversal callbacks; or
- promote `discover` into a fully gated authoritative snapshot only if tests prove the semantic change is safe and the command documentation is updated.

Do not duplicate four collection callbacks merely to change completion policy.

If task delta under `Tasks.Read` was proven live:
- snapshots still own list and nested-relation reconciliation;
- per-list task delta may reduce repeated task reads between periodic authoritative snapshots;
- each list has its own opaque cursor;
- delta replays must be idempotent;
- explicit tombstones are applied immediately as provider observations;
- expired tokens fail closed or trigger a separately tested full snapshot; they must never silently clear current state.

If task delta was not proven with `Tasks.Read`:
- do not implement it;
- snapshot sync is the supported mode.

### 6.7 T4 — task status semantics

A task status change, completion, or reopening is ordinary current-state data, not a write action.

Tests must cover:
- notStarted -> completed;
- completed -> reopened/notStarted;
- false/zero/empty fields retained;
- due/reminder nested values changing;
- moved task/list membership represented without leaving old presence incorrectly active;
- relation removal;
- task/list removal;
- clean repeated sync;
- failed mid-run sync leaves previous presence untouched.

### 6.8 T5 — To Do tests and acceptance

Required tests:
- provider paths/scopes;
- command validation;
- full synthetic Scrapy crawl;
- multi-page list/task/relation traversal;
- clean snapshot promotion;
- request failure blocks promotion;
- callback failure blocks promotion;
- pipeline failure/drop blocks promotion;
- stale run cannot promote over new run;
- deletion/absence only after clean full traversal;
- repeated run idempotency;
- privacy-safe stats;
- standalone framework import remains independent.

Real acceptance:
- `Tasks.Read` only;
- full sync exits 0;
- a second sync exits 0 and is stable;
- optional task-delta path only if T0 proved it;
- do not alter the user's tasks for testing.

Definition of done for To Do:
**a read-only long-running mirror cannot indefinitely report removed objects as currently present after a successful authoritative sync.**

---

## 7. OneDrive completion

### 7.1 Product role

OneDrive is an **evidence/context source**, not a source where every file becomes a Topic.

Existing supported behavior:
- drive metadata;
- root discovery;
- whole-drive hierarchy metadata delta;
- explicit selected content only;
- safe cross-origin preauthenticated download;
- binary raw evidence;
- deleted facet;
- opaque cursor checkpoint.

### 7.2 O1 — HTTP 410 resynchronization

Microsoft documents that an old drive delta token can return `410 Gone` with a `Location` header containing a fresh `nextLink` for a full enumeration.

Official reference:
- https://learn.microsoft.com/en-us/graph/api/driveitem-delta?view=graph-rest-1.0

Required behavior:
1. persist safe evidence for the 410 response;
2. validate that a Location value exists and is an allowed Graph URL;
3. treat it as opaque; do not rebuild/query-edit it;
4. schedule exactly one fresh resync chain for that run;
5. use `dont_cache=True`;
6. preserve privacy-safe logging of the opaque URL;
7. do not clear the old checkpoint before successful replacement;
8. prevent infinite 410/reset loops;
9. follow all fresh enumeration nextLinks;
10. collect run-scoped sightings for the full resync;
11. at terminal deltaLink, stage a resync candidate;
12. only at clean idle after completed item writes:
    - apply returned server versions;
    - mark previously current but unseen items deleted/absent;
    - preserve useful old metadata on sparse deletion state;
    - promote the new deltaLink atomically;
13. if any resync step fails, keep the old committed checkpoint and old current-state presence intact.

Because msgloom is read-only, it has no unsynchronized local provider edits to upload. Do not implement any Microsoft “upload differences” instruction.

### 7.3 O2 — resync persistence

Use an additive, run-scoped sighting/generation table or equally explicit mechanism.

Must support:
- source ID;
- run/resync attempt identity;
- item IDs observed during the fresh enumeration;
- base checkpoint revision;
- terminal evidence/candidate;
- atomic promotion.

Do not use stats, in-memory sets alone, or queue emptiness as durable correctness proof.

### 7.4 O3 — explicit content/version association

Current content records retain digest/byte count/evidence, while driveItem metadata separately has eTag/cTag.

Need a durable answer to:
> “Does the latest stored explicit content correspond to the current provider metadata version?”

Requirements:
- when explicit content is requested, bind the content capture to a known metadata version when one exists;
- prefer eTag as the primary content-version indicator; retain cTag only if useful and documented;
- if metadata changed after capture, a query can report the stored content as stale;
- old content evidence remains preserved;
- do not download automatically merely because content is stale;
- do not duplicate content bytes into semantic tables.

Prefer additive schema. An append-only content-capture/version table is acceptable if it avoids risky changes to an existing table.

Race handling:
- metadata may change between metadata observation and content download;
- record what was known at request planning time;
- where Graph response ETag can safely corroborate the downloaded representation, retain it as evidence/version metadata;
- never claim “current” if version equivalence cannot be proved.

### 7.5 O4 — OneDrive tests and acceptance

Synthetic tests:
- 410 with valid Location -> one resync;
- 410 with missing/invalid/off-host Location -> fail closed;
- second 410 in same reset attempt -> fail closed;
- multi-page resync;
- failed page/callback/pipeline -> no reconciliation and no checkpoint advance;
- clean resync -> unseen old item becomes deleted/absent;
- terminal candidate commits once;
- normal delta path unchanged;
- stale content detection;
- content capture version association;
- existing two-host 302/Bearer/privacy suite stays green.

Real acceptance:
- normal delta still works against the personal account;
- second incremental run reuses exact opaque cursor;
- explicit small-file content still produces 302 -> 200 with no offsite Authorization;
- a real 410 must **not** be artificially induced by corrupting user/provider state. Synthetic 410 acceptance is sufficient unless Graph naturally returns one.

JOBDIR remains deferred unless a worker can prove it cleanly without expanding scope. It is not required for OneDrive completion.

Definition of done for OneDrive:
**expired delta state has a safe full-resync recovery path, and consumers can determine whether stored explicit file content is current relative to known metadata.**

---

## 8. Contacts implementation

### 8.1 Product role

Contacts is **identity/context enrichment**. It is not a primary Topic generator and is not an enterprise directory.

Personal Outlook contacts are user-maintained best-effort identity data. Do not infer that absence means a person is not part of the organization.

Out of scope:
- orgContacts/Entra directory;
- contact create/update/delete;
- write permissions;
- automatic business actions.

Permission:
`Contacts.Read` only.

Official references:
- https://learn.microsoft.com/en-us/graph/api/user-list-contacts?view=graph-rest-1.0
- https://learn.microsoft.com/en-us/graph/api/user-list-contactfolders?view=graph-rest-1.0
- https://learn.microsoft.com/en-us/graph/api/contactfolder-list-contacts?view=graph-rest-1.0
- https://learn.microsoft.com/en-us/graph/api/contact-delta?view=graph-rest-1.0

### 8.2 C1 — framework provider primitives

Add provider-only support under `microsoft_graph`, likely:
- `microsoft_graph/spiders/contacts.py` or a clearer Outlook-personal-contacts location;
- `microsoft_graph/items/contacts.py`.

Provider spider owns:
- `Contacts.Read`;
- `/me/contacts`;
- `/me/contactFolders`;
- encoded child-folder path;
- contacts-under-folder path;
- per-folder contacts delta path;
- optional provider field sets;
- opaque continuation behavior via existing Graph helpers.

Do not put catalog, provenance, reconciliation, or Topic identity in the framework.

Provider items:
- ContactFolder provider projection: id, displayName, parentFolderId, raw.
- Contact provider projection: stable useful fields such as id, displayName, givenName, surname, initials, nickName, title, companyName, department, jobTitle, emailAddresses, businessPhones, homePhones, mobilePhone, birthday, personalNotes only if explicitly accepted by privacy/product policy, parentFolderId, lastModifiedDateTime if supplied, raw.
- preserve nested provider values and falsey values;
- raw identity retained.

Do not over-project every Graph contact property. Raw JSON remains the provider representation.

### 8.3 C2 — discovery and folder inventory

The default Contacts folder is read via `/me/contacts`.

Custom contact folders:
- enumerate `/me/contactFolders`;
- recursively follow childFolders where the API permits;
- collect contacts for each folder;
- preserve folder hierarchy;
- follow opaque nextLinks.

Do not assume `/me/contactFolders` is itself the default contacts collection.

Discovery is evidence-first.

### 8.4 C3 — delta and reconciliation

Contact delta is per folder:
`/me/contactFolders/{id}/contacts/delta`.

Use `Contacts.Read` only.

Before committing to a default-folder delta strategy, perform a real personal-account probe to establish how the default Contacts folder is addressed for delta in this account/API. Do not invent a well-known folder ID.

For folders that support delta:
- persist an opaque cursor per contact folder;
- follow nextLink/deltaLink exactly;
- apply explicit removed/tombstone observations;
- promote only after clean completion.

Folder inventory remains authoritative for folder existence. If no read-only folder-delta endpoint is validated for the chosen path, use clean folder snapshot reconciliation.

Default Contacts folder must still have a correct removal strategy:
- use validated delta if a stable folder identity is obtainable under `Contacts.Read`;
- otherwise use clean authoritative snapshot reconciliation for default contacts.

### 8.5 C4 — app storage

Add:
- application items with observed_at/evidence_id/run_id;
- contact folder records;
- contact current-state records;
- presence/removal state;
- per-folder checkpoint/candidate tables if delta is used;
- store/pipeline under shared CatalogService lock;
- source ID `MSGLOOM_CONTACTS_SOURCE_ID` defaulting to a clear value such as `microsoft-contacts-default`.

No Outlook mailbox source-target binding is required unless the implementation explicitly supports delegated/shared mailbox Contacts later. Initial scope is the signed-in personal account.

### 8.6 C5 — command

Use the one public Microsoft hierarchy, for example:

```console
scrapy microsoft contacts discover --page-size 100
scrapy microsoft contacts sync --page-size 100
```

If only one mode is justified, prefer `sync` after implementation. Do not create a second top-level Scrapy command.

Reject unrelated Mail/Calendar/To Do/OneDrive options.

### 8.7 C6 — Contacts tests and real acceptance

Synthetic:
- paths encode IDs once;
- Contacts.Read only;
- no write verbs/capabilities;
- recursive contact folder traversal;
- default contacts plus custom-folder contacts;
- opaque pagination;
- contact delta per folder;
- tombstone/removal;
- snapshot failure blocks absence inference;
- stale observations;
- source identity;
- privacy-safe stats;
- standalone framework imports.

Real:
- consent `Contacts.Read` if absent;
- list default contacts;
- list folders;
- traverse any real custom folders if present;
- execute delta for a real folder if the account has one;
- if the account has zero contacts/folders, successful empty responses still count for transport/auth acceptance, while synthetic tests cover nonempty behavior;
- never display personal contact names/addresses in status output.

Definition of done for Contacts:
**msgloom has a real-personal-account-validated, read-only, current-state personal Contacts source suitable for best-effort identity enrichment.**

---

# Part II — Parallelization and orchestration

## 9. Program dependency graph

```text
BASELINE / docs / manager bootstrap
        |
        +-------------------+-------------------+
        |                   |                   |
        v                   v                   v
   To Do T0-T5        OneDrive O1-O4       Contacts C1-C6
        |                   |                   |
        +---------+---------+---------+---------+
                  |
                  v
        Microsoft A1 completion gate
                  |
                  v
        Phase 1 foundation merge gate
                  |
          +-------+---------+----------+
          |                 |          |
          v                 v          v
     A2 parsing       A2 group/filter  A3 foundations
          |                 |          |
          +--------+--------+          |
                   |                   |
                   v                   v
             Prepared groups ---> semantic triage
                                  |
                                  v
                              saved topics
                                  |
                                  v
                            A5 reporting
                                  |
                                  v
                       Phase 1 end-to-end gate
```

Important: Phase 1 **preparation work** may begin while Microsoft source workers run, as long as it does not change source semantics or depend on unfinished schemas.

---

## 10. Worktree strategy

The manager owns integration.

Create one temporary git worktree/branch per implementation lane, all from the exact baseline/integration head chosen by the manager. Example:

- `worktrees/todo-sync`
- `worktrees/onedrive-resync`
- `worktrees/contacts`
- `worktrees/phase1-foundation`
- later parser/triage/report worktrees.

Rules:
1. no two workers edit the same worktree;
2. ChatGPT worker prompts include the exact worktree path and branch;
3. workers do not push directly to `master`;
4. manager reviews commits/diffs and integrates/cherry-picks/merges serially;
5. manager resolves conflicts, then reruns affected focused tests;
6. only manager pushes integration/master after gates pass;
7. unrelated pre-existing untracked files are never staged or modified;
8. each worker must report changed files, tests run, limitations, and commit SHA if it commits its lane.

When a worker cannot edit through the local connector, it must return a unified diff or precise patch instructions. The manager may apply that patch. Do not replace the worker with a local Codex/Claude sub-agent.

---

## 11. ChatGPT worker orchestration

The local manager must use the installed `chatgpt-web-operations` skill:

```text
~/.claude/skills/chatgpt-web-operations/
~/.codex/skills/chatgpt-web-operations/
```

Read:
- `SKILL.md`
- `references/worker-rounds.md`

### 11.1 Mandatory worker model

Workers are ChatGPT conversations sent through the skill tooling, not:
- `codex exec` child agents;
- `claude --agents`;
- Claude subagents;
- Codex local sub-agent commands.

The top-level local manager itself may be Codex or Claude. It may use shell/git/tests and integrate worker output.

### 11.2 Preflight and rate limits

Before sending workers:
```bash
S="$HOME/.claude/skills/chatgpt-web-operations/scripts"
python3 "$S/preflight.py" --workdir /home/grammy-jiang/Projects/msgloom --browser
```

If blocked by a temporary browser slot or account rate limit:
1. do not ask the user;
2. continue local preparation;
3. create worktrees;
4. write all worker prompts;
5. build fixtures/interfaces/tests that do not need ChatGPT;
6. periodically rerun preflight at a conservative interval;
7. send workers immediately when GO/usable;
8. never hammer a rate-limited endpoint.

### 11.3 ChatGPT project

Prefer a dedicated ChatGPT Project for this implementation round so worker chats do not clutter the main list.

If an existing suitable msgloom worker project exists, reuse it. Otherwise create one with the skill tooling and record its project ID in local orchestration state.

Record profile context once before worker sends.

### 11.4 Local-repository connector

Discover the existing ChatGPT custom connector that exposes the Pi/project workspace. Prefer the already configured local MCP/Binnacle-style connector if healthy.

If a connector is usable:
- pin each worker send to that connector with the documented `--system-hint plugin:...`;
- give each worker only its worktree path.

If no usable connector is available:
- do not block;
- workers return patches/review artifacts;
- manager applies them locally.

### 11.5 Concurrency

Browser sends may need to be serialized, but ChatGPT turns run concurrently after posting.

Initial ChatGPT worker round, send with `--no-wait`:
1. **W-TODO** — To Do capability probe design + authoritative sync implementation.
2. **W-ONEDRIVE** — OneDrive 410 resync + content-version linkage.
3. **W-CONTACTS** — Contacts framework/app implementation.
4. **W-P1-FOUNDATION** — Phase 1 provider-neutral operation/result/persistence foundation and architecture-gap spike; must not modify A1 source behavior.
5. **W-P1-PARSER-PREP** — parser dependency/fixture qualification plan and isolated parser contracts; no broad dependency merge yet.
6. **W-REVIEW** — read-only architecture/security integration review of the above planned changes; no implementation ownership.

Manager should collect workers as they finish, not wait for the slowest before integrating an independent lane.

### 11.6 Worker prompts

Every worker prompt must contain:
- exact worktree path;
- exact baseline SHA;
- assigned files/scope;
- required design docs;
- relevant current implementation files;
- explicit non-goals;
- tests and acceptance;
- no personal data in output;
- no write Graph scopes;
- instruction to use installed Scrapy skill for Scrapy work;
- instruction not to change other lanes;
- expected final report format.

Workers must not be told vague prompts such as “finish To Do”.

---

# Part III — Phase 1 implementation after Microsoft source completion

## 12. Phase 1 current state

The repository is strong in A1 collection but does not yet contain a complete A2/A3/A5 product chain.

Phase 1 enabled path:

```text
A1 Collection -> A2 Preparation -> A3 Triage -> A5 Reporting
```

Teams must not block this path. Use real Outlook/To Do/OneDrive/Contacts plus synthetic Teams fixtures for shared contracts until a work/school account becomes available.

---

## 13. P0 — provider-neutral application foundation

This lane may prepare in parallel with Microsoft source completion but should not be integrated until its contracts are reviewed.

### 13.1 Package structure

Do not force exact names if existing repository conventions suggest better ones, but target responsibilities such as:

```text
msgloom/ or message_ingest/application/
  config/
  application/
  persistence/
  preparation/
  triage/
  reporting/
  cli/
```

Do not put A2/A3/A5 inside `microsoft_graph`.

### 13.2 Operation contract

Implement typed provider-neutral:
- OperationRequest;
- OperationOutcome;
- execution identity;
- capability enum;
- target input/version references;
- terminal status:
  - complete
  - incomplete
  - failed
  - blocked
  - cancelled;
- limitations;
- external-effect state.

Later capabilities A4/A6/A7 must be rejected before adapter/client construction.

### 13.3 Stage result/lineage contract

Every stage result must record:
- result kind;
- schema version;
- input references;
- source/prepared/topic versions;
- configuration version;
- code version/build identifier;
- rule version;
- prompt version;
- model identifier where applicable;
- working-context snapshot reference;
- attempt identity;
- terminal status;
- exposed AI output/diagnostics where applicable;
- limitations/failures.

Reruns create new results. Never overwrite accepted historical outcomes.

### 13.4 Claims and ordered execution

Implement a provider-neutral durable claim model for:
- preparation work;
- triage work;
- report build/submission.

A dependent stage starts only after its input result is durably complete/acceptable.

No in-package daemon/queue.

### 13.5 Persistence spike

Perform the async-vs-existing-catalog spike described in Section 4.2. The manager records the decision in a design note before merging a broad persistence pattern.

---

## 14. A2 Preparation

### 14.1 Prepared record contract

A prepared source record preserves:
- source identity and source record/version;
- author/sender;
- recipients;
- source timestamp;
- body content;
- source-native relationships;
- attachment references;
- parsed attachment content references;
- missing/unsupported/partial limitations;
- deterministic filtering disposition;
- exact source mappings/locations.

Do not flatten away tables, cells, pages, blocks, links, or meaningful order.

### 14.2 Parser worker contract

Parser workers:
- receive already-saved bytes;
- run under bounded resources;
- write only isolated temporary output;
- return structured extraction + source locations + limitations;
- cannot mark attempts complete directly;
- are awaited;
- are terminated/reaped on timeout.

### 14.3 Parser lanes

After the foundation schema is stable, parallelize:

**PARSER-MIME/HTML**
- standard-library email;
- encoding/MIME relationships;
- selectolax HTML extraction qualification;
- meaningful text/table/link order.

**PARSER-EXCEL**
- python-calamine primary;
- cell coordinates/types/sheets/hidden-content policy;
- targeted openpyxl metadata fallback;
- formulas vs cached values.

**PARSER-PDF**
- follow current tech-stack proposal after verifying exact current dependency choice;
- page/source mapping;
- scanned/incomplete limitation;
- OCR only where explicitly permitted by design.

**PARSER-WORD**
- paragraph/table/block order;
- source mapping;
- unsupported embedded object limitations.

Before adding dependencies, update the lockfile once through a manager-owned dependency integration lane. Avoid workers independently rewriting `uv.lock`.

### 14.4 Filtering

Deterministic filters:
- typed validated configuration;
- exact sender/address predicates;
- subject pattern predicates;
- source scope predicates;
- timestamps with timezone;
- explicit exclusion/guidance result.

Save matched rule and disposition. Excluded content remains replayable.

### 14.5 Grouping

Phase 1 grouping:
- Outlook email: source-native conversation membership is candidate/support; normalized subject alone never confirms identity.
- Teams channel fixtures: root/reply relation.
- Teams chat fixtures: messages stay separate unless supported relationship exists.
- To Do/OneDrive/Contacts are contextual sources and must not automatically create communication groups.

Grouping result:
- Confirmed / Uncertain / None;
- members;
- method;
- evidence;
- reason.

No cross-source semantic joining in Phase 1.

---

## 15. A3 Triage

### 15.1 Deterministic triage

Typed rules may produce:
- exclusion;
- required priority;
- minimum priority;
- guidance.

Conflicts are explicit review items. Rule order must not silently resolve conflicting constraints.

Priority:
Critical > Important > Normal > Low-value.

Pending or failed processing is never Low-value by default.

### 15.2 Working context

Read only configured memory paths.

Create immutable/versioned working-context snapshots:
- selected files/content references;
- capture time;
- configuration;
- missing/stale state;
- hash/version.

Do not alter interactive ChatGPT/Claude memory or sessions.

### 15.3 AI runner

Follow the Phase 1 architecture:
- fresh SDK-managed Claude Code session per analysis attempt;
- no resume of daily sessions;
- isolated settings/session/work directory;
- no source credentials in AI process;
- disable shell/file editing/source discovery/report sending in AI runner;
- expose only declared data inputs;
- save exposed SDK messages and diagnostics;
- close session on success/failure/cancel.

Use the Claude Agent SDK Python interface selected in the design unless a current qualification demonstrates a required change.

### 15.4 Structured triage result

Validate with Pydantic.

A result binds topics to:
- source records;
- rule matches;
- priority;
- reason;
- developments;
- actions;
- action owner;
- deadlines including original wording;
- interpreted date + timezone basis;
- risks;
- limitations;
- source vs interpretation distinction.

Every included source record gets:
- a topic mapping; or
- explicit disposition.

### 15.5 Topic identity

Do not use AI-generated titles as identity.

Implement stable topic identity/relationship records with evidence and versioning.

A group may produce several topics.

Continuation of a prior topic requires explicit supported linkage; otherwise remain separate/uncertain.

---

## 16. A5 Reporting

### 16.1 Report selection

Report policy selects by:
- priority;
- due criteria;
- destination;
- previous report state;
- reminder policy.

Track reporting state per policy + assessment version, never a global sent flag.

Freeze selected versions before rendering.

Pending newer triage must produce a visible warning rather than silently presenting stale results as current.

### 16.2 Saved report

Persist:
- report identity;
- selection snapshot;
- topic assessment versions;
- overview;
- topic details;
- evidence/source references;
- limitations/pending work;
- renderer version;
- output parts.

Coverage validation before and after rendering:
- every due topic identity;
- essential action;
- deadline;
- risk;
- required details reachable.

### 16.3 Rendering

Jinja2 HTML + plain text.

Email itself must satisfy Phase 1 report contract; no required information may exist only behind a future website link.

Multipart reports preserve one report identity and explicit topic-to-part mapping.

### 16.4 Delivery

Deliver only to the owner under configured destination.

Persist attempt before external submission.

States:
- accepted submission;
- confirmed delivery if observable;
- rejected;
- unknown.

Unknown outcome is not automatically resent. Retry reuses the exact saved report/output and does not rerun triage.

No other external business action is enabled.

---

## 17. Application / CLI

The Phase 1 package must have one explicit async application boundary.

CLI:
- one event loop;
- explicit finite subcommands;
- manual execution works without scheduler;
- help/config inspection requires no source credentials/AI startup;
- process exits only after requested operation reaches a saved terminal outcome.

External scheduler:
- deployment-only;
- do not add Prefect as a package runtime dependency merely to schedule work.

Recommended operation families, names to finalize against existing command conventions:
- collect/sync sources;
- prepare;
- triage;
- report build;
- report submit;
- replay;
- status/config inspection.

Microsoft Scrapy commands may remain provider-specific low-level/operator tools while the product Application composes higher-level operations.

---

# Part IV — Integration gates and acceptance

## 18. Gate M1 — To Do complete

Pass only when Section 6 definition is met and full regression is green.

## 19. Gate M2 — OneDrive complete

Pass only when Section 7 definition is met and existing real content/delta acceptance still passes.

## 20. Gate M3 — Contacts accepted

Pass only after real personal-account auth + at least transport-level live acceptance using `Contacts.Read`.

## 21. Gate M4 — Microsoft A1 closeout

Requirements:
- M1/M2/M3 green;
- Outlook Mail/Calendar regressions green;
- Teams blocker documented;
- framework reverse dependency zero;
- no write Graph scopes added;
- docs reconciled with implemented Scrapy architecture;
- stop adding Microsoft products.

## 22. Gate P1 — Phase 1 foundation

Requirements:
- typed Operation contracts;
- stage-result/lineage model;
- durable claims;
- persistence decision recorded;
- later capabilities blocked before adapter construction;
- async non-CLI caller contract test.

## 23. Gate P2 — A2 accepted

Requirements:
- common attachment acceptance fixtures;
- parser resource limits;
- source mappings;
- deterministic filters;
- grouping statuses;
- replay/version behavior;
- no AI required for mechanical grouping/filtering.

## 24. Gate P3 — A3 accepted

Requirements:
- deterministic rules;
- conflict behavior;
- working-context snapshot;
- isolated AI runner;
- validated structured output;
- complete source dispositions;
- stable topic identity;
- user-reviewed fixture set can measure missed important work/wrong grouping.

## 25. Gate P4 — A5 accepted

Requirements:
- saved report;
- overview + topic detail;
- all due topic coverage;
- HTML/plain text;
- owner-only delivery;
- unknown delivery outcome reconciliation;
- replay does not accidentally redeliver.

## 26. Gate P5 — Phase 1 end-to-end

Exercise `docs/phase-1/design.md#7-acceptance-cases`:

1. restart during collection;
2. message edit/move/repeated page;
3. same subject, different work;
4. several topics in one group;
5. conflicting rules/malformed AI;
6. missing memory/attachment content;
7. many important topics;
8. timeout after submission;
9. replay with changed prompt;
10. common Excel/PDF/Word attachments;
11. ordered execution;
12. scheduler-free invocation.

Teams cases may use synthetic fixtures while the personal-account blocker remains explicitly recorded.

---

## 27. Test policy

Every lane:
- TDD/focused tests first;
- no weakening an existing test merely because architecture changed;
- real API only after synthetic behavior is stable;
- no personal data in test fixtures;
- no provider IDs in stat keys.

Before each integration commit:
- focused pytest;
- relevant Scrapy contract;
- Ruff check;
- Ruff format check;
- Pyright for touched source.

Before push to master:
```bash
.venv/bin/pytest -q
.venv/bin/ruff check microsoft_graph message_ingest tests
.venv/bin/ruff format --check microsoft_graph message_ingest tests
pyright microsoft_graph message_ingest
.venv/bin/scrapy check
git diff --check
```

Also:
- reverse-coupling scan for `microsoft_graph`;
- forbidden write scope/verb scan;
- package/module size review;
- git status review excluding unrelated untracked files.

Phase 1 later adds:
- Python 3.12/3.13/3.14 qualification after dependency lock stabilizes;
- representative semantic acceptance fixtures;
- event-loop responsiveness tests for parser workers;
- cancellation/resource cleanup.

---

## 28. Commit and integration policy

Prefer small logical commits:

1. To Do capability probe/tests;
2. To Do authoritative sync;
3. OneDrive resync;
4. OneDrive content version linkage;
5. Contacts framework;
6. Contacts app/sync;
7. Microsoft A1 docs closeout;
8. Phase 1 foundation;
9. parser lanes;
10. grouping/filter;
11. triage;
12. reporting;
13. end-to-end acceptance.

Do not combine unrelated research/untracked artifacts.

Manager may squash lane noise before integration but must preserve meaningful review boundaries.

Push only green integration commits.

---

## 29. Security checklist

For every worker and integration:
- no tokens/device codes/account IDs/contact names/emails/file names in public logs or worker transcripts unless unavoidable and explicitly redacted;
- no Authorization on non-Graph redirects;
- opaque continuation URLs never emitted by ordinary logging;
- raw evidence owns source bytes;
- AI process gets no source credentials;
- no Graph write scopes for this program;
- no business-action adapter enabled in Phase 1;
- report destination restricted to owner;
- unknown external effect never triggers blind retry.

---

## 30. Manager completion/reporting format

The manager maintains a local orchestration ledger with:
- lane;
- worker conversation ID/URL;
- ChatGPT project ID;
- worktree;
- branch;
- baseline SHA;
- state;
- blocker;
- latest commit;
- test result;
- review result;
- integrated SHA.

Status reports to the supervising session should be concise:
- completed;
- active;
- blocked;
- next integration gate;
- test counts;
- any architecture decision.

Never say work is running unless a real local process or ChatGPT turn is actually active.

---

## 31. Immediate first actions for the manager

Execute these without waiting for product-owner input:

1. verify `HEAD == origin/master == c3227ab89092f97b9a3e7e5025d2ce3cd7c2287b`;
2. run/record the 984-test baseline if not already freshly verified;
3. read the authoritative docs in Section 2;
4. read installed `scrapy-framework-development` skill;
5. read `chatgpt-web-operations/SKILL.md` and `references/worker-rounds.md`;
6. create orchestration directory under `/tmp/msgloom-next-program/`;
7. create per-lane worktrees;
8. prepare W-TODO/W-ONEDRIVE/W-CONTACTS/W-P1-FOUNDATION/W-P1-PARSER-PREP/W-REVIEW prompts;
9. run ChatGPT preflight;
10. while preflight is blocked, locally prepare:
    - current schema maps;
    - test fixture maps;
    - To Do live delta probe script/command that does not request write scopes;
    - OneDrive 410 fixture;
    - Contacts synthetic fixtures;
    - Phase 1 persistence spike checklist;
11. when ChatGPT preflight becomes usable, send all worker prompts sequentially with `--no-wait` so turns execute concurrently;
12. collect finished workers continuously and integrate independent lanes;
13. run real Graph acceptance locally after synthetic merges;
14. continue through M1-M4 and then P1-P5 without waiting for another user message unless an external credential/account action genuinely cannot be completed automatically.

If a real Microsoft consent screen for `Contacts.Read` requires user interaction while the owner is unavailable, continue every nonblocked synthetic/integration task and leave only that real acceptance gate pending. Do not request a broader permission to avoid consent.

---

## 32. Final program exit condition

This program is complete when:

- To Do is a trustworthy read-only current-state mirror;
- OneDrive safely recovers expired cursors and knows explicit-content freshness;
- Contacts is a real-personal-account-validated identity/context source;
- Teams is explicitly blocked, not silently omitted;
- Microsoft source expansion is closed;
- source data can flow through A2 Preparation, A3 Triage, and A5 Reporting;
- the Phase 1 acceptance cases pass;
- all output remains traceable to source evidence and versions;
- the user can receive a complete owner-only report without any business-action capability being enabled.
