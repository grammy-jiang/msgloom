# Outlook Mail deterministic RuleEngine and user configuration design

## Status

Design approved conversationally on 2026-09-30 / 2026-10-01. This document is
the implementation contract for the next phase after the completed Outlook Mail
acquisition-rule Spider Middleware slice.

Implementation has not started. The existing middleware remains the runtime
adapter; this phase supplies the real deterministic RuleEngine, the first
universal user-configuration slice, and the Mail sync planner/checkpoint handoff.

## Intent

msgloom should let a non-technical user decide which Outlook Mail messages
remain at the discovery acquisition profile and which require the existing
Full-v1 acquisition profile. Rule evaluation itself may need one bounded probe
for content that cannot be decided from discovery metadata; `discovery` means no
Full-v1 traversal, not a guarantee that no rule-probe content was acquired. The
policy must be deterministic, explainable, safe to resume, and simple to
maintain in one user configuration file.

The user should be able to express common Outlook-like rules, exceptions,
ordered processing, regular expressions, and a small set of useful msgloom
extensions without learning Scrapy, Microsoft Graph internals, RE2 APIs, or
msgloom's internal profile version names.

Success means:

- one default user configuration file;
- zero-config behavior remains exactly as it is today;
- rule evaluation never mutates or drops the original provider observation;
- evaluation is deterministic for the same effective policy and source facts;
- expensive provider data is fetched only when cheap facts cannot decide the
  result;
- one observation schedules at most one rule probe;
- rule decisions are not persisted as Mail content/catalog state;
- rules-enabled Mail sync cannot lose a required Full acquisition when later
  Full work does not reach the current-attempt terminal-completeness gate;
- resumable JOBDIR execution cannot mix different policy semantics;
- logs and Scrapy settings never expose configured email addresses, keywords,
  regex patterns, body criteria, or provider payloads;
- user-facing documentation contains high-quality examples covering normal,
  exceptional, and failure cases.

## Scope

This phase includes:

- the first universal `msgloom.toml` resolver needed by Outlook Mail rules;
- Outlook Mail rule configuration models and validation;
- canonical Mail policy-family identity and effective policy digest;
- Google RE2-backed `msgloom-regex-v1` support;
- deterministic RuleEngine implementation behind the already-defined
  `MailRuleEvaluator` boundary;
- expansion of the current body-only rule probe into one dynamic composite
  rule probe;
- Mail policy-identity JOBDIR binding;
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
  policy change;
- automatic migration of old acquisition decisions;
- a rewrite/migration of all existing A2/A3/A5 CLI configuration entrypoints;
- hot reloading configuration during a running command;
- changing Full-v1's provider traversal/profile semantics; this phase may add
  a rules-enabled completion verifier around existing Full-v1 surfaces/evidence
  without changing which surfaces Full-v1 acquires;
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

For any command path that resolves the universal configuration, an invalid
existing file must never be treated as if it were absent. Silent fallback could
make a user believe rules are active when they are not. Commands that are
explicitly outside the V1 policy/config matrix in section 1.5 (for example an
operator-forced `outlook mail full`) do not open the default file merely to
validate unrelated policy.

The universal reader reuses the existing hardened configuration-file contract:
it performs a bounded read of one regular file, does not follow the final
symlink (`O_NOFOLLOW` or the platform-equivalent safe open), and rejects FIFOs,
directories, devices, oversized inputs, permission failures, and other I/O
failures as configuration errors. Only a genuine `FileNotFoundError` for the
**default** path maps to the built-in empty document. An explicit missing path
always fails. The file is decoded once per invocation; operation projections do
not reopen it independently.

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

V1 does not require a user-maintained top-level `schema_version`. The parser's
closed vocabulary and the internal Mail policy/regex/profile contract versions
own compatibility. A future incompatible universal-file grammar may add an
explicit version only through a reviewed config-migration design; ordinary
users do not need to manage a version field for this Mail slice.

Examples:

- Outlook Mail acquisition validates the Mail acquisition section;
- triage validates the sections required by triage;
- report validates report configuration;
- `config validate` validates every present supported section of the selected
  universal document.

This phase only needs enough universal-document infrastructure for the Outlook
Mail slice; it must not redesign the existing A2/A3/A5 domain models. However,
"one universal file" requires immediate coexistence with those models.

The universal document layer therefore owns the closed top-level vocabulary and
projects the same decoded TOML document into operation-specific validators:

```text
one decoded msgloom.toml
        |
        +-- legacy operator projection
        |     code_version/storage/admissions/secrets/source/
        |     preparation/triage/report
        |        -> existing OperatorSettings validation
        |
        +-- acquisition projection
              acquisition.microsoft.outlook.mail
                 -> Mail policy validation
```

Existing `OperatorSettings(extra="forbid")` must never receive the
`acquisition` subtree and then reject it as an unknown field. Conversely, the
Mail validator must not reinterpret legacy operator sections. The universal
document rejects unknown top-level sections once, then each operation validates
only its required known projection.

Operation-specific validation is strict but isolated:

- an Outlook Mail operation validates only the universal top-level shape plus
  `acquisition.microsoft.outlook.mail`; it does **not** construct
  `OperatorSettings`, even if legacy sections such as `[triage]` or `[report]`
  are present or incomplete;
- an existing A2/A3/A5 execution command projects the legacy fields
  (`code_version`, `storage`, `admissions`, `secrets`, `source`, `preparation`,
  `triage`, `report`) and validates them through the existing complete
  `OperatorSettings` contract while ignoring the known `[acquisition]` subtree;
- `msgloom config validate` validates every present supported projection. If any
  legacy operator field is present, its legacy projection must satisfy the
  complete existing `OperatorSettings` root contract, including required
  `code_version`, `storage`, and `admissions`; a half-written legacy operator
  configuration therefore fails `config validate` without blocking an unrelated
  Mail acquisition command;
- `config inspect` first performs the same all-present validation as
  `config validate`; it does not present an invalid unrelated section as though
  the whole universal document were healthy.

Operation-specific identities remain operation-specific. A Mail-only semantic
change updates the private Mail policy digest but does not perturb the existing
legacy operator snapshot/version used by A2/A3/A5; conversely, changing
`[report]` does not invalidate a Mail JOBDIR. `config inspect` may display the
existing legacy redacted snapshot identity plus safe Mail metadata, but not the
private Mail effective-policy digest.

As a transitional CLI boundary, existing non-Scrapy A2/A3/A5 commands may keep
their current explicit config *argument syntax* in this phase, but that argument
names the same universal document and must coexist with `[acquisition]` in that
file. No separate legacy/operator TOML is required or documented. The existing
`config validate`/`config inspect` commands must at least recognize the
acquisition subtree in the universal document; `validate` validates every
present supported section, while `inspect` reports only redacted/safe Mail
metadata such as enabled state, fixed policy-family identifier, and rule count.
The private effective policy digest is deliberately not an inspect surface.

The legacy `MSGLOOM_CONFIG__...` and mounted-setting precedence may remain for
legacy operator projections during this transition. It does **not** apply to
Mail acquisition rule semantics: Mail rules, predicates, profiles, and ordering
come only from the selected universal TOML document. Migrating all legacy CLI
entrypoints to the XDG default resolver is a later configuration-migration slice.

The two configuration-management commands are part of this phase and adopt the
universal resolver immediately:

```text
msgloom config validate
msgloom config validate --config /path/to/msgloom.toml
msgloom config inspect
msgloom config inspect --config /path/to/msgloom.toml
```

With no `--config`, they use the XDG default path/empty-default semantics from
section 1.1. They no longer require the old positional config path. `validate`
checks every present supported projection; `inspect` emits only redacted/safe
metadata. This does not force the execution commands for prepare/triage/report
to change their invocation syntax in this phase.

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

Programmatic handoff to collection spiders uses an explicit private Python
Spider argument such as `_mail_rule_config`, not environment variables, globals,
a singleton registry, or Scrapy settings. `OutlookMailCollectionSpider.__init__`
consumes that named argument itself rather than forwarding it into generic
`Spider.__init__(**kwargs)`, constructs/stores only the private immutable runtime
policy/evaluator state it needs, and never copies the raw config object into:

- `spider.state` / SpiderState;
- Request `meta` or `cb_kwargs`;
- crawler stats;
- log message arguments or `LogRecord.extra`;
- source/provider Items.

The pending composite-probe Request continues to carry only the bounded
serializable `MailRuleObservation` required for callback reconstruction. The
actual ruleset remains process-local and is reconstructed from the same frozen
invocation config on a clean JOBDIR resume.

