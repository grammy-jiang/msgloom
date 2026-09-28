"""Shared SQLite engine and session lifecycle for the local acquisition catalog."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import cast

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from message_ingest.catalog.schema import initialize_schema
from message_ingest.catalog.stores.evidence import RawEvidenceStore


class Catalog:
    """Own one SQLite engine/session factory shared by domain persistence stores."""

    def __init__(self, database_url: str) -> None:
        """Create the SQLite schema and restrict local file permissions."""
        self.database_url = database_url
        url = make_url(database_url)
        if url.get_backend_name() != "sqlite":
            raise ValueError("The current local catalog implementation requires SQLite")
        database = url.database
        in_memory = not database or database == ":memory:"
        if database and not in_memory:
            path = Path(database)
            path.parent.mkdir(parents=True, exist_ok=True)
            os.chmod(path.parent, 0o700)

        schema_image = initialize_schema(database_url, in_memory=in_memory)
        self.engine = create_engine(
            database_url,
            connect_args={
                "autocommit": False,
                "timeout": 30.0,
                **({"check_same_thread": False} if in_memory else {}),
            },
            **({"poolclass": QueuePool} if in_memory else {}),
            pool_size=1,
            max_overflow=0,
            pool_timeout=30.0,
        )
        if schema_image is not None:
            try:
                with self.engine.connect() as connection:
                    driver = cast(
                        sqlite3.Connection,
                        connection.connection.driver_connection,
                    )
                    driver.deserialize(schema_image)
            except BaseException:
                self.engine.dispose()
                raise
        self.Session: sessionmaker[Session] = sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
        )
        self.evidence = RawEvidenceStore(self)
        if database and not in_memory:
            os.chmod(Path(database), 0o600)

    def close(self) -> None:
        """Dispose the engine after outstanding pipeline work finishes."""
        self.engine.dispose()


__all__ = ["Catalog"]
