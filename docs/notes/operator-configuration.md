# Operator configuration

## Scope

The msgloom.configuration package is the closed Phase 1 operator-configuration
boundary. It loads one explicitly named TOML file and produces immutable
configuration data for later CLI composition. It does not construct
Application, stage handlers, source adapters, parsers, AI runners, Graph
clients, or report transports.

Recurring schedules and external triggers are intentionally absent. A4, A6,
and A7 are rejected by the configuration/admission boundary before a factory
can be selected.

## Settings sources and precedence

The loader uses the pinned pydantic-settings 2.15.0 custom-source API.
OperatorSettings.settings_customise_sources defines this exact precedence,
highest first:

1. explicit approved command_options;
2. environment variables under MSGLOOM_CONFIG__;
3. files in the explicitly supplied mounted settings/secret directory;
4. the explicitly supplied TOML file;
5. technical model defaults.

The dotenv source is omitted and _env_file=None is forced. There is no
implicit .env discovery, remote configuration, dynamic import, or expression
evaluation.

The TOML file is bounded to 256 KiB. Consumed mounted settings files are
bounded to 64 KiB. Environment values under the configuration prefix are
bounded to 64 KiB. Unknown top-level command/environment settings, unknown
nested model fields, duplicate TOML keys, duplicate admission/binding
identities, and inconsistent credential-purpose references fail with fixed
privacy-safe errors.

Mounted settings files use the top-level field name, for example
code_version; they do not use the environment prefix. Credential files may
share the directory but are not read during configuration loading.

Relative paths are resolved against the directory containing the explicit
TOML file. The configuration snapshot never displays those paths.

## Public API

The stable loader signature is:

~~~python
load_operator_configuration(
    config_file: Path,
    *,
    command_options: Mapping[str, object] | None = None,
    mounted_secret_dir: Path | None = None,
) -> OperatorConfiguration
~~~

OperatorConfiguration exposes:

~~~text
.version -> str
.code_version -> str
.database_url -> str
.admissions -> tuple[TrustedAdmission, ...]
.snapshot() -> ConfigurationSnapshot
.source_reader_config() -> SavedSourceReaderConfig
.operation(capability: PhaseCapability) -> OperationData
.secret_binding(binding_id: str) -> SecretBinding
~~~

operation() returns one of these immutable types:

~~~text
PreparationOperationData
TriageOperationData
ReportOperationData
ReportSubmitOperationData
~~~

PreparationOperationData.plan(...) constructs the reviewed PreparationPlan
from exact caller-supplied SelectionPlan values.

TriageOperationData.producer_config(...) constructs the reviewed
TriageProducerConfig from an exact caller-supplied TriageReplayPlan.
TriageOperationData.runtime_isolation(credentials) constructs only the
reviewed RuntimeIsolation; callers resolve credentials explicitly first.

ReportOperationData.handler_config(...) constructs the reviewed
ReportHandlerConfig from exact per-run identities. Report selection remains
an exact caller-supplied ReportSelectionPlan to ReportBuildHandler.

ReportSubmitOperationData contains only the trusted transport reference,
report policy reference, and report-purpose secret binding IDs. The manager's
delivery/CLI integration owns transport construction.

Unavailable or unsupported capability access raises ConfigurationError with
ConfigurationErrorCode.CONFIG_UNAVAILABLE.

## Phase 1 composition

The root configuration requires code_version, storage, and at least one
trusted admission. storage.sqlite_path is the Phase 1 persistence path.
Admissions are exact caller/authority/capability bindings and accept only
A2 prepare, A3 triage, A5 report build, and A5 report submit.

source names the saved A1 catalog, bounded evidence roots, source-reader
limits, and optional source-purpose credential references. It is converted
through SavedSourceReaderConfig validation. A2 becomes available only when
both source and preparation are configured.

preparation requires the reviewed FilterConfig and parser profiles. Parser
identity/profile/limits are validated through the reviewed ParserProfile and
parser dataclasses. Reusable A2 byte/count/time ceilings are operator
settings; exact source selections and replay references remain
per-invocation data.

