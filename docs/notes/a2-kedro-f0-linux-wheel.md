# A2 Kedro F0-05a: scratch lock with the Kedro 1.7.0 wheel

Date: 2026-10-24. Host: Raspberry Pi 5, Linux aarch64, uv 0.12.24.
Task: F0-05a. Branch `research/a2-kedro-f0-20261024`, base `895fc40`.

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

Adding `kedro==1.7.0` to the full msgloom dependency set adds 20 lock
entries and changes no existing locked version or hash. The Kedro wheel in
the scratch lock has SHA-256
`488701a27c7d595b62a611cb23596953a9929fe5cc42a376c28abe26654c2438`. This
matches F0-01. All 20 new packages ship one pure-Python wheel each. The
resolution ran with `--no-build`. No sdist was downloaded or built.

One condition applies. The scratch lock needs a scratch-only
`exclude-dependencies = ["pypydispatcher"]` setting. Without it, the
resolution fails under `--no-build`. See "pypydispatcher" below. No STOP
condition was found. This note does not approve any dependency change.

## Method

All work ran in `/tmp/f0-scratch-20261024/f05a/`. No repository file was
changed. The production venv and the main checkout were not touched.

1. `git archive HEAD | tar -x -C f05a/src` gave a clean source copy.
2. `base/` holds the unchanged `pyproject.toml` and `uv.lock`.
3. `cand/` holds the same files with two scratch edits in `pyproject.toml`:
   `"kedro==1.7.0"` added to `[project].dependencies`, and a `[tool.uv]`
   table with `exclude-dependencies = ["pypydispatcher"]`.
4. `uv lock --no-build` ran in `cand/`.
5. A script (`python -I`, kept outside the lock directories) compared both
   lock files by package name and version, wheel hashes and sdist hash.

| Item | SHA-256 |
| --- | --- |
| Production `uv.lock` (equal to `base/uv.lock`) | `5db0bbf6f7ec6b787f892c85477d90a5a22abf343010cc84e6843828168ae02d` |
| Production `pyproject.toml` | `e83c1cb4dc8bb4d495288eff8c66d0cef7d227f86099f8fd81421852d5da4fdf` |
| Scratch `cand/uv.lock` | `be6dbacb03873335654c32b4a3434aee944402554d1cd241eab5edf902b794c1` |
| Scratch `cand/pyproject.toml` | `64f49d0d3ee05798385bab17afed5860bf97ec68a7d3ce5c470cc136cd436018` |

## Commands and exit codes

| Step | Command (abridged) | Exit code |
| --- | --- | --- |
| Source copy | `git archive HEAD \| tar -x -C f05a/src` | 0 |
| Scratch lock | `uv lock --no-build` in `cand/` | 0 (`Resolved 166 packages`) |
| Lock check | `uv lock --check --no-build` in `cand/` | 0 |
| Baseline lock check | `uv lock --check --no-build-package pypydispatcher` in `base/` | 0 (`Resolved 147 packages`) |
| Negative control | same edit without the exclusion, `uv lock --no-build` | 1 (no solution, see below) |
| Lock comparison | `python -I scripts/cmp_locks.py base/uv.lock cand/uv.lock` | 0 |
| Wheel hash | `sha256sum wheel/dl2/kedro-1.7.0-py3-none-any.whl` | 0 |
| Hash export | `uv export --frozen --no-dev --hashes --no-emit-project` (base and cand) | 0 and 0 |

## Dependency-tree delta

Counts are lock entries (`[[package]]` tables). They include the `msgloom`
project entry. `beartype` has two entries in both locks (0.22.9 and 0.23.1,
split by Python marker). Both locks keep them unchanged.

| Measure | Base | Scratch candidate |
| --- | --- | --- |
| Lock entries | 147 | 166 |
| Added | - | 20 |
| Removed | - | 1 (`pypydispatcher`, scratch artifact) |
| Existing entries with a changed version, source or hash | - | 0 |
| Existing entries with changed dependency edges | - | 2 (`msgloom` gains `kedro`; `scrapy` loses the PyPy-only `pypydispatcher` edge) |

The two edge changes are expected. The `scrapy` edge change comes from the
scratch exclusion only.

### Added packages (20)

Each package has exactly one wheel and one sdist listed in the lock. The
hash is the wheel hash that the lock records. The sdist was not fetched.

