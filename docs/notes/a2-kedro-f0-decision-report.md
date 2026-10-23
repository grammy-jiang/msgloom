# A2 Kedro F0: decision report for the security owner

Date: 2026-10-24. Host: Raspberry Pi 5, Linux aarch64, uv 0.12.24.
Branch: `research/a2-kedro-f0-20261024`, base `895fc40`. Candidate: `kedro`
1.7.0, wheel SHA-256
`488701a27c7d595b62a611cb23596953a9929fe5cc42a376c28abe26654c2438`.

This report summarizes the nine F0 evidence notes. It is interim. It is not
a risk acceptance. It does not approve any dependency change. No ignore was
added anywhere. The owner decides.

## Result

F0-09 and F0-10 stay BLOCKED. They stay blocked until the owner gives an
explicit admission. Nothing in this report is that admission.

What is established (each item has a scratch file in the evidence table):

- The Kedro 1.7.0 wheel from PyPI has the expected SHA-256. The hash check
  exited 0. A negative control exited 1.
- A scratch lock with `kedro==1.7.0` adds 20 packages. It changes no
  existing locked version or hash. All 20 are pure-Python wheels.
- The scratch lock needs a scratch-only `exclude-dependencies =
  ["pypydispatcher"]` setting to resolve under `--no-build`. The production
  route for that lock is an owner decision.
- msgloom and Kedro co-install on Python 3.12.14, 3.13.16 and 3.14.7 on this
  host. `uv pip check`, imports and Pyright exited 0. The full normal pytest
  set on 3.13.16 passed (4705 passed, exit 0).
- The 1.7.0 wheel guards `_get_versioned_path()` against path separators and
  dot-only version strings. OSV returns no advisory for `kedro` 1.7.0.
- Adding Kedro adds no report to the advisory scan output (byte-identical to
  the baseline for 3.12, 3.13 and 3.14).
- Plain use of Kedro (import plus an in-memory pipeline run, no session)
  made 0 network attempts in a network-less sandbox.

What is NOT established:

- CVE-2026-3840 is unresolved. Sources disagree. See "Open risks".
- The reachability controls (F0-03 gate, telemetry test) are a specification
  and a scratch prototype. No production code or test enforces them.
- No test exercises Kedro through msgloom code. Existing tests passing shows
  only that adding Kedro does not break them.
- Dataset deserialization (pickle and similar) reachability has no dedicated
  test. See "Open risks".
- Execution evidence exists for Linux aarch64 only.
- Full pytest runs on 3.12 and 3.14 are PENDING. See "Pending items".

What blocks F0-10:

1. There is no explicit owner admission.
2. The advisory scan of the current production lock is already red without
   Kedro: 11 unignored reports, 9 with the two documented ignores. Kedro is
   not the cause. The red state still has to be resolved or dispositioned by
   the owner before any lock change is merged.
3. The CVE-2026-3840 difference between sources has no recorded disposition.
4. The production lock route for `pypydispatcher` is undecided.
5. The two full-suite runs are not finished.

## Evidence table

Scratch root: `/tmp/f0-scratch-20261024/`. Note names are
`docs/notes/a2-kedro-f0-<name>.md`.

