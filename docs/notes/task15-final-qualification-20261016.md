# Task 15 final qualification — ACCEPTED

**Status (2026-10-23, Australia/Sydney):** **ACCEPTED.** The official
exact-SHA 28-gate run passed every automated gate on the source candidate
below, and the separate independent GPT-6 Astra/max review accepted the full
source diff from the original base and the same-SHA evidence. The runner
manifest keeps `qualification_status: blocked` by design; that field records
the runner's own boundary and was not edited. The review record below closes
the external review requirement.

**Formally qualified source SHA:** `34057c6c9f85688fd2bd1868d90302ab5a61205f`.
**Original review base SHA:** `765d3c67c707257514d882310873f8a89f3d866b`.
**Documentation closeout:** a later documentation-only commit records these
results. That commit is not the qualified source SHA. Compare its diff
against `34057c6` to confirm that it changes only documentation.

## Evidence scope

| Evidence | Recorded scope | Effect |
| --- | --- | --- |
| Official run on `34057c6` | 28/28 gates passed; 17,507 executed testcase records, 0 failed, 0 skipped. | Automated qualification of this exact source SHA. |
| Official run on `d9acf2f` | 28/28 gates passed; 17,507 testcase records, 0 failed, 0 skipped. | Supporting evidence. A later lock-only security patch superseded this SHA; the run does not qualify `34057c6`. |
| GitHub CI | PR #58, PR #59, and PR #60: 10/10 each. Master `34057c6`: 10/10 (run 39859888885). | Does not replace exact-SHA gates or independent QA. |
| Independent QA | Separate read-only GPT-6 Astra/max review, arranged by the supervising assistant; not started by the primary agent. First line `DECISION: ACCEPT`. | **ACCEPTED** for the source and same-SHA evidence. |

Testcase record totals add the gate counts. Gates repeat many test IDs, so
these totals are not unique-test counts.

## Attempt history

Every attempt keeps its original evidence directory and outcome. None was
resumed, relabeled, or transferred to a later candidate.

