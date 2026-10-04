<!-- markdownlint-disable MD036 -->

# Microsoft Teams A1 implementation plan

**Status:** P0 and core P1 frozen; P2 persistence worker active
**Prepared:** 2026-10-03
**Integration branch:** `program/a1-teams-spider`
**Integration worktree:** `/home/grammy-jiang/Projects/msgloom-worktrees/a1-teams-spider`
**Implementation base:** `46ff93e0e3cd3122743b6048526ebdbd88ea3252`
**Design authority:** `docs/plans/2026-10-03-teams-a1-readonly-acquisition-plan.md`
**Closed A1 master baseline:** `9e072eed17672f8380c709a9932ea56dbcbaff85`
**Actual master at execution start:** `765d3c67c707257514d882310873f8a89f3d866b`
**Runtime:** Python 3.13.5, Scrapy 2.19.0
**Live acceptance:** deferred until a suitable Microsoft work/school tenant is available

## 1. Purpose

This document turns the reviewed Teams acquisition design into an executable
engineering program.

It is intentionally more operational than the design authority. A coordinator
with no prior chat context must be able to:

1. verify the baseline;
2. create dependency-safe worker worktrees;
3. start ChatGPT Chat workers in parallel;
4. assign non-overlapping file ownership;
5. integrate completed lanes;
6. run focused and combined gates;
7. keep optional Teams/Microsoft 365 profiles from blocking core Teams;
8. stop before any live-support or merge claim that has not been proven with a
   real work/school tenant.

The design authority remains authoritative for product/API semantics. If this
execution plan conflicts with it, fix this plan rather than silently changing
the design.

## 2. Scope

### 2.1 Core implementation required before company live acceptance

The first implementation target is delegated **T1 + T2**:

- one-on-one, group, and meeting chats;
- chat members;
- chat messages;
- pinned messages;
- Teams-hosted message content;
- teams and full team detail;
- standard, private, shared, and incoming shared channels;
- full channel detail;
- shared-channel host/associated-team topology;
- team members;
- channel direct/all members including indirect membership paths;
- channel root messages;
- every reply page;
- edits/deletes observed through supported provider facts;
- mentions, reactions, system events, message history, and custom-emoji
  occurrences present in stable message content;
- reference/forwarded/message/meeting/tab attachment forms;
- cards, code snippets, announcements, Loop cards, unknown provider attachment
  forms;
- raw evidence and durable provider observations;
- source identity;
- repeatable current projection without absence-based deletion inference.

### 2.2 Optional profiles that do not block core

Implement only after their own profile is explicitly selected:

- T3 Teams context:
  - tags;
  - tabs;
  - app installations;
  - resource-specific permission grants.
- T4 meeting/virtual-event artifacts:
  - onlineMeeting;
  - attendance;
  - transcripts;
  - recordings;
  - webinar/town-hall metadata.
- T5 adjacent Microsoft 365 surfaces:
  - Microsoft 365 group calendar;
  - Microsoft 365 group conversations when relevant;
  - team/SharePoint files;
  - OneNote;
  - Planner;
  - Shifts/time cards;
  - workforce integration metadata;
  - Presence as contextual observation only;
  - Viva Learning;
  - Viva Engage as its own future source lane.

Optional profiles have separate consent, tests, and live gates.

### 2.3 Explicitly excluded from the initial production implementation

Do not implement as part of core T1/T2:

- Microsoft-generated Python Graph SDK;
- Azure Identity;
- Kiota;
- a second HTTP transport;
- application-only chat/channel export;
- application-only retained-message collection;
- targeted-message export;
- tenant-wide Q&A export;
- call records;
- complete virtual-event registration export;
- beta Teams sections;
- beta tenant custom-emoji directory;
- beta approvalItem read surface;
- deprecated Teams device-management APIs;
- write permissions or provider mutations.

Application-only surfaces may receive read-only design/tests in a separate lane
but must not be enabled.

## 3. Non-negotiable architecture invariants

### 3.1 Reuse the existing Graph-over-Scrapy framework

`microsoft_graph/` owns reusable provider mechanics:

- Graph scopes;
- Graph path/query construction;
- pure provider JSON validation/parsing;
- provider dataclasses;
- opaque continuation handling;
- Graph transport metadata;
- existing MSAL auth integration;
- existing Graph retry/error/diagnostics/privacy/fingerprinting.

It must not import `message_ingest`, SQLAlchemy, or product persistence.

### 3.2 message_ingest remains thin

`message_ingest/` owns:

- source ID and source identity;
- Scrapy callbacks that see Responses;
- evidence-before-semantics ordering;
- run integrity;
- application completion semantics;
- provider-observation persistence;
- current/history state;
- public command mapping.

Callbacks must follow this pattern:

```text
Scrapy Response
    |
    +--> yield RawHttpEvidenceItem
    |
    +--> call microsoft_graph pure parser
    |
    +--> yield application item(s)
    |
    +--> yield provider-built follow-up Request(s)
```

### 3.3 One transport

All Teams Graph requests go through:

```text
MicrosoftGraphSpider.graph_request()
    -> Scrapy Scheduler
    -> Scrapy Downloader
    -> existing MSAL/retry/error/diagnostics middleware
    -> Microsoft Graph
```

No HTTPX, Requests, SDK client, or duplicate evidence fetch.

### 3.4 Evidence ordering is a correctness contract

Current project setting:

```python
CONCURRENT_ITEMS = 1
```

is required for Teams unless a future explicit durable dependency mechanism
replaces it.

Pipeline order remains:

```text
200 RawEvidencePipeline
250 EvidenceLinkPipeline
300 TeamsPipeline
```

The Teams lane must never override `CONCURRENT_ITEMS`.

### 3.5 Run integrity

Reuse `MicrosoftGraphIntegrityExtension` and the existing msgloom application
Graph spider failure path.

Every Teams **application spider** under
`message_ingest/spiders/microsoft/teams/` must subclass the existing
`message_ingest.spiders.microsoft._graph.MicrosoftGraphSpider` (directly or
through an application-owned subclass), not only the reusable provider
`microsoft_graph.spiders.graph.MicrosoftGraphSpider`. This preserves the named
errback that marks terminal request/download failures while keeping provider
mechanics below the application boundary.

