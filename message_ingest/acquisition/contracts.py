"""Structural contracts shared by acquisition resources."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EvidenceLinkedItem(Protocol):
    """
    Item with writable evidence reference and observation timestamp fields.

    ``EvidenceLinkPipeline`` mutates these attributes in place after validating
    a canonical persisted evidence record. Runtime Protocol checks establish
    only attribute presence; concrete resource items remain responsible for
    using compatible writable values.
    """

    evidence_id: str | None
    observed_at: str
