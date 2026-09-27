"""
Verify the catalog uses the expected SQLAlchemy schema without legacy tables.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import inspect

from message_ingest.catalog import Base, Catalog


def _url(path: Path) -> str:
    return f"sqlite:///{path}"


def test_fresh_catalog_creates_current_sqlalchemy_schema(tmp_path: Path) -> None:
    path = tmp_path / "catalog.sqlite3"

    catalog = Catalog(_url(path))
    try:
        with catalog.engine.connect() as connection:
            tables = set(inspect(connection).get_table_names())
        if set(Base.metadata.tables) != tables:
            pytest.fail("Expected: set(Base.metadata.tables) == tables")
    finally:
        catalog.close()

    if path.stat().st_mode & 511 != 384:
        pytest.fail("Expected: path.stat().st_mode & 0o777 == 0o600")


def test_reopening_current_catalog_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "catalog.sqlite3"

    first = Catalog(_url(path))
    first.close()
    second = Catalog(_url(path))
    try:
        with second.engine.connect() as connection:
            tables = set(inspect(connection).get_table_names())
        if set(Base.metadata.tables) != tables:
            pytest.fail("Expected: set(Base.metadata.tables) == tables")
    finally:
        second.close()