The following invalidate any future checkpoint/promotion:

- terminal request/download failure through the application Graph spider
  errback;
- callback/start exception;
- item-processing exception;
- dropped acquisition item;
- source-identity failure;
- write/promotion failure.

Initial Teams discovery is observation/version based and has no authoritative
absence promotion.

Any future Teams checkpoint, notification/subscription cursor, or authoritative
promotion may commit only when all are true:

1. Scrapy has reached native `spider_idle` for that logical run;
2. `spider.run_failed is False`;
3. the shared catalog write lock is free;
4. the resource-specific durable completion proof is satisfied.

Follow the existing To Do / Contacts fail-closed pattern; do not infer
completion from yield order, stats, `spider_closed` alone, or JOBDIR state.

### 3.6 JOBDIR

Initial Teams spiders should **reject JOBDIR** unless a dedicated later task
qualifies pause/resume through the real Scrapy scheduler.

Do not add a custom scheduler.

### 3.7 Live MSAL concurrency

Parallel synthetic workers are allowed.

Real company-account crawls sharing the same `MSGLOOM_MS_TOKEN_CACHE` must be
serialized unless explicitly given different cache paths.

## 4. Worker model

### 4.1 Local coordinator model and effort contract

The unattended local implementation coordinator may be either **Claude Code**
or **Codex CLI**. Use the strongest explicitly qualified configuration below;
do not silently drop to a lower-effort mode merely for speed.

#### Claude Code coordinator

Use:

```text
model: opus
effort: max
```

Equivalent CLI selection:

```bash
claude --model opus --effort max
```

The locally installed Claude Code version was verified to support
`low|medium|high|xhigh|max`; this plan intentionally selects `max`.

#### Codex CLI coordinator

Use:

```text
model: gpt-6-astra
reasoning effort: high
```

Equivalent CLI selection:

```bash
codex -m gpt-6-astra -c 'model_reasoning_effort="high"'
```

For unattended execution, use `codex-budgeted-manager` with this model and
effort. Do not start a raw long-running `codex exec` manager. Run
`codex-usage-guard check` before starting substantial work. The default policy
does not start another manager when the daily guard is critical. On 2026-10-04,
the user explicitly authorized continued execution and automatic resumption
for `MSGLOOM_TEAMS_A1_AUTONOMOUS_IMPLEMENTATION_20261003`, including at the
daily critical level. This program's supervisor passes the supported
`--allow-daily-critical` flag on every authorized launch. The exception is
recorded in the program ledger and control state. It does not change global
guard thresholds, other programs, session budgets, or implementation gates.

Update the launcher checkpoint and program ledger after each dispatch or
integration unit. Run `codex-usage-guard thread --run-id ID` after each major
unit. Rotate to a fresh session before 35 minutes or 6,000,000 local tokens,
whichever comes first. The external supervisor owns rotation and waiting;
coordinators must not sleep, poll, or launch another coordinator themselves.

#### Fallback policy

If the exact selected local model is temporarily unavailable, the coordinator
must not stop to ask the user. It may use the strongest available model in the
same tool within the user's budget rules, record the variance in the execution
log, and continue. A Codex coordinator must retain `high` effort; never select
`max` for an unattended manager or orchestration loop. Do not fall back to an
OSS/local model unless the implementation plan is explicitly revised to allow
it.

### 4.2 ChatGPT Chat worker model and effort contract

Every delegated ChatGPT Chat engineering/review worker launched through
`chatgpt-web-operations` uses:

```text
model: gpt-5-6-thinking
effort: max
```

Equivalent send options:

```text
--model gpt-5-6-thinking --effort max
```

Do not inherit an unspecified browser default. Pin both fields on every worker
send so parallel lanes and reviews are reproducible.

### 4.3 Unattended execution policy

The local coordinator is expected to run without human interaction for the
entire implementation session.

It must **never stop to ask the user** for clarification, approval, a next step,
or permission to continue ordinary repository work.

When it encounters ambiguity or failure, it must resolve it in this order:

1. authoritative Teams design document;
2. this implementation plan;
3. repository code/tests/configuration and `AGENTS.md`;
4. installed `scrapy-framework-development` skill and exact Scrapy 2.19.0
   runtime/source;
5. current official Microsoft documentation where the plan explicitly requires
   a T0 recheck;
6. the narrowest implementation consistent with all evidence.

For a local implementation problem such as a failing test, merge conflict,
static-analysis failure, worker finding, or small design ambiguity, the
coordinator must investigate, repair, rerun the affected gates, and continue to
the next unblocked task. It must not treat CI/review boundaries as a reason to
stop.

Only an **external, non-local blocker** may remain unresolved at the end, for
example:

- no suitable Microsoft work/school account;
- missing tenant administrator consent;
- company policy forbids a required webhook/live acceptance action;
- a provider capability cannot be exercised because the tenant has no example.

Even then, complete every locally executable production change, synthetic test,
static gate, and independent review first. Record the blocker precisely and
leave the branch in the strongest reviewable state without fabricating live
acceptance.

The coordinator must keep `master` untouched and must not bypass the design's
live-acceptance/merge gates merely to claim completion.

### 4.4 Only ChatGPT Chat workers for delegated lanes

All delegated engineering/review work must use separate ChatGPT **Chat**
conversations through `chatgpt-web-operations`.

Do not use:

- local Codex sub-agents;
- local Claude sub-agents;
- Work-mode sub-agents.

The local Claude Code or Codex session is the coordinator/implementer. When it
delegates a parallel engineering or review lane, that lane must be a separate
ChatGPT Chat conversation, not a traditional local sub-agent.

Each worker prompt must contain:

- unique `TASK_ID`;
- exact input commit;
- exact owned files/directories;
- explicit non-owned files;
- finite output contract;
- required tests;
- stop condition;
- pinned `gpt-5-6-thinking` / `max` model-effort settings.

### 4.5 Worktree rule

Every code-writing worker receives its own git worktree/branch based on the
current Teams integration commit.

