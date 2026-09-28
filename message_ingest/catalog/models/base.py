"""Shared SQLAlchemy declarative base for the catalog schema."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared metadata for schema creation; keep model changes migration-aware."""


__all__ = ["Base"]
