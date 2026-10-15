"""Independent evidence pipelines may publish identical bytes concurrently."""

import hashlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

from message_ingest.pipelines.evidence import RawEvidencePipeline


def test_independent_writers_do_not_share_temporary_blob(tmp_path, monkeypatch):
    """Force both writers past the absent-file check before either writes."""
    body = b"identical Graph page"
    destination = tmp_path / (hashlib.sha256(body).hexdigest() + ".bin")
    barrier = Barrier(2)
    exists = Path.exists

    def observed_absent(path):
        result = exists(path)
        if path == destination:
            barrier.wait(timeout=10)
        return result

    monkeypatch.setattr(Path, "exists", observed_absent)
    pipelines = [object.__new__(RawEvidencePipeline) for _ in range(2)]
    for pipeline in pipelines:
        pipeline.raw_dir = tmp_path
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda pipeline: pipeline._store_blob(body), pipelines))
    if any(path != destination for _, path, _ in results):
        pytest.fail("Concurrent blob capture lost its content-addressed destination")
    if destination.read_bytes() != body or list(tmp_path.glob("*.tmp")):
        pytest.fail("Concurrent evidence lost original bytes or leaked temporary files")
