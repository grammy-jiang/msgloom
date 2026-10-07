"""Immutable Mail captures, exact applications, pages and inventory members."""

from sqlalchemy import CheckConstraint, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ...base import Base


class MailComponentCapture(Base):
    """
    Retain selected bytes and bounded metadata independently of authority.
    """

    __tablename__ = "mail_component_captures"
    __table_args__ = (
        CheckConstraint("length(payload) <= 8192", name="mail_capture_v1"),
    )
    capture_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    message_id: Mapped[str] = mapped_column(Text)
    selection_id: Mapped[str] = mapped_column(String(64), index=True)
    parent_key: Mapped[str] = mapped_column(String(64))
    component: Mapped[str] = mapped_column(String(2048))
    resource_id: Mapped[str] = mapped_column(Text)
    observed_at: Mapped[str] = mapped_column(String(40))
    ordinal: Mapped[int] = mapped_column(Integer)
    payload: Mapped[str] = mapped_column(Text)


class MailApplicationBinding(Base):
    """Bind a selection or capture to an exact immutable fact application."""

    __tablename__ = "mail_application_bindings"
    __table_args__ = (
        CheckConstraint("length(payload) <= 8192", name="mail_application_v1"),
    )
    binding_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    message_id: Mapped[str] = mapped_column(Text)
    selection_id: Mapped[str] = mapped_column(String(64), index=True)
    capture_id: Mapped[str | None] = mapped_column(String(64), index=True)
    primary_fact_id: Mapped[str] = mapped_column(String(64), index=True)
    fact_id: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[str] = mapped_column(Text)


class MailInventoryPage(Base):
    """One explicit traversal link, never an inferred run-wide page scan."""

    __tablename__ = "mail_inventory_pages"
    __table_args__ = (
        UniqueConstraint("source_id", "inventory_id", "page_number"),
        CheckConstraint("page_number >= 1", name="mail_page_ordinal_v1"),
        CheckConstraint("length(payload) <= 8192", name="mail_page_v1"),
    )
    page_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(200), index=True)
    message_id: Mapped[str] = mapped_column(Text)
    selection_id: Mapped[str] = mapped_column(String(64))
    parent_key: Mapped[str] = mapped_column(String(64))
    inventory_id: Mapped[str] = mapped_column(String(64), index=True)
    page_number: Mapped[int] = mapped_column(Integer)
    previous_page_id: Mapped[str | None] = mapped_column(String(64))
    payload: Mapped[str] = mapped_column(Text)


class MailInventoryMember(Base):
    """Exact retained member projection and metadata capture for one page."""

    __tablename__ = "mail_inventory_members"
    __table_args__ = (
        CheckConstraint("length(payload) <= 4096", name="mail_member_v1"),
    )
    page_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    member_id: Mapped[str] = mapped_column(Text, primary_key=True)
    capture_id: Mapped[str] = mapped_column(String(64))
    payload: Mapped[str] = mapped_column(Text)


MAIL_BINDING_TABLES = tuple(
    Base.metadata.tables[model.__tablename__]
    for model in (
        MailComponentCapture,
        MailApplicationBinding,
        MailInventoryPage,
        MailInventoryMember,
    )
)
