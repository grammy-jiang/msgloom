# A1 Microsoft Graph ownership finalization plan

**Status:** design/implementation plan only; no production refactor has started
**Prepared:** 2026-10-08
**Coordination-plan branch:** `program/a1-teams-spider`
**Implementation branches:** `master` + `program/a1-teams-spider`
**Branch invariant:** Teams-only code changes go to the Teams branch; every other
code change goes to `master`
**Final integration:** rebase `program/a1-teams-spider` onto the final accepted
`master` SHA before final convergence
**Rebased candidate at plan entry:** `4ba461a41ee6068a9de4c56f0ffcd42db2351517`
**Current master base:** `4502efa117e753e47e1fbbeb6ed61881a85c9c18`
**Runtime authority:** Scrapy 2.19.0 from the project virtual environment

## 1. Purpose

A1 is functionally complete enough to expose the next architectural risk: the
Microsoft Graph provider/application ownership line is mostly correct but not
fully closed.

This plan performs one final A1-only ownership cleanup before A2 implementation.
It has two symmetric goals:

1. `microsoft_graph/` must contain every reusable Microsoft Graph / Scrapy
   provider mechanic that another consumer could reuse without msgloom.
2. `microsoft_graph/` must contain no msgloom business state, selected
   acquisition profile, completeness policy, persistence concept, A1/A2 stage
   concept, or product privacy decision.

The result is not a new framework. It is a narrowing and completion of the
existing Graph-over-Scrapy framework boundary.

## 2. Entry evidence

The branch was rebased onto current `master` before this plan was written.
Focused post-rebase verification already passed on two Raspberry Pis:

- Pi 1 framework/provider shard: 173 passed;
- Pi 1 framework/application-composition shard: 71 passed;
- Pi 2 Teams/raw-evidence/source-reader shard: 426 passed;
- total focused tests: 670 passed, 0 failed.

The current dependency direction is already correct:

```text
message_ingest
      |
      v
microsoft_graph
      |
      v
Scrapy 2.19.0
```

`microsoft_graph/` has no import dependency on `message_ingest`, `msgloom`, or
SQLAlchemy. That remains necessary but is no longer considered sufficient proof
of a clean boundary.

## 3. Authoritative ownership contract

### 3.1 `microsoft_graph/` owns reusable provider mechanics

The framework owns only behavior that is true because Microsoft Graph or Scrapy
works that way, independently of msgloom's product choices:

- Graph service-root and host handling;
- Graph request construction;
- opaque continuation behavior;
- path-segment encoding and Graph path/query construction;
- provider query constraints and provider maximum bounds;
- pure Graph collection/delta/error envelopes;
- pure provider resource parsing/projection;
- provider tombstone shape validation;
- provider-specific response mechanics such as safe OneDrive 410 reset-location
  extraction;
- representation headers required by a Graph endpoint;
- MSAL/auth session mechanics;
- downloader auth/retry/error/diagnostics/privacy behavior;
- provider request fingerprinting;
- endpoint-specific helpers that do not choose a msgloom acquisition profile;
- reusable Scrapy add-on/components.

A useful test is:

> Could an unrelated Scrapy application use this code without adopting a
> msgloom source ID, database, evidence model, completeness definition, privacy
> profile, or A1 workflow?

If yes, the code may belong in `microsoft_graph/`.

### 3.2 `message_ingest/` owns application policy and durable semantics

The application owns behavior that exists because msgloom decided what to
capture, retain, prove, publish, or hand to downstream stages:

- source ID/source binding/source-target identity;
- selected acquisition profiles and permission bundles;
- selected field/projection sets;
- privacy-driven field inclusion/exclusion policy;
- page-size defaults chosen for an acquisition profile;
- raw HTTP evidence and content-addressed payload storage;
- run IDs and run integrity;
- application request purpose/context;
- catalog/SQL/pipelines;
- checkpoints and promotion;
- JOBDIR application execution state;
- absence/deletion inference;
- evidence-before-semantics ordering;
- detail/full/hydration completeness;
- limitation/coverage/history-gap semantics;
- notification delivery bookkeeping and source binding;
- A1 release/handoff and all A2-facing semantics;
- commands/workflows/product UX.

A second test is:

> Would changing msgloom's product scope, privacy posture, completeness
> definition, or downstream contract require this value to change?

If yes, it belongs in `message_ingest/`, even when it contains Graph field or
permission names.

### 3.3 Branch ownership contract

This cleanup has two implementation branches, and branch ownership is stricter
than checkpoint/lane ownership.

#### `master` owns every non-Teams change

A change belongs on `master` unless its reason for existence is directly and
exclusively Microsoft Teams behavior.

`master` therefore owns:

- reusable Graph/Scrapy mechanics that are provider-generic rather than
  Teams-specific;
- Outlook Mail and Calendar changes;
- Contacts changes;
- OneDrive changes;
- To Do and user/profile changes if any are required;
- generic Graph delta/tombstone/continuation/request helpers;
- generic architecture/package-boundary tests and guardrails;
- non-Teams documentation corrections;
- any bug discovered during this work whose behavior is not Teams-specific.

Concretely, F3 Mail/Contacts, F6, F7, F8, and F9 are `master` work.

The existing `master` development worktree contains unrelated untracked
research/output artifacts. They are outside this task and must remain untouched:

- never use `git clean` on the master worktree for this cleanup;
- never use broad `git add .` / `git add -A` when preparing these commits;
- stage only explicit task-owned paths;
- do not reset or delete unrelated untracked files to obtain a clean status;
- use the dedicated clean synchronized test worktrees for broad/distributed
  validation rather than treating the master development worktree as a clean
  test checkout.

#### `program/a1-teams-spider` owns Teams-only changes

