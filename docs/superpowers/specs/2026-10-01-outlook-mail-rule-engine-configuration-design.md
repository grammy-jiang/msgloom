# Outlook Mail deterministic RuleEngine and user configuration design

## Status

Design approved conversationally on 2026-09-30 / 2026-10-01. This document is
the implementation contract for the next phase after the completed Outlook Mail
acquisition-rule Spider Middleware slice.

Implementation has not started. The existing middleware remains the runtime
adapter; this phase supplies the real deterministic RuleEngine, the first
universal user-configuration slice, and the Mail sync planner/checkpoint handoff.

## Intent

msgloom should let a non-technical user decide which Outlook Mail messages need
only lightweight discovery data and which need the existing Full-v1 acquisition
profile. The policy must be deterministic, explainable, safe to resume, and
simple to maintain in one user configuration file.

The user should be able to express common Outlook-like rules, exceptions,
ordered processing, regular expressions, and a small set of useful msgloom
extensions without learning Scrapy, Microsoft Graph internals, RE2 APIs, or
msgloom's internal profile version names.

Success means:

- one default user configuration file;
- zero-config behavior remains exactly as it is today;
- rule evaluation never mutates or drops the original provider observation;
- evaluation is deterministic for the same semantic ruleset and source facts;
- expensive provider data is fetched only when cheap facts cannot decide the
  result;
- one observation schedules at most one rule probe;
- rule decisions are not persisted as Mail content/catalog state;
- rules-enabled Mail sync cannot lose a required Full acquisition if a later
  Full crawler fails;
- resumable JOBDIR execution cannot mix different policy semantics;
- logs and Scrapy settings never expose configured email addresses, keywords,
  regex patterns, body criteria, or provider payloads;
- user-facing documentation contains high-quality examples covering normal,
  exceptional, and failure cases.

## Scope

This phase includes:

- the first universal `msgloom.toml` resolver needed by Outlook Mail rules;
- Outlook Mail rule configuration models and validation;
- canonical Mail ruleset identity and digest;
- Google RE2-backed `msgloom-regex-v1` support;
- deterministic RuleEngine implementation behind the already-defined
  `MailRuleEvaluator` boundary;
- expansion of the current body-only rule probe into one dynamic composite
  rule probe;
- Mail ruleset JOBDIR binding;
- attempt-local Full-target handoff to `outlook mail sync`;
- rules-enabled deferred message-delta checkpoint promotion;
- user and developer documentation;
- focused and regression tests, including real Scrapy lifecycle tests.

This phase does not include:

- arbitrary nested boolean expressions;
- a generic workflow/rules language shared by every msgloom product;
- durable per-message rule decisions;
- parsing logs as planner/control state;
- retroactive reevaluation of every unchanged historical Mail message after a
  ruleset change;
- automatic migration of old acquisition decisions;
- a rewrite/migration of all existing A2/A3/A5 CLI configuration entrypoints;
- hot reloading configuration during a running command;
- changing the existing Full-v1 acquisition implementation;
- changing other Microsoft products.

## Existing baseline

The completed middleware slice already provides:

- `MailRuleEvaluationState`: `FINAL`, `NEEDS_DATA`, `UNRESOLVED`;
- `MailRuleDecisionOutcome`: `MATCHED`, `DEFAULT`, `UNRESOLVED`;
- bounded observation and probe contracts;
- a `MailRuleEvaluator` protocol;
- Mail-only Spider Middleware registration on discovery/delta collection
  spiders;
- preservation of the original `OutlookMailItem`;
- one body-probe lifecycle with named Spider callbacks for JOBDIR;
- attempt-local selected-profile state;
- safe decision/probe/unresolved/error logs and aggregate stats;
- silent `NotConfigured` behavior when no evaluator is present;
- fail-closed programming/integrity handling.

This design extends those contracts rather than moving policy logic into the
middleware.

## 1. Configuration architecture

### 1.1 One universal user configuration file

The default configuration location is:

```text
$XDG_CONFIG_HOME/msgloom/msgloom.toml
```

When `XDG_CONFIG_HOME` is unset or empty:

```text
~/.config/msgloom/msgloom.toml
```

A relative `XDG_CONFIG_HOME` is invalid per the XDG Base Directory contract and
must not be treated as a valid base path; msgloom falls back to `~/.config`.

msgloom does not search the current working directory and does not merge
multiple config files. It deliberately does not search `$XDG_CONFIG_DIRS` for
this user policy file.

An explicit command option:

```text
--config FILE
```

selects one complete alternative universal configuration file. It does not
merge with the default file.

### 1.2 Missing and invalid files

| Situation | Required behavior |
| --- | --- |
| default config file does not exist | valid; use built-in empty/default config |
| default config exists but is empty/comment-only | valid; equivalent to empty/default config |
| default config exists and is valid | load it |
| default config exists but is invalid | fail command startup |
| explicit `--config FILE` does not exist | fail command startup |
| explicit `--config FILE` is invalid | fail command startup |
| file changes during a running command | current command remains on its frozen snapshot |

An invalid existing file must never be treated as if it were absent. Silent
fallback could make a user believe rules are active when they are not.

### 1.3 Universal document, operation-specific validation

The user still maintains one file, but msgloom does not require every subsystem
to be fully configured for every operation.

Conceptually:

```text
UniversalConfigDocument
    |
    +-- acquisition
    |     +-- microsoft
    |           +-- outlook
    |                 +-- mail
    +-- preparation
    +-- triage
    +-- report
    +-- future sections
```

The universal loader owns bounded file discovery/read/TOML decoding. Individual
operations strictly validate only the sections they require.

Examples:

- Outlook Mail acquisition validates the Mail acquisition section;
- triage validates the sections required by triage;
- report validates report configuration;
- once the existing operator CLI is migrated to the universal resolver,
  `config validate` validates every present supported section.

This phase only needs to add enough universal-document infrastructure for the
Outlook Mail slice. It must not force a broad A2/A3/A5 migration. The resolver
and document shape must not create a separate Mail-only file or dead-end schema;
they are the foundation those existing operator sections can migrate onto later.

As a transitional compatibility boundary, existing non-Scrapy A2/A3/A5 CLI
entrypoints may retain their current explicit-config invocation in this phase.
That temporary compatibility does not authorize a second Mail-specific config
file. Integrating those CLI entrypoints with the XDG default resolver and the
universal `config validate/inspect` experience is a later configuration-migration
slice, not a prerequisite for the Mail RuleEngine.

### 1.4 Separate Scrapy and msgloom policy configuration planes

