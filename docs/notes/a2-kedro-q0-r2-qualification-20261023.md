# A2 Kedro Q0 R2 — independent-review candidate

**Status:** R2 experimental evidence is complete. Independent exact-commit R2 review is **PENDING**. This is NOT a go-ahead for production dependencies, A2 migration, or A1 changes.

Date: 2026-10-23, Australia/Sydney. Target: Raspberry Pi 5, Linux aarch64.

The prior R1 independent read-only review at SHA ddceb3719d753d13f1265472bb83f7b7d1af832c was **REVISE**. Its verbatim transcript is archived as [R1 review](a2-kedro-q0-independent-review-r1-20261023.txt); original [R1 qualification](a2-kedro-q0-qualification-20261023.md) and [R1 evidence](a2-kedro-q0-evidence-20261023.json) are immutable historical snapshots, not current accepted results.

R2 sources: scripts/research/q0_kedro_runtime_probe.py, scripts/research/q0_kedro_matrix.py and [R2 raw per-process matrix](a2-kedro-q0-r2-matrix-20261023.json).

## R1 REVISE findings addressed

| R1 issue | R2 observable evidence | Production limitation |
| --- | --- | --- |
| P1-1: leak test did not exercise actual Kedro Node.run ERROR logger | Real Kedro node logger captured in three cases. An intentionally unsafe node error with the synthetic PRIVATE_CANARY marker MUST appear as positive control. Safe node error and parser dataset failure both produce nonempty logs without that marker. | Only known local hook/logger configuration tested; arbitrary plugins unproven |
| P1-2: heartbeat was vacuous | Eight measured inter-tick gaps overlap a 0.23-second busy CPU Kedro node; at least five must overlap and maximum gap must remain below 0.08 seconds. | Synthetic cooperative CPU, not native calamine/pdfium/lxml or high-load Pi |
| P1-3: in-flight cancellation/late-write not tested | CancelledError propagates after draining true asyncio.to_thread worker. Service future is settled on deadline. Additional cases cover cancel INSIDE publisher BEFORE acceptance, changing valid claim to invalid DURING publisher, cancelling AFTER acceptance but BEFORE acknowledgement, then idempotent read-back. | Postcommit cancellation has an ambiguous business outcome until durable read-back. Fake in-memory store is not SQLite, Phase1Persistence, ClaimToken or cross-process fencing |
| P1-4: telemetry/network checks were vacuous | Explicit kedro-telemetry consent checker returns False with both opt-out variables, and send_telemetry_event returns False. Socket attempts are 0 during programmatic pipeline/telemetry tests; one deliberately intercepted socket control proves monkeypatch active. | Not an OS-level sandbox or proof all future hooks lack network access |
| P1-5: hardcoded successes/asserts could hide failures | Every scenario appends only AFTER independent require() checks pass. Exactly 20 unique named checks. Actual exit codes, stderr, full stdout JSON are recorded. Six runs include -O, which cannot disable require(). Failure-specific parser, publisher, claim, output-conflict counters are verified. | Synthetic tests do not prove production contracts |

Extra negative tests: the Kedro DAG fails closed if any dataset name is not explicitly in its DataCatalog; the exact Kedro 1.7.0 source `AbstractVersionedDataset._get_versioned_path` is tested with eight unsafe and three safe path-version components. No versioned filesystem data is created.

## Raspberry Pi runtime matrix

Reproduce from the research worktree with Python 3.12, 3.13 and 3.14 disposable environments under /tmp/msgloom-a2-q0-20261023:

    python3 -I scripts/research/q0_kedro_matrix.py

This stdlib runner does not install dependencies or touch production DB. It invokes each Python environment in ordinary -I mode and in optimized -O -I mode; checks full stdout as a SINGLE valid JSON record; records return code, stderr, stdout checksum, scenarios and measured timings; writes only within the explicitly supplied temporary sandbox.

| Interpreter | Normal exit | Optimized exit | Cases per run | Observed max heartbeat gap |
| --- | --- | --- | --- | --- |
| CPython 3.12.14 | 0 | 0 | 20/20 | 0.01719–0.01723 s |
| CPython 3.13.16 | 0 | 0 | 20/20 | 0.01719–0.01725 s |
| CPython 3.14.7 | 0 | 0 | 20/20 | 0.01717–0.01733 s |

