# Outlook Mail acquisition-policy Spider Middleware design

Date: 2026-09-30

## Status

This is the formal design for the first implementation phase of Outlook Mail
acquisition rules: the Scrapy Spider Middleware boundary.

The owner has approved the architectural direction in conversation. This
document supersedes the earlier version of this file that proposed persisting
rule-decision sidecar Items in the Mail catalog.

The current approved data-ownership decision is:

- Microsoft source observations and acquired evidence remain in the existing
  acquisition catalog and evidence storage;
- rule evaluation results are not Mail content and are not persisted in the
  final Mail database;
- rule decisions and rule-processing diagnostics are emitted through the
  existing Scrapy/Python logging and stats system;
- logs are observability and audit records, not business-control state;
- later Full-acquisition orchestration must use attempt-local runtime state,
  not parse logs and not add rule decisions to the Mail database.

The prerequisite Mail collection boundary already exists:

- `OutlookDiscoverSpider` is an `OutlookMailCollectionSpider`;
- `OutlookDeltaSpider` reaches the same boundary through
  `OutlookFolderTraversal`;
- `OutlookFolderDeltaSpider` is not a Mail collection spider;
- `OutlookFullSpider` is not a Mail collection spider;
- no acquisition-policy Spider Middleware exists yet.

This specification intentionally defines the middleware integration contract
before the deterministic RuleEngine is implemented.

## Goal

Add a Mail-only Scrapy Spider Middleware that can apply an independently
implemented deterministic acquisition policy to each Outlook Mail observation.

The middleware answers an acquisition-depth question:

> Given this Outlook Mail observation and the currently available rule data,
> should msgloom keep only discovery-level evidence, request a bounded rule
> probe, or select a later Full acquisition profile?

The middleware is not a mailbox mutation system and is not a content-deletion
filter.

Its primary responsibilities are:

1. observe `OutlookMailItem` values emitted by Outlook Mail collection
   spiders;
2. preserve every original provider observation unchanged;
3. call a pure RuleEvaluator contract without implementing matching semantics;
4. schedule at most one bounded probe when the evaluator reports missing data;
5. pass probe results back to the evaluator;
6. emit privacy-safe, searchable rule-decision log events and aggregate stats;
7. expose bounded attempt-local runtime selection state for a future sync
   planner handoff;
8. fail safely when rule data is unresolved or the evaluator/middleware itself
   fails.

## Non-goals

This phase does not implement:

- sender, recipient, subject, category, importance, attachment, or body matching;
- Outlook-like rule conditions, exceptions, ordering, or stop-processing
  semantics beyond the evaluator interface needed by the middleware;
- TOML rule parsing or validation;
- import of Microsoft Outlook Inbox rules;
- persistent rule-decision tables or rule-configuration snapshots;
- new fields on `OutlookMailItem`;
- A2 filtering or A3 triage behavior;
- Full-v1 traversal;
- Mail attachment traversal;
- Outlook mutation of any kind;
- a new logging backend, log file writer, or log rotation subsystem;
- parsing log files as control state;
- automatic historical re-evaluation of unchanged messages.

The later RuleEngine phase will implement deterministic rule semantics against
the contract defined here.

## Terminology

### Provider observation

An `OutlookMailItem` emitted from discovery, delta, or reconciliation. It
represents facts supplied by Microsoft Graph and remains provider/source data.

### Acquisition policy

A deterministic owner-controlled policy that selects how much additional
source evidence msgloom should acquire for a Mail observation.

### Acquisition profile

A stable name for a supported acquisition depth. The rule system is expected
initially to choose between at least:

- `discovery-only`;
- `outlook-mail-full-v1`.

The middleware treats profile names as evaluator outputs. It does not implement
the Full profile.

### RuleEvaluator

A pure deterministic component, implemented later, that consumes one Mail
observation plus optional probe data and returns an evaluation state.

The evaluator has no Scrapy lifecycle responsibility.

### Probe

A bounded additional Graph request made only because a potentially relevant
rule cannot be decided from discovery/delta fields alone.

The first expected probe use is complete message body evaluation.

### Runtime selection state

Attempt-local in-memory control information accumulated while the crawler is
alive. It is not a database record and is not reconstructed by parsing logs.

The future sync planner may consume this state immediately after the collection
crawler closes in the same process.

## Current project baseline

The repository currently runs:

- Scrapy 2.19.0;
- Python 3.13;
- `MicrosoftGraphAddon` for reusable Graph transport components;
- `MessageIngestLogFormatter` for application item summaries;
- `MicrosoftGraphScrapyPrivacyFilter` for Scrapy core log sanitization;
- Scrapy's native Stats Collector;
- Scrapy `PeriodicLog` for periodic aggregate stats;
- `OutlookCrawlStatusExtension` for terminal crawl summaries.