The Teams branch owns only changes whose reason for existence is Teams support,
including:

- `microsoft_graph` Teams provider items/protocol/path/query helpers;
- Teams notification protocol and intake behavior;
- Teams T1/T2 application scope/profile selection;
- Teams-specific projection/page-size policy;
- Teams acquisition completeness/limitation state;
- `message_ingest` Teams spiders/items/pipelines/readers;
- Teams-specific tests and documentation;
- a shared package export or registration change only when its sole purpose is
  to expose/register a Teams-specific symbol.

Concretely, F1, F2, the Teams portion of F3, F4, and F5 are Teams-branch work.

#### No mixed commits

A commit must not contain both Teams-only implementation and unrelated
non-Teams/shared implementation. If one conceptual fix spans both categories,
split it:

1. implement the reusable/non-Teams foundation on `master`;
2. finish and validate that `master` change;
3. rebase the Teams branch onto the resulting master when the master lane is
   frozen;
4. implement or adapt only the Teams-specific consumer delta on the Teams
   branch.

Do not cherry-pick non-Teams implementation commits into the Teams branch as a
substitute for the final rebase. Do not make an opportunistic Mail, Contacts,
OneDrive, Calendar, or generic Graph fix in the Teams worktree just because that
is where a failing test was observed.

For shared files, classify the *reason for the edit*, not the path. A generic
framework change belongs on `master`; a Teams-only export/registration delta may
belong on the Teams branch. If both branches need to touch the same shared file,
make the generic master edit first and preserve both changes during the final
rebase.

This coordination plan may remain on the Teams branch as documentation. That is
not an exception allowing non-Teams production code to be developed there.

### 3.4 Important distinction: provider constraint vs selected policy

Do not move every Graph-looking constant into the framework.

Examples:

- `page_size <= 50` because an endpoint documents 50 as a maximum: provider
  mechanic -> framework.
- `page_size = 50` because msgloom wants maximum throughput: application policy
  -> application.
- a helper that accepts `$select`: provider mechanic -> framework.
- the exact fields msgloom selects for Discovery-v1: application profile ->
  application.
- `ChannelMessage.Read.All` as an endpoint permission fact: provider knowledge
  may be represented by a narrow capability helper/test.
- the five-scope "complete T2" bundle: msgloom acquisition profile ->
  application.

## 4. Scope of this cleanup

This cleanup covers the current A1 Microsoft acquisition implementation:

- shared Graph transport/auth/protocol;
- Outlook Mail;
- Outlook Calendar;
- Contacts;
- To Do;
- OneDrive;
- user/profile;
- Teams chat/channel/notification support.

It includes tests and architecture guardrails needed to preserve the boundary.

## 5. Explicitly out of scope

Do not use this cleanup to implement or redesign:

- A2 or Kedro;
- A3/A5;
- new Microsoft products or endpoints;
- Teams T3/T4/T5;
- application-only Teams acquisition;
- new write Graph permissions;
- a Microsoft Graph Python SDK;
- a second HTTP transport;
- new live-tenant acceptance claims;
- authoritative absence semantics where A1 currently does not provide them;
- broad renaming or style cleanup without ownership value.

No behavior should be removed merely to make the boundary look smaller.

## 6. Confirmed findings at plan entry

The implementation phase starts from these confirmed findings rather than doing
another broad rediscovery pass.

### F1 — Teams notification protocol carries msgloom source state `[TEAMS]`

Current location:

```text
microsoft_graph/protocol/teams_notifications.py
    TeamsTrustedSubscription.source_id
```

`source_id` is a msgloom acquisition identity, not a Microsoft Graph
notification protocol property.

Target:

- remove `source_id` from the framework subscription model;
- load/validate the application's source binding in
  `message_ingest/spiders/microsoft/teams/_notification_intake.py` or a small
  adjacent application model;
- pass only provider/security subscription facts into the framework parser.

Also re-evaluate framework-owned `gap_kind`. Graph lifecycle events are provider
facts; interpreting them as a durable history/coverage gap is application
semantics. Prefer returning normalized lifecycle facts from the framework and
mapping them to `gap_kind` in `message_ingest`.

### F2 — Teams provider items contain acquisition completeness semantics `[TEAMS]`

Current location:

```text
microsoft_graph/items/teams/channel.py
    TeamsTeamItem.detail_complete
    TeamsTeamItem.detail_limitation
    TeamsChannelItem.detail_complete
    TeamsChannelItem.detail_limitation
```

`associated` / `joined` / `detail` identify the provider representation and may
remain provider provenance. `detail_complete` and `detail_limitation` state what
msgloom has or has not completed and why; those are application semantics.

Target:

- keep pure provider representation/topology in `microsoft_graph`;
- move completeness/limitation state to `message_ingest` Teams topology or
  coverage items;
- preserve existing durable output and public reader behavior.

### F3 — acquisition field/profile policy exists in the framework `[SPLIT]`

Confirmed examples:

```text
microsoft_graph/spiders/outlook/mail.py
    discovery_fields
    full_fields
    folder_fields

microsoft_graph/spiders/contacts.py
    contact_select_fields
    folder_select_fields

microsoft_graph/spiders/teams/channel_paths.py
    CHANNEL_SELECT_FIELDS
```

The Contacts implementation explicitly excludes `personalNotes` pending a
privacy decision, proving that this selection is product policy rather than a
provider requirement.

Target:

- framework path/query helpers continue accepting caller-selected fields;
- selected field tuples move into application profile modules/spiders;
- existing wire queries stay byte-for-byte equivalent unless a current test
  proves the old query was invalid.

### F4 — Teams T1/T2 scope bundles are product profiles `[TEAMS]`

Current examples:

```text
microsoft_graph/spiders/teams/chat.py
    T1-oriented scope/profile wording

microsoft_graph/spiders/teams/channel.py
    complete-T2 five-scope graph_permissions bundle
```

The complete T2 bundle is explicitly a msgloom-selected production profile and
contains permissions for multiple optional capabilities. It is not a minimal
requirement for every consumer of the provider path helpers.

Target:

- framework helpers remain usable without silently requesting the whole msgloom
  T1/T2 profile;
- framework may expose narrow provider permission facts/constants per capability,
  but must not compose the product's T1/T2 bundle implicitly;
- exact T1/T2 selected scope sets move to Teams application spiders/profile
  constants; the minimal implementation is for the concrete application spiders
  to declare/compose those provider scope constants;
- standalone provider tests prove helpers are not coupled to the application
  permission profile;
- application tests prove msgloom still requests the exact selected scopes.

### F5 — selected Teams query defaults are mixed with provider constraints `[TEAMS]`

Current examples include fixed/frozen page sizes and selected channel
projection fields in the framework.

Target:

- retain provider max validation in the framework;
- move profile-selected defaults/projections into `message_ingest`;
- avoid replacing simple arguments with a new configuration framework.

### F6 — OneDrive 410 reset-location validation remains application-local `[MASTER]`

Current location:

```text
message_ingest/spiders/microsoft/onedrive/delta.py
    _resync_location()
```

Validating the provider's 410 `Location` as an exact safe same-origin Graph URL
is provider mechanics.

Target:

- move the pure extraction/validation helper into a narrowly scoped OneDrive
  provider/protocol module;
- application keeps reset-attempt policy, checkpoint policy, evidence redaction,
  and whether/when to resync.

### F7 — Mail/folder delta still inspects opaque token text `[MASTER]`

Current application code checks `$deltatoken=` / `$skiptoken=` to decide whether
an URL is provider-owned/opaque.

Target:

- stop interpreting opaque continuation/cursor bytes;
- make request construction explicit from known request provenance
  (initial/continuation/checkpoint/reset);
- use `continuation_request()` / `verbatim_url=True` based on provenance, never
  substring inspection.

### F8 — repeated Graph tombstone parsing remains in application callbacks `[MASTER]`

Mail message delta, Mail folder delta, and Calendar delta independently parse
and validate `@removed`.

Target:

- add the smallest pure framework helper needed to validate/read the Graph
  tombstone shape;
- keep semantic interpretation in each application callback (mail folder
  membership removal vs event removal vs other domain meaning);
- do not create a generic delta workflow abstraction.

### F9 — duplicated `Prefer` composition remains in application code `[MASTER]`

Mail delta currently reconstructs immutable-ID + page-size preferences even
though the provider base already owns immutable-ID representation and exposes
`compose_prefer()`.

Target:

- use the existing provider composition API;
- preserve exact header value/order expected by tests;
- do not add another header-composition utility.

## 7. Work breakdown

Implementation is split into six logical checkpoints, G0 through G5, but the
execution unit is a much smaller **micro-step**. Checkpoints are quality labels,
not barriers that force unrelated work to wait.

### 7.1 Hard parallelism and 30-minute micro-step rules

Every implementation micro-step is designed to fit inside one **less-than-30
minute** engineering timebox, including its narrow characterization/focused
verification. Use a target of roughly 20-25 minutes of active implementation so
there is margin for a focused test or repair. This is a scope constraint, not a
reason to stop and ask the user for approval.

Rules:

- if a proposed unit cannot reasonably fit the timebox, split it **before**
  implementation;
- if work reaches the timebox boundary without a coherent green result, preserve
  the smallest coherent subset, split the residual work into the next micro-step,
  and continue autonomously;
- a micro-step owns an explicit, non-overlapping production-file set; tests may
  overlap only when one coordinator owns the shared test file;
- do not assign two concurrent writers to the same production file;
- do not create a large "cleanup" commit spanning multiple independent
  ownership findings;
- characterization is **lane-local**: each lane adds or updates the test that
  proves its own boundary, then immediately implements that lane; unrelated
  lanes never wait for a global G0 test freeze;
- after a micro-step has a coherent candidate commit, dispatch its focused tests
  against that exact SHA and immediately continue with another disjoint
  micro-step while those tests run;
- a focused test failure blocks only that micro-step and its dependents, not the
  other branch or unrelated lanes;
- all repair work is itself another bounded micro-step;
- the full tracked suite remains a single final convergence activity, never a
  per-step requirement.

The plan should therefore run end-to-end without routine user decisions and
without any single implementation step becoming a long serial critical path.

### 7.2 Lane-local characterization instead of a global G0 barrier

G0 contains only the generic architecture guardrail that is truly shared. Every
resource lane owns its own characterization tests as part of its first
micro-step. Mail, Contacts, OneDrive, Teams notification, Teams topology, and
Teams profile work may all begin in parallel once their file ownership is
assigned.

## Checkpoint G0 — generic ownership guardrail

**Branch: `master`.** This checkpoint is intentionally tiny and does not block
resource-specific lanes.

One bounded micro-step (`M0-ARCH`) extends the existing framework package-layout
architecture test to cover only generic application-state leakage that can be
checked without Teams-specific/product-specific false positives. It preserves:

- standalone `microsoft_graph` imports without `message_ingest`, `msgloom`, or
  SQLAlchemy;
- no generic application identities such as `run_id`/`evidence_id` in reusable
  framework dataclasses where the rule is semantically valid;
- clear diagnostics when the boundary fails.

Mail/Contacts/OneDrive/Teams-specific characterization belongs to those lanes,
not here. As soon as `M0-ARCH` is committed it can be tested independently while
all other lanes continue.

## Checkpoint G1 — remove application state from Teams notification protocol/items

**Branch: `program/a1-teams-spider` only.**

