# Outlook Mail acquisition rules

This guide explains how to choose which Outlook Mail messages remain at the
lightweight `discovery` acquisition profile and which are upgraded to `full`.
It is written for operators first; implementation details are collected later in
this document.

## Quick start

msgloom reads one universal user configuration file. By default it is:

```text
$XDG_CONFIG_HOME/msgloom/msgloom.toml
```

If `XDG_CONFIG_HOME` is unset or relative, msgloom uses:

```text
~/.config/msgloom/msgloom.toml
```

A missing default file is valid and means built-in defaults. An existing but
invalid file is an error. `--config FILE` selects one complete alternative file;
it does not merge files.

A minimal selective-Full policy is:

```toml
[acquisition.microsoft.outlook.mail]
enabled = true
default_profile = "discovery"

[[acquisition.microsoft.outlook.mail.rules]]
id = "important-01"
sequence = 10
profile = "full"

[acquisition.microsoft.outlook.mail.rules.conditions]
from_addresses = ["manager@example.test"]
subject_contains = ["approval"]
```

Run the policy-completing workflow with:

```text
scrapy microsoft outlook mail sync
```

or select another complete universal config:

```text
scrapy microsoft outlook mail sync --config /path/to/msgloom.toml
```

Validate or inspect the default config without starting acquisition:

```text
msgloom config validate
msgloom config inspect
```

Use `--config FILE` with those commands to validate or inspect another complete
universal file.

## Activation and default behavior

Mail rules are opt-in. These cases all keep the existing no-rules behavior:

- the Mail section is absent;
- `enabled` is omitted;
- `enabled = false`.

Rules control acquisition only when the section explicitly contains:

```toml
[acquisition.microsoft.outlook.mail]
enabled = true
```

When rules are enabled, the default profile is `discovery` unless changed.
`discovery` means msgloom does not schedule the Full-v1 detail/MIME/attachment
traversal for that message. It does **not** mean rule evaluation can never read
additional content: body, header, size, sensitivity, or message-class predicates
may need one bounded rule probe.

The two user-visible profiles are:

| Profile | Meaning |
| --- | --- |
| `discovery` | Keep the message at discovery acquisition depth unless a rule upgrades it. |
| `full` | Require the existing Outlook Mail Full-v1 acquisition surfaces. |

Profile selection is monotonic:

```text
discovery < full
```

A later matching `discovery` rule cannot downgrade a message that is already
`full`.

## Rule structure

Each rule has a non-secret audit ID, a unique sequence, a target profile, one
conditions block, and zero or more exception blocks:

```toml
[[acquisition.microsoft.outlook.mail.rules]]
id = "finance-01"
sequence = 20
enabled = true
profile = "full"
stop_processing = false

[acquisition.microsoft.outlook.mail.rules.conditions]
from_address_regex = ['@finance\.example\.test$']
subject_contains = ["invoice", "approval"]

[[acquisition.microsoft.outlook.mail.rules.exceptions]]
categories = ["ignore"]
```

Rule IDs are written to ordinary INFO decision logs. Use neutral IDs such as
`finance-01`; do not put names, email addresses, subject text, customer names, or
other private matching values in an ID.

`sequence` is an integer from `0` through `2147483647`, and every rule must use a
unique value. Lower sequence values run first.

A disabled individual rule remains fully validated. If you want to keep an
invalid or unfinished draft, comment it out rather than relying on
`enabled = false`.

## Boolean semantics

V1 deliberately avoids arbitrary nested boolean expressions.

Inside one conditions or exception block:

- different fields are **AND**;
- multiple values in one field are **OR**.

For example:

```toml
[acquisition.microsoft.outlook.mail.rules.conditions]
from_addresses = ["a@example.test", "b@example.test"]
subject_contains = ["approval", "invoice"]
has_attachments = true
```

means:

```text
(from is a OR b)
AND
(subject contains approval OR invoice)
AND
has attachments
```

Exception blocks are OR with each other. A rule matches only when its conditions
are true and no exception block is true.

The engine is cheap-first. A known false cheap condition can avoid an expensive
body/header probe. Likewise, a known true exception can exclude a rule without
fetching an otherwise-unknown body condition.

## Ordering and `stop_processing`