Read-only reviewers do not need worktrees.

The integration coordinator alone:

- merges/cherry-picks worker commits;
- edits shared package exports;
- edits shared model registries;
- edits schema registration;
- edits project settings;
- edits public command root;
- edits cross-lane documentation;
- resolves conflicts;
- runs combined gates.

### 4.6 Parallelism rule

There is no artificial worker-count limit.

Start every lane whose dependency edges are satisfied and whose file ownership
does not overlap another active writer.

Browser/session capacity may queue ChatGPT sends, but it is not a project-level
serialization rule.

## 5. Global dependency graph

```text
Reviewed design baseline 46ff93e
        |
        v
P0 framework qualification
   |      |      |      |      |
   A      B      C      D     E-pre
   \______|______|______|______/
                 |
                 v
        P0-E closure review
                 |
                 v
        P0 contract freeze
                 |
     +-----------+------------------+
     |           |                  |
     v           v                  v
 P1-MSG      P1-CHAT           P1-CHANNEL
     |           |                  |
     +-----+-----+                  |
           |                        |
           v                        v
 P1-CHAT-COMPOSITION     P1-CHANNEL-COMPOSITION
           |                        |
           +-----------+------------+
                       |
                       v
              core provider freeze
                       |
                       v
                P2-PERSISTENCE

Optional profile lanes (P1-CTX, P1-MEETING, P1-ADJACENT, P1-APPONLY)
branch from P0 independently and have their own profile freezes/P2 gates.
They have no dependency edge into core P2/P3/merge.
        |
        +-------------------+
        |                   |
        v                   v
 P2-CHAT-SPIDER     P2-CHANNEL-SPIDER
        |                   |
        +---------+---------+
                  |
                  v
          core synthetic crawls
                  |
                  v
            P3 convergence
                  |
                  v
       future company acceptance
```

`P1-CONTEXT`, `P1-MEETING`, `P1-ADJACENT`, and `P1-APPONLY` can run in
parallel with the core P1 graph only when their profile is selected. They gate
only their own optional profile and never feed the core provider freeze.

## 6. P0 — framework qualification

P0 produces no broad production implementation.

Small probes, pure contract tests, and planning artifacts are allowed.

### P0-A — existing framework extension map

**Goal**

Map every core Teams responsibility to an existing Scrapy/Graph extension point
before creating new abstractions.

**Input**

- reviewed design at `46ff93e`;
- `microsoft_graph/`;
- `message_ingest/spiders/microsoft/_graph.py`;
- Graph add-on/middleware/fingerprint/protocol tests;
- Scrapy 2.19.0 runtime.

**Work**

For each core resource determine:

- path builder owner;
- pure parser owner;
- request builder owner;
- callback owner;
- item owner;
- evidence owner;
- persistence owner;
- lifecycle owner;
- required existing component.

Produce a table for:

- chats;
- chat members;
- chat messages;
- pins;
- hosted content;
- teams;
- channels;
- team/channel membership;
- root/reply messages;
- shared-channel topology.

**Output**

`docs/implementation/teams/p0-framework-map.md`

No production code unless a missing primitive is proven.

**Downstream**

Required by all P1 production lanes.

**Parallel**

Runs with P0-B/C/D.

**Gate**

No new middleware, scheduler, auth client, retry loop, or generic workflow layer
without a concrete missing behavior.

### P0-B — auth, source identity, and permission contract

**Goal**

Freeze how T1/T2 scopes plug into existing MSAL/source identity.

**Input**

- `MicrosoftGraphAuthSession`;
- auth management command;
- `docs/authentication.md`;
- reviewed Teams permission profiles.

**Work**

Confirm:

- T1:
  - `Chat.Read`.
- complete T2:
  - `Team.ReadBasic.All`;
  - `Channel.ReadBasic.All`;
  - `ChannelMessage.Read.All`;
  - `TeamMember.Read.All`;
  - `ChannelMember.Read.All`.
- admin-consent requirements;
- source ID `microsoft-teams-default`;
- same delegated home-account binding across native Teams lanes;
- live shared-cache serialization rule.

**Output**

`docs/implementation/teams/p0-auth-scope-contract.md`

Add focused scope tests only if existing scope declaration behavior lacks
coverage.

**Downstream**

P1 provider spiders/items and future company live acceptance.

**Parallel**

Runs with P0-A/C/D.

### P0-C — exact API/path contract freeze

**Goal**

Translate the reviewed Graph surface into exact v1.0 paths/query rules before
coding.

**Input**

- reviewed Teams design;
- current Microsoft Learn v1.0 docs.

**Work**

Freeze exact path/query contracts for:

- `/me/chats`;
- chat members/messages/pins/hosted content;
- `/me/teamwork/associatedTeams`;
- full team GET;
- `allChannels`;
- `incomingChannels`;
- `sharedWithTeams`;
- full channel GET;
- team members;
- channel `members` and `allMembers`;
- channel root messages/replies;
- cross-tenant resource-link workaround;
- supported chat message date filter;
- hosted-content headers;
- message attachment forms.

Record unresolved contracts/decisions separately:

- advertised channel-message delta;
- activity-feed read endpoint for delegated `TeamsActivity.Read`;
- exact stable resource API/product meaning for
  `TeamworkUserInteraction.Read.All`;
- resource-specific permission-grant read transition;
- notification maximum lifetime conflict;
- whether optional channel `summary` / `email` detail is product-relevant; if
  omitted, record that omission instead of treating the basic channel detail
  projection as exhaustive.

**Output**

`docs/implementation/teams/p0-api-contract.md`

**Downstream**

All P1 lanes.

**Parallel**

Runs with P0-A/B/D.

**Gate**

No beta endpoint may enter core production code.

### P0-D — synthetic Graph transport harness design

**Goal**

Define one deterministic local fixture mechanism that exercises the actual
Scrapy Downloader and A1 evidence path.

**Input**

Existing crawl tests such as:

- `tests/test_contacts_crawl.py`;
- `tests/test_todo_crawl.py`;
- `tests/test_onedrive_crawl.py`;
- Graph middleware tests.

**Work**

