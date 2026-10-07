"""Contacts lifecycle extensions."""

from .checkpoint import (
    ContactsDeltaCheckpointExtension,
    ContactsSnapshotPromotionExtension,
)

__all__ = ["ContactsDeltaCheckpointExtension", "ContactsSnapshotPromotionExtension"]
