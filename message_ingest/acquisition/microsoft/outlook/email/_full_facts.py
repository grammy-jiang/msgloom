"""
Bounded immutable fact selection for Outlook Full profile verifiers.

These read helpers do not publish or stage facts. The caller may supply its
writer session so profile proof and publication share one transaction. The
ledger must still revalidate every selected fact at publication time.
"""

from __future__ import annotations

import hashlib
import json
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from message_ingest.acquisition.handoff import (
    AcquisitionStream,
    EffectiveStateKey,
    FactSpec,
    StorageRelation,
)
from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.catalog.models.handoff import AcquisitionFact
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore, Writer


class IncompleteProof(ValueError):
    """Signal a bounded, fail-closed profile proof failure."""


@dataclass(frozen=True, slots=True)
class FullTargetCompletion:
    """Bind one target to at most 128 exact facts, without provider bodies."""

    resource_kind: str
    resource_identity: str
    complete: bool
    terminal_with_limitations: bool = False
    required_facts: tuple[FactSpec, ...] = ()
    limitation_codes: tuple[str, ...] = ()
    reason_code: str = "incomplete"


class FullFactReader:
    """Read exact effective facts within a caller-owned transaction."""

    def __init__(
        self,
        catalog,
        writer: Writer,
        source_id: str,
        stream: AcquisitionStream,
        run_id: str,
        current: bool,
    ) -> None:
        self.ledger = AcquisitionHandoffStore(catalog)
        self.writer = writer
        self.source_id = source_id
        self.stream = stream
        self.run_id = run_id
        self.current = current
        self.facts: dict[str, FactSpec] = {}
        self.limitations: set[str] = set()
        self.evidence_bytes = 0

    def bind(
        self,
        kind: str,
        identity: str,
        *,
        component: str | None = None,
        parent: str | None = None,
        evidence_id: str | None = None,
        run_id: str | None = None,
        effective_only: bool = False,
    ) -> FactSpec:
        """Require the exact current application, including equivalent pins."""
        parent_kind = (
            "message"
            if self.stream == AcquisitionStream.OUTLOOK_MAIL
            else "calendar_event"
        )
        key = EffectiveStateKey(
            self.source_id,
            self.stream,
            kind,
            identity,
            parent_kind if parent else None,
            parent,
            component_kind=component,
        )
        current = self.ledger.current_effective_state(self.writer, key)
        if current is None:
            raise IncompleteProof("missing_effective_fact")
        table = AcquisitionFact.__table__
        query = select(table.c.fact_id, table.c.payload).where(
            table.c.effective_key == key.digest,
            table.c.source_state_key == current["source_state_key"],
            or_(
                table.c.fact_id == current["fact_id"],
                (table.c.storage_relation == StorageRelation.CURRENT_EQUIVALENT)
                & (
                    func.json_extract(table.c.payload, "$.revalidated_fact_id")
                    == current["fact_id"]
                ),
            ),
        )
        if effective_only:
            query = query.where(table.c.fact_id == current["fact_id"])
        elif run_id is not None or self.current:
            query = query.where(table.c.run_id == (run_id or self.run_id))
        if evidence_id is not None:
            query = query.where(
                func.json_extract(table.c.payload, "$.evidence_id") == evidence_id
            )
        row = self.writer.execute(query.order_by(table.c.fact_id).limit(1)).first()
        if row is None:
            raise IncompleteProof("missing_current_fact")
        fact = FactSpec.from_json(row.payload)
        locator = fact.source_version_locator
        if (
            fact.fact_id != row.fact_id
            or fact.storage_relation
            not in {
                StorageRelation.ADVANCED,
                StorageRelation.CURRENT_EQUIVALENT,
            }
            or locator is None
            or locator.resource_identity != identity
            or locator.component_kind != component
            or locator.evidence_id != fact.evidence_id
        ):
            raise IncompleteProof("invalid_fact_locator")
        evidence = RawHttpEvidence.__table__
        if (
            self.writer.execute(
                select(evidence.c.evidence_id).where(
                    evidence.c.evidence_id == fact.evidence_id,
                    evidence.c.source_id == self.source_id,
                )
            ).first()
            is None
        ):
            raise IncompleteProof("missing_source_evidence")
        self.facts[fact.fact_id] = fact
        if len(self.facts) > 128:
            raise IncompleteProof("fact_limit")
        return fact

    def finish(self, kind: str, identity: str) -> FullTargetCompletion:
        """Return only proven facts and closed profile limitation codes."""
        limitations = tuple(sorted(self.limitations))
        return FullTargetCompletion(
            kind,
            identity,
            True,
            bool(limitations),
            tuple(self.facts.values()),
            limitations,
            "terminal_complete_with_limitations"
            if limitations
            else "terminal_complete",
        )