Design fixture support for:

- paginated collection responses;
- opaque next links;
- Graph 429/503;
- 401/auth-disabled synthetic mode;
- malformed envelopes;
- response headers;
- binary hosted content;
- cross-tenant resource links;
- callback/item failure injection.

**Output**

`docs/implementation/teams/p0-fixture-harness.md`

Preferred later code location:

`tests/teams_support.py` or a small `tests/teams/` fixture package if the
existing test layout conventions justify a directory.

**Downstream**

Every crawl/integration test.

**Parallel**

Runs with P0-A/B/C.

### P0-E — independent architecture review

**Parallel pre-review**

Start P0-E at the same time as P0-A-D. Its first pass reviews:

- the reviewed design baseline;
- the current Graph-over-Scrapy framework;
- the planned extension points and non-negotiable ownership boundaries.

This preserves the design requirement that P0-D/E can proceed in parallel and
allows architecture objections to surface before A-D finish.

**Closure starts after**

- P0-A complete;
- P0-B complete;
- P0-C complete;
- P0-D complete.

**Goal**

Perform a bounded closure review of the converged P0-A-D outputs before
production implementation.

**Worker**

Fresh ChatGPT Chat reviewer, or the same pre-review conversation only if it is
given the exact converged outputs and asked for a new bounded closure verdict.

**Input**

P0-A-D outputs plus exact framework files.

**Output**

Compact verdict:

- `PASS`, or
- concrete findings with file/section owner.

**Gate**

P1 does not start until the closure verdict is PASS and all blockers/majors are
resolved.

## 7. P0 convergence — coordinator-owned

After P0 workers return, the coordinator:

1. reconciles contradictions;
2. rechecks official docs for any disputed claim;
3. defines exact file ownership for P1;
4. adds only the minimal shared package directories/exports needed to unblock
   P1;
5. runs current Graph framework tests;
6. records the P0 freeze commit.

No worker may independently modify shared exports/settings at this stage.

## 8. P1 — provider primitives

P1 primarily extends reusable `microsoft_graph/`.

Every P1 writer must include lane-local tests.

### P1-MESSAGE-PRIMITIVES

**Goal**

Create the common Teams message provider model used by both chats and channels.

**Owned production files**

Preferred:

```text
microsoft_graph/items/teams/message.py
microsoft_graph/protocol/teams.py
```

If module size approaches the repository limit, split protocol helpers by
resource rather than growing one generic file.

The coordinator owns the shared Teams package exports, including
`microsoft_graph/items/teams/__init__.py` and
`microsoft_graph/spiders/teams/__init__.py`. Freeze any additional file ownership
in the lane prompt before dispatch.

**Owned tests**

Preferred:

```text
tests/test_teams_message_provider.py
tests/test_teams_message_protocol.py
```

**Input**

P0 contracts.

**Implement**

Pure provider parsing for:

- scoped message ID context;
- timestamps;
- etag/version observation;
- sender/onBehalfOf;
- body/content type;
- mentions;
- custom-emoji occurrences preserved from stable message payload/body/hosted
  content without requiring the beta tenant emoji directory;
- reactions;
- messageHistory without pretending it stores old bodies;
- messageType/system event detail;
- importance/subject/summary;
- provider `scope` where present;
- provider `webUrl` preserved as source metadata/evidence linkage, not as an
  instruction to crawl arbitrary UI URLs;
- channel `replyToId`;
- attachment taxonomy:
  - reference;
  - forwardedMessageReference;
  - messageReference;
  - meetingReference;
  - tabReference;
  - Loop/card/code/announcement;
  - unknown values preserved.
- hosted-content metadata.

No msgloom evidence fields here.

**Output**

Provider dataclasses/parsers and passing focused tests. Fidelity tests must
explicitly prove `scope` and `webUrl` survive parsing without turning `webUrl`
into a follow-up crawl target.

**Downstream**

P1-CHAT-COMPOSITION, P1-CHANNEL-COMPOSITION, persistence design.

**Parallel**

Runs with P1-CHAT-TOPOLOGY, P1-CHANNEL-TOPOLOGY, P1-CONTEXT,
P1-MEETING, P1-ADJACENT, P1-APPONLY.

### P1-CHAT-TOPOLOGY

**Goal**

Implement reusable chat path/query/topology primitives without application
callbacks.

**Owned production files**

```text
microsoft_graph/spiders/teams/chat.py
microsoft_graph/items/teams/chat.py
```

**Owned tests**

```text
tests/test_teams_chat_provider.py
```

**Implement**

- T1 `Chat.Read`;
- chat inventory path;
- explicit member path;
- messages path;
- `lastModifiedDateTime` filter helper;
- pins path;
- hosted-content paths;
- ID validation/encoding;
- page-size bounds;
- chatType preservation.

**Do not implement**

Scrapy response callbacks or msgloom persistence.

**Output**

Provider primitives plus focused tests.

**Downstream**

P1-CHAT-COMPOSITION.

**Parallel**

First P1 tranche.

### P1-CHANNEL-TOPOLOGY

**Goal**

Implement reusable team/channel/shared-topology primitives.

**Owned production files**

```text
microsoft_graph/spiders/teams/channel.py
microsoft_graph/items/teams/channel.py
```

**Owned tests**

```text
tests/test_teams_channel_provider.py
```

**Implement**

Paths/parsers for:

- associated teams;
- full team detail where the current user can retrieve it, with explicit
  partial-detail state when an associated/shared host team cannot be hydrated;
- allChannels;
- incomingChannels;
- sharedWithTeams;
- full channel detail where retrievable, with explicit detail-completeness
  state rather than treating the discovery projection as exhaustive;
- team members;
- channel members;
- allMembers;
- channel root messages;
- replies;
- hosted content;
- documented cross-tenant resource-link normalization.

Preserve `@microsoft.graph.originalSourceMembershipUrl`.

Do not rewrite `@odata.nextLink`.

**Output**

Provider primitives plus focused tests.

**Downstream**

P1-CHANNEL-COMPOSITION.

**Parallel**

First P1 tranche.

### P1-CONTEXT — optional T3

**Goal**

