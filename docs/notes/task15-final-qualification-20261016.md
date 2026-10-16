# Task 15 final qualification — PENDING

**Status:** Documentation preparation only, 2026-10-16. Final qualification,
independent QA, design signoff, and final approval are **PENDING**.
**Final candidate SHA:** `TO_BE_FROZEN`.
**Original review base SHA:** `765d3c67c707257514d882310873f8a89f3d866b`.

Resolve both identities before the formal gate. Freeze a clean reviewed commit
that includes the intended implementation and operator documentation. This
preparation branch's HEAD is not designated as the final candidate. Do not
substitute `HEAD` or a moving branch name for the frozen full SHA.

## Evidence scope

| Evidence | Recorded scope | Final qualification effect |
| --- | --- | --- |
| Preflight | 98 verified test nodes, as reported in the task handoff. | Supporting evidence only; not an official 28-gate run. |
| PR50 / PR51 CI | Separate CI evidence reported in the task handoff. Run identities and artifacts must be attached during reconciliation. | Does not replace exact-SHA gates or independent QA. |
| Prior candidate `d5d0201` | Interrupted invocation: 7/28 gates passed, one interrupted, 20 not run. | Incomplete historical evidence; retain original outcomes and artifacts. |
| Official final invocation | PENDING on `TO_BE_FROZEN`. | No final PASS claimed. |
| Independent QA and final approval | PENDING on the same frozen candidate and original review base. | No design signoff or Task 15 acceptance claimed. |

The preflight count is a test-node count, not a gate count. This documentation
preparation does not rerun or independently verify that reported count or the
PR CI results. No network or GitHub lookup is part of this preparation. Do not
copy old results or artifact hashes into the official final invocation.
Historical A1 closeout and scoped handoff evidence remain in
[a1-closeout.md](a1-closeout.md).

## Operator boundary

A1 owns immutable acquisition facts, atomic release groups, and ordered release
entries in its catalog. Facts alone are not releases. Authority state,
checkpoint promotion, and its release commit together. Non-authoritative
release gates verify completion and current effective state. Mutable provider
rows and the effective-state index are not historical replay truth.

A2 uses `ReleaseSourceReader` to reconstruct exact committed versions and
verify evidence. Intake captures a finite cutoff and saves exact selections
before atomically committing its workset, pending index, and consumer cursor
in the separate Phase 1 store. Cursor progress means durable admission, not
successful preparation. Failed preparation leaves pending work for a later
finite invocation. Missing or corrupt evidence has a durable held disposition;
later valid entries can progress without claiming that held content succeeded.

