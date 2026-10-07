"""Prove rule-selected Full-v1 completion from current-run catalog evidence."""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass

from sqlalchemy import select

from message_ingest.acquisition.handoff import AcquisitionStream
from message_ingest.acquisition.microsoft.outlook.email.profile import (
    attachment_required_surfaces,
    attachment_type_name,
    surface_is_complete,
)
from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.catalog.models.microsoft.outlook.email import (
    AttachmentRecord,
    MessageSurface,
)
from message_ingest.catalog.stores.handoff import Writer
from message_ingest.catalog.stores.microsoft.outlook._email_handoff import (
    decode_surface_reason,
    semantic_digest,
)
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore

from ._full_facts import (
    FullFactReader,
    FullTargetCompletion,
    IncompleteProof,
    inventory_ids,
    mail_application,
)

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
        # from the attachment inventory without an attachment-raw request
        # failure.
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


__all__ = [
    "FullTargetCompletion",
    "MailFullCompletionResult",
    "verify_current_full_v1",
    "verify_full_v1_target",
]


def verify_full_v1_target(
    catalog,
    *,
    source_id: str,
    run_id: str,
    message_id: str,
    require_current_attempt: bool = True,
    writer: Writer | None = None,
) -> FullTargetCompletion:
    """
    Bind one Mail target independently of the all-selected authority gate.

    The workflow gate remains stricter about evidence capture runs. This
    additional release proof uses logical fact provenance, so canonical cache
    evidence can be older. Explicit no-work revalidation reads existing facts
    without claiming that acquisition ran again. Supply the publication writer
    to keep proof and publication in the same caller-owned transaction.
    """
    with nullcontext(writer) if writer is not None else catalog.Session() as session:
        reader = FullFactReader(
            catalog,
            session,
            source_id,
            AcquisitionStream.OUTLOOK_MAIL,
            run_id,
            require_current_attempt,
        )
        try:
            try:
                primary = reader.bind("message", message_id, effective_only=True)
            except IncompleteProof as error:
                if str(error) != "missing_effective_fact":
                    raise
                primary = None
            surfaces = {}
            for name in _BASE_PURPOSE:
                surfaces[name] = _target_surface(reader, message_id, name)
            detail = surfaces["detail"][1]
            if surfaces["detail"][0] == "acquired" and (
                primary is None
                or detail.source_version_locator is None
                or detail.source_version_locator.resource_version
                != primary.source_state_key
            ):
                raise IncompleteProof("primary_version_mismatch")
            for _, fact in surfaces.values():
                locator = fact.source_version_locator
                if (
                    locator is not None
                    and locator.resource_version is not None
                    and (
                        primary is None
                        or locator.resource_version != primary.source_state_key
                    )
                ):
                    raise IncompleteProof("component_version_mismatch")
            if surfaces["attachments"][0] == "acquired":
                _target_attachments(
                    reader,
                    message_id,
                    surfaces["attachments"][1],
                )
        except IncompleteProof as error:
            return FullTargetCompletion(
                "message",
                message_id,
                False,
                reason_code=str(error),
            )
        return reader.finish("message", message_id)


def _target_surface(reader, message_id, name):
    """Match mutable planning state against a durable semantic fact."""
    table = MessageSurface.__table__
    row = (
        reader.writer.execute(
            select(table).where(
                table.c.source_id == reader.source_id,
                table.c.message_id == message_id,
                table.c.surface == name,
            )
        )
        .mappings()
        .first()
    )
    if row is None or not surface_is_complete({name: dict(row)}, name):
        raise IncompleteProof("incomplete_surface")
    fact = reader.bind(
        "message_surface",
        message_id,
        component=name,
        parent=message_id,
        evidence_id=row["evidence_id"],
    )
    locator = fact.source_version_locator
    if locator is None:
        raise IncompleteProof("missing_surface_locator")
    state = {
        "surface": name,
        "status": row["status"],
        "profile": row["profile_version"],
        # Qualified Mail facts bind acquired bytes to their exact parent.
        "resource_version": locator.resource_version,
    }
    if row["status"] == "acquired":
        evidence = RawHttpEvidence.__table__
        digest = reader.writer.execute(
            select(evidence.c.response_body_sha256).where(
                evidence.c.evidence_id == row["evidence_id"],
                evidence.c.source_id == reader.source_id,
            )
        ).scalar_one_or_none()
        state["content_sha256"] = digest
    selected = mail_application(reader, fact)
    if selected is not None:
        if (selected[0]["status"], selected[0]["profile_version"]) != (
            row["status"],
            row["profile_version"],
        ):
            raise IncompleteProof("surface_fact_mismatch")
    elif semantic_digest(state) != fact.source_state_key:
        raise IncompleteProof("surface_fact_mismatch")
    if row["status"] != "acquired":
        reader.limitations.add(row["status"])
    return row["status"], fact


def _target_attachments(reader, message_id, inventory):
    """Use only inventory-owned metadata, preserving old-row exclusion."""
    table = AttachmentRecord.__table__
    required_ids = inventory_ids(reader, inventory)
    rows = (
        reader.writer.execute(
            select(table)
            .where(
                table.c.source_id == reader.source_id,
                table.c.message_id == message_id,
                table.c.attachment_id.in_(required_ids),
            )
            .order_by(table.c.attachment_id)
            .limit(129)
        )
        .mappings()
        .all()
    )
    if len(rows) > 128:
        raise IncompleteProof("fact_limit")
    matched_ids = set()
    for row in rows:
        try:
            fact = reader.bind(
                "attachment",
                row["attachment_id"],
                component="attachment_metadata",
                parent=message_id,
                evidence_id=row["latest_evidence_id"],
                run_id=inventory.run_id,
            )
        except IncompleteProof as error:
            if str(error) == "missing_current_fact":
                continue
            raise
        try:
            status, profile = decode_surface_reason(fact.transition_reason)
        except ValueError as error:
            raise IncompleteProof("attachment_fact_mismatch") from error
        locator = fact.source_version_locator
        state = {
            "id": row["attachment_id"],
            "resource_version": locator.resource_version if locator else None,
            "status": status,
            "profile_version": profile,
            **{
                name: row[name]
                for name in (
                    "attachment_type",
                    "name",
                    "content_type",
                    "size",
                    "is_inline",
                )
            },
        }
        selected = mail_application(reader, fact)
        if selected is not None:
            if any(row[key] != value for key, value in selected[0]["metadata"].items()):
                raise IncompleteProof("attachment_fact_mismatch")
        elif semantic_digest(state) != fact.source_state_key:
            raise IncompleteProof("attachment_fact_mismatch")
        matched_ids.add(row["attachment_id"])
        for name in attachment_required_surfaces(
            row["attachment_type"],
            row["attachment_id"],
        ):
            _, child = _target_surface(reader, message_id, name)
            locator = child.source_version_locator
            parent_locator = inventory.source_version_locator
            if (
                locator is not None
                and parent_locator is not None
                and locator.resource_version is not None
                and parent_locator.resource_version is not None
                and locator.resource_version != parent_locator.resource_version
            ):
                raise IncompleteProof("attachment_version_mismatch")
    if not required_ids <= matched_ids:
        raise IncompleteProof("missing_attachment_metadata")