The Mail sync workflow is multi-phase:

1. folder delta;
2. message delta/reconciliation;
3. after the delta crawler closes, plan Full work;
4. run one or more `OutlookFullSpider` phases.

Multi-phase Mail sync rejects a shared `JOBDIR`. The standalone delta primitive
may use `JOBDIR`.

These existing lifecycle choices materially shape this design.

## Component ownership

### `microsoft_graph`

The reusable `microsoft_graph` package remains unaware of msgloom Mail
acquisition policy.

It continues to own:

- Graph authentication and transport;
- retry/error handling;
- request representation;
- provider paths and fields;
- Graph protocol parsing;
- generic Graph diagnostics and privacy behavior.

No msgloom rule model, policy evaluator, rule middleware, rule runtime state, or
rule configuration belongs in this package.

### Mail acquisition domain

Rule contracts and the future deterministic RuleEngine belong under:

`message_ingest/acquisition/microsoft/outlook/email/`

The RuleEngine must remain independent of Scrapy.

The middleware phase may introduce only the minimum contracts needed to call a
future engine, such as evaluation states, required-data descriptors, and a
protocol/interface.

### Spider Middleware

The Scrapy adapter belongs under:

`message_ingest/spidermiddlewares/microsoft/outlook/email.py`

Recommended class name:

`OutlookMailAcquisitionRuleMiddleware`

It owns Scrapy output processing, probe scheduling, logging, aggregate stats,
and attempt-local runtime selection publication.

It must not own predicate semantics.

### Mail collection Spider

`OutlookMailCollectionSpider` is the activation and request-serialization
seam.

It owns:

- per-Spider middleware registration;
- named probe request builders;
- named probe callbacks/errbacks required for Scrapy request serialization;
- any minimal attempt-local runtime container that must remain accessible from
  the crawler after the collection phase.

It must not implement rule matching.

### Item Pipeline

The existing Outlook Mail pipeline remains responsible only for durable source
and acquisition state already in its contract.

This design does not add a rule-decision Item and does not add rule-decision
persistence.

Probe evidence that is genuine acquired source evidence may continue through
the existing evidence path when appropriate. The derived rule decision itself
does not.

### Observability components

The middleware emits safe per-message rule events and increments Scrapy stats.

The existing `OutlookCrawlStatusExtension` remains the natural owner for any
crawl-level terminal summary that includes rule counters.

The middleware must not install its own logging handler or file writer.

## Activation contract

The rule middleware must not be configured globally in
`message_ingest/settings.py`.

Only `OutlookMailCollectionSpider` descendants may register it.

The activation matrix is:

| Spider/resource | Rule middleware configured |
| --- | --- |
| `outlook_discover` | yes |
| `outlook_delta` | yes |
| `outlook_folder_delta` | no |
| `outlook_full` | no |
| Outlook Calendar spiders | no |
| Microsoft To Do spiders | no |
| Microsoft OneDrive spiders | no |
| Microsoft Contacts spiders | no |
| Microsoft profile spider | no |

The middleware may then raise `NotConfigured` when Mail rule evaluation is not
enabled for that crawl.

This preserves the key distinction:

- registration is Mail-collection-specific;
- enablement is configuration-specific.

No unrelated Microsoft product should even have this Mail middleware in its
effective per-Spider component dictionary.

## Spider Middleware priority and ordering

The intended custom middleware priority is `1100`.

Scrapy 2.19.0 currently provides these relevant built-in Spider Middleware
priorities:

- StartSpiderMiddleware: 25;
- HttpErrorMiddleware: 50;
- RefererMiddleware: 700;
- UrlLengthMiddleware: 800;
- DepthMiddleware: 900;
- MetaCopyDetectionMiddleware: 1000.

Spider output middleware runs in reverse priority order.

Placing the Mail acquisition middleware at 1100 means that a probe Request
created while processing Spider output continues through the lower-priority
built-ins, including MetaCopyDetection, Depth, UrlLength, Referer, and
HttpError-related output behavior.

The implementation test must verify behavior through the real Scrapy
SpiderMiddlewareManager. The numeric priority alone is not sufficient evidence.

The implementation should use Scrapy's component-priority dictionary helper
rather than overwrite the entire `SPIDER_MIDDLEWARES` setting.

## Middleware API shape

Scrapy 2.19.0 supports asynchronous Spider Middleware output.

The middleware needs one-to-many behavior:

- one `OutlookMailItem` must always continue downstream;
- the same Mail Item may additionally cause a probe Request.