This checkpoint has two disjoint lanes that may run in parallel after G0.

### Lane G1-A — notification boundary

Files likely owned by this lane:

```text
microsoft_graph/protocol/teams_notifications.py
message_ingest/spiders/microsoft/teams/_notification_intake.py
tests/test_teams_notification_protocol.py
tests/test_teams_notification_documented_payloads.py
tests/test_teams_notification_*.py
```

Work:

- remove application `source_id` from provider subscription state;
- move source matching to application input validation;
- move coverage-gap interpretation out of the framework if current tests confirm
  it is application-only;
- keep provider authentication, tenant/resource/clientState validation and
  notification resource parsing reusable;
- preserve wire-format validation and privacy behavior.

### Lane G1-B — team/channel provider item purity

Files likely owned by this lane:

```text
microsoft_graph/items/teams/channel.py
message_ingest/items/microsoft/teams/topology.py
message_ingest/items/microsoft/teams/coverage.py
message_ingest/spiders/microsoft/teams/_channel_topology.py
message_ingest/spiders/microsoft/teams/channel.py
related Teams provider/application/catalog tests
```

Work:

- provider objects retain provider representation and topology only;
- move hydration completeness/limitation to application state;
- preserve catalog schema and public saved-source behavior where possible;
- if persisted bytes/shape would otherwise change, adapt at the application
  projection boundary rather than migrating provider semantics into SQL.

### G1 checkpoint

- `microsoft_graph` contains no msgloom source identity or acquisition
  completeness state;
- provider notification/item tests remain standalone;
- application notification/topology tests pass.

## Checkpoint G2 — return selected acquisition profiles to `message_ingest`

Run three lanes in parallel; they own disjoint provider/application files.

### Lane G2-MAIL — `master`

Move from framework to application:

- Mail discovery field tuple;
- Mail full field tuple;
- Mail folder field tuple.

Framework retains:

- `messages_path(... fields=...)`;
- `message_path(... fields=..., expand=...)`;
- mail/folder delta path builders;
- immutable-ID provider representation behavior;
- own/shared mailbox path mechanics.

Preferred destination: keep the selected Mail tuples with the existing
application acquisition profile, for example
`message_ingest/acquisition/microsoft/outlook/email/profile.py`, unless the
current module split makes a smaller adjacent profile module clearer.

Update any handoff validation that currently imports the framework field tuple
to import the application profile contract instead.

### Lane G2-CONTACTS — `master`

Move from framework to application:

- selected folder projection;
- selected contact projection;
- the privacy decision that excludes `personalNotes`.

Preferred destination: one application-owned Contacts profile constant surface
under `message_ingest/acquisition/microsoft/contacts/` (or the existing Contacts
spider package if adding a package solely for two constants would be worse).
Do not put the privacy selection back into a provider item.

Framework retains:

- Contacts scope/path mechanics;
- folder ID encoding;
- caller-supplied `$select` and `$top` construction;
- pure Contact/Folder provider items.

### Lane G2-TEAMS — `program/a1-teams-spider`

Move to application:

- exact T1 selected scope set;
- complete T2 selected scope set;
- selected channel projection fields;
- selected page-size defaults where they are policy rather than API maximums;
- T1/T2 product terminology.

Preferred destination: one Teams application profile surface owns selected
T1/T2 permission sets, selected projections, and profile defaults. The concrete
Teams application spiders consume that surface; provider modules expose only
capability facts and mechanics.

Framework retains:

- endpoint path helpers;
- pure query construction;
- provider max bounds;
- representation requirements such as `include-unknown-enum-members` when the
  endpoint semantics require them;
- hosted-content consistency/representation mechanics;
- pure provider parsing.

### G2 checkpoint

- changing a msgloom acquisition profile no longer requires editing
  `microsoft_graph`;
- framework provider helpers remain independently useful;
- current application request bytes/scopes remain unchanged;
- no new permission is requested.

## Checkpoint G3 — finish remaining provider mechanics extraction

**Branch: `master` only.**

Run these disjoint provider lanes immediately in parallel with G2. They do not
depend on Mail/Contacts profile relocation. No G3 implementation is committed
to the Teams branch.

### Lane G3-ONEDRIVE

- move 410 reset `Location` extraction/same-origin validation into a narrow
  OneDrive provider helper;
- keep evidence redaction and retry/reset count policy in `message_ingest`;
- preserve the exact accepted Location bytes when safe.

### Lane G3-MAIL-DELTA

- remove `$deltatoken` / `$skiptoken` substring checks;
- derive opaque handling from known request provenance;
- use provider continuation/request helpers directly;
- replace hand-built immutable-ID/page-size `Prefer` values with
  `compose_prefer()` while preserving exact bytes.

### Lane G3-GRAPH-DELTA

- add one small pure tombstone helper or equally small provider primitive;
- use it from Mail message delta, Mail folder delta, Calendar delta, and any
  other duplicated A1 callback where it reduces genuine Graph parsing
  duplication;
- do not move traversal, checkpointing, failure items, or removal semantics into
  the framework.

### G3 checkpoint

- no application code constructs/decodes provider cursor structure;
- repeated provider tombstone validation is centralized;
- OneDrive provider response mechanics are reusable;
- application callbacks still own traversal and semantic decisions.

### 7.3 Bounded micro-step matrix

The detailed ownership rules in G1-G3 are executed using the following units.
Each row is independently assignable; dependencies are the only reason to wait.

