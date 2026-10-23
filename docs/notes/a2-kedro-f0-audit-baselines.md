# A2 Kedro F0-07: unignored audit baseline and candidate delta

Date: 2026-10-24. Task: F0-07. Base commit: `895fc40` (master).

## Full-suite results (final)

The full normal pytest set finished on all three Python versions.

| Python | Exit code | Result |
| --- | --- | --- |
| 3.12.14 | 0 | 4705 passed, 42 min 17 s |
| 3.13.16 | 0 | 4705 passed, 24 min 9 s |
| 3.14.7 | 1 | 1 failed, 4704 passed, 43 min 0 s |

The 3.14.7 failure is
`tests/container_deployment/test_container_qualification.py::test_real_local_container_timeout_is_removed_if_image_present`.
The 3.12.14 and 3.14.7 runs ran at the same time. Both started at about
09:14 local time. They ended at 09:56:39 and 09:57:22 (file times of the
`.time` logs). That test uses the fixed Docker container name
`msgloom-qual-pytest-timeout`. A name collision between the two runs is a
likely cause. It is not proven. Other explanations are not excluded: host
load (the two runs used `-n 2` each, so four workers on four cores), a delay
in Docker `--rm` removal after the client process is killed, or a defect in
the test. Supporting facts: the 12-directory subset, which includes
`tests/container_deployment`, passed on 3.14.7 earlier (exit 0, 327 passed,
`pytest-subset-cand-3.14.out`). The same test passed alone on 3.14.7 in two
runs, with raw logs `pytest-solo-container-3.14-run1.out` and
`pytest-solo-container-3.14-run2.out` (exit 0 each). A clean sequential full
rerun on 3.14.7 was not made. This failure is an open item for the security
owner. Logs: `/tmp/f0-scratch-20261024/f05b/logs/`
(`pytest-normal-cand-3.12.out`, `pytest-normal-cand-3.14.out`,
`exitcodes.txt`).

## Result

The production lock fails an unignored `uv audit` with 11 reports. It also
fails the CI-like audit (with the two documented ignores) with 9 reports.
The reports PYSEC-2026-4322 (Brotli) and PYSEC-2026-4323 (brotlicffi) are
new and have fixed releases. Five Twisted advisories are also new. This
task was not asked to look for them. They have only a prerelease fix.
Adding Kedro 1.7.0 to a scratch lock adds 20 packages and changes the audit
output by zero bytes. No existing package version changes.

The unignored raw output is kept below. No ignore was added anywhere.

## How CI audits

`.github/workflows/ci.yml` (job step "Audit locked Python dependencies"):

    for version in 3.12 3.13 3.14; do
      uv audit --locked --no-progress --preview-features audit-command \
        --python-version "$version" \
        --ignore-until-fixed PYSEC-2017-83 \
        --ignore-until-fixed GHSA-8pqf-f4m5-798g
    done

CI pins uv 0.13.5 (`setup-uv` `version: "0.13.5"`). The Pi has uv 0.12.24.
The tool and database are not the same build. The OSV data is live. The
numbers below are valid for 2026-10-24 on this host. No pip-audit or
osv-scanner configuration exists in the workflow or in `pyproject.toml`.
The reviewed policy is `docs/dependency-vulnerability-policy.md`.

## Read-only method

The audit ran in a scratch copy, not in the repository:

- `cp pyproject.toml uv.lock /tmp/f0-scratch-20261024/audit-base/`
- Production `uv.lock` SHA-256:
  `5db0bbf6f7ec6b787f892c85477d90a5a22abf343010cc84e6843828168ae02d`.
- Production `pyproject.toml` SHA-256:
  `e83c1cb4dc8bb4d495288eff8c66d0cef7d227f86099f8fd81421852d5da4fdf`.
- `git status` in the F0 worktree shows only new `docs/notes/a2-kedro-f0-*`
  files. The repository lock and project file were not changed.

## Commands and exit codes (baseline lock)

Run in `/tmp/f0-scratch-20261024/audit-base/`.

| Command | Exit code | Summary line |
| --- | --- | --- |
| `uv audit --locked --no-progress --preview-features audit-command --python-version 3.12` (unignored) | 1 | 11 vulnerabilities, 146 packages |
| Same, `--python-version 3.13` | 1 | 11 vulnerabilities, 146 packages |
| Same, `--python-version 3.14` | 1 | 11 vulnerabilities, 146 packages |
| CI-like (both `--ignore-until-fixed`), 3.12 | 1 | 9 vulnerabilities |
| CI-like, 3.13 | 1 | 9 vulnerabilities |
| CI-like, 3.14 | 1 | 9 vulnerabilities |
| `uv lock --check --no-build-package pypydispatcher` | 0 | lock is current |