`BaseSpiderMiddleware.get_processed_item()` is a one-input/one-output helper
and therefore is not the primary abstraction for this middleware.

The middleware should implement a streaming asynchronous
`process_spider_output` async generator.

Conceptually:

    async for output in result:
        if output is internal probe result:
            consume it
            evaluate it
            publish final decision
            continue

        yield output

        if output is OutlookMailItem:
            evaluate it
            maybe yield one probe Request

The implementation must never materialize the callback iterable into a list.

The middleware does not need a `process_spider_input` hook for the approved
flow.

## Output preservation invariant

Every original `OutlookMailItem` must pass through unchanged.

This remains true when:

- no rule matches;
- the default profile is discovery-only;
- a body probe is needed;
- rule evaluation becomes unresolved;
- the evaluator raises an unexpected exception;
- the middleware itself encounters an internal failure after receiving the
  item.

The acquisition policy decides additional acquisition depth. It does not decide
whether the source observation is allowed to exist in the Mail catalog.

This invariant prevents local policy changes from rewriting source history.

All unrelated Spider outputs also pass through unchanged:

- normal Requests;
- `RawHttpEvidenceItem`;
- folder Items;
- removal Items;
- presence sightings;
- checkpoint candidates;
- other Mail acquisition Items.

An internal rule-probe result is the only output type that the middleware is
expected to consume rather than forward to Item Pipelines.

## RuleEvaluator contract

The middleware and RuleEngine are intentionally separated.

The middleware phase defines the interface but not the matching implementation.

The evaluator must be callable without Scrapy. It receives:

- the original Mail observation;
- optional validated probe data;
- the active immutable rule configuration in the future implementation.

The evaluator returns a bounded result with one of these lifecycle states:

### `FINAL`

The acquisition decision is complete for this observation.

A FINAL result carries at least:

- selected acquisition profile;
- decision outcome code, such as matched or default;
- internal policy-family identity and effective policy digest when rules are
  implemented;
- matched rule identifiers or an equivalent bounded audit reference;
- optional stop-processing rule identifier;
- whether a probe participated.

### `NEEDS_DATA`

The evaluator cannot decide yet because a potentially relevant predicate needs
additional source data.

It carries a bounded required-data descriptor.

The completed middleware-only slice supports one BODY probe class. The follow-up
RuleEngine specification extends `required_data` to a bounded immutable set for
one composite metadata/body/header/extended-property/type probe without changing
the one-probe cardinality.

The middleware must never translate missing required data into a negative
match.

### `UNRESOLVED`

Required source data could not be safely obtained or bound to the original
observation.

It carries:

- a bounded reason code;
- a fail-safe selected profile.

The intended V1 fail-safe profile is `outlook-mail-full-v1`.

### Programming failure

An exception raised by the evaluator is not an `UNRESOLVED` source-data
condition. It is a software/integrity failure and follows the separate
programming-failure contract below.

## Cheap-first evaluation expectation

The RuleEngine phase must evaluate discovery-resolvable conditions before
requesting body data.

The middleware only needs to honor `NEEDS_DATA`; it must not know why the
evaluator reached that result.

Examples of expected future evaluator behavior:

- sender mismatch plus body predicate -> FINAL no-match, no probe;
- sender match plus unresolved body predicate -> NEEDS_DATA;
- subject satisfies body-or-subject predicate -> FINAL, no probe;
- the middleware carries `bodyPreview` but does not decide how a future engine
  may use it.

The follow-up RuleEngine specification now deliberately declines to use
`bodyPreview` as terminal body-matching evidence because V1 defines its own
deterministic logical-text projection for complete HTML/text bodies.

This keeps rule semantics out of the middleware while ensuring the middleware
supports efficient evaluation.

## Probe contract

### Why the middleware may schedule a probe

Microsoft Graph discovery exposes `bodyPreview`, but Outlook-like complete body
matching cannot use a negative preview as negative proof.

A bounded detail/body probe is therefore required for some future RuleEngine
results.

### Request ownership

The middleware decides whether a probe is required.

The actual Request must be constructed by
`OutlookMailCollectionSpider` through a named request builder.

The Request callback and errback must be named methods on the Spider.

This is required because Scrapy `JOBDIR` serializes callback/errback method
names relative to the Spider. A middleware-bound callback would not satisfy
the established resume contract.

### Expected Spider methods

The exact names may vary, but the contract should be equivalent to:

- `mail_rule_probe_request(...)`;
- `parse_mail_rule_probe(...)`;
- a named error path compatible with the existing Graph acquisition failure
  model.

The callback must not evaluate rules.

### Probe representation

The first expected V1 probe selects only fields needed for rule evaluation and
version binding.

The middleware-only body-probe slice implemented the then-minimal fields:

- message id;
- `lastModifiedDateTime`;
- full body;
- body preview when useful for comparison/debug validation.

The follow-up RuleEngine specification extends this probe to a composite fact
model and adds `changeKey` as the authoritative message-version token.

`uniqueBody` is not required by the middleware contract unless the later
RuleEngine explicitly proves it is needed.

The request should ask Graph for text body representation while retaining the
existing Outlook immutable-ID preference.

### Mutation fence

The body probe must be compatible with the original observation. The
middleware-only slice preserved `lastModifiedDateTime` on both sides because
that was the metadata available when this contract was implemented.

The follow-up RuleEngine specification supersedes the future-fence detail here:
Mail discovery/delta adds `changeKey`, which Microsoft Graph defines as the
message version, and composite-probe evaluation requires exact `changeKey`
equality. Missing or mismatched version identity becomes an unresolved
fail-safe result rather than combining stale metadata with probed facts.

That condition becomes `UNRESOLVED` and uses the fail-safe profile.

### Internal probe result

The named Spider callback emits a bounded internal result intended for the rule
middleware.

It may contain:

- message id;
- original observation identity/version context;
- probed message version;
- body text required by the evaluator;
- evidence reference required for source lineage;
- run id.

It must not contain arbitrary rule configuration.

The custom middleware, at priority 1100, consumes this internal result before
it can reach the ordinary Item Pipeline.

If source evidence for the probe is acquired, the callback may separately emit
the normal source-evidence Item through the existing evidence path.

### Probe cardinality

For one Mail observation and one rule-evaluation attempt:

- at most one V1 body probe may be scheduled;
- several body-dependent rules share that one probe;
- the full ruleset is reevaluated after the probe;
- a second NEEDS_DATA result for the same already-probed data class is treated
  as an integrity/programming problem, not an unbounded probe loop.

## JOBDIR and request serialization

Standalone Mail delta supports Scrapy `JOBDIR`.

Therefore a queued rule-probe Request must survive:

1. Request serialization;
2. clean Spider shutdown;
3. process restart with the same compatible configuration;
4. callback/errback reconstruction against the running Spider.

The implementation must test `Request.to_dict(spider=...)` and
`request_from_dict(..., spider=...)` or an equivalent controlled JOBDIR
round-trip.

The implementation must not store shared mutable Python objects in Request
`meta` or `cb_kwargs` and rely on object identity after resume.

Only bounded serializable rule-probe context may be carried.

The follow-up RuleEngine/configuration phase binds effective policy identity to
the existing execution/JOBDIR context so a job paused under one policy cannot
silently resume under another. That follow-up also defines a one-time
backward-compatible disabled-policy marker bootstrap for pre-feature JOBDIRs.
This binding was outside the middleware-only implementation phase.

## Runtime control state

Rule decisions are not persisted to the Mail database.

They also must not be recovered by parsing log text.

For a future multi-phase Mail sync integration, the collection crawler needs a
bounded attempt-local handoff.

The approved direction is:

- retain only the minimum control state needed by the next phase;
- prefer the set/order of message IDs selected for Full acquisition rather than
  retaining full rule-decision objects;
- keep this state in memory on the collection crawler/Spider runtime;
- expose it through a documented read-only interface after the crawler closes;
- let `run_graph_workflow(...)` / the Mail sync planner consume it immediately.

This is compatible with current Mail sync because multi-phase sync rejects a
shared `JOBDIR`.

Standalone resumable delta does not automatically launch Full acquisition, so
it does not require durable cross-process Full-target handoff.

The middleware-only phase may define the runtime-state interface but does not
modify the Mail sync planner to consume it.

## Failure handling

Failure semantics are deliberately asymmetric.

### Expected source-data failure

Examples:

- probe returns a terminal source response that cannot provide required body
  data;
- the provider resource disappeared;
- a configured acquisition limit prevents usable probe completion;
- the mutation fence fails because the message changed;
- the probe representation is valid source evidence but insufficient for the
  evaluator.

These become a bounded `UNRESOLVED` rule result.

The middleware must:

- preserve the original Mail Item;
- record the safe unresolved event;
- increment unresolved/fallback stats;
- select the evaluator-defined fail-safe profile, expected to be Full-v1.

An expected unresolved condition does not masquerade as NO_MATCH.

### Evaluator or middleware programming failure

Examples:

- unexpected `TypeError`;
- invalid evaluator output shape;
- a second identical NEEDS_DATA request after the required probe was already
  supplied;
- impossible state transition.

The middleware must:

- preserve the original Mail Item if it has already received one;
- call the existing Spider logical-integrity mechanism with a bounded reason,
  such as `mail_rule_evaluation_error`;