| ID | Branch | Depends on | Exclusive production ownership / outcome | Focused verification |
| --- | --- | --- | --- | --- |
| `I1` | infra | none | Add `master` LAN sync channel and clean Pi 2 master test checkout/lock | SHA sync/status smoke |
| `I2` | infra | none | Add clean branch-specific test worktrees on Pi 1 plus exact-SHA test wrapper support | wrapper/lock smoke |
| `M0-ARCH` | master | none | generic package/semantic ownership guardrail only | package-layout test |
| `M1-MAIL-PROFILE` | master | none | move Mail discovery/full/folder selected fields from provider to application Mail base/profile; provider keeps path mechanics | Outlook provider + discovery/full profile tests |
| `M2-CONTACTS-PROFILE` | master | none | move Contacts selected/privacy fields to application profile; provider keeps caller-selected paths | Contacts provider + crawl tests |
| `M3-ONEDRIVE-410` | master | none | extract pure safe 410 Location validation to an existing OneDrive provider module or a directly imported narrow module; do not claim a shared package export during the parallel wave | OneDrive resync/reset tests |
| `M4-MAIL-MSG-CURSOR` | master | none | message delta: explicit opaque provenance + existing `compose_prefer()` | mail delta tests |
| `M5-MAIL-FOLDER-CURSOR` | master | none | folder delta: explicit opaque provenance + existing preference composition | folder-delta tests |
| `M6-TOMBSTONE-CORE` | master | none | add smallest pure Graph `@removed` validator/value primitive in a dedicated delta/protocol module; consumers may import it directly so no shared package export is required during the parallel wave | Graph protocol tests |
| `M7-TOMBSTONE-MSG` | master | `M4`,`M6` | consume tombstone primitive in message delta only | mail delta removal tests |
| `M8-TOMBSTONE-FOLDER` | master | `M5`,`M6` | consume tombstone primitive in folder delta only | folder removal tests |
| `M9-TOMBSTONE-CALENDAR` | master | `M6` | consume tombstone primitive in Calendar delta only | calendar delta tests |
| `T1-NOTIFY-SOURCE` | Teams | none | remove `source_id` from provider trusted subscription; preserve app input/source binding | notification protocol/intake tests |
| `T2-NOTIFY-GAP` | Teams | `T1` | provider returns lifecycle fact; app maps lifecycle to coverage `gap_kind` | notification reconciliation/reader tests |
| `T3-TOPOLOGY-COMPLETENESS` | Teams | none | move `detail_complete/detail_limitation` to application subclasses while preserving stored/public shape | channel provider + topology catalog/reader tests |
| `T4-CHAT-PROFILE` | Teams | none | move exact Chat T1 scope/profile terminology and selected chat page defaults to application ownership | chat provider/composition tests |
| `T5-CHANNEL-SCOPES` | Teams | none | move exact complete-T2 scope bundle to application ownership | channel provider/composition scope tests |
| `T6-CHANNEL-QUERY-PROFILE` | Teams | `T5` | make provider channel select/page helpers caller-driven; move selected projection/defaults to app | channel paths/provider/crawl tests |
| `M10A-MASTER-AUDIT` | master | `M0-M9` | read-only ownership scan; emit concrete findings only | static ownership scan |
| `M10B-MASTER-CLOSE` | master | `M10A` | bounded docs/guardrail/repair for M10A findings, focused static checks, freeze candidate; split multiple findings into `M10B-<n>` | changed-path tests + narrow static checks |
| `T7A-TEAMS-AUDIT` | Teams | `T1-T6` | read-only Teams ownership scan; emit concrete findings only | Teams ownership scan |
| `T7B-TEAMS-CLOSE` | Teams | `T7A` | bounded docs/guardrail/repair for T7A findings; split independent findings into `T7B-<n>` | Teams focused tests + narrow static checks |
| `R1A-REBASE-START` | Teams | `M10B`,`T7B` | fetch/freeze exact master SHA, verify clean Teams worktree, start rebase | branch/SHA checks |
| `R1-C<n>` | Teams | previous rebase step | resolve exactly one conflicting replayed commit or one tightly coupled conflict cluster, then continue rebase | conflict-affected tests/static parse only when useful |
| `R1B-REBASE-VERIFY` | Teams | rebase complete | verify merge-base, no merge commit, and Teams-only delta | merge-base + changed-path checks |
| `R2-POST-REBASE` | Teams | `R1B` | bounded Teams adaptation only where master generic contracts changed; split unrelated adaptations | conflict-affected tests only |
| `F1-FINAL` | integrated | `R2` | validation-only final full convergence on rebased Teams SHA | two-Pi full shard + static checks |

`M1` through `M6` can all run concurrently. After `M6` lands, `M9` can start
immediately; `M7` waits only for `M4`, and `M8` waits only for `M5`. On Teams,
`T1`, `T3`, `T4`, and `T5` can all start concurrently; `T2` waits only for
`T1`, and `T6` waits only for `T5`.

A unit may be subdivided further if source inspection reveals more than one
independent responsibility. It must never be enlarged merely to reduce commit
count.

## Checkpoint G4 — branch convergence and architecture audit

G4 freezes `master` first, then rebases the Teams branch onto that exact SHA.
There is no merge commit and no manual copying of non-Teams changes into the
Teams branch.

### G4-M — finalize `master`

Complete master micro-steps `M0` through `M9`, then run a fresh read-only
master-side ownership audit in `M10A`; apply any bounded findings in `M10B-<n>`
and freeze in `M10B`.

Required checks on `master` (audit first, repair in separately bounded
micro-steps):

1. zero imports from `microsoft_graph` to `message_ingest`, `msgloom`, or
   SQLAlchemy;
2. standalone framework imports with consumer modules blocked;
3. non-Teams selected acquisition profiles live in `message_ingest`;
4. non-Teams application code does not duplicate Graph mechanics now provided
   by the framework;
5. focused tests/static checks for the changed master files are green;
6. no Teams implementation has been added to `master` as part of this cleanup.

Once these checks pass:

- create the final master candidate commit(s);
- push `master` to origin;
- record the exact master SHA;
- treat that SHA as frozen for the rebase unless a later test proves a genuine
  non-Teams defect.

### G4-R — mandatory final rebase sequence

Rebase `program/a1-teams-spider` onto the recorded final `master` SHA. The
rebase is an orchestration sequence, not one large implementation step:

```text
git fetch origin
git rebase <final-master-sha>
```

`R1A` starts the rebase. If Git reports conflicts, each replayed conflicting
commit or tightly coupled conflict cluster becomes its own `R1-C<n>` micro-step
under the same less-than-30-minute rule. `R1B` performs final ancestry/delta
verification after rebase completion.

Conflict handling is semantic:

- preserve the generic/non-Teams implementation from `master`;
- preserve only the Teams-specific delta from the Teams branch;
- never resolve a conflict by discarding a newer generic master contract merely
  to keep old Teams code unchanged;
- do not introduce a merge commit;
- if a Teams implementation now has a reusable dependency already supplied by
  master, adapt Teams to consume it rather than duplicating it.

After the rebase, verify:

```text
merge-base(master, program/a1-teams-spider) == final master SHA
```

and verify the Teams branch contains no new non-Teams implementation delta when
compared with master.

### G4-T — post-rebase Teams audit

On the rebased Teams branch, run the Teams-side ownership audit:

1. `microsoft_graph` Teams modules contain provider mechanics only;
2. Teams source/completeness/profile policy lives in `message_ingest`;
3. Teams T1/T2 selected bundles are application-owned;
4. Teams uses the new generic master contracts where applicable rather than
   duplicating them;
5. generic architecture guardrails inherited from master also pass with Teams
   modules present;
6. only focused tests affected by rebase/conflict resolution are rerun here.

If G4-T exposes a **Teams-specific** defect, fix it directly on the Teams
branch. If it exposes a **generic/non-Teams** defect, return to `master`, fix it
there, push the new master SHA, and repeat G4-R. A late master fix always
invalidates the previous Teams rebase baseline.

## Checkpoint G5 — final A1 ownership acceptance

G5 is the only full convergence checkpoint.

### 5.1 Focused tests during development

During G0-G4:

- run only tests affected by the current lane;
- a single narrow test may run on one Pi;
- as soon as verification spans multiple independent test files or logical test
  groups, split those tests across both Raspberry Pis in parallel;
- both Pis must test the same committed SHA; the dedicated LAN synchronization
  mechanism keeps Pi 2 pre-warmed on the latest candidate, so distributed tests
  must not pay a normal fetch/reset synchronization cost at test start;
- before a distributed run, use the lightweight sync-status check and start the
  tests immediately when it reports the same candidate SHA on both Pis;
- on a failure, fix the current lane autonomously and rerun only the failing or
  directly affected shard;
- do not restart already-green independent shards after an unrelated fix;
- do not run the full tracked suite during normal lane development;
- the full tracked suite is reserved for the final G5 convergence pass, except
  when a genuinely cross-cutting failure makes a broader run necessary.

### 5.2 Two-Raspberry-Pi final test split

Use both Raspberry Pis for the final tracked suite. This is the same execution
policy used for multi-file focused tests during G0-G4, not a special one-off.

The final full tracked-suite run targets the **rebased Teams candidate**, which
contains the frozen master baseline plus the Teams-only delta. Split tests into
stable, non-overlapping shards by file. One recommended split:

- Pi A: framework/provider/Outlook/Contacts/To Do/OneDrive and generic
  architecture tests inherited from master;
- Pi B: Teams + source-reader/handoff + remaining application tests.

Both Pis must test the same rebased Teams candidate SHA and frozen dependency
lock. The master lanes have already been focused-tested before the rebase; this
single final run proves the integrated tree. If one Pi
needs environment bootstrap, use the lock rather than an ad-hoc dependency
install.

### 5.3 Final static/framework checks

Run once on the final candidate:

```text
pytest (two-Pi sharded full tracked suite)
ruff check microsoft_graph message_ingest tests
ruff format --check microsoft_graph message_ingest tests
pyright microsoft_graph message_ingest
scrapy check
```

Also run the semantic ownership scans from G4.

### 5.4 Final review cells

Run a final independent review as an automated quality check. It must return
PASS for all four cells; a REVISE result is not a user-approval blocker. Apply
the concrete findings, rerun only affected verification, and repeat the review
autonomously until it passes:

1. **Framework purity** — no msgloom business/application policy in
   `microsoft_graph`.
2. **Provider completeness** — reusable Graph mechanics are not duplicated in
   `message_ingest`.
3. **Behavior compatibility** — A1 wire requests, evidence, catalog output,
   public reader behavior, and source identity remain compatible.
4. **Validation/rollback** — focused and final checks cover the moved boundaries
   and every checkpoint is independently revertible.

After the four cells pass, record both the frozen master SHA and the final
rebased Teams SHA. The Teams SHA must have the frozen master SHA as its
merge-base/ancestor. Use the final rebased Teams SHA as the integrated A1 entry
baseline for subsequent work. No intermediate checkpoint requires user
confirmation.

## 8. Parallel execution model

### 8.0 Critical-path review

The final review removes four avoidable serialization points from the previous
plan:

1. no global G0 wait; characterization is lane-local;
2. master and Teams implementation proceed concurrently on separate worktrees;
3. focused verification is pipelined behind exact candidate SHAs instead of
   blocking the next disjoint implementation unit;
4. generic tombstone implementation is split into one provider primitive plus
   three parallel consumers instead of one multi-resource edit.

The remaining serialization is intentional and small: notification source
separation precedes notification gap mapping; channel scope separation precedes
channel query-profile cleanup; tombstone consumers wait for the tiny core
primitive; final rebase waits for frozen master.