Scrapy settings and user acquisition policy are different concerns.

```text
SCRAPY CONFIGURATION PLANE
scrapy.cfg
  -> message_ingest.settings
  -> command defaults / -s overrides
  -> add-ons
  -> Spider.update_settings()
  -> middleware / extensions / pipelines

MSGLOOM USER POLICY PLANE
msgloom.toml
  -> UniversalConfigResolver
  -> MailRulesetConfig
  -> MailRuleEvaluator
```

Scrapy settings answer how the crawler/runtime operates. The universal config
answers what the user wants msgloom to do with acquired data.

Raw universal configuration must not become a Scrapy settings source.

Specifically, Scrapy settings must never contain:

- raw rule models;
- configured email addresses;
- subject/body/category match values;
- regex strings;
- compiled RE2 objects;
- RuleEngine instances.

Scrapy 2.19 logs overridden settings after settings are applied/frozen, so
putting private policy values in settings would create a privacy leak even if
msgloom's own logs were careful.

### 1.5 Command lifecycle

The supported user path is the unified Microsoft command, for example:

```text
scrapy microsoft outlook mail sync
scrapy microsoft outlook mail sync --config /path/to/msgloom.toml
```

The command must resolve, load, validate, canonicalize, and freeze the universal
config once before the first Mail crawler is created. Every phase in that user
invocation receives the same immutable semantic Mail policy.

`--mailbox` remains a Scrapy setting because it affects provider targeting and
required Graph permissions. `--config` is different: it selects msgloom policy
and must not be converted into raw Scrapy settings.

Programmatic handoff to collection spiders should use private Python Spider
arguments/config objects, not environment variables, globals, a singleton
registry, or Scrapy settings.

Direct developer execution such as:

```text
scrapy crawl outlook_delta
```

may resolve the default XDG config itself when no command-owned runtime context
exists. V1 does not add a second `-s MSGLOOM_CONFIG_FILE=...` configuration
route merely for direct crawl override.

## 2. User-facing Mail configuration

### 2.1 Minimal activation model

The Mail policy section is optional.

Rules are active only when the user explicitly writes:

```toml
[acquisition.microsoft.outlook.mail]
enabled = true
```

Required semantics:

| State | Behavior |
| --- | --- |
| section absent | rules disabled; current behavior unchanged |
| section present, `enabled` omitted | rules disabled |
| `enabled = false` | rules disabled |
| `enabled = true` | deterministic RuleEngine active |

The explicit activation gate prevents an accidentally-created empty section from
silently changing Mail acquisition depth. All fields that are present are still
validated even when the global policy is disabled; `enabled = false` is not a
syntax/validation escape hatch.

### 2.2 User profile vocabulary

The user-facing profile names are deliberately simple:

```text
discovery
full
```

They map to versioned internal contracts:

| User value | Internal contract |
| --- | --- |
| `discovery` | `outlook-mail-discovery-v1` |
| `full` | `outlook-mail-full-v1` |

Internal version names must not be required in user TOML.

The V1 profile lattice is:

```text
discovery < full
```

### 2.3 Default profile

When policy is enabled, the default profile is `discovery` unless explicitly
configured otherwise.

Typical policy:

```toml
[acquisition.microsoft.outlook.mail]
enabled = true
default_profile = "discovery"
```

An enabled policy with no rules is valid:

```toml
[acquisition.microsoft.outlook.mail]
enabled = true
default_profile = "discovery"
```

This means every evaluated message remains discovery-only.

Likewise:

```toml
[acquisition.microsoft.outlook.mail]
enabled = true
default_profile = "full"
```

means every evaluated message is Full. Because profile combination is monotonic,
a later rule cannot downgrade this to discovery.

### 2.4 Rule shape

A rule has:

- `id`;
- `sequence`;
- optional `enabled` (default true);
- `profile`;
- optional `stop_processing` (default false);
- one conditions block;
- zero or more exception blocks.

Example:

```toml
[[acquisition.microsoft.outlook.mail.rules]]
id = "finance-approval"
sequence = 10
enabled = true
profile = "full"
stop_processing = true

[acquisition.microsoft.outlook.mail.rules.conditions]
from_addresses = ["manager@example.com"]
subject_contains = ["approval"]
```

Rule IDs must be unique. `sequence` is an integer in the inclusive range
0..2,147,483,647 and must be unique within the Mail ruleset. V1 does not use a
hidden rule-ID tie-breaker for equal sequence numbers.

A disabled rule remains fully validated, including its regex syntax and field
names. Users who want to keep invalid/incomplete experiments should comment them
out rather than rely on `enabled = false` as a syntax escape hatch.

### 2.5 Boolean semantics

V1 intentionally does not support arbitrary nested boolean expressions.

A conditions block must contain at least one predicate. An exception block must
also contain at least one predicate. Configured list-valued predicates must be
non-empty. Exact duplicate entries are rejected; ordinary case-insensitive
text/address/category lists also reject duplicates after case-folding. Regex
patterns remain distinct by their literal pattern string.

Within a condition block:

- multiple values of one predicate are OR;
- different predicate fields are AND.

Example:

```toml
[acquisition.microsoft.outlook.mail.rules.conditions]
from_addresses = ["a@example.com", "b@example.com"]
subject_contains = ["approval", "invoice"]
has_attachments = true
```

means:

```text
(from == a OR from == b)
AND
(subject contains approval OR subject contains invoice)
AND
has_attachments
```

Exceptions are a list of blocks:

- fields inside one exception block are AND;
- values inside one predicate are OR;
- exception blocks are OR.

Example:

```toml
[[acquisition.microsoft.outlook.mail.rules.exceptions]]
categories = ["Ignore"]

[[acquisition.microsoft.outlook.mail.rules.exceptions]]
from_addresses = ["automation@example.com"]
subject_contains = ["test"]
```

means:

```text
except if category == Ignore
OR
except if (from == automation@example.com AND subject contains test)
```

### 2.6 Rule ordering and profile combination

Rules are evaluated by ascending unique `sequence`.

The selected profile starts at `default_profile`. Each matching rule can only
maintain or upgrade the selected profile:

```text
selected = max(selected, matching_rule.profile)
```

For V1:

```text
max(discovery, full) = full
```

A later broad discovery rule cannot undo an earlier Full selection.

`stop_processing = true` means the matching rule applies its profile and then
prevents all later rules from being evaluated.