- increment an evaluation-error counter;
- emit an ERROR log containing only the exception class name and safe
  correlation identifiers;
- never call `logger.exception()` with arbitrary exception text;
- never silently convert the bug into NO_MATCH or discovery-only.

The existing Mail sync workflow already stops later phases when
`spider.run_failed` is true. This is the correct integrity behavior for a
policy engine whose result cannot be trusted.

### Probe request failure

The probe must use the existing Graph request/error acquisition path wherever
possible so transport failure and raw evidence handling are not reimplemented
inside Spider Middleware.

Expected terminal probe failure is translated to a bounded unresolved rule
condition rather than inventing a second retry system.

## Logging requirements

### Principle

Rule decisions are operational/audit information, not Mail content.

The middleware uses the existing Python/Scrapy logging system.

It must not:

- open a private log file;
- add a logging handler;
- implement rotation;
- bypass Scrapy logging configuration;
- serialize full evaluator objects;
- log raw provider payloads.

### Logger

Use a normal module logger:

`logging.getLogger(__name__)`

The expected logger namespace is the middleware module, for example:

`message_ingest.spidermiddlewares.microsoft.outlook.email`

### Severity policy

Per-message final decisions are INFO because the owner explicitly requires
historical decision audit under ordinary production log levels.

Probe mechanics are DEBUG.

Expected unresolved source-data conditions are WARNING.

Programming/integrity failures are ERROR.

This is the fixed severity model:

| Event class | Level |
| --- | --- |
| final rule decision | INFO |
| probe scheduled/completed | DEBUG |
| expected unresolved/fallback | WARNING |
| evaluator/middleware programming failure | ERROR |
| crawl-level rule summary | INFO |

### Event vocabulary

Log messages use a stable machine-searchable event token.

Recommended events:

- `outlook_mail_rule_decision`;
- `outlook_mail_rule_probe_scheduled`;
- `outlook_mail_rule_probe_completed`;
- `outlook_mail_rule_unresolved`;
- `outlook_mail_rule_error`;
- `outlook_mail_rule_summary`.

Human prose around these tokens should stay stable and short.

### Final decision log

One final decision event is emitted per evaluated Mail observation.

The allowlisted fields are:

- `event`;
- `run_id`;
- `message_id`;
- `observation_kind`;
- `ruleset_id` as the fixed internal policy-family identifier when available;
- no content-derived policy digest; the follow-up RuleEngine spec reserves that
  digest for private control state;
- decision outcome code;
- selected profile;
- matched rule identifiers;
- optional stop-processing rule identifier;
- probe count or probe-used boolean;
- fallback-used boolean.

Example shape:

    Outlook Mail rule decision:
    event=outlook_mail_rule_decision
    run_id=<opaque-run-id>
    message_id=<opaque-message-id>
    observation_kind=delta
    ruleset_id=outlook-mail-acquisition-rules-v1
    outcome=matched
    profile=outlook-mail-full-v1
    matched_rules=r17,r22
    stop_rule=r22
    probe_used=true
    fallback_used=false

The implementation may render this on one physical line. The field vocabulary,
not whitespace, is the compatibility contract.

### Probe logs

Probe scheduling and completion logs contain only:

- event;
- run id;
- message id;
- bounded probe kind;
- bounded status/reason code.

They do not contain body data or the Graph request URL.

### Error logs

Programming errors include only:

- event;
- run id;
- message id when known;
- bounded phase;
- exception class name;
- bounded integrity reason code.

They must not include:

- exception message text;
- traceback text from the middleware logger;
- evaluator repr;
- rule source values.

### Prohibited log data

The middleware must never intentionally log:

- subject text;
- body text or body preview;
- sender or recipient addresses;
- configured match strings;
- configured body/subject keywords;
- local label values;
- full rule names;
- raw ruleset TOML;
- raw canonical rule JSON;
- Graph URLs;
- authentication/token data;
- arbitrary exception text.

Rule IDs are allowed because exact rule correlation is required by the owner,
but they are user-controlled identifiers and may themselves be sensitive.
Documentation should recommend stable low-sensitivity rule IDs.

Message IDs and run IDs are already used by current Mail diagnostics and are
allowed as opaque correlation identifiers. Log storage must still be
access-controlled.

### Historical explainability limit

Because the owner chose not to persist rule decisions or canonical ruleset
snapshots in the Mail database, the logging contract does not guarantee exact
historical rule replay after a configuration file is changed or deleted.

The logs guarantee event-level audit:

- which message was evaluated;
- which internal policy-family identity was active; the effective policy digest
  remains private control state under the follow-up RuleEngine specification;
