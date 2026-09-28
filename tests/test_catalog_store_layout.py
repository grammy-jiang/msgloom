"""Lock catalog lifecycle and domain persistence into separate modules."""

from __future__ import annotations

import pytest

from message_ingest.catalog import (
    Catalog,
    OutlookCalendarStore,
    OutlookMailStore,
    RawEvidenceStore,
)


def test_catalog_owns_lifecycle_not_domain_operations() -> None:
    catalog = Catalog("sqlite:///:memory:")
    try:
        if not isinstance(catalog.evidence, RawEvidenceStore):
            pytest.fail("Catalog must expose the provider-independent evidence store")
        forbidden = {
            "record_message",
            "record_folder_removal",
            "set_message_surface",
            "upsert_attachment",
            "upsert_folder",
            "get_message_state",
            "get_message_surfaces",
            "get_attachments",
        }
        leaked = sorted(name for name in forbidden if hasattr(catalog, name))
        if leaked:
            pytest.fail(f"Domain persistence leaked back into Catalog: {leaked!r}")
    finally:
        catalog.close()


def test_outlook_domain_stores_live_in_catalog_store_tree() -> None:
    expected = {
        OutlookMailStore: "message_ingest.catalog.stores.microsoft.outlook.email",
        OutlookCalendarStore: "message_ingest.catalog.stores.microsoft.outlook.calendar",
        RawEvidenceStore: "message_ingest.catalog.stores.evidence",
    }
    for cls, module in expected.items():
        if cls.__module__ != module:
            pytest.fail(
                f"{cls.__name__} belongs to {cls.__module__!r}, expected {module!r}"
            )