Prepare optional stable v1.0 Teams context primitives.

**Owned production files**

```text
microsoft_graph/items/teams/context.py
microsoft_graph/spiders/teams/context.py
```

**Owned tests**

```text
tests/test_teams_context_provider.py
```

**Implement only stable selected contracts**

- tags as context/audience metadata, never automatic Topic identity;
- tabs as configuration metadata only; never crawl an arbitrary tab URL;
- installed apps;
- permission grants only after P0 resolves the exact v1.0 permission contract,
  and never request a broader scope solely to collect permission-grant metadata.

**Gate**

T3 failures do not block T1/T2.

### P1-MEETING — optional T4

**Owned production files**

```text
microsoft_graph/items/teams/meeting.py
microsoft_graph/spiders/teams/meeting.py
```

**Owned tests**

```text
tests/test_teams_meeting_provider.py
```

**Scope**

Pure provider primitives only for selected T4 capabilities.

Preserve meeting chat, `onlineMeeting`, Outlook/Exchange calendar event, webinar,
and town-hall resources as distinct provider observations linked by
provider-supported identifiers. Do not flatten them into one record and do not
duplicate Outlook Calendar ownership.

### P1-ADJACENT — optional design/provider work

Separate ChatGPT lanes may investigate or implement narrowly selected stable
provider primitives for:

- Microsoft 365 group calendar;
- Microsoft 365 group conversations;
- SharePoint/team files;
- OneNote;
- Planner;
- Shifts/time cards;
- workforce integration metadata;
- Presence;
- Viva Learning.

These are adjacent Microsoft 365 resources surfaced in Teams, not native Teams
chat/channel state. Each lane must define and preserve its real provider/source
ownership and may link back to Teams context, but must not silently reuse
`microsoft-teams-default` merely because the UI exposes the resource inside
Teams.

Specific semantic guards:

- group calendar must not duplicate existing signed-in-user Outlook Calendar
  ownership;
- group conversations remain group/Outlook resources, never substitutes for
  Teams channel messages;
- Presence is timestamped context only and must not imply Topic identity,
  responsibility, message receipt, or user awareness;
- file resolution must use an authorized Microsoft provider API and explicit
  resolved/denied/missing/stale/not-attempted state; never hand an arbitrary
  Teams `contentUrl` to a generic downloader.

Viva Engage remains a separate future source lane with its own identity and
permission contract.

Do not let this lane edit core Teams message/chat/channel modules.

### P1-APPONLY — design/tests only

Document/test only:

- chat getAllMessages/delta;
- channel getAllMessages;
- retained-message APIs;
- targeted messages;
- registration export;
- Q&A;
- call records.

This lane must also design the separate application-only source-identity key
scheme required by the design authority. It has no signed-in user home account
and must not reuse the delegated `microsoft-teams-default` source binding by
assumption.

No application credentials or production enablement.

## 9. P1 composition lanes

### P1-CHAT-COMPOSITION

Starts after:

- P1-MESSAGE-PRIMITIVES PASS;
- P1-CHAT-TOPOLOGY PASS.

**Goal**

Define the exact contract consumed by the application chat spider.

Prefer adding small provider composition helpers rather than a callback-owning
base class.

**Output**

Stable chat provider item/path contract.

### P1-CHANNEL-COMPOSITION

Starts after:

- P1-MESSAGE-PRIMITIVES PASS;
- P1-CHANNEL-TOPOLOGY PASS.

**Goal**

Define root/reply/topology contracts consumed by the application channel spider.

**Output**

Stable channel provider item/path contract.

## 10. Core P1 convergence gate

Before **core** persistence/chat/channel spiders start:

- P1-MESSAGE-PRIMITIVES PASS;
- P1-CHAT-TOPOLOGY and P1-CHAT-COMPOSITION PASS;
- P1-CHANNEL-TOPOLOGY and P1-CHANNEL-COMPOSITION PASS;
- all focused tests for those core lanes pass;
- provider package has no `message_ingest` imports;
- no SQLAlchemy imports in `microsoft_graph`;
- Graph framework regression passes;
- Ruff/Pyright pass on changed core code;
- provider files respect repository size/source conventions;
- exact core permission/path assumptions match P0 freeze.

P1-CONTEXT, P1-MEETING, P1-ADJACENT, and P1-APPONLY are explicitly excluded
from this core gate. Each optional profile owns an independent convergence gate
and cannot delay P2-PERSISTENCE, P2-CHAT-SPIDER, P2-CHANNEL-SPIDER, core
synthetic convergence, or the core merge decision.

Coordinator records a **core provider-contract freeze** commit.

## 11. P2 — durable application storage

### P2-PERSISTENCE

**Starts after**

- common message contract stable;
- chat item contract stable;
- channel item contract stable.

**Goal**

Add additive durable Teams observation/history storage.

**Owned production files**

Preferred:

```text
message_ingest/catalog/models/microsoft/teams/
  __init__.py
  topology.py
  message.py
  content.py

message_ingest/catalog/stores/microsoft/teams/
  __init__.py
  topology.py
  message.py
  content.py

message_ingest/items/microsoft/teams/
  __init__.py
  topology.py
  message.py
  content.py

message_ingest/pipelines/microsoft/teams.py
```

The exact split can be simplified if modules stay comfortably below project
limits.

**Coordinator-owned shared files**

The worker must not edit:

- `message_ingest/catalog/models/__init__.py`;
- shared catalog metadata/base registries;
- `message_ingest/items/microsoft/__init__.py`;
- `message_ingest/pipelines/microsoft/__init__.py`;
- migrations/shared schema registry;
- settings.

Coordinator integrates those after the lane commit.

**Persistence semantics**

Store at least:

- logical source ID;
- scoped provider identity;
- team/chat/channel topology observations;
- team/channel discovery-versus-hydration completeness and access limitations;
- membership observations with indirect-source path;
- message observations/versions;
- root/reply relation;
- chat `messageReference` relation candidate;
- pin/unpin relation observations separate from the underlying message;
- attachment/reference observations, including
  resolved/denied/missing/stale/not-attempted state;
