"""Saved provider evidence for per-target Full completion checks."""

from __future__ import annotations

import json
from typing import Literal, overload

from outlook_mail_handoff_fixtures import saved_mail_evidence

from message_ingest.catalog.stores.microsoft.outlook.calendar import (
    OutlookCalendarStore,
)
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
from message_ingest.items.microsoft.outlook.calendar import (
    OutlookCalendarEventItem,
)

NOW = "2026-10-03T00:00:00+00:00"
LATER = "2026-10-03T01:00:00+00:00"


@overload
def seed_target(
    catalog,
    family: Literal["mail"],
    target="one",
    run="run",
    version: str | None = "v1",
) -> OutlookMailStore: ...


@overload
def seed_target(
    catalog,
    family: Literal["calendar"],
    target="one",
    run="run",
    version: str | None = "v1",
) -> OutlookCalendarStore: ...


@overload
def seed_target(
    catalog,
    family: str,
    target="one",
    run="run",
    version: str | None = "v1",
) -> OutlookMailStore | OutlookCalendarStore: ...


def seed_target(catalog, family, target="one", run="run", version: str | None = "v1"):
    """Persist exact primary and base surfaces using real provider stores."""
    profile = f"outlook-{family}-full-v1"
    raw = {"id": target, "changeKey": version, "type": "singleInstance"}
    evidence = save(catalog, f"{family}-{target}-{run}-detail", raw, run=run)
    if family == "mail":
        store = OutlookMailStore(catalog, source_id="source")
        primary = store.record_message(
            run_id=run,
            message=raw,
            kind="detail",
            evidence_id=evidence,
            observed_at=NOW,
        ).fact
        binding = primary.source_state_key
    else:
        store = OutlookCalendarStore(catalog, source_id="source")
        store.persist_event(
            OutlookCalendarEventItem(
                event_id=target,
                raw=raw,
                run_id=run,
                evidence_id=evidence,
                observed_at=NOW,
                observation_kind="full",
            )
        )
        binding = version
    for name in (
        ("detail", "mime", "attachments")
        if family == "mail"
        else ("detail", "attachments")
    ):
        capture = (
            evidence
            if name == "detail"
            else save(
                catalog,
                f"{family}-{target}-{run}-{name}",
                {"value": []} if name == "attachments" else {"mime": "saved"},
                run=run,
            )
        )
        set_surface(
            store,
            family,
            target,
            name,
            capture,
            run=run,
            version=binding,
            profile=profile,
        )
    return store


def save(catalog, identity, body, *, run="run", at=NOW):
    """Save real bounded JSON bytes before provider semantics."""
    return saved_mail_evidence(
        catalog,
        evidence_id=identity,
        source_id="source",
        run_id=run,
        observed_at=at,
        body=json.dumps(body).encode(),
    )


def set_surface(
    store,
    family,
    target,
    name,
    evidence,
    *,
    run="run",
    version: str | None = "v1",
    profile=None,
    status="acquired",
    at=NOW,
):
    """Persist one surface without hiding its profile or parent binding."""
    kwargs = {
        "run_id": run,
        "surface": name,
        "status": status,
        "evidence_id": evidence,
        "observed_at": at,
        "profile_version": profile or f"outlook-{family}-full-v1",
        "resource_version": version,
    }
    if family == "mail":
        return store.set_surface(message_id=target, **kwargs)
    return store.set_event_surface(event_id=target, **kwargs)
