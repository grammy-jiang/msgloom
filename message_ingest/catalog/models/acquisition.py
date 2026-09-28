"""Provider-independent acquisition catalog models."""

from __future__ import annotations

from sqlalchemy import JSON, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SourceBinding(Base):
    """Stable logical source bound to one hashed external provider account."""

    __tablename__ = "source_bindings"

    source_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    key_scheme: Mapped[str] = mapped_column(String(96))
    account_key_sha256: Mapped[str] = mapped_column(String(64), index=True)
    binding_method: Mapped[str] = mapped_column(String(32))
    bound_at: Mapped[str] = mapped_column(String(40))


class RawHttpEvidence(Base):
    """
    One captured exchange, with credential-free headers and digest-named
    payload files.
    """

    __tablename__ = "raw_http_evidence"

    evidence_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    run_id: Mapped[str | None] = mapped_column(String(32), index=True)
    purpose: Mapped[str | None] = mapped_column(String(80), index=True)
    observed_at: Mapped[str] = mapped_column(String(40), index=True)
    origin: Mapped[str] = mapped_column(String(24), index=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64), index=True)

    request_url: Mapped[str] = mapped_column(Text)
    request_method: Mapped[str] = mapped_column(String(16))
    request_headers: Mapped[dict[str, list[str]]] = mapped_column(JSON)
    request_body_sha256: Mapped[str] = mapped_column(String(64), index=True)
    request_body_path: Mapped[str] = mapped_column(Text)
    request_body_bytes: Mapped[int] = mapped_column(Integer)

    response_url: Mapped[str | None] = mapped_column(Text)
    response_status: Mapped[int | None] = mapped_column(Integer)
    response_headers: Mapped[dict[str, list[str]]] = mapped_column(JSON)
    response_body_sha256: Mapped[str] = mapped_column(String(64), index=True)
    response_body_path: Mapped[str] = mapped_column(Text)
    response_body_bytes: Mapped[int] = mapped_column(Integer)
    response_flags: Mapped[list[str]] = mapped_column(JSON)
    error_type: Mapped[str | None] = mapped_column(String(160))
    error_message: Mapped[str | None] = mapped_column(Text)


__all__ = ["RawHttpEvidence", "SourceBinding"]
