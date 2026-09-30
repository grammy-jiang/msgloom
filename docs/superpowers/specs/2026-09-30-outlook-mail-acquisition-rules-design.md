# Outlook Mail acquisition rules design

Date: 2026-09-30

## Status

This document defines the design for deterministic, user-defined Outlook Mail
acquisition rules in A1.

The prerequisite collection boundary has already been implemented:

- OutlookDiscoverSpider and OutlookDeltaSpider are Mail collection spiders.
- OutlookFolderDeltaSpider is not a Mail collection spider.
- OutlookFullSpider is not a Mail collection spider.
- no acquisition-rule Spider Middleware exists yet.

Implementation of the rule system must start only after this design is
reviewed and an implementation plan is approved.

## Goal

Let the owner define deterministic Outlook-like rules over facts they can
recognize in Outlook, such as sender, recipient, subject, importance,
categories, attachments, and message body.

The rule system has two outputs:

1. an acquisition profile that tells the existing planner whether more source
   evidence should be acquired for a message; and
2. local msgloom labels that classify the message without modifying Microsoft
   Outlook.

The system must preserve A1 evidence, resume safety, replayability, and the
existing Microsoft Graph framework boundary.

## Non-goals

V1 does not:

- modify Outlook rules, categories, folders, read state, flags, or messages;
- move, delete, forward, or reply to mail;
- silently import a user's existing Outlook Inbox rules;
- implement arbitrary boolean expressions or regular expressions;
- apply Mail rules to Calendar, To Do, OneDrive, Contacts, or Microsoft profile;
- run acquisition rules inside OutlookFullSpider;
- re-evaluate historical unchanged catalog records when a rules file changes;
- replace A2 filtering or A3 triage rules;
- put rule decisions inside the provider observation represented by
  OutlookMailItem.

## External semantic baseline

The design intentionally follows the parts of Outlook Inbox Rules that map to
msgloom's use case.

Microsoft documents an Inbox rule as having conditions, exceptions, actions,
enablement, and an execution sequence. Outlook also exposes "Stop processing
more rules". Microsoft Graph represents these concepts through messageRule,
messageRulePredicates, and messageRuleActions.

Relevant official references:

- [Microsoft Graph messageRule](https://learn.microsoft.com/en-us/graph/api/resources/messagerule?view=graph-rest-1.0)
- [Microsoft Graph messageRulePredicates](https://learn.microsoft.com/en-us/graph/api/resources/messagerulepredicates?view=graph-rest-1.0)
- [Manage email messages by using rules in Outlook](https://support.microsoft.com/en-us/outlook/mail/manage-email-messages-by-using-rules-in-outlook)
- [Stop processing more rules in Outlook](https://support.microsoft.com/en-us/outlook/mail/stop-processing-more-rules-in-outlook)
- [Microsoft Graph message resource](https://learn.microsoft.com/en-us/graph/api/resources/message?view=graph-rest-1.0)
- [Get message](https://learn.microsoft.com/en-us/graph/api/message-get?view=graph-rest-1.0)

The msgloom rules are not Microsoft rules. Outlook provides the user mental
model and predicate vocabulary; msgloom owns the rule file, actions, evidence,
and persistence semantics.

## Component ownership

### Reusable Microsoft Graph package

microsoft_graph remains unaware of msgloom acquisition rules.

It continues to own:

- Graph authentication and transport behavior;
- safe retry/error handling;
- provider path and field mechanics;
- reusable Outlook Mail fields and request construction;
- Graph protocol parsing;
- representation-aware request identity.

No acquisition-rule model, middleware, persistence, or msgloom configuration
may be added to microsoft_graph.

### Msgloom Mail acquisition domain

Rule models, validation, evaluation, and probe planning belong under:

message_ingest/acquisition/microsoft/outlook/email/

Suggested modules:

- rules.py — immutable rule and result contracts;
- rule_config.py — bounded TOML loading and canonicalization;
- rule_evaluation.py — pure deterministic evaluation.

These modules must not depend on Scrapy.

### Spider Middleware

The Scrapy adapter belongs under:

message_ingest/spidermiddlewares/microsoft/outlook/email.py

Its responsibilities are limited to:

- observing OutlookMailItem outputs from Mail collection spiders;
- calling the pure rule evaluator;
- passing provider Items through unchanged;
- scheduling a bounded body probe when evaluation needs full body data;
- replacing an internal probe-result Item with a durable decision sidecar Item.

It must not:

- implement predicate semantics itself;
- persist state directly;
- perform Full-v1 acquisition;
- alter provider Items;
- apply to unrelated Items.

### Outlook Mail collection spider

OutlookMailCollectionSpider is the activation and request-serialization seam.

It owns named Spider callbacks and request builders required for rule probes so
that probe Requests remain compatible with Scrapy JOBDIR serialization.

It must not own rule matching.

### Item Pipeline

The existing Outlook Mail pipeline remains the durable-state boundary.

It may persist an OutlookMailAcquisitionDecisionItem and its canonical rule
configuration snapshot. It must not mutate the original OutlookMailItem with
the rule result.

### Sync planner

The existing Mail sync planner consumes durable acquisition decisions after the
collection crawler has fully closed.

The planner decides which messages require OutlookFullSpider. The middleware
selects a profile; the Full spider executes that profile.

## Activation contract

The acquisition-rule middleware must never be configured globally in
message_ingest/settings.py.

Only Mail collection spiders may activate it:

| Spider | Rule middleware |
| --- | --- |
| outlook_discover | yes, when a rules file is configured |
| outlook_delta | yes, when a rules file is configured |
| outlook_folder_delta | no |
| outlook_full | no |
| Outlook Calendar spiders | no |
| Microsoft To Do spiders | no |
| Microsoft OneDrive spiders | no |
| Microsoft Contacts spiders | no |
| Microsoft profile spider | no |

OutlookMailCollectionSpider.update_settings() should conditionally add the
middleware to SPIDER_MIDDLEWARES only when
MSGLOOM_OUTLOOK_MAIL_RULES_FILE is non-empty.

Use Scrapy's component-priority-dictionary helper rather than replacing the
whole setting.

The intended middleware priority is above the current built-in Spider
Middleware priorities, for example 1100. On the Spider output path this lets
Requests emitted by the custom middleware continue through the normal built-in
MetaCopy, Depth, UrlLength, Referer, and lower-priority middleware.

The implementation must verify this ordering against Scrapy 2.19.0 rather than
treat the numeric value alone as proof.

## Configuration entry point

### Dedicated A1 rules file

A1 rules use a dedicated owner-controlled TOML file.

They do not reuse A2 FilterConfig, A3 TriageRuleConfig, or
msgloom.configuration.OperatorSettings.

Reasons:

- A1 rules control acquisition cost and source evidence.
- A2/A3 rules operate on already prepared records.
- message_ingest currently has no dependency on msgloom.
- reusing A2/A3 models would create a reverse dependency and conflate
  different lifecycle semantics.

### Scrapy setting

Add:

MSGLOOM_OUTLOOK_MAIL_RULES_FILE

The project default is empty, which means acquisition rules are disabled and
current behavior remains unchanged.

An environment default may be supplied by MSGLOOM_OUTLOOK_MAIL_RULES_FILE,
following the existing settings pattern.

### CLI

Add:

--rules-file PATH

It is valid for:

- scrapy microsoft outlook mail discover
- scrapy microsoft outlook mail delta
- scrapy microsoft outlook mail sync

It is rejected for:

- outlook mail full;
- Calendar;
- To Do;
- OneDrive;
- Contacts;
- profile/auth commands.

The option is applied before CrawlerProcess creation so Spider
update_settings() can see the final path.

Direct developer scrapy crawl usage may use the Scrapy setting explicitly.

### Configuration trust

The rules file is owner configuration and therefore instruction.

Message fields matched by a rule remain source data.

The loader must:

- read a bounded regular file;
- reject malformed TOML and unknown fields;
- reject duplicate rule IDs;
- reject unsupported predicates or profiles;
- reject unbounded expressions and regex;
- produce an immutable validated rule model;
- canonicalize the semantic model to deterministic JSON bytes;
- compute the ruleset digest from canonical bytes, not raw TOML formatting.

Changing comments or harmless TOML formatting must not create a new ruleset
version. Reordering rules must create a new version because rule order affects
behavior.

## V1 rules file model

Illustrative syntax:

    schema_version = 1
    ruleset_id = "owner-mail-acquisition"
    default_profile = "discovery-only"

    [[rules]]
    id = "manager-important"
    name = "Manager mail"
    enabled = true
    stop_processing = true

    [rules.action]
    profile = "outlook-mail-full-v1"
    labels = ["vip", "manager"]

    [rules.conditions]
    from_addresses = ["manager@example.com"]

    [[rules]]
    id = "approval-request"
    name = "Approval request"
    enabled = true
    stop_processing = false

    [rules.action]
    profile = "outlook-mail-full-v1"
    labels = ["approval"]

    [rules.conditions]
    subject_contains = ["approval", "please approve"]
    body_contains = ["approval required"]

    [rules.exceptions]
    from_addresses = ["noreply@example.com"]

The exact TOML spelling may be refined during implementation only if the
semantic model remains identical.

### Rule identity and order

Each rule has a stable unique id.

The array order in the TOML file is the execution order. V1 does not add a
second numeric sequence field.

Each rule also has:

- a human-readable name;
- enabled;
- explicit stop_processing;
- one non-empty conditions object;
- an optional exceptions object;
- one action with at least one effect.

### Action

V1 actions are:

- optional acquisition profile;
- zero or more local labels.

Supported profiles are initially:

- discovery-only;
- outlook-mail-full-v1.

Labels are msgloom-local metadata. They never write Outlook categories.

A matched label-only rule leaves the current profile unchanged.

The current profile starts as default_profile.

A later matched rule that supplies a profile replaces the earlier profile.
Labels accumulate in rule execution order with duplicate values removed by
first occurrence.

stop_processing = true stops evaluation after that rule is fully resolved and
applied.

## Predicate model

V1 supports predicates that map directly to owner-visible Outlook facts and the
current discovery representation.

Recommended initial set:

- from_addresses
- from_domains
- sender_addresses
- to_addresses
- cc_addresses
- recipient_addresses
- subject_equals
- subject_contains
- body_contains
- body_or_subject_contains
- has_attachments
- importance
- categories

Deferred predicates include header matching, message size, sensitivity,
approval/automatic-message classifiers, meeting classifiers, encryption,
signature state, and folder display-name matching.

Folder display names are intentionally deferred because the current Mail Item
contains a folder identifier while user-facing folder names require a separate
catalog lookup and ambiguity policy.

### Predicate composition

Within one rule:

- different condition categories are ANDed;
- multiple values inside one condition category are ORed;
- any matching exception suppresses the rule;
- multiple exception categories are ORed.

No arbitrary nested boolean expression is accepted in V1.

No regex is accepted in V1.

### Text comparison

V1 uses deterministic Unicode case-folded comparisons for addresses, domains,
subject substrings, body substrings, and category values unless an individual
predicate has a stronger exact semantic.

Outer whitespace in configured identities is rejected instead of silently
trimmed.

Email-domain rules compare the domain portion after address validation and
case folding.

The implementation plan must define finite limits for rules, values, labels,
and text lengths before code is written.

## Evaluation state

The pure evaluator must distinguish four states:

- FINAL — the current ruleset can produce a complete acquisition decision;
- NEEDS_DATA — the decision is not yet knowable because a potentially relevant
  body predicate needs full body data;
- UNRESOLVED — required source data could not be acquired or safely bound;
- internal per-rule MATCH / NO_MATCH facts used to produce the above.

NO_MATCH is not equivalent to missing data.

The final durable decision has one of:

- matched — one or more enabled rules applied;
- default — no rule action changed the default decision;
- unresolved — evaluation could not be completed and fail-safe behavior was
  used.

## Cheap-first evaluation

The evaluator first resolves predicates available from the discovery Item.

Example:

    from == ceo@example.com
    AND body contains "Project Phoenix"

If from does not match, the rule is NO_MATCH and no body probe is needed.

If from matches and full body data is unavailable, the rule is NEEDS_DATA.

For body_or_subject_contains, a subject match is sufficient and avoids a probe.

For body_contains, bodyPreview may provide positive evidence when the
configured text is present in the preview. A negative preview is not negative
proof, because Microsoft documents bodyPreview as only the first 255 characters
of the message body.

## Body probe

### Why a probe exists

Outlook server-side rules can evaluate the complete body. A1 discovery cannot.

Microsoft Graph documents bodyPreview as the first 255 characters only.
Therefore V1 must not approximate a negative body_contains result from
bodyPreview.

### Probe representation

A rule probe retrieves a minimal message representation containing at least:

- id;
- lastModifiedDateTime;
- body;
- bodyPreview;
- uniqueBody when useful for evidence/debugging.

The request asks Graph for text body representation using:

Prefer: outlook.body-content-type="text"

and preserves the existing immutable-ID preference.

The body used for the V1 body_contains predicate is the full body, not
uniqueBody. uniqueBody may be retained as evidence but must not silently
change Outlook-like body matching semantics.

### Mutation fence

The original discovery/delta Item already contains lastModifiedDateTime.

A body probe is valid for the original rule decision only when the returned
message version is compatible with that observation.

At minimum V1 compares lastModifiedDateTime.

If the message changed between discovery and probe, the rule decision becomes
UNRESOLVED instead of mixing metadata from one version with body from another.

The fail-safe profile is then applied.

### Probe ownership

The middleware decides that a probe is needed.

OutlookMailCollectionSpider builds the Request and owns the named callback and
errback required for JOBDIR serialization.

The callback:

1. preserves raw HTTP evidence through the existing A1 evidence path;
2. emits an internal bounded probe-result Item carrying only fields required
   for rule evaluation and evidence references.

The middleware consumes that internal probe-result Item, re-runs the pure
evaluator, and emits a durable decision sidecar Item.

Probe callbacks must not live on the middleware object.

## Spider Middleware streaming behavior

The middleware must preserve Scrapy streaming.

It must not materialize an unbounded callback output iterable into a list.

For each ordinary output:

- Requests pass through unchanged.
- non-Mail Items pass through unchanged.
- OutlookMailItem always passes through unchanged.
- an OutlookMailItem may additionally cause one probe Request.
- an internal rule-probe Item is replaced by an acquisition-decision Item.

One message may schedule at most one V1 body probe for one ruleset evaluation.

If several rules need body data, the single probe resolves them together and
the entire ruleset is reevaluated in original order.

## Original Item versus decision sidecar

The original OutlookMailItem represents Microsoft source observation.

It must not gain fields such as:

- matched rule IDs;
- acquisition profile;
- labels;
- ruleset version;
- fallback flags.

Those facts are msgloom decisions, not provider facts.

Instead introduce a sidecar Item, conceptually:

OutlookMailAcquisitionDecisionItem

with bounded fields including:

- source ID context supplied by the crawler/pipeline;
- message_id;
- run_id;
- source observation evidence ID;
- optional probe evidence ID;
- ruleset ID;
- ruleset canonical digest;
- canonical ruleset snapshot or an equivalent durable reference;
- final decision status;
- selected acquisition profile;
- local labels;
- matched rule IDs in execution order;
- optional rule ID that stopped processing;
- fallback-used flag;
- bounded unresolved reason code.

The Item must not duplicate message body, subject, or arbitrary matching source
text.

## Persistence design

### Why the decision goes through Item Pipeline

The decision is structured deterministic state produced from a specific source
observation and ruleset. It therefore belongs in durable Item processing.

The pipeline provides:

- awaited completion;
- shared catalog write locking;
- idempotent replay handling;
- consistent failure observation.

The middleware must not write SQL directly.

### Rule configuration snapshot

A decision must remain explainable after the owner edits the TOML file.

The canonical validated ruleset must therefore be stored durably by digest.

The preferred V1 implementation is:

- the decision Item carries a reference to the same immutable canonical
  ruleset bytes held by the middleware;
- the pipeline upserts one ruleset snapshot keyed by canonical digest;
- the pipeline writes the decision referencing that digest in the same
  awaited transaction where practical.

This avoids dependence on the external rules file for historical explanation.

The canonical snapshot can contain owner-defined addresses and keywords, so it
is private catalog data. It must never be put into stat keys or ordinary logs.

### Decision idempotency

Reprocessing the same source evidence with the same ruleset and same probe
evidence must not create duplicate logical decisions.

A later source observation or a changed ruleset is a different decision input.

The persistence key must therefore bind at least:

- logical source;
- message ID;
- source observation evidence/version;
- ruleset digest;
- probe evidence/version when a probe participated.

The table design must not require the message catalog row to have completed
first. Scrapy Item Pipeline order is per Item, while different Items can
overlap. The decision write must be safe even if the corresponding semantic
message Item is still being processed.

## Fail-safe behavior

Rule evaluation must never convert missing required data into NO_MATCH.

If body acquisition fails, is cancelled by a configured size bound, returns an
unusable representation, or fails the mutation fence:

- decision status is unresolved;
- fallback_used = true;
- the selected profile is outlook-mail-full-v1;
- the reason is recorded as a bounded code;
- source evidence/failure evidence remains preserved.

The rationale is asymmetric risk: an unresolved acquisition decision should
prefer extra source acquisition over silently omitting evidence the owner may
have marked important.

A failure to parse or validate the owner rules file is different. Explicit
invalid configuration fails the crawl before Mail decisions are made; it does
not silently fall back to no rules.

## Existing behavior when no rules file exists

No rules file means:

- no acquisition-rule Spider Middleware is activated;
- no rule-decision Items are emitted;
- no rule probes are issued;
- Mail sync retains the existing changed-message refresh and incomplete-backlog
  enrichment behavior.

This is a hard backward-compatibility requirement.

## Mail sync behavior when rules are enabled

After the delta collection crawler closes, the sync planner reads durable
decisions from that collection run.

Messages whose selected profile is outlook-mail-full-v1 become targets for the
existing OutlookFullSpider.

Messages whose selected profile is discovery-only do not.

The middleware does not duplicate Full-v1 traversal.

### Historical backlog

When rules are enabled, the existing generic "enrich every incomplete
historical backlog message" behavior is disabled for records that have no
decision under the current collection run.

Enabling or changing rules does not automatically reprocess unchanged history.

Reasons:

- rules are acquisition policy for observed source versions;
- retroactive evaluation may require fresh body probes;
- silently applying new rules to old observations would mix configuration and
  evidence time.

A future explicit historical rule-application workflow can be designed
separately.

The full command remains an explicit operator override and does not require a
rule decision.

## Discover and delta primitive behavior

outlook mail discover and outlook mail delta remain collection primitives.

With rules enabled they persist decisions and any required probe evidence, but
they do not automatically start a separate Full crawler.

outlook mail sync remains the normal multi-phase user workflow that consumes
the decisions and launches Full acquisition.

This preserves the existing command architecture.

## JOBDIR and ruleset binding

Rule configuration affects crawl behavior and therefore must be bound to
JOBDIR resume identity.

A delta crawl paused with ruleset A must not resume with ruleset B.

The implementation should extend the existing source/catalog JOBDIR context
mechanism with an optional deterministic execution-context binding.

Requirements:

- no rules file keeps the current source/catalog JOBDIR digest unchanged;
- an enabled ruleset adds its canonical digest to the job context;
- changing the semantic ruleset makes the existing JOBDIR fail closed;
- comments or formatting changes that preserve the canonical ruleset do not
  invalidate resume;
- rejection occurs before provider work resumes whenever the existing
  lifecycle permits it.

Do not create a second generic workflow engine or duplicate Scrapy SpiderState.

## Observability and privacy

Useful stats include counts only:

- messages evaluated;
- matched/default/unresolved decisions;
- probes scheduled/completed/failed;
- profile selection counts;
- matched-rule count totals;
- stop-processing count;
- fallback count.

Do not place these values in stat keys or ordinary logs:

- email addresses;
- subjects;
- body text;
- configured keyword values;
- local label values;
- message IDs;
- attachment IDs;
- raw ruleset payload.

Rule IDs may also be private. Prefer aggregate counts in normal logs; exact rule
IDs remain in private durable decision state.

## Testing contract

### Pure rule engine

Unit tests cover:

- AND across condition categories;
- OR within one category;
- OR across exceptions;
- rule order;
- disabled rules;
- profile replacement;
- label accumulation/deduplication;
- stop-processing;
- case-folded matching;
- sender versus from semantics;
- recipient semantics;
- positive preview body match;
- negative preview producing NEEDS_DATA;
- cheap predicate failure avoiding a body probe;
- body_or_subject_contains short-circuit;
- mutation-fence unresolved result;
- invalid and bounded configurations.

### Component activation matrix

A regression test must prove:

| Component | Middleware loaded |
| --- | --- |
| Outlook Mail discover | yes with config |
| Outlook Mail delta | yes with config |
| Outlook Mail folder delta | no |
| Outlook Mail full | no |
| Outlook Calendar | no |
| To Do | no |
| OneDrive | no |
| Contacts | no |
| Microsoft profile | no |

The test must inspect effective crawler settings, not only class names.

### Middleware integration

Use real Scrapy Request/Response/Item objects and the actual Spider Middleware
manager where ordering matters.

Test:

- non-Mail Items unchanged;
- original Mail Item always preserved;
- final decision without probe;
- one body probe emitted for multiple body predicates;
- probe Request has the named Spider callback;
- callback/cb_kwargs survive Request serialization;
- probe result becomes a decision Item;
- output remains streaming;
- middleware priority lets generated Requests pass through the intended
  built-in middleware chain.

### Persistence

Test:

- ruleset snapshot upsert;
- decision write;
- replay idempotency;
- changed ruleset creates a new decision version;
- probe evidence participates in identity;
- decision persistence does not depend on Mail Item completion order;
- item/pipeline failure marks the run unsafe in the existing integrity path.

### Sync workflow

Test:

- no rules preserves current behavior;
- rules-enabled current-run Full selections are honored;
- discovery-only selections are not enriched;
- unresolved decisions select Full;
- generic historical backlog is not automatically enriched with rules enabled;
- explicit mail full still works independently.

### JOBDIR

Test a controlled pause/resume:

- same canonical ruleset resumes;
- formatting-only file change resumes;
- semantic ruleset change is rejected;
- no-rules legacy behavior remains unchanged;
- queued rule-probe Requests restore the named Spider callback and context.

### Full regression

Run the repository's normal serial suite and the supported parallel/nonparallel
split. The collection must be stable across xdist workers.

## Rollout sequence

Implementation should be split into reviewable stages:

1. rule contracts, TOML loader, canonical digest, and pure evaluator;
2. rules-file CLI/setting and JOBDIR context binding;
3. Mail-only Spider Middleware activation and probe callback contract;
4. decision sidecar Item and catalog persistence;
5. Mail sync planner consumption;
6. integration/resume/privacy tests and documentation;
7. real Microsoft Graph acceptance using a deliberately small mailbox/sample.

Each stage must keep no-rules behavior green.

## Rejected alternatives

### Global Spider Middleware

Rejected because project settings are shared by all Microsoft products and
would load Mail policy into unrelated spiders.

### Rule middleware on every Outlook Mail spider

Rejected because folder-delta has no message decision and Full is already the
profile executor.

### Put rules in microsoft_graph

Rejected because acquisition policy is application behavior, not reusable Graph
transport/provider mechanics.

### Reuse A2/A3 filter models

Rejected because their inputs, lifecycle, actions, and package ownership differ
from A1 acquisition.

### Put rule results inside OutlookMailItem

Rejected because provider observation and msgloom decision have different
provenance and versioning.

### Let middleware perform Full-v1 acquisition itself

Rejected because it would duplicate the existing Full spider, attachment
traversal, surface completion, failure, and resume logic.

### Treat bodyPreview miss as body miss

Rejected because Microsoft documents the preview as only the first 255
characters.

### Automatically import Outlook Inbox Rules

Deferred. Outlook rule actions express mailbox-organization intent, not
necessarily evidence-acquisition intent. A future importer may map selected
conditions into an owner-reviewed msgloom rule template, but must not silently
adopt Outlook rules as acquisition policy.
