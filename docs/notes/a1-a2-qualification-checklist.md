# A1-to-A2 qualification preparation checklist

Status: preparation only. Final Task15 gates have not been executed here.
This file does not mark the design implemented, accept another shard, or
replace the manager's integration and independent review.

Authority: the complete committed handoff design and implementation plan,
Task15 and its 13 scenarios; Task10 supplies the real Scrapy coverage matrix.
Repository commands come from `pyproject.toml`, `AGENTS.md`,
`docs/component-layout.md`, and `.pre-commit-config.yaml`. No CI workflow is
tracked at the preparation base.

## Candidate and execution

- [ ] Integrate and review all prerequisite shards before final qualification.
- [ ] Select a clean exact candidate SHA and its exact original review base.
- [ ] Supply installed interpreter paths for all six matrix environments.
- [ ] Reserve the host; do not overlap this run with other pytest/tox runs.
- [ ] Run on Linux cgroup v2 with a writable delegated child and `cgroup.kill`.
- [ ] Supply a candidate-bound coverage map for the 17 spiders and all 13
      scenarios.
- [ ] Use a fresh evidence directory outside every source checkout.
- [ ] Run the complete plan once; retain failures and interruptions.
- [ ] Obtain the separate independent GPT-6 Astra/max review of the full
      original-base-to-exact-candidate diff and evidence.
- [ ] Let the manager reconcile gates, review and closeout documentation.

List the exact argument vectors without running anything:

~~~console
.venv/bin/python scripts/qualify_a1_a2_handoff.py
~~~

The listing includes every command, timeout, environment override and artifact
requirement. It does not create the default evidence directory. An explicit
execution has this shape; replace every placeholder with the final values:

~~~console
.venv/bin/python scripts/qualify_a1_a2_handoff.py --execute \
  --base ORIGINAL_BASE_SHA --candidate EXACT_CANDIDATE_SHA \
  --output-root /tmp/msgloom-final-qualification-UNIQUE \
  --python312 /prepared/py312/bin/python \
  --python313 /prepared/py313/bin/python \
  --python314 /prepared/py314/bin/python \
  --python312fastmcp /prepared/py312-fastmcp4/bin/python \
  --python313fastmcp /prepared/py313-fastmcp4/bin/python \
  --python314fastmcp /prepared/py314-fastmcp4/bin/python \
  --coverage-map /prepared/exact-candidate-coverage.json
~~~

Run from the candidate repository root. Do not resolve interpreter executable
symlinks: doing so can discard virtual-environment identity. The normal 3.13
runtime must be Python 3.13.5; every environment must have Scrapy 2.19.0,
pytest 8, pytest-cov 7.1.0 and pytest-xdist 3.8.0. Compatibility environments
also require FastMCP 4.0.10.

The inspected host has Python 3.13.5 with Scrapy 2.19.0 at the existing
`.venv/bin/python`. Its existing `.tox/py313-fastmcp4/bin/python` has the
pinned compatibility dependencies. Installed base interpreters 3.12.14 and
3.14.7 were found, but those inspected interpreters lack Scrapy and the test
dependencies. They are not qualified matrix environments. Provisioning is
outside this preparation; this runner never installs or upgrades dependencies.

## Final gates, all pending

| Gate | Resolved execution |
| --- | --- |
| A1-focused | All top-level `tests/test_*.py` plus `tests/source_reader`. |
| Normal/default coverage | Full pytest selection on Python 3.13.5. |
| Serial exclusive state | `exclusive_state and not fastmcp_compat`, `-n 0`. |
| FastMCP compatibility | Opt-in file and marker, FastMCP 4.0.10, `-n 0`. |
| Python matrix | Normal, serial and FastMCP groups on 3.12/3.13/3.14. |
| Ruff | `python -m ruff check .`. |
| Format | `python -m ruff format --check .`. |
| Pyright | Full configured source/tests plus the qualification scripts. |
| Live LSP | Actual changed Python documents, versioned diagnostics required. |
| Scrapy contracts | `python -m scrapy check -v`, local data-URL fixtures. |
| Diff | `git diff --check BASE CANDIDATE` and candidate cleanliness checks. |
| Pre-commit | All configured hooks on all files, existing cache only. |
| Reverse imports | AST scan of A1 and standalone Graph transport boundaries. |
| Spider/scenario coverage | Exact 17 names and 13 executed-test mappings. |
| Independent review | External GPT-6 Astra/max, exact candidate and base. |

