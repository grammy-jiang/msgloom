"""Source-native grouping never invents cross-source topic identity."""

from datetime import UTC, datetime

import pytest

from msgloom.contracts import VersionRef
from msgloom.preparation.filtering import (
    AddressNormalization,
    FilterConfig,
    FilterOutcome,
    apply_filters,
)
from msgloom.preparation.grouping import GroupStatus, group_records
from msgloom.preparation.records import (
    FilteringDecision,
    FilteringDisposition,
    NativeRelationship,
    PreparedRecord,
    PreparedSourceType,
)
from tests.prepared_contract_fixtures import prepared_record


def _filter(record: PreparedRecord):
    config = FilterConfig(
        reference=VersionRef("filter_config", "synthetic", "v1"),
        address_normalization=AddressNormalization.EXACT,
        rules=(),
    )
    result = apply_filters(record, config)
    if result.outcome is not FilterOutcome.INCLUDED:
        pytest.fail("default synthetic filter should include the record")
    return result


def _record(
    identity: str,
    source_type: PreparedSourceType,
    *,
    subject: str | None = "Shared subject",
    relationships: tuple[NativeRelationship, ...] = (),
    scope: str | None = "scope-a",
) -> PreparedRecord:
    base = prepared_record()
    scoped_relationships = relationships
    if scope is not None:
        scoped_relationships += (
            NativeRelationship(
                kind="source_scope",
                target=VersionRef("source_scope", scope, "v1"),
            ),
        )
    return PreparedRecord(
        source=VersionRef(source_type.value, identity, "v1"),
        source_type=source_type,
        sender=base.sender,
        author=base.author,
        recipients=base.recipients,
        source_time=datetime(2026, 9, 29, 7, 15, tzinfo=UTC),
        subject=subject,
        body="Synthetic body.",
        relationships=scoped_relationships,
        attachments=(),
        parsed_contents=(),
        limitations=(),
        source_mappings=(),
        filtering=FilteringDecision(disposition=FilteringDisposition.PENDING),
    )


def _group(records: tuple[PreparedRecord, ...]):
    return group_records(records, tuple(_filter(record) for record in records))


def test_same_subject_different_outlook_work_stays_separate() -> None:
    groups = _group(
        (
            _record("mail-1", PreparedSourceType.OUTLOOK_EMAIL),
            _record("mail-2", PreparedSourceType.OUTLOOK_EMAIL),
        )
    )
    if len(groups) != 2 or any(
        group.status is not GroupStatus.NONE for group in groups
    ):
        pytest.fail("subject equality alone must never create an Outlook group")


def test_outlook_conversation_membership_is_uncertain_support_only() -> None:
    conversation = VersionRef("outlook_conversation", "scope-a:conv-1", "v1")
    records = (
        _record(
            "mail-1",
            PreparedSourceType.OUTLOOK_EMAIL,
            relationships=(
                NativeRelationship(kind="outlook_conversation", target=conversation),
            ),
        ),
        _record(
            "mail-2",
            PreparedSourceType.OUTLOOK_EMAIL,
            relationships=(
                NativeRelationship(kind="outlook_conversation", target=conversation),
            ),
        ),
    )

    groups = _group(records)
    if len(groups) != 1 or groups[0].status is not GroupStatus.UNCERTAIN:
        pytest.fail("conversation membership may support only an uncertain candidate")


def test_direct_outlook_reply_confirms_only_when_parent_is_present() -> None:
    parent = _record("mail-1", PreparedSourceType.OUTLOOK_EMAIL)
    reply = _record(
        "mail-2",
        PreparedSourceType.OUTLOOK_EMAIL,
        relationships=(NativeRelationship(kind="in_reply_to", target=parent.source),),
    )
    confirmed = _group((reply, parent))
    missing = _group((reply,))

    if len(confirmed) != 1 or confirmed[0].status is not GroupStatus.CONFIRMED:
        pytest.fail("an exact present Outlook reply parent should confirm membership")
    if len(missing) != 1 or missing[0].status is not GroupStatus.UNCERTAIN:
        pytest.fail("a missing reply parent must remain uncertain")