def evidence_object(reader: FullFactReader, fact: FactSpec | str) -> dict:
    """Read verified JSON under an 8 MiB per-evidence profile-proof bound."""
    table = RawHttpEvidence.__table__
    row = (
        reader.writer.execute(
            select(table).where(
                table.c.source_id == reader.source_id,
                table.c.evidence_id
                == (fact if isinstance(fact, str) else fact.evidence_id),
            )
        )
        .mappings()
        .first()
    )
    if row is None or not 0 <= row["response_body_bytes"] <= 8 * 1024 * 1024:
        raise IncompleteProof("evidence_limit")
    reader.evidence_bytes += row["response_body_bytes"]
    if reader.evidence_bytes > 32 * 1024 * 1024:
        raise IncompleteProof("evidence_limit")
    try:
        with Path(row["response_body_path"]).open("rb") as stream:
            raw = stream.read(8 * 1024 * 1024 + 1)
    except OSError as error:
        raise IncompleteProof("missing_evidence_bytes") from error
    if (
        len(raw) != row["response_body_bytes"]
        or hashlib.sha256(raw).hexdigest() != row["response_body_sha256"]
    ):
        raise IncompleteProof("evidence_digest_mismatch")
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as error:
        raise IncompleteProof("invalid_evidence_json") from error
    if not isinstance(value, dict):
        raise IncompleteProof("invalid_evidence_json")
    return value


def _page_ids(payload: dict) -> frozenset[str]:
    """Read bounded provider identities from one saved inventory page."""
    values = payload.get("value")
    if not isinstance(values, list):
        raise IncompleteProof("incomplete_inventory")
    if len(values) > 128:
        raise IncompleteProof("fact_limit")
    identities: set[str] = set()
    for value in values:
        identity = value.get("id") if isinstance(value, dict) else None
        if not isinstance(identity, str) or not identity:
            raise IncompleteProof("invalid_inventory_member")
        identities.add(identity)
    return frozenset(identities)


def inventory_ids(reader: FullFactReader, fact: FactSpec) -> frozenset[str]:
    """
    Bind saved pagination edges, never infer pages from capture ordering.

    The initial Graph attachment request uses select/top/expand parameters.
    Continuations must connect that root to the exact terminal capture. Reads
    are confined to this source, endpoint and logical/canonical capture runs.
    Ambiguous or absent cache provenance fails closed instead of guessing.
    """
    selected = mail_application(reader, fact)
    if selected is not None:
        return selected[1]
    payload = evidence_object(reader, fact)
    if payload.get("@odata.nextLink"):
        raise IncompleteProof("incomplete_inventory")
    table = RawHttpEvidence.__table__
    terminal = (
        reader.writer.execute(
            select(table).where(
                table.c.evidence_id == fact.evidence_id,
                table.c.source_id == reader.source_id,
            )
        )
        .mappings()
        .one()
    )
    target_url = terminal["request_url"]
    initial_keys = {"$select", "$top", "$expand"}
    if (
        set(parse_qs(urlsplit(target_url).query, keep_blank_values=True))
        <= initial_keys
    ):
        return _page_ids(payload)
    endpoint = target_url.split("?", 1)[0]
    rows = (
        reader.writer.execute(
            select(table)
            .where(
                table.c.source_id == reader.source_id,
                table.c.run_id.in_({fact.run_id, terminal["run_id"]}),
                table.c.purpose == terminal["purpose"],
                table.c.request_url.startswith(endpoint, autoescape=True),
            )
            .limit(129)
        )
        .mappings()
        .all()
    )
    if len(rows) > 128:
        raise IncompleteProof("inventory_page_limit")
    pages = {}
    roots = []
    for row in rows:
        url = row["request_url"]
        if urlsplit(url).path != urlsplit(target_url).path:
            continue
        old = pages.get(url)
        if old is not None and (
            old["response_body_sha256"] != row["response_body_sha256"]
        ):
            raise IncompleteProof("ambiguous_inventory")
        pages[url] = row
        if set(parse_qs(urlsplit(url).query, keep_blank_values=True)) <= initial_keys:
            roots.append(url)
    successes = []
    for root in dict.fromkeys(roots):
        current = root
        visited = set()
        identities = set()
        while current not in visited and current in pages:
            visited.add(current)
            page = (
                payload
                if current == target_url
                else evidence_object(
                    reader,
                    pages[current]["evidence_id"],
                )
            )
            identities.update(_page_ids(page))
            if len(identities) > 128:
                raise IncompleteProof("fact_limit")
            if current == target_url:
                successes.append(frozenset(identities))
                break
            current = page.get("@odata.nextLink")
            if not isinstance(current, str):
                break
    if len(successes) != 1:
        raise IncompleteProof("unproven_inventory_chain")
    return successes[0]