The three unignored outputs are byte-identical (MD5 `73fc5063...`). The
three CI-like outputs are byte-identical (MD5 `21c64ce6...`). The output of
`--python-version 3.13` has SHA-256
`0b8d54f4f65f5798790660772d17d4cdb2c78208071a0bc6f085c577d93e1218`.

Last green master run (from `gh run list --branch master`): head
`895fc40a0ec889bd96f620df8c62491787218217`, created 2026-10-23T03:46:48Z,
conclusion `success`. This task did not rerun CI. This task did not find
why that run passed, so it makes no claim about the cause.

## Raw output: unignored audit, baseline lock (3.13; same for 3.12, 3.14)

    brotli 1.2.0 has 2 known vulnerabilities:
    - GHSA-9v8h-qqgm-4m35: Brotli: Out-of-bounds write in the Brotli decoder ("Node2Shell") also affects the PyPI Brotli package
      Fixed in: 1.2.1
      Advisory information: https://nvd.nist.gov/vuln/detail/CVE-2026-111497
    - PYSEC-2026-4322: (same title)
      Fixed in: 1.2.1
      Advisory information: https://www.cve.org/CVERecord?id=CVE-2026-111497

    brotlicffi 1.2.0.2 has 2 known vulnerabilities:
    - GHSA-9v8h-qqgm-4m35: (same title)
      Fixed in: 1.2.1.0
    - PYSEC-2026-4323: Out-of-bounds write in the brotlicffi decoder ("Node2Shell")
      Fixed in: 1.2.1.0
      Advisory information: https://www.cve.org/CVERecord?id=CVE-2026-111497

    scrapy 2.19.0 has 1 known vulnerability:
    - PYSEC-2017-83: No summary provided
      No fix versions available
      Advisory information: https://github.com/advisories/GHSA-h7wm-ph43-c39p

    twisted 26.4.0 has 6 known vulnerabilities:
    - GHSA-2qrf-pqgx-qh9v: Denial of Service in the Twisted IMAP4 Server via a Negative Literal Size in SEARCH
      Fixed in: 26.10.0rc1
    - GHSA-53xc-49m8-p798: Unauthenticated Remote Denial of Service in the Twisted IRC Server via an Unbounded Line Buffer
      Fixed in: 26.10.0rc1
    - PYSEC-2026-4304: Twisted: IMAP wildcardToRegexp() ReDoS
      No fix versions available
      Advisory information: https://nvd.nist.gov/vuln/detail/CVE-2026-106454
    - GHSA-cwm5-jh59-mwxr: Unauthenticated Remote Denial of Service in the Twisted conch Telnet Transport via an Unbounded Subnegotiation Buffer
      Fixed in: 26.10.0rc1
    - GHSA-3476-c5c2-fr73: Unauthenticated Remote Denial of Service in the Twisted words domish XML Element Stream via an Unbounded Element Tree
      Fixed in: 26.10.0rc1
    - GHSA-q7qq-6mhp-9rc4: HTTP Request Smuggling in twisted.web via a Bare CR or LF in a Header Value
      Fixed in: 26.10.0rc1

    stderr: Using CPython 3.14.7 / Resolved 147 packages in 1ms /
    Found 11 known vulnerabilities and no adverse project statuses in 146 packages

The block above is shortened for the repeated titles and URLs. The full
files are in `/tmp/f0-scratch-20261024/audit-base-3.1{2,3,4}.out`.

## Findings that make the CI audit red

| Finding | Package | Installed | Fixed release | Where it comes from |
| --- | --- | --- | --- | --- |
| PYSEC-2026-4322 (alias CVE-2026-111497, GHSA-9v8h-qqgm-4m35) | `brotli` | 1.2.0 | 1.2.1 | `scrapy` 2.19.0, marker `implementation_name != 'pypy'` |
| PYSEC-2026-4323 (same CVE and GHSA) | `brotlicffi` | 1.2.0.2 | 1.2.1.0 | `scrapy` 2.19.0, marker `implementation_name == 'pypy'` |
| GHSA-2qrf-pqgx-qh9v | `twisted` | 26.4.0 | 26.10.0rc1 (prerelease) | `scrapy` 2.19.0 |
| GHSA-53xc-49m8-p798 | `twisted` | 26.4.0 | 26.10.0rc1 (prerelease) | `scrapy` 2.19.0 |
| GHSA-cwm5-jh59-mwxr | `twisted` | 26.4.0 | 26.10.0rc1 (prerelease) | `scrapy` 2.19.0 |
| GHSA-3476-c5c2-fr73 | `twisted` | 26.4.0 | 26.10.0rc1 (prerelease) | `scrapy` 2.19.0 |
| GHSA-q7qq-6mhp-9rc4 | `twisted` | 26.4.0 | 26.10.0rc1 (prerelease) | `scrapy` 2.19.0 |