Matching a rule applies its profile and normally continues to later rules.
Because acquisition depth is monotonic, later rules may maintain or upgrade the
profile but never reduce it.

`stop_processing = true` applies the current rule and then stops evaluating
later rules. This is the way to create a narrow early `discovery` exception in
front of broader Full rules.

Once `full` is proven, later rules cannot change acquisition depth, so msgloom
may stop evaluating them instead of fetching data only for audit completeness.

## Text matching

Ordinary textual exact/contains predicates are case-insensitive using Unicode
`str.casefold()`. V1 does not add Unicode normalization, accent folding,
transliteration, or locale-specific rewriting.

Address configuration values have surrounding whitespace stripped. Other
free-text values preserve the whitespace you wrote. Empty strings are rejected.

Display-name behavior is explicit:

- `from_contains` searches the From display name or address and corresponds to
  Outlook's `senderContains` concept;
- `sender_contains` searches the actual Sender display name or address;
- `recipient_contains` searches To + Cc display names or addresses;
- fields containing `_address_` search addresses only.

Bcc is never silently included in `recipient_contains`.

## Regular expressions

Regex fields use the public `msgloom-regex-v1` contract backed by Google RE2.
They use search semantics and are case-insensitive by default. msgloom passes the
pattern to RE2 unchanged.

Prefer TOML literal strings so backslashes do not need double escaping:

```toml
subject_regex = ['invoice\s+#\d+']
from_address_regex = ['@example\.test$']
```

Use anchors when you want field boundaries:

```toml
subject_regex = ['^urgent:$']
```

Advanced RE2 inline flags can override the default. For example, an explicitly
case-sensitive region can use:

```toml
subject_regex = ['(?-i:URGENT)']
```

V1 rejects RE2-unsupported constructs at config load, including look-around and
backreferences. There is no fallback regex engine.

Literal predicates and regex predicates can differ on unusual Unicode case
edges because RE2's Unicode case behavior is its own regex-language contract,
whereas literals use Python `str.casefold()`.

## Data cost and the one-probe rule

Discovery metadata can decide many rules without another provider request. Some
predicates require facts that are not in the normal discovery representation.
msgloom may issue **at most one composite rule probe per observation** to fetch
all still-relevant missing facts together.

The probe is bounded and may include:

- complete logical BODY;
- internet message headers;
- missing metadata;
- documented Outlook/MAPI extended properties for sensitivity, message size, or
  message class.

A rule-probe response is normal acquisition evidence. It can persist body or
header content even if the final selected profile is `discovery`. If data
minimization is important, prefer sender/recipient/subject/category/importance
predicates where they express the policy you need.

`bodyPreview` is not terminal body-match evidence. Body predicates use the
complete logical body unless a subject match alone resolves a
body-or-subject predicate.

Both provider text and HTML bodies are supported. HTML is converted to bounded
visible logical text; scripts/styles and other active content are omitted, table
text is retained, and raw HTML/MIME bytes are never the rule matching surface.

## Fail-safe behavior

If a still-relevant source fact cannot be resolved after the one probe, msgloom
selects `full` for that message rather than treating unknown as false. Examples
include:

- requested provider fact unavailable;
- rule-probe transport/resource failure;
- bounded regex runtime failure;
- source version changes between discovery and probe.

The mutation fence uses Graph `changeKey`. If the initial observation has no
trustworthy `changeKey`, the probe has no trustworthy `changeKey`, or the values
differ, the result is unresolved and falls back to `full`.

Programming/integrity errors are different. They fail the logical crawl/run
instead of being disguised as a source-data fallback.

## Commands and workflow restrictions

When Mail rules are active:

- use `scrapy microsoft outlook mail sync` for policy-completing acquisition;
- `scrapy microsoft outlook mail delta` is rejected because it cannot safely
  advance the provider cursor while discarding non-durable Full obligations;
- `--max-enrich` is rejected because truncating rule-required Full work would
  lose non-durable obligations;
- `scrapy microsoft outlook mail discover` may evaluate/log decisions but does
  not execute selected Full work;
- `scrapy microsoft outlook mail full MESSAGE_ID ...` remains an explicit
  operator override and does not consume Mail rule config.

