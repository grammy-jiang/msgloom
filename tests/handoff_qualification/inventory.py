"""Explicit installed-spider mapping; pending paths are not qualified here."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Coverage:
    """Bind a release contract to executable tests or a named dependency."""

    stream: str | None
    subject: str | None
    gate: str
    tests: tuple[str, ...] = ()
    pending: str | None = None


MATRIX = {
    "microsoft_profile": Coverage(
        None, None, "no_release", ("test_profile_keeps_evidence_without_handoff",)
    ),
    "microsoft_todo_sync": Coverage(
        "todo",
        "todo_snapshot",
        "snapshot_promotion",
        (
            "test_todo_large_group_pages_and_unchanged_round",
            "test_todo_incomplete_and_release_failure_preserve_authority",
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
    ),
    "microsoft_contacts_delta": Coverage(
        "contacts",
        "contacts_delta",
        "winning_generation",
        (
            "test_contacts_sparse_delta_staging_and_release_rollback",
            "test_contacts_new_snapshot_fences_inflight_delta",
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
    ),
    "outlook_calendar_delta": Coverage(
        "outlook_calendar",
        "calendar_window",
        "winning_fixed_window",
        (
            "test_calendar_410_winning_attempt_is_window_scoped",
            "test_calendar_release_failure_preserves_prior_window",
        ),
    ),
    "microsoft_todo_discover": Coverage(
        "todo", "discovery", "natural_idle", pending="Task8"
    ),
    "microsoft_contacts_discover": Coverage(
        "contacts", "recursive_discovery", "natural_idle", pending="Task8"
    ),
    "microsoft_onedrive_discover": Coverage(
        "onedrive", "root_inventory", "natural_idle", pending="Task8"
    ),
    "microsoft_onedrive_content": Coverage(
        "onedrive", "content_target", "version_linked_capture", pending="Task8"
    ),
    "outlook_discover": Coverage(
        "outlook_mail", "configured_traversal", "natural_idle", pending="Task8"
    ),
    "outlook_folder_delta": Coverage(
        "outlook_mail", "folder_delta", "checkpoint_promotion", pending="Task9A"
    ),
    "outlook_delta": Coverage(
        "outlook_mail", "mail_delta", "immediate_or_deferred", pending="Task9A"
    ),
    "outlook_full": Coverage(
        "outlook_mail", "message_profile", "target_completion", pending="Task8"
    ),
    "outlook_calendar_discover": Coverage(
        "outlook_calendar", "inventory", "natural_idle", pending="Task8"
    ),
    "outlook_calendar_window": Coverage(
        "outlook_calendar", "fixed_window", "natural_idle_resume", pending="Task8"
    ),
    "outlook_calendar_full": Coverage(
        "outlook_calendar", "event_profile", "target_completion", pending="Task8"
    ),
}
