# A1 Microsoft Graph ownership finalization plan

**Status:** design/implementation plan only; no production refactor has started
**Prepared:** 2026-10-08
**Working branch:** `program/a1-teams-spider`
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

### 3.3 Important distinction: provider constraint vs selected policy

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
- schema redesign unrelated to ownership moves;
- new live-tenant acceptance claims;
- authoritative absence semantics where A1 currently does not provide them;
- broad renaming or style cleanup without ownership value.

No behavior should be removed merely to make the boundary look smaller.

## 6. Confirmed findings at plan entry

The implementation phase starts from these confirmed findings rather than doing
another broad rediscovery pass.

### F1 — Teams notification protocol carries msgloom source state

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

### F2 — Teams provider items contain acquisition completeness semantics

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

### F3 — acquisition field/profile policy exists in the framework

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

### F4 — Teams T1/T2 scope bundles are product profiles

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

### F5 — selected Teams query defaults are mixed with provider constraints

Current examples include fixed/frozen page sizes and selected channel
projection fields in the framework.

Target:

- retain provider max validation in the framework;
- move profile-selected defaults/projections into `message_ingest`;
- avoid replacing simple arguments with a new configuration framework.

### F6 — OneDrive 410 reset-location validation remains application-local

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

### F7 — Mail/folder delta still inspects opaque token text

Current application code checks `$deltatoken=` / `$skiptoken=` to decide whether
an URL is provider-owned/opaque.

Target:

- stop interpreting opaque continuation/cursor bytes;
- make request construction explicit from known request provenance
  (initial/continuation/checkpoint/reset);
- use `continuation_request()` / `verbatim_url=True` based on provenance, never
  substring inspection.

### F8 — repeated Graph tombstone parsing remains in application callbacks

Mail message delta, Mail folder delta, and Calendar delta independently parse
and validate `@removed`.

Target:

- add the smallest pure framework helper needed to validate/read the Graph
  tombstone shape;
- keep semantic interpretation in each application callback (mail folder
  membership removal vs event removal vs other domain meaning);
- do not create a generic delta workflow abstraction.

### F9 — duplicated `Prefer` composition remains in application code

Mail delta currently reconstructs immutable-ID + page-size preferences even
though the provider base already owns immutable-ID representation and exposes
`compose_prefer()`.

Target:

- use the existing provider composition API;
- preserve exact header value/order expected by tests;
- do not add another header-composition utility.

## 7. Work breakdown

Implementation is split into six gates, G0 through G5. Each gate should be
independently reviewable and revertible.

## Gate G0 — freeze ownership tests before moves

### Goal

Convert the ownership contract above into tests that fail on the known leaks
before production relocation begins.

### Add or extend tests

1. `microsoft_graph` standalone import test remains independent of
   `message_ingest`, `msgloom`, and SQLAlchemy.
2. Add a semantic-boundary test that rejects product-only field names/types in
   framework dataclasses where practical, including `source_id`, `run_id`, and
   `evidence_id`.
3. Add direct tests proving Teams provider helpers can be instantiated/used
   without the msgloom T1/T2 scope bundle.
4. Add tests proving application Teams spiders still select exact T1/T2 scopes.
5. Add tests pinning exact Outlook/Contacts/Teams application projections after
   relocation.
6. Add a focused test proving no application delta request inspects/rebuilds an
   opaque Graph cursor.

### Gate

- tests demonstrate the intended ownership, not just import direction;
- no production behavior changed yet;
- each test has one clear ownership failure message.

## Gate G1 — remove application state from Teams notification protocol/items

This gate has two disjoint lanes that may run in parallel after G0.

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

### G1 gate

- `microsoft_graph` contains no msgloom source identity or acquisition
  completeness state;
- provider notification/item tests remain standalone;
- application notification/topology tests pass.

## Gate G2 — return selected acquisition profiles to `message_ingest`

Run three lanes in parallel; they own disjoint provider/application files.

### Lane G2-MAIL

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

### Lane G2-CONTACTS

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

### Lane G2-TEAMS

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

### G2 gate

- changing a msgloom acquisition profile no longer requires editing
  `microsoft_graph`;
- framework provider helpers remain independently useful;
- current application request bytes/scopes remain unchanged;
- no new permission is requested.

## Gate G3 — finish remaining provider mechanics extraction

Run disjoint provider lanes in parallel after G2 unless a shared helper is
needed.

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

### G3 gate

- no application code constructs/decodes provider cursor structure;
- repeated provider tombstone validation is centralized;
- OneDrive provider response mechanics are reusable;
- application callbacks still own traversal and semantic decisions.

## Gate G4 — architecture guardrails and cleanup

After G1-G3 converge, perform one fresh static ownership audit.

Required checks:

1. zero imports from `microsoft_graph` to `message_ingest`, `msgloom`, or
   SQLAlchemy;
