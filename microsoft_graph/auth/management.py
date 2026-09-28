"""Safe local inspection and classification of Microsoft authentication state."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from scrapy.settings import BaseSettings

MICROSOFT_GRAPH_CLI_CLIENT_ID = "14d82eec-204b-4c2f-b7e8-296a70dab67e"
MICROSOFT_GRAPH_CLI_APP_NAME = "Microsoft Graph Command Line Tools"
_OIDC_SCOPES = frozenset({"openid", "profile", "offline_access", "email"})


@dataclass(frozen=True, slots=True)
class MicrosoftAuthStatus:
    """Privacy-safe local authentication diagnostics for operator commands."""

    status: str
    application_mode: str
    application_name: str
    client_id: str
    auth_method: str
    authority: str
    token_cache: str
    cache_exists: bool
    cache_valid: bool | None
    cache_mode: str | None
    cached_account_count: int
    cached_application_count: int
    cached_applications: tuple[str, ...]
    cache_matches_configured_application: bool
    cached_scopes: tuple[str, ...]
    warnings: tuple[str, ...]
    remediation: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        """Return JSON-serializable diagnostics without token or account data."""
        return asdict(self)


def classify_client_id(client_id: str) -> tuple[str, str]:
    """Classify a public client without treating its identifier as a secret."""
    normalized = client_id.strip().lower()
    if not normalized:
        return "unconfigured", "Not configured"
    if normalized == MICROSOFT_GRAPH_CLI_CLIENT_ID:
        return "development", MICROSOFT_GRAPH_CLI_APP_NAME
    return "custom", "Custom Microsoft application"


def inspect_auth_status(settings: BaseSettings) -> MicrosoftAuthStatus:
    """Inspect configured application and local MSAL cache without network I/O."""
    client_id = str(settings.get("MS_GRAPH_CLIENT_ID") or "").strip()
    auth_method = str(
        settings.get("MS_GRAPH_AUTH_METHOD", "device_code") or "device_code"
    )
    authority = str(settings.get("MS_GRAPH_AUTHORITY") or "")
    cache_raw = str(settings.get("MS_GRAPH_TOKEN_CACHE") or "").strip()
    cache_path = Path(cache_raw) if cache_raw else None
    mode, app_name = classify_client_id(client_id)

    warnings: list[str] = []
    remediation: list[str] = []
    cached_scopes: set[str] = set()
    scopes_by_client: dict[str, set[str]] = {}
    cached_client_ids: set[str] = set()
    credential_client_ids: set[str] = set()
    cached_account_count = 0
    cache_matches = False
    cache_valid: bool | None = None
    cache_mode: str | None = None

    if mode == "unconfigured":
        remediation.extend(
            (
                (
                    "Development: set MSGLOOM_MS_CLIENT_ID to the documented "
                    "Microsoft Graph Command Line Tools development client ID."
                ),
                (
                    "Production: use the msgloom-managed Microsoft application "
                    "when available, or configure your own Entra public-client "
                    "application ID."
                ),
                (
                    "Run 'scrapy microsoft auth status' after changing the "
                    "configuration."
                ),
            )
        )
    elif mode == "development":
        warnings.append(
            "Development authentication is active. Microsoft consent screens "
            "will name Microsoft Graph Command Line Tools, not msgloom."
        )
        remediation.append(
            "Use this application identity for development/testing only; "
            "configure a managed or custom application for real users."
        )

    if cache_path is not None and cache_path.exists():
        try:
            cache_mode = oct(cache_path.stat().st_mode & 0o777)
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise TypeError("cache root is not an object")
            cache_valid = True
            cached_account_count = _mapping_count(payload.get("Account"))
            for section in ("AccessToken", "RefreshToken", "AppMetadata"):
                entries = payload.get(section)
                if not isinstance(entries, dict):
                    continue
                for row in entries.values():
                    if not isinstance(row, dict):
                        continue
                    row_client_id = row.get("client_id")
                    if isinstance(row_client_id, str) and row_client_id:
                        normalized_row_client_id = row_client_id.lower()
                        cached_client_ids.add(normalized_row_client_id)
                        if section in {"AccessToken", "RefreshToken"}:
                            credential_client_ids.add(normalized_row_client_id)
                            row_scopes = scopes_by_client.setdefault(
                                normalized_row_client_id, set()
                            )
                            _collect_scopes(row.get("target"), row_scopes)
                    if (
                        section in {"AccessToken", "RefreshToken"}
                        and client_id
                        and isinstance(row_client_id, str)
                        and row_client_id.lower() == client_id.lower()
                    ):
                        cache_matches = True
            if os.name == "posix" and cache_mode != "0o600":
                warnings.append(
                    "The local Microsoft token cache permissions are not "
                    "0600; restrict the file before using live credentials."
                )
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
            cache_valid = False
            warnings.append(
                "The Microsoft token cache exists but could not be read as a "
                "valid MSAL cache."
            )
            remediation.append(
                "If the cache is corrupted, use 'scrapy "
                "microsoft auth clear --yes' to remove only the local cached "
                "credentials, then sign in again."
            )

    normalized_client_id = client_id.lower()
    if cache_matches:
        cached_scopes.update(scopes_by_client.get(normalized_client_id, set()))
    elif not client_id and len(cached_client_ids) == 1:
        only_client = next(iter(cached_client_ids))
        cached_scopes.update(scopes_by_client.get(only_client, set()))

    if client_id and credential_client_ids and not cache_matches:
        warnings.append(
            "The token cache contains credentials for a different Microsoft "
            "application. The configured application will require its own "
            "sign-in/consent."
        )
    elif not client_id and credential_client_ids:
        warnings.append(
            "The token cache contains Microsoft credentials, but no Client ID "
            "is currently configured. Cached credentials are not selected "
            "automatically."
        )

    cached_applications = tuple(
        sorted(_cached_application_label(value) for value in cached_client_ids)
    )

    if mode == "unconfigured":
        status = "unconfigured"
    elif cache_path is None or not cache_path.exists():
        status = "configured_no_cache"
    elif cache_valid is False:
        status = "configured_cache_invalid"
    elif cache_matches:
        status = "configured_cached"
    elif credential_client_ids:
        status = "configured_cache_mismatch"
    else:
        status = "configured_no_credentials"

    return MicrosoftAuthStatus(
        status=status,
        application_mode=mode,
        application_name=app_name,
        client_id=_display_client_id(client_id),
        auth_method=auth_method,
        authority=authority,
        token_cache=str(cache_path) if cache_path is not None else "not configured",
        cache_exists=bool(cache_path is not None and cache_path.exists()),
        cache_valid=cache_valid,
        cache_mode=cache_mode,
        cached_account_count=cached_account_count,
        cached_application_count=len(cached_client_ids),
        cached_applications=cached_applications,
        cache_matches_configured_application=cache_matches,
        cached_scopes=tuple(sorted(cached_scopes)),
        warnings=tuple(warnings),
        remediation=tuple(remediation),
    )


def clear_local_token_cache(settings: BaseSettings) -> bool:
    """Delete only the configured local MSAL cache; never revoke remote consent."""
    raw = str(settings.get("MS_GRAPH_TOKEN_CACHE") or "").strip()
    if not raw:
        return False
    path = Path(raw)
    if not path.exists():
        return False
    if not path.is_file():
        raise RuntimeError("Configured Microsoft token cache is not a file")
    path.unlink()
    return True


def _mapping_count(value: Any) -> int:
    """Return mapping size without trusting malformed cache structure."""
    return len(value) if isinstance(value, dict) else 0


def _collect_scopes(raw: Any, target: set[str]) -> None:
    """Collect resource scopes while excluding ordinary OpenID Connect scopes."""
    if not isinstance(raw, str):
        return
    target.update(
        scope for scope in raw.split() if scope and scope.lower() not in _OIDC_SCOPES
    )


def _display_client_id(client_id: str) -> str:
    """Keep diagnostics recognizable without needlessly printing a full ID."""
    if not client_id:
        return ""
    if len(client_id) <= 13:
        return client_id
    return f"{client_id[:8]}...{client_id[-4:]}"


def _cached_application_label(client_id: str) -> str:
    """Describe a cached application without exposing account information."""
    mode, name = classify_client_id(client_id)
    if mode == "development":
        return f"{name} (development)"
    return f"{_display_client_id(client_id)} ({mode})"