| Package | Version | Wheel file | Wheel SHA-256 |
| --- | --- | --- | --- |
| `appdirs` | 1.4.4 | `appdirs-1.4.4-py2.py3-none-any.whl` | `a841dacd6b99318a741b166adb07e19ee71a274450e68237b4650ca1055ab128` |
| `arrow` | 1.4.0 | `arrow-1.4.0-py3-none-any.whl` | `749f0769958ebdc79c173ff0b0670d59051a535fa26e8eba02953dc19eb43205` |
| `binaryornot` | 0.6.0 | `binaryornot-0.6.0-py3-none-any.whl` | `900adfd5e1b821255ba7e63139b0396b14c88b9286e74e03b6f51e0200331337` |
| `build` | 1.6.1 | `build-1.6.1-py3-none-any.whl` | `ecd351a4be9d35a9eaaba244a7687143c9c7d4aea6ac964e7e7ddab20cbcf4e7` |
| `cookiecutter` | 2.7.1 | `cookiecutter-2.7.1-py3-none-any.whl` | `cee50defc1eaa7ad0071ee9b9893b746c1b3201b66bf4d3686d0f127c8ed6cf9` |
| `dynaconf` | 3.3.5 | `dynaconf-3.3.5-py3-none-any.whl` | `b3b4a753d5c866fc85466b65fc58d4954f6ed7dc8aa67f2b15bcbfd85d184687` |
| `fsspec` | 2026.9.0 | `fsspec-2026.9.0-py3-none-any.whl` | `8dd6e646e99ea382bd85f97a45e6b526a442d79423a7dc673f1e2756d05fcb5f` |
| `gitdb` | 4.0.12 | `gitdb-4.0.12-py3-none-any.whl` | `67073e15955400952c6565cc3e707c554a4eea2e428946f7a4c162fab9bd9bcf` |
| `gitpython` | 3.2.1 | `gitpython-3.2.1-py3-none-any.whl` | `d66b0832aa8755c1a84892937282df0befb16c97e5a64aeebd68be9c5e323f53` |
| `kedro` | 1.7.0 | `kedro-1.7.0-py3-none-any.whl` | `488701a27c7d595b62a611cb23596953a9929fe5cc42a376c28abe26654c2438` |
| `kedro-telemetry` | 0.9.0 | `kedro_telemetry-0.9.0-py3-none-any.whl` | `88238665e5eaf9c74a89cf1a1412da8c7344e95008414be425bfec719675b78b` |
| `omegaconf` | 2.4.0 | `omegaconf-2.4.0-py3-none-any.whl` | `f141a664c777582405e3cc6e0545ecc79429e79f844995b1a6e71c35946a025c` |
| `parse` | 1.22.4 | `parse-1.22.4-py2.py3-none-any.whl` | `ae430a4477316eed4a9710f642b2db968ec89d5d82e6b0908b8169673b476847` |
| `pyproject-hooks` | 1.3.3 | `pyproject_hooks-1.3.3-py3-none-any.whl` | `5fc53fdac9f7bd63fbcdc868fb5f90b4784d78a53a3d3388cd738b807441a20b` |
| `python-dateutil` | 3.0.0 | `python_dateutil-3.0.0-py2.py3-none-any.whl` | `3c79630202e4152c6add678446984236efe4f57e84d8e892aab0637bab82e9fd` |
| `python-slugify` | 9.1.3 | `python_slugify-9.1.3-py3-none-any.whl` | `9aced0670e54c5603e2335c0fa9a4011ad4bc41ecb3c46e8097294c46fd60ed4` |
| `six` | 1.17.0 | `six-1.17.0-py2.py3-none-any.whl` | `4721f391ed90541fddacab5acf947aa0d3dc7d27b2e1e8eda2be8970586c3274` |
| `smmap` | 5.0.3 | `smmap-5.0.3-py3-none-any.whl` | `c106e05d5a61449cf6ba9a1e650227ecfb141590d2a98412103ff35d89fc7b2f` |
| `text-unidecode` | 1.3 | `text_unidecode-1.3-py2.py3-none-any.whl` | `1311f10e8b895935241623731c2ba64f4c455287888b18189350b67134a822e8` |
| `tzdata` | 2026.5 | `tzdata-2026.5-py2.py3-none-any.whl` | `b683bd1b6659ddcd810ff02ad09ba821d4bf1065072805063eb35c49617905ac` |

All 20 wheels are pure Python (`none-any`). No new compiled artifact enters
the lock. Kedro 1.7.0 direct requirements in the lock: `attrs`, `build`,
`click`, `cookiecutter`, `dynaconf`, `fsspec`, `gitpython`,
`kedro-telemetry`, `more-itertools`, `omegaconf`, `parse`, `pluggy`,
`pyyaml`, `rich`, `tomli-w`, `typing-extensions`. `tomli` is absent because
the project requires Python 3.12 or newer.

