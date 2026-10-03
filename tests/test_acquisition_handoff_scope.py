"""Reject relabelled direct impacts while retaining parent and proof roles."""

from dataclasses import replace

import pytest
from test_acquisition_handoff_catalog import (
    Kind,
    Stream,
    entry,
    fact,
    group,
    release,
    stage,
)
from test_acquisition_handoff_catalog import (
    catalog as _catalog,
)

from message_ingest.acquisition.handoff import ReleaseKind
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore

catalog = _catalog


@pytest.mark.parametrize("component", [False, True])
@pytest.mark.parametrize("field", ["scope", "parent"])
def test_direct_entry_preserves_scope_and_parent(catalog, component, field):
    """A direct impact cannot change its fact's scope or semantic owner."""
    spec = replace(
        fact(),
        scope_kind="folder",
        scope_identity="folder-a",
        parent_resource_kind="mailbox",
        parent_resource_identity="mailbox-a",
    )
    if component:
        spec = replace(
            spec,
            fact_kind=Kind.COMPONENT_OBSERVATION,
            resource_kind="attachment",
            resource_identity="attachment-a",
            parent_resource_kind="message",
            parent_resource_identity="message-a",
            component_kind="metadata",
        )
    staged = stage(catalog, spec)
    direct = replace(
        entry(staged),
        parent_resource_kind=spec.parent_resource_kind,
        parent_resource_identity=spec.parent_resource_identity,
        scope_kind="folder",
        scope_identity="folder-a",
    )
    bad = (
        replace(direct, scope_identity="folder-b")
        if field == "scope"
        else replace(direct, parent_resource_identity="other-owner")
    )
    with pytest.raises(ValueError, match="scope|parent"):
        release(catalog, group(), [bad])
    release(catalog, group(), [direct])
    if (
        len(
            AcquisitionHandoffStore(catalog).list_release_entries(
                "source", Stream.OUTLOOK_MAIL
            )
        )
        != 1
    ):
        pytest.fail("A legitimate direct impact was rejected")


def test_component_parent_impact_and_unrelated_profile_proof(catalog):
    """Retain exact child facts and independent profile proof."""
    child = stage(
        catalog,
        replace(
            fact(),
            fact_kind=Kind.COMPONENT_OBSERVATION,
            resource_kind="attachment",
            resource_identity="attachment-a",
            parent_resource_kind="message",
            parent_resource_identity="message-a",
            component_kind="metadata",
            scope_kind="folder",
            scope_identity="folder-a",
        ),
    )
    proof = stage(catalog, fact(resource="profile-proof"))
    impact = replace(
        entry(child),
        resource_kind="message",
        resource_identity="message-a",
        scope_kind="folder",
        scope_identity="folder-a",
        facts=((child.fact_id, "component"), (proof.fact_id, "proof")),
    )
    release(
        catalog,
        replace(group(), release_kind=ReleaseKind.RESOURCE_PROFILE),
        [impact],
    )
    store = AcquisitionHandoffStore(catalog)
    page = store.list_release_entries("source", Stream.OUTLOOK_MAIL)
    if len(page) != 1 or [
        f.fact_id for f in store.load_release_facts(page[0]["release_entry_seq"])
    ] != [child.fact_id, proof.fact_id]:
        pytest.fail("Parent impact or independent proof was lost")
