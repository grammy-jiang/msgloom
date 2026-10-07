# Application CLI

## Scope

The installed msgloom command is a finite Phase 1 operator surface. It owns
one synchronous entry point, msgloom.cli.main, and that entry point owns the
only asyncio.run call. The awaited API does not create or nest an event loop.

The command surface is:

- msgloom config inspect CONFIG
- msgloom config validate CONFIG
- msgloom status CONFIG EXECUTION
- msgloom prepare CONFIG INVOCATION
- msgloom triage CONFIG INVOCATION
- msgloom report build CONFIG INVOCATION
- msgloom report submit CONFIG INVOCATION
- msgloom report reconcile CONFIG INVOCATION
- msgloom replay STAGE CONFIG INVOCATION

STAGE is closed to prepare, triage, and report-build. There is no scheduler,
crawl-all mode, MCP command, web server, UI, or later-phase action command.
Microsoft collection and authentication remain in the existing
provider-specific Scrapy command surface, for example scrapy microsoft ....
The application CLI never starts or nests a Scrapy reactor.

The package metadata exposes exactly:

    [project.scripts]
    msgloom = "msgloom.cli:main"

## Awaited API

Code already running inside an event loop uses these signatures:

    async def execute_invocation(
        configuration: OperatorConfiguration,
        invocation: PrepareInvocation
        | TriageInvocation
        | ReportBuildInvocation
        | ReportSubmitInvocation,
        *,
        options: ExecutionOptions = ...,
        dependencies: CompositionDependencies = ...,
    ) -> OperationOutcome: ...

    async def reconcile_invocation(
        configuration: OperatorConfiguration,
        invocation: ReportReconcileInvocation,
        *,
        options: ExecutionOptions = ...,
        dependencies: CompositionDependencies = ...,
    ) -> ReconciliationResult: ...

    async def load_and_execute(
        config_file: Path,
        invocation: PrepareInvocation
        | TriageInvocation
        | ReportBuildInvocation
        | ReportSubmitInvocation,
        *,
        mounted_secret_dir: Path | None = None,
        allowed_secret_environment: frozenset[str] = frozenset(),
        allowed_secret_files: frozenset[str] = frozenset(),
        dependencies: CompositionDependencies = ...,
    ) -> OperationOutcome: ...

    async def run_request(
        request: CliRequest,
        *,
        dependencies: CompositionDependencies = ...,
    ) -> CliResult: ...

CompositionDependencies is a Python composition seam for tests and trusted
embedding only. Cyclopts exposes no factory, fake-runner, or fake-transport
option.

## Invocation files

Invocation files are UTF-8 JSON, bounded to 2 MiB, duplicate-key rejecting,
and closed against unknown fields. The CLI reads each file through one
non-blocking descriptor that does not follow a final symlink and accepts only
a regular file, so a FIFO, device, or swapped path fails with
`invocation_unavailable` instead of blocking. Every execution file binds schema version
1, the exact redacted operator configuration version, execution identity,
attempt identity, caller, authority reference, and the stage-specific plan.

A minimal live preparation file is:

    {
      "schema_version": "1",
      "configuration_version": "CONFIG_DIGEST",
      "execution": "prepare-20260929-001",
      "attempt": "prepare-attempt-001",
      "caller": "operator-cli",
      "authority_ref": "owner-approved",
      "parameters": [],
      "mode": "live",
      "selections": [
        {
          "source": {
            "kind": "outlook_email",
            "identity": "synthetic-source/message",
            "version": "obs-current"
          },
          "replay_result": null,
          "replay_selection": null
        }
      ]
    }

A preparation replay uses the same envelope, changes mode to replay, and
supplies the exact saved replay_result and replay_selection required by
SelectionPlan. A triage replay must carry a TriageReplayPlan whose mode is
replay. Report-build replay uses exact saved triage inputs and new report,
selection-result, and semantic-data identities. Replay never implies submit.

Submission and reconciliation plan objects are reconstructed through the
reviewed delivery codecs after the CLI envelope is validated. Reconciliation
requires the exact retained claim token and durable provider evidence required
by ReportReconciliationPlan. It invokes ReportReconciler directly and does not
construct a transport.

## Trusted construction

Configuration owns source-reader bounds, parser profiles, filter and grouping
rules, model and schema references, report policy, owner destination, transport
reference, credential references, and reusable operation budgets. Invocation
content cannot replace those values.

A2 constructs SavedSourceReader and PreparationHandler only after the
invocation and configuration version pass admission. A3 resolves only the
configured AI-purpose bindings, then constructs a fresh RuntimeIsolation,
runner, and TriageHandler. Report build constructs ReportBuildHandler with
DeliveryReportHistoryResolver.

Report submission first matches the plan policy, owner, and destination to the
trusted report configuration. The default user-facing CLI has no provider
guessing rule. The stable configuration API supplies a transport reference but
does not encode enough Graph endpoint and sender semantics to safely invent a
Graph HTTP transport. Without a trusted transport factory, submission is a
saved blocked outcome with no external effect. A trusted embedding can provide
a ReportTransportFactory; report-purpose credentials are resolved only after
Application admission and immediately before that factory is called.

This preserves the Graph write-scope gate. No new Graph scopes, token cache
access, redirects, retries, or automatic send behavior are introduced here.

## Status and output

status does not initialize Phase1Persistence. It resolves the configured SQLite
file, requires it to exist, opens it with SQLite mode=ro, requires schema
version 3, and reads one exact saved terminal execution. A missing or older
database is not created or migrated.

Machine output is one compact JSON object. Terminal operation output contains
only execution identity, capability, terminal status, result references,
limitation codes, failure codes, and external-effect state. It does not emit
business text, source names, paths, destination addresses, credentials, or raw
exception text.

Exit code 0 means a complete operation or successful read/reconciliation. Exit
code 2 is invalid or unavailable operator input. Exit code 3 is a saved blocked
operation. Exit code 4 is a failed, incomplete, cancelled, or unavailable
operation. Keyboard interruption returns 130 after awaited cleanup and terminal
persistence have had their normal drain path.

## Synthetic operator sequence

The following sequence is scheduler-free and performs no provider collection:

    msgloom config validate operator.toml
    msgloom config inspect operator.toml
    msgloom status operator.toml previous-execution
    msgloom prepare operator.toml prepare.json
    msgloom triage operator.toml triage.json \
      --allow-secret-environment SYNTHETIC_AI_REGION
    msgloom report build operator.toml report-build.json
    msgloom report submit operator.toml report-submit.json
    msgloom report reconcile operator.toml report-reconcile.json
    msgloom replay triage operator.toml triage-replay.json \
      --allow-secret-environment SYNTHETIC_AI_REGION

Real AI execution requires explicitly approved AI credential locations. Real
report submission additionally requires a trusted report transport composition.
Neither missing capability is converted into synthetic success.