def test_ambiguous_native_parent_links_do_not_confirm() -> None:
    first = VersionRef("outlook_email", "mail-1", "v1")
    second = VersionRef("outlook_email", "mail-2", "v1")
    record = _record(
        "mail-3",
        PreparedSourceType.OUTLOOK_EMAIL,
        relationships=(
            NativeRelationship(kind="in_reply_to", target=first),
            NativeRelationship(kind="in_reply_to", target=second),
        ),
    )
    groups = _group((record,))
    if groups[0].status is not GroupStatus.UNCERTAIN:
        pytest.fail("ambiguous native parent evidence must not confirm a group")


def test_teams_channel_reply_confirms_but_chat_requires_explicit_relation() -> None:
    root = _record("root", PreparedSourceType.TEAMS_CHANNEL_MESSAGE)
    reply = _record(
        "reply",
        PreparedSourceType.TEAMS_CHANNEL_MESSAGE,
        relationships=(
            NativeRelationship(kind="teams_channel_reply_to", target=root.source),
        ),
    )
    chat_a = _record("chat-a", PreparedSourceType.TEAMS_CHAT_MESSAGE)
    chat_b = _record("chat-b", PreparedSourceType.TEAMS_CHAT_MESSAGE)

    channel_groups = _group((reply, root))
    chat_groups = _group((chat_b, chat_a))

    if channel_groups[0].status is not GroupStatus.CONFIRMED:
        pytest.fail("channel root/reply evidence should confirm a group")
    if len(chat_groups) != 2 or any(
        group.status is not GroupStatus.NONE for group in chat_groups
    ):
        pytest.fail("chat messages without supported relationships stay separate")


@pytest.mark.parametrize(
    "source_type",
    [
        PreparedSourceType.TODO,
        PreparedSourceType.ONEDRIVE,
        PreparedSourceType.CONTACT,
    ],
)
def test_context_sources_never_form_automatic_communication_groups(
    source_type: PreparedSourceType,
) -> None:
    first = _record("one", source_type)
    second = _record(
        "two",
        source_type,
        relationships=(NativeRelationship(kind="in_reply_to", target=first.source),),
    )
    groups = _group((first, second))
    if len(groups) != 2 or any(
        group.status is not GroupStatus.NONE for group in groups
    ):
        pytest.fail("context sources must remain independent communication inputs")


def test_grouping_is_order_independent_and_never_cross_source_joins() -> None:
    root = _record("shared", PreparedSourceType.TEAMS_CHANNEL_MESSAGE)
    reply = _record(
        "reply",
        PreparedSourceType.TEAMS_CHANNEL_MESSAGE,
        relationships=(
            NativeRelationship(kind="teams_channel_reply_to", target=root.source),
        ),
    )
    mail = _record(
        "shared",
        PreparedSourceType.OUTLOOK_EMAIL,
        relationships=(NativeRelationship(kind="in_reply_to", target=root.source),),
    )

    first = _group((mail, reply, root))
    second = _group((root, mail, reply))
    if first != second:
        pytest.fail("group output must be canonical regardless of input order")
    if any(len(group.members) > 1 and mail.source in group.members for group in first):
        pytest.fail("relationships must never join different source types")