Brotli facts (OSV records fetched 2026-10-24):

- PYSEC-2026-4322 affects `brotli` from `0` to before 1.2.1. PYSEC-2026-4323
  affects `brotlicffi` from `0` to before 1.2.1.0. GHSA-9v8h-qqgm-4m35
  affects both from 1.0.3 to before the same fixed versions.
- Published 2026-10-22 (GHSA) and 2026-10-23 (PYSEC). Severity is CVSS 4.0
  with high impact ratings; GitHub marks it CRITICAL. Summary: out-of-bounds
  write in the Brotli decoder.
- Fixed releases exist on PyPI: `brotli` 1.2.1 and `brotlicffi` 1.2.1.0,
  both uploaded 2026-10-22. `brotli` 1.2.1 has `cp312`, `cp313` and `cp314`
  `manylinux2014_aarch64` wheels. The `brotlicffi` 1.2.1.0 release lists
  these aarch64 files (`json/pypi-brotlicffi.json`): `cp314t`, `cp39-abi3`,
  `pp311` and `pp312` wheels, and an sdist. The `cp39-abi3` wheel would
  cover CPython 3.12 to 3.14. This task did not install either fixed
  release.
- Scrapy 2.19.0 requires `brotli>=1.2.0` (non-PyPy) and
  `brotlicffi>=1.2.0.0` (PyPy). The fixed releases satisfy those ranges.
- `uv tree --locked --offline --all-groups --invert --package brotli`
  (exit 0): `brotli v1.2.0` <- `scrapy v2.19.0` <- `msgloom v0.1.0`.
  The same command for `brotlicffi` prints no dependents on CPython,
  because the PyPy marker excludes it. `uv audit` still reports it, because
  the lock contains the package.
- Whether msgloom code reaches the Brotli decoder (Scrapy decompresses
  `Content-Encoding: br` responses when Brotli is installed) was not
  assessed in this task.

Twisted facts:

- The five GHSA entries show a fix only in the prerelease `26.10.0rc1`
  (uploaded 2026-10-22). Latest stable on PyPI is 26.4.0. Scrapy 2.19.0
  accepts `twisted>=21.7.0`.
- Reachability for msgloom was not assessed. The advisory titles name IMAP,
  IRC, conch Telnet, words domish and `twisted.web` header handling.

## Existing documented ignores (CI policy)

From `docs/dependency-vulnerability-policy.md` and `ci.yml`:

| ID | Package | Policy | Fixed release |
| --- | --- | --- | --- |
| `PYSEC-2017-83` (GHSA-h7wm-ph43-c39p) | `scrapy` 2.19.0 | `--ignore-until-fixed`, reviewed exception | None listed |
| `GHSA-8pqf-f4m5-798g` (PYSEC-2026-4304, CVE-2026-106454) | `twisted` 26.4.0 | `--ignore-until-fixed`, reviewed 2026-10-16 | None listed |

The CI-like run confirms that these two IDs remove exactly two reports
(11 to 9). The ignores are scope-limited and expire when OSV lists a fix.

## Baseline versus candidate delta

Candidate: baseline `pyproject.toml` plus `kedro==1.7.0`, in
`/tmp/f0-scratch-20261024/audit-cand/`. Starting `uv.lock` was a copy of the
production lock. The resolver preferred locked versions.

| Command | Exit code | Result |
| --- | --- | --- |
| `uv lock --no-build` (first try) | 1 | Failed: `pypydispatcher` is sdist-only |
| `uv lock --no-build-package pypydispatcher` | 1 | Same failure |
| `uv lock --no-build` with `exclude-dependencies = ["pypydispatcher"]` | 0 | 166 packages resolved |
| `uv audit ...` unignored, 3.12 / 3.13 / 3.14 | 1 / 1 / 1 | 11 vulnerabilities, 165 packages |

Why the exclusion exists: Scrapy requires `pypydispatcher` only on PyPy. It
is sdist-only. A build to read its metadata would be an sdist build, which
this task must not run. The scratch `pyproject.toml` therefore contains a
`[tool.uv] exclude-dependencies` entry. The scratch lock reports the
package as removed. That removal is an artifact of the scratch setup. It is
not a real change. The package is not installed on CPython.

