"""Prove rule-selected Full-v1 completion from current-run catalog evidence."""

from __future__ import annotations

from dataclasses import dataclass

from message_ingest.acquisition.microsoft.outlook.email.profile import (
    attachment_required_surfaces,
    attachment_type_name,
    surface_is_complete,
)
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore

_BASE_PURPOSE = {
    "detail": "message-detail",
    "mime": "message-mime",
    "attachments": "attachments-list",
}
_REQUEST_LIMITATION_STATUSES = frozenset({"unauthorized", "unavailable", "unsupported"})


@dataclass(frozen=True, slots=True)
class MailFullCompletionResult:
    """Bounded workflow gate result without target identifiers."""

    complete: bool
    with_limitations: bool
    reason_code: str
    waivable_failure_reasons: frozenset[str]


def verify_current_full_v1(
    catalog,
    *,
    source_id: str,
    run_id: str,
    message_ids: tuple[str, ...],
) -> MailFullCompletionResult:
    """Require terminal Full-v1 surfaces proven by evidence from *run_id*."""

    if not message_ids:
        return MailFullCompletionResult(
            complete=True,
            with_limitations=False,
            reason_code="terminal_complete",
            waivable_failure_reasons=frozenset(),
        )

    store = OutlookMailStore(catalog, source_id=source_id)
    waivable: set[str] = set()
    with_limitations = False

    for message_id in dict.fromkeys(message_ids):
        surfaces = store.get_surfaces(message_id=message_id)
        base = _verify_surfaces(
            catalog,
            surfaces=surfaces,
            surface_names=tuple(_BASE_PURPOSE),
            run_id=run_id,
            purpose_by_surface=_BASE_PURPOSE,
        )
        if base is None:
            return _incomplete()
        base_limitations, base_waivable = base
        with_limitations = with_limitations or base_limitations
        waivable.update(base_waivable)

        attachments_state = surfaces["attachments"]
        if attachments_state["status"] != "acquired":
            continue

        attachments = store.get_attachments(message_id=message_id)
        metadata_ids = tuple(
            value
            for attachment in attachments
            if isinstance((value := attachment.get("latest_evidence_id")), str)
        )
        metadata_runs = catalog.evidence.run_ids_for(metadata_ids)

        current_attachments = [
            attachment
            for attachment in attachments
            if isinstance((evidence_id := attachment.get("latest_evidence_id")), str)
            and metadata_runs.get(evidence_id) == run_id
        ]
        for attachment in current_attachments:
            attachment_id = attachment.get("attachment_id")
            attachment_type = attachment.get("attachment_type")
            if not isinstance(attachment_id, str) or not attachment_id:
                return _incomplete()
            required = attachment_required_surfaces(attachment_type, attachment_id)
            child = _verify_surfaces(
                catalog,
                surfaces=surfaces,
                surface_names=required,
                run_id=run_id,
                purpose_by_surface={
                    surface: _child_purpose(surface) for surface in required
                },
                attachment_type=(
                    attachment_type if isinstance(attachment_type, str) else None
                ),
            )
            if child is None:
                return _incomplete()
            child_limitations, child_waivable = child
            with_limitations = with_limitations or child_limitations
            waivable.update(child_waivable)

    return MailFullCompletionResult(
        complete=True,
        with_limitations=with_limitations,
        reason_code=(
            "terminal_complete_with_limitations"
            if with_limitations
            else "terminal_complete"
        ),
        waivable_failure_reasons=frozenset(waivable),
    )


def _verify_surfaces(
    catalog,
    *,
    surfaces: dict[str, dict[str, object]],
    surface_names: tuple[str, ...],
    run_id: str,
    purpose_by_surface: dict[str, str],
    attachment_type: str | None = None,
) -> tuple[bool, set[str]] | None:
    evidence_ids: list[str] = []
    for surface in surface_names:
        if not surface_is_complete(surfaces, surface):
            return None
        evidence_id = surfaces[surface].get("evidence_id")
        if not isinstance(evidence_id, str) or not evidence_id:
            return None
        evidence_ids.append(evidence_id)

    evidence_runs = catalog.evidence.run_ids_for(evidence_ids)
    if any(evidence_runs.get(evidence_id) != run_id for evidence_id in evidence_ids):
        return None

    with_limitations = False
    waivable: set[str] = set()
    for surface in surface_names:
        status = surfaces[surface]["status"]
        if status == "acquired":
            continue
        with_limitations = True
        if status not in _REQUEST_LIMITATION_STATUSES:
            continue
        # Reference/unknown attachment types can be marked unsupported directly
        # from the attachment inventory without an attachment-raw request failure.
        if surface.startswith("attachment_raw:") and attachment_type_name(
            attachment_type
        ) not in {"fileAttachment", "itemAttachment"}:
            continue
        waivable.add(f"request_failure:{purpose_by_surface[surface]}")
    return with_limitations, waivable


def _child_purpose(surface: str) -> str:
    if surface.startswith("attachment_raw:"):
        return "attachment-raw"
    if surface.startswith("item_attachment_detail:"):
        return "item-attachment-detail"
    raise ValueError("unknown Full-v1 child surface")


def _incomplete() -> MailFullCompletionResult:
    return MailFullCompletionResult(
        complete=False,
        with_limitations=False,
        reason_code="incomplete",
        waivable_failure_reasons=frozenset(),
    )


__all__ = ["MailFullCompletionResult", "verify_current_full_v1"]