Because `full` is the maximal V1 acquisition profile, once the engine has
selected `full`, later rules cannot change the acquisition result. The engine
may therefore terminate rule evaluation at that point and must not fetch extra
provider data solely to discover additional audit-only matches.
`matched_rule_ids` records rules actually evaluated/matched on the decision
path; it is not a promise to probe every later no-op rule for audit completeness.

Example:

```toml
[[acquisition.microsoft.outlook.mail.rules]]
id = "newsletter"
sequence = 10
profile = "discovery"
stop_processing = true

[acquisition.microsoft.outlook.mail.rules.conditions]
from_address_regex = ["@newsletter\\.example$"]

[[acquisition.microsoft.outlook.mail.rules]]
id = "approval"
sequence = 20
profile = "full"

[acquisition.microsoft.outlook.mail.rules.conditions]
subject_contains = ["approval"]
```

A matching newsletter stops before the approval rule.

## 3. Text matching and regular expressions

### 3.1 Default case behavior

All user-oriented textual predicates are case-insensitive by default. Users
should not need to reason about capitalization to make normal rules work.

This includes:

- email-address predicates;
- subject/body contains and exact predicates;
- categories;
- header textual predicates;
- regex predicates.

Ordinary exact/contains comparisons use a consistent Unicode-aware
case-insensitive comparison strategy. They do not introduce accent folding or
other broad text rewriting beyond the documented case-insensitive behavior.

Email-address comparisons are deliberately case-insensitive for user-facing
rule behavior, even though obscure protocol edge cases can distinguish local
part case.

Documented textual enum values in the user config, including profiles,
importance, sensitivity, follow-up status, inference classification, and
message-action flag names, are accepted case-insensitively and canonicalized to
the documented lowercase/snake-case form before semantic hashing. Structural
TOML field names remain exact.

### 3.2 `msgloom-regex-v1`

V1 regex is a msgloom language contract implemented by the maintained Google
RE2 Python binding (`google-re2`). The public contract is not the dependency
package name or version.

The engine abstraction is conceptually:

```text
MailRegexEngine
  compile(pattern)
  search(compiled, text) -> bool
```

User regex strings are preserved exactly. msgloom does not prepend inline
flags, escape the pattern, or rewrite it. Case-insensitive default behavior is
supplied through RE2 engine options.

Regex predicates use search semantics: a match anywhere in the field is a
match. Users may use anchors to require full-field boundaries.

Examples:

```toml
subject_regex = ["invoice\\s+#\\d+"]
from_address_regex = ["@example\\.com$"]
subject_regex = ["^urgent:"]
```

The default case-insensitive engine setting means `^urgent:` also matches
`URGENT:`. Advanced users may use RE2-supported inline options such as an
explicit case-sensitive region when needed.

`msgloom-regex-v1` deliberately excludes constructs RE2 does not support,
including backreferences and look-around. Invalid/unsupported regex is a
configuration-time error, not a per-message runtime surprise.

msgloom does not perform Unicode normalization before regex evaluation. Regex
matches the source text under RE2 semantics plus the configured case setting.

### 3.3 Regex maintenance rationale

`regex` was considered because it supports timeouts and a very broad Python-like
syntax. It was rejected as the default long-lived dependency because current
maintenance is strongly centered on a single maintainer.

Google RE2 was selected for V1 because:

- it has a long-lived upstream implementation and official Python binding;
- it intentionally avoids catastrophic backtracking;
- it provides predictable linear-time matching behavior for the supported
  syntax;
- Linux/aarch64 and current supported Python releases have suitable packaging;
- msgloom can hide the concrete engine behind `msgloom-regex-v1` so a future
  compatible implementation does not require user config changes.

## 4. Predicate coverage

### 4.1 Principle

V1 should cover common Outlook-like rule conditions wherever msgloom can derive
reliable local facts. It may add useful msgloom extensions. It must not pretend
to support an Outlook predicate through an unproven heuristic.

Unsupported/deferred predicates are rejected during configuration validation;
they are never silently ignored.

### 4.2 Exact V1 predicate vocabulary

The following field names are the V1 public configuration contract. The
implementation must not substitute hidden prefix syntax such as `regex:...`.
Unless a row says otherwise, a list means OR across configured values and the
field participates in AND with other fields in the same block.

