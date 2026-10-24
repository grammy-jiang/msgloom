# A2 Q0 — Kedro 1.7.0 security and isolated runtime qualification

**Status:** CONDITIONAL TECHNICAL GO for continued research and C0 design; **NO-GO** for production manifest/lock edit and A2 cutover.
**Date:** 2026-10-23 Australia/Sydney.
**Target:** Raspberry Pi 5, Linux aarch64, kernel 6.18.50+rpt-rpi-2712.
**Project source anchor:** `grammy-jiang/msgloom` master `895fc40a0ec889bd96f620df8c62491787218217`.
**Design authority:** D4 independent R6 `ACCEPT` on `878121fa9ab7ca35754b36d824440a77e92f5f4d`; design PR [#68](https://github.com/grammy-jiang/msgloom/pull/68).
**Experiment isolation:** `/tmp/msgloom-a2-q0-20261023/`; research-only code `scripts/research/q0_kedro_runtime_probe.py`; evidence JSON `docs/notes/a2-kedro-q0-evidence-20261023.json`.
**Authority limitations:** No A1 edits, no msgloom production code edits, no provider credentials, no actual user data, no mutation to the real `pyproject.toml`, `uv.lock`, virtualenv or SQLite DB. Tests use a synthetic async service and a synthetic token/claim store.

## 1. Gate verdicts

| Gate | Evidence | Current disposition |
| --- | --- | --- |
| Q0.1 exact Kedro package | PyPI 1.7.0 (2026-09-28), SHA-256-checked `py3-none-any` wheel, source inspected without sdist build | **PASS** for candidate verification |
| Q0.2 CVE adjudication | 1.7 wheel uses `_is_unsafe_version` in `_get_versioned_path`; 11 safe/unsafe path tests. OSV/GHSA fixed 1.3.0. Snyk CVE-2026-3840 still says no patched version | **CONDITIONAL / owner security disposition required** |
| Q0.3 exact public API | `AbstractDataset[save, load]`, `DataCatalog`, `MemoryDataset(copy_mode="assign")`, `SequentialRunner(is_async=False)`; source + live adapter use | **PASS for isolated, programmatic usage** |
| Q0.4 telemetry / unwanted effects | Kedro 1.7 pulls `kedro-telemetry==0.9.0` as required dependency; both opt-outs set before imports; 0 socket connection attempts, no synthetic payload in failure log capture | **PASS for synthetic process; production network policy unproven** |
| Q0.5 trusted Dataset + awaited async bridge | One real Kedro DAG uses source load → trusted parser dataset save/load → transform → trusted stage dataset save/load → manifest; 12 synthetic tests per interpreter | **PASS for synthetic scope only** |
| Q0.6 Raspberry Pi matrix | Python 3.12.14, 3.13.16, 3.14.7 in isolated environments, binary-only installation and `uv pip check`, each 12/12 | **PASS for isolated Pi smoke, not whole msgloom wheel** |
| Q0.7 independent Q0 reviewer | Separate exact-SHA review of probe, report, package/source and evidence needed | **PENDING** |
| Q0.8 production dependency PR | Scratch copy of real uv.lock: 146→166 packages, +20, no existing version changes; no actual lock edit | **NOT AUTHORISED / NOT DONE** |

These separate Q0 findings **must not be misread as production qualification**. The most important unanswered proof is a real bounded bridge into `Phase1Persistence` with exact `ClaimToken`/A2 receipt constraints, real parser worker/CPU limits, and a complete package+Pi CI matrix. The project currently does not contain the new `a2_input_disposition@1` and `a2_completion_receipt@2` contracts or their migrations.

## 2. Trusted wheel metadata, exact source and security review

From live PyPI metadata:

- Candidate: `kedro==1.7.0`, published 2026-09-28, supported Python metadata `>=3.10`; universal `kedro-1.7.0-py3-none-any.whl`, 248,245 bytes.
- Verified wheel SHA-256: `488701a27c7d595b62a611cb23596953a9929fe5cc42a376c28abe26654c2438`. This matches both PyPI JSON and a locally downloaded binary. The official release reports **no PyPI provenance attestation**; it is not an independently attested build.
- The relevant exact-wheel `kedro/io/core.py:950-957` calls `_is_unsafe_version(version)` **before constructing the versioned path**.
- Exact-wheel `kedro/utils.py:346-352` rejects empty strings, `/`, backslash, `.` and `..`. Eight unsafe and three ordinary strings behaved as expected in Python 3.13.
- GitHub upstream `GHSA-6326-w46w-ppjw` and GitLab `CVE-2026-35167` mark versions **older than 1.3.0** vulnerable, fixed in 1.3.0 (upstream PR #5442, merged 2026-03-10).
- OSV live `CVE-2026-35167` likewise contains an affected Git range with fix, and `CVE-2026-3840` identifies a `1.2.0` affected ancestor/last-affected commit. It does **not** establish `kedro==1.7.0` vulnerable.
- **Conflict remains:** Snyk `SNYK-PYTHON-KEDRO-17752561` lists CVE-2026-3840 with "no fixed version" and affected releases despite the version guard in the exact 1.7 wheel. Treat this as **unresolved external registry status**, not permission to suppress audit results.

The source-level risk of this specific traversal call **appears mitigated** in 1.7.0. More importantly, the planned msgloom design bans all Kedro versioned filesystem datasets, untrusted `version` parameters, `DataCatalog.from_config`, arbitrary `load_obj` imports and the Kedro CLI. The production catalogue will require an explicit static dataset allowlist and no untrusted paths. These guards are **future code**, so independent security review and explicit repository-owner risk acceptance are still required before adding Kedro to the actual dependency manifest. Do not add `uv audit --ignore` or automatic exemptions from this report.

Official references:

- <https://pypi.org/project/kedro/1.7.0/>
- <https://github.com/kedro-org/kedro/security/advisories/GHSA-6326-w46w-ppjw>
- <https://github.com/kedro-org/kedro/pull/5442>
- <https://advisories.gitlab.com/pkg/pypi/kedro/CVE-2026-35167/>
- <https://security.snyk.io/vuln/SNYK-PYTHON-KEDRO-17752561>
- <https://api.osv.dev/v1/vulns/CVE-2026-35167>
- <https://api.osv.dev/v1/vulns/CVE-2026-3840>

## 3. Kedro 1.7.0 runner, DataCatalog and dataset constraints

Actual wheel source shows:

- `AbstractDataset` can be typed with distinct save and load payload types. A trusted `ParserRequest` can be accepted at `save()`, while `load()` yields a checked parsed output. A claim-fenced stage Dataset can `save()` and later `load()` a durable acceptance reference.
- `SequentialRunner(is_async=False)` loads node inputs from the DataCatalog, invokes a synchronous node, saves each output in topological order and returns output **dataset objects** (not data or a business completion receipt). `runner.run(...).get(...).load()` or the returned dataset's `load()` gets the value.
- **Important catalog hazard:** `AbstractRunner.run` calls `catalog.get(name, fallback_to_runtime_pattern=True)` for all pipeline datasets. An unregistered output may therefore silently become a `MemoryDataset`. The msgloom adapter MUST check exact equality/subset of node dataset names against explicit catalog entries before constructing/running the graph, never rely on a missing-output implicit dataset.
- `MemoryDataset` infers deepcopy for most custom objects. Use reviewed `copy_mode="assign"` **only for frozen domain values**, and qualify RSS and mutation guards against future Pydantic models.
- Custom Dataset `_describe()` and Kedro logs can reveal information if raw IDs or errors are used in names. DataCatalog may wrap `DatasetError` messages. The synthetic facade strips provider exception messages before raising a static `SafeBoundaryError`. A captured Kedro error-log path contained no synthetic `PRIVATE_CANARY` marker.
- `kedro-telemetry` is a compulsory transitive package for full Kedro 1.7, even without Kedro CLI/Session. Opt-out and network-deny tests belong in production CI. Do not assume it is absent just because the programmatic pipeline does not register plugins.

The programmatic PoC uses **all five catalog entries explicitly**, four Kedro nodes, and two side-effectful trusted datasets (`ParseServiceDataset` and `SemanticStageDataset`). The external async bridge runs `asyncio.run_coroutine_threadsafe()` from an owned worker and blocks **that worker only**, never the Application's event-loop thread.

## 4. Actual Pi test matrix

Each version uses the same verified wheel, install without building sdists (`uv pip install --only-binary ':all:'`), and `uv pip check` passes on the 39 installed packages.

| Platform runtime | Scenarios | Synthetic parser cancellation drain | Cooperative CPU-node cancellation drain | Peak process RSS observed |
| --- | --- | --- | --- | --- |
| CPython 3.12.14, aarch64 | 12/12 PASS | ~0.161 s | ~0.031 s | ~43 MiB |
| CPython 3.13.16, aarch64 | 12/12 PASS | ~0.161 s | ~0.031 s | ~44 MiB |
| CPython 3.14.7, aarch64 | 12/12 PASS | ~0.161 s | ~0.031 s | ~47 MiB |

Scenarios are: true Kedro catalog-source load/parser-dataset save+load/normalized node/claim-fenced stage save+load/final manifest; idempotent re-run; same logical accepted key with different output digest; injected parser failure; injected stage failure; expired/stale claim; cancellation during a deliberately slow async service; operation deadline with no late saved result; eight Application-loop heartbeat ticks while runner is active; cancellation during cooperative busy-CPU node; capture/redaction of a real Kedro error-log path; socket network deny.

**Hard limits of this evidence:** only a short synthetic parser delay and short cooperative CPU loop are measured. Neither arbitrary Python thread interruption, worst-case production file parsing, actual parser subprocess cgroup cleanup, SQLite atomicity, true `ClaimToken` fencing, cross-workset held receipts, or high-load memory bounds are proven. The fake async service's dictionary is *not* `Phase1Persistence`. The synthetic test does not establish long-running stability or automatic Prefect trigger deployment.

Reproduce with the included `scripts/research/q0_kedro_runtime_probe.py` inside each disposable environment, always with both telemetry opts and `python -I`. Test logic asserts zero attempted socket connections and rejects the synthetic private marker in both raised exceptions and a captured Kedro error logger.

## 5. Dependency compatibility and vulnerability baseline

A **scratch copy** of the existing production `pyproject.toml` and `uv.lock` was edited to add `kedro==1.7.0`; `uv lock` in that scratch directory completed.

- Original project lock: **146** package entries.
- Scratch Kedro candidate lock: **166** package entries.
- Delta: **20 newly locked distributions, 0 changed existing package versions, 0 removed distributions**.
- New additions include `kedro==1.7.0`, `kedro-telemetry==0.9.0`, `dynaconf==3.3.5`, `fsspec==2026.9.0`, `omegaconf==2.4.0`, `cookiecutter==2.7.1`, and their dependencies. The script and exact added package/version list are in the evidence JSON.
- A second independent fresh `uv pip compile` of direct msgloom runtime requirements plus Kedro resolved Python 3.12/3.13/3.14 without a pin conflict (112–113 packages), compared against an equivalent fresh msgloom-only compile. The difference in total count versus `uv.lock` comes from existing dev/compat groups and lock history; it is not an actual upgrade.
- `uv audit --frozen` on the scratch candidate returns **exit 1** with 2 OSV vulnerability IDs, `PYSEC-2017-83` for existing Scrapy and `GHSA-8pqf-f4m5-798g` for existing Twisted. The exact same two IDs occur in an untouched scratch copy of the old lock. **0 new OSV vulnerabilities**, but **audit is not globally green**.
- Snyk's separate Kedro advisory is not covered by a clean candidate OSV delta and must remain visible to the owner. Do not create an unapproved exception or suppress pre-existing advisories.

This confirms no **resolution-level** dependency conflict on the tested Python versions. An installed `msgloom + Kedro` wheel in each supported runtime, the project pytest/CI quality matrix and transitive full deployment need separate qualification.

## 6. Next gates and no-go conditions

Before a production dependency PR or A2 implementation:

1. **Q0.7 independent review** of this Q0 source/evidence, source-level CVE rationale, and failure paths, tied to an exact SHA. A positive review qualifies only the isolated synthetic feasibility claim.
2. **Repository owner security disposition** on the unresolved Snyk CVE-2026-3840 classification, with a dated source-level applicability explanation and deployment catalog restrictions; pre-existing `uv audit` warnings must remain visible under existing vulnerability policy.
3. **C0 contract freeze** for accepted `A2ResultManifest`, input-only immutable result identity, canonical output digest, `a2_input_disposition@1`, `a2_completion_receipt@2`, source role recovery, and A3 backward reader adapter.
4. **Real bounded integration proof** in an isolated SQLite fixture using the actual msgloom Phase1Persistence and ClaimToken paths, including same-key conflict under concurrent claims, late worker writes, multi-record/transition-only and held-only, and crash/recovery.
5. **Resource/security tests:** representative native PDF/Word/Excel/MIME parser child workers, cancellation under worst bounded CPU input, memory/timeout/lease safety margin on Pi, privacy-safe logging enabled, package/wheel CI 3.12/3.13/3.14, no telemetry or unexpected connections.
6. **Only then** propose a reviewed production dependency/lock PR, with one owner and no upstream A1 modifications, followed by the new Kedro A2 implementation and external Prefect activation.

**Overall: Q0 established real Kedro-ETL integration feasibility in an isolated, reproducible synthetic program. It has NOT established production security approval, full transactional/lifecycle safety, or any permission to merge Kedro runtime code into master.**