def test_chat_explicit_reply_can_confirm_and_channel_missing_root_is_uncertain() -> (
    None
):
    chat_root = _record("chat-root", PreparedSourceType.TEAMS_CHAT_MESSAGE)
    chat_reply = _record(
        "chat-reply",
        PreparedSourceType.TEAMS_CHAT_MESSAGE,
        relationships=(
            NativeRelationship(kind="teams_chat_reply_to", target=chat_root.source),
        ),
    )
    missing_channel_root = _record(
        "channel-reply",
        PreparedSourceType.TEAMS_CHANNEL_MESSAGE,
        relationships=(
            NativeRelationship(
                kind="teams_channel_reply_to",
                target=VersionRef(
                    PreparedSourceType.TEAMS_CHANNEL_MESSAGE.value,
                    "missing-root",
                    "v1",
                ),
            ),
        ),
    )

    chat_groups = _group((chat_reply, chat_root))
    channel_groups = _group((missing_channel_root,))
    if chat_groups[0].status is not GroupStatus.CONFIRMED:
        pytest.fail("explicit supported chat reply evidence may confirm membership")
    if channel_groups[0].status is not GroupStatus.UNCERTAIN:
        pytest.fail("a missing channel root must remain visibly uncertain")


def test_excluded_records_remain_replayable_and_do_not_enter_groups() -> None:
    from msgloom.preparation.filtering import FilterEffect, FilterRule

    parent = _record("excluded-parent", PreparedSourceType.OUTLOOK_EMAIL)
    reply = _record(
        "included-reply",
        PreparedSourceType.OUTLOOK_EMAIL,
        relationships=(NativeRelationship(kind="in_reply_to", target=parent.source),),
    )
    exclusion = FilterConfig(
        reference=VersionRef("filter_config", "exclude-one", "v1"),
        address_normalization=AddressNormalization.EXACT,
        rules=(
            FilterRule(
                reference=VersionRef("filter_rule", "exclude-parent", "v1"),
                effect=FilterEffect.EXCLUDE,
                sender_addresses=("sender-1",),
            ),
        ),
    )
    excluded = apply_filters(parent, exclusion)
    included = _filter(reply)
    groups = group_records((parent, reply), (excluded, included))

    excluded_group = next(group for group in groups if parent.source in group.members)
    if excluded_group.status is not GroupStatus.NONE:
        pytest.fail("excluded input must not enter semantic communication grouping")
    if (
        excluded.input != parent.source
        or parent.filtering.disposition is not FilteringDisposition.PENDING
    ):
        pytest.fail("exclusion must preserve the exact replayable prepared input")


@pytest.mark.parametrize(
    "identities",
    [
        ("a-child", "b-child", "y-parent", "z-parent"),
        ("y-child", "z-child", "a-parent", "b-parent"),
    ],
)
def test_missing_ancestry_closes_before_components_regardless_of_identity_order(
    identities: tuple[str, str, str, str],
) -> None:
    first_id, second_id, shared_id, parent_id = identities
    missing = VersionRef("outlook_email", "missing-parent", "v1")
    parent = _record(
        parent_id,
        PreparedSourceType.OUTLOOK_EMAIL,
        relationships=(NativeRelationship(kind="in_reply_to", target=missing),),
    )
    shared = _record(
        shared_id,
        PreparedSourceType.OUTLOOK_EMAIL,
        relationships=(NativeRelationship(kind="in_reply_to", target=parent.source),),
    )
    first = _record(
        first_id,
        PreparedSourceType.OUTLOOK_EMAIL,
        relationships=(NativeRelationship(kind="in_reply_to", target=shared.source),),
    )
    second = _record(
        second_id,
        PreparedSourceType.OUTLOOK_EMAIL,
        relationships=(NativeRelationship(kind="in_reply_to", target=shared.source),),
    )

    groups = _group((first, second, shared, parent))
    if any(group.status is GroupStatus.CONFIRMED for group in groups):
        pytest.fail("missing ancestry must close before any descendant component union")
    if {member for group in groups for member in group.members} != {
        first.source,
        second.source,
        shared.source,
        parent.source,
    }:
        pytest.fail("ambiguity closure must preserve every input disposition")