### 8.0.1 Maximum-parallel execution waves

```text
WAVE 0 — start immediately
  infra:   I1 master sync      || I2 clean test worktrees / exact-SHA wrapper
  master:  M0-ARCH || M1-MAIL || M2-CONTACTS || M3-ONEDRIVE
           || M4-MSG-CURSOR || M5-FOLDER-CURSOR || M6-TOMBSTONE-CORE
  teams:   T1-NOTIFY-SOURCE || T3-TOPOLOGY || T4-CHAT || T5-CHANNEL-SCOPES

WAVE 1 — dependency-triggered, no global barrier
  master:  M9-CALENDAR-TOMBSTONE as soon as M6 is green
           M7-MSG-TOMBSTONE when M4+M6 are green
           M8-FOLDER-TOMBSTONE when M5+M6 are green
  teams:   T2-NOTIFY-GAP when T1 is green
           T6-CHANNEL-QUERY when T5 is green

WAVE 2 — branch closeout in parallel
  master:  M10A read-only audit -> M10B bounded repairs/freeze
  teams:   T7A read-only audit  -> T7B bounded repairs

WAVE 3 — integration critical path
  push/freeze master -> R1A rebase start -> zero or more R1-C<n> conflict units
  -> R1B rebase verification -> R2 bounded post-rebase adaptation

WAVE 4 — one final convergence
  two-Pi full pytest shards || cheap static checks
  -> pyright/scrapy check
  -> independent final ownership review
```

A wave is not a barrier: every downstream unit starts as soon as its listed
predecessors are green, even if unrelated units in the same wave are still
running.

### 8.0.2 Immutable file ownership while parallel writers run

Before dispatching a unit, record its exact production files. The coordinator
owns shared `__init__.py`, common exports, and architecture docs/tests when two
lanes would otherwise collide. Shared-export edits are deferred until the
producer lane is green and are performed as a separate bounded integration
micro-step on the semantically correct branch.

Important known non-overlap decisions from the source review:

- `M1-MAIL-PROFILE` should place selected Mail fields on the application Mail
  base/profile, so it does not need to edit `delta.py` or `folder_delta.py` and
  can run concurrently with `M4`/`M5`;
- `M4` and `M5` own different delta modules and can run concurrently;
- `M6` owns a dedicated pure Graph delta/protocol helper module and avoids a
  shared `protocol/__init__.py` edit during the parallel wave; `M7`/`M8`/`M9`
  own separate application consumers;
- Teams notification, topology item, chat-profile, and channel-profile tracks
  use distinct primary production files and can run concurrently;
- `T5` and `T6` intentionally stay in one channel-profile writer track because
  they share channel provider/path files.

### 8.0.3 Verification pipeline does not block implementation

Each coherent micro-step produces a candidate SHA and a focused test manifest.
The test scheduler may run that manifest on either Pi while the implementation
coordinator continues with a disjoint unit.

Every test job is identified by:

```text
branch + exact candidate SHA + shard/test selection
```

A later commit does not invalidate a passing result for an earlier candidate
unless the later commit touches the tested boundary or one of its dependencies.
Do not rerun an already-green independent shard merely because the branch head
advanced.

If a test fails, classify the failure to the owning micro-step, create a small
repair commit, and rerun only that failed/affected shard. Unrelated workers keep
running.

## 8.1 Automatic two-Pi candidate synchronization and test isolation

Distributed testing uses commits as immutable source snapshots. Do not mirror an
actively edited/uncommitted working tree between Pis.

Before implementation, complete `I1` and `I2` so the test topology is:

```text
Pi 1
  development: master worktree (may contain unrelated untracked research data)
  development: program/a1-teams-spider worktree
  test: clean master candidate worktree       [branch-specific lock]
  test: clean Teams candidate worktree        [branch-specific lock]

Pi 2
  test: clean master candidate clone/worktree [branch-specific lock]
  test: clean Teams candidate clone/worktree  [branch-specific lock]
```

The development worktrees are never used as mutable targets for background test
synchronization. This lets coding continue while tests execute against a stable
snapshot on the same Pi.

The LAN synchronization channels remain independent:

```text
master
  -> refs/heads/__pi_sync/master

program/a1-teams-spider
  -> refs/heads/__pi_sync/a1-teams-spider
```

Each channel follows the existing rules: asynchronous LAN Git publication,
coalesced ref changes, branch-specific `flock`, and dependency synchronization
only when `pyproject.toml` or `uv.lock` changes.

### Exact-SHA test pinning

The current "always test latest sync ref" behavior is not sufficient for a
pipelined implementation. Both Pi test wrappers must accept an **explicit
candidate SHA** in addition to branch/shard arguments.

A pinned test wrapper must:

1. acquire the branch-specific test lock;
2. verify the requested commit object is available and belongs to the intended
   candidate history;
3. reset only the dedicated clean test checkout to that exact SHA;
4. perform frozen dependency sync only when required by that candidate;
5. print/log the exact branch + SHA before running the test command;
6. execute the requested focused shard;
7. on exit, restore/converge the test checkout to the latest sync ref so it is
   pre-warmed for the next job.

This closes the race where commit B arrives after commit A is queued but before
A's test process acquires the lock. A still tests A; B can continue developing
and syncing independently.

For a test distributed across both Pis, both workers must receive the **same
explicit SHA**. For independent focused tests, the two Pis may test different
SHAs/branches concurrently as long as every result is bound to its own manifest.

The lightweight status check continues to answer whether a branch's *latest*
candidate is pre-warmed. It is an optimization/readiness signal, not the source
of truth for a pinned test job.

After G4/R1B, final distributed testing switches exclusively to the final rebased
Teams candidate, because that SHA contains the frozen master baseline plus the
Teams-only delta.