Direct developer execution such as:

```text
scrapy crawl outlook_delta
```

may resolve the default XDG config itself when no command-owned runtime context
exists. V1 does not add a second `-s MSGLOOM_CONFIG_FILE=...` configuration
route merely for direct crawl override.

For the unified Microsoft command in this phase, `--config` is meaningful only
for Outlook Mail paths that evaluate or must guard against Mail policy:

| Command path | `--config` in V1 |
| --- | --- |
| `microsoft outlook mail discover` | accepted; policy may evaluate observations |
| `microsoft outlook mail delta` | accepted so active policy can be detected and the unsafe standalone primitive rejected |
| `microsoft outlook mail sync` | accepted; policy-completing workflow |
| `microsoft outlook mail full` | rejected as unrelated; explicit Full is an operator override independent of policy |
| `microsoft outlook mail folder-delta` | rejected as unrelated |
| Outlook Calendar / To Do / OneDrive / Contacts / auth / profile | rejected in this phase |

This narrow CLI matrix does not change the universal-file architecture; other
product sections can adopt the same selector when they gain user policy.

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

This means every evaluated message remains discovery-only **as its selected
acquisition profile**: msgloom does not schedule Full-v1 detail/MIME/attachment
traversal for it. This name is not a promise that rule evaluation never fetched
additional content. A body/header/extended-property condition may require the
bounded rule probe, and the existing acquisition evidence contract persists that
probe response as raw HTTP evidence even when the final profile is `discovery`.
Users minimizing content acquisition should prefer cheap sender/recipient/subject/
category/importance predicates where they express the intended policy.

Likewise:

```toml
[acquisition.microsoft.outlook.mail]
enabled = true
default_profile = "full"
```

means every evaluated message is Full. Because profile combination is monotonic,
a later rule cannot downgrade this to discovery.
 Because `full` is already the maximal V1 profile, an evaluator may return
`DEFAULT/full` immediately without evaluating otherwise audit-only rules. Users
who want rule-match audit information should use `default_profile = "discovery"`
and explicit Full rules rather than relying on rules that cannot change a Full
default.

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

Rule IDs are operational audit identifiers and are emitted in ordinary INFO
rule-decision logs when they match. They are therefore explicitly **non-secret**
configuration metadata. The user guide must tell users to choose neutral IDs
such as `finance-01` and never place email addresses, customer/person names,
subject/body keywords, or other private matching content in a rule ID.

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

Ordinary exact/contains comparisons use Python Unicode `str.casefold()` on
both configured literals and source text. V1 performs no Unicode normalization,
accent folding, transliteration, or locale-specific rewriting. This makes the
ordinary literal contract deterministic and more tolerant than ASCII-only
lowercasing without silently changing characters beyond case folding.

Email-address comparisons are deliberately case-insensitive for user-facing
rule behavior, even though obscure protocol edge cases can distinguish local
part case. User-configured address values are stripped of surrounding
whitespace before validation/canonicalization; other free-text literals preserve
the whitespace the user wrote. Empty literal and empty regex values are rejected
because `contains = ""` or an empty regex would accidentally match everything.

Documented textual enum values in the user config, including profiles,
importance, sensitivity, follow-up status, inference classification, and
message-action flag names, are accepted case-insensitively and canonicalized to
the documented lowercase/snake-case form before semantic hashing. Structural
TOML field names remain exact.

### 3.2 `msgloom-regex-v1`

V1 regex is a msgloom language contract implemented by the maintained Google
RE2 Python binding. This phase pins `google-re2==1.1.20251105`, matching the
repository's general exact-pin policy for runtime dependencies. The selected
release publishes CPython 3.12, 3.13, and 3.14 Linux/aarch64 wheels. The public
contract remains `msgloom-regex-v1`, not the dependency package/version, so a
future reviewed engine upgrade does not rewrite user TOML.

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

Examples (TOML literal strings are preferred for regexes because backslashes
do not need double escaping):

```toml
subject_regex = ['invoice\s+#\d+']
from_address_regex = ['@example\.com$']
subject_regex = ['^urgent:']
```

The default case-insensitive engine setting means `^urgent:` also matches
`URGENT:`. Advanced users may use RE2-supported inline options such as an
explicit case-sensitive region when needed.

`msgloom-regex-v1` deliberately excludes constructs RE2 does not support,
including backreferences and look-around. Invalid/unsupported regex is a
configuration-time error, not a per-message runtime surprise.

The RE2 adapter uses explicit bounded options rather than dependency defaults:

```text
case_sensitive = false
log_errors = false
max_mem = 4 MiB per compiled pattern
```

`log_errors = false` is a privacy requirement: RE2 must not print a private
invalid pattern to stderr before msgloom can convert the failure to a safe
configuration error. The whole Mail section may contain at most 64 regex
patterns across enabled and disabled rules and exception blocks. Identical
patterns may share one compiled runtime object; the configured-entry bound still
applies before deduplication. Runtime code never depends on RE2 capture groups.

msgloom does not perform Unicode normalization before regex evaluation. Regex
matches the source text under RE2 semantics plus the configured case setting.
RE2's case-insensitive Unicode behavior is its
own regex-language contract and is not defined as Python `str.casefold()`;
exotic Unicode edge cases can therefore differ between literal predicates and
regex predicates. The user guide must call this out in its advanced regex
section.
The pinned dependency must be qualified on the project's supported Python
3.12/3.13/3.14 environments, including Linux/aarch64 packaging used by the
development/runtime estate. Upgrading the dependency is allowed later only when the
`msgloom-regex-v1` compatibility corpus remains green. That corpus contains both
accepted-pattern/match cases and explicitly rejected syntax (including
look-around and backreferences), so an engine upgrade must not silently widen or
change V1 semantics. A deliberate language expansion requires a regex-contract
review/version decision.

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
`Origin` column is part of the design record: it distinguishes conditions that
map to Outlook/Graph rule concepts from msgloom-specific conveniences so future
work does not accidentally claim provider-equivalent behavior for an extension.
The implementation must not substitute hidden prefix syntax such as
`regex:...`.

Unless a row says otherwise, a list means OR across configured values and the
field participates in AND with other fields in the same block.

