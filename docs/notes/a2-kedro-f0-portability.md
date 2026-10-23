# A2 Kedro F0-06: portability of Kedro 1.7.0

Date: 2026-10-24. Host: Raspberry Pi 5, Linux aarch64 (glibc), uv 0.12.24.
Task: F0-06. Branch `research/a2-kedro-f0-20261024`, base `895fc40`.
Candidate: `kedro` 1.7.0 (wheel SHA-256
`488701a27c7d595b62a611cb23596953a9929fe5cc42a376c28abe26654c2438`).

## Pending items in this evidence set

PENDING: two cells in the co-install note (`a2-kedro-f0-coinstall.md`).
They are the full pytest run on Python 3.12.14 (`FULL_312`, with
`FULL_312_EXIT` and `FULL_312_RESULT`) and on Python 3.14.7 (`FULL_314`,
with `FULL_314_EXIT` and `FULL_314_RESULT`). Both runs were still running
when this note was committed. No value is recorded and none is guessed.
The 3.13.16 full run is final: 4705 passed, exit 0.

Rows in this note that depend on the two cells: the "Execution with Kedro"
cell of the Linux aarch64 row (it names pytest), the Python 3.12 and 3.14
rows in "Python versions", and the last row of "What each platform claim
rests on". Their import and Pyright evidence is final. Their full pytest
evidence is PENDING.

## Result

Kedro 1.7.0 and its 20 new transitive packages ship as pure-Python wheels.
Their metadata does not block Python 3.12, 3.13 or 3.14 on Linux x86_64,
Linux aarch64, macOS arm64 or Windows x86_64. Only one platform check shows
a failure, and it is not caused by Kedro (see "Intel macOS" below).

The project executes Kedro on one platform only: Linux aarch64 (glibc) on
the Raspberry Pi. That evidence is in F0-05b. This note does not extend it
to other platforms. Every other platform in this note has resolution
evidence only. Resolution is not execution. No import, test or run
happened on Linux x86_64, macOS or Windows.

The project CI never installs Kedro on macOS or Windows. The `portability`
job installs three packages through `--with` and does not install msgloom.
No x86_64 Linux runner exists in `.github/workflows/ci.yml`.

No STOP condition was found. This note does not approve any dependency
change.

One metadata condition applies. `dynaconf` 3.3.5 declares
`Requires-Python: <3.15,>=3.10`. msgloom declares `>=3.12` with no upper
bound. The candidate lock covers Python 3.15 and later, and `uv` ignores
the upper bound. A metadata-strict installer such as pip would reject
`dynaconf` on Python 3.15. See "Python versions".

## Verification status by platform

"Resolution" means `uv pip compile --python-platform ... --only-binary
:all:` with the pins of the scratch candidate lock. It checks that a
compatible wheel exists for every selected package. It does not install or
run any code.

| Platform | Resolution exit codes (base and candidate, runtime and dev sets, 3.12 to 3.14) | Execution with Kedro | CI runner today |
| --- | --- | --- | --- |
| Linux aarch64 glibc (host) | 0 for all 12 runs | Done: F0-05b (imports, Pyright, pytest on this Pi) | `ubuntu-26.04-arm`: quality, tests, linux_safety. The workflow was not run here. |
| Linux x86_64 glibc | 0 for all 12 runs | NOT TESTED | None |
| macOS arm64 | 0 for all 12 runs | NOT TESTED | `macos-15`: portable smoke without msgloom or Kedro |
| macOS x86_64 | 1 for all 12 runs (existing `cryptography` pin, not Kedro) | NOT TESTED | None |
| Windows x86_64 (`win_amd64`) | 0 for all 12 runs | NOT TESTED | `windows-2025`: portable smoke without msgloom or Kedro |

Other targets were not examined: Windows arm64, musl Linux, 32-bit
platforms, free-threaded CPython builds and PyPy.

## Kedro wheel and sdist

| Item | Value | Source |
| --- | --- | --- |
| Wheel tag | `py3-none-any` (`Root-Is-Purelib: true`) | `WHEEL` file in the wheel |
| Compiled files in the wheel | 0 (`*.so` and `*.pyd` files: none) | file search of the unpacked wheel |
| `Requires-Python` | `>=3.10` | `METADATA` |
| Python classifiers | 3.10, 3.11, 3.12, 3.13, 3.14 | `METADATA` |
| Operating system classifier | none | `METADATA` |
| Platform-marked requirement | `tomli>=1.1.0; python_version < "3.11"` only | `METADATA` |
| `py.typed` marker | present | wheel contents |

