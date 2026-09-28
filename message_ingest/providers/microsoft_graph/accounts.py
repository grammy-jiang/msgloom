"""Select stable MSAL account identities without parsing provider keys."""

from __future__ import annotations

from typing import Any

import msal

from message_ingest.acquisition.source_identity import (
    SourceBindingSnapshot,
    SourceIdentity,
    SourceIdentityService,
)
from message_ingest.providers.microsoft_graph import PROVIDER_ID

ACCOUNT_KEY_SCHEME = "msal_home_account_id/sha256-v1"


class MicrosoftGraphAuthError(RuntimeError):
    """Authentication cannot safely produce a source-pinned Graph token."""


def account_key(account: dict[str, Any]) -> str:
    """Read MSAL 1.39 home_account_id as an opaque, unparsed key."""
    value = account.get("home_account_id")
    if not isinstance(value, str) or not value or not value.strip():
        raise MicrosoftGraphAuthError(
            "MSAL account does not expose a stable home_account_id"
        )
    return value


def identity_for_account(account: dict[str, Any]) -> SourceIdentity:
    """Convert MSAL account metadata into provider identity input."""
    return SourceIdentity(
        provider=PROVIDER_ID,
        key_scheme=ACCOUNT_KEY_SCHEME,
        account_key=account_key(account),
    )


def all_accounts(app: msal.PublicClientApplication) -> list[dict[str, Any]]:
    """Return current account records without logging user identifiers."""
    return list(app.get_accounts())


def account_key_set(accounts: list[dict[str, Any]]) -> set[str]:
    """Return exact opaque keys for all account records."""
    return {account_key(account) for account in accounts}


def find_account_by_key(
    accounts: list[dict[str, Any]], key: str
) -> dict[str, Any] | None:
    """Find exactly one cached account by opaque home-account key."""
    matches = [account for account in accounts if account_key(account) == key]
    if len(matches) > 1:
        raise MicrosoftGraphAuthError(
            "MSAL returned duplicate records for one home account"
        )
    return matches[0] if matches else None


def find_bound_account(
    accounts: list[dict[str, Any]],
    service: SourceIdentityService,
    binding: SourceBindingSnapshot,
) -> dict[str, Any] | None:
    """Find exactly one cached account matching a persisted source binding."""
    matches = [
        account
        for account in accounts
        if service.matches_binding(identity_for_account(account), binding)
    ]
    if len(matches) > 1:
        raise MicrosoftGraphAuthError(
            "Multiple cached Microsoft accounts match one source binding"
        )
    return matches[0] if matches else None


def select_unbound_cached_account(
    app: msal.PublicClientApplication,
    accounts: list[dict[str, Any]],
    username: str,
) -> dict[str, Any] | None:
    """Select the first source account only when the choice is unambiguous."""
    if username:
        matches = list(app.get_accounts(username=username))
        if len(matches) > 1:
            raise MicrosoftGraphAuthError(
                "Configured Microsoft username matches multiple cached accounts"
            )
        if len(matches) == 1:
            account_key(matches[0])
            return matches[0]
        return None
    if len(accounts) > 1:
        raise MicrosoftGraphAuthError(
            "Multiple Microsoft accounts are cached; set MSGLOOM_MS_USERNAME "
            "for the first source binding"
        )
    if not accounts:
        return None
    account_key(accounts[0])
    return accounts[0]


def select_after_interaction(
    app: msal.PublicClientApplication,
    before_keys: set[str],
    username: str,
) -> dict[str, Any]:
    """Resolve an interactive account without using the returned token."""
    if username:
        matches = list(app.get_accounts(username=username))
        if len(matches) != 1:
            raise MicrosoftGraphAuthError(
                "Interactive sign-in did not yield exactly one configured account"
            )
        account_key(matches[0])
        return matches[0]

    after = all_accounts(app)
    new_accounts = [
        account for account in after if account_key(account) not in before_keys
    ]
    if len(new_accounts) == 1:
        return new_accounts[0]
    if not new_accounts and len(after) == 1:
        account_key(after[0])
        return after[0]
    raise MicrosoftGraphAuthError(
        "Interactive sign-in did not identify one unambiguous Microsoft account"
    )