Lock comparison (`tomllib`, name to version):

- Baseline: 146 packages. Candidate: 165 packages.
- Added (20): `appdirs` 1.4.4, `arrow` 1.4.0, `binaryornot` 0.6.0,
  `build` 1.6.1, `cookiecutter` 2.7.1, `dynaconf` 3.3.5, `fsspec`
  2026.9.0, `gitdb` 4.0.12, `gitpython` 3.2.1, `kedro` 1.7.0,
  `kedro-telemetry` 0.9.0, `omegaconf` 2.4.0, `parse` 1.22.4,
  `pyproject-hooks` 1.3.3, `python-dateutil` 3.0.0, `python-slugify` 9.1.3,
  `six` 1.17.0, `smmap` 5.0.3, `text-unidecode` 1.3, `tzdata` 2026.5.
- Changed versions: none (empty list).
- Removed: `pypydispatcher` 2.1.2 (artifact, see above).
- Audit stdout for 3.12, 3.13 and 3.14 is byte-identical to the baseline
  output (`diff` exit 0; SHA-256 of the 3.13 output is the same value shown
  above). Stderr differs (146 vs 165 packages). The new Kedro stack adds no
  report in this tool. The tool is blind to CVE-2026-3840 by construction:
  the OSV record lists a GIT range with `versions: ["1.2.0"]` only, and the
  package query for `kedro` 1.2.0 does not return it (`json/osv3840.json`,
  `osvq12.json`). A clean result does not speak to this CVE.
- Candidate scratch lock SHA-256:
  `be6dbacb03873335654c32b4a3434aee944402554d1cd241eab5edf902b794c1`.

This agrees with the Q0 R2 result (146 to 166 packages, 20 added, 0
upgraded) except for the package count: this run counts 165 because of the
`pypydispatcher` exclusion.

Limits of the delta:

- It shows no new report from this OSV source and this uv build. It does
  not clear Kedro. The Snyk report for CVE-2026-3840 does not appear in
  OSV for Kedro 1.7.0 (F0-02), so this audit cannot see it.
- The tool reported no "adverse project statuses".
- The uv build (0.12.24) differs from the CI build (0.13.5).

## Owner decision options (not actions taken)

For the Brotli reports:

- Change the lock to `brotli` 1.2.1 and `brotlicffi` 1.2.1.0 in a separate
  reviewed dependency change.
- Wait for a Scrapy release or Renovate batch that selects the fixed
  releases.

For the Twisted reports with a prerelease-only fix:

- Keep CI red until a stable Twisted release exists.
- Adopt the prerelease `26.10.0rc1` after a separate review.

The owner makes each decision. This task adds no ignore and changes no lock.

## Source URLs

- `https://api.osv.dev/v1/vulns/PYSEC-2026-4322`
- `https://api.osv.dev/v1/vulns/PYSEC-2026-4323`
- `https://api.osv.dev/v1/vulns/GHSA-9v8h-qqgm-4m35`
- `https://pypi.org/pypi/brotli/json`, `https://pypi.org/pypi/brotlicffi/json`
- `https://pypi.org/pypi/twisted/json`, `https://pypi.org/pypi/scrapy/json`
- `https://github.com/advisories/GHSA-h7wm-ph43-c39p`

## Status / Open items

- F0-07: DONE (baseline, raw output, command log, delta).
- STOP-and-risk for the manager: master-equivalent CI audit is red on this
  host and date for 9 reports: 4 Brotli reports (PYSEC-2026-4322 and
  GHSA-9v8h-qqgm-4m35 on `brotli`; PYSEC-2026-4323 and GHSA-9v8h-qqgm-4m35
  on `brotlicffi`) and 5 Twisted reports. Count source:
  `/tmp/f0-scratch-20261024/audit-base-ci-3.13.out` (an earlier draft of
  this line said "2 of which are Brotli"; the file shows 4).
- Open: Q0 R2 reported only the two documented reports for the same lock on
  an earlier date (see F0-01 note). The 2026-10-24 scan shows 11. The
  Brotli advisories were published 2026-10-22 and 2026-10-23, so the
  OSV data changed. This task did not establish why the last master CI run
  (2026-10-23T03:46:48Z) was green. No cause is claimed.
- Open: Twisted advisories need an owner reachability review. Not assessed.
- Open: Brotli decoder reachability through Scrapy was not assessed.
- Open: CI uses uv 0.13.5. A rerun with that exact build may differ.
- Open: the delta used a scratch lock with a `pypydispatcher` exclusion.
- Open: the Snyk CVE-2026-3840 report is outside this OSV scan (see F0-02).