Kedro declares no operating system classifier. Kedro declares no platform
marker for its own requirements. The metadata therefore makes no claim
about Windows or macOS behavior. Only tests can show that behavior.

## The 20 new transitive packages

The scratch candidate lock (F0-05a, SHA-256
`be6dbacb03873335654c32b4a3434aee944402554d1cd241eab5edf902b794c1`) adds
20 packages. The table lists the wheel tags and metadata that the lock and
the installed `METADATA` files show.

| Package | Version | Wheel tag in lock | `Requires-Python` | Platform-marked requirements | OS classifier |
| --- | --- | --- | --- | --- | --- |
| `appdirs` | 1.4.4 | `py2.py3-none-any` | none declared | none | OS Independent |
| `arrow` | 1.4.0 | `py3-none-any` | `>=3.8` | `tzdata` (Python 3.9 and newer) | OS Independent |
| `binaryornot` | 0.6.0 | `py3-none-any` | `>=3.10` | none | none |
| `build` | 1.6.1 | `py3-none-any` | `>=3.10` | `colorama` when `os_name == "nt"` | none |
| `cookiecutter` | 2.7.1 | `py3-none-any` | `>=3.10` | none | none |
| `dynaconf` | 3.3.5 | `py3-none-any` | `<3.15,>=3.10` | none | OS Independent |
| `fsspec` | 2026.9.0 | `py3-none-any` | `>=3.10` | none | OS Independent |
| `gitdb` | 4.0.12 | `py3-none-any` | `>=3.7` | none | Independent, POSIX, Windows, macOS |
| `gitpython` | 3.2.1 | `py3-none-any` | `>=3.8` | none for 3.12 and newer | Independent, POSIX, Windows, macOS |
| `kedro` | 1.7.0 | `py3-none-any` | `>=3.10` | `tomli` below Python 3.11 | none |
| `kedro-telemetry` | 0.9.0 | `py3-none-any` | `>=3.10` | `tomli` below Python 3.11 | none |
| `omegaconf` | 2.4.0 | `py3-none-any` | `>=3.10` | none | OS Independent |
| `parse` | 1.22.4 | `py2.py3-none-any` | none declared | none | none |
| `pyproject-hooks` | 1.3.3 | `py3-none-any` | `>=3.8` | none | none |
| `python-dateutil` | 3.0.0 | `py2.py3-none-any` | `!=3.0.*,!=3.1.*,!=3.2.*,>=2.7` | none | none |
| `python-slugify` | 9.1.3 | `py3-none-any` | `>=3.10` | none | none |
| `six` | 1.17.0 | `py2.py3-none-any` | `>=2.7, !=3.0.*, !=3.1.*, !=3.2.*` | none | none |
| `smmap` | 5.0.3 | `py3-none-any` | `>=3.7` | none | Independent, POSIX, Windows, macOS |
| `text-unidecode` | 1.3 | `py2.py3-none-any` | none declared | none | none |
| `tzdata` | 2026.5 | `py2.py3-none-any` | `>=2` | none | none |

Findings:

- All 20 lock entries list exactly one wheel and one sdist. Every wheel is
  pure Python. No compiled or native package is new.
- The lock records no platform marker on any dependency edge that points to
  one of the 20 packages. All 20 install on every platform in the table
  above (resolution result: 20 of 20 selected on every successful run).
- Floor of `Requires-Python` across the 20 packages: 3.10. Python 3.12,
  3.13 and 3.14 satisfy every lower bound. One upper bound exists:
  `dynaconf` `<3.15`.
- `python-dateutil` 3.0.0 excludes Python 3.0 to 3.2 only. It does not
  affect the supported range.
- `gitpython` and `gitdb` call the `git` executable. `gitdb` and `smmap`
  are pure Python. Whether a `git` executable exists on a host is not
  visible in package metadata. This note did not test it.

### Existing packages that Kedro moves into the runtime set

F0-05a found five packages that earlier appeared only in the dev or compat
groups and now reach the runtime set. The resolution below shows the
effect per platform.

| Platform | Runtime set before | Runtime set with Kedro | Added | Removed or changed |
| --- | --- | --- | --- | --- |
| Linux x86_64, 3.12 and 3.13 | 89 | 113 | 24 | 0 |
| Linux x86_64, 3.14 | 88 | 112 | 24 | 0 |
| Linux aarch64, 3.12 and 3.13 | 89 | 113 | 24 | 0 |
| macOS arm64, 3.12 and 3.13 | 88 | 112 | 24 | 0 |
| Windows x86_64, 3.12 and 3.13 | 90 | 115 | 25 | 0 |
| Windows x86_64, 3.14 | 89 | 114 | 25 | 0 |