triage requires the reviewed filter and triage-rule configuration, triage
input choices, working-context allowlist, prompt/model/schema selections,
attempt limits, isolated-runtime paths, A3 aggregate budgets, and at least
one AI-purpose credential reference. The configuration version is injected
as the exact TriageInputConfig.version and
TrustedInputVersions.configuration value. That reference has kind
`triage_input_config`, identity `phase1`, and the redacted snapshot
version, which is the kind the reviewed A3 producer requires.

The prompt file is read by load_operator_configuration as bounded UTF-8 text
(64 KiB maximum). The JSON output-schema file is read by the same loader with
duplicate-key rejection and a 256 KiB maximum, then passed through
TrustedPolicy. Prompt/schema content is represented in inspection only by
content digests.

Working-context files are not read by configuration loading.
WorkingContextConfig contains only explicit selected files and allowed roots;
the reviewed working-context capture component reads those files later during
A3 execution.

report requires the reviewed ReportPolicy, including explicit owner and
destination identities, due criteria, timezone, priorities, repeat/reminder
choices, plus reviewed RendererConfig and finite build budgets. There are no
owner/destination business defaults. Report build is available without a
transport. Report submit is available only when an explicit transport
reference and report-purpose credential references are present.

R1 deliberately does not invent a file codec for exact preparation, triage,
or report-selection plans because no reviewed plan-file codec exists in the
baseline. The later CLI supplies those exact typed plans directly. If a
reviewed bounded plan codec is added, a future configuration revision may
add explicit plan-file references without changing the current semantics.

## Scheduled preparation

`msgloom prepare-scheduled` runs one finite A2 intake and preparation cycle.
It reads saved A1 data and does not start collection or install a scheduler.
Configure the existing `source`, `preparation.filter_config`, parser profiles,
storage, and trusted `a2_prepare` admission first. Add targets to the same
operator TOML document; this fragment is not a complete configuration:

~~~toml
[[preparation.intake_targets]]
expected_catalog = { catalog_identity = "trusted-catalog-id", schema_version = 1 }
source_id = "configured-a1-source"
stream = "outlook_mail"
consumer_id = "daily-preparation"
max_entries = 100
max_pending_worksets = 10
~~~

`expected_catalog` is mandatory trusted operator configuration. Copy the identity
from the intended catalog or a known saved cursor during explicit setup or
reconciliation. Never populate it automatically from the current file at startup.
A mismatch fails before pending replay, claims, or fresh source admission.
An explicit approved baseline needs a matching pin for subsequent scheduling;
a mismatch does not authorize baseline creation. All target fields affect the
configuration version, so reload invocation versions after changing them.

`source_id` must match the saved A1 source binding. Supported streams are
`outlook_mail`, `outlook_calendar`, `todo`, `contacts`, and `onedrive`. Keep
`consumer_id` stable across scheduled runs and retries. It identifies cursor
progress within the catalog/source/stream scope. A new consumer ID creates a
separate intake scope; it is not a recovery command for the existing scope.

At most 32 targets are accepted. Each source/stream/consumer tuple must be
unique. `max_entries` defaults to 100 and permits 1 through 1000; it must not
exceed `preparation.max_records`. `max_pending_worksets` defaults to 10 and
permits 1 through 100. These are entry-admission and workset-attempt limits,
not a promise to drain the backlog in one invocation. A failed pending attempt
consumes a work unit. Durable rotation allows other pending work to progress.
Each target still gets one bounded fresh intake after pending processing.

The existing execution timeout and claim lease apply to bounded operations.
The claim lease must exceed the execution timeout by more than one second.
Each target and workset is awaited sequentially. The complete multi-target
invocation can take longer than one operation timeout; allow time for all
configured bounds and cleanup in the external scheduler's process deadline.

Inspect the effective configuration version before creating an invocation:

~~~console
msgloom config inspect --config operator.toml
~~~

