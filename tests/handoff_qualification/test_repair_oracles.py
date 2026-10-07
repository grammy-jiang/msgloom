"""
Regression controls for independently reviewed Task10 qualification gaps.
"""

from __future__ import annotations

import subprocess

import pytest

from tests import test_onedrive_resync_crawl as drive
from tests.handoff_qualification.faults import (
    FAILURE_SIGNATURES,
    release_failure_problem,
)
from tests.handoff_qualification.feed import (
    feed,
    publication_metadata,
    retained_evidence_with,
    successful,
)
from tests.handoff_qualification.server import (
    DOWNLOAD_PATH,
    DOWNLOAD_SENTINEL,
    local_graph,
    onedrive_download_url,
)

PROVIDERS = tuple(FAILURE_SIGNATURES)


@pytest.mark.parametrize("provider", PROVIDERS)
def test_release_failure_oracle_rejects_unrelated_failure(tmp_path, provider):
    """
    An exit-one startup/request failure must not qualify as rollback proof.
    """
    result = subprocess.CompletedProcess(
        args=["scrapy"],
        returncode=1,
        stdout="",
        stderr="unrelated startup/request failure",
    )
    marker = tmp_path / "not-reached"
    if release_failure_problem(result, marker, provider) is None:
        pytest.fail("Unrelated failure satisfied the publication-fault oracle")


@pytest.mark.parametrize("provider", PROVIDERS)
def test_release_failure_oracle_requires_reached_marker(tmp_path, provider):
    """
    Expected lifecycle text alone cannot substitute for SQL-boundary proof.
    """
    signature = FAILURE_SIGNATURES[provider]
    result = subprocess.CompletedProcess(
        args=["scrapy"],
        returncode=1,
        stdout="",
        stderr=signature.error_line + "\n" + signature.reason,
    )
    marker = tmp_path / "not-reached"
    if release_failure_problem(result, marker, provider) is None:
        pytest.fail("Promotion log text passed without the reached marker")


@pytest.mark.parametrize("provider", PROVIDERS)
def test_release_failure_oracle_accepts_reached_injection(tmp_path, provider):
    """
    Exact lifecycle failure plus release-entry SQL marker is qualifying proof.
    """
    signature = FAILURE_SIGNATURES[provider]
    result = subprocess.CompletedProcess(
        args=["scrapy"],
        returncode=1,
        stdout="",
        stderr=signature.error_line + "\n" + signature.reason,
    )
    marker = tmp_path / "reached"
    marker.write_text(
        "INSERT INTO acquisition_release_entries (release_entry_seq) VALUES (?)"
    )
    if problem := release_failure_problem(result, marker, provider):
        pytest.fail(problem)


def test_onedrive_download_url_input_is_retained_but_never_published(tmp_path):
    """
    Real retained Graph input may contain a download URL; handoff may not.
    """
    with local_graph() as (origin, _state, _reached, _release, seen):
        successful(drive._crawl(tmp_path, origin))
        url = onedrive_download_url(origin)
        evidence = retained_evidence_with(
            tmp_path,
            "@microsoft.graph.downloadUrl",
            DOWNLOAD_SENTINEL,
            url,
        )
        if not evidence:
            pytest.fail("Synthetic download URL never entered retained crawl evidence")
        released = feed(tmp_path, "onedrive-resync-fixture", "onedrive")
        if not released:
            pytest.fail("OneDrive crawl did not produce a real release")
        metadata = publication_metadata(tmp_path)
        if "@microsoft.graph.downloadUrl" in metadata or url in metadata:
            pytest.fail("Download URL key or value leaked into handoff metadata")
        if any(path.startswith(DOWNLOAD_PATH) for path in seen):
            pytest.fail("Synthetic preauthenticated download URL was requested")
