"""Validate the structure and integrity of the A2 independent golden corpus.

The corpus lives in ``tests/a2_kedro/golden``. Humans annotated every
expected value by hand. This module checks only shape: strict JSON, required
fields, unique case IDs, polarity coverage, provenance text, synthetic-only
domains, and the SHA-256 manifest. It never imports ``msgloom.a2_kedro`` and
never computes an expected value.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pytest

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"
MANIFEST = GOLDEN_DIR / "MANIFEST.sha256"
EXPECTED_TASKS = ("T0-01", "T0-02", "T0-03", "T0-04", "T0-05", "T0-09", "T0-10")
SCHEMA = "a2-golden-case-file@1"
FILE_FIELDS = (
    "schema",
    "task_id",
    "title",
    "annotator",
    "independence_statement",
    "provenance",
    "cases",
)
CASE_FIELDS = ("case_id", "polarity", "title", "input", "expected")
POLARITIES = ("positive", "negative")
ALLOWED_DOMAINS = ("example.invalid", "example.test")
REAL_TLDS = (
    "com", "net", "org", "edu", "gov", "io", "co", "us", "uk", "de", "cn",
    "jp", "ai", "dev", "app", "info", "biz", "ru", "fr", "cloud",
)  # fmt: skip
HOST_RE = re.compile(
    r"(?<![A-Za-z0-9_-])((?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,})(?![A-Za-z0-9_-])"
)


def _reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_strict(path: Path) -> Any:
    """Load JSON and reject duplicate object keys."""
    with path.open(encoding="utf-8") as handle:
        return json.load(handle, object_pairs_hook=_reject_duplicates)


def bad_hosts(text: str) -> list[str]:
    """Return host-like tokens that use a real-looking TLD outside the allow list."""
    found = []
    for match in HOST_RE.finditer(text):
        host = match.group(1).lower()
        if (
            host.endswith(tuple("." + d for d in ALLOWED_DOMAINS))
            or host in ALLOWED_DOMAINS
        ):
            continue
        if host.rsplit(".", 1)[-1] in REAL_TLDS:
            found.append(host)
    return found


def _corpus_files() -> list[Path]:
    return sorted(GOLDEN_DIR.glob("t0_*.json"))


def _non_empty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def test_expected_task_files_exist() -> None:
    names = [path.name for path in _corpus_files()]
    wanted = [task.lower().replace("-", "_") + ".json" for task in EXPECTED_TASKS]
    if names != wanted:
        pytest.fail(f"corpus files {names} differ from required {wanted}")


@pytest.mark.parametrize("path", _corpus_files(), ids=lambda p: p.name)
def test_file_structure(path: Path) -> None:
    data = load_strict(path)
    missing = [field for field in FILE_FIELDS if field not in data]
    if missing:
        pytest.fail(f"{path.name} lacks fields {missing}")
    if data["schema"] != SCHEMA:
        pytest.fail(f"{path.name} has schema {data['schema']!r}")
    expected_task = path.stem.upper().replace("_", "-")
    if data["task_id"] != expected_task:
        pytest.fail(f"{path.name} task_id {data['task_id']!r} != {expected_task}")
    for field in ("title", "annotator", "independence_statement"):
        if not _non_empty_text(data[field]):
            pytest.fail(f"{path.name} field {field} is empty")
    sources = (
        data["provenance"].get("sources")
        if isinstance(data["provenance"], dict)
        else None
    )
    if (
        not isinstance(sources, list)
        or not sources
        or not all(_non_empty_text(s) for s in sources)
    ):
        pytest.fail(f"{path.name} provenance.sources must be a non-empty list of text")


@pytest.mark.parametrize("path", _corpus_files(), ids=lambda p: p.name)
def test_cases_have_required_fields_and_both_polarities(path: Path) -> None:
    data = load_strict(path)
    cases = data["cases"]
    if not isinstance(cases, list) or not cases:
        pytest.fail(f"{path.name} has no cases")
    prefix = data["task_id"] + "-"
    seen: set[str] = set()
    polarities: set[str] = set()
    for case in cases:
        missing = [field for field in CASE_FIELDS if field not in case]
        if missing:
            pytest.fail(f"{path.name} case {case.get('case_id')} lacks {missing}")
        case_id = case["case_id"]
        if not case_id.startswith(prefix):
            pytest.fail(f"{case_id} does not start with {prefix}")
        if case_id in seen:
            pytest.fail(f"duplicate case_id {case_id} in {path.name}")
        seen.add(case_id)
        if case["polarity"] not in POLARITIES:
            pytest.fail(f"{case_id} has bad polarity {case['polarity']!r}")
        polarities.add(case["polarity"])
        if not _non_empty_text(case["title"]):
            pytest.fail(f"{case_id} has empty title")
        if not isinstance(case["input"], dict) or not isinstance(
            case["expected"], dict
        ):
            pytest.fail(f"{case_id} input and expected must be objects")
        if not case["expected"]:
            pytest.fail(f"{case_id} expected is empty")
    if polarities != set(POLARITIES):
        pytest.fail(
            f"{path.name} needs positive and negative cases, has {sorted(polarities)}"
        )


def test_case_ids_unique_across_corpus() -> None:
    seen: dict[str, str] = {}
    for path in _corpus_files():
        for case in load_strict(path)["cases"]:
            if case["case_id"] in seen:
                pytest.fail(
                    f"{case['case_id']} in {path.name} and {seen[case['case_id']]}"
                )
            seen[case["case_id"]] = path.name


@pytest.mark.parametrize("path", _corpus_files(), ids=lambda p: p.name)
def test_only_synthetic_domains(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    hosts = bad_hosts(text)
    if hosts:
        pytest.fail(f"{path.name} has real-looking hosts: {sorted(set(hosts))}")
    for email in re.findall(
        r"[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)", text
    ):
        if not email.lower().endswith(ALLOWED_DOMAINS):
            pytest.fail(f"{path.name} has non-synthetic email domain {email}")


def test_manifest_matches_files() -> None:
    entries: dict[str, str] = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, _, name = line.partition("  ")
        if not re.fullmatch(r"[0-9a-f]{64}", digest) or not name:
            pytest.fail(f"bad manifest line: {line!r}")
        if name in entries:
            pytest.fail(f"duplicate manifest entry {name}")
        entries[name] = digest
    files = {path.name: path for path in _corpus_files()}
    if set(entries) != set(files):
        pytest.fail(
            f"manifest names {sorted(entries)} differ from files {sorted(files)}"
        )
    for name, path in files.items():
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != entries[name]:
            pytest.fail(
                f"{name} digest changed: manifest {entries[name]}, actual {actual}"
            )


def test_loader_rejects_duplicate_keys(tmp_path: Path) -> None:
    bad = tmp_path / "dup.json"
    bad.write_text('{"a": 1, "a": 2}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON key"):
        load_strict(bad)


def test_host_check_flags_real_looking_domain() -> None:
    if bad_hosts("write to person@mail.example.invalid") != []:
        pytest.fail("synthetic host was flagged")
    if bad_hosts("see https://outlook.com/x") != ["outlook.com"]:
        pytest.fail("real-looking host was not flagged")