Rules-enabled sync does not use the legacy global incomplete-Full backlog.
Only Full targets selected from the current delta attempt are scheduled.
Message-delta checkpoint promotion is held until every required target reaches
current-attempt Full-v1 terminal completeness; promotion of message lifecycle
state and delta cursors is atomic.

## Policy changes and history

V1 rules apply to messages observed after the policy becomes active. Changing a
ruleset does not automatically enumerate and reevaluate every unchanged
historical message.

If an old message is observed again through normal discovery, delta, or
reconciliation recovery, the current policy applies. A future policy
reconciliation workflow may add explicit historical reevaluation; V1 does not
fake this by clearing delta cursors or storing per-message rule decisions.

## Supported predicate reference

The `Origin` column distinguishes Outlook-style baseline concepts from explicit
msgloom extensions. `Probe` means a still-relevant predicate can require the
single composite rule probe.

| Fields | Origin | Source/cost |
| --- | --- | --- |
| `subject_contains` | Outlook baseline | discovery |
| `subject_exact`, `subject_regex` | msgloom extension | discovery |
| `body_contains` | Outlook baseline | BODY probe |
| `body_regex` | msgloom extension | BODY probe |
| `body_or_subject_contains` | Outlook baseline | subject first; BODY probe if still unknown |
| `body_or_subject_regex` | msgloom extension | subject first; BODY probe if still unknown |
| `from_addresses` | Outlook baseline | discovery |
| `from_contains` | Outlook baseline (`senderContains`) | discovery, display name or address |
| `from_address_contains`, `from_address_regex` | msgloom extension | discovery, address only |
| `sender_addresses`, `sender_contains`, `sender_address_contains`, `sender_address_regex` | msgloom extension | discovery, actual Sender |
| `to_addresses`, `to_address_contains`, `to_address_regex` | baseline + extensions | discovery |
| `cc_addresses`, `cc_address_contains`, `cc_address_regex` | msgloom extension | discovery |
| `bcc_addresses`, `bcc_address_contains`, `bcc_address_regex` | msgloom extension | discovery |
| `recipient_contains` | Outlook baseline | discovery, To + Cc display name/address |
| `recipient_address_contains`, `recipient_address_regex` | msgloom extension | discovery, To + Cc addresses only |
| `reply_to_addresses`, `reply_to_address_contains`, `reply_to_address_regex` | msgloom extension | discovery |
| `categories` | Outlook baseline | discovery |
| `importance` | Outlook baseline | discovery |
| `has_attachments` | Outlook baseline | discovery |
| `header_contains` | Outlook baseline | headers probe |
| `header_regex` | msgloom extension | headers probe |
| `sensitivity` | Outlook baseline | extended-property probe |
| `message_size_min_kb`, `message_size_max_kb` | Outlook-inspired msgloom contract | extended-property probe |
| `received_after`, `received_before`, `sent_after`, `sent_before`, `created_after`, `created_before` | msgloom extension | discovery |
| `is_read`, `is_draft` | msgloom extension | discovery |
| `inference_classification` | msgloom extension | discovery |
| `followup_status` | msgloom extension | discovery |
| `item_class_exact`, `item_class_contains`, `item_class_regex` | Outlook/EWS-inspired extension | extended-property probe |
| `is_meeting_request`, `is_meeting_response`, `is_non_delivery_report`, `is_read_receipt` | Outlook baseline | message-class extended-property probe |

### Enum and range values

`importance` accepts:

```text
low, normal, high
```

`sensitivity` accepts:

```text
normal, personal, private, confidential
```

`inference_classification` accepts:

```text
focused, other
```

`followup_status` accepts:

```text
not_flagged, flagged, complete
```

These enum values and profile names are accepted case-insensitively and stored
canonically.

Message-size bounds are inclusive and use KiB-style units:

```text
bytes >= message_size_min_kb * 1024
bytes <= message_size_max_kb * 1024
```

Each configured size is `0..2097151`.

Datetime values must be timezone-aware ISO-8601 strings. Lower bounds are
inclusive; upper bounds are exclusive. Equivalent instants with different UTC
offsets compare identically.

### Special message predicates

Special-message predicates use documented Outlook/MAPI message classes, not
subject/header heuristics:

| Predicate | True message class |
| --- | --- |
| `is_meeting_request` | `IPM.Schedule.Meeting.Request` |
| `is_meeting_response` | `IPM.Schedule.Meeting.Resp.Pos`, `.Tent`, or `.Neg` |
| `is_non_delivery_report` | starts with `REPORT.` and ends with `.NDR` |
| `is_read_receipt` | starts with `REPORT.` and ends with `.IPNRN`, or exactly `IPM.Note.Receipt.SMIME` |

## Deferred Outlook concepts

V1 deliberately does not claim local Outlook-equivalent semantics for these
concepts:

- sent to me / sent Cc me / sent only to me / sent to or Cc me / not sent to
  me;
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

Unknown/deferred configuration fields fail validation; they are never silently
ignored. The to-me family is deferred until msgloom has a trustworthy mailbox
SMTP identity + aliases without broadening Graph permissions.

## Troubleshooting configuration

`msgloom config validate` reports only safe source/field/reason diagnostics. It
never echoes the offending private regex, email address, keyword, or filesystem
config path.

Typical failures include:

- unsupported profile;
- duplicate rule ID or sequence;
- unknown predicate;
- invalid `msgloom-regex-v1` syntax;
- inverted size range;
- naive datetime without timezone offset;
- configured structure/value exceeding a documented bound.

A globally disabled policy and disabled individual rules are still validated.
This lets validation mean the config is safe to enable later.

## Example catalogue

The examples below use fictional `.test` addresses and values. Unless an example
shows the root section, assume this preamble:

```toml
[acquisition.microsoft.outlook.mail]
enabled = true
default_profile = "discovery"
```

### Example 1: enable rules with discovery default

```toml
[acquisition.microsoft.outlook.mail]
enabled = true
default_profile = "discovery"
```

With no rules, every newly evaluated message remains at discovery depth.

### Example 2: make every observed Mail full

```toml
[acquisition.microsoft.outlook.mail]
enabled = true
default_profile = "full"
```

A Full default cannot later be downgraded by ordinary rules.

### Example 3: exact From address

```toml
[[acquisition.microsoft.outlook.mail.rules]]
id = "manager-01"
sequence = 10
profile = "full"

[acquisition.microsoft.outlook.mail.rules.conditions]
from_addresses = ["manager@example.test"]
```

### Example 4: multiple From addresses are OR

```toml
[acquisition.microsoft.outlook.mail.rules.conditions]
from_addresses = ["a@example.test", "b@example.test"]
```

Either address satisfies this one predicate.

### Example 5: sender domain regex

```toml
[acquisition.microsoft.outlook.mail.rules.conditions]
from_address_regex = ['@finance\.example\.test$']
```

### Example 6: subject contains

```toml
[acquisition.microsoft.outlook.mail.rules.conditions]
subject_contains = ["approval"]
```

### Example 7: subject regex

```toml
[acquisition.microsoft.outlook.mail.rules.conditions]
subject_regex = ['invoice\s+#\d+']
```

### Example 8: body contains

```toml
[acquisition.microsoft.outlook.mail.rules.conditions]
body_contains = ["action required"]
```

This can require a BODY probe.

### Example 9: body regex

```toml
[acquisition.microsoft.outlook.mail.rules.conditions]
body_regex = ['purchase\s+order\s+#\d+']
```

### Example 10: body or subject

```toml
[acquisition.microsoft.outlook.mail.rules.conditions]
body_or_subject_contains = ["incident"]
```

A subject match avoids the BODY probe.

### Example 11: multiple condition fields are AND

```toml
[acquisition.microsoft.outlook.mail.rules.conditions]
from_addresses = ["manager@example.test"]
subject_contains = ["approval"]
has_attachments = true
```

All three fields must be true.

### Example 12: multiple values inside a field are OR

```toml
[acquisition.microsoft.outlook.mail.rules.conditions]
subject_contains = ["invoice", "approval", "contract"]
```

### Example 13: one exception block

```toml
[[acquisition.microsoft.outlook.mail.rules.exceptions]]
categories = ["ignore"]
```

A matching category excludes the rule.

### Example 14: multiple exception blocks are OR