| Config field | Type | Source | V1 semantics |
| --- | --- | --- | --- |
| `subject_exact` | list[string] | discovery | case-insensitive whole subject equality |
| `subject_contains` | list[string] | discovery | case-insensitive substring search |
| `subject_regex` | list[regex] | discovery | `msgloom-regex-v1` search |
| `body_contains` | list[string] | composite probe | case-insensitive substring search over complete text body |
| `body_regex` | list[regex] | composite probe | regex search over complete text body |
| `body_or_subject_contains` | list[string] | subject then optional probe | each value matches if present in either subject or complete body |
| `body_or_subject_regex` | list[regex] | subject then optional probe | each regex matches if it searches successfully in either subject or complete body |
| `from_addresses` | list[string] | discovery | exact address membership |
| `from_address_contains` | list[string] | discovery | substring search over From address text |
| `from_address_regex` | list[regex] | discovery | regex search over From address text |
| `sender_addresses` | list[string] | discovery | exact Sender address membership; distinct from From |
| `sender_address_contains` | list[string] | discovery | substring search over Sender address text |
| `sender_address_regex` | list[regex] | discovery | regex search over Sender address text |
| `to_addresses` | list[string] | discovery | any To address equals any configured value |
| `to_address_contains` | list[string] | discovery | any To address contains any configured value |
| `to_address_regex` | list[regex] | discovery | any To address matches any regex |
| `cc_addresses` | list[string] | discovery | any Cc address equals any configured value |
| `cc_address_contains` | list[string] | discovery | any Cc address contains any configured value |
| `cc_address_regex` | list[regex] | discovery | any Cc address matches any regex |
| `bcc_addresses` | list[string] | discovery | any Bcc address equals any configured value |
| `bcc_address_contains` | list[string] | discovery | any Bcc address contains any configured value |
| `bcc_address_regex` | list[regex] | discovery | any Bcc address matches any regex |
| `recipient_address_contains` | list[string] | discovery | Outlook-style aggregate over To + Cc only; Bcc stays separate |
| `recipient_address_regex` | list[regex] | discovery | regex equivalent over To + Cc only |
| `reply_to_addresses` | list[string] | discovery | any Reply-To address equals any configured value |
| `reply_to_address_contains` | list[string] | discovery | substring search over Reply-To addresses |
| `reply_to_address_regex` | list[regex] | discovery | regex search over Reply-To addresses |
| `categories` | list[string] | discovery | any message category equals any configured value, case-insensitive |
| `importance` | list[`low`,`normal`,`high`] | discovery | provider importance membership |
| `has_attachments` | boolean | discovery | exact provider boolean; provider inline-only caveats remain documented |
| `header_contains` | list[string] | composite probe | search any canonical `name: value` internet-header line |
| `header_regex` | list[regex] | composite probe | regex search any canonical `name: value` internet-header line |
| `sensitivity` | list[`normal`,`personal`,`private`,`confidential`] | composite probe | canonical Outlook/MAPI sensitivity value |
| `message_size_min_kb` | integer >= 0 | composite probe | inclusive lower bound; 1 KiB = 1024 bytes for msgloom V1 |
| `message_size_max_kb` | integer >= 0 | composite probe | inclusive upper bound; must be >= configured minimum |
| `received_after` | timezone-aware ISO-8601 datetime | discovery | inclusive lower bound on received time |
| `received_before` | timezone-aware ISO-8601 datetime | discovery | exclusive upper bound on received time |
| `sent_after` | timezone-aware ISO-8601 datetime | discovery | inclusive lower bound on sent time |
| `sent_before` | timezone-aware ISO-8601 datetime | discovery | exclusive upper bound on sent time |
| `created_after` | timezone-aware ISO-8601 datetime | discovery | inclusive lower bound on created time |
| `created_before` | timezone-aware ISO-8601 datetime | discovery | exclusive upper bound on created time |
| `is_read` | boolean | discovery | exact current read state |
| `is_draft` | boolean | discovery | exact current draft state |
| `inference_classification` | list[`focused`,`other`] | discovery | provider inference classification membership |
| `followup_status` | list[`not_flagged`,`flagged`,`complete`] | discovery | provider follow-up flag status; distinct from message action flag |
| `message_action_flags` | list[`any`,`call`,`do_not_forward`,`follow_up`,`fyi`,`forward`,`no_response_necessary`,`read`,`reply`,`reply_to_all`,`review`] | composite probe | user values map to the canonical Outlook message-action flag enum |
| `item_class_exact` | list[string] | composite probe | case-insensitive exact canonical Outlook/MAPI message class |
| `item_class_contains` | list[string] | composite probe | case-insensitive substring search over message class |
| `item_class_regex` | list[regex] | composite probe | regex search over message class |
| `is_meeting_request` | boolean | type/class fact | exact special-message classification |
| `is_meeting_response` | boolean | type/class fact | exact special-message classification |
| `is_non_delivery_report` | boolean | message class | exact report-message classification |
| `is_read_receipt` | boolean | message class | exact report-message classification |

Range lower/upper fields are ordinary fields in the block and therefore combine
with AND. Config validation rejects an inverted range.

`body_or_subject_*` preserves value-level OR semantics across the two source
fields: one configured term/pattern is true when either subject or body proves
it. A subject match short-circuits the body requirement.

Body predicates evaluate the complete Graph body requested with
`Prefer: outlook.body-content-type="text"`; they do not match raw HTML or raw
MIME bytes.

Header matching canonicalizes a provider header only as the documented textual
view `name: value`; it does not expose a raw MIME parser as rule semantics.

Display names are deliberately not mixed into V1 address predicates. Address
rules operate on address strings only. A future display-name predicate can be
added explicitly without changing existing address behavior.

The supported special-message booleans must be derived from exact documented
provider type/message-class facts. They must not use subject/header wording
heuristics.

### 4.3 Deferred predicates

These Outlook-style predicates are deferred because V1 does not yet have a
reliable local source fact or would require a broader identity/permissions
contract:

- sent-to-me;
- sent-cc-me;
- sent-only-to-me;
- sent-to-or-cc-me;
- not-sent-to-me;
- approval request;
- automatic forward;
- automatic reply;
- encrypted;
- signed;
- permission controlled;
- voicemail;
- Exchange message classifications;
- from connected accounts.

The `*to-me` family needs a trustworthy target mailbox SMTP identity and alias
set. `MSGLOOM_TARGET_MAILBOX` may be an immutable object ID and is not a safe
substitute. V1 must not silently add directory/profile permissions merely to
make these predicates work.

The security/report predicates above may be inferable from MIME or headers in
some cases, but V1 does not claim Outlook-equivalent semantics from heuristics.

## 5. Deterministic RuleEngine

### 5.1 Pure engine boundary

The deterministic engine is independent of Scrapy:

```text
MailRuleset
  + MailRuleObservation
  + optional MailRuleProbeData
        |
        v
DeterministicMailRuleEvaluator
        |
        v
MailRuleEvaluation
```

The engine must not import or depend on:

- Scrapy Request/Response;
- Downloader or Scheduler state;
- SQLAlchemy/catalog access;
- logging;
- provider URLs;
- CLI objects.

### 5.2 Internal predicate truth model

Individual predicates use a three-state internal result:

```text
TRUE
FALSE
UNKNOWN_NEEDS_DATA
```

The public evaluator state remains:

```text
FINAL
NEEDS_DATA
UNRESOLVED
```

`UNKNOWN_NEEDS_DATA` is not the same as false. It means the engine cannot yet
prove true or false from the currently supplied source facts.

### 5.3 Cheap-first short-circuiting

Evaluation must avoid probes that cannot change the result.

Example:

```text
sender mismatch AND body predicate unknown
=> rule condition is FALSE
=> no body probe
```

Example:

```text
sender match AND body predicate unknown
=> rule may still match
=> body becomes required data
```

For body-or-subject predicates:

```text
subject already matches
=> TRUE
=> no body probe
```

A negative body preview never proves that the complete body does not contain a
term/pattern.

### 5.4 Exception short-circuiting

Conditions are evaluated before exceptions.

- if conditions are definitely false, exceptions are not evaluated;
- if conditions are true, exceptions are evaluated;
- if any exception block is definitely true, the rule is excluded and later
  exception blocks need not be evaluated;
- if an exception fact is required to determine whether an otherwise matching
  rule is excluded, that fact may contribute to the composite probe request.

### 5.5 Required-data union

The first evaluation pass must compute the union of all still-relevant missing
facts across the rules that can still influence the terminal result.

This avoids a multi-probe sequence such as:

```text
probe body
reevaluate
probe headers
```

Instead:

```text
still-relevant required facts = {BODY, HEADERS}
=> one composite probe
```

Facts for rules already proven false or rules that cannot execute after an
already-determined stop-processing match must not be requested merely because
the wider ruleset mentions them.