| Candidate | Evidence directory | Outcome | Cause |
| --- | --- | --- | --- |
| `d5d0201` | `/tmp/msgloom-task15-final-20261016-d5d0201-r1` | Interrupted: 7 passed, 1 interrupted, 20 not run. | Runner interrupted. |
| `33723d9` | `/tmp/msgloom-task15-final-33723d9-20261016-r2` | Failed: 21 passed, 3 failed, 4 blocked. | Deterministic offline-package and report fixture defects (repaired by PR #53); one To Do child watchdog expired during an NVMe stall. |
| `f1bf54e` | `/tmp/msgloom-task15-final-qualification-f1bf54e-20261016-r1` | Failed: 26 passed, 1 failed, 1 blocked. | Two Contacts child watchdogs and two barrier deadlines expired in one NVMe stall (PR #55 raised only those four). |
| `2ce2ec0` | `/tmp/msgloom-task15-final-qualification-2ce2ec0-20261017-r1` | Failed: 24 passed, 2 failed, 2 blocked. | Two native Mail child watchdogs (30 s) expired during NVMe stalls. |
| `9e48d93` | `/tmp/msgloom-task15-final-qualification-9e48d93-20261023-r1` | Blocked: 14 passed, 14 not run. | Host guard: another session's `pytest` process existed at a gate boundary. |
| `d9acf2f` | `/tmp/msgloom-task15-final-qualification-d9acf2f-20261023-r1` | Automated passed: 28/28. | Superseded by the lock-only patch below. |
| `34057c6` | `/tmp/msgloom-task15-final-qualification-34057c6-20261023-r1` | Automated passed: 28/28. | Formally qualified source SHA. |

## Root cause of the 2ce2ec0 failures

Both failures were native Mail crawl children that a fixed 30 s
`subprocess.run` timeout killed while they were still progressing. The cause
was a test-budget defect on the qualification host, not a product deadlock.

- The retained `normal314` database had steady commits and one ordinary,
  not-yet-synchronized write transaction open 0.2 s before the kill.
- On an idle host, one child crawl takes 6.3–6.5 s and is CPU bound; Spider
  open to close takes 0.57 s. The child makes about 90 `fsync` calls,
  because every catalog commit uses SQLite `synchronous=FULL`.
- The host's 30 s `atop` history shows that every earlier formal timing
  failure overlapped an NVMe latency collapse caused by the suites' own
  write and flush load: io full 26–73%, average I/O time 2–27 ms instead of
  0.2–0.65 ms. Episodes of 120–330 s occur under heavy load.
- An instrumented reproduction of the exact `normal314` gate on a clean
  `2ce2ec0` checkout failed 4 other native child watchdogs (Calendar delta
  30 s during an NVMe stall; source context and identity gate 20 s during
  CPU saturation from another session). A stack dump of the killed Calendar
  child showed its writer thread inside the SQLite `COMMIT` and the reactor
  idle.

## Repair and dependency remediation

| Change | Scope | Evidence |
| --- | --- | --- |
| PR #58 (`e6ce1e9`) | `tests/native_watchdog.py`: one documented 300 s native-command watchdog and a 120 s fixture-barrier budget (below Scrapy's 180 s `DOWNLOAD_TIMEOUT`). Every test watchdog around a child that commits SQLite work uses them. The investigated runners collect an all-thread stack dump before an expired child is reaped. No product code, assertion, fixture response, or expected behavior changed. Timeout-behavior tests keep their short values. | Validation of the exact `normal314` gate on the merged tree: 4,736 passed, 0 failed. |
| PR #59 (`d235197`) | aiohttp 3.14.5, certifi 2026.10.19, uv 0.13.5, virtualenv 21.14.11 for advisories published after the 2026-10-17 green master. | `uv audit --locked` clean for Python 3.12, 3.13, and 3.14. |
| PR #60 (`412160f`) | opentelemetry-api 1.45.1 for GHSA-xcq7-p3pf-p88h, published after PR #58 passed CI. | `uv audit --locked` clean; CI 10/10. |

See [dependency vulnerability auditing](../dependency-vulnerability-policy.md)
for the advisory details and the virtualenv seed-wheel constraint.

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

The installed scope is **20 Spiders**: the original 17 plus Teams chat, channel,
and notification reconciliation. Teams native local fixtures prove crawl,
release, and A2 intake behavior. **Out of scope:** live work/school Teams
tenant acceptance and any external scheduler deployment. `prepare-scheduled`
runs one finite invocation; this qualification installs no scheduler, daemon,
or detached workflow. It is not a broader Phase 1 product release.

## Official invocation record

| Field | Value |
| --- | --- |
| Candidate full SHA | `34057c6c9f85688fd2bd1868d90302ab5a61205f` (master after PR #60) |
| Original review base full SHA | `765d3c67c707257514d882310873f8a89f3d866b` |
| Clean candidate verification | Fresh detached worktree `/home/grammy-jiang/Projects/msgloom-worktrees/task15-final-qualification-34057c6-20261023`; `HEAD` equal to the candidate and empty `git status --porcelain` before the run; manifest `observed_head_after` equal and `observed_status_after` empty. |
| Invocation start and end (UTC) | 2026-10-22T21:47:59.475366+00:00 to 2026-10-22T23:07:09.035991+00:00 |
| Host and architecture | Raspberry Pi 5, aarch64, Linux 6.18.50+rpt-rpi-2712, Linux cgroup v2 with a delegated `systemd-run --user --scope -p Delegate=yes` scope. |
| Six runtime environments | `/tmp/msgloom-task15-envs-final-20261023-34057c6/{py312,py313,py314,py312fastmcp,py313fastmcp,py314fastmcp}`: Python 3.12.14, 3.13.5, 3.14.7; Scrapy 2.19.0, pytest 9.1.1, pytest-cov 7.1.0, pytest-xdist 3.8.0, Ruff 0.17.1; FastMCP 4.1.0 in the compatibility environments. Provisioned from the candidate `uv.lock` with `uv sync --locked --no-install-project --compile-bytecode --group dev` (plus `--group compat-fastmcp4`). |
| Evidence directory and manifest | `/tmp/msgloom-task15-final-qualification-34057c6-20261023-r1/manifest.json`, SHA-256 `69b492287e14fb31344ba0c9f7a508235854f81d1c2f86c97c3450a5c888e9b1` |
| Command | `systemd-run --user --scope -p Delegate=yes --quiet <py313>/bin/python scripts/qualify_a1_a2_handoff.py --execute --base 765d3c6… --candidate 34057c6… --output-root <evidence> --python312 … --python314fastmcp … --coverage-map <map> --precommit-python <py313>/bin/python --precommit-cache ~/.cache/pre-commit`; exit code 2 (automated gates passed; external review required). |
| Candidate-bound map | `/tmp/msgloom-task15-map-34057c6-20261023.json`, SHA-256 `ea996d5b233108fb2535d3a21c1609926fa38a717bc6bb69a27bf625c8937b60`; 20 Spiders, 13 scenarios, 105 exact node IDs, all passed in `a1` or `normal313`. |
| Durable evidence archive | `/home/grammy-jiang/Projects/msgloom-agent-handoffs/task15-opus55-20261023/evidence/msgloom-task15-34057c6-qualification-evidence-20261023.tar.gz`, SHA-256 `b8a503b787209124b4bbf86a40f1d08970a9526b74b7b41ac0ae2c64f877b801`. It holds the manifest, postcheck, all 77 artifacts, map, launcher log, runner output, the independent review record, the primary audit, and the manifests and postchecks of every earlier attempt, with a `SHA256SUMS` list of the original files (`sha256sum -c SHA256SUMS` after extraction). The `/tmp` copies are subject to the host's 10-day `systemd-tmpfiles` cleanup; the archive is the durable local copy. |
| Artifact digests | The manifest records SHA-256 and size for all 77 artifacts. The retained postcheck (`independent-postcheck.json`, SHA-256 `748b30363bd8df5610d4dfdbddc74bfb9a1bd357d93cbc3629d7cd2961d57352`), a separate primary-agent audit, and the independent review recomputed them: 0 mismatches. |
| Independent QA | **ACCEPT** — `/home/grammy-jiang/Projects/msgloom-agent-handoffs/task15-opus55-20261023/INDEPENDENT_REVIEW.md`, SHA-256 `392eb7c583a8365fd874e04cc6abf70bbef9d54954901a63e43415f212ea2602` |
| Final approval and Task 15 acceptance | **ACCEPTED** — owner-approved merge of this documentation-only closeout after 10/10 CI; PRIMARY acceptance by the primary agent |

## Gate results

| Gate ID | Official result | Duration (s) | Outcome | Primary artifact SHA-256 |
| --- | --- | --- | --- | --- |
| runtime312 | PASS | 0.6 | Python 3.12.14; pytest 9.1.1, pytest-cov 7.1.0, pytest-xdist 3.8.0, ruff 0.17.1, scrapy 2.19.0 | stdout.log `d6684fe9ae3980d2f74cfa2a0721a4e0edc322143577385b21ca4f7b3b5e5c84` |
| runtime312fastmcp | PASS | 0.6 | Python 3.12.14; fastmcp 4.1.0, pytest 9.1.1, pytest-cov 7.1.0, pytest-xdist 3.8.0, ruff 0.17.1, scrapy 2.19.0 | stdout.log `68cca5ca7d38d1b4d3cc779820dce807a9112de8c4a16c2dca668dcad20f336b` |
| runtime313 | PASS | 0.7 | Python 3.13.5; pytest 9.1.1, pytest-cov 7.1.0, pytest-xdist 3.8.0, ruff 0.17.1, scrapy 2.19.0 | stdout.log `176891c1227f5bfc76e416da382c3ae54f33a72f056e91aa4a0b3913c78e8230` |
| runtime313fastmcp | PASS | 0.6 | Python 3.13.5; fastmcp 4.1.0, pytest 9.1.1, pytest-cov 7.1.0, pytest-xdist 3.8.0, ruff 0.17.1, scrapy 2.19.0 | stdout.log `f3e78dc7f91fef5d35ccdb864f9339db42ef05bbbe6f741bf91206e356d737da` |
| runtime314 | PASS | 0.7 | Python 3.14.7; pytest 9.1.1, pytest-cov 7.1.0, pytest-xdist 3.8.0, ruff 0.17.1, scrapy 2.19.0 | stdout.log `5b21572782ad0c6cd84c63210cd6c0c5ac79b762f1a491e6679b9cca808605cf` |
| runtime314fastmcp | PASS | 0.6 | Python 3.14.7; fastmcp 4.1.0, pytest 9.1.1, pytest-cov 7.1.0, pytest-xdist 3.8.0, ruff 0.17.1, scrapy 2.19.0 | stdout.log `1e4e44d6947442ddfb45d207ee950db139617074ce3119402c8a754b517430d5` |
| a1 | PASS | 985.5 | 3284 tests: 3284 passed, 0 failed, 0 errors, 0 skipped | junit.xml `660918ac1d68b9a258e1511454ee71700c119862b1ed60fe67267c4059c3a33d` |
| normal313 | PASS | 1182.0 | 4736 tests: 4736 passed, 0 failed, 0 errors, 0 skipped | junit.xml `e3681fb704ba66c9e74b232d8b873225ae26ccb74cde23c222ce0ecdf8580393` |
| exclusive313 | PASS | 30.5 | 1 test: 1 passed, 0 failed, 0 errors, 0 skipped | junit.xml `9c4eb8ddd16fd106b619d1cf1feda3b0c53e0c9915108114856379d0ccd8216c` |
| fastmcp313 | PASS | 8.9 | 4 tests: 4 passed, 0 failed, 0 errors, 0 skipped | junit.xml `fd749f9001fdb0afcb2b90561859456c4b8da643461ff06bf011383bc798f8e2` |
| normal312 | PASS | 1206.8 | 4736 tests: 4736 passed, 0 failed, 0 errors, 0 skipped | junit.xml `fc5d280b82b4a93511ae8a973705a262b6a9941d6c29d42e90ebc1deb45b3a32` |
| exclusive312 | PASS | 37.5 | 1 test: 1 passed, 0 failed, 0 errors, 0 skipped | junit.xml `158acb202d5d329346f748232e40a64f9180d281231ecc8afb2334ea524a425c` |
| fastmcp312 | PASS | 11.0 | 4 tests: 4 passed, 0 failed, 0 errors, 0 skipped | junit.xml `04124449969189359fa953c3d132340ea6fbacc89e19aeadebfe144e6999bd48` |
| normal314 | PASS | 1147.4 | 4736 tests: 4736 passed, 0 failed, 0 errors, 0 skipped | junit.xml `39393b98abef3306d4309518dd8840d1e13b8986f077df4e89a7399cc32e9fbe` |
| exclusive314 | PASS | 30.3 | 1 test: 1 passed, 0 failed, 0 errors, 0 skipped | junit.xml `97bddbe7c04aea820d12f32e2c045247be354f773c81be4d0ef5af02c795e357` |
| fastmcp314 | PASS | 10.1 | 4 tests: 4 passed, 0 failed, 0 errors, 0 skipped | junit.xml `b7ec45c770120e6f3f8b0bbc9704ea4d7d563cf2f7e1691a546eef0129a13be1` |
| scrapy_version | PASS | 2.8 | Scrapy : 2.19.0 | stdout.log `d54e24b3bfe2063686ff49daa43388214d40543d147fc746ae321c3a8d3aa5ed` |
| ruff_version | PASS | 0.1 | ruff 0.17.1 | stdout.log `027fa459f46a02ce06da5b43de9da2bdcccf90a32acecdce930b4c1739fc4814` |
| ruff | PASS | 0.4 | All checks passed! | stdout.log `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| format | PASS | 0.5 | 1191 files already formatted | stdout.log `f4b4d55f677c296bcba47b2daa8196ef230c0be91641c50ec5f6f9fab5f4dc4c` |
| pyright_version | PASS | 0.4 | pyright 1.1.413 | stdout.log `ece63728bf99615e9d63c5ba03698f34acbd373152a141ab3ec1e1d1147ad4f3` |
| pyright | PASS | 62.9 | 0 errors, 0 warnings, 0 informations | stdout.log `6d88a1b220adb7a3d62092b6e38431f0b3fe8babe9864fab90e5849766260332` |
| contracts | PASS | 3.5 | 4 Scrapy contracts passed (scrapy check -v) | stderr.log `de04aea4fb776cec4d09e54063a6ef179c2605041236c94121d18a6e46203dba` |
| diff | PASS | 0.4 | no whitespace errors | stderr.log `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| precommit | PASS | 11.7 | 13 hooks passed, 0 skipped (no files), 0 failed | stdout.log `332bb961eea5273ca4bbbb2099e178dd8f1b991ee7520167a5d80b979e10f108` |
| reverse_imports | PASS | 0.8 | A1/Graph reverse-import scan: passed | stdout.log `4b4e3074b80375f538f60fc616525c17ca6c094e5907f29802fd7750a1fdb383` |
| spider_coverage | PASS | 2.4 | 20 Spiders, 13 scenarios; map sha256 ea996d5b233108fb… | coverage-map.json `ea996d5b233108fb2535d3a21c1609926fa38a717bc6bb69a27bf625c8937b60` |
| live_lsp | PASS | 7.0 | 601 documents opened, 601 with versioned diagnostics | stdout.log `10324132042205cac17cad0e81ea4b5e291ed63911101eaa6b977fcc25e1270f` |

Full per-gate commands, environments, timeouts, cgroup paths, exit codes and
artifact digests are in the manifest. The runner leaves final qualification
blocked even when every automatic gate passes; exit 2 means the mandatory
external review is outstanding. The independent review record below closes
that requirement without editing the manifest.

## Independent review record

| Field | Value |
| --- | --- |
| Reviewer | Separate GPT-6 Astra/max instance, read-only sandbox, arranged by the supervising assistant |
| Decision | `DECISION: ACCEPT` |
| Record | `/home/grammy-jiang/Projects/msgloom-agent-handoffs/task15-opus55-20261023/INDEPENDENT_REVIEW.md`, SHA-256 `392eb7c583a8365fd874e04cc6abf70bbef9d54954901a63e43415f212ea2602` |
| Reviewed scope | Full source diff `765d3c6..34057c6` (645 files: H1–H20 invariants, provider release paths, the Scrapy 2.19.0 lifecycle, A2 schema v4, finite `prepare-scheduled`), the latest delta (PRs #58–#60), and the same-SHA formal evidence: all 77 artifacts re-hashed, every JUnit file parsed, 28/28 gates, all 105 mapped nodes passed in `normal313` (99 also in `a1`), cgroup-v2 ownership for every gate, and master CI run 39859888885 (10/10). It does not cover this documentation closeout. |
| Findings | P1: none. P2: none. P3, non-blocking: `run_native_command()` in `tests/native_watchdog.py` relies on `Popen.__exit__` for exceptions other than watchdog expiry, and its post-kill `communicate()` has no separate deadline; a follow-up should make exceptional cleanup explicit. Residual limits: the macOS and Windows CI jobs are smoke suites; a 120 s barrier is not a proof under arbitrary host load; native HTTP 503 cases do not isolate every completion-validator branch; the empty-backup scenario is not a missing-ledger-schema migration test; the existing exact-ID Scrapy and Twisted audit exceptions remain. |

## Acceptance and remaining limits

Task 15 is accepted: all 28 automated gates passed on `34057c6`, the
independent review accepted the source and evidence, the primary agent
records PRIMARY acceptance, and the owner approved merging this
documentation-only closeout after 10/10 CI. The acceptance does not cover
live work/school Teams tenant access, an external scheduler deployment, or a
broader Phase 1 product release.

A changed source candidate requires new exact-SHA evidence and a new review.
Do not resume or relabel any retained evidence directory.