| Claim | Note | Scratch file |
| --- | --- | --- |
| Wheel SHA-256 is `488701a2...c2438`; size 248245 bytes; uploaded 2026-09-28T16:13:26Z; not yanked | version-provenance | `wheel/dl2/kedro-1.7.0-py3-none-any.whl` (fresh `sha256sum`), `json/kedro.json` |
| Sdist SHA-256 `50b654c0...bd493` is a PyPI JSON claim only. The sdist was not downloaded | version-provenance | `json/kedro.json` |
| The scratch lock wheel entry for Kedro has the same SHA-256 | linux-wheel | `f05a/cand/uv.lock`, `f05a/cand-runtime-hashes.txt` |
| Scratch lock adds 20 packages, changes 0 locked versions | linux-wheel | `f05a/cand/uv.lock`, `f05a/base/uv.lock` |
| Lock needs the `pypydispatcher` exclusion (negative control exits 1) | linux-wheel | `f05a/noexcl.out`, `f05a/noexcl.err`, `f05a/lock-cand.exit` |
| Installed set matches the production lock, 0 version mismatches, on 3 Python versions | coinstall | `f05b/logs/exitcodes.txt`, `f05b/logs/freeze-cand-3.1{2,3,4}.txt` |
| Full normal pytest on 3.13.16: 4705 passed, 8 warnings, exit 0 (pytest time 24 m 08 s, wall clock 24 m 10 s) | coinstall | `f05b/logs/pytest-normal-cand-3.13.out`, `.time`, `exitcodes.txt` |
| Pyright 1.1.413: 0 errors on 3.12, 3.13, 3.14 | coinstall, types-tests | `f05b/logs/pyright-cand-3.1{2,3,4}.out` |
| Build is reproducible with Kedro present (same hashes across repeats and Python versions) | types-tests | `f05c/logs/artifact-sha256.txt`, `f05c/logs/f05c-exitcodes.txt` |
| CVE-2026-3840: OSV and NVD list only 1.2.0. Snyk lists `[0,` and "no fixed version". No dispute tag in NVD, OSV or Snyk text | cve-reachability | `json/osv3840.json`, `json/nvd3840.json`, `json/snyk.html` |
| GHSA-6326-w46w-ppjw (CVE-2026-35167, PYSEC-2026-71): fixed in 1.3.0. OSV query for `kedro` 1.7.0 and 1.3.0 is empty | cve-reachability | `json/ghsa.json`, `json/osv35167.json`, `json/osvq.json`, `json/osvq13.json`, `json/osvq12.json` |
| Version guard probe of the 1.7.0 wheel (POSIX only) | cve-reachability | `json/f0_02_validator.out` (SHA-256 `d3d40bea...1d7a`), `scripts/f0_02_validator.py` |
| Advisory scan, unignored: 11 reports on 3.12, 3.13, 3.14 (identical output) | audit-baselines | `audit-base-3.1{2,3,4}.out` |
| Advisory scan, CI-like (two documented ignores): 9 reports (4 Brotli, 5 Twisted) | audit-baselines | `audit-base-ci-3.1{2,3,4}.out` |
| Candidate lock gives byte-identical scan output to the baseline | audit-baselines | `audit-cand-3.1{2,3,4}.out` (MD5 `73fc5063...` same as baseline) |
| PYSEC-2026-4322 (`brotli` 1.2.0, fixed 1.2.1) and PYSEC-2026-4323 (`brotlicffi` 1.2.0.2, fixed 1.2.1.0) | audit-baselines | `json/osv-PYSEC-2026-4322.json`, `json/osv-PYSEC-2026-4323.json`, `json/osv-GHSA-9v8h-qqgm-4m35.json`, `json/pypi-brotli.json`, `json/pypi-brotlicffi.json` |
| Locked versions today: brotli 1.2.0, brotlicffi 1.2.0.2, twisted 26.4.0, scrapy 2.19.0 | audit-baselines | `uv.lock` in the F0 worktree (lines 314, 352, 3169, 2908) |
| Five Twisted reports have a fix only in the prerelease 26.10.0rc1 | audit-baselines | `audit-base-ci-3.13.out`, `json/pypi-twisted.json` |
| Telemetry: modes A and B made 0 socket attempts; C and G made 1 DNS lookup for `heapanalytics.com`; D, F, H, I made 0 | telemetry-networks | `f0-04/<mode>/out.json` (nine modes) |
| `kedro-telemetry` is a core `Requires-Dist` of Kedro 1.7.0 | version-provenance, telemetry-networks | `wheel/x/kedro-1.7.0.dist-info/METADATA` |
| Dataset gate prototype rejects the listed bad inputs; a failing node leaks input text into the ERROR log | dataset-security | `json/f0_03_demo.out`, `scripts/f0_03_gate_demo.py` |
| Kedro core wheel uses `pickle` only in `shared_memory_dataset.py` (`pickle.dumps` check) and `PicklingError` handling. No `pickle.loads` in `kedro/` outside templates. `kedro_datasets` is not installed | this report (grep, see below) | `wheel/x/kedro/`, `venv-kedro/lib/python3.13/site-packages` |
| Resolution only (no execution) for x86_64 Linux, macOS arm64, Windows | portability | `f05c/logs/plat-exitcodes.txt`, `f05c/plat/*.log` |

## Open risks

All items are open. None is marked safe or accepted.

### Kedro advisories

| ID | Aliases | Status for 1.7.0 | Open point |
| --- | --- | --- | --- |
| CVE-2026-3840 (Snyk `SNYK-PYTHON-KEDRO-17752561`) | none found | OSV and NVD: affects 1.2.0 only. Snyk: all versions, no fixed version | Unresolved. It may duplicate CVE-2026-35167 or may be a residual weakness. No source decides. No formal "disputed" tag was found in the saved NVD, OSV or Snyk text. The difference between sources is the finding |
| GHSA-6326-w46w-ppjw | CVE-2026-35167, PYSEC-2026-71 | Fixed in 1.3.0 (GitHub, OSV). Guard present in the 1.7.0 wheel | The guard was probed on POSIX with a minimal dataset. Strings such as `*` pass the guard. Entry points depend on controls that do not exist in msgloom code |
| GHSA-9cqf-439c-j96r | CVE-2026-35171, PYSEC-2026-72 | Fixed in 1.3.0 per GitHub. The wheel comment says the `()` key is rejected | Not tested. Reach: code that imports `kedro.framework.project` and reads `KEDRO_LOGGING_CONFIG` |