The A1 selection is intentionally explicit and includes all top-level tests,
including newly integrated handoff tests. It is not a claim to reproduce the
historical closeout's exact 2003-test selection. Full normal coverage also
runs,
so nested application tests cannot disappear from final qualification.

Normal source suites use the committed tox command semantics: `-q -n 4`,
`-m "not exclusive_state and not fastmcp_compat"`, coverage of `msgloom`,
`message_ingest` and `microsoft_graph`, branch coverage and term/XML reports.
Exclusive suites append only to their own interpreter's preceding normal
coverage database. FastMCP uses its separate opt-in coverage database and
`tests/packaging/test_fastmcp_compatibility.py`. The 3.13 pair serves both the
normal/default gate and the 3.13 matrix row.

These are the exact source-suite selections defined inside tox. The runner
uses supplied existing environments directly because tox's provisioning and
wheel installation are prohibited in this shard. It does not certify wheel
installation or replace a separately required packaging/container gate.

The four current contracts use data URLs. Scrapy 2.19.0's actual
`scrapy/commands/check.py` disables pipelines and feeds; contract success is
not persistence, release atomicity or lifecycle evidence. At least four
successful contracts must be reported. No persistent Graph credentials are
supplied.

The pre-commit adapter requires the inspected version 4.6.2 and a populated
source cache (default `~/.cache/pre-commit`). The source cache is opened only
for read-only repository lookup. The real pre-commit Store instead uses a
fresh per-gate writable metadata sandbox, so `mark_config_used()` cannot alter
the shared source database. Clone and environment installation are blocked.
Missing cache, unhealthy environments or an unreviewed adapter version remain
unavailable. Hook versions, selection and arguments remain those in the
committed configuration. A hook that modifies the candidate invalidates the
run; it is not rerun automatically.

## Exact spider coverage

Every row needs one or more passing real Scrapy crawl/command test node IDs
from Task10. Merely loading 17 names is not semantic qualification.

| Spider | Required release contract |
| --- | --- |
| microsoft_profile | No release. |
| microsoft_todo_discover | Complete additive traversal. |
| microsoft_todo_sync | Winning snapshot, scoped presence/absence. |
| microsoft_contacts_discover | Complete configured recursive traversal. |
| microsoft_contacts_sync | Winning snapshot and generation. |
| microsoft_contacts_delta | Winning custom-folder delta. |
| microsoft_onedrive_discover | Drive and root pagination. |
| microsoft_onedrive_delta | Winning checkpoint, normal and 410 reset. |
| microsoft_onedrive_content | Exact version-linked item capture. |
| outlook_discover | Normal and explicitly truncated discovery. |
| outlook_folder_delta | Atomic folder checkpoint and scoped transitions. |
| outlook_delta | Immediate and rules-deferred authority. |
| outlook_full | Per-message profile, multi-target partial success. |
| outlook_calendar_discover | Complete inventory. |
| outlook_calendar_window | Exact window, pause/resume without early release. |
| outlook_calendar_delta | Winning window promotion and 410 rebaseline. |
| outlook_calendar_full | Per-event profile, multi-target partial success. |

The coverage JSON has `base_sha`, `candidate_sha`, `spiders` and
`scenarios`. The `spiders` object must contain exactly the 17 names above.
The `scenarios` object must contain exactly string keys `"1"` through
`"13"`. Every value is a nonempty list of exact pytest node IDs, for example
`tests/test_a1_handoff_end_to_end.py::test_profile_no_release` **only if that
test actually exists and passes**. Parameterized suffixes and class names
must match exactly.