- `meetingReference` / `tabReference` provider relation candidates where
  present;
- hosted-content evidence linked to the triggering observed message record
  without claiming the returned bytes are provider-version-bound to that exact
  message etag/body version;
- explicit deletion facts;
- coverage/retention/subscription-gap metadata.

Do not infer deletion from ordinary absence.

**Pipeline**

One small `TeamsPipeline`:

- type dispatch;
- shared catalog write lock;
- awaited `asyncio.to_thread` persistence;
- bounded stats;
- no Graph parsing or traversal.

**Tests**

Preferred:

```text
tests/test_teams_catalog.py
tests/test_teams_pipeline.py
tests/test_teams_persistence_ordering.py
```

Include:

- duplicate provider IDs in different scopes;
- multiple observations/etags;
- old content preserved after deletion;
- membership-path multiplicity;
- evidence FK/lookup failure;
- async write serialization.

**Output**

Stable application item/store/pipeline contract.

## 12. P2 — core chat spider

### P2-CHAT-SPIDER

**Starts after**

- P1-CHAT-COMPOSITION PASS;
- persistence item contract available.

**Owned production files**

```text
message_ingest/spiders/microsoft/teams/
  chat.py
```

If hosted-content callbacks become large, use a focused private helper module
under the same package.

The coordinator owns the shared spider package `__init__.py`. Shared
hosted-content helpers need explicit ownership before either spider writer
starts.

**Spider name**

Target:

```text
microsoft_teams_chat_discover
```

**Settings**

- source ID: `MSGLOOM_TEAMS_SOURCE_ID` default
  `microsoft-teams-default`;
- T1 scope only;
- catalog/evidence pipelines 200/250/300;
- no authoritative absence promotion;
- reject JOBDIR initially;
- use uncached reads where current-state correctness requires it.

**Traversal**

1. list chats;
2. emit chat evidence/items;
3. explicit members;
4. message pages;
5. pins;
6. per-message hosted content/reference operations as selected;
7. opaque continuation requests.

Every callback emits evidence before parsing provider state.

**Tests**

```text
tests/test_teams_chat_spider.py
tests/test_teams_chat_crawl.py
tests/test_teams_chat_integrity.py
```

Must cover T1 mandatory fixtures, including a terminal request/download
failure proving the inherited application Graph errback marks the logical run
failed.

## 13. P2 — core channel spider

### P2-CHANNEL-SPIDER

**Starts after**

- P1-CHANNEL-COMPOSITION PASS;
- persistence item contract available.

**Owned production files**

```text
message_ingest/spiders/microsoft/teams/channel.py
```

**Spider name**

Target:

```text
microsoft_teams_channel_discover
```

**Traversal**

1. associated-team discovery;
2. full detail for directly accessible teams;
3. all/incoming channel discovery;
4. full detail for accessible channels;
5. sharedWithTeams topology;
6. team members;
7. channel members/allMembers;
8. channel root message pages;
9. every reply page;
10. hosted content/reference operations;
11. opaque pagination.

Preserve discovery evidence separately from hydrated detail evidence.

**Tests**

```text
tests/test_teams_channel_spider.py
tests/test_teams_channel_crawl.py
tests/test_teams_shared_channel_crawl.py
tests/test_teams_channel_integrity.py
```

Integrity tests must exercise terminal request/download failure plus
`spider_error` / `item_error` / dropped-item paths. If a later checkpoint,
subscription cursor, or promotion is introduced, add a real idle-boundary test
that proves it is blocked when `run_failed` is true or the shared write lock is
busy.

## 14. Coordinator-owned command/settings integration

This step starts only after chat/channel spider contracts exist.

Coordinator edits shared files.

### Public command target

Keep all Microsoft products below the single Microsoft namespace.

Target hierarchy:

```text
scrapy microsoft teams chat discover
scrapy microsoft teams channel discover
```

Optional later profiles:

```text
scrapy microsoft teams context discover
scrapy microsoft teams meeting discover
```

Do not create a second top-level `teams` Scrapy command.

### Shared files

Likely changes:

- `message_ingest/commands/microsoft/__init__.py`;
- new `message_ingest/commands/microsoft/teams.py`;
- `message_ingest/commands/microsoft/options.py` only if truly shared options
  are required;
- `message_ingest/settings.py`;
- shared package exports/registries.

### Command tests

```text
tests/test_teams_commands.py
tests/test_microsoft_command_package_layout.py
```

Commands own intent/argument mapping only.

## 15. P2 — optional T3/T4 application spiders

These do not block core.

### P2-CONTEXT-SPIDER

Only after T3 provider contract and consent profile are frozen.

Candidate:

```text
microsoft_teams_context_discover
```

### P2-MEETING-SPIDER

Only after T4 provider contract is frozen.

Candidate:

```text
microsoft_teams_meeting_discover
```

Must link to existing Outlook Calendar facts where provider-supported IDs exist;
do not duplicate calendar ownership.

## 15.1 P2 — optional T5 adjacent application lanes

T5 remains independently selected and independently gated. No T5 lane has an
edge into core T1/T2 convergence or merge.

After a selected P1-ADJACENT provider contract is frozen, create a separate
application/persistence lane for **that resource family only**. Examples include
group calendar/conversations, SharePoint/team files, OneNote, Planner, Shifts,
Presence, or Viva Learning.

Each selected lane must define:

- its own application spider/adapter and durable item/store contract;
- its real provider/source identity instead of defaulting to
  `microsoft-teams-default`;
- its dedicated read-only permission profile and admin-consent requirement;
- its own synthetic and future live acceptance gate;
- explicit Teams-context links where useful without changing source ownership.

Product-specific guards from the design authority remain mandatory:

- group calendar does not duplicate signed-in-user Outlook Calendar ownership;
- group conversations never substitute for Teams channel messages;
- Planner is distinct from Microsoft To Do and standard Graph Planner does not
  claim premium Planner coverage;
- Presence is timestamped context only;
- file references retain explicit resolution state and are fetched only through
  authorized Microsoft provider APIs.

Viva Engage remains a separate future source lane, not a Teams T5 spider.

## 16. Change-notification implementation track

