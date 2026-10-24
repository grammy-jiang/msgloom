"""P2-02 pointer memory bounds and lone-surrogate object keys."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from msgloom.a2_kedro.parsers import plain_json as pj
from msgloom.a2_kedro.parsers.plain_json import FieldState, parse_json
from tests.a2_kedro.helpers import check

ROOT = Path(__file__).resolve().parents[2]
ADDRESS_SPACE = 3 * 1024**3

#: Child program. It limits the address space, then parses a hostile body.
CHILD = """
import json, resource, sys
sys.path.insert(0, sys.argv[1])
resource.setrlimit(resource.RLIMIT_AS, (int(sys.argv[2]), int(sys.argv[2])))
from msgloom.a2_kedro.parsers.plain_json import parse_json
key, count = int(sys.argv[3]), int(sys.argv[4])
body = b'{"' + b"k" * key + b'":[' + b",".join([b"null"] * count) + b"]}"
result = parse_json(body)
print(json.dumps({
    "outcome": result.outcome.value,
    "limits": [item.value for item in result.limitations],
    "fields": len(result.fields),
    "pointer_bytes": sum(len(f.pointer.encode()) for f in result.fields),
    "body_bytes": len(body),
}))
"""


def limits(result: pj.ParseResult) -> tuple[str, ...]:
    return tuple(item.value for item in result.limitations)


@pytest.mark.parametrize("count", [400_000, 20_000])
def test_megabyte_key_over_many_nulls_stays_bounded_without_memory_error(
    count,
) -> None:
    if importlib.util.find_spec("resource") is None:
        pytest.skip("resource module is not available")
    run = subprocess.run(
        [sys.executable, "-I", "-c", CHILD, str(ROOT), str(ADDRESS_SPACE)]
        + [str(2**20), str(count)],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if run.returncode != 0 and "ValueError" in run.stderr and "setrlimit" in run.stderr:
        pytest.skip("RLIMIT_AS is not supported here")
    check(run.returncode == 0, "child failed: " + run.stderr[-300:])
    report = json.loads(run.stdout)
    check(report["body_bytes"] < pj.MAX_BODY_BYTES, "body is inside the size bound")
    check(report["outcome"] == "incomplete", "hostile body is incomplete")
    check("pointer_limit" in report["limits"], "pointer bound is reported")
    check(report["pointer_bytes"] <= pj.MAX_POINTER_BYTES_TOTAL, "retained bytes")


def test_retained_pointer_bytes_never_pass_the_total_cap() -> None:
    keys = {"k" * 1000 + str(index): None for index in range(5000)}
    result = parse_json(json.dumps(keys).encode())
    total = sum(len(field.pointer.encode()) for field in result.fields)
    check(0 < len(result.fields) < 5000, "walk stopped part way")
    check(total <= pj.MAX_POINTER_BYTES_TOTAL, "retained pointer bytes bound")
    check(limits(result) == ("pointer_limit",), "pointer limitation only")
    check(result.lookup("/absent").state is FieldState.UNPROVEN, "absence unproven")


def test_one_oversize_pointer_stops_the_walk_with_a_limitation() -> None:
    body = json.dumps({"k" * (pj.MAX_POINTER_BYTES + 1): [None, None]}).encode()
    result = parse_json(body)
    check(result.fields == (), "no oversize pointer is kept")
    check(limits(result) == ("pointer_limit",), "pointer limitation")


def test_pointers_inside_the_bound_are_unchanged() -> None:
    body = b'{"a/b":[null,{"~":"x"}],"c":"","d":3}'
    result = parse_json(body)
    pointers = [field.pointer for field in result.fields]
    check(pointers == ["/a~1b/0", "/a~1b/1/~0", "/c"], f"pointers {pointers}")
    check(result.outcome is pj.Outcome.COMPLETE, "complete")


def test_field_bound_is_checked_before_key_work(monkeypatch) -> None:
    monkeypatch.setattr(pj, "MAX_JSON_FIELDS", 1)
    body = json.dumps({"a": None, "b" * 2**20: None}).encode()
    result = parse_json(body)
    check(len(result.fields) == 1, "one field kept")
    check(limits(result) == ("field_limit",), "field limit, not pointer limit")


@pytest.mark.parametrize(
    ("body", "pointer"),
    [
        (b'{"a\\ud800b": "x"}', "/a?b"),
        (b'{"\\udc00": ["x"]}', "/?/0"),
        (b'{"k": {"\\ud800/": null}}', "/k/?~1"),
    ],
)
def test_lone_surrogate_keys_give_encodable_pointers(body, pointer) -> None:
    result = parse_json(body)
    check("lone_surrogate" in limits(result), "surrogate limitation")
    pointers = [field.pointer for field in result.fields]
    check(pointers == [pointer], f"pointers {pointers}")
    for item in pointers:
        item.encode("utf-8")
    check(result.lookup(pointer).state is not FieldState.MISSING, "cleaned lookup")


def test_lookup_finds_a_surrogate_key_by_raw_and_cleaned_pointer() -> None:
    result = parse_json(b'{"a\\ud800b": "x"}')
    for pointer in ("/a?b", "/a\ud800b"):
        found = result.lookup(pointer)
        check(found.state is FieldState.TEXT and found.value == "x", "found")
    check(result.lookup("/a?c").state is FieldState.MISSING, "other key missing")
