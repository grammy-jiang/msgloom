"""Validate the structure and integrity of the A2 independent golden corpus.

The corpus lives in ``tests/a2_kedro/golden``. A language model annotated
every expected value by hand-reading; no human has reviewed it. This module
checks only shape: strict JSON, required fields, unique case IDs, polarity
coverage, provenance text, synthetic-only domains, and the SHA-256 manifest.
It never imports ``msgloom.a2_kedro`` and never computes an expected value.
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
EXPECTED_TASKS = (
    "T0-01",
    "T0-02",
    "T0-03",
    "T0-04",
    "T0-05",
    "T0-06",
    "T0-07",
    "T0-08",
    "T0-09",
    "T0-10",
)
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
# RFC 2606 and RFC 6761 reserved names. The corpus may use only these hosts.
RESERVED_SECOND_LEVEL = ("example.com", "example.net", "example.org")
RESERVED_TLDS = ("example", "invalid", "test", "localhost")
# Exact file names and code names that the corpus cites. Each is a dotted
# token that looks like a host only because its suffix is also a country
# TLD (``.md``, ``.py``) or a file type. The check never exempts a suffix.
# It exempts only these whole tokens, and never in a URL or email position.
# ``test_non_host_allowlist_is_exact_and_used`` rejects stale entries.
NON_HOST_TOKENS = frozenset(
    {
        "2026-10-03-a1-a2-handoff-contract-design.md",
        "a1-closeout.md",
        "agents.md",
        "architecture.md",
        "component-layout.md",
        "contacts-sync.md",
        "container-deployment.md",
        "contracts.py",
        "dependency-vulnerability-policy.md",
        "handoff.py",
        "inside.json",
        "mail-provisional-authority.md",
        "microsoft-graph-error-handling.md",
        "msgloom-security-review.md",
        "node.run",
        "notes.txt",
        "ok.json",
        "onedrive-resync.md",
        "out.json",
        "outside.json",
        "parser-excel.md",
        "parser-isolation.md",
        "parser-mime-html.md",
        "parser-pdf.md",
        "parser-qualification.md",
        "parser-word.md",
        "part-0001.json",
        "phase1-claim-fencing.md",
        "phase1-claim-reconciliation.md",
        "preparation-semantics.md",
        "report.pdf",
        "secret.json",
        "socket.getaddrinfo",
        "socket.socket.connect",
        "task15-final-qualification-20261016.md",
        "todo-sync.md",
        "u0000.txt",
    }
)
# Token-like strings are allowed only when they are one of these exact fake
# canaries or one of the pinned SHA-256 digests of T0-08. Every other match
# of ``SECRET_RES`` fails ``test_no_token_like_strings``. The allowlist is
# exact and ``test_secret_allowlist_is_exact_and_used`` rejects stale entries.
FAKE_SECRETS = frozenset({"CANARY-PII-7731-ZQ", "FAKE-TOKEN-0000", "FAKE-TOKEN-0001"})
PINNED_DIGESTS = frozenset(
    {
        "758c90cb56df8dd1071dbf258d612075a8820a10439d57094ce329049a20e7e4",
        "a98bc1d2108bc72b07d1608e2774c91adbd86ca24705e0bdf137fc4a0314f4db",
        "ab" * 32,
    }
)
_QUERY_KEYS = (
    "access_token|refresh_token|id_token|token|sig|signature|client_secret|"
    "api_key|apikey|password|secret|code"
)
SECRET_RES = (
    # Authorization header value: ``Bearer <value>``. Prose such as "bearer
    # token" has no digit and is short, so it does not match.
    re.compile(r"(?i)\bbearer\s+((?=[^\s\"',;]*\d|[^\s\"',;]{20})[^\s\"',;]+)"),
    # URL query or form parameter that carries a secret.
    re.compile(rf"(?i)(?:^|[?&;\s\"])(?:{_QUERY_KEYS})=([^&\s\"',;]+)"),
    # JSON Web Token: two or three base64url segments that start with eyJ.
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}(?:\.[A-Za-z0-9_-]*)?"),
    # GUID.
    re.compile(r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"),
    # Long opaque run of base64 or hex characters without separators.
    re.compile(r"(?<![A-Za-z0-9+/_=.-])[A-Za-z0-9+/]{40,}={0,2}(?![A-Za-z0-9+/_=.-])"),
)
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
    """Return host-like tokens that are not RFC 2606 or RFC 6761 reserved names."""
    found = []
    for match in HOST_RE.finditer(text):
        host = match.group(1).lower()
        if host in NON_HOST_TOKENS and not _in_url_or_email(text, match.start()):
            continue
        if is_reserved_host(host):
            continue
        found.append(host)
    return found


def _in_url_or_email(text: str, start: int) -> bool:
    """Return True when a token follows ``//`` or ``@`` and so may be a host."""
    return (
        text[max(0, start - 2) : start].endswith("//") or text[start - 1 : start] == "@"
    )


def is_reserved_host(host: str) -> bool:
    """Return True when host is a reserved example, test, invalid or local name."""
    if host.rsplit(".", 1)[-1] in RESERVED_TLDS:
        return True
    return any(host == d or host.endswith("." + d) for d in RESERVED_SECOND_LEVEL)


