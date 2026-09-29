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
TrustedInputVersions.configuration value.

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
