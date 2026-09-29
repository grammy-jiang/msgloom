"""Exercise archive validation with synthetic package artifacts."""

from __future__ import annotations

import importlib.util
import io
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "scripts" / "qualify_installed_wheel.py"


def _module():
    spec = importlib.util.spec_from_file_location("qualify_installed_wheel", HELPER)
    if spec is None or spec.loader is None:
        pytest.fail("qualification helper could not be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _tar(path: Path, members: dict[str, bytes]) -> None:
    with tarfile.open(path, "w:gz") as archive:
        for name, content in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))


def _wheel(path: Path, members: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)


def test_sdist_allowlist_accepts_rebuild_files_and_runtime_only(tmp_path: Path) -> None:
    """Accept a minimal synthetic sdist with the required rebuild metadata."""
    module = _module()
    archive = tmp_path / "msgloom-0.1.0.tar.gz"
    _tar(
        archive,
        {
            "msgloom-0.1.0/pyproject.toml": b"[build-system]\n",
            "msgloom-0.1.0/MANIFEST.in": b"prune tests\n",
            "msgloom-0.1.0/PKG-INFO": b"Metadata-Version: 2.4\n",
            "msgloom-0.1.0/msgloom/__init__.py": b"",
        },
    )
    names = module.inspect_sdist(archive)
    if "msgloom/__init__.py" not in names:
        pytest.fail("runtime module missing from accepted sdist")


def test_sdist_allowlist_rejects_tests_and_traversal(tmp_path: Path) -> None:
    """Reject development payloads and archive traversal."""
    module = _module()
    archive = tmp_path / "bad.tar.gz"
    _tar(
        archive,
        {
            "msgloom-0.1.0/pyproject.toml": b"",
            "msgloom-0.1.0/MANIFEST.in": b"",
            "msgloom-0.1.0/tests/test_private.py": b"",
        },
    )
    with pytest.raises(module.QualificationError):
        module.inspect_sdist(archive)

    traversal = tmp_path / "traversal.tar.gz"
    _tar(
        traversal,
        {
            "msgloom-0.1.0/pyproject.toml": b"",
            "msgloom-0.1.0/MANIFEST.in": b"",
            "msgloom-0.1.0/../secret": b"",
        },
    )
    with pytest.raises(module.QualificationError):
        module.inspect_sdist(traversal)


def test_wheel_allowlist_rejects_forbidden_runtime_dependencies(
    tmp_path: Path,
) -> None:
    """Reject FastMCP or Prefect from normal wheel metadata."""
    module = _module()
    wheel = tmp_path / "msgloom-0.1.0-py3-none-any.whl"
    _wheel(
        wheel,
        {
            "msgloom/__init__.py": b"",
            "msgloom-0.1.0.dist-info/METADATA": (
                b"Metadata-Version: 2.4\nName: msgloom\n"
                b"Requires-Dist: fastmcp==4.0.10\n"
            ),
        },
    )
    with pytest.raises(module.QualificationError):
        module.inspect_wheel(wheel)


@pytest.mark.exclusive_state
def test_qualification_cli_has_no_implicit_paths() -> None:
    """Require all build, output, environment, and uv paths explicitly."""
    completed = subprocess.run(
        [sys.executable, str(HELPER)],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode == 0:
        pytest.fail("qualification helper accepted missing explicit paths")
    for option in ("--source-root", "--output-root", "--env-python", "--uv"):
        if option not in completed.stderr:
            pytest.fail(f"missing required CLI path diagnostic: {option}")


def test_output_root_must_be_outside_source_checkout(tmp_path: Path) -> None:
    """Reject artifact output paths nested beneath the source checkout."""
    module = _module()
    source = tmp_path / "checkout"
    source.mkdir()
    request = module.QualificationRequest(
        source_root=source,
        output_root=source / "dist",
        env_python=tmp_path / "venv" / "bin" / "python",
        uv=tmp_path / "bin" / "uv",
        required_cli=(),
        required_resource=(),
    )
    with pytest.raises(module.QualificationError):
        module._validate_request_paths(request)


def test_sdist_normalization_is_byte_reproducible(tmp_path: Path) -> None:
    """Normalize ordering and archive timestamps to stable bytes."""
    module = _module()
    first = tmp_path / "first.tar.gz"
    second = tmp_path / "second.tar.gz"
    members = {
        "msgloom-0.1.0/pyproject.toml": b"[build-system]\n",
        "msgloom-0.1.0/MANIFEST.in": b"prune tests\n",
        "msgloom-0.1.0/msgloom/__init__.py": b"",
    }
    _tar(first, members)
    _tar(second, dict(reversed(tuple(members.items()))))
    module._normalize_sdist(first, 1_700_000_000)
    module._normalize_sdist(second, 1_700_000_000)
    if first.read_bytes() != second.read_bytes():
        pytest.fail("normalized sdists differ for identical source bytes")
