"""
Stage per-folder delta links and atomically promote a validated run.

Candidates are durable pending state. Only the idle extension may promote them
after every folder, reconciliation request, and pipeline write has completed.
An interrupted or failed crawl must retain the last committed links.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from message_ingest.catalog import Catalog, DeltaCheckpoint, DeltaCheckpointCandidate
from message_ingest.extensions.catalog import CatalogService


class OutlookDeltaCheckpointStore:
    """
    Checkpoint queries scoped to one source and the shared catalog engine.
    """

    def __init__(self, catalog_or_url: Catalog | str, source_id: str) -> None:
        """
        Borrow a crawler catalog, or own an engine for standalone inspection.
        """
        self._owns_catalog = isinstance(catalog_or_url, str)
        self.catalog = (
            Catalog(catalog_or_url)
            if isinstance(catalog_or_url, str)
            else catalog_or_url
        )
        self.source_id = source_id

    @classmethod
    def from_crawler(cls, crawler):
        """Use the engine that the catalog extension closes after the crawl."""
        return cls(
            CatalogService.from_crawler(crawler).catalog,
            crawler.settings["MSGLOOM_SOURCE_ID"],
        )

    def close(self) -> None:
        """
        Release only engines created by this store, never a borrowed engine.
        """
        if not self._owns_catalog:
            return
        self.catalog.close()

    def get_delta_link(self, folder_id: str) -> str | None:
        """
        Read a committed link; pending candidates are never resume points.
        """
        with self.catalog.Session() as session:
            return session.scalar(
                select(DeltaCheckpoint.delta_link).filter_by(
                    source_id=self.source_id,
                    folder_id=folder_id,
                )
            )

    def get_delta_links(self) -> dict[str, str]:
        """Load committed links once at startup to avoid a query per folder."""
        with self.catalog.Session() as session:
            rows = session.execute(
                select(DeltaCheckpoint.folder_id, DeltaCheckpoint.delta_link).filter_by(
                    source_id=self.source_id
                )
            ).all()
            return {folder_id: delta_link for folder_id, delta_link in rows}

    def write_candidate(
        self,
        *,
        run_id: str,
        folder_id: str,
        delta_link: str,
        observed_at: str,
        evidence_id: str | None = None,
    ) -> None:
        """
        Persist the final page's link without changing the committed cursor.

        The pipeline holds the crawler's write lock while calling this method.
        Replaying the same run/folder replaces its candidate in one
        transaction.
        """
        with self.catalog.Session() as session, session.begin():
            record = session.scalar(
                select(DeltaCheckpointCandidate).filter_by(
                    run_id=run_id,
                    source_id=self.source_id,
                    folder_id=folder_id,
                )
            )
            if record is None:
                session.add(
                    DeltaCheckpointCandidate(
                        run_id=run_id,
                        source_id=self.source_id,
                        folder_id=folder_id,
                        delta_link=delta_link,
                        evidence_id=evidence_id,
                        observed_at=observed_at,
                    )
                )
                return
            record.delta_link = delta_link
            record.evidence_id = evidence_id
            record.observed_at = observed_at

    def load_candidates(self, run_id: str) -> dict[str, DeltaCheckpointCandidate]:
        """
        Return this run's candidates for exact folder-set validation at idle.
        """
        with self.catalog.Session() as session:
            rows = session.scalars(
                select(DeltaCheckpointCandidate).filter_by(
                    run_id=run_id,
                    source_id=self.source_id,
                )
            ).all()
            return {row.folder_id: row for row in rows}

    def commit(self, run_id: str) -> int:
        """
        Promote all candidates together after the caller validates completion.

        One transaction updates the committed links and candidate timestamps.
        Any write failure rolls back the entire promotion, so a partial set of
        folders cannot become the next run's starting point.
        """
        committed_at = datetime.now(UTC).isoformat()
        with self.catalog.Session() as session, session.begin():
            candidates = session.scalars(
                select(DeltaCheckpointCandidate).filter_by(
                    run_id=run_id,
                    source_id=self.source_id,
                )
            ).all()
            for candidate in candidates:
                checkpoint = session.scalar(
                    select(DeltaCheckpoint).filter_by(
                        source_id=self.source_id,
                        folder_id=candidate.folder_id,
                    )
                )
                if checkpoint is None:
                    session.add(
                        DeltaCheckpoint(
                            source_id=self.source_id,
                            folder_id=candidate.folder_id,
                            delta_link=candidate.delta_link,
                            committed_at=committed_at,
                            run_id=run_id,
                        )
                    )
                else:
                    checkpoint.delta_link = candidate.delta_link
                    checkpoint.committed_at = committed_at
                    checkpoint.run_id = run_id
                candidate.committed_at = committed_at
            return len(candidates)


class OutlookFolderDeltaCheckpointStore:
    """Persist the single mailbox-level mailFolder delta cursor per source."""

    def __init__(self, catalog_or_url: Catalog | str, source_id: str) -> None:
        self._owns_catalog = isinstance(catalog_or_url, str)
        self.catalog = (
            Catalog(catalog_or_url)
            if isinstance(catalog_or_url, str)
            else catalog_or_url
        )
        self.source_id = source_id

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            CatalogService.from_crawler(crawler).catalog,
            crawler.settings["MSGLOOM_SOURCE_ID"],
        )

    def close(self) -> None:
        if self._owns_catalog:
            self.catalog.close()

    def get_delta_link(self) -> str | None:
        from message_ingest.catalog import FolderDeltaCheckpoint

        with self.catalog.Session() as session:
            return session.scalar(
                select(FolderDeltaCheckpoint.delta_link).filter_by(
                    source_id=self.source_id
                )
            )

    def write_candidate(
        self,
        *,
        run_id: str,
        delta_link: str,
        observed_at: str,
        evidence_id: str | None = None,
    ) -> None:
        from message_ingest.catalog import FolderDeltaCheckpointCandidate

        with self.catalog.Session() as session, session.begin():
            record = session.scalar(
                select(FolderDeltaCheckpointCandidate).filter_by(
                    source_id=self.source_id,
                    run_id=run_id,
                )
            )
            if record is None:
                session.add(
                    FolderDeltaCheckpointCandidate(
                        source_id=self.source_id,
                        run_id=run_id,
                        delta_link=delta_link,
                        evidence_id=evidence_id,
                        observed_at=observed_at,
                    )
                )
                return
            record.delta_link = delta_link
            record.evidence_id = evidence_id
            record.observed_at = observed_at

    def get_candidate(self, run_id: str):
        from message_ingest.catalog import FolderDeltaCheckpointCandidate

        with self.catalog.Session() as session:
            return session.scalar(
                select(FolderDeltaCheckpointCandidate).filter_by(
                    source_id=self.source_id,
                    run_id=run_id,
                )
            )

    def commit(self, run_id: str) -> None:
        from message_ingest.catalog import (
            FolderDeltaCheckpoint,
            FolderDeltaCheckpointCandidate,
        )

        committed_at = datetime.now(UTC).isoformat()
        with self.catalog.Session() as session, session.begin():
            candidate = session.scalar(
                select(FolderDeltaCheckpointCandidate).filter_by(
                    source_id=self.source_id,
                    run_id=run_id,
                )
            )
            if candidate is None:
                raise RuntimeError("folder delta candidate missing")
            checkpoint = session.scalar(
                select(FolderDeltaCheckpoint).filter_by(source_id=self.source_id)
            )
            if checkpoint is None:
                session.add(
                    FolderDeltaCheckpoint(
                        source_id=self.source_id,
                        delta_link=candidate.delta_link,
                        committed_at=committed_at,
                        run_id=run_id,
                    )
                )
            else:
                checkpoint.delta_link = candidate.delta_link
                checkpoint.committed_at = committed_at
                checkpoint.run_id = run_id
            candidate.committed_at = committed_at


__all__ = [
    "OutlookDeltaCheckpointStore",
    "OutlookFolderDeltaCheckpointStore",
]