Do not implement notification infrastructure as a prerequisite for initial
full/read discovery.

For continuous change detection, preserve the design's Teams polling rule:
do not repeatedly poll the same resource for changes more than once per day
unless that exact Graph API documents a different supported pattern. A bounded
initial/full acquisition is not itself permission to implement high-frequency
polling. Use the supported chat `lastModifiedDateTime` range read where
appropriate; do not invent an equivalent general date filter for channel root
listing. Prefer change notifications when fresher detection is needed.

Start only after basic T1/T2 discovery is stable. However, if the future company
tenant/policy permits webhook acceptance, the design authority requires at
least one real notification-driven update/delete acceptance flow before core
merge. In that case this track becomes a pre-merge requirement, not an optional
implementation choice. Only tenant/policy inability to accept the webhook can
justify `NOT EXERCISED`.

### N0 — subscription contract recheck

Recheck:

- current maximum subscription lifetime;
- tenant quota;
- lifecycle events;
- rich-notification lifetime;
- delegated per-chat/per-channel support;
- encryption requirements if resource data is included.

Resolve the currently conflicting Microsoft documentation before hard-coding
renewal time.

### N1 — provider-neutral notification evidence

Reuse existing Graph notification protocol code where possible.

Persist:

- raw notification payload evidence;
- subscription/resource identity;
- change type;
- provider resource identity;
- subscription validity window;
- lifecycle events;
- known/suspected delivery gaps.

### N2 — reconciliation

Created/updated:

- normally trigger targeted Graph read/reconciliation.

Deleted:

- may be the only remaining provider deletion evidence;
- persist deletion fact even if readback is unavailable.

After subscription gap:

- reconcile current readable state;
- mark intervening history incomplete/unknown.

This track has its own tests and does not block initial T1/T2 discovery.

## 17. P2-A2 handoff

This lane starts as read-only design/tests and cannot modify persistence models
while P2-PERSISTENCE is active.

After persistence stabilizes, add Teams support to the A1 saved-source boundary.

**Input**

Committed Teams catalog/evidence only.

**Output to A2 must preserve**

- source ID/account binding;
- scoped provider IDs;
- observed message versions;
- evidence IDs;
- team/chat/channel context, including entity-detail completeness/partial-state
  limitations;
- channel root/reply edges;
- chat `messageReference` candidate relation;
- membership-path provenance;
- attachment/reference resolution state;
- retention window;
- notification coverage window/gaps;
- unknown/incomplete history state.

A2 must not need:

- Spider;
- Request;
- Response;
- Crawler;
- scheduler state;
- MSAL session;
- Graph checkpoint internals.

Preferred tests belong under:

```text
tests/source_reader/
```

in Teams-specific files owned only after the persistence contract lands.

## 18. P3 — core synthetic convergence

Core T1/T2 acceptance is profile scoped.

### 18.1 Focused provider tests

Run all new Teams provider tests.

### 18.2 Focused application tests

Run all Teams catalog/pipeline/spider/command tests.

### 18.3 Core synthetic crawls

The implementation must cover the mandatory fixture matrix from the design
authority, including:

- >25 group chat members;
- meeting chat;
- federated identities;
- standard/private/shared/incoming shared channels;
- associated host teams;
- team/channel detail hydration;
- allMembers indirect paths;
- multi-page root/reply traversal;
- edit observations;
- explicit delete evidence;
- attachment/reference taxonomy;
- hosted-content limitations;
- cross-tenant resource-link workaround;
- malformed/failure paths;
- evidence-before-semantics;
- JOBDIR rejection or explicitly qualified resume behavior.

### 18.4 Existing framework regression

Run the affected existing Microsoft Graph/A1 tests.

### 18.5 Full repository gate

Before declaring synthetic implementation complete:

- full normal Python 3.13 suite;
- serial `exclusive_state` suite;
- FastMCP compatibility suite if still part of the repository gates;
- Ruff check;
- Ruff format check;
- Pyright;
- live Python LSP diagnostics for `microsoft_graph/`, `message_ingest/`, and
  `tests/`;
- Scrapy contracts;
- pre-commit on changed files.

### 18.6 Compatibility

Qualify Python 3.12, 3.13, and 3.14 using the project's existing compatibility
mechanism before final implementation review.

## 19. P3 independent reviews

Run separate ChatGPT Chat reviewers in parallel:

- provider/API/permissions review;
- Graph-over-Scrapy ownership review;
- privacy/security review;
- evidence/provenance/replay review;
- Scrapy lifecycle/cancellation review;
- persistence/history/deletion review;
- shared-channel topology review;
- synthetic-fixture completeness review;
- Python compatibility review.

Repair findings in parallel only where file ownership is disjoint.

A final closure round must review the repaired exact candidate.

## 20. Future company-account acceptance

No merge to `master` before this gate.

### 20.1 Tenant preparation

Record without secrets:

- company-approved application/client;
- tenant account capability;
- T1/T2 admin-consent availability;
- refused scopes;
- representative resource availability.

### 20.2 T1 live acceptance

Use an isolated catalog/raw-evidence root.

Validate:

- work/school source binding;
- one-on-one chat if available;
- group chat if available;
- meeting chat if available;
- members;
- messages;
- pins;
- attachments/hosted content examples where available;
- repeat acquisition.

### 20.3 T2 live acceptance

After administrator approval where required:

A reduced T2 may omit only `TeamMember.Read.All` and/or
`ChannelMember.Read.All`, matching the design authority; it must label
roster/membership coverage incomplete. `ChannelMessage.Read.All` remains
required for core channel-message support and cannot be waived by calling the
result "reduced T2".

- associated teams;
- directly joined teams;
- standard/private/shared channels;
- incoming shared channels;
- full team/channel hydration;
- team roster;
- channel members/allMembers;
- roots/replies;
- cross-tenant behavior if available.

If the tenant lacks an example of a particular resource, mark that live cell
`NOT EXERCISED`; do not fabricate support.

### 20.4 Optional profile live acceptance

T3/T4/T5 are independently gated.

A denied optional profile does not block core T1/T2 merge.

### 20.5 Live repeat/reconciliation