### 5.6 At most one composite provider probe per observation

The existing body-only probe evolves into one dynamic composite Mail detail
probe. The request selects/expands only the facts needed by the current
observation/ruleset, using the existing authenticated Microsoft Graph request
path, raw-evidence handling, retry policy, and named Spider callback/errback.

Candidate required-data vocabulary includes:

```text
BODY
HEADERS
EXTENDED_MESSAGE_PROPERTIES
MESSAGE_TYPE
```

The final exact enum may split extended properties into narrower fact groups if
that improves validation/testing without creating extra provider requests.

One observation may schedule at most one rule probe. A second `NEEDS_DATA`
after probe delivery is a programming/integrity failure.

Real Microsoft Graph tests must verify that the chosen `$select` / `$expand`
shape can retrieve the required supported facts in one request. Current Graph
v1.0 documentation explicitly documents expanding a *specific*
`singleValueLegacyExtendedProperty`; it does not by itself prove that one
filtered expansion can return every extended property needed by this ruleset.
This is therefore a qualification gate, not an assumed provider capability.

If the real Graph service cannot return the required V1 fact combination in one
message GET, implementation must stop and revise the supported predicate set or
probe design before claiming this phase complete. It must not silently add a
second rule probe, parse heuristics as equivalent facts, or weaken the
one-probe acceptance criterion without a reviewed design change.

### 5.7 Partial composite results

A successful HTTP probe is not treated as an all-or-nothing data blob.

The probe result records which bounded facts are available and which requested
facts are unavailable/invalid, with safe reason codes.

Example:

```text
BODY available
HEADERS available
requested extended flag property absent
```

After the probe, the full ruleset is reevaluated. If the missing fact cannot
change the final decision, evaluation may still be `FINAL`. Only a terminal
decision that genuinely depends on unavailable required data becomes
`UNRESOLVED`.

### 5.8 Source mutation fence

The initial observation and probe must represent the same provider version.

The evaluator compares the initial `lastModifiedDateTime` with the probed
version when a probe is used. If the versions differ, msgloom must not combine
old cheap facts with new detail facts.

Required result:

```text
UNRESOLVED
selected_profile = full
fallback_used = true
reason_code = source_changed_during_evaluation
```

### 5.9 Regex failure behavior

Regex syntax/unsupported language features are rejected at configuration load.

Google RE2 avoids ordinary catastrophic backtracking, so runtime regex timeout
is not expected as a normal path. Nevertheless, a bounded engine/resource
failure while evaluating one message follows the previously approved fail-safe
policy:

```text
that message -> UNRESOLVED -> full
crawl continues
```

It emits a safe WARNING/stat without pattern contents.

Unexpected Python/programming exceptions are different. They mark the logical
run failed through the existing Spider integrity mechanism rather than being
misclassified as a recoverable source-data condition.

## 6. Runtime profile accumulation and planner handoff

### 6.1 Attempt-local state

Rule decisions remain attempt-local control state. They are not written to the
Mail catalog and logs are never parsed back into control flow.

The Spider may expose a bounded runtime handoff such as a set/ordered tuple of
message IDs requiring Full-v1. The exact internal representation is private.

### 6.2 Duplicate observations

The middleware-only phase temporarily allowed last-observation-wins profile
state. Planner integration replaces that rule.

For the same message ID within one attempt, runtime acquisition depth uses the
same monotonic strongest-profile rule as rule evaluation:

```text
Full + later discovery => Full
```

This removes callback completion ordering as a planner correctness dependency.
Every individual observation can still produce its own audit log event.

## 7. Mail sync and checkpoint correctness

### 7.1 Existing planner conflict

Today, `pending_full_v1_message_ids()` treats every current message missing any
Full-v1 surface as a Full backlog candidate.

That definition is invalid when rules are active: a message intentionally kept
at discovery naturally lacks detail/MIME/attachment Full surfaces.

Therefore, while Mail rules are enabled, the existing global incomplete-Full
backlog must not run as an implicit rule bypass.

### 7.2 Full obligation loss if the delta checkpoint commits too early

Current Mail sync commits the message-delta checkpoint when the delta crawler
reaches a complete clean idle, before later Full crawlers run.

With rules enabled, this sequence is unsafe:

```text
delta observes M
rule selects Full for M
delta checkpoint commits
Full crawler for M fails
next delta starts after M's change
```

Because per-message rule decisions are intentionally not persisted, M's Full
obligation can be lost.

### 7.3 Rules-enabled sync defers message-delta promotion

The approved model is:

```text
folder delta
  -> message delta
  -> validate complete delta run
  -> retain candidate message-delta links; do not promote yet
  -> read attempt-local rule-selected Full targets
  -> run required Full crawlers
  -> all Full phases succeed
  -> promote lifecycle + message-delta checkpoints
```

If any required Full crawler fails:

- final message-delta promotion does not happen;
- prior committed cursors remain authoritative;
- staged candidates remain non-authoritative pending data;
- next sync replays the change and reevaluates policy.

This preserves the no-rule-decision-persistence decision while giving Full
selection durable retry semantics through the existing checkpoint boundary.

### 7.4 Rules-disabled compatibility

When Mail rules are disabled, current behavior remains unchanged:

```text
delta
-> immediate validated checkpoint promotion
-> current changed-message Full behavior
-> current global incomplete Full backlog
```

No-rules behavior is a hard backward-compatibility requirement.

### 7.5 Checkpoint validation versus promotion

The existing delta checkpoint extension currently validates completion and
promotes lifecycle/checkpoints in one idle handler. This phase should refactor
that logic so validation is reusable and promotion timing can differ without
duplicating integrity rules.

Conceptually:

```text
validate_delta_completion(...) -> ValidatedDeltaRun
```

Then:

- direct/legacy delta execution validates and promotes immediately;
- rules-enabled sync validates and holds candidates;
- the workflow promotes only after all planned Full phases succeed.

The exact API may differ, but validation rules must remain single-sourced.

### 7.6 Workflow finalizer

The existing sequential `run_graph_workflow()` gains an optional
`on_success` finalizer with the logical contract:

```text
on_success(completed_crawlers)
```

It runs exactly once only when all initial and dynamically-added phases complete
successfully. `completed_crawlers` is the final ordered tuple of crawlers from
the workflow. Rules-enabled Mail sync uses the callback (normally through a
closure over its validated delta run) to promote the held message-delta state.

If the finalizer raises, the command fails, the held message-delta checkpoint is
not considered successfully promoted, and a bounded ERROR diagnostic records
only the finalizer/error class context. The workflow must not manufacture a fake
Scrapy Spider merely to perform the commit.

