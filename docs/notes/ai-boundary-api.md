# Phase 1 AI boundary API

## Scope

msgloom.ai owns one transport-level analysis attempt. It does not define
triage semantics, validate triage@1, select source records, mutate shared
registries, or persist an accepted semantic result.

The public entry point is AIRunner.run(attempt, trace_sink). AnalysisAttempt is
immutable and binds an AttemptIdentity to exact input, working-context,
prompt, output-schema, and model VersionRef values. Supplied input, context,
and prompt text is byte-bounded before process creation. AttemptLimits
contains the exact elapsed timeout, input, context, prompt, output, trace,
turn, and task-token bounds. Timeout and termination grace values must be
finite and positive. There are no implicit production defaults.

The request carries only schema and model references. TrustedPolicy maps those
references to the JSON schema and model identifier. Message text and transport
callers therefore cannot add a CLI flag, choose a schema, select a model, or
enable a tool.

AnalysisResponse is transport output only. A complete response contains a
bounded JSON object and is merely eligible for later parent semantic
validation. Missing, malformed, incomplete, oversized, timed-out, SDK-error,
trace-persistence, nonzero-exit, or disabled-tool output remains failed or
timed out. This layer never manufactures a Low-value or other triage result.

## Composition sequence

The trusted application composes an attempt in this order:

1. Save or select exact prepared input and working-context versions.
2. Select a trusted prompt, output-schema, and model reference.
3. Construct AnalysisAttempt with supplied bounded text and exact limits.
4. Construct TrustedPolicy from application-owned schema/model mappings.
5. Construct RuntimeIsolation from a qualified Python executable, Claude CLI,
   Bubblewrap, exact read-only runtime/package roots, application-owned
   storage root, and explicitly supplied Bedrock values.
6. Await AIRunner.run() with a durable TraceSink.
7. Persist and inspect the returned transport response.
8. Only then may the parent triage layer validate semantic contracts and
   decide whether a semantic result is acceptable.

Every exposed SDK trace event accepted by the sink is awaited before output can
be eligible. A failed sink fails the attempt and preserves the exact count and
sequence of earlier durable events. No global trace codec or registry entry is
installed.

## SDK 0.2.161 controls

The pinned claude-agent-sdk 0.2.161 source and subprocess transport were
inspected. The transport merges os.environ into the Claude CLI environment.
The boundary therefore starts a dedicated worker with an exact environment
instead of overlaying a safe mapping on the manager environment.

The worker constructs ClaudeAgentOptions with:

- tools=[] and allowed_tools=[];
- setting_sources=[], skills=[], and plugins=[];
- mcp_servers={} plus strict_mcp_config=True;
- no hooks, agents, added directories, file checkpointing, resume, continue,
  session id, fallback model, or extra CLI arguments;
- permission_mode=dontAsk;
- the trusted model, trusted JSON schema, maximum turns, and task-token budget;
- isolated /work as cwd and the trusted absolute bundled CLI path.

For this SDK version, tools=[] emits an empty --tools value. Empty
allowed_tools alone does not disable the default base tool set.
setting_sources=[] emits an empty setting-sources declaration. Tests inspect
the SDK-generated argv so these controls are not prompt-only claims.

The child environment contains only isolated HOME/XDG/TMP locations, a fixed
minimal PATH, PYTHONNOUSERSITE, and explicitly supplied values from the closed
Bedrock allowlist. The runner never reads credential values from the host
environment and never logs them. Source-provider credentials are rejected.

## Exposed evidence and IPC

The worker retains the public SDK evidence needed by the Phase 1 architecture.
Closed trace kinds cover assistant text, exposed ThinkingBlock data, tool
use/result blocks, system messages, result messages, and runner diagnostics.
Assistant metadata includes model, error, usage, message/session identifiers,
stop reason, and UUID where exposed. Every SystemMessage.data JSON value is
retained. Result evidence includes structured output, usage/model usage, cost,
durations, turns, session, stop/terminal reason, result text, permission
denials, deferred tool metadata, errors, API status, UUID, and origin where the
public SDK exposes them.

