"""Check the A2 combined security lock candidate without network access."""

import re
import tomllib
from pathlib import Path
from typing import Any

import pytest

LOCK_PATH = Path(__file__).resolve().parents[2] / "uv.lock"
MINIMUM_VERSIONS = {
    "brotli": "1.2.1",
    "brotlicffi": "1.2.1.0",
    "filelock": "4.2.4",
}
_RELEASE_PART = re.compile(r"^[0-9]+(?:\.[0-9]+)*")
_PRERELEASE_MARKER = re.compile(
    r"(?:a|b|rc|dev|alpha|beta|pre|preview)[0-9]*", re.IGNORECASE
)


def _load_packages() -> dict[str, dict[str, Any]]:
    with LOCK_PATH.open("rb") as lock_file:
        lock = tomllib.load(lock_file)
    packages: dict[str, dict[str, Any]] = {}
    for package in lock["package"]:
        packages[str(package["name"]).lower()] = package
    return packages


def _release(version: str) -> tuple[int, ...]:
    match = _RELEASE_PART.match(version)
    if match is None:
        pytest.fail(f"Version has no numeric release part: {version!r}")
    parts = [int(part) for part in match.group(0).split(".")]
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def _is_prerelease(version: str) -> bool:
    match = _RELEASE_PART.match(version)
    suffix = version[match.end() :] if match else version
    return _PRERELEASE_MARKER.search(suffix) is not None


@pytest.mark.parametrize(("name", "minimum"), sorted(MINIMUM_VERSIONS.items()))
def test_locked_version_meets_security_minimum(name: str, minimum: str) -> None:
    packages = _load_packages()
    if name not in packages:
        pytest.fail(f"{name} is missing from uv.lock")
    locked = str(packages[name]["version"])
    if _is_prerelease(locked):
        pytest.fail(f"{name} is locked to a prerelease: {locked}")
    if _release(locked) < _release(minimum):
        pytest.fail(f"{name} is locked to {locked}; the minimum is {minimum}")


def test_kedro_is_not_locked() -> None:
    packages = _load_packages()
    if "kedro" in packages:
        pytest.fail("kedro must not be in the production lock")
    for name, package in packages.items():
        for dependency in package.get("dependencies", []):
            if str(dependency["name"]).lower() == "kedro":
                pytest.fail(f"{name} depends on kedro")
        for group in package.get("optional-dependencies", {}).values():
            for dependency in group:
                if str(dependency["name"]).lower() == "kedro":
                    pytest.fail(f"{name} has an optional dependency on kedro")


def test_no_prerelease_twisted_is_locked() -> None:
    packages = _load_packages()
    if "twisted" not in packages:
        pytest.fail("twisted is missing from uv.lock")
    version = str(packages["twisted"]["version"])
    if _is_prerelease(version):
        pytest.fail(f"twisted is locked to a prerelease: {version}")