def bad_secrets(text: str) -> list[str]:
    """Return token-like strings that are not an allowed fake canary or digest."""
    found = []
    for pattern in SECRET_RES:
        for match in pattern.finditer(text):
            value = match.group(1) if pattern.groups else match.group(0)
            if value in FAKE_SECRETS or value in PINNED_DIGESTS:
                continue
            found.append(value)
    return found


def _json_strings(node: Any) -> list[str]:
    """Return every key and string value of a decoded JSON document."""
    if isinstance(node, str):
        return [node]
    if isinstance(node, dict):
        return [s for k, v in node.items() for s in [k, *_json_strings(v)]]
    if isinstance(node, list):
        return [s for item in node for s in _json_strings(item)]
    return []


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


@pytest.mark.parametrize("path", _corpus_files(), ids=lambda p: p.name)
def test_positive_cases_come_before_negative_cases(path: Path) -> None:
    order = [case["polarity"] for case in load_strict(path)["cases"]]
    first_negative = order.index("negative") if "negative" in order else len(order)
    if "positive" in order[first_negative:]:
        pytest.fail(f"{path.name} lists a positive case after a negative case")


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
        if not is_reserved_host(email.lower()):
            pytest.fail(f"{path.name} has non-synthetic email domain {email}")


@pytest.mark.parametrize("path", _corpus_files(), ids=lambda p: p.name)
def test_no_token_like_strings(path: Path) -> None:
    text = "\n".join(_json_strings(load_strict(path)))
    found = bad_secrets(text)
    if found:
        pytest.fail(f"{path.name} has token-like strings: {sorted(set(found))}")


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


def test_host_check_rejects_non_reserved_hosts() -> None:
    for host in ("foo.internal", "files.corp", "mail.example.invalid.evil.io"):
        if bad_hosts(f"connect to {host} now") != [host]:
            pytest.fail(f"non-reserved host {host} was not flagged")


def test_host_check_accepts_reserved_hosts() -> None:
    reserved = (
        "example.com", "www.example.net", "a.b.example.org", "host.example",
        "x.invalid", "mail.test", "svc.localhost", "files.example.invalid",
    )  # fmt: skip
    for host in reserved:
        if bad_hosts(f"connect to {host} now") != []:
            pytest.fail(f"reserved host {host} was flagged")
    if bad_hosts("notexample.com") != ["notexample.com"]:
        pytest.fail("suffix lookalike notexample.com was not flagged")


def test_host_check_has_no_suffix_exemption() -> None:
    for token in ("evil.md", "evil.py", "files.json", "a.example.md", "x.zip"):
        if bad_hosts(f"connect to {token} now") != [token]:
            pytest.fail(f"suffix exemption hid {token}")


def test_non_host_allowlist_cannot_hide_a_host() -> None:
    # A listed file name is exempt only as a bare token.
    for name in sorted(NON_HOST_TOKENS)[:3]:
        for text in (f"https://{name}/x", f"mail@{name}"):
            if bad_hosts(text) != [name]:
                pytest.fail(f"allowlisted {name} hid a host in {text!r}")
    if bad_hosts("see parser-pdf.md.evil.io") != ["parser-pdf.md.evil.io"]:
        pytest.fail("allowlist matched a prefix of a longer host")


def test_non_host_allowlist_is_exact_and_used() -> None:
    corpus = "\n".join(p.read_text(encoding="utf-8") for p in _corpus_files())
    for name in sorted(NON_HOST_TOKENS):
        if name != name.lower() or is_reserved_host(name):
            pytest.fail(f"allowlist entry {name} is not an exact lowercase name")
        if name not in corpus.lower():
            pytest.fail(f"allowlist entry {name} is unused; remove it")


def test_secret_scan_flags_token_like_strings() -> None:
    samples = (
        "Authorization: Bearer abc123def456",
        "GET /v1.0/me?access_token=abc123def456&top=1",
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ4In0.c2ln",
        "id 123e4567-e89b-12d3-a456-426614174000",
        "blob QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVowMTIzNDU2Nzg5",
        "Bearer FAKE-TOKEN-0000x",
    )
    for text in samples:
        if not bad_secrets(text):
            pytest.fail(f"secret scan missed {text!r}")


def test_secret_scan_accepts_fake_canaries() -> None:
    samples = (
        "Authorization: Bearer FAKE-TOKEN-0000",
        "GET /v1.0/me?access_token=FAKE-TOKEN-0001&top=1",
        "note CANARY-PII-7731-ZQ",
        "a bearer token value must never reach a log",
    )
    for text in samples:
        if bad_secrets(text):
            pytest.fail(f"secret scan flagged {text!r}")


def test_secret_allowlist_is_exact_and_used() -> None:
    corpus = "\n".join(
        "\n".join(_json_strings(load_strict(p))) for p in _corpus_files()
    )
    for value in sorted(FAKE_SECRETS | PINNED_DIGESTS):
        if value not in corpus:
            pytest.fail(f"secret allowlist entry {value} is unused; remove it")