Total: 6 independent process runs, **120 exercised synthetic checks**, zero stderr bytes, a single machine-readable JSON stdout record for each. Actual process exit code and per-run scenario lists are embedded in the adjacent raw matrix JSON, not inferred from a constant in the report.

20 checks: end-to-end Kedro typed source load, parser Dataset save/load, normalizer, claim-fenced stage Dataset save/load, manifest; replay idempotence; conflicting output rejected; injected parser, publisher and stale-claim failures; missing-catalog entry rejected; parser cancellation drained; deadline service future drained; precommit publisher cancel; midflight claim revocation; postcommit cancel plus idempotent recovery read-back; heartbeat during CPU work; cooperative CPU-node cancellation; Kedro node logger redaction positive+negative; parser Dataset log redaction; explicit telemetry opt-out; active socket blocking control; exact wheel version-path validator; optimized-mode assertion-gate control.

The parser cancellation drain is approximately 0.14 seconds even though cancellation is requested earlier: it drains the still-running service, **not immediate task preemption**. Postcommit cancellation can leave an already accepted stage with no positive caller acknowledgement: C0 MUST perform durable read-back and deterministic append-or-verify, not infer failure from CancelledError.

## Dependency and security gates — unchanged, NOT APPROVED

- PyPI candidate Kedro 1.7.0 universal wheel SHA-256: 488701a27c7d595b62a611cb23596953a9929fe5cc42a376c28abe26654c2438, checked against local wheel and PyPI metadata.
- GitLab CVE-2026-35167 / GitHub GHSA-6326-w46w-ppjw declares the earlier versioned-dataset path traversal fixed in Kedro 1.3.0. The exact 1.7.0 wheel guards `_get_versioned_path` with _is_unsafe_version. R2 now exercises that wheel code path.
- Snyk CVE-2026-3840 STILL marks Kedro 1.7.0 as affected, with no fixed version. OSV CVE-2026-3840 has narrower affected ancestor evidence. This discrepancy remains an **explicit owner security-applicability decision**, not an automatically granted waiver. Do not suppress this advisory.
- Scratch lock resolving project dependencies plus Kedro: 146 to 166 locked packages, **20 new, 0 existing upgraded, 0 removed**. Actual project pyproject.toml and uv.lock unchanged.
- Experimental-preview uv audit --frozen exited **1** on both original and candidate scratch locks: two PREEXISTING reports PYSEC-2017-83 (Scrapy) and GHSA-8pqf-f4m5-798g (Twisted). **Zero new OSV vulnerabilities** is only a delta assertion, NOT full security clearance. No ignores were added.
- Kedro 1.7.0 requires kedro-telemetry. Its opt-out is tested in isolation. Importing kedro.framework.project may configure logging and emit stdout; Q0 explicitly buffers its own Kedro imports and validates clean output, but live msgloom stdio/plugin behavior is unproven.
- Expected production constraints (not implemented) forbid Kedro versioned filesystem datasets, dynamic from_config catalog import, CLI, untrusted load_versions and automatically discovered hooks.

External references: [Kedro 1.7](https://pypi.org/project/kedro/1.7.0/), [GitLab CVE-2026-35167](https://advisories.gitlab.com/pkg/pypi/kedro/CVE-2026-35167/), [GitHub GHSA](https://github.com/kedro-org/kedro/security/advisories/GHSA-6326-w46w-ppjw), [Snyk CVE-2026-3840](https://security.snyk.io/vuln/SNYK-PYTHON-KEDRO-17752561), [OSV CVE-2026-3840](https://api.osv.dev/v1/vulns/CVE-2026-3840).

## Gate decision and next actions

**R2 proposes a conditional GO only for continued Kedro-main-ETL engineering preparation, contingent on an independent R2 read-only verdict tied to an exact SHA.** This is NOT production security approval.

Still OPEN: owner security disposition for Snyk CVE-2026-3840; C0 immutable result/held/completion-receipt schemas; actual Phase1Persistence/ClaimToken/SQLite transactional test with the accepted A1 ReleaseEntry fixture; bounded real native parser worker and cancellation/cgroup tests; whole project+Kedro installed wheel and CI 3.12/3.13/3.14; external Prefect collection-release wakeup and recovery deployment.

No A1 work is authorised or needed. New A2 must consume the immutable A1 selection and exact release reader output, preserve all roles/contexts/transitions, and use Kedro as the MAIN ETL DAG.

**Do not merge a runtime dependency, rename A1 artifacts, or deprecate the old A2 in master based on this synthetic R2 pass alone.**