def test_self_links_and_cycles_never_manufacture_confirmed_membership() -> None:
    self_ref = VersionRef("outlook_email", "self", "v1")
    self_link = _record(
        "self",
        PreparedSourceType.OUTLOOK_EMAIL,
        relationships=(NativeRelationship(kind="in_reply_to", target=self_ref),),
    )
    first_ref = VersionRef("outlook_email", "cycle-a", "v1")
    second_ref = VersionRef("outlook_email", "cycle-b", "v1")
    first = _record(
        "cycle-a",
        PreparedSourceType.OUTLOOK_EMAIL,
        relationships=(NativeRelationship(kind="in_reply_to", target=second_ref),),
    )
    second = _record(
        "cycle-b",
        PreparedSourceType.OUTLOOK_EMAIL,
        relationships=(NativeRelationship(kind="in_reply_to", target=first_ref),),
    )

    for records in ((self_link,), (first, second)):
        groups = _group(records)
        if any(group.status is GroupStatus.CONFIRMED for group in groups):
            pytest.fail("self-links and cycles cannot confirm membership")
        if any(group.status is not GroupStatus.UNCERTAIN for group in groups):
            pytest.fail("invalid native-link topology must remain visibly uncertain")


def test_native_confirmation_requires_exact_compatible_source_scope() -> None:
    parent = _record("parent", PreparedSourceType.OUTLOOK_EMAIL, scope="scope-b")
    reply = _record(
        "reply",
        PreparedSourceType.OUTLOOK_EMAIL,
        scope="scope-a",
        relationships=(NativeRelationship(kind="in_reply_to", target=parent.source),),
    )
    groups = _group((reply, parent))
    if any(group.status is GroupStatus.CONFIRMED for group in groups):
        pytest.fail("different declared source scopes must never confirm or merge")
    reply_group = next(group for group in groups if reply.source in group.members)
    if reply_group.status is not GroupStatus.UNCERTAIN:
        pytest.fail("cross-scope native parent evidence must remain uncertain")


def test_missing_or_multiple_scope_evidence_blocks_native_confirmation() -> None:
    parent = _record(
        "parent",
        PreparedSourceType.OUTLOOK_EMAIL,
        scope=None,
    )
    reply = _record(
        "reply",
        PreparedSourceType.OUTLOOK_EMAIL,
        scope="scope-a",
        relationships=(NativeRelationship(kind="in_reply_to", target=parent.source),),
    )
    extra_scope = NativeRelationship(
        kind="source_scope",
        target=VersionRef("source_scope", "scope-b", "v1"),
    )
    ambiguous = _record(
        "ambiguous",
        PreparedSourceType.OUTLOOK_EMAIL,
        relationships=(
            NativeRelationship(kind="in_reply_to", target=reply.source),
            extra_scope,
        ),
    )
    groups = _group((ambiguous, reply, parent))
    if any(group.status is GroupStatus.CONFIRMED for group in groups):
        pytest.fail("missing or multiple source scope evidence must block confirmation")
    if not all(group.status is GroupStatus.UNCERTAIN for group in groups):
        pytest.fail("scope defects in native ancestry must remain visibly uncertain")


def test_conversation_candidates_never_merge_different_declared_scopes() -> None:
    conversation = VersionRef("outlook_conversation", "qualified:conv", "v1")
    first = _record(
        "mail-a",
        PreparedSourceType.OUTLOOK_EMAIL,
        scope="scope-a",
        relationships=(
            NativeRelationship(kind="outlook_conversation", target=conversation),
        ),
    )
    second = _record(
        "mail-b",
        PreparedSourceType.OUTLOOK_EMAIL,
        scope="scope-b",
        relationships=(
            NativeRelationship(kind="outlook_conversation", target=conversation),
        ),
    )
    groups = _group((first, second))
    if len(groups) != 2 or any(len(group.members) != 1 for group in groups):
        pytest.fail("conversation candidates cannot merge independent source scopes")
    if any(group.status is not GroupStatus.UNCERTAIN for group in groups):
        pytest.fail("conversation membership must remain support-only uncertainty")