| Config field | Type | Origin | Source | V1 semantics |
| --- | --- | --- | --- | --- |
| `subject_contains` | list[string] | Outlook baseline | discovery | case-insensitive substring search |
| `subject_exact` | list[string] | msgloom extension | discovery | case-insensitive whole subject equality |
| `subject_regex` | list[regex] | msgloom extension | discovery | `msgloom-regex-v1` search |
| `body_contains` | list[string] | Outlook baseline | composite probe | literal search over complete logical body text |
| `body_regex` | list[regex] | msgloom extension | composite probe | regex search over complete logical body text |
| `body_or_subject_contains` | list[string] | Outlook baseline | subject + optional composite probe | each value may match either subject or complete logical body text |
| `body_or_subject_regex` | list[regex] | msgloom extension | subject + optional probe | each regex may match either subject or complete logical body text |
| `from_addresses` | list[string] | Outlook baseline | discovery | exact From address membership |
| `from_contains` | list[string] | Outlook baseline (`senderContains`) | discovery | search the From recipient display name or address |
| `from_address_contains` | list[string] | msgloom extension | discovery | search only the From address |
| `from_address_regex` | list[regex] | msgloom extension | discovery | regex search only the From address |
| `sender_addresses` | list[string] | msgloom extension | discovery | exact actual Sender address; distinct from From |
| `sender_contains` | list[string] | msgloom extension | discovery | search actual Sender display name or address |
| `sender_address_contains` | list[string] | msgloom extension | discovery | search only the actual Sender address |
| `sender_address_regex` | list[regex] | msgloom extension | discovery | regex search only the actual Sender address |
| `to_addresses` | list[string] | Outlook baseline (`sentToAddresses`) | discovery | any To address equals any configured value |
| `to_address_contains` | list[string] | msgloom extension | discovery | any To address contains any configured value |
| `to_address_regex` | list[regex] | msgloom extension | discovery | any To address matches any regex |
| `cc_addresses` | list[string] | msgloom extension | discovery | any Cc address equals any configured value |
| `cc_address_contains` | list[string] | msgloom extension | discovery | any Cc address contains any configured value |
| `cc_address_regex` | list[regex] | msgloom extension | discovery | any Cc address matches any regex |
| `bcc_addresses` | list[string] | msgloom extension | discovery | any Bcc address equals any configured value |
| `bcc_address_contains` | list[string] | msgloom extension | discovery | any Bcc address contains any configured value |
| `bcc_address_regex` | list[regex] | msgloom extension | discovery | any Bcc address matches any regex |
| `recipient_contains` | list[string] | Outlook baseline | discovery | search display name or address across To + Cc; Bcc excluded |
| `recipient_address_contains` | list[string] | msgloom extension | discovery | address-only search across To + Cc |
| `recipient_address_regex` | list[regex] | msgloom extension | discovery | address-only regex across To + Cc |
| `reply_to_addresses` | list[string] | msgloom extension | discovery | any Reply-To address equals any configured value |
| `reply_to_address_contains` | list[string] | msgloom extension | discovery | substring search over Reply-To addresses |
| `reply_to_address_regex` | list[regex] | msgloom extension | discovery | regex search over Reply-To addresses |
| `categories` | list[string] | Outlook baseline | discovery | category membership, case-insensitive |
| `importance` | list[`low`,`normal`,`high`] | Outlook baseline | discovery | provider importance membership |
| `has_attachments` | boolean | Outlook baseline | discovery | exact provider boolean; provider inline-only caveat is documented |
| `header_contains` | list[string] | Outlook baseline | composite probe | search any canonical `name: value` internet-header line |
| `header_regex` | list[regex] | msgloom extension | composite probe | regex search any canonical `name: value` internet-header line |
| `sensitivity` | list[`normal`,`personal`,`private`,`confidential`] | Outlook baseline | extended-property probe | canonical Outlook sensitivity value |
| `message_size_min_kb` | integer 0..2,097,151 | Outlook-inspired local contract | extended-property probe | inclusive lower bound; exactly `bytes >= value * 1024` |
| `message_size_max_kb` | integer 0..2,097,151 | Outlook-inspired local contract | extended-property probe | inclusive upper bound; exactly `bytes <= value * 1024`; must be >= minimum |
| `received_after` | timezone-aware ISO-8601 datetime | msgloom extension | discovery | inclusive lower bound on received time |
| `received_before` | timezone-aware ISO-8601 datetime | msgloom extension | discovery | exclusive upper bound on received time |
| `sent_after` | timezone-aware ISO-8601 datetime | msgloom extension | discovery | inclusive lower bound on sent time |
| `sent_before` | timezone-aware ISO-8601 datetime | msgloom extension | discovery | exclusive upper bound on sent time |
| `created_after` | timezone-aware ISO-8601 datetime | msgloom extension | discovery | inclusive lower bound on created time |
| `created_before` | timezone-aware ISO-8601 datetime | msgloom extension | discovery | exclusive upper bound on created time |
| `is_read` | boolean | msgloom extension | discovery | exact current read state |
| `is_draft` | boolean | msgloom extension | discovery | exact current draft state |
| `inference_classification` | list[`focused`,`other`] | msgloom extension | discovery | provider inference classification membership |
| `followup_status` | list[`not_flagged`,`flagged`,`complete`] | msgloom extension | discovery | provider follow-up flag status; not Outlook `messageActionFlag` |
| `item_class_exact` | list[string] | Outlook/EWS-inspired extension | extended-property probe | exact canonical Outlook/MAPI message class |
| `item_class_contains` | list[string] | msgloom extension | extended-property probe | substring search over message class |
| `item_class_regex` | list[regex] | msgloom extension | extended-property probe | regex search over message class |
| `is_meeting_request` | boolean | Outlook baseline | message-class extended-property probe | exact canonical message-class classification |
| `is_meeting_response` | boolean | Outlook baseline | message-class extended-property probe | exact canonical message-class classification |
| `is_non_delivery_report` | boolean | Outlook baseline | message-class extended-property probe | exact report-message classification |
| `is_read_receipt` | boolean | Outlook baseline | message-class extended-property probe | exact report-message classification |

`Outlook baseline` in the table means the predicate concept is exposed by
Microsoft's Inbox-rule model; it does not promise undocumented byte-for-byte
identity with Exchange's internal matcher. msgloom's exact local matching,
normalization, range, and case rules in this specification are authoritative.

The Graph `senderContains` name is misleading for local mapping: Microsoft
defines it against the incoming message `from` property. `from_contains`
therefore searches the From recipient's display name and address. Likewise,
`recipient_contains` follows the Outlook definition over To + Cc recipients and
searches each recipient's display name and address independently. The
address-only predicates remain explicit msgloom extensions.

Range lower/upper fields are ordinary fields in the block and therefore combine
with AND. Config validation rejects an inverted range.

The message-size fields intentionally define a stable msgloom conversion from
the byte-valued provider fact to KiB-style configuration (`value * 1024`).
Microsoft documents Outlook/Graph rule `sizeRange` in kilobytes but does not
make this local conversion/rounding contract sufficiently explicit for msgloom
to claim byte-for-byte server-rule equivalence. The user-facing behavior above
is authoritative. The 2,097,151 KiB ceiling keeps the multiplied value within
the documented 32-bit `PidTagMessageSize` provider fact. If that
property is unavailable for a message, the fact is unavailable rather than
silently treated as zero.

Configured datetimes and provider timestamps are parsed as timezone-aware
instants and normalized to UTC for comparison. Their original textual offsets
do not affect matching or semantic hashing once parsed to the same instant.

`body_or_subject_*` preserves value-level OR semantics across the two source
fields: one configured term/pattern is true when either subject or body proves
it. A subject match short-circuits the body requirement.

Body predicates operate on a deterministic *logical text body*:

- a Graph `body.contentType == "text"` value is used as supplied;
- an HTML body is converted to visible text with a bounded Lexbor/selectolax
  projection: active elements (`script`, `style`, `noscript`, `template`,
  `iframe`, `object`, `embed`) are omitted, `<br>` and block boundaries create
  line boundaries, normal-flow whitespace is collapsed, and `<pre>` content
  preserves preformatted whitespace;
- malformed or unsupported body representations make the BODY fact unavailable.

This HTML path is required because Microsoft Graph v1.0 currently returns
`eventMessage` bodies only as HTML even when ordinary message GETs support the
body-content preference. Rule semantics must not depend on beta-only behavior.
Body rules never match raw HTML markup or raw MIME bytes.
The policy projection must include text inside ordinary HTML tables because
Outlook messages frequently use tables for layout. It must not directly reuse
the preparation helper that intentionally omits table contents for document
block extraction; the rule-body projector is a separate bounded helper with the
contract above.

Graph-representation conversion belongs to the composite-probe adapter: it
turns provider `body` JSON into one bounded logical `BODY` text fact before
calling the pure evaluator. `DeterministicMailRuleEvaluator` does not parse HTML
or import Scrapy/Graph response types. The implementation may use a focused
pure Mail-acquisition helper built on the already-pinned selectolax/Lexbor
library; it must not couple A1 rule evaluation to the A2 preparation pipeline's
stateful parser contracts.

Graph `bodyPreview` is deliberately **not** terminal matching evidence for V1
body predicates. Microsoft defines it as a truncated provider-generated text
preview, while msgloom's HTML body semantics use the deterministic logical-text
projection above; a positive preview match is therefore not guaranteed to be a
match in the same normalized logical body contract, especially for event
messages. `body_contains` and `body_regex` require the complete logical body.
`body_or_subject_*` can avoid the BODY probe only when the subject itself
already proves the predicate. `bodyPreview` may remain in the bounded source
observation for provider diagnostics/compatibility, but the RuleEngine does not
use it to prove body truth in V1.

Header matching canonicalizes a provider header only as the documented textual
view `name: value`; it does not expose a raw MIME parser as rule semantics.

The V1 extended-property facts use documented canonical properties and fixed
Graph legacy-property identifiers:

| Fact | Canonical property | Graph single-value ID |
| --- | --- | --- |
| sensitivity | `PidTagSensitivity` | `Integer 0x0036` |
| message size | `PidTagMessageSize` | `Integer 0x0E08` |
| message class | `PidTagMessageClass` | `String 0x001A` |

The provider-fact parser is strict and deterministic:

- Graph legacy extended-property `value` text for sensitivity must parse as an
  integer exactly in `0..3`, mapped to `normal`, `personal`, `private`, and
  `confidential`; any other/malformed value makes the fact unavailable;
- message size must parse as a non-negative 32-bit integer byte count; missing,
  malformed, negative, or out-of-range data makes the fact unavailable;