### 7.7 Public primitive behavior while policy is active

`outlook mail sync` is the policy-completing user workflow when Mail rules are
active. A standalone delta crawl cannot safely select Full targets, advance the
provider cursor, and then discard the attempt-local targets.

Required public-command behavior:

- `scrapy microsoft outlook mail sync` evaluates rules, executes required Full
  work, and owns deferred checkpoint promotion;
- `scrapy microsoft outlook mail discover` may evaluate/log rule decisions for
  observed messages, but it does not claim to execute selected Full work and it
  advances no message-delta checkpoint;
- `scrapy microsoft outlook mail delta` with an active Mail policy is rejected
  before crawl startup with a safe message directing the user to `mail sync`;
- `scrapy microsoft outlook mail full ...` remains an explicit operator
  override independent of rule selection.

A low-level developer `scrapy crawl outlook_delta` under an active policy must
also fail closed with respect to checkpoint promotion when no workflow-owned
deferred-commit context exists. It may collect/stage data for development, but
it must never advance the authoritative message-delta cursor while discarding
rule-required Full obligations.

### 7.8 `--max-enrich` under active rules

The existing `--max-enrich` option limits legacy backlog enrichment. It must not
truncate rule-required Full targets: without a durable obligation queue, doing
so would lose required work if the delta checkpoint were promoted.

Therefore, while Mail rules are active:

- omitted/default `--max-enrich` is fine;
- an explicitly supplied `--max-enrich` is rejected as incompatible with the
  rules-enabled sync policy in V1.

A future bounded batching feature would require its own durable obligation or
checkpoint model. V1 does not overload the old backlog limit with different
semantics.

## 8. Ruleset identity and JOBDIR safety

### 8.1 No user-managed ruleset ID

Users do not configure a ruleset identifier.

The internal family identifier is fixed as:

```text
outlook-mail-acquisition-rules-v1
```

The effective semantic ruleset is distinguished by a SHA-256 digest.

### 8.2 Semantic digest

The digest is computed from a canonical effective model, not raw TOML bytes.

Pipeline:

```text
TOML
-> strict validated model
-> defaults applied
-> enabled semantic policy extracted
-> canonical JSON
-> SHA-256 lowercase hex
```

Whitespace, comments, TOML key ordering, rule array order when `sequence` is
unchanged, OR-value ordering, and exception-block ordering do not change the
digest. Canonicalization sorts rules by `sequence`, sorts semantically
order-independent ordinary value sets, and canonicalizes/sorts exception blocks
by their canonical content. Regex pattern text is preserved exactly; only the
order of OR-alternative regex entries is canonicalized.

The canonical material includes relevant semantic contract versions, including:

- Mail rule schema/engine contract version;
- `msgloom-regex-v1`;
- profile lattice version;
- enabled/default profile state;
- enabled rule IDs, sequence, predicates, exceptions, profile, and
  stop-processing behavior.

Compiled RE2 objects and dependency package versions are not serialized into
the digest.

### 8.3 Disabled-policy digest

When the Mail policy is globally disabled, inactive rule contents do not change
the effective policy digest. The effective semantic payload is equivalent to:

```json
{"contract":"outlook-mail-acquisition-rules-v1","enabled":false}
```

When policy is enabled, disabled individual rules also do not affect the
effective digest, though they are still validated.

### 8.4 JOBDIR binding

Mail collection JOBDIR must bind the effective Mail policy digest even when the
policy is disabled.

Conceptually:

```text
JOBDIR/
  .msgloom-source-context-v1
  .msgloom-mail-policy-context-v1
```

Only safe digests/contract metadata are stored; no configured values or rule
content are written into the marker.

Required behavior:

| Saved policy | Current policy | Resume |
| --- | --- | --- |
| disabled | disabled | allowed |
| disabled | enabled | refused |
| rules A | rules A | allowed |
| rules A | rules B | refused |

The guard must run before queued requests can execute under a different policy.
It may obtain the digest from the already-created Mail collection Spider/runtime
context rather than from raw Scrapy settings.

## 9. Validation, bounds, and privacy-safe diagnostics

### 9.1 Closed configuration vocabulary

Models reject unknown fields. Unsupported predicate names and deferred Outlook
predicate names fail configuration validation; they are not silently ignored.

Rule IDs and other loggable identifiers use the existing middleware
safe-token contract exactly: 1-96 characters matching `[A-Za-z0-9_.:-]`.

### 9.2 Bounds

V1 uses these exact finite acceptance bounds:

| Structure | Bound |
| --- | ---: |
| universal config bytes | 256 KiB |
| rules | 256 |
| exception blocks per rule | 32 |
| values per predicate | 128 |
| regex pattern length | 4096 characters |
| rule ID | 96 characters |

Changing these bounds requires an explicit design/spec change; the
implementation plan must not silently tighten, relax, or remove them.

### 9.3 Privacy-safe error detail

User-facing configuration errors must be more actionable than a single generic
`invalid_input` message while still protecting configured values.

Allowed detail:

- config path chosen by the user/system;
- TOML line/column when available;
- safe field path;
- safe field/predicate name;
- stable reason category;
- suggestions for known field-name typos.

Not allowed:

- email addresses;
- subject/body/category configured values;
- regex pattern text;
- arbitrary provider payload;
- arbitrary exception text that may embed private configuration.

Examples:

```text
acquisition.microsoft.outlook.mail.rules[2].profile:
unsupported acquisition profile
```

```text
acquisition.microsoft.outlook.mail.rules[4].conditions.subject_regex[0]:
pattern is not valid msgloom-regex-v1 syntax
```

An error must not echo the offending regex.

## 10. Logging and observability

The completed middleware log-level policy remains authoritative:

| Event | Level |
| --- | --- |
| final rule decision | INFO |
| probe scheduled/completed | DEBUG |
| expected unresolved/fallback | WARNING |
| programming/integrity failure | ERROR |
| aggregate crawl rule summary | INFO |

The rule implementation must not add a private log file/handler.

Rule logs may include bounded IDs/digests/profile/outcome/stop-rule/probe/fallback
flags, but never configured match values or Mail content.

Raw rules must not be inserted into Scrapy settings because Scrapy itself logs
overridden settings.

Aggregate stats remain identifier-free.

## 11. Ruleset changes and V1 historical scope

V1 rules apply to Mail observations evaluated after the ruleset becomes active.
Changing a ruleset does not by itself cause every unchanged historical message
to be enumerated and reevaluated.