If company policy permits webhook acceptance, the notification track must be
implemented far enough to exercise at least one real notification-driven
created/updated or deleted flow and confirm the persisted coverage semantics
before merge. This requirement cannot be skipped merely because notification
implementation was deferred during initial discovery work.

If webhook acceptance is not permitted by the tenant/company policy, record
`NOT EXERCISED` with that external limitation; this does not block core
discovery acceptance.

Run repeat read-only acquisition and confirm:

- no duplicate logical current objects from stable provider identity;
- new observations remain append-only/evidence-linked;
- no deletion inferred from absence;
- no write permission requested;
- privacy logs contain no tokens or sensitive URLs beyond accepted evidence
  storage.

### 20.6 Post-live exact-candidate convergence

After T1/T2 live acceptance and the repeat acquisition above, rerun the complete
repository/static compatibility gates required by Sections 18.5-18.6.

Then run a fresh independent closure review of the **exact post-live candidate**
covering at minimum:

- provider/API/permission claims;
- Graph-over-Scrapy ownership;
- Scrapy lifecycle/cancellation;
- privacy/evidence;
- persistence/history/deletion;
- live-acceptance evidence and any `NOT EXERCISED` cells.

The pre-live P3 gates/reviews remain useful convergence checks but do **not**
satisfy this post-live requirement. If no source commit changed during live
acceptance, record that exact SHA and still rerun the gates/review so the merge
decision follows the ordering required by the design authority.

## 21. Merge gate

The Teams branch may be proposed for merge only when all are true:

- core T1/T2 implementation complete;
- core synthetic gate complete;
- company-account T1 acceptance complete;
- company-account T2 channel-message acceptance complete with
  `ChannelMessage.Read.All`; an explicitly product-approved reduced-T2 contract
  may omit only team/channel roster-member scopes and must label membership
  coverage incomplete;
- post-live full repository/static/compatibility gates PASS on the exact
  candidate;
- post-live independent exact-candidate closure review PASS;
- no false claim for unexercised optional profiles;
- no beta endpoint in production core;
- no write permission;
- no second Microsoft auth/transport stack;
- core Teams application spiders retain the existing msgloom
  `MicrosoftGraphSpider` failure/integrity path;
- any implemented checkpoint/subscription cursor/promotion satisfies the native
  idle + clean-run + free-write-lock gate;
- source identity correct;
- this program has not changed `master`; preserve unrelated work already
  present at execution start and record later independent advances without
  resetting them to the historical A1 baseline.

Do not merge automatically merely because CI is green.

## 22. Proposed file map

Expected new core files, subject to P0 refinement:

```text
microsoft_graph/
  items/teams/
    __init__.py
    chat.py
    channel.py
    message.py
  spiders/teams/
    __init__.py
    chat.py
    channel.py
  protocol/
    teams.py                    # only if generic protocol helpers justify it

message_ingest/
  items/microsoft/teams/
    __init__.py
    topology.py
    message.py
    content.py
  spiders/microsoft/teams/
    __init__.py
    chat.py
    channel.py
  catalog/models/microsoft/teams/
    __init__.py
    topology.py
    message.py
    content.py
  catalog/stores/microsoft/teams/
    __init__.py
    topology.py
    message.py
    content.py
  pipelines/microsoft/
    teams.py
  commands/microsoft/
    teams.py

tests/
  test_teams_message_provider.py
  test_teams_message_protocol.py
  test_teams_chat_provider.py
  test_teams_channel_provider.py
  test_teams_catalog.py
  test_teams_pipeline.py
  test_teams_persistence_ordering.py
  test_teams_chat_spider.py
  test_teams_chat_crawl.py
  test_teams_chat_integrity.py
  test_teams_channel_spider.py
  test_teams_channel_crawl.py
  test_teams_shared_channel_crawl.py
  test_teams_channel_integrity.py
  test_teams_commands.py
```

Optional-profile files are added only when their profile starts.

## 23. Shared-file ownership table

The coordinator owns these for the whole implementation round:

| Shared file/category | Owner |
| --- | --- |
| `message_ingest/settings.py` | coordinator |
| Microsoft root command dispatch | coordinator |
| shared package `__init__.py` exports outside lane-owned package | coordinator |
| catalog base/model registry | coordinator |
| migration registry/schema orchestration | coordinator |
| cross-lane documentation | coordinator |
| dependency/lock files | coordinator |
| final integration fixes | coordinator |

Workers may propose diffs for coordinator-owned files but must not commit
overlapping edits to them unless the coordinator temporarily transfers explicit
ownership.

## 24. Worker completion contract

Every code-writing worker returns:

1. task ID;
2. exact base SHA;
3. commit SHA;
4. files changed;
5. tests added;
6. commands run;
7. test results;
8. unresolved assumptions;
9. whether shared-file changes are requested from coordinator;
10. next dependency now unblocked.

The coordinator independently reviews the diff and reruns critical tests before
integration.

## 25. Stop conditions

Stop the relevant lane and return to design review if any of these occurs:

- official Graph docs contradict the frozen API contract;
- a required core endpoint is beta only;
- delegated permission is unavailable for the intended user model;
- implementation would require a write permission;
- implementation requires a second HTTP/auth stack;
- evidence-before-semantics cannot be preserved;
- shared-channel topology cannot be represented without loss;
- a provider object cannot be scoped uniquely enough for durable identity;
- persistence would require destructive migration of the closed A1 baseline;
- company security refuses `ChannelMessage.Read.All` for delegated core T2;
- company security refuses roster/member scopes and no explicitly approved
  reduced-membership coverage contract exists.

Do not paper over these conditions with mocks or broader permissions.

## 26. First action after this plan is approved

Create one ChatGPT Project for Teams implementation, then start these P0 lanes
concurrently:

- P0-A framework extension map;
- P0-B auth/scope/source identity;
- P0-C exact API/path freeze;
- P0-D fixture harness design;
- P0-E architecture pre-review.

As soon as A-D are complete, give their exact outputs to P0-E for a bounded
closure review.

No Teams production implementation begins before P0 convergence and P0-E
closure PASS.