### Advisories in the current lock (not caused by Kedro)

| ID | Package and locked version | Fixed release | Delta with Kedro added |
| --- | --- | --- | --- |
| PYSEC-2026-4322 (CVE-2026-111497, GHSA-9v8h-qqgm-4m35) | `brotli` 1.2.0 | 1.2.1 (on PyPI since 2026-10-22) | None. Same report in baseline and candidate |
| PYSEC-2026-4323 (CVE-2026-111497, GHSA-9v8h-qqgm-4m35) | `brotlicffi` 1.2.0.2 | 1.2.1.0 (on PyPI since 2026-10-22) | None. Reported because the lock lists the package. It is PyPy-only through the Scrapy marker. No CPython dependent |
| GHSA-2qrf-pqgx-qh9v | `twisted` 26.4.0 | 26.10.0rc1 (prerelease) | None |
| GHSA-53xc-49m8-p798 | `twisted` 26.4.0 | 26.10.0rc1 (prerelease) | None |
| GHSA-cwm5-jh59-mwxr | `twisted` 26.4.0 | 26.10.0rc1 (prerelease) | None |
| GHSA-3476-c5c2-fr73 | `twisted` 26.4.0 | 26.10.0rc1 (prerelease) | None |
| GHSA-q7qq-6mhp-9rc4 | `twisted` 26.4.0 | 26.10.0rc1 (prerelease) | None |
| PYSEC-2017-83 (GHSA-h7wm-ph43-c39p) | `scrapy` 2.19.0 | None listed | None. Documented CI ignore, already in policy |
| PYSEC-2026-4304 (GHSA-8pqf-f4m5-798g, CVE-2026-106454) | `twisted` 26.4.0 | None listed | None. Documented CI ignore, already in policy |

Facts about the table:

- PYSEC-2026-4322 and PYSEC-2026-4323 name each other as aliases in OSV.
  Both name CVE-2026-111497. GitHub rates the shared GHSA CRITICAL.
- The five Twisted reports and the two Brotli reports are not covered by a
  documented ignore. The CI-like scan therefore stays red for 9 reports on
  the current master lock, with or without Kedro.
- Brotli decoder reachability through Scrapy and Twisted reachability were
  not assessed. Scrapy decompresses `Content-Encoding: br` responses when
  Brotli is installed. That statement comes from Scrapy behavior, not from a
  test in this work.
- Q0 R2 recorded only the two documented reports for the same lock on an
  earlier date. The 2026-10-24 scan shows 11. The Brotli advisories were
  published on 2026-10-22 and 2026-10-23. The last green master CI run is
  dated 2026-10-23T03:46:48Z. This work did not find out why that run passed.

### Telemetry

- `kedro-telemetry` 0.9.0 is a forced dependency and it depends on
  `requests`. Missing consent is treated as consent.
- Opt-out facts observed: `DO_NOT_TRACK=1` (also `KEDRO_DISABLE_TELEMETRY`),
  a `.telemetry` file with `consent: false`, or
  `DISABLE_HOOKS_FOR_PLUGINS = ("kedro-telemetry",)` all gave 0 socket
  attempts. Default consent through a hook or a session gave one DNS lookup
  for `heapanalytics.com`. The sandbox blocked it. No payload was captured.
- The default path also wrote `~/.config/kedro/telemetry.toml`. A session
  appended a `[tool.kedro_telemetry]` table to a project `pyproject.toml`
  that has `[tool.kedro]`. A project without that section was not tested.
- The env opt-out depends on call order. With the context step skipped, the
  hook failed with `AttributeError` before any send. That failure is not a
  designed control.
- The plugin is installed even if msgloom never starts a session. The
  protection is the design rule "no session, no `kedro.hooks` entry points".
  That rule is not enforced by code or tests today.

### Dataset deserialization (pickle and similar)

- No F0 note contains a dedicated test of this topic. The F0-03 gate
  specification forbids `kedro_datasets`, config-driven catalogs, versioned
  datasets and the Kedro CLI and session. That is a design rule only.
- A grep of the unpacked 1.7.0 wheel (`wheel/x/kedro/`, templates excluded)
  found `pickle` only in `kedro/io/shared_memory_dataset.py` (a
  `pickle.dumps` check), in `PicklingError` handling in `data_catalog.py`
  and `parallel_runner.py`, and in a log text in `cached_dataset.py`. It
  found no `pickle.loads` and no unsafe YAML load call. `kedro_datasets`
  (which holds `PickleDataset`) is not installed in the scratch venv.