### Runtime set versus dev and compat packages

This is a finding that earlier notes did not state. Five packages were
already in the lock, but only through the dev group or the compat-fastmcp4
group.
Kedro makes them runtime dependencies. Their locked versions did not change.

| Package | Locked version | Reached before only through |
| --- | --- | --- |
| `colorama` | 0.4.6 (marker `os_name == 'nt'`) | pytest, tox (dev group) |
| `more-itertools` | 11.1.0 | `jaraco-classes`, `jaraco-functools`, from `keyring` (compat-fastmcp4 group) |
| `pluggy` | 1.6.0 | pytest, pytest-cov, tox (dev group) |
| `pyyaml` | 6.0.3 | pre-commit (dev group), `fastmcp-slim` and `jsonschema-path` (compat-fastmcp4 group) |
| `tomli-w` | 1.2.0 | tox (dev group) |

Evidence: `uv export --frozen --no-dev --no-emit-project --hashes` lists 93
pinned runtime requirements for the base lock and 117 for the candidate.
The difference is 20 added, 5 promoted, 1 removed (`pypydispatcher`).
93 + 25 - 1 = 117. The runtime set that a deployment installs therefore
grows by 25 packages, not 20, in the exported requirement list. Tools that
scan only that list see 25 new lines. The F0-07 audit delta used the full
lock and is unaffected.

Platform detail (checked against
`/tmp/f0-scratch-20261024/f05a/base-runtime-hashes.txt` and
`cand-runtime-hashes.txt`, 93 and 117 pinned lines). One of the 25 is
`colorama`, which carries the marker `os_name == 'nt'`. It installs on
Windows only. The removed `pypydispatcher` is PyPy-only. On Linux with
CPython the effective growth is therefore 24 packages. This matches the
Linux rows in the portability note (24 added) and the co-install note
(20 packages not in the base lock, plus 4 already-locked packages that
move into the runtime set). The two counts do not contradict each other.

## Wheel identity

| Source | SHA-256 |
| --- | --- |
| Fresh `sha256sum` of the F0-01 download (exit 0) | `488701a27c7d595b62a611cb23596953a9929fe5cc42a376c28abe26654c2438` |
| Scratch `cand/uv.lock` wheel entry (size 248245) | same |
| `uv export --hashes` line for `kedro==1.7.0` | same |
| Expected value in the handoff | same |

The lock also lists the Kedro sdist with hash
`50b654c0f6ec79c465bc913c1680ea6ad35fff287160262dce7f9d4c1bdbd493` (size
210797). This value comes from the index metadata. The sdist was not
downloaded. The sdist was not built. No sdist build ran as a probe.

## pypydispatcher

`scrapy==2.19.0` requires `pypydispatcher>=2.1.0` only on PyPy
(`platform_python_implementation == 'PyPy'`). `pypydispatcher` 2.1.2 has an
sdist and no wheel. The lock resolves for all platforms, so uv must read its
metadata. With `--no-build`, the resolution without the exclusion exits 1:
"`pypydispatcher` ... has no usable wheels". The failing split is
`python_full_version >= '3.15'`.

Consequences:

- A real lock update that adds Kedro without the exclusion may make uv build
  the `pypydispatcher` sdist to read its metadata. This note did not test
  that path. It would be an sdist build, and this task forbids sdist builds
  as a probe.
- The scratch exclusion removes one lock entry that is never installed on
  CPython. The exclusion is an artifact of the scratch setup. It is not a
  proposal for `pyproject.toml`.
- The decision on how to produce the production lock (allow the build,
  re-use the existing metadata, or another route) belongs to the owner.

## Limits

- Resolution is universal (all platforms and Python 3.12 or newer). A wheel
  for every new package exists, so no platform needs a build.
- This note proves the lock delta only. Installation and import tests on
  Python 3.12, 3.13 and 3.14 are in `a2-kedro-f0-coinstall.md` (F0-05b).
- The local uv is 0.12.24. CI pins uv 0.13.5. A different uv may order or
  format the lock differently. It should not change versions, but this was
  not tested.
- Index data is live. The versions apply to 2026-10-24.
- The comparison covers versions, sources and hashes. It does not cover the
  security status of the new packages. See F0-02 and F0-07.

## Status / Open items

- F0-05a: DONE. The lock delta is exact. No existing locked version or hash
  changed.
- Open: the production lock route for `pypydispatcher` (owner decision).
- Open: the 25-package runtime growth (20 new, 5 promoted from dev or compat groups).
- No STOP condition was found.