- message class must be a non-empty provider string; V1 comparisons are
  case-insensitive as required by the canonical MAPI message-class contract;
- duplicate instances of the same requested extended-property ID with
  conflicting values make that fact unavailable rather than choosing one by
  response order.

The exact single-request `$expand` ability for the needed combination remains a
real-service qualification gate in section 5.
 The supported V1 predicate set must remain within the Mail read permissions
already declared by the existing Mail spiders (`Mail.Read` for the signed-in
mailbox and `Mail.Read.Shared` where the current shared-mailbox path uses it).
This phase does not add `User.Read`, directory/profile, mailbox-settings, or
write scopes merely for rule evaluation. If a supposedly supported predicate
proves to require a broader scope on the real Graph service, it moves to
`deferred` unless that permission expansion receives a separate reviewed design.

The supported special-message booleans use the canonical case-insensitive
`PidTagMessageClass` fact only; V1 does not need a second Graph polymorphic-type
contract:

| Predicate | True message-class contract |
| --- | --- |
| `is_meeting_request` | exactly `IPM.Schedule.Meeting.Request` |
| `is_meeting_response` | exactly one of `IPM.Schedule.Meeting.Resp.Pos`, `IPM.Schedule.Meeting.Resp.Tent`, `IPM.Schedule.Meeting.Resp.Neg` |
| `is_non_delivery_report` | message class begins with `REPORT.` and ends with `.NDR` |
| `is_read_receipt` | message class begins with `REPORT.` and ends with `.IPNRN`, or exactly `IPM.Note.Receipt.SMIME` for a secure read receipt |

These mappings come from documented Exchange/MAPI message-class contracts. V1
does not use subject/header wording heuristics, and it does not classify meeting
cancellations (`IPM.Schedule.Meeting.Canceled`) as requests or responses.

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
- message action flag / `messageActionFlag`;
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

`messageActionFlag` is also deferred after this review. Specific nonzero
`PidLidFlagString` values map to several predefined Outlook strings, but zero or
missing values fall back to `PidLidFlagRequest`, and Outlook's `Any` condition is
not equivalent to a single stable numeric property check. V1 must not expose a
partial mapping as though it were the server Inbox-rule condition.

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

For an enabled policy, every `MailRuleEvaluation` state (`FINAL`, `NEEDS_DATA`,
or `UNRESOLVED`) carries the fixed internal family ID
`outlook-mail-acquisition-rules-v1` and the effective policy digest. Terminal
`matched_rule_ids` are emitted in sequence order and `stop_rule_id`, when set,
is one of those matched IDs. The disabled policy constructs no evaluator, so it
does not manufacture per-message evaluation records merely to carry an identity.

All unresolved/failure `reason_code` values are selected from a closed constant
vocabulary owned by the RuleEngine/adapter (for example
`initial_version_unavailable`, `source_changed_during_evaluation`,
`probe_too_large`, `probe_fact_unavailable`, `regex_evaluation_failed`). Provider
exception text, URLs, configured values, and RE2 error strings are never used as
reason codes.

### 5.2 Source-fact availability and contract extensions

The current middleware contracts collapse several provider states that the real
RuleEngine must distinguish. In particular, an empty recipient/category list is
a known value, while a selected field that is absent or malformed is not proof
of an empty value.

V1 therefore extends the existing contracts explicitly:

```text
MailRuleObservation
  values for bounded discovery facts
  available_facts: frozenset[MailRuleFact]

MailRuleEvaluation
  required_data: frozenset[MailRuleRequiredData]

MailRuleRequiredData
  METADATA
  BODY
  HEADERS
  EXTENDED_PROPERTIES

MailRuleProbeStatus
  COMPLETE
  PARTIAL
  FAILED
```

`MailRuleFact` is a closed internal vocabulary covering the source facts used by
the predicate table. The observation projector decides availability from the raw
Graph object's field presence and expected type, not from Python default values.
Examples:

- `categories: []` present in the Graph object is **known empty**;
- `categories` absent is **unavailable**;
- `toRecipients: []` is **known empty**;
- a missing/malformed `toRecipients` field is **unavailable**;
- `from: null` explicitly returned by Graph is a known nullable value;
- an absent/malformed `from` representation is unavailable;
- `subject: null` explicitly returned is known null; an absent subject is
  unavailable.

A predicate may return `FALSE` only from available facts. If a fact that could
change the rule result is unavailable in the initial observation, it contributes
to `NEEDS_DATA`; `METADATA` tells the single composite probe to re-request the
needed discovery metadata alongside any expensive facts. The request builder may
select only the concrete missing metadata fields even though the evaluator uses
the bounded `METADATA` request category.

`MailRuleProbeData` carries fact-level availability, values for available facts,
and bounded per-fact failure records (`fact`, safe `reason_code`). `PARTIAL`
means the provider request succeeded but one or more requested facts remain
unavailable. `FAILED` means the probe did not provide usable requested facts due
to a bounded transport/protocol/resource failure. Neither status by itself
decides the rule result; the evaluator asks whether an unavailable fact is still
semantically relevant.

The V1 discovery observation/fact projection contains only bounded rule-relevant
facts, not the raw message object:

```text
change_key
last_modified_date_time
subject
from_recipient(name, address)
sender_recipient(name, address)
to_recipients[(name, address), ...]
cc_recipients[(name, address), ...]
bcc_recipients[(name, address), ...]
reply_to_recipients[(name, address), ...]
received_date_time
sent_date_time
created_date_time
importance
categories
has_attachments
is_read
is_draft
inference_classification
followup_status
body_preview        # retained for provider compatibility; not V1 body truth
available_facts
```

Recipient facts use a small frozen/serializable recipient value object so both
Outlook-style name-or-address predicates and msgloom address-only predicates can
share one source projection. The object carries only `name` and `address`; it
must not retain the original Graph recipient dictionary. These observation
values remain JOBDIR-serializable because a pending composite probe stores the
observation in callback arguments.

The observation projection is lossless-within-bounds; it never truncates a
provider value and then treats the truncated representation as complete truth.
V1 bounds are:

| Observation material | Bound |
| --- | ---: |
| subject | 16,384 Unicode code points |
| recipient name | 1,024 Unicode code points |
| recipient address | 1,024 Unicode code points |
| total To + Cc + Bcc + Reply-To recipients retained | 256 |
| categories retained | 128 |
| one category | 1,024 Unicode code points |
| changeKey / timestamp / enum-like scalar | 2,048 Unicode code points |
| bodyPreview retained | 1,024 Unicode code points |

A syntactically valid provider fact that exceeds its bound is represented as
unavailable, not truncated. The projector may stop collecting that fact as soon
as the bound is exceeded and does not retain the oversized values in the
observation. If the fact is irrelevant to the reachable rule result, evaluation
continues normally; if it is relevant, the normal single-probe/unresolved
fail-safe rules apply. The composite probe applies the same metadata bounds.

The logical BODY fact is separately bounded to **8 MiB UTF-8** after text/HTML
projection as well as by the 8 MiB HTTP response cap. A projection that exceeds
that logical-text bound is unavailable; RuleEngine matching never scans a
larger body.

The provider version is special. V1 adds `changeKey` to the Mail discovery/delta
`$select` fields and uses it as the mutation-fence token because Microsoft Graph
defines `changeKey` as the version of the message. `lastModifiedDateTime` remains
a useful source timestamp but is not the primary equality token for rule-probe
version integrity.

If evaluation needs any probe but the initial observation has no trustworthy
`changeKey`, msgloom cannot establish the mutation fence. It returns
`UNRESOLVED -> full` with a safe reason such as `initial_version_unavailable`
instead of probing and combining unversioned initial facts with a later
response.

### 5.3 Internal predicate truth model

Individual predicates use a three-state internal result:

```text
TRUE
FALSE
UNKNOWN
```

The public evaluator state remains:

```text
FINAL
NEEDS_DATA
UNRESOLVED
```

`UNKNOWN` is not the same as false. It means the engine cannot prove true or
false from the currently supplied source facts. The unknown result carries the
bounded fact/reason information needed by the outer evaluator. Before the one
probe opportunity is consumed, a semantically relevant unknown can become
public `NEEDS_DATA`; after probe delivery, a still-relevant unknown becomes
public `UNRESOLVED` rather than asking for a second probe.

Three-valued composition is order-independent and uses these fixed tables.
For OR (multiple values in one predicate, multiple exception blocks, and the
body-or-subject source choice):