Write a bounded JSON invocation file. Replace the configuration version with
the returned value and use the caller/authority pair from the trusted
admission. Give each later scheduled invocation or retry a new execution and
attempt identity. Retain the same target `consumer_id` in configuration.

~~~json
{
  "schema_version": "1",
  "configuration_version": "REPLACE_WITH_INSPECTED_VERSION",
  "execution": "scheduled-2026-10-07-001",
  "attempt": "scheduled-2026-10-07-001-attempt-1",
  "caller": "operator-cli",
  "authority_ref": "owner-approved"
}
~~~

Run the command with two positional file paths:

~~~console
msgloom prepare-scheduled operator.toml scheduled-invocation.json
msgloom status operator.toml scheduled-2026-10-07-001
~~~

The scheduled envelope accepts no source selections, mode, or nonempty
parameters. Configuration version and trusted PREPARE admission are checked
before source intake. An empty target list is a finite no-work operation.
The command returns result references and limitation codes. Exit 0 means
`complete`; exit 3 means `blocked`; other terminal outcomes, including
`incomplete`, use exit 4. Input/configuration failures use exit 2.
`scheduled-work-pending` reports work that remains pending or a failed intake;
`scheduled-preparation-incomplete` reports accepted preparation with incomplete
output. Read the saved outcome and limitations before deciding the next run.

### Scheduled recovery boundary

Intake freezes a release cutoff and saves immutable selections. The cursor,
workset, and pending index commit together. Cursor progress means admission;
it does not mean parsing succeeded. New A1 entries after the cutoff wait for
a later intake. A retry after preparation failure finds the existing pending
workset and replays its saved selections without rewinding the cursor.
Completion requires exact accepted preparation receipts. Scoped removals and
context changes retain their scope in accepted `prepared_transitions` results.

Missing or corrupt evidence creates a held entry disposition. This permits
later valid entries to progress but does not claim the held content was
prepared. Retain the workset and evidence for operator inspection. Within an
existing catalog scope, intake rejects catalog identity or cursor-anchor
mismatch. A different catalog identity at the start of a new scheduled
invocation selects another scope, without comparison to the old cursor.
Restore consistent catalog, Phase 1 store, and evidence state together; do
not rely on catalog replacement to recover an existing scope. Do not reset
or edit the cursor to bypass anchor checks. This command has no automatic
reconciliation or historical-baseline option.