- which rule IDs matched;
- which profile was selected;
- whether a probe or fallback participated.

Exact reconstruction of the old predicate values requires the deployment to
retain/version owner configuration separately.

The middleware must not solve that limitation by logging private rule values.

## Log retention boundary

Repository inspection currently shows no project-owned `LOG_FILE`,
`RotatingFileHandler`, logrotate, or journald retention configuration.

Therefore this feature has two distinct contracts:

### Middleware contract

Emit stable privacy-safe Python/Scrapy LogRecords at the defined levels.

### Deployment contract

Retain, rotate, protect, and optionally index the process log stream long enough
to satisfy the owner's audit needs.

The middleware implementation must not create a second logging subsystem.

A later deployment change may use Scrapy `LOG_FILE`, systemd/journald, a
container log driver, or another deployment-standard sink.

Until such retention is configured, the application can produce correct audit
events but cannot promise they remain available indefinitely.

## Stats requirements

Stats are aggregate observability only.

Recommended counters:

- `msgloom/crawl/mail_rules/evaluated_count`;
- `msgloom/crawl/mail_rules/matched_count`;
- `msgloom/crawl/mail_rules/default_count`;
- `msgloom/crawl/mail_rules/unresolved_count`;
- `msgloom/crawl/mail_rules/probe_scheduled_count`;
- `msgloom/crawl/mail_rules/probe_completed_count`;
- `msgloom/crawl/mail_rules/probe_failed_count`;
- `msgloom/crawl/mail_rules/stop_processing_count`;
- `msgloom/crawl/mail_rules/fallback_count`;
- `msgloom/crawl/mail_rules/evaluation_error_count`.

Do not put identifiers in stat-key labels.

In particular, do not create per-message or per-rule stat-key families.

The existing `PeriodicLog` includes the `msgloom/crawl/` family, so these
counters naturally participate in current periodic observability.

Stats must never be read as acquisition correctness/control state.

## Crawl-level summary

The existing `OutlookCrawlStatusExtension` already owns terminal Mail crawl
summaries.

When rule middleware is enabled, it should include bounded aggregate rule
counters in the existing final summary or emit one additional INFO summary
event.

The summary must not list message IDs or rule IDs.

The status extension remains observational: it does not decide which messages
are Full targets.

## Privacy integration

The project already protects Scrapy core logs with:

- `MessageIngestLogFormatter`;
- `MicrosoftGraphScrapyPrivacyFilter`.

These protections remain active.

However, middleware-authored log messages must be safe at creation time and
must not rely on the privacy filter to redact them.

Tests must inspect both:

- rendered log text;
- structured LogRecord extras where the test harness exposes them.

No unsafe object should be attached to `extra` merely because the formatted
message is safe.

## Backward compatibility

With Mail rules disabled:

- the custom middleware may be absent or raise `NotConfigured`;
- no probe Requests are scheduled;
- no per-message rule-decision logs are emitted;
- no rule counters are incremented;
- discovery/delta Item output is unchanged;
- current Mail sync behavior is unchanged;
- other Microsoft products are unchanged.

This is a hard acceptance requirement.

The first middleware-only implementation must not change the current
planner-driven Full behavior because the actual RuleEngine and planner handoff
are separate phases.

## Concurrency and ordering

Current project settings use `CONCURRENT_ITEMS = 1`, but the middleware design
must not rely on Item Pipeline completion order.

The middleware runs before Item Pipelines and makes no database write.

It may maintain attempt-local runtime selection state keyed by message ID, but
that state must be updated synchronously with the final evaluation event so
there is no background task whose completion is inferred from Spider close.

One Mail observation may be reevaluated after a probe.

The implementation must define deterministic overwrite behavior for duplicate
observations of the same message within one attempt before the runtime handoff
is connected to the planner.

The completed middleware-only phase uses last-observation-in-evaluation-order
semantics for its provisional profile map while every decision remains
independently logged. Before planner consumption, the follow-up RuleEngine spec
replaces that provisional handoff behavior with monotonic strongest-profile
accumulation so callback ordering cannot downgrade a Full requirement.

## Middleware phase implementation boundary

The first implementation phase is allowed to add:

- `OutlookMailAcquisitionRuleMiddleware`;
- evaluator protocol/result contracts required by the middleware;
- internal probe-result contract;
- Mail-collection named probe request/callback seam;
- Mail-only per-Spider middleware registration;
- middleware priority 1100;
- streaming output handling;
- safe per-message logs;
- aggregate stats;
- logical-run integrity handling;
- attempt-local runtime-state interface;
- focused middleware/JOBDIR/privacy tests;
- documentation updates.

It must not add:

- actual Outlook-like predicate evaluation;
- TOML rules;
- rules CLI;
- rule-decision SQL models;
- rule-decision Item Pipeline code;
- Mail sync planner consumption;
- Full-v1 traversal changes.

Tests may inject a deterministic fake evaluator.

## Test contract

### Component activation

Verify effective crawler settings, not only inheritance.

Required matrix:

| Spider/resource | Middleware present in effective Spider Middleware settings |
| --- | --- |
| Outlook Mail discover | yes |
| Outlook Mail delta | yes |
| Outlook Mail folder delta | no |
| Outlook Mail full | no |
| Outlook Calendar | no |
| To Do | no |
| OneDrive | no |
| Contacts | no |
| Microsoft profile | no |

When rule evaluation is disabled, construction may end in `NotConfigured`
without changing crawl behavior.

### Streaming output

Using real Scrapy Requests/Responses and the actual middleware manager where
ordering matters, prove:

- Requests pass through;
- non-Mail Items pass through;
- original `OutlookMailItem` is preserved;
- FINAL decision adds no unnecessary Request;
- NEEDS_DATA emits exactly one probe Request;
- middleware does not materialize callback output;
- internal probe result is consumed before Item Pipeline processing.

### Priority behavior

Prove that a Request emitted by the custom middleware continues through the
expected lower-priority built-in output middleware chain.

At minimum confirm the intended Depth/Referer-compatible behavior rather than
only comparing numeric priorities.

### Probe serialization

Prove:

- probe callback is a named Spider method;
- errback is serializable;
- required `cb_kwargs`/meta are bounded and serializable;
- Request `to_dict` / `request_from_dict` round-trip restores the callback;
- a controlled JOBDIR pause/resume does not increment
  `scheduler/unserializable` for the probe.

### Rule lifecycle with fake evaluator

Cover:

- FINAL full profile;
- FINAL discovery-only profile;
- NEEDS_DATA then FINAL;
- NEEDS_DATA then UNRESOLVED;
- duplicate NEEDS_DATA after probe is treated as integrity failure;
- evaluator exception marks the logical run failed;
- original Mail Item remains available in all cases.

### Logging

Capture logs at the relevant levels and verify:

- one INFO final-decision event per final evaluation;
- DEBUG probe events;
- WARNING unresolved event;
- ERROR programming-failure event;
- message/run/rule correlation fields are present where defined;
- subject, body, addresses, keywords, labels, URLs, exception message text, and
  traceback text are absent;
- the same sensitive values are absent from structured record extras.

### Stats

Verify aggregate counters and ensure no identifier appears in stat-key names.

### Regression

Run:

- the focused Outlook Mail middleware tests;
- relevant Outlook discover/delta/full/folder-delta tests;
- logging/privacy tests;
- JOBDIR/resume tests;
- Ruff;
- Pyright;
- the repository's supported xdist/non-xdist pytest split.

The repository currently supports stable xdist collection after assigning
explicit IDs to the dynamic native-parser parameterization; that regression
must remain green.

## Acceptance criteria

The middleware phase is complete only when all of the following are true:

1. only Outlook Mail collection spiders configure the middleware;
2. unrelated Microsoft products do not configure it;
3. original Mail observations are never dropped or mutated;
4. the middleware does not implement rule predicates;
5. output processing remains streaming;
6. FINAL, NEEDS_DATA, and UNRESOLVED states are representable;
7. one Mail observation schedules at most one V1 body probe;
8. probe callbacks are named Spider methods and survive request serialization;
9. expected source-data failure selects the fail-safe path without becoming a
   false NO_MATCH;
10. programming failure marks the logical run failed without losing the source
    observation;
11. per-message final decisions are emitted at INFO;
12. probe details are DEBUG, unresolved source conditions WARNING, and software
    failures ERROR;
13. logs contain the approved correlation fields but no Mail content or
    configured match values;
14. stats are aggregate and identifier-free;
15. rule decisions are not written to the Mail database;
16. logs are never parsed as business-control state;
17. no-rules behavior is unchanged;
18. current Full spider behavior is unchanged;
19. the supported repository test/lint/type-check suite is green.

## RuleEngine and planner follow-up

The deterministic RuleEngine, universal Mail user-configuration slice,
composite probe, policy/JOBDIR identity, and planner/checkpoint integration are
now specified separately in:

`docs/superpowers/specs/2026-10-01-outlook-mail-rule-engine-configuration-design.md`

That specification supersedes the earlier future-phase sketch in this document.
In particular, planner integration now requires rules-enabled Mail sync to hold
message-delta checkpoint promotion until every rule-required Full target meets
the current-attempt terminal-completeness gate, so incomplete Full work cannot
lose a non-persisted policy obligation. The completed middleware contracts in
this document remain authoritative unless the new spec explicitly extends them.