| OR inputs | Result |
| --- | --- |
| at least one `TRUE` | `TRUE` |
| no `TRUE`, at least one `UNKNOWN` | `UNKNOWN` |
| all `FALSE` | `FALSE` |

For AND (different fields inside a conditions/exception block):

| AND inputs | Result |
| --- | --- |
| at least one `FALSE` | `FALSE` |
| no `FALSE`, at least one `UNKNOWN` | `UNKNOWN` |
| all `TRUE` | `TRUE` |

This matters for partial regex/fact failures. For example, if one configured
regex encounters a bounded engine failure but another regex in the same OR list
matches, the predicate is `TRUE`, not unresolved. If none matches and at least
one remains unknown, the predicate remains unknown.

A rule is `matched` only when its conditions are `TRUE` and no exception block
is `TRUE`. If conditions are `TRUE` and exceptions contain no `TRUE` but at
least one unresolved block, the rule remains unknown. A rule excluded by a true
exception is not included in `matched_rule_ids`.

At terminal evaluation:

- `outcome=MATCHED` means at least one rule actually matched on the evaluated
  decision path, even if it did not raise the already-selected profile;
- `outcome=DEFAULT` means no rule matched and `default_profile` supplied the
  result;
- `outcome=UNRESOLVED` is reserved for fail-safe Full selection when a
  semantically relevant truth value cannot be resolved after the one-probe
  opportunity or another documented bounded evaluation failure occurs.

### 5.4 Cheap-first short-circuiting

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

`bodyPreview` is not consulted for terminal body truth in V1; if a still-relevant
predicate needs BODY and subject truth does not already resolve a
body-or-subject condition, the complete logical body is required.

### 5.5 Exception short-circuiting

A rule's tri-state truth is the logical expression:

```text
conditions AND NOT(any_exception_block)
```

Evaluation is cheap-first rather than rigidly "conditions then exceptions":

- if conditions are definitely `FALSE`, the rule is `FALSE` and exceptions are
  irrelevant;
- if any exception block is definitely `TRUE`, the rule is `FALSE` even when a
  condition is still `UNKNOWN`; this can avoid an unnecessary body
  or extended-property probe;
- if conditions are `TRUE` and every exception block is definitely `FALSE`, the
  rule is `TRUE`;
- if no decisive false/exclusion exists and conditions and/or exceptions remain
  unknown, the rule remains `UNKNOWN` and the missing facts that can
  still change the result contribute to the one composite probe.

Example:

```text
condition: body contains "approval"   -> UNKNOWN (needs BODY)
exception: category == "ignore"       -> TRUE
rule                                      FALSE, no BODY probe
```

Within multiple exception blocks, the fixed OR truth table applies. Once one
block is `TRUE`, later exception blocks cannot change the rule result and do not
justify provider data.

### 5.6 Required-data union

The first evaluation pass must compute the union of all still-relevant missing
facts across **every execution branch that can still become reachable** before
the terminal profile is known.

This avoids a multi-probe sequence such as:

```text
probe body
reevaluate
probe headers
```

Instead:

```text
still-relevant required data = {BODY, HEADERS}
=> one composite probe
```

An unresolved earlier `stop_processing` rule is a branch barrier, not permission
to ignore later rules. Example:

```text
rule 10: body condition, profile=discovery, stop_processing=true
rule 20: header condition, profile=full
```

Before BODY is known, rule 10 may either stop the ruleset or fail and expose
rule 20. The one permitted probe must therefore request both BODY and HEADERS.
After probe delivery, normal sequential semantics decide which branch actually
runs.

Facts for rules already proven false or rules that are unreachable after an
**already proven** stop-processing match are omitted. Likewise, once the maximal
V1 profile `full` is proven, later rules cannot affect acquisition depth and do
not justify additional probe data solely for audit completeness.

### 5.7 At most one composite provider probe per observation

The existing body-only probe evolves into one dynamic composite Mail detail
probe. The request selects/expands only the facts needed by the current
observation/ruleset, using the existing authenticated Microsoft Graph request
path, raw-evidence handling, retry policy, and named Spider callback/errback.

The required-data vocabulary is the fixed set from section 5.2:
`METADATA`, `BODY`, `HEADERS`, and `EXTENDED_PROPERTIES`.
`required_data` is an immutable set because one request may need several groups.

One observation may schedule at most one rule probe. A second `NEEDS_DATA`
after probe delivery is a programming/integrity failure.

A rule probe has a hard 8 MiB HTTP response download limit, independent of
Scrapy's much larger global downloader default and the Full-v1 raw-content
limit. Exceeding the rule-probe limit is an expected bounded probe failure; if
the oversized fact is still needed, evaluation becomes `UNRESOLVED -> full` and
the normal Full profile may subsequently use its own existing content budget.
The rule engine never scans an unbounded provider body.

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

### 5.8 Partial composite results

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

### 5.9 Source mutation fence

The initial observation and probe must represent the same provider message
version, identified by `changeKey` in V1.

The evaluator compares the trustworthy initial `changeKey` with the probed
`changeKey` whenever a probe is used. The composite probe always requests
`changeKey`. If the probe omits/malforms it, or if the values differ, msgloom
must not combine initial cheap facts with later detail facts.

Required result:

```text
UNRESOLVED
selected_profile = full
fallback_used = true
reason_code = source_changed_during_evaluation
```

### 5.10 Regex failure behavior

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
  -> run required Full refresh work
  -> prove every required target reached current-attempt Full-v1 terminal completeness
  -> atomically promote lifecycle + message-delta checkpoints
```

If required Full work does not reach that completion gate:

- final message-delta promotion does not happen;
- prior committed cursors remain authoritative;
- staged candidates remain non-authoritative pending data;
- next sync replays the change and reevaluates policy.

The gate is deliberately stronger and more precise than "crawler closed without
`run_failed`". Full-v1 defines several provider outcomes (`unsupported`,
`not_applicable`, `omitted_size_limit`, `unauthorized`, `unavailable`) as
terminal surfaces. Those terminal outcomes satisfy the acquisition profile even
though the underlying request was not a 2xx success. Conversely, old Full
surfaces from an earlier message version/run cannot prove that the current
rule-selected refresh succeeded.

This preserves the no-rule-decision-persistence decision while giving Full
selection durable retry semantics through the existing checkpoint boundary.

If the clean rules-enabled delta run selects **zero** Full targets, the Full
completion gate is vacuously satisfied. No `outlook_full` crawler is created;
the workflow proceeds directly to its success finalizer and atomically promotes
the validated message lifecycle/checkpoint state. A no-target run must not leave
a permanently deferred candidate merely because there was no Full phase to
close.

### 7.4 Current-attempt Full-v1 completion gate

Rules-enabled sync requires an explicit completion proof for each rule-selected
Full target. Existing catalog/evidence provenance is sufficient; no rule
decision table is added.

Rule-planned Full work is an **authoritative refresh**. The sync workflow
passes a private Full-Spider flag that cannot be selected through the public Full
CLI. When set, every provider Request that can satisfy the target's Full-v1
surfaces (detail, MIME, attachment inventory, attachment raw content, and item
attachment detail) uses `dont_cache=True`. This is required even though msgloom's
production HTTP-cache default is disabled: development cache replay can
canonicalize evidence to an older capture/run and would otherwise make
current-attempt completion impossible to prove. Rules-disabled sync and explicit
operator Full preserve their existing cache behavior.

For each target and the Full crawler run that processed it, the verifier must
prove:

1. `detail`, `mime`, and `attachments` surfaces have a Full-v1 terminal status;
2. each proving surface's `evidence_id` belongs to a non-cache-replayed raw HTTP
   evidence capture from that current Full crawler `run_id`;
3. when the current attachment inventory is `acquired`, attachment records
   considered for completeness are those whose latest metadata evidence belongs
   to that same Full run, and every required child surface for those attachments
   is terminal Full-v1 with evidence from the same run;
4. a surface or attachment state left only from an older Full attempt cannot
   satisfy the current refresh obligation.

This also handles attachment deletion correctly: old attachment rows may remain
historically in the catalog, but they are not part of the current attachment
inventory proof unless their metadata was observed in the current Full run.

The rules-enabled Full `GraphPhase` therefore needs a phase-specific completion
validator rather than blindly using the generic `_crawler_failed()` decision.
`run_graph_workflow()` keeps its current default behavior for every phase that
has no validator. `process.bootstrap_failed` is always fatal. When a phase
validator is present, it becomes the authoritative application-level gate after
the crawler closes; the validator itself must account for the crawler's failure
facts instead of the workflow also applying `_crawler_failed()` a second time.

For a rule-planned Full phase, the validator may accept profile-defined terminal
request outcomes **only** when the current-attempt surface proof above is
complete. The existing Full errback marks final HTTP request failures with
bounded reasons such as `request_failure:message-detail` even when it also emits
a profile-terminal surface (`unavailable`, `unauthorized`, `unsupported`). The
validator may waive only `request_failure:<purpose>` reasons whose exact required
surface(s) are proven terminal by current-run evidence. It must not waive:

- `spider_error` or callback/programming failures;
- `item_error` / `item_dropped` persistence failures;
- framework close/signal integrity failures;
- source identity/policy/JOBDIR failures;
- a request-failure reason for which the corresponding required current-run
  surface is missing/non-terminal;
- any transient provider/transport failure that leaves Full-v1 incomplete.

`OutlookCrawlStatusExtension` remains attempt-level observability and continues
to avoid claiming Full-profile completeness; its existing Full summary need not
be redefined merely because the higher-level workflow gate accepts a terminal
provider limitation. The workflow validator emits a separate bounded gate event
and stat, e.g. `terminal_complete`, `terminal_complete_with_limitations`, or
`incomplete`. A successful sync with terminal provider limitations may therefore
contain the existing per-request ERROR/WARNING evidence plus an explicit
workflow-level completion event explaining why the durable profile obligation
is nevertheless complete.

The validator never logs target IDs or provider content in aggregate summaries.
Rules-disabled sync and explicit operator Full commands retain their current
generic phase-failure behavior.

### 7.5 Rules-disabled compatibility

When Mail rules are disabled, current behavior remains unchanged:

```text
delta
-> immediate validated checkpoint promotion
-> current changed-message Full behavior
-> current global incomplete Full backlog
```

No-rules behavior is a hard backward-compatibility requirement.

### 7.6 Checkpoint validation versus promotion

The existing delta checkpoint extension currently validates completion and then
calls lifecycle/checkpoint promotion through separate store transactions. This
phase refactors the boundary so validation is reusable and final promotion is
atomic.

Conceptually:

```text
validate_delta_completion(...) -> ValidatedDeltaRun