Future-only intake does not admit unchanged pre-ledger historical records.
Manual `prepare` and explicit preparation replay keep their existing
exact-selection contracts. See the
[collection/preparation boundary](../phase-1/architecture.md#durable-incremental-handoff).
Final handoff qualification and independent acceptance remain pending.

### Explicit historical baseline

`HistoricalBaselineService.run` is an async service API, not a CLI option.
The caller supplies an `IntakeScope`, a `sources` tuple of 1 to 1024 unique
exact `VersionRef` values, and a nonblank `approval_id`. The caller owns the
approval decision; the service records that identifier. It also requires
execution and attempt identities, `configuration_version`, and `code_version`.
The caller owns the reader and persistence lifetimes.

Use a new consumer scope with no prior workset and no advanced cursor. The
service rejects an initialized scope, even after its baseline has completed.
Each selected version must belong to the approved source and stream. The
service does not discover history, expand a timestamp range, or manufacture
release entries. Calendar input identifies an exact saved event observation;
`a1_released_source` input resolves an exact immutable acquisition fact without
expanding mutable full-profile projections. Other supported versions use the
existing exact-selection reader. Unavailable or invalid evidence and versions
outside the approved scope fail admission. Source-reader byte and query limits
still apply.

Before reading the approved evidence, the service captures the current release
anchor for that source and stream, or genesis if no release exists. With saved
evidence verified, it saves exact selections before atomically committing one
immutable starting workset, its pending state, and the cursor. The workset
records the approval identifier, exact versions, saved selection references,
and cutoff. Later incremental intake starts after that cutoff. Releases at
or below the cutoff are not separately admitted by later intake; the explicit
version list defines the baseline content. Releases after the cutoff remain
future work.

A failure before atomic admission may leave reusable exact selections but no
workset or cursor progress. A new attempt captures the then-current cutoff;
it does not preserve a failed attempt's cutoff. After successful admission,
retry preparation from the saved pending workset through scheduled preparation.
Do not rerun baseline admission or change its immutable input. Baseline support
is integrated; final handoff gates and independent acceptance remain pending.

## Secrets

SecretBinding stores only:

~~~text
binding_id
purpose = source | ai | report
logical_name
source = environment | mounted-file
locator
~~~

No credential value is accepted by the configuration model. Source, AI, and
report references cannot be substituted across purposes. AI logical names
are restricted to the credential environment accepted by the reviewed AI
runtime contract.

Configuration loading and snapshot() never resolve a credential. Execution
must explicitly create a SecretResolver:

~~~python
SecretResolver(
    *,
    allowed_environment: Set[str],
    allowed_files: Set[str],
    mounted_secret_dir: Path | None,
    environ: Mapping[str, str] | None = None,
)
~~~

SecretResolver.resolve(binding) returns a Pydantic SecretStr. Resolution is
whitelist-based and bounded to 16 KiB. Mounted files are opened without
following a final symlink. Failures expose only fixed safe classifications,
not locators, paths, values, or arbitrary exception text.

The resolver whitelist is execution-owned. This prevents a TOML-provided
locator from granting itself access to an arbitrary process environment
variable or mounted file.

## Redacted snapshot and version

ConfigurationSnapshot is a frozen pair of version and canonical JSON payload.
The payload retains safe structural choices and finite budgets. Private
identities, source/evidence/runtime paths, credential binding details, report
policy/destination data, filter/rule semantics, model selection, and
working-context selection are represented by deterministic SHA-256 digests.
Prompt/schema files contribute content digests.

The configuration version is SHA-256 over that canonical redacted payload.
Therefore a configuration change, including a private path, destination,
prompt/schema content, rule/policy choice, or budget, produces a different
version without making the private value inspectable.

## Minimal example

~~~toml
code_version = "build-2026-09-29"

[storage]
sqlite_path = "state/phase1.sqlite3"

[[admissions]]
caller = "operator-cli"
authority_ref = "owner-approved"
capabilities = ["a2_prepare"]
~~~

This configuration is valid for inspection but A2 remains unavailable until
both source and preparation are explicitly configured. No fake adapter or
credential is substituted.

Environment override example:

~~~text
MSGLOOM_CONFIG__CODE_VERSION=build-override
~~~

A command option mapping containing code_version=build-command overrides that
environment value. A mounted settings file named code_version overrides TOML
but remains below environment and command options.

## R2 validation and file-boundary hardening

Configuration inspection now rejects reusable settings that the reviewed
execution contracts cannot use: A2 lease/operation and derived aggregate
relationships, A3 attempt/cleanup/operation/lease relationships, and A5 build
timeout/lease relationships are enforced before OperatorConfiguration is
returned. A2 parser profiles must match the exact production registry identity
for their format and the reviewed production profile/settings contract; this
validation does not start a parser.

Environment preflight follows pydantic-settings' case-insensitive
MSGLOOM_CONFIG__ matching. Unknown recognized-prefix names, case aliases,
overlapping whole/nested settings, and oversized values fail with fixed safe
configuration errors before source composition.

The explicit TOML and consumed mounted settings are read once through bounded,
nonblocking, no-follow descriptors and then supplied to pydantic-settings as
in-memory custom mapping sources. Prompt and schema files use the same
nonblocking/no-follow descriptor validation after relative path resolution
without dereferencing the final object. Secret resolution opens both the
mounted root and leaf without following symlinks and adds a nonblocking leaf
open, so FIFOs and other nonregular files are rejected before any read.
Inspection still never resolves credential files or environment values.

OperatorConfiguration.database_url uses SQLite file-URI mode with the
filesystem path percent-encoded before the controlled uri=true query option.
Reserved filename characters such as question marks therefore remain part of
the exact configured database filename rather than becoming URL query syntax.