## Rejected alternatives

### Global Spider Middleware

Rejected because project settings are shared across all Microsoft products.

### Middleware on every Outlook Mail spider

Rejected because folder delta has no Mail message decision and Full acquisition
is already the profile executor.

### Put the middleware in `microsoft_graph`

Rejected because msgloom acquisition policy is application behavior, not
reusable Graph transport/provider behavior.

### Drop non-matching Mail Items

Rejected because the policy controls acquisition depth, not source evidence
existence.

### Put rule results on `OutlookMailItem`

Rejected because provider observations and msgloom policy decisions have
different provenance.

### Persist an acquisition-decision sidecar Item

Superseded by the owner's current decision. Rule decisions are audit/control
information and are not part of the final Mail database.

### Use logs as the planner input

Rejected because logs are observability, not correctness/control state.

### Let the middleware implement Full-v1

Rejected because it would duplicate the existing Full spider, attachment
traversal, surface completion, and failure handling.

### Put probe callbacks on the middleware

Rejected because resumable Scrapy Requests bind named callbacks to the Spider.

### Treat body preview as complete body truth

Rejected by the follow-up RuleEngine specification. The discovery preview is
truncated provider-generated text and is not guaranteed to be equivalent to
msgloom's complete logical-body projection, so V1 uses it for neither positive
nor negative terminal body proof.

### Log Mail content for easier debugging

Rejected because it creates a second uncontrolled copy of private mailbox data.

### Give the middleware its own log file

Rejected because it bypasses Scrapy logging configuration and duplicates
deployment-level retention responsibilities.

## Implementation transition

After the owner reviews and approves this formal specification, the next
artifact is a detailed implementation plan for the middleware-only phase.

That plan must follow the implementation boundary and acceptance criteria in
this document. It must not silently reintroduce rule-decision persistence or
pull the RuleEngine implementation into the middleware phase.

## Evidence base

This design was checked against the repository's active Scrapy 2.19.0 runtime,
not against an unreleased Scrapy branch.

Framework references:

- Scrapy 2.19 Spider Middleware documentation:
  [Scrapy 2.19 Spider Middleware](https://docs.scrapy.org/en/2.19/topics/spider-middleware.html)
- Scrapy jobs and request persistence:
  [Scrapy 2.19 Jobs](https://docs.scrapy.org/en/2.19/topics/jobs.html)
- Scrapy Request/Response serialization:
  [Scrapy 2.19 Requests and Responses](https://docs.scrapy.org/en/2.19/topics/request-response.html)
- Scrapy logging:
  [Scrapy 2.19 Logging](https://docs.scrapy.org/en/2.19/topics/logging.html)
- Scrapy signals and stats:
  [Scrapy 2.19 Signals](https://docs.scrapy.org/en/2.19/topics/signals.html)
  and [Scrapy 2.19 Stats](https://docs.scrapy.org/en/2.19/topics/stats.html)
- Scrapy 2.19 implementation inspected locally:
  `scrapy.core.spidermw.SpiderMiddlewareManager`,
  `scrapy.spidermiddlewares.base.BaseSpiderMiddleware`,
  `scrapy.spidermiddlewares.depth.DepthMiddleware`, and
  `scrapy.http.Request.to_dict`.

Provider references relevant to the later body-rule implementation:

- Microsoft Graph message resource:
  [Microsoft Graph message resource](https://learn.microsoft.com/en-us/graph/api/resources/message)
- Microsoft Graph Get message:
  [Microsoft Graph Get message](https://learn.microsoft.com/en-us/graph/api/message-get)
- Microsoft Graph messageRule predicates:
  [Microsoft Graph message resource](https://learn.microsoft.com/en-us/graph/api/resources/message)rulepredicates

Repository contracts inspected for this design include:

- `message_ingest/spiders/microsoft/outlook/email/_base.py`;
- `message_ingest/spiders/microsoft/outlook/email/discover.py`;
- `message_ingest/spiders/microsoft/outlook/email/delta.py`;
- `message_ingest/spiders/microsoft/outlook/email/_folders.py`;
- `message_ingest/spiders/microsoft/outlook/email/full.py`;
- `message_ingest/spiders/microsoft/_graph.py`;
- `message_ingest/commands/microsoft/outlook/sync.py`;
- `message_ingest/observability/formatter.py`;
- `message_ingest/observability/item_summary.py`;
- `message_ingest/extensions/microsoft/outlook/email/status.py`;
- `microsoft_graph/extensions/_logfilters.py`;
- `microsoft_graph/logformatter.py`;
- `docs/statistics.md`.