The 24 added packages are the 20 new packages plus `more-itertools`,
`pluggy`, `pyyaml` and `tomli-w`. Windows adds `colorama` (marker
`os_name == 'nt'`, reached through `build`). Counts use the exported
runtime requirement set without the project entry. Rows for 3.14 count
one package fewer than rows for 3.12 and 3.13 (`backports-zstd` does not
apply on 3.14). The macOS arm64 rows count one package fewer than Linux
(`greenlet` is not selected there). Both differences exist before Kedro.

`pyyaml` 6.0.3 is a compiled package. The lock lists 38 wheels for it and
no universal wheel. It was already locked, so Kedro adds no new compiled
version. It does move to the runtime set. `markupsafe` 3.0.3 (55 platform
wheels, no universal wheel) is already a runtime package through Jinja2.
`charset-normalizer` 3.5.1 has a universal wheel as a fallback. Resolution
selected a usable wheel for each of these on every successful platform
run.

## Resolution commands and exit codes

All work ran under `/tmp/f0-scratch-20261024/f05c/`. No repository file was
changed. The production venv and the main checkout were not touched. The
scratch locks were copied; their hashes match the F0-05a locks.

1. Export: `uv export --frozen --no-dev --no-emit-project --no-hashes
   --format requirements-txt --no-header -o plat/<variant>-runtime.txt`
   (exit 0 for base and candidate). A second export without `--no-dev`
   gave the dev set (exit 0 for both).
2. Resolution: `uv pip compile plat/<variant>-<set>.txt --python-platform
   <platform> --python-version <version> --only-binary :all: --no-header
   --no-annotate -o <out>`.
3. Kedro-only resolution: `uv pip compile plat/kedro-only.in -c
   plat/cand-runtime.txt --python-platform <platform> --python-version
   <version> --only-binary :all:` with `kedro==1.7.0` as the only input.
4. Wheel-tag check: `python -I scripts/tagcheck.py` matched the lock wheel
   file names against `packaging.tags` for each target. Result: every
   selected package had at least one compatible wheel on every successful
   target.

| Run group | Count | Exit 0 | Exit 1 |
| --- | --- | --- | --- |
| Candidate runtime, 5 platforms, 3 versions | 15 | 12 | 3 |
| Candidate dev set, 5 platforms, 3 versions | 15 | 12 | 3 |
| Base (production lock) runtime, same grid | 15 | 12 | 3 |
| Base (production lock) dev set, same grid | 15 | 12 | 3 |
| Kedro-only closure with lock pins, same grid | 15 | 15 | 0 |

Every exit 1 is `x86_64-apple-darwin`. The base lock fails the same way as
the candidate. The Kedro-only closure resolves on `x86_64-apple-darwin` for
all three Python versions. Kedro-only closure size: 39 packages, and 40 on
Windows.

Delta between base and candidate for every successful platform and
version: no removed package and no changed version, for the runtime set
and for the dev set. The dev set adds 21 packages (the 20 new packages
plus `more-itertools`).

### Intel macOS

`cryptography` 50.0.1 has no usable wheel for `x86_64-apple-darwin`.
Under `--only-binary :all:` the base lock and the candidate lock both fail
for this reason. The failure exists before Kedro. Kedro adds nothing to
it. With source builds allowed, `uv` would try to build `cryptography`
from source. This note did not test that build. No CI job uses Intel macOS.

### Python 3.15

Two attempts used `--python-version 3.15`. For the full runtime set, the
base and the candidate both exit 1, because `brotli` has no usable wheel
for 3.15 in this resolution. That failure is not Kedro related. For
`dynaconf==3.3.5` alone, `uv pip compile --python-version 3.15` exits 0.
`uv` therefore does not enforce the `<3.15` bound from `dynaconf`
`Requires-Python`. This means a lock that includes Python 3.15 can list
`dynaconf` even though the package metadata excludes 3.15. pip would
reject this combination. Neither result shows how Kedro behaves on 3.15.

The first 3.15 attempt made `uv` download CPython 3.15.0rc3 (30 MiB) into
the `uv` interpreter store. The later `uv python uninstall 3.15` removed
it. No other Python interpreter changed.

## Python versions

| Python | Kedro `Requires-Python >=3.10` | Every one of the 20 packages | Execution with Kedro |
| --- | --- | --- | --- |
| 3.12 | satisfied | satisfied | aarch64 Linux only (F0-05b) |
| 3.13 | satisfied | satisfied | aarch64 Linux only (F0-05b) |
| 3.14 | satisfied | satisfied | aarch64 Linux only (F0-05b) |
| 3.15 and newer | satisfied | `dynaconf` `<3.15` excludes it | NOT TESTED |

