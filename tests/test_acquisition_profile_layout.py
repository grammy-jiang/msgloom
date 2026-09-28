"""Lock Outlook Mail acquisition profiles into the product policy domain."""

from __future__ import annotations

from pathlib import Path

import pytest

from message_ingest.acquisition.microsoft import outlook
from message_ingest.acquisition.microsoft.outlook import email
from message_ingest.acquisition.microsoft.outlook.email import profile


def test_acquisition_profile_packages_expose_only_domain_surfaces() -> None:
    if outlook.__all__ != ["calendar", "email"]:
        pytest.fail(f"Unexpected Outlook acquisition exports: {outlook.__all__!r}")
    if "FULL_V1" not in email.__all__:
        pytest.fail("Expected Outlook Mail acquisition profile to expose FULL_V1")
    if "surface_is_complete" not in email.__all__:
        pytest.fail("Expected Outlook Mail acquisition policy helpers to be public")


def test_full_v1_profile_lives_in_outlook_mail_policy_module() -> None:
    if profile.FULL_V1 != "outlook-mail-full-v1":
        pytest.fail(f"Unexpected Full-v1 profile identifier: {profile.FULL_V1!r}")
    if profile.surface_is_complete.__module__ != (
        "message_ingest.acquisition.microsoft.outlook.email.profile"
    ):
        pytest.fail("Outlook Mail acquisition policy moved outside its domain")


def test_legacy_root_profiles_module_is_gone() -> None:
    legacy = Path(__file__).parents[1] / "message_ingest" / "profiles.py"
    if legacy.exists():
        pytest.fail(f"Legacy root profiles module must not return: {legacy}")
