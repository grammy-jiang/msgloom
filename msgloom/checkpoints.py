from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from msgloom.catalog import Catalog
from msgloom.services import get_catalog_service


class OutlookDeltaCheckpointStore:
    """Per-folder Outlook delta state backed by the crawler's SQLAlchemy catalog."""

    def __init__(self, catalog_or_url: Catalog | str, source_id: str) -> None:
        if isinstance(catalog_or_url, Catalog):
            self.catalog = catalog_or_url
            self._owns_catalog = False
        else:
            self.catalog = Catalog(catalog_or_url)
            self._owns_catalog = True
        self.source_id = source_id

    @classmethod
    def from_crawler(cls, crawler):
        service = get_catalog_service(crawler)
        return cls(service.catalog, crawler.settings["MSGLOOM_SOURCE_ID"])

    def close(self) -> None:
        if self._owns_catalog:
            self.catalog.close()

    def get_delta_link(self, folder_id: str) -> str | None:
        return self.catalog.get_delta_link(
            source_id=self.source_id,
            folder_id=folder_id,
        )

    def get_delta_links(self) -> dict[str, str]:
        return self.catalog.get_delta_links(source_id=self.source_id)

    def write_candidate(
        self,
        *,
        run_id: str,
        folder_id: str,
        delta_link: str,
        observed_at: str,
        evidence_id: str | None = None,
    ) -> None:
        self.catalog.write_delta_candidate(
            run_id=run_id,
            source_id=self.source_id,
            folder_id=folder_id,
            delta_link=delta_link,
            evidence_id=evidence_id,
            observed_at=observed_at,
        )

    def load_candidates(self, run_id: str) -> dict[str, Any]:
        return self.catalog.load_delta_candidates(
            run_id=run_id,
            source_id=self.source_id,
        )

    def commit(self, run_id: str) -> int:
        return self.catalog.commit_delta_candidates(
            run_id=run_id,
            source_id=self.source_id,
            committed_at=datetime.now(UTC).isoformat(),
        )