The audit checks the installed loader, committed design matrix, candidate
identity and JUnit artifact digests. It requires mapped cases to have passed
in the current A1 or full normal 3.13 run. After validation, the exact coverage
map bytes are copied into the fresh run evidence and hashed there. Later source
map deletion or mutation cannot remove the reviewed mapping. Skips, fabricated
node IDs, missing rows and stale candidate maps fail. The independent reviewer
must still check that mapped tests prove their claimed behavior.

## Thirteen Task15 scenarios

All remain pending in this preparation:

1. New Mail acquisition, scheduled intake and preparation once.
2. Future-only bootstrap excludes unchanged pre-ledger history.
3. Explicit historical baseline saves one immutable starting workset.
4. Failed advanced acquisition recovers through equivalent retry exactly once.
5. A delayed older run cannot publish after a newer state wins.
6. A large snapshot drains through several bounded worksets without loss.
7. Crash after selection save but before cursor finalization safely retries.
8. Preparation failure after cursor commit leaves rediscoverable pending work.
9. Restore behind the saved cursor fails the anchor check.
10. Missing/corrupt evidence is held while later entries can progress.
11. Mail folder and Calendar window removals remain scoped.
12. Rules-enabled authority waits for all required Full obligations.
13. Entries after the fixed A2 cutoff wait for the next intake.

## Evidence and interruption semantics

The runner writes `manifest.json`, per-command stdout/stderr, JUnit and
coverage artifacts under the supplied external directory. It records exact
base/candidate, commands, runtime versions, timestamps, exit codes, parsed
counts and SHA-256 artifact digests. Each record starts unexecuted and is
saved as running before launch. Nonzero exits are never retried. Independent
later gates may run after an ordinary failure; failed prerequisites block
their dependants. Timeout, signal interruption or candidate mutation stops
the remaining plan.

Normal suites retain the existing four-worker limit; exclusive and
compatibility groups run serially. A shared advisory lock identifies the
repository across worktrees. Existing pytest/tox processes are checked before
each gate. Unrelated tools must also honor the host reservation: an advisory
lock cannot prevent an uncooperative process from starting later.

The reverse scan permits the existing shared configuration imports; it
rejects A2 imports and standalone Graph reverse dependencies.

Mutable database, evidence, temporary, pytest-cache and coverage paths are
isolated. Coverage-data parent directories are created before launch; normal
and exclusive suites for one interpreter retain their shared append database.
Inherited credentials and pytest overrides are not forwarded. The wrapper
preserves test-internal timeouts; its outer suite ceiling is 3600 seconds.
Smaller command ceilings are visible in the listing. A timeout is incomplete
evidence, never permission to weaken a test.

Before a gate command executes, a wrapper moves itself into a fresh delegated
cgroup-v2 child and acknowledges admission to the runner. The wrapper then
waits until the runner atomically saves the PID, cgroup path and log links and
explicitly releases execution. Recorder death, save failure or invalid release
closes admission without running the user command. Descendants inherit
that boundary even when they call `setsid()` or start a new process group. The
runner also acts as a child subreaper so orphaned owned descendants can be
reaped. Normal parent exit with any remaining owned process is non-passing and
hard-stops later gates. Cleanup sends bounded SIGTERM only after PID/start-time
and cgroup ownership revalidation, then uses `cgroup.kill` for the complete
subtree if needed. Timeout and runner interruption use the same boundary.

The platform prerequisite is Linux cgroup v2 with permission to create a child
below the runner's current delegated cgroup and with `cgroup.kill` available.
The runner probes this before launching a gate and fails closed if unavailable.
Direct SIGKILL of the runner or power loss can still leave running evidence.
The saved PID, cgroup path and log links support explicit operator cleanup.
Such an invocation can never be treated as passed or resumed into the same
output directory.

CLI exit 0 means listing only. Exit 1 means blocked/failed/interrupted
execution. Exit 2 means automatic gates passed but mandatory external review
is still outstanding. The manifest always keeps final qualification blocked.
No review pass, Task15 completion or `completion.json` is generated.