def mail_application(reader: FullFactReader, fact: FactSpec):
    """
    Recheck a selected Mail application without publishing or committing.

    Reuse Mail's inventory validation in the caller transaction. A Connection
    receives a read-only ORM view whose close cannot commit or roll it back.
    Legacy direct facts have no application and retain their original checks.
    """
    if reader.stream != AcquisitionStream.OUTLOOK_MAIL:
        return None
    from message_ingest.catalog.models.microsoft.outlook._email_bindings import (
        MailApplicationBinding as Binding,
    )
    from message_ingest.catalog.models.microsoft.outlook._email_bindings import (
        MailComponentCapture as Capture,
    )
    from message_ingest.catalog.stores.microsoft.outlook._email_handoff import (
        decode_surface_reason,
        semantic_digest,
        verified_digest,
    )
    from message_ingest.catalog.stores.microsoft.outlook._email_inventory import (
        chain,
        inventory_manifest,
    )

    context = (
        nullcontext(reader.writer)
        if isinstance(reader.writer, Session)
        else Session(bind=reader.writer, join_transaction_mode="rollback_only")
    )
    with context as session:
        bindings = session.scalars(
            select(Binding)
            .where(
                Binding.source_id == reader.source_id,
                Binding.fact_id == fact.fact_id,
                Binding.capture_id.is_not(None),
            )
            .limit(129)
        ).all()
        if not bindings:
            return None
        if len(bindings) > 128:
            raise IncompleteProof("fact_limit")
        primary = next(
            (f for f in reader.facts.values() if f.resource_kind == "message"),
            None,
        )
        for binding in bindings:
            if primary is None or binding.primary_fact_id != primary.fact_id:
                continue
            capture = session.get(Capture, binding.capture_id)
            if capture is None:
                continue
            data = json.loads(capture.payload)
            locator = fact.source_version_locator
            if (
                locator is None
                or data["evidence_id"] != fact.evidence_id
                or capture.parent_key != locator.resource_version
                or capture.component != fact.component_kind
                or capture.resource_id != fact.resource_identity
            ):
                continue
            try:
                status, profile = decode_surface_reason(fact.transition_reason)
                if (status, profile) != (data["status"], data["profile_version"]):
                    continue
                state = {
                    "component": capture.component,
                    "resource_version": capture.parent_key,
                    "status": status,
                    "profile_version": profile,
                }
                members = frozenset()
                if capture.component == "attachments":
                    manifest = inventory_manifest(
                        session,
                        capture,
                        data,
                        primary.fact_id,
                    )
                    retained = json.loads(binding.payload)["capture_manifest"]
                    if manifest is None or manifest != retained:
                        continue
                    if manifest["page_count"] > 128 or manifest["member_count"] > 128:
                        raise IncompleteProof("fact_limit")
                    pages = chain(session, capture, data)
                    if pages is None:
                        continue
                    for _, page_data, _ in pages:
                        evidence_object(reader, page_data["evidence_id"])
                    members = frozenset(
                        member.member_id
                        for _, _, entries in pages
                        for member in entries
                    )
                    state["membership_sha256"] = manifest["semantic_sha256"]
                elif capture.component == "attachment_metadata":
                    state["metadata"] = data["metadata"]
                elif status == "acquired":
                    state["content_sha256"] = verified_digest(
                        session,
                        reader.source_id,
                        fact.evidence_id,
                    )
                if semantic_digest(state) == fact.source_state_key:
                    return state, members
            except (ValueError, OSError) as error:
                raise IncompleteProof("invalid_mail_application") from error
        raise IncompleteProof("missing_mail_application")
