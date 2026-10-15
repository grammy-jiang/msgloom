"""Mail-local provisional projections and sealed authority applications."""

from sqlalchemy import CheckConstraint, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ...base import Base


class MailAuthorityObservation(Base):
    """
    Retain original ownership and a run-local application order.

    ``sequence`` is local capture order, never Graph provider order. Payloads
    contain the exact supplied fields and the resolved projection pinned at
    intake. They cannot be reconstructed from a later mutable resource row.
    """

    __tablename__ = "mail_authority_observations"
    __table_args__ = (
        CheckConstraint("authority_kind IN ('message_delta','folder_delta')"),
        Index(
            "mail_authority_run_scope",
            "source_id",
            "run_id",
            "authority_kind",
            "scope_identity",
            "effective_key",
            "sequence",
        ),
        Index("mail_authority_fact", "fact_id"),
        Index(
            "mail_authority_resource",
            "source_id",
            "resource_kind",
            "resource_id",
            "sequence",
        ),
    )
    sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str] = mapped_column(String(200))
    run_id: Mapped[str] = mapped_column(String(32))
    authority_kind: Mapped[str] = mapped_column(String(32))
    scope_identity: Mapped[str] = mapped_column(Text)
    resource_kind: Mapped[str] = mapped_column(String(32))
    resource_id: Mapped[str] = mapped_column(Text)
    effective_key: Mapped[str] = mapped_column(String(64))
    capture_key: Mapped[str] = mapped_column(String(64))
    fact_id: Mapped[str] = mapped_column(String(64))
    payload: Mapped[str] = mapped_column(Text)


class MailAuthorityDecision(Base):
    """Seal all promotion inputs, selected applications and return values."""

    __tablename__ = "mail_authority_decisions"
    source_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    authority_kind: Mapped[str] = mapped_column(String(32), primary_key=True)
    input_digest: Mapped[str] = mapped_column(String(64))
    payload: Mapped[str] = mapped_column(Text)


class MailProjectionOwner(Base):
    """
    Identify the accepted delta projection for scope-aware freshness.

    Independent writes clear this pointer. Absence means independent or
    legacy state, which retains the conservative timestamp freshness rule.
    """

    __tablename__ = "mail_projection_owners"
    effective_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    observation_sequence: Mapped[int] = mapped_column(Integer)


MAIL_AUTHORITY_TABLES = tuple(
    Base.metadata.tables[model.__tablename__]
    for model in (MailAuthorityObservation, MailAuthorityDecision, MailProjectionOwner)
)
