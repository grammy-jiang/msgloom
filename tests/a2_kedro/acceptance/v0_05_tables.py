"""
Gold case tables of the V0-05 acceptance test: what no P3 API can answer
(``NOT_MAPPABLE``, ``UNMAPPED``) and where the implementation differs from
the gold (``DISAGREEMENTS``). Every entry names its reason.
"""

from __future__ import annotations

#: Gold cases that no P3 API can answer. Each entry names the reason.
NOT_MAPPABLE: dict[str, str] = {
    "T0-03-P04": (
        "a chat-level component (chat_member_list) has no message ID; "
        "P3-05 component_refresh needs a message ID, so no entry can be built"
    ),
    "T0-03-N04": (
        "a null scope cannot be built: TeamsScope and NodeRef require a "
        "scope ID, so the input is unrepresentable (the gap is not graded)"
    ),
}
_PARSER = "contributed/quoted text is the P2 parser lane, checked in V0-04"
_GROUP = "ContextPublication has no group status and no group size field"
#: Gold keys of a covered case that no P3 API can answer.
UNMAPPED: dict[str, dict[str, str]] = {
    "T0-02-N01": {
        "records_kept": "NativeRelations holds one node per ID; version is no field",
        "reason": "prose; the result holds codes, not gold wording",
    },
    "T0-02-P02": {
        "contributed_text": _PARSER,
        "quoted_text": _PARSER,
        "attribution_line": _PARSER,
    },
    "T0-02-P03": {
        "contributed_text": _PARSER,
        "quoted_text": _PARSER,
        "ancestor_order": "relations sort by target ID; list position is no field",
    },
    "T0-02-P04": {"contributed_text": _PARSER},
    "T0-03-P07": {
        "older_version_overwritten": "TeamsEntry has no provider version",
        "deletion_marked": "TeamsGrouping has no deletion field (P3-08 does)",
    },
    "T0-03-P08": {
        "deletion_evidence_for_tch-d-1": "the caller supplies the authority text"
    },
    "T0-04-N02": {"group_size_od": _GROUP},
    "T0-04-N05": {"communication_groups_after": "no communication group is input"},
    "T0-04-N06": {"observation_kept": "the transition outcome keeps no observation"},
    **{
        f"T0-04-P0{n}": {"group_status": _GROUP, "group_size": _GROUP}
        for n in (1, 2, 3, 4, 6, 7, 8)
    },
}
UNMAPPED["T0-04-P06"]["treated_as_deleted"] = "a context record has no deletion field"

#: Implementation vs gold disagreements: reason and the pinned bad fields.
DISAGREEMENTS: dict[str, tuple[str, frozenset[str]]] = {
    "T0-02-N01": (
        (
            "P3-04 collapses two equal evidence copies of one Message-ID "
            "with no conflict (P3-01 flags them); gold: never silently merged"
        ),
        frozenset({"merged", "message_id_treated_as_unique_key"}),
    ),
    "T0-02-N02": (
        (
            "equal duplicate evidence of one Message-ID keeps a reply_to "
            "relation to it, so a parent is named; gold: chosen_parent null"
        ),
        frozenset({"chosen_parent"}),
    ),
    "T0-03-P07": (
        (
            "two versions of one channel message ID collapse to one member; "
            "TeamsEntry has no provider version; gold: both records kept"
        ),
        frozenset({"records_kept", "merged"}),
    ),
    **{
        f"T0-04-P0{n}": (
            f"ContextPublication has no {name} field (type_fields_unavailable)",
            frozenset({key}),
        )
        for n, name, key in (
            (6, "is_cancelled", "is_cancelled_preserved"),
            (7, "is_all_day", "is_all_day_preserved"),
            (8, "series_master_id", "series_master_id_preserved"),
        )
    },
}