2. standalone framework imports with consumer modules blocked;
3. search `microsoft_graph` for application-only identifiers:
   - `source_id`;
   - `run_id`;
   - `evidence_id`;
   - handoff/release/promotion/catalog terms;
   - A1/A2/T1/T2 product-profile terminology;
   - completeness/limitation fields not present in provider payloads;
4. search `message_ingest` for duplicated Graph mechanics:
   - hard-coded Graph service URLs;
   - path/query construction that has a framework helper;
   - manual auth/retry handling;
   - opaque continuation parsing;
   - repeated Graph envelope/tombstone parsing;
5. verify every remaining Graph-looking constant in `message_ingest` is a
   deliberate application policy, not missing provider infrastructure.

Update old documentation that currently says the framework owns selected
"fields" or T1/T2 profiles so the written architecture matches the final code.
Do not rewrite historical implementation reports except where a current
architecture statement would otherwise mislead future work.

## Gate G5 — final A1 ownership acceptance

G5 is the only full convergence gate.

### 5.1 Focused tests during development

During G0-G4:

- run only tests affected by the current lane;
- on a failure, rerun only the failing/related test set;
- do not repeatedly run the full suite after each patch.

### 5.2 Two-Raspberry-Pi final test split

Use both Raspberry Pis for the final tracked suite.

Split tests into stable, non-overlapping shards by file. One recommended split:

- Pi A: framework/provider/Outlook/Contacts/To Do/OneDrive tests;
- Pi B: Teams + source-reader/handoff + remaining application tests.

Both Pis must test the same committed SHA and frozen dependency lock. If one Pi
needs environment bootstrap, use the lock rather than an ad-hoc dependency
install.

### 5.3 Final static/framework gates

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

A final independent review must return PASS for all four cells:

1. **Framework purity** — no msgloom business/application policy in
   `microsoft_graph`.
2. **Provider completeness** — reusable Graph mechanics are not duplicated in
   `message_ingest`.
3. **Behavior compatibility** — A1 wire requests, evidence, catalog output,
   public reader behavior, and source identity remain compatible.
4. **Validation/rollback** — focused and final gates cover the moved boundaries
   and every gate is independently revertible.

Only then mark A1 Graph ownership finalization complete and use that exact SHA as
the A2 entry baseline.

## 8. Parallel execution model

After G0 freezes the target contract, maximize parallelism without overlapping
writers.

```text
G0 ownership tests
       |
       +------------------+
       |                  |
       v                  v
 G1-A notifications   G1-B Teams items
       |                  |
       +--------+---------+
                |
                v
      +---------+---------+
      |         |         |
      v         v         v
 G2-MAIL   G2-CONTACTS  G2-TEAMS
      |         |         |
      +---------+---------+
                |
      +---------+---------+
      |         |         |
      v         v         v
 G3-OD     G3-MAIL    G3-DELTA
      \         |         /
       +--------+--------+
                |
                v
          G4 boundary audit
                |
                v
          G5 final acceptance
```

Shared `__init__.py`, settings, common protocol exports, and architecture tests
are coordinator-owned. A worker must not edit a shared file unless ownership is
explicitly transferred for that round.

## 9. Commit/rollback strategy

Use small ownership commits rather than one large refactor.

Recommended commit boundaries:

1. ownership characterization tests;
2. Teams notification boundary;
3. Teams item completeness boundary;
4. Mail profile relocation;
5. Contacts profile relocation;
6. Teams scope/query profile relocation;
7. OneDrive provider helper extraction;
8. Mail delta opaque-request cleanup;
9. Graph tombstone primitive + consumers;
10. architecture guardrails/docs;
11. final repair commit only if G5 finds a real regression.

Each commit must preserve a buildable/testable state. Avoid compatibility
aliases unless an external/public import actually requires one; do not keep
aliases merely to hide an unfinished move.

Rollback is reverse commit order. No database migration or irreversible user
data operation is planned, so rollback should be code-only. If any lane proves
that a schema change is necessary, stop that lane and revise this plan before
proceeding.

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
- no new write permission or transport exists;
- final two-Pi test gate and static/framework checks are green;
- fresh independent ownership review is PASS;
- the final accepted SHA is recorded as the A2 entry baseline.

## 11. Stop conditions

Stop and revise the plan rather than pushing through if any of these occurs:

- a proposed framework primitive needs `message_ingest`, `msgloom`, or SQLAlchemy;
- preserving behavior requires moving evidence/catalog/checkpoint state into the
  framework;
- a profile relocation unexpectedly changes Graph permissions or request
  semantics without an explicit product decision;
- a persisted schema migration becomes necessary;
- a refactor requires a second scheduler/HTTP/retry abstraction;
- a provider mechanic cannot be separated from application policy without a
  misleading abstraction;
- a current live/security contract would be weakened.

## 12. Expected end state

The desired architecture after G5 is deliberately simple:

```text
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