Example:

```text
January: message M observed under discovery-only policy
March: policy changes so M would now be Full
M never changes and is never observed again
```

V1 does not guarantee a March retroactive Full acquisition for M.

If M is observed again through a normal discovery/delta/reconciliation recovery
path, the new ruleset applies.

A future policy-reconciliation workflow may detect ruleset changes and perform a
bounded mailbox reevaluation sweep. That feature requires its own design for
enumeration, provider probes, checkpointing, resume, and cost limits. This phase
must not approximate it by clearing cursors or persisting per-message decisions.

## 12. User documentation requirements

The user guide is a product requirement, not optional polish. Its fixed path is:

```text
docs/outlook-mail-rules.md
```

It must be written for a non-technical user first, with technical/reference
sections clearly separated.

The guide must explain:

- where `msgloom.toml` lives;
- what happens when the default file is absent;
- how `--config` selects another complete file;
- how to enable/disable Mail rules;
- default profile behavior;
- rule IDs and sequence;
- conditions field-AND / value-OR semantics;
- exception block semantics;
- monotonic strongest-profile selection;
- stop-processing;
- default case-insensitive matching;
- exact/contains/regex choices;
- `msgloom-regex-v1` and major RE2 unsupported constructs;
- one-probe/fail-safe behavior in user-friendly terms;
- unsupported/deferred predicates;
- config validation troubleshooting;
- the V1 non-retroactive ruleset-change boundary;
- explicit `outlook mail full` as an operator override;
- why active rules require `outlook mail sync` rather than standalone `mail delta`;
- why `--max-enrich` is rejected while rule-required Full work is active.

### 12.1 Required example catalogue

The guide must contain examples covering at least:

1. enabling rules with the default discovery profile;
2. making every Mail Full;
3. exact sender address;
4. multiple sender addresses (OR);
5. sender domain regex;
6. subject contains;
7. subject regex;
8. body contains;
9. body regex;
10. body-or-subject;
11. multiple fields in one conditions block (AND);
12. multiple values inside one predicate (OR);
13. one exception block;
14. multiple exception blocks;
15. category exclusion;
16. attachment condition;
17. importance;
18. To condition;
19. Cc condition;
20. Bcc condition;
21. recipient aggregate condition;
22. header condition;
23. sensitivity;
24. size range;
25. received/sent date range;
26. read/draft condition;
27. focused/other inference classification;
28. follow-up flag;
29. message-class/special-message predicate;
30. multiple ordered rules;
31. stop-processing;
32. monotonic Full upgrade;
33. an attempted later discovery downgrade that does not reduce Full;
34. disabled individual rule;
35. enabled policy with no rules;
36. globally disabled policy;
37. invalid profile;
38. duplicate sequence;
39. invalid/unsupported RE2 syntax;
40. case-insensitive behavior;
41. using anchors for full-field regex intent;
42. body preview positive versus negative limitations;
43. successful composite probe;
44. probe source change -> Full fail-safe;
45. provider fact unavailable -> Full fail-safe when decision depends on it;
46. regex runtime/resource failure -> Full fail-safe;
47. programming failure distinction;
48. rules-enabled Full failure causing delta checkpoint to remain unpromoted;
49. policy change not retroactively scanning unchanged history;
50. explicit operator Full override;
51. discovery command evaluates decisions but does not execute selected Full work;
52. standalone delta rejected while policy is active;
53. `--max-enrich` rejected while policy is active.

Examples should use fictional addresses/domains and should not mirror real user
content from logs/tests.

## 13. Testing requirements

### 13.1 Pure RuleEngine tests

Cover deterministic truth tables for:

- every supported predicate family;
- case-insensitive exact/contains semantics;
- RE2 search/anchor/inline option behavior;
- unsupported RE2 syntax validation;
- conditions AND and values OR;
- exception block AND and block OR;
- ordered rule processing;
- unique sequence validation;
- monotonic profile selection;
- stop-processing;
- cheap-first false short-circuit;
- body-or-subject positive short-circuit;
- required-data union;
- partial composite probe facts;
- source mutation fence;
- provider-fact unavailable -> unresolved only when relevant;
- bounded regex engine failure -> unresolved Full fallback;
- deterministic canonical digest independent of TOML formatting/key order;
- digest changes for effective semantic changes;
- digest stability for comments/whitespace/disabled-policy draft edits.

### 13.2 Configuration tests

Cover:

- XDG default resolution;
- `~/.config` fallback;
- invalid relative `XDG_CONFIG_HOME` handling;
- absent default file;
- explicit missing `--config` error;
- invalid TOML;
- unknown fields;
- bounds;
- privacy-safe validation messages;
- enabled/disabled/empty rules semantics;
- profile vocabulary mapping;
- operation-specific validation without requiring unrelated A2/A3/A5 config.

### 13.3 Scrapy integration tests

Use actual Scrapy 2.19 component paths where lifecycle/order matters.

Cover:

- no-rules middleware remains silently disabled;
- original Mail Item passes unchanged;
- one composite probe maximum;
- named callbacks remain JOBDIR serializable;
- middleware consumes internal probe result before pipelines;
- actual Spider Middleware ordering;
- evaluator/programming error marks logical run failed;
- safe log text and structured extras;
- no raw rules appear in Scrapy overridden-settings logs;
- JOBDIR ruleset marker creation and same-policy resume;
- policy mismatch rejects resume before queued work runs.

### 13.4 Planner/checkpoint tests

Cover:

- rules disabled preserves current sync planner behavior exactly;
- rules enabled plans Full only from attempt-local selected targets;
- discovery-only messages do not re-enter Full via legacy global backlog;
- duplicate observations use strongest profile;
- successful rules-enabled sync promotes staged delta checkpoint once;
- failed Full phase does not promote staged delta checkpoint;
- next run can replay from prior committed delta cursor;
- explicit Full command remains independent of rules;
- public standalone Mail delta is rejected when policy is active;
- low-level direct delta cannot promote a policy-selected cursor outside a policy-completing workflow;
- explicit `--max-enrich` is rejected while policy is active;
- checkpoint validation logic remains single-sourced.

### 13.5 Real Microsoft Graph evidence

At least one development/qualification test against the real Microsoft Graph
service must prove the composite probe request shape for the supported V1 facts,
particularly `$select` plus any required extended-property `$expand` behavior.

Provider-specific message types/extended properties used to classify special
messages must be validated against documented source facts, not fixture-only
assumptions.

## 14. Implementation boundaries