promote_validated_delta_run(validated_run)
    -> one SQL transaction containing:
       - folder/message presence snapshot promotion for this message-delta run
       - authoritative per-folder message DeltaCheckpoint updates
       - candidate committed_at updates
```

If any part of final promotion fails, that transaction rolls back and the prior
committed message-delta cursors/lifecycle promotion remain authoritative. There
must not be a state where absence/presence snapshot promotion commits but the
matching provider cursor does not.

Then:

- direct/rules-disabled delta execution validates and atomically promotes
  immediately, preserving its observable behavior;
- rules-enabled sync validates at Spider idle and holds the durable candidates;
- the workflow atomically promotes only after the current-attempt Full-v1 gate
  passes for every required target.

Validation and promotion rules remain single-sourced. The independent
mailFolder-delta cursor remains its own provider stream and transaction; this
atomicity requirement applies to the message-delta lifecycle/cursor unit.

During rules-enabled sync, the delta checkpoint extension records a safe
`deferred` checkpoint outcome after successful validation instead of
`committed`. `OutlookCrawlStatusExtension` must recognize this private workflow
mode: a clean, validated delta collection may report phase status `completed`
with checkpoint outcome `deferred`, allowing `accepted_final_statuses` to
continue to Full work. `deferred` never means the authoritative cursor advanced;
the later workflow finalizer owns that commit and emits a separate safe
promotion success/failure event.

`OutlookDeltaSpider` exposes one private runtime commit mode; it is not a Scrapy
setting or user CLI option:

| Effective policy / owner | Commit mode | Idle behavior |
| --- | --- | --- |
| policy disabled | `immediate` | validate then atomically promote, preserving current behavior |
| policy enabled and created by `outlook mail sync` | `deferred` | validate, retain candidates, report safe deferred outcome |
| policy enabled without a policy-completing workflow owner | `blocked` | validate/stage only, never promote, terminate as incomplete with bounded `policy_completion_required` reason |

The sync command supplies only the safe private workflow-owner/mode argument when
creating its delta spider; the active Mail policy itself already determines
whether `immediate` is legal. A caller cannot force `immediate` while policy is
enabled. The checkpoint extension derives/validates the final mode from Spider
runtime state and fails closed on an impossible combination.

`blocked` is primarily a low-level development safety net because the public
`microsoft outlook mail delta` path rejects active policy before starting a
crawl. It may leave durable candidates/evidence for inspection, but those
candidates remain non-authoritative and the crawl must not report normal
completed status.

### 7.7 Workflow finalizer

The existing sequential `run_graph_workflow()` gains an optional
`on_success` finalizer with the logical contract:

```text
on_success(completed_crawlers)
```

It runs exactly once only when all initial and dynamically-added phases satisfy
their normal or phase-specific completion gates. `completed_crawlers` is the
final ordered tuple of crawlers from the workflow. Rules-enabled Mail sync uses
the callback (normally through a closure over its validated delta run) to
atomically promote the held message-delta state.

If the finalizer raises, the command fails, the held message-delta checkpoint is
not considered successfully promoted, and a bounded ERROR diagnostic records
only the finalizer/error class context. The workflow must not manufacture a fake
Scrapy Spider merely to perform the commit.

### 7.8 Public primitive behavior while policy is active

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

### 7.9 `--max-enrich` under active rules

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

The effective policy identity is distinguished by a SHA-256 digest. The digest
covers both behavior-affecting semantics and audit-visible active rule identity,
so renaming an enabled rule intentionally changes the policy identity even when
its predicates remain equivalent.

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
order-independent value sets, and canonicalizes/sorts exception blocks by their
canonical content.

Ordinary case-insensitive literals are hashed in their effective matching form
(`str.casefold()`, plus the documented surrounding-whitespace stripping for
address values). Thus changing `URGENT` to `urgent` does not invalidate a JOBDIR
when matching behavior is identical. Enum values are hashed in canonical
lowercase/snake-case form. Regex pattern text is preserved exactly because case,
inline options, whitespace, and escapes are part of regex semantics; only the
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

The effective policy digest is **private control-plane state**, not redacted
observability. Because canonical policy material can contain low-entropy email
addresses, categories, and keywords, publishing an unsalted SHA-256 in logs or
inspection output would enable offline dictionary guesses. Therefore the digest:

- may exist in process memory;
- may be carried by the existing internal `MailRuleEvaluation.ruleset_digest`
  field for contract/integrity checks;
- is written only to the private `0600` policy JOBDIR marker when JOBDIR is used;
- must not appear in Python/Scrapy logs, `LogRecord.extra`, stats, user-facing
  errors, `config inspect`, or provider/source Items.

Ordinary audit logs use the fixed policy-family ID plus non-secret matched rule
IDs, run/message correlation IDs, outcome/profile, and stop/probe/fallback flags.
Exact policy-value identity remains a private correctness primitive rather than
a loggable fingerprint.

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

Only the private effective digest and bounded contract metadata are stored; no
configured values or rule content are written into the marker. The marker is
created with owner-only `0600` permissions, matching the existing source-context
marker contract. The digest is safe for this private local control file but is
not considered safe for general observability.

Required behavior:

| Saved/job state | Current policy | Resume/start |
| --- | --- | --- |
| disabled marker | disabled | allowed |
| disabled marker | enabled | refused |
| rules A marker | rules A | allowed |
| rules A marker | rules B | refused |
| policy marker missing and, after source-context verification, JOBDIR contains only `.msgloom-source-context-v1` | disabled or enabled | treat as new/pre-Scheduler job; create current policy marker |
| policy marker missing from a pre-feature JOBDIR that already contains other persisted Scrapy state | disabled | one-time bootstrap allowed only after source/catalog context verification |
| policy marker missing from a pre-feature JOBDIR that already contains other persisted Scrapy state | enabled | refused |

The source-context guard runs before the policy guard. For a brand-new/empty
JOBDIR it may therefore create `.msgloom-source-context-v1` immediately before
the policy guard executes. The presence of that one marker alone is **not**
evidence of legacy queued work and must not block first use of an enabled
ruleset. The policy guard classifies a markerless job as legacy only when the
directory contains entries other than the verified source-context marker.

The legacy disabled-policy exception is required for backward compatibility: an
existing no-rules JOBDIR created after source-context binding but before this
policy feature may resume under the same no-rules semantics. After source/catalog
ownership verifies, msgloom writes the disabled-policy marker before Scheduler
construction. A markerless legacy job containing persisted Scrapy state is never
allowed to bootstrap directly into an enabled ruleset.

The guard runs before the Scheduler is constructed, not from a lifecycle signal.
`OutlookMailCollectionSpider.update_settings()` registers a Mail-specific policy
context extension at extension component priority **60**. The existing global
`SourceContextExtension` remains priority **50**. Scrapy 2.19 constructs
extensions in component-priority order during `Crawler._apply_settings()`, after
the Spider exists and before Engine/Scheduler construction, so the sequence is:

```text
SourceContextExtension (50)
  -> verify/create source+catalog JOBDIR marker
