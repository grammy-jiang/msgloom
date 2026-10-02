"""Raw HTTP evidence persistence backed by the shared catalog session factory."""

from __future__ import annotations

from collections.abc import Iterable
from itertools import batched

from sqlalchemy import select

from message_ingest.catalog.models.acquisition import RawHttpEvidence

_PROVENANCE_QUERY_CHUNK = 500


class RawEvidenceStore:
    """Persist and query provider-independent raw HTTP evidence."""

    def __init__(self, catalog) -> None:
        self.catalog = catalog

    def record(self, evidence: RawHttpEvidence) -> str:
        """Insert an HTTP capture once, retaining the original row on replay."""
        with self.catalog.Session() as session, session.begin():
            existing = session.get(RawHttpEvidence, evidence.evidence_id)
            if existing is not None:
                return existing.evidence_id
            session.add(evidence)
        return evidence.evidence_id

    def find_cached_response(
        self,
        *,
        source_id: str,
        request_fingerprint: str,
        response_body_sha256: str,
    ) -> tuple[str, str] | None:
        """Find the latest matching response capture for cache aliasing."""
        with self.catalog.Session() as session:
            stmt = (
                select(RawHttpEvidence.evidence_id, RawHttpEvidence.observed_at)
                .where(
                    RawHttpEvidence.source_id == source_id,
                    RawHttpEvidence.request_fingerprint == request_fingerprint,
                    RawHttpEvidence.response_body_sha256 == response_body_sha256,
                    RawHttpEvidence.response_status.is_not(None),
                )
                .order_by(RawHttpEvidence.observed_at.desc())
                .limit(1)
            )
            row = session.execute(stmt).first()
            if row is None:
                return None
            return row.evidence_id, row.observed_at

    def run_ids_for(self, evidence_ids: Iterable[str]) -> dict[str, str | None]:
        """Return run provenance for a bounded set of committed evidence IDs."""
        normalized = tuple(dict.fromkeys(evidence_ids))
        if not normalized:
            return {}
        result: dict[str, str | None] = {}
        with self.catalog.Session() as session:
            for chunk in batched(normalized, _PROVENANCE_QUERY_CHUNK):
                rows = session.execute(
                    select(RawHttpEvidence.evidence_id, RawHttpEvidence.run_id).where(
                        RawHttpEvidence.evidence_id.in_(chunk)
                    )
                ).all()
                result.update({evidence_id: run_id for evidence_id, run_id in rows})
        return result

    def contains(self, evidence_id: str) -> bool:
        """Return whether *evidence_id* references a committed capture."""
        with self.catalog.Session() as session:
            return session.get(RawHttpEvidence, evidence_id) is not None


__all__ = ["RawEvidenceStore"]