The implementation should remain decomposed into focused units, for example:

- universal config resolver/read boundary;
- Mail rule config models/validation;
- regex engine adapter;
- predicate evaluation helpers;
- deterministic ruleset evaluator;
- ruleset canonicalization/digest;
- composite probe fact model and Spider request/parser seam;
- JOBDIR policy-context guard;
- attempt-local planner handoff;
- reusable delta validation/promotion service;
- workflow success finalizer;
- user/reference documentation.

The exact file split is deferred to the implementation plan after repository
reinspection. No unit should require reading Scrapy internals to understand pure
rule semantics.

## 15. Rejected alternatives

## Separate Mail-only config file

Rejected because msgloom should have one universal user configuration surface,
not one file per feature.

## Eagerly require every universal section

Rejected because using Mail acquisition rules must not require configuring
triage/report/other unrelated subsystems.

## Load `msgloom.toml` from `message_ingest.settings`

Rejected because project settings load before custom command selection, would
make unrelated Scrapy commands parse Mail policy, complicates `--config`, and
turns user policy into module-import side effects.

## Put raw rules into Scrapy settings

Rejected for privacy, deepcopy/pickle, lifecycle, and ownership reasons.

## Create a Scrapy add-on only to load user rules

Rejected because Mail user policy is not framework component configuration.

## Multiple environment/CLI overrides for individual rule fields

Rejected because the user must be able to understand persistent policy from one
file. `--config` selects another complete file; it does not build a hidden
precedence maze for rule semantics.

## Python standard-library `re`

Rejected for user-supplied rules because it lacks a safe per-match timeout and
does not provide RE2's predictable execution model.

## Broad `regex` package as public dialect

Rejected as the V1 default because long-term maintenance is strongly centered
on one maintainer and its broad syntax would make the dependency's behavior the
user contract.

## Automatic fallback from RE2 to another engine

Rejected because two regex dialect/runtime paths increase semantic and
maintenance risk.

## Arbitrary nested boolean expressions in V1

Rejected to keep configuration understandable, deterministic, and bounded for
non-technical users.

## Persist per-message rule decisions

Rejected because they are policy/control state, not provider content, and would
create migration/staleness obligations when rules change.

## Use logs as planner state

Rejected because observability is not a correctness/control channel.

## Continue global incomplete-Full backlog when rules are active

Rejected because intentional discovery-only messages would be upgraded to Full
outside the rule policy.

## Commit delta cursor before rule-selected Full work completes

Rejected because a later Full failure can permanently lose the obligation after
the provider delta cursor advances.

## Clear delta cursors whenever rules change

Rejected because it is an implicit expensive historical reconciliation with
poor resume/cost semantics. A future policy-reconciliation workflow should be
explicitly designed instead.

## 16. Acceptance criteria

The phase is complete only when all of the following hold:

1. one XDG-based universal config resolver exists and absent default config is
   valid;
2. explicit `--config` selects one complete config and missing/invalid explicit
   files fail;
3. Mail policy is opt-in with `enabled = true`;
4. zero-config / rules-disabled acquisition behavior remains unchanged;
5. user profile vocabulary is `discovery` / `full` while internal contracts
   remain versioned;
6. conditions/exceptions implement the documented AND/OR model without nested
   boolean syntax;
7. regex uses the `msgloom-regex-v1` contract backed by Google RE2 and is
   case-insensitive by default without rewriting user patterns;
8. every V1 supported predicate has a documented reliable source fact;
9. deferred predicates fail validation rather than use heuristics;
10. the pure RuleEngine is deterministic and independent of Scrapy;
11. cheap-first evaluation avoids unnecessary probes;
12. one observation schedules at most one composite rule probe;
13. probe facts are partial/typed and missing irrelevant facts do not force a
    fallback;
14. source-version mismatch during probe becomes `UNRESOLVED` with Full fallback;
15. bounded provider/regex evaluation uncertainty becomes per-message
    `UNRESOLVED` + Full fallback;
16. unexpected programming/integrity failures mark the logical run failed;
17. profile selection is ordered and monotonic with explicit stop-processing;
18. duplicate observations accumulate the strongest required acquisition
    profile;
19. no per-message rule decision is written to the Mail catalog;
20. rules-enabled sync does not use the legacy global incomplete-Full backlog;
21. rules-enabled sync delays message-delta promotion until all required Full
    phases succeed;
22. a failed required Full phase leaves the prior committed delta cursor
    authoritative;
23. rules-disabled sync retains the current checkpoint/backlog behavior;
24. standalone user-level Mail delta is refused while policy is active, and low-level direct delta cannot unsafely promote the cursor;
25. `--max-enrich` cannot truncate rule-required Full obligations;
26. Mail JOBDIR binds effective policy semantics and refuses mismatched resume;
27. raw rule values never enter Scrapy settings or logs;
28. validation diagnostics identify safe field locations/reasons without
    echoing configured values;
29. the ordinary user guide includes the required example catalogue and clearly
    documents V1 historical/non-retroactive behavior;
30. focused, regression, lint, type-check, native Scrapy lifecycle, JOBDIR, and
    real-Graph qualification tests pass on the project's supported runtime.

## 17. Evidence base

This design was reviewed against the repository's active Scrapy 2.19.0 runtime
and the current feature worktree, including:

- `scrapy.cfg`;
- `message_ingest/settings.py`;
- `message_ingest/commands/microsoft/__init__.py`;
- `message_ingest/commands/_common.py`;
- `message_ingest/spiders/microsoft/outlook/email/_base.py`;
- `message_ingest/spiders/microsoft/outlook/email/delta.py`;
- `message_ingest/spidermiddlewares/microsoft/outlook/email.py`;
- `message_ingest/acquisition/microsoft/outlook/email/rule_evaluation.py`;
- `message_ingest/acquisition/microsoft/outlook/email/planner.py`;
- `message_ingest/acquisition/microsoft/outlook/email/profile.py`;
- `message_ingest/commands/microsoft/outlook/sync.py`;
- `message_ingest/extensions/microsoft/outlook/email/checkpoint.py`;
- `message_ingest/sync/microsoft/outlook/email/checkpoints.py`;
- Mail catalog/surface persistence and lifecycle stores;
- existing Phase 1 configuration loader/models/snapshot machinery.

Framework/provider research used the version-matched Scrapy settings/add-ons/
commands/jobs contracts and current Microsoft Graph Outlook Mail/message-rule,
message, extended-property, and MAPI documentation. Implementation must verify
provider request shapes against the real Graph service before claiming support.