Keep the trusted catalog pin and consumer identity stable. On restore/anchor
failure, reconcile the catalog, evidence, and Phase 1 store explicitly. Do not
edit a cursor to bypass validation. Preserve held references and reasons for
explicit repair/replay. `prepare-scheduled` has no automatic historical-baseline
or held-evidence repair option. Historical baseline is the explicit service API
described in [operator configuration](operator-configuration.md#explicit-historical-baseline).

The installed scope is **20 Spiders**: the original 17 plus Teams chat, channel,
and notification reconciliation. Teams native local fixtures must prove crawl,
release, and A2 intake behavior. Chat and channel have separate streams;
notification reconciliation contributes to those streams. Live work/school
Teams tenant acceptance is excluded. Fixture and CI results do not qualify it.

The external scheduler launches and awaits each finite command. All writes,
workers, and cleanup are awaited. No detached background scheduling continues
after command exit. This qualification does not certify a scheduler deployment.

## Commands and focused checks

Run from the repository root with the installed environment. These help calls
were checked locally during documentation preparation:

```console
.venv/bin/msgloom --help
.venv/bin/msgloom config inspect --help
.venv/bin/msgloom prepare-scheduled --help
.venv/bin/msgloom status --help
.venv/bin/python scripts/qualify_a1_a2_handoff.py --help
```

Inspect the effective configuration first. Create the bounded invocation JSON
using that version and an authorized caller/authority pair. Use fresh execution
and attempt identities. Keep `consumer_id` stable across retries. Follow the
[configuration and invocation example](operator-configuration.md#scheduled-preparation):

```console
.venv/bin/msgloom config inspect --config operator.toml
.venv/bin/msgloom prepare-scheduled operator.toml scheduled-invocation.json
.venv/bin/msgloom status operator.toml scheduled-2026-10-07-001
```

The status execution ID must match the invocation JSON. Inspect result references
and limitations: exit 0 is complete, 3 is blocked, 4 is another terminal outcome
such as incomplete, and 2 is an input/configuration failure.

These existing focused tests are useful checks on a host with local fixture
support. They are not the complete 98-node preflight selection or the formal
qualification map. Their execution remains part of future verification:

```console
.venv/bin/python -m scrapy list
.venv/bin/python -m pytest -q tests/test_task15_intake_acceptance.py
.venv/bin/python -m pytest -q tests/test_teams_handoff_release.py
.venv/bin/python -m pytest -q tests/test_teams_native_contracts.py
.venv/bin/python -m pytest -q tests/source_reader/test_teams_release_intake.py
.venv/bin/python -m pytest -q tests/preparation_pipeline/test_scheduled_recovery.py
```

`scrapy list` was checked locally and returned 20 names. It proves inventory,
not semantic coverage. The official map must bind all 20 Spiders and all 13
Task 15 scenarios to exact passing pytest nodes, including parameter suffixes.
Use the [qualification checklist](a1-a2-qualification-checklist.md) for the
full execution command, six interpreter environments, cgroup-v2 requirement,
coverage-map schema, and interruption handling. The runner's default listing
was checked locally and contains 28 gates; listing executes none of them.

## Official invocation record — fill after execution

| Field | Value |
| --- | --- |
| Candidate full SHA | `TO_BE_FROZEN` |
| Original review base full SHA | `765d3c67c707257514d882310873f8a89f3d866b` |
| Clean candidate verification | PENDING |
| Invocation identity and UTC start/end | PENDING |
| Host, architecture, six runtime paths and versions | PENDING |
| Fresh external evidence directory and manifest path | PENDING |
| Exact command/environment record | PENDING |
| Candidate-bound 20-Spider / 13-scenario map | PENDING |
| Artifact paths and computed SHA-256 digests | PENDING — compute from retained files after execution |
| Independent QA reviewer, exact diff, evidence, and decision | PENDING |
| Final approval and Task 15 acceptance | PENDING |

Record each gate independently. Attach its exit code, parsed counts, logs,
required artifacts, and computed digests. Do not infer success from silence,
a listing, a prior candidate, or a later unrelated CI pass.

| Gate ID | Official result | Evidence reference |
| --- | --- | --- |
| runtime312 | PENDING | PENDING |
| runtime312fastmcp | PENDING | PENDING |
| runtime313 | PENDING | PENDING |
| runtime313fastmcp | PENDING | PENDING |
| runtime314 | PENDING | PENDING |
| runtime314fastmcp | PENDING | PENDING |
| a1 | PENDING | PENDING |
| normal313 | PENDING | PENDING |
| exclusive313 | PENDING | PENDING |
| fastmcp313 | PENDING | PENDING |
| normal312 | PENDING | PENDING |
| exclusive312 | PENDING | PENDING |
| fastmcp312 | PENDING | PENDING |
| normal314 | PENDING | PENDING |
| exclusive314 | PENDING | PENDING |
| fastmcp314 | PENDING | PENDING |
| scrapy_version | PENDING | PENDING |
| ruff_version | PENDING | PENDING |
| ruff | PENDING | PENDING |
| format | PENDING | PENDING |
| pyright_version | PENDING | PENDING |
| pyright | PENDING | PENDING |
| contracts | PENDING | PENDING |
| diff | PENDING | PENDING |
| precommit | PENDING | PENDING |
| reverse_imports | PENDING | PENDING |
| spider_coverage | PENDING | PENDING |
| live_lsp | PENDING | PENDING |

The runner leaves final qualification blocked even when automatic gates pass.
Exit 2 means mandatory external review is outstanding. Preserve failures and
interruptions; start any later attempt in a new evidence directory. Never
resume into or relabel the interrupted `d5d0201` evidence.

After the complete exact-SHA run, obtain the separate independent review of
the full original-base-to-candidate diff and evidence. Resolve findings before
final approval. A changed candidate requires evidence bound to its new SHA.
Update this report with actual results and provenance while retaining the
historical records. Do not mark the design signed off merely because these
documents or CI checks pass.