OutlookMailPolicyContextExtension (60)
  -> verify/create policy marker using spider.mail_ruleset_digest
Scheduler
  -> may load persisted requests only after both guards succeeded
```

The policy extension does not connect a signal handler for this gate and does
not rely on signal-handler order. It raises a bounded startup integrity failure
on mismatch. It is registered only for Mail collection spiders and raises
`NotConfigured` when JOBDIR is absent. The extension reads only the private
effective digest/policy-enabled state from the already-created Spider runtime
context; raw rules never enter Scrapy settings, and the digest is never logged.

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
| regex patterns across the whole Mail section | 64 |
| regex pattern length | 4096 characters |
| RE2 memory budget per compiled pattern | 4 MiB |
| rule-probe HTTP response | 8 MiB |
| logical BODY UTF-8 after projection | 8 MiB |
| rule ID | 96 characters |

Changing these bounds requires an explicit design/spec change; the
implementation plan must not silently tighten, relax, or remove them.

### 9.3 Privacy-safe error detail

User-facing configuration errors must be more actionable than a single generic
`invalid_input` message while still protecting configured values.

Allowed detail:

- a non-sensitive source label such as `default-config` or `explicit-config`;
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
- filesystem config paths (the existing configuration privacy contract does
  not echo them);
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
An invalid private-looking regex must also remain absent from stdout, stderr,
Python logging records, and wrapped exception text. The RE2 adapter's disabled
engine logging is part of this guarantee, not merely an optimization.

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

Rule logs may include the fixed policy-family ID, bounded run/message/rule IDs,
profile/outcome/stop-rule/probe/fallback flags, but never the private effective
policy digest, configured match values, or Mail content. The existing middleware
log format must be revised to stop rendering `ruleset_digest` once real policy
configuration supplies a content-derived digest.

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
- rule IDs and sequence, including that rule IDs are loggable non-secret audit labels;
- conditions field-AND / value-OR semantics;
- exception block semantics;
- monotonic strongest-profile selection;
- stop-processing;
- default case-insensitive matching;
- exact/contains/regex choices;
- `msgloom-regex-v1`, TOML literal-string regex examples, and major RE2 unsupported constructs;
- one-probe/fail-safe behavior in user-friendly terms;
- that a rule probe is normal acquisition evidence and may persist body/header
  content even when the selected profile is `discovery`;
- data-minimizing guidance to prefer cheap predicates when possible;
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
42. why `bodyPreview` is not used as terminal body-match evidence;
43. successful composite probe;
44. probe source change -> Full fail-safe;
45. provider fact unavailable -> Full fail-safe when decision depends on it;
46. regex runtime/resource failure -> Full fail-safe;
47. programming failure distinction;
48. rule-required Full work that fails the current-attempt terminal-completeness
    gate leaves the delta checkpoint unpromoted;
49. policy change not retroactively scanning unchanged history;
50. explicit operator Full override;
51. discovery command evaluates decisions but does not execute selected Full work;
52. standalone delta rejected while policy is active;
53. `--max-enrich` rejected while policy is active;
54. a body/header rule that ends at `discovery` still persists its rule-probe
    raw evidence, contrasted with an equivalent cheap metadata-only rule.

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
- a cheap true exception excludes an otherwise-unknown condition without a
  probe;
- ordered rule processing;
- unique sequence validation;
- monotonic profile selection;
- stop-processing;
- cheap-first false short-circuit;
- body-or-subject positive short-circuit;
- required-data union;
- partial composite probe facts;
- known-empty versus unavailable initial metadata;
- oversized discovery facts become unavailable without truncation or oversized
  JOBDIR callback state;
- unavailable relevant cheap metadata joins the one composite probe;
- missing initial `changeKey` plus required probe -> unresolved Full fallback;
- unresolved stop-processing branch requests later-branch facts in the same probe;
- bodyPreview is never terminal body-matching proof in V1;
- deterministic text-body and HTML-body visible-text projection;
- `changeKey`-based source mutation fence;
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
- one universal document containing both legacy operator sections and
  `[acquisition]` without `OperatorSettings` rejecting the acquisition subtree;
- Mail acquisition ignores an incomplete/invalid-but-top-level-known unrelated
  legacy section, while `config validate` and the corresponding legacy operation
  reject it through their strict projection;
- operation-specific validation without requiring unrelated A2/A3/A5 config;
- `config validate` / `config inspect` use the XDG default when `--config` is
  omitted, accept one explicit whole-file `--config` override, recognize the
  Mail acquisition section, and expose only redacted Mail metadata on inspect;
- config errors never echo the filesystem config path or a private regex value;
- RE2 compile failures emit no pattern content to stdout/stderr/log records;
- the 64-pattern and RE2 memory-budget bounds.

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
- no raw rules or private effective-policy digest appear in Scrapy
  overridden-settings logs, Spider startup/decision logs, SpiderState, request
  serialization, stats, config inspection, or structured log extras;
- JOBDIR ruleset marker creation and same-policy resume;
- real ExtensionManager construction orders source-context priority 50 before
  Mail policy-context priority 60, and policy mismatch rejects resume before the
  Scheduler can load/run queued work;
- a new JOBDIR containing only the source-context marker can create either an
  enabled or disabled policy marker before Scheduler construction;
- a pre-feature markerless JOBDIR with persisted Scrapy state can bootstrap only
  the disabled-policy marker after source/catalog ownership is verified;
- markerless legacy JOBDIR with persisted state + enabled rules is rejected;
- rule-probe response-size overflow becomes bounded unresolved fallback rather
  than an unbounded download;
- body/header probe responses remain normal raw evidence even for final
  discovery-profile decisions.

### 13.4 Planner/checkpoint tests

Cover:

- rules disabled preserves current sync planner behavior exactly;
- rules enabled plans Full only from attempt-local selected targets;
- discovery-only messages do not re-enter Full via legacy global backlog;
- duplicate observations use strongest profile;
- clean rules-enabled delta reports checkpoint outcome `deferred` and remains an
  accepted collection phase without advancing the cursor;
- current-attempt Full-v1 terminal completeness accepts profile-defined terminal
  unavailable/unauthorized/unsupported outcomes even when the existing Full
  crawler carries only the corresponding waivable `request_failure:<purpose>`
  reasons;
- transient Full failures and non-waivable crawler integrity failures reject the
  Full completion gate;
- old terminal surfaces cannot satisfy a new rule-selected refresh;
- with Scrapy HTTP cache enabled and a matching old cached response present, a
  rule-planned authoritative Full refresh bypasses cache and produces current-run
  evidence;
- current attachment-inventory proof ignores attachment rows not observed in the
  current Full run;
- a rules-enabled run with zero Full targets creates no Full crawler and still
  atomically promotes the validated lifecycle/checkpoint once;
- successful rules-enabled sync with Full targets atomically promotes lifecycle
  and staged delta checkpoints once;
- an injected failure during final promotion rolls back both lifecycle and
  checkpoint changes;
- failed/incomplete Full work does not promote the staged delta checkpoint;
- next run can replay from the prior committed delta cursor;
- explicit Full command remains independent of rules;
- public standalone Mail delta is rejected when policy is active;
- low-level direct delta under active policy enters private `blocked` commit
  mode, cannot promote a policy-selected cursor, and terminates incomplete;
- a caller cannot force `immediate` commit mode while policy is enabled;
- explicit `--max-enrich` is rejected while policy is active;
- checkpoint validation logic remains single-sourced.

### 13.5 Real Microsoft Graph evidence

At least one development/qualification test against the real Microsoft Graph
service must prove the composite probe request shape for the supported V1 facts,
particularly `$select` plus any required extended-property `$expand` behavior,
using only the existing Mail read-scope contract.
The real delta/discovery qualification also proves that adding `changeKey` to
the selected Mail metadata supplies a stable version token to rule observations.

The message-class extended property and the special-message mappings above must
be validated against documented source facts, not fixture-only assumptions.
Qualification must include a real `eventMessage` body case so the
HTML-to-logical-text path is proven against Graph v1.0 behavior.

Dependency qualification must also exercise the pinned `google-re2` build on
the repository's supported Python 3.12/3.13/3.14 environments; the development
Linux/aarch64 target must use an available supported wheel or a deliberately
reviewed build path rather than an accidental local compiler dependency.

## 14. Implementation boundaries

The implementation should remain decomposed into focused units, for example:

- universal config resolver/read boundary;
- Mail rule config models/validation;
- regex engine adapter;
- predicate evaluation helpers and source-fact availability projection;
- bounded logical HTML/text body projection;
- deterministic ruleset evaluator;
- ruleset canonicalization/digest;
- composite probe fact model and Spider request/parser seam;
- JOBDIR policy-context guard;
- attempt-local planner handoff;
- current-attempt Full-v1 completion verifier;
- reusable atomic delta validation/promotion service;
- workflow phase-completion validator and success finalizer;
- user/reference documentation.

The exact file split is deferred to the implementation plan after repository
reinspection. No unit should require reading Scrapy internals to understand pure
rule semantics.

## 15. Rejected alternatives

### Separate Mail-only config file

Rejected because msgloom should have one universal user configuration surface,
not one file per feature.

### Eagerly require every universal section

Rejected because using Mail acquisition rules must not require configuring
triage/report/other unrelated subsystems.

### Load `msgloom.toml` from `message_ingest.settings`

Rejected because project settings load before custom command selection, would
make unrelated Scrapy commands parse Mail policy, complicates `--config`, and
turns user policy into module-import side effects.

### Put raw rules into Scrapy settings

Rejected for privacy, deepcopy/pickle, lifecycle, and ownership reasons.

### Create a Scrapy add-on only to load user rules

Rejected because Mail user policy is not framework component configuration.

### Multiple environment/CLI overrides for individual rule fields

Rejected because the user must be able to understand persistent policy from one
file. `--config` selects another complete file; it does not build a hidden
precedence maze for rule semantics.

### Python standard-library `re`

Rejected for user-supplied rules because it lacks a safe per-match timeout and
does not provide RE2's predictable execution model.

### Broad `regex` package as public dialect

Rejected as the V1 default because long-term maintenance is strongly centered
on one maintainer and its broad syntax would make the dependency's behavior the
user contract.

### Automatic fallback from RE2 to another engine

Rejected because two regex dialect/runtime paths increase semantic and
maintenance risk.

### Arbitrary nested boolean expressions in V1

Rejected to keep configuration understandable, deterministic, and bounded for
non-technical users.

### Persist per-message rule decisions

Rejected because they are policy/control state, not provider content, and would
create migration/staleness obligations when rules change.

### Use logs as planner state

Rejected because observability is not a correctness/control channel.

### Continue global incomplete-Full backlog when rules are active

Rejected because intentional discovery-only messages would be upgraded to Full
outside the rule policy.

### Commit delta cursor before rule-selected Full work completes

Rejected because a later Full failure can permanently lose the obligation after
the provider delta cursor advances.

### Clear delta cursors whenever rules change

Rejected because it is an implicit expensive historical reconciliation with
poor resume/cost semantics. A future policy-reconciliation workflow should be
explicitly designed instead.

## 16. Acceptance criteria

The phase is complete only when all of the following hold:

1. one XDG-based universal config resolver exists and absent default config is
   valid;
2. one universal TOML can contain both existing operator sections and the new
   acquisition section; Mail operations validate only Mail policy, legacy
   operations validate only their legacy projection, and `config validate`
   strictly validates all present supported projections;
3. explicit `--config` selects one complete config and missing/invalid explicit
   files fail;
4. Mail policy is opt-in with `enabled = true`, and Mail rule semantics are not
   overridden by environment/mounted setting sources;
5. zero-config / rules-disabled acquisition behavior remains unchanged;
6. user profile vocabulary is `discovery` / `full` while internal contracts
   remain versioned;
7. conditions/exceptions implement the documented AND/OR model without nested
   boolean syntax;
8. regex uses the `msgloom-regex-v1` contract backed by pinned Google RE2,
   defaults case-insensitive without rewriting patterns, disables RE2 error
   logging, and enforces the documented pattern/memory bounds;
9. every V1 supported predicate has a documented reliable source fact and an
   explicit Outlook-baseline versus msgloom-extension classification, and the
   supported set requires no Graph permission beyond the existing Mail read
   scopes;
10. deferred predicates, including `messageActionFlag`, fail validation rather
    than use partial/heuristic provider mappings;
11. the pure RuleEngine is deterministic and independent of Scrapy;
12. initial source facts distinguish known empty/null from unavailable/malformed
    provider data, and unavailable relevant facts never silently become false;
13. cheap-first evaluation avoids unnecessary probes while unresolved
    stop-processing branches still contribute all data needed for the single
    possible future branch probe;
14. one observation schedules at most one composite rule probe, with an 8 MiB
    response bound;
15. probe facts are partial/typed and missing irrelevant facts do not force a
    fallback;
16. `bodyPreview` is not terminal body-match evidence in V1; body predicates
    use the complete deterministic logical body unless subject truth alone
    resolves a body-or-subject predicate;
17. text and HTML Graph bodies map to the documented deterministic logical-text
    body, including real Graph v1.0 `eventMessage` HTML behavior;
18. missing initial `changeKey` when a probe is required, missing/malformed
    probe `changeKey`, or a `changeKey` mismatch becomes `UNRESOLVED` with Full
    fallback;
19. bounded provider/regex evaluation uncertainty becomes per-message
    `UNRESOLVED` + Full fallback;
20. unexpected programming/integrity failures mark the logical run failed;
21. profile selection is ordered and monotonic with explicit stop-processing;
22. duplicate observations accumulate the strongest required acquisition
    profile;
23. no per-message rule decision is written to the Mail catalog;
24. rules-enabled sync does not use the legacy global incomplete-Full backlog;
25. each rule-required Full target is acquired through an authoritative
    no-cache refresh and must prove current-attempt Full-v1 terminal completeness;
    old/cached surfaces and old attachment metadata cannot satisfy a new refresh;
26. profile-defined terminal unavailable/unauthorized/unsupported Full outcomes
    may satisfy that completion gate, while transient or integrity failures do
    not;
27. a clean rules-enabled delta phase reports a safe deferred-checkpoint state
    and does not advance the authoritative message cursor before Full completion;
28. final message lifecycle and message-delta checkpoint promotion occurs in one
    atomic SQL transaction after all rule-required Full completion gates pass;
29. failure during final promotion rolls back both lifecycle and checkpoint
    changes, leaving the prior committed cursor authoritative;
30. rules-disabled sync retains the current planner/checkpoint behavior;
31. standalone user-level Mail delta is refused while policy is active, and a
    low-level direct delta cannot unsafely promote the cursor outside a
    policy-completing workflow;
32. `--max-enrich` cannot truncate non-durable rule-required Full obligations;
33. Mail JOBDIR binds effective policy identity, distinguishes a new job that
    contains only the just-verified source marker from a legacy job with
    persisted Scrapy state, refuses mismatched resume, and supports only the
    documented one-time disabled-policy bootstrap for a markerless legacy job
    whose source/catalog ownership already verifies;
34. raw rule values and the private effective-policy digest never enter Scrapy
    settings, logs, stats, config inspection, or Items, and privacy-safe config
    errors do not echo filesystem config paths or invalid private regex text to
    stdout/stderr/log records;
35. rule-probe responses continue through normal raw-evidence persistence, and
    user documentation clearly explains that final `discovery` does not mean a
    body/header probe was never acquired;
36. `config validate` recognizes every present supported universal section and
    `config inspect` exposes only redacted/safe Mail policy metadata;
37. the ordinary user guide includes the required example catalogue and clearly
    documents V1 historical/non-retroactive behavior;
38. the pinned `google-re2` dependency is qualified on supported Python
    3.12/3.13/3.14 environments including Linux/aarch64;
39. real Microsoft Graph qualification proves the actual one-request composite
    probe shape and the supported extended-property/special-message facts,
    including an event-message body case;
40. focused, regression, lint, type-check, native Scrapy lifecycle, JOBDIR,
    privacy, atomicity, and real-Graph qualification tests pass on the project's
    supported runtime.

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