- This grep is a name search. It does not follow `getattr`, `importlib` or
  the Python `multiprocessing` internals. `SharedMemoryDataset` and
  `ParallelRunner` use `multiprocessing`, which pickles objects between
  processes. The F0 work did not test either.
- Third-party loaders pulled in by Kedro (`omegaconf`, `dynaconf`,
  `cookiecutter`, `gitpython`, `fsspec`) were not examined for
  deserialization or network paths.

### Other open points

- Execution on Linux x86_64, macOS and Windows: NOT TESTED. CI never installs
  Kedro on macOS or Windows. `dynaconf` 3.3.5 declares `<3.15` while msgloom
  has no upper Python bound.
- `exclusive_state`, `fastmcp_compat` and `linux_cgroup_v2` tests did not run
  with Kedro installed. The `linux_cgroup_v2` CI gate stays required.
- The local uv is 0.12.24. CI pins uv 0.13.5. A rerun with the CI build may
  differ.
- The sdist hash and any upstream provenance attestation were not verified.
- Importing Kedro framework code configures logging and prints Rich-formatted
  lines to stdout.
- Strict-mode Pyright would report partly unknown Kedro types
  (type completeness 84.7%).

## Pending items

Two cells are PENDING. They are in `a2-kedro-f0-coinstall.md`. The runs were
still running when this report was committed. No value is recorded.

| Placeholder | Meaning | Rows that depend on it |
| --- | --- | --- |
| `FULL_312`, `FULL_312_EXIT`, `FULL_312_RESULT` | Full normal pytest set on Python 3.12.14 | coinstall Result table and Tests table; coinstall F0-05b status (now PARTIAL); types-tests part (b); portability 3.12 execution cells |
| `FULL_314`, `FULL_314_EXIT`, `FULL_314_RESULT` | Full normal pytest set on Python 3.14.7 | Same rows, 3.14 side |

Logs for the owner of the runs:
`f05b/logs/pytest-normal-cand-3.12.out` and `pytest-normal-cand-3.14.out`.
The runs use `-n 2`. The subset runs (327 tests each) passed on both
versions. The subset is not a substitute for the full run.

Lint result: `pre-commit run --files docs/notes/a2-kedro-f0-*.md` exited 0
(all 10 notes; markdownlint-cli2, gitleaks, whitespace and end-of-file hooks
passed).

## Decision options for the owner

Each option is a choice for the owner. This work takes none of them.

| Option | What it means | Consequences |
| --- | --- | --- |
| Admit | Accept `kedro==1.7.0` as a runtime dependency now | The 20 packages (25 requirement lines; 24 effective on Linux CPython) enter the runtime set. `kedro-telemetry` and `requests` are installed even if unused. CVE-2026-3840 has no disposition. The telemetry and dataset rules are unenforced. The CI advisory scan stays red from the Brotli and Twisted reports. This option leaves every open item above without a disposition |
| Admit with mitigations | Admit only after named controls exist and the pending items close | Needs: an owner disposition or answer for CVE-2026-3840; the F0-03 gate and tests in code; a network-namespace test and a `DO_NOT_TRACK=1` or plugin-disable control for telemetry; a rule that no `version`, `load_versions`, session, CLI or `kedro_datasets` is used; a decision on the Brotli and Twisted reports; a decision on the `pypydispatcher` lock route; the 3.12 and 3.14 full runs. This delays F0-09 and F0-10 |
| Reject | Do not add Kedro | No new packages, no new open Kedro advisory. Existing Brotli and Twisted reports remain and need their own decision. A later reconsideration needs fresh evidence because the data is live and dated 2026-10-24 |
| Defer | Keep Kedro out of the lock and wait for events | Candidate events: Snyk or the Kedro maintainers answer on CVE-2026-3840; stable Twisted release; Brotli 1.2.1 in the lock through a separate reviewed change; the two pending runs finish. F0-09 and F0-10 stay blocked in the meantime. The evidence needs a refresh when it is used, because it is dated |

Independent of the choice, the owner decides separately:

- how to handle the 9 reports in the baseline lock (separate dependency
  change for `brotli` 1.2.1 and `brotlicffi` 1.2.1.0; prerelease or ignore
  decisions for Twisted, each after a reachability review);
- how to produce the production lock given the `pypydispatcher` sdist.

## Status of F0-09 and F0-10

F0-09 and F0-10 stay BLOCKED until the security owner gives an explicit
admission. A passing hash check, a clean co-install, a clean type
check and a byte-identical scan delta do not replace that admission. This
report adds no ignore, no lock change and no policy change.
