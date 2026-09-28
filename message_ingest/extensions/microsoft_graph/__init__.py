"""Msgloom lifecycle extensions for Microsoft Graph acquisition."""

from .identity import MicrosoftGraphSourceIdentityExtension
from .integrity import MicrosoftGraphIntegrityExtension
from .privacy import MicrosoftGraphLogPrivacyExtension

__all__ = [
    "MicrosoftGraphIntegrityExtension",
    "MicrosoftGraphLogPrivacyExtension",
    "MicrosoftGraphSourceIdentityExtension",
]
