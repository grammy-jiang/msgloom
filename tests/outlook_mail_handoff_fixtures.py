"""Local saved evidence for Mail planning and handoff fixtures."""

import hashlib
from pathlib import Path

from sqlalchemy.engine import make_url

from message_ingest.catalog.models.acquisition import RawHttpEvidence


def saved_mail_evidence(
    catalog,
    *,
    evidence_id,
    source_id="source-1",
    run_id="fixture-run",
    observed_at="2026-09-28T00:00:00+00:00",
    purpose="test",
    body=b"{}",
    origin="network",
):
    """Save real local bytes with a verified digest and explicit provenance."""
    database = make_url(catalog.database_url).database
    if not database or database == ":memory:":
        raise ValueError("Mail evidence fixture needs an isolated file catalog")
    root = Path(database).parent / "mail-fixture-evidence"
    root.mkdir(exist_ok=True)
    digest = hashlib.sha256(body).hexdigest()
    path = root / f"{digest}.bin"
    path.write_bytes(body)
    catalog.evidence.record(
        RawHttpEvidence(
            evidence_id=evidence_id,
            source_id=source_id,
            run_id=run_id,
            purpose=purpose,
            observed_at=observed_at,
            origin=origin,
            request_fingerprint=hashlib.sha256(evidence_id.encode()).hexdigest(),
            request_url="https://example.test/synthetic",
            request_method="GET",
            request_headers={},
            request_body_sha256=digest,
            request_body_path=str(path),
            request_body_bytes=len(body),
            response_url="https://example.test/synthetic",
            response_status=200,
            response_headers={},
            response_body_sha256=digest,
            response_body_path=str(path),
            response_body_bytes=len(body),
            response_flags=[],
            error_type=None,
            error_message=None,
        )
    )
    return evidence_id