## 9. Commit/rollback strategy

Use one coherent commit per bounded micro-step from Section 7.3 whenever that
step can be left green independently. If a unit must be split to stay under the
30-minute constraint, use multiple small commits rather than extending the unit.

Commit order is allowed to interleave across independent lanes on the same
branch. The order does not create a dependency unless Section 7.3 declares one.
Repair commits name the owning unit (for example `M4` or `T2`) and never absorb
unrelated cleanup.

After all master micro-steps and `M10A/M10B` are complete and pushed, perform
the mandatory final rebase sequence before G5/F1. Do not merge the branches as part of this
plan unless separately requested.

Each commit must preserve a buildable/testable state. Avoid compatibility
aliases unless an external/public import actually requires one; do not keep
aliases merely to hide an unfinished move.

After each lane reaches a coherent candidate commit, the local branch-ref watcher
automatically publishes that SHA over the LAN to Pi 2's dedicated sync ref and
Pi 2 applies it to its dedicated test clone. No explicit synchronization step is
part of the normal test path. If a distributed shard fails, fix the defect,
create the next small candidate commit, and rerun only the affected shard(s).

Rollback is reverse commit order. This is a development-stage system with no
database migration compatibility burden and no production data migration to
preserve. The cleanup is not expected to require schema changes; if a minimal
schema adjustment becomes necessary to keep ownership correct, make it directly
with its focused tests and continue autonomously rather than stopping for a
migration-design decision. Do not add migration machinery solely for backward
compatibility with disposable development data.

## 10. Acceptance criteria

This cleanup is complete only when all statements below are true:

- `microsoft_graph` is reusable without msgloom;
- `microsoft_graph` has zero application persistence/source/handoff state;
- selected A1 permission bundles live in the application;
- selected A1 field/privacy profiles live in the application;
- provider endpoint/path/query constraints remain reusable in the framework;
- Teams provider items no longer encode msgloom hydration completeness;
- Teams notification protocol no longer contains msgloom source identity;
- application code does not inspect opaque Graph cursor token contents;
- reusable OneDrive 410 reset-location mechanics live in the provider layer;
- shared Graph tombstone validation is not copied across application spiders;
- application traversal/evidence/checkpoint/handoff semantics remain in
  `message_ingest`;
- current A1 behavior remains compatible;
- all non-Teams implementation deltas from this round are on `master`;
- the Teams branch contains only Teams-specific deltas on top of master;
- the final Teams branch is rebased onto the final accepted master SHA with no
  merge commit;
- no new write permission or transport exists;
- exactly one normal final full tracked-suite convergence is green, sharded
  across the two Pis; if historical runtime suggests one shard could approach
  30 minutes, split it further before launch; only targeted reruns follow any
  final-run defect;
- final static/framework checks are green;
- fresh independent ownership review is PASS after any autonomous repair loop;
- the final accepted master SHA and final rebased Teams SHA are both recorded;
  the rebased Teams SHA is the integrated A2 entry baseline.

## 11. Autonomous recovery rules

The implementation is expected to complete without routine user intervention.
A failed checkpoint means repair and continue, not stop and ask for approval.

Use these recovery rules:

- if a proposed framework primitive accidentally depends on `message_ingest`,
  `msgloom`, or SQLAlchemy, move the application concern back out and keep the
  provider primitive narrower;
- if behavior preservation appears to require moving evidence/catalog/checkpoint
  state into the framework, keep those concerns in `message_ingest` and adapt at
  the application boundary instead;
- if a profile relocation changes Graph permissions or request bytes, determine
  whether it is an implementation regression, restore the existing contract,
  and continue; do not silently broaden permissions;
- if a small development schema adjustment is required, apply it directly with
  focused tests; no backward migration path is required for disposable
  development data;
- if a proposed change starts creating a second scheduler/HTTP/retry abstraction,
  discard that approach and use the existing Scrapy/Graph component instead;
- if provider mechanics and application policy are entangled, prefer the
  smallest explicit seam or argument rather than inventing a new framework;
- if a security/privacy contract regresses, restore the stricter current
  behavior first, then continue the refactor;
- if a micro-step grows beyond the 30-minute scope, split the remaining
  responsibility into a new dependency-labelled micro-step and continue; never
  turn the timebox into a request for user direction;
- if tests fail, first classify the defect by branch ownership and micro-step: a
  non-Teams or generic defect is fixed on `master`; a Teams-only defect is fixed
  on the Teams branch; rerun only affected shards and continue automatically;
- any fix committed to `master` after a Teams rebase invalidates that rebase;
  push the new master SHA and rebase the Teams branch again before final
  convergence;
- if a final independent review returns REVISE, implement its concrete findings
  and repeat the affected checks/review without waiting for user confirmation.

Escalation to the user is reserved only for a true product-policy ambiguity that
cannot be resolved from the existing design/code/contracts. This ownership
cleanup is not expected to contain such a decision.

## 12. Expected end state

The desired architecture and history after G5 are deliberately simple:

```text
master
    generic Graph/Scrapy + non-Teams A1 ownership cleanup
        \
         \  rebase
          v
program/a1-teams-spider
    master baseline + Teams-only implementation delta

integrated tree:
    microsoft_graph/
        pure Graph/Scrapy mechanics
        provider paths + validation + representations
        auth/retry/privacy/fingerprint components

    message_ingest/
        selected A1 profiles
        source/evidence/run semantics
        response callbacks + traversal
        persistence/checkpoint/completeness/coverage
        A1 release/handoff

    A2/
        consumes the accepted A1 output contract
        does not repair A1 provider/application ownership
```

The success condition is not fewer lines in `message_ingest` or more lines in
`microsoft_graph`. The success condition is that ownership follows the reason a
piece of code exists.