## CI matrix in `.github/workflows/ci.yml`

The workflow has four jobs. Triggers are push to `master`, pull request and
manual dispatch. All GitHub Actions are pinned by commit SHA. `uv` is
pinned to 0.13.5.

| Job | Runner | Python | What it runs | Installs msgloom and its locked set |
| --- | --- | --- | --- | --- |
| `quality` | `ubuntu-26.04-arm` | 3.13 | `uv audit` for 3.12, 3.13, 3.14; Ruff; Pyright 1.1.413; actionlint; architecture boundary checks; Scrapy contracts; pre-commit | Yes (`uv sync --locked --group dev`) |
| `tests` | `ubuntu-26.04-arm` | 3.12, 3.13, 3.14 (tox `py312`, `py313`, `py314`) and the three `-fastmcp4` environments | Normal and exclusive test sets, coverage gate, wheel qualification | Yes |
| `linux_safety` | `ubuntu-26.04-arm` | 3.13 | `linux_cgroup_v2` tests, at least 36 executed and 0 skipped | Yes |
| `portability` | `macos-15`, `windows-2025` | 3.13 | 7 pytest targets with `uv run --no-project --with pytest==9.0.3 --with scrapy==2.19.0 --with sqlalchemy==2.0.54` | No |

Facts that follow from the workflow:

- Three of four jobs run on one runner architecture, Arm64 Linux. The
  matrix has no x86_64 Linux runner.
- The `portability` job uses `--no-project`. It does not install msgloom,
  the lock or Kedro. If Kedro enters `pyproject.toml`, the macOS and
  Windows jobs still never install it and never import it.
- The macOS and Windows jobs use Python 3.13 only. Python 3.12 and 3.14
  have no macOS or Windows execution.
- The `macos-15` label names an Apple silicon (arm64) runner according to
  GitHub documentation. This note did not verify the architecture on a
  real runner.
- The `quality` job runs `uv audit --locked` for Python 3.12, 3.13 and
  3.14 on Arm64 Linux. Results for the Kedro closure are in the sibling
  baseline and reachability notes, not here.
- The container `deployment/Dockerfile` installs with `pip install
  --only-binary=:all: --require-hashes` into a Debian slim image that
  qualification supplies. Kedro and the 20 packages have wheels, so that
  command can satisfy them. This note did not build the image.
- Wheel qualification (`scripts/qualify_installed_wheel.py`) runs in the
  `tests` job on Arm64 Linux. The F0-05c note records a local run of the
  same script.

## What each platform claim rests on

| Claim | Rests on | Strength |
| --- | --- | --- |
| A compatible Kedro wheel exists for Linux x86_64, macOS arm64, Windows x86_64 | Wheel tag `py3-none-any` and `uv pip compile` | Metadata and resolution only |
| The 20 new packages need no compiler on any platform | All 20 wheels are `none-any`; 0 compiled files in the Kedro wheel | Metadata and file inspection |
| Kedro imports and runs on Linux x86_64, macOS or Windows | Nothing | NOT TESTED |
| Kedro file path, logging and subprocess behavior on Windows | Nothing | NOT TESTED |
| msgloom tests pass with Kedro installed off aarch64 Linux | Nothing | NOT TESTED |
| Kedro imports and msgloom tests on aarch64 Linux | F0-05b, Pi 5, three Python versions | Executed, one platform |

## Limits

- Package versions, hashes and wheel lists apply to the PyPI index on
  2026-10-24.
- The grid used `uv` 0.12.24. CI pins `uv` 0.13.5. Resolution results can
  differ between uv releases.
- `--python-platform` selects a platform by name for wheel and marker
  choice. It does not emulate that platform. No Windows or macOS code ran.
- The platform tag sets in `tagcheck.py` use glibc 2.5 to 2.40 for Linux,
  macOS 15 and Windows `win_amd64`. A host with an older libc or macOS is
  not covered by that check.
- Kedro behavior on Windows (path handling, console output, the `git`
  executable for `gitpython`) is not visible in metadata.

## Status / Open items

- F0-06: DONE for metadata evidence. Execution evidence exists for one
  platform only.
- Open: no runner executes Kedro on Linux x86_64, macOS or Windows.
- Open: the `portability` job does not exercise Kedro or the locked set.
- Open: `dynaconf` `<3.15` and the open upper bound of msgloom
  `requires-python`.
- Open: Intel macOS cannot resolve under wheel-only mode because of the
  existing `cryptography` pin.