```toml
[[acquisition.microsoft.outlook.mail.rules.exceptions]]
categories = ["ignore"]

[[acquisition.microsoft.outlook.mail.rules.exceptions]]
from_addresses = ["automation@example.test"]
subject_contains = ["test"]
```

Either exception block excludes the rule; fields within the second block are
AND.

### Example 15: category exclusion

```toml
[acquisition.microsoft.outlook.mail.rules.conditions]
subject_contains = ["invoice"]

[[acquisition.microsoft.outlook.mail.rules.exceptions]]
categories = ["archive-only"]
```

### Example 16: attachments

```toml
[acquisition.microsoft.outlook.mail.rules.conditions]
has_attachments = true
```

Graph's `hasAttachments` provider semantics apply, including its inline-only
attachment caveat.

### Example 17: importance

```toml
[acquisition.microsoft.outlook.mail.rules.conditions]
importance = ["high"]
```

### Example 18: To recipient

```toml
[acquisition.microsoft.outlook.mail.rules.conditions]
to_addresses = ["team@example.test"]
```

### Example 19: Cc recipient

```toml
[acquisition.microsoft.outlook.mail.rules.conditions]
cc_address_contains = ["@legal.example.test"]
```

### Example 20: Bcc recipient

```toml
[acquisition.microsoft.outlook.mail.rules.conditions]
bcc_address_regex = ['@audit\.example\.test$']
```

### Example 21: aggregate Outlook recipient condition

```toml
[acquisition.microsoft.outlook.mail.rules.conditions]
recipient_contains = ["Operations"]
```

This searches To + Cc recipient display names/addresses, not Bcc.

### Example 22: header condition

```toml
[acquisition.microsoft.outlook.mail.rules.conditions]
header_contains = ["X-Workflow: production"]
```

Header conditions can require the composite probe.

### Example 23: sensitivity

```toml
[acquisition.microsoft.outlook.mail.rules.conditions]
sensitivity = ["private", "confidential"]
```

### Example 24: message size range

```toml
[acquisition.microsoft.outlook.mail.rules.conditions]
message_size_min_kb = 100
message_size_max_kb = 2048
```

Both bounds are inclusive.

### Example 25: received and sent time ranges

```toml
[acquisition.microsoft.outlook.mail.rules.conditions]
received_after = "2026-10-01T00:00:00+10:00"
received_before = "2026-11-01T00:00:00+11:00"
sent_after = "2026-09-30T00:00:00Z"
```

### Example 26: read and draft state

```toml
[acquisition.microsoft.outlook.mail.rules.conditions]
is_read = false
is_draft = false
```

### Example 27: Focused Inbox classification

```toml
[acquisition.microsoft.outlook.mail.rules.conditions]
inference_classification = ["focused"]
```

### Example 28: follow-up flag

```toml
[acquisition.microsoft.outlook.mail.rules.conditions]
followup_status = ["flagged"]
```

This is the provider follow-up status, not Outlook Inbox-rule
`messageActionFlag`.

### Example 29: message class and special message

```toml
[acquisition.microsoft.outlook.mail.rules.conditions]
is_meeting_request = true
item_class_exact = ["IPM.Schedule.Meeting.Request"]
```

The two fields are AND. Either could also be used independently.

### Example 30: multiple ordered rules

```toml
[[acquisition.microsoft.outlook.mail.rules]]
id = "manager"
sequence = 10
profile = "full"

[acquisition.microsoft.outlook.mail.rules.conditions]
from_addresses = ["manager@example.test"]

[[acquisition.microsoft.outlook.mail.rules]]
id = "invoices"
sequence = 20
profile = "full"

[acquisition.microsoft.outlook.mail.rules.conditions]
subject_contains = ["invoice"]
```

### Example 31: stop processing

```toml
[[acquisition.microsoft.outlook.mail.rules]]
id = "newsletter"
sequence = 10
profile = "discovery"
stop_processing = true

[acquisition.microsoft.outlook.mail.rules.conditions]
from_address_regex = ['@newsletter\.example\.test$']
```

A matching newsletter prevents later rules from running.

### Example 32: monotonic Full upgrade