The representation accepts only finite JSON values with string object keys and
bounded nesting. It does not serialize arbitrary Python objects or undocumented
SDK internals. A tool event remains visible in the durable trace, but any tool
use/result event fails the attempt because Phase 1 tools are disabled.

Parent IPC is bounded line-oriented JSON. Duplicate fields, unknown fields,
wrong types, non-finite numbers, unknown event/failure kinds, multiple terminal
events, and events after a terminal event fail closed. A success-shaped
terminal event is still rejected if the worker exits nonzero. Raw child stderr
is never retained; only its bounded byte count can become a diagnostic.
Diagnostics consume the same event-count and event-byte budgets as SDK traces.

## Host and lifecycle isolation

Bubblewrap is mandatory and absence fails closed. Each attempt receives a fresh
namespace with /proc, /dev, isolated /tmp, and only configured runtime/package
roots mounted read-only. The worker source is mounted read-only. Host home,
project, authentication stores, Claude settings, plugins, MCP configuration,
and daily sessions are not implicitly mounted.

For a new attempt identity, the runner creates a SHA-256-named directory under
the application-owned storage root with separate state and work directories.
Only those directories are writable as /state and /work. Reusing an attempt
identity fails closed because its directory already exists. Attempt directories
remain after every terminal state for parent inspection; the runner never
resumes them.

One monotonic elapsed deadline begins before accepted storage work and process
startup. It covers storage, spawn acceptance, initial stdin write/drain/close,
stdout/stderr/exit, trace persistence eligibility, and process ownership.
Timeout or cancellation prevents result acceptance. Accepted storage, spawn,
durable trace writes, termination, pipe draining, and reaping are nevertheless
finished after the elapsed deadline when necessary so no accepted work remains
in the background.

Cleanup targets the process group even when its leader has already exited.
This prevents descendants holding inherited pipes from deadlocking completion.
SIGTERM is followed by the configured grace and SIGKILL when required.
Repeated cancellation cannot interrupt accepted durable writes or cleanup.
Parent diagnostic writes also remain inside the output-acceptance deadline.
Cleanup errors propagate after the other accepted tasks drain; they cannot
silently permit successful output.

Network isolation remains distinct from tool isolation: Bubblewrap shares the
network namespace so a later qualified model transport can reach its configured
service. No source-discovery, web, shell, file-editing, or report tool is
enabled.

## Qualification status

All lane tests use synthetic inputs. No paid/model request, model credential,
Microsoft access, source credential, daily Claude session, or personal data was
read or written.

Offline runtime assembly was exercised inside the real Bubblewrap namespace
with Python 3.12.14, 3.13.5, and 3.14.7 qualification environments. Each
isolated worker imported the installed pinned SDK and executed the bundled
Claude CLI --version successfully. The portable lane test qualifies the
interpreter that runs it by deriving its prefix, site-packages path,
executable,
and bundled CLI from that runtime. An explicit
MSGLOOM_AI_QUALIFICATION_RUNTIMES path list makes every supplied interpreter a
required test parameter; missing or broken configured runtimes fail rather than
skip. The test also verifies isolated HOME, absence of an inherited synthetic
source secret, and invisibility of an unmounted synthetic host-session
sentinel. This is runtime/import/CLI availability qualification only.

Remaining deployment acceptance includes the real Bedrock/model network path,
TLS/DNS mounts, credential delivery, actual structured-output behavior, and
cancellation/descendant behavior under a real SDK/CLI model session. The
manager owns that live acceptance and semantic triage validation.

The attempt timeout is not a hard upper bound on return time after work has
been accepted: durable sinks, accepted storage/spawn operations, and cleanup
must drain even past it. A permanently stuck external durable sink or operating
system operation therefore has no second destructive wall-clock cutoff here.
Bubblewrap also does not impose CPU or memory cgroup limits in this lane.
Deployment must provide any required outer resource limits.
