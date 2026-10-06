"""Explicit installed-spider mapping; pending paths are not qualified here."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Coverage:
    """Bind a release contract to receipts, candidates, or a named gap."""

    stream: str | None
    subject: str | None
    gate: str
    tests: tuple[str, ...] = ()
    pending: str | None = None
    candidate_tests: tuple[str, ...] = ()
    gap: str | None = None


AUTHORITY = "tests/test_a1_handoff_authority_nonmail.py::"
MAIL_DISCOVERY = (
    "tests/test_handoff_release_extension_mail_crawl.py::"
    "test_native_mail_discovery_release"
)
MAIL_DISCOVERY_CANDIDATES = (
    MAIL_DISCOVERY + "[0-2-complete-False]",
    MAIL_DISCOVERY + "[1-1-truncated-False]",
)
MAIL_SYNC = (
    "tests/test_outlook_mail_sync_crawl.py::"
    "test_mail_sync_delta_then_full_refresh_in_one_scrapy_process"
)
CALENDAR_NATIVE = (
    "tests/test_handoff_release_extension_calendar_crawl.py::"
    "test_calendar_native_release"
)
TODO_DISCOVERY = (
    "tests/test_todo_crawl.py::"
    "test_real_todo_command_crawls_all_surfaces_and_preserves_evidence"
)
CONTACTS_DISCOVERY = (
    "tests/test_handoff_release_extension_contacts_crawl.py::"
    "test_public_contacts_discover_releases_complete_additive_traversal"
)
ONEDRIVE_NATIVE = (
    "tests/test_handoff_release_extension_onedrive_crawl.py::"
    "test_native_inventory_and_independent_content[False-False]"
)
MAIL_CACHE = (
    "tests/test_handoff_release_extension_remaining_mail.py::"
    "test_native_mail_cache_release_retains_effective_policy[False]"
)
MAIL_RULE_SYNC = (
    "tests/test_outlook_mail_rule_sync_crawl.py::"
    "test_rules_enabled_sync_probes_then_fulls_only_selected_and_promotes_last"
)
FULL_FAILURE = (
    "tests/test_handoff_release_extension_remaining_full.py::"
    "test_native_full_failure_blocks_only_affected_complete_target"
)
CALENDAR_RESUME = (
    "tests/test_handoff_release_extension_calendar_crawl.py::"
    "test_calendar_jobdir_pause_resume_releases_one_group"
)


MATRIX = {
    "microsoft_profile": Coverage(
        None,
        None,
        "no_release",
        ("test_profile_keeps_evidence_without_handoff",),
        candidate_tests=(AUTHORITY + "test_profile_keeps_evidence_without_handoff",),
    ),
    "microsoft_todo_sync": Coverage(
        "todo",
        "todo_snapshot",
        "snapshot_promotion",
        (
            "test_todo_large_group_pages_and_unchanged_round",
            "test_todo_incomplete_and_release_failure_preserve_authority",
        ),
        candidate_tests=(
            AUTHORITY + "test_todo_large_group_pages_and_unchanged_round",
        ),
    ),
    "microsoft_contacts_sync": Coverage(
        "contacts",
        "contacts_snapshot",
        "snapshot_promotion",
        (
            "test_contacts_snapshot_identity_churn_and_atomic_failure",
            "test_contacts_new_snapshot_fences_inflight_delta",
        ),
        candidate_tests=(
            AUTHORITY + "test_contacts_snapshot_identity_churn_and_atomic_failure",
        ),
    ),
    "microsoft_contacts_delta": Coverage(
        "contacts",
        "contacts_delta",
        "winning_generation",
        (
            "test_contacts_sparse_delta_staging_and_release_rollback",
            "test_contacts_new_snapshot_fences_inflight_delta",
        ),
        candidate_tests=(
            AUTHORITY + "test_contacts_sparse_delta_staging_and_release_rollback",
        ),
    ),
    "microsoft_onedrive_delta": Coverage(
        "onedrive",
        "onedrive_delta",
        "checkpoint_promotion",
        (
            "test_onedrive_failed_reset_then_exact_winner",
            "test_onedrive_release_failure_preserves_prior_authority",
            "test_onedrive_unchanged_normal_delta_has_no_churn",
        ),
        candidate_tests=(AUTHORITY + "test_onedrive_failed_reset_then_exact_winner",),
    ),
    "outlook_calendar_delta": Coverage(
        "outlook_calendar",
        "calendar_window",
        "winning_fixed_window",
        (
            "test_calendar_410_winning_attempt_is_window_scoped",
            "test_calendar_release_failure_preserves_prior_window",
        ),
        candidate_tests=(
            AUTHORITY + "test_calendar_410_winning_attempt_is_window_scoped",
        ),
    ),
    "microsoft_todo_discover": Coverage(
        "todo",
        "discovery",
        "natural_idle",
        pending="Task8",
        candidate_tests=(TODO_DISCOVERY,),
    ),
    "microsoft_contacts_discover": Coverage(
        "contacts",
        "recursive_discovery",
        "natural_idle",
        pending="Task8",
        candidate_tests=(CONTACTS_DISCOVERY,),
    ),
    "microsoft_onedrive_discover": Coverage(
        "onedrive",
        "root_inventory",
        "natural_idle",
        pending="Task8",
        candidate_tests=(ONEDRIVE_NATIVE,),
    ),
    "microsoft_onedrive_content": Coverage(
        "onedrive",
        "content_target",
        "version_linked_capture",
        pending="Task8",
        candidate_tests=(ONEDRIVE_NATIVE,),
    ),
    "outlook_discover": Coverage(
        "outlook_mail",
        "configured_traversal",
        "natural_idle",
        pending="Task8",
        candidate_tests=(
            *MAIL_DISCOVERY_CANDIDATES,
            MAIL_CACHE,
        ),
    ),
    "outlook_folder_delta": Coverage(
        "outlook_mail",
        "folder_delta",
        "checkpoint_promotion",
        pending="Task9A",
        candidate_tests=(MAIL_SYNC,),
    ),
    "outlook_delta": Coverage(
        "outlook_mail",
        "mail_delta",
        "immediate_or_deferred",
        pending="Task9A",
        candidate_tests=(
            MAIL_SYNC,
            MAIL_RULE_SYNC,
        ),
    ),
    "outlook_full": Coverage(
        "outlook_mail",
        "message_profile",
        "target_completion",
        pending="Task8",
        candidate_tests=(FULL_FAILURE + "[False-callback-mail]",),
    ),
    "outlook_calendar_discover": Coverage(
        "outlook_calendar",
        "inventory",
        "natural_idle",
        pending="Task8",
        candidate_tests=(CALENDAR_NATIVE + "[False-False]",),
    ),
    "outlook_calendar_window": Coverage(
        "outlook_calendar",
        "fixed_window",
        "natural_idle_resume",
        pending="Task8",
        candidate_tests=(
            CALENDAR_NATIVE + "[False-True]",
            CALENDAR_RESUME,
        ),
    ),
    "outlook_calendar_full": Coverage(
        "outlook_calendar",
        "event_profile",
        "target_completion",
        pending="Task8",
        candidate_tests=(FULL_FAILURE + "[False-callback-calendar]",),
    ),
}


TASK10_EXECUTABLE_SCENARIOS = {
    "mail_discovery": MAIL_DISCOVERY_CANDIDATES,
    "mail_cache_replay": (MAIL_CACHE,),
    "mail_immediate_delta": (MAIL_SYNC,),
    "mail_rules_deferred_full": (MAIL_RULE_SYNC,),
    "mail_folder_delta": (MAIL_SYNC,),
    "calendar_discovery_window_resume": (
        *MATRIX["outlook_calendar_discover"].candidate_tests,
        *MATRIX["outlook_calendar_window"].candidate_tests,
    ),
    "calendar_delta": MATRIX["outlook_calendar_delta"].candidate_tests,
    "calendar_full_partial_success": MATRIX["outlook_calendar_full"].candidate_tests,
    "todo_discover_sync": (
        *MATRIX["microsoft_todo_discover"].candidate_tests,
        *MATRIX["microsoft_todo_sync"].candidate_tests,
    ),
    "contacts_discover_sync_delta": (
        *MATRIX["microsoft_contacts_discover"].candidate_tests,
        *MATRIX["microsoft_contacts_sync"].candidate_tests,
        *MATRIX["microsoft_contacts_delta"].candidate_tests,
    ),
    "onedrive_discover_delta_reset_content": (
        *MATRIX["microsoft_onedrive_discover"].candidate_tests,
        *MATRIX["microsoft_onedrive_delta"].candidate_tests,
        *MATRIX["microsoft_onedrive_content"].candidate_tests,
    ),
    "profile_no_release": MATRIX["microsoft_profile"].candidate_tests,
}

TASK10_SCENARIO_GAPS = {
    "mail_discovery": (
        "Normal and truncated nodes remain candidates until a passing exact-candidate "
        "Task 10 runtime receipt replaces the retained RED evidence."
    ),
}

# Task 15 owns these scenario receipts. Task 10 must not prefill them from
# spider candidate names or treat collection as runtime qualification.
TASK15_SCENARIOS_PENDING = tuple(str(index) for index in range(1, 14))