```toml
[[acquisition.microsoft.outlook.mail.rules]]
id = "ordinary"
sequence = 10
profile = "discovery"

[acquisition.microsoft.outlook.mail.rules.conditions]
subject_contains = ["report"]

[[acquisition.microsoft.outlook.mail.rules]]
id = "important"
sequence = 20
profile = "full"

[acquisition.microsoft.outlook.mail.rules.conditions]
importance = ["high"]
```

A message matching both ends at `full`.

### Example 33: later discovery cannot downgrade Full

```toml
[[acquisition.microsoft.outlook.mail.rules]]
id = "full-first"
sequence = 10
profile = "full"

[acquisition.microsoft.outlook.mail.rules.conditions]
subject_contains = ["approval"]

[[acquisition.microsoft.outlook.mail.rules]]
id = "discovery-later"
sequence = 20
profile = "discovery"

[acquisition.microsoft.outlook.mail.rules.conditions]
categories = ["archive"]
```

If both match, the final profile is still `full`.

### Example 34: disabled individual rule

```toml
[[acquisition.microsoft.outlook.mail.rules]]
id = "paused-01"
sequence = 10
enabled = false
profile = "full"

[acquisition.microsoft.outlook.mail.rules.conditions]
subject_contains = ["approval"]
```

The rule does not evaluate, but its configuration must still be valid.

### Example 35: enabled policy with no rules

```toml
[acquisition.microsoft.outlook.mail]
enabled = true
default_profile = "discovery"
```

This intentionally keeps all newly evaluated messages at discovery depth.

### Example 36: globally disabled policy

```toml
[acquisition.microsoft.outlook.mail]
enabled = false
```

This preserves the existing no-rules acquisition workflow.

### Example 37: invalid profile

```toml
[acquisition.microsoft.outlook.mail]
enabled = true
default_profile = "deep"
```

`msgloom config validate` rejects this; supported values are `discovery` and
`full`.

### Example 38: duplicate sequence is invalid

```toml
[[acquisition.microsoft.outlook.mail.rules]]
id = "one"
sequence = 10
profile = "full"
conditions = { subject_contains = ["one"] }

[[acquisition.microsoft.outlook.mail.rules]]
id = "two"
sequence = 10
profile = "full"
conditions = { subject_contains = ["two"] }
```

Use unique sequence values; msgloom does not hide a second tie-breaker.

### Example 39: unsupported RE2 syntax

```toml
[acquisition.microsoft.outlook.mail.rules.conditions]
subject_regex = ['(?=approval)']
```

Look-ahead is rejected by `msgloom-regex-v1`. Backreferences and look-behind are
also unsupported.

### Example 40: case-insensitive behavior

```toml
[acquisition.microsoft.outlook.mail.rules.conditions]
subject_contains = ["URGENT"]
from_addresses = ["Manager@Example.Test"]
```

These ordinary literals match regardless of case under the documented
case-folding contract.

### Example 41: anchors for full-field regex intent

```toml
[acquisition.microsoft.outlook.mail.rules.conditions]
subject_regex = ['^invoice$']
```

Without anchors, regex uses search semantics and can match a substring.

### Example 42: `bodyPreview` is not a complete body

```toml
[acquisition.microsoft.outlook.mail.rules.conditions]
body_contains = ["approval token"]
```

Even if `bodyPreview` happens to contain or omit the term, V1 does not use the
preview as terminal BODY truth. The complete logical body is the matching
surface.

### Example 43: one composite probe satisfies several predicates

```toml
[acquisition.microsoft.outlook.mail.rules.conditions]
body_contains = ["approval"]
header_contains = ["X-Workflow: production"]
sensitivity = ["private"]
```

If all three facts remain relevant, msgloom asks for them in one bounded
provider probe rather than chaining BODY then headers then sensitivity requests.

### Example 44: source changes during probe

A message is first observed with Graph `changeKey=A`. If the rule probe returns
`changeKey=B`, msgloom does not combine facts from two versions. The result is
unresolved and falls back to `full`.

### Example 45: provider fact unavailable

Suppose a rule depends on `sensitivity`, but the requested extended property is
not available. If another cheap condition already proves the rule false, no
fallback is needed. If sensitivity can still change the final decision after the
one probe, the message falls back to `full`.

### Example 46: regex runtime/resource failure

Invalid regex syntax is rejected at config load. If the bounded RE2 runtime
fails while evaluating an otherwise-relevant valid pattern, msgloom treats the
relevant truth as unresolved and falls back to `full`; it never switches to a
second regex engine.

### Example 47: programming failure is not source uncertainty

An impossible internal state, wrong evaluator return type, or a second
`NEEDS_DATA` after the one probe marks the logical run failed. These are not
converted into a normal Full fallback because doing so would hide a software
integrity defect.

### Example 48: Full work fails before delta commit

With active rules, the message delta cursor is validated but held. If a
rule-selected Full target does not reach current-attempt Full-v1 terminal
completeness, the prior committed cursor stays authoritative so the next sync can
replay and reevaluate that change.

### Example 49: policy changes are not retroactive in V1

If a January message was discovery-only and the policy changes in March, msgloom
does not automatically scan that unchanged historical message. If the message is
observed again later, the March policy applies then.

### Example 50: explicit Full override

```text
scrapy microsoft outlook mail full MESSAGE_ID
```

This explicit operator action requests Full-v1 regardless of Mail rules. It does
not accept `--config` for Mail policy.

### Example 51: discovery evaluates but does not complete Full work

```text
scrapy microsoft outlook mail discover
```

With active rules, discovery observations can produce policy decisions and rule
probes, but this command does not launch the selected Full targets. Use `sync`
for policy-completing acquisition.

### Example 52: standalone delta is rejected with active rules

```text
scrapy microsoft outlook mail delta
```

If the selected universal config enables Mail rules, the command fails before
crawl startup and directs the operator to `mail sync`. This prevents advancing a
cursor while losing attempt-local Full obligations.

### Example 53: `--max-enrich` is rejected with active rules

```text
scrapy microsoft outlook mail sync --max-enrich 10
```

This is valid only for the legacy rules-disabled backlog path. With active rules
it is rejected because selected Full obligations are not durably queued and must
not be truncated.

### Example 54: a discovery result can still have probe evidence

Compare these two policies:

```toml
# Cheap metadata-only rule
[acquisition.microsoft.outlook.mail.rules.conditions]
subject_contains = ["newsletter"]
```

```toml
# Content-backed rule
[acquisition.microsoft.outlook.mail.rules.conditions]
body_contains = ["newsletter"]
```

Either rule can ultimately leave a message at `discovery`, but the second can
persist a BODY rule-probe response as raw evidence. `discovery` describes the
selected acquisition profile, not an assertion that no content was fetched while
making the decision.

## Privacy and observability

Rule values never enter Scrapy settings. Scrapy can log overridden settings, so
raw policy values are intentionally kept in the separate msgloom configuration
plane.

The effective policy digest is private control state used for JOBDIR resume
integrity. It is not printed in logs, stats, `config inspect`, Items, or user
errors. A content-derived hash would otherwise permit dictionary guesses of
low-entropy email addresses/keywords.

Decision logs may contain:

- fixed policy-family ID;
- opaque run/message correlation IDs;
- non-secret bounded rule IDs;
- selected profile/outcome;
- stop/probe/fallback flags;
- bounded fixed reason/error tokens.

They must not contain configured match values, subjects, bodies, addresses,
headers, regex strings, provider URLs, tokens, or arbitrary exception text.

## JOBDIR resume safety

Mail collection JOBDIR state binds the effective private Mail policy identity in
an owner-only marker. Reusing a JOBDIR with different rule semantics is refused
before the Scheduler can load queued requests.

Source/catalog context is checked first; Mail policy context is checked next.
This prevents a queued request created under one source or policy from executing
under another.

## Real Graph qualification notes

The production V1 composite probe was qualified against real Microsoft Graph
using only the existing Mail read scope. One message GET returned the required
BODY, internet headers, sensitivity, message size, message class, and `changeKey`
facts together.

A real `eventMessageRequest` was also qualified. On 2026-10-02 Graph honored the
text-body preference used by the production probe even though Microsoft's public
v1.0 eventMessage documentation still describes event-message GET bodies as
HTML-only. A separate qualification-only GET without the body-format preference
returned HTML for the same kind of real event message, and the deterministic
HTML-to-logical-text path succeeded. Production therefore accepts both text and
HTML provider representations; the extra HTML read belongs only to the
qualification harness and is not a second RuleEngine probe.
