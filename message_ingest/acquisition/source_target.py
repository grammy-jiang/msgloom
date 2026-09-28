"""Bind one logical source ID to one stable provider resource target."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime

from scrapy.exceptions import NotConfigured
from sqlalchemy import insert, select, update

from message_ingest.catalog.models.acquisition import (
    RawHttpEvidence,
    SourceBinding,
    SourceTargetBinding,
)
from message_ingest.catalog.models.base import Base
from message_ingest.extensions.catalog import CatalogService

_SERVICE_ATTR = "_msgloom_source_target_service"
_HASH_DOMAIN = b"msgloom-source-target-v1\0"
SELF_MAILBOX_KEY = "signed-in-mailbox"


class SourceTargetError(RuntimeError):
    """Base error for source-to-provider-resource integrity failures."""


class SourceTargetMismatch(SourceTargetError):
    """The source is already bound to another provider resource target."""


@dataclass(frozen=True, slots=True)
class SourceTargetIdentity:
    provider: str
    resource_kind: str
    key_scheme: str
    target_key: str


@dataclass(frozen=True, slots=True)
class SourceTargetBindingSnapshot:
    provider: str
    resource_kind: str
    key_scheme: str
    target_key_sha256: str
    binding_method: str
    bound_at: str


class SourceTargetBindingService:
    """Bind one logical source to one opaque provider resource target."""

    def __init__(self, *, service: CatalogService, source_id: str, stats=None) -> None:
        if not source_id.strip() or source_id != source_id.strip():
            raise ValueError("MSGLOOM_SOURCE_ID must be non-empty without whitespace")
        self.service = service
        self.catalog = service.catalog
        self.source_id = source_id
        self.stats = stats

    @classmethod
    def from_crawler(cls, crawler):
        if not crawler.settings.getbool("MSGLOOM_CATALOG_ENABLED"):
            raise NotConfigured("Source target binding requires the SQL catalog")
        if (existing := getattr(crawler, _SERVICE_ATTR, None)) is not None:
            return existing
        service = cls(
            service=CatalogService.from_crawler(crawler),
            source_id=crawler.settings["MSGLOOM_SOURCE_ID"],
            stats=crawler.stats,
        )
        setattr(crawler, _SERVICE_ATTR, service)
        return service

    def get_binding(self) -> SourceTargetBindingSnapshot | None:
        with self.catalog.Session() as session:
            binding = session.get(SourceTargetBinding, self.source_id)
            if binding is None:
                return None
            return self._snapshot(binding)

    def bind_or_verify(self, identity: SourceTargetIdentity) -> str:
        provider, resource_kind, key_scheme, digest = self._normalized(identity)
        with self.catalog.engine.begin() as connection:
            connection.execute(
                update(SourceTargetBinding)
                .where(SourceTargetBinding.source_id == self.source_id)
                .values(bound_at=SourceTargetBinding.bound_at)
            )
            existing = (
                connection.execute(
                    select(SourceTargetBinding.__table__).where(
                        SourceTargetBinding.source_id == self.source_id
                    )
                )
                .mappings()
                .first()
            )
            if existing is not None:
                if (
                    existing["provider"] != provider
                    or existing["resource_kind"] != resource_kind
                    or existing["key_scheme"] != key_scheme
                    or existing["target_key_sha256"] != digest
                ):
                    self._inc("msgloom/source_target/mismatch_count")
                    raise SourceTargetMismatch(
                        "Configured source is already bound to a different external "
                        "resource target; use a distinct MSGLOOM_SOURCE_ID."
                    )
                self._inc("msgloom/source_target/verified_count")
                return "verified"

            has_data = self._source_has_persisted_data(connection)
            if has_data and identity.target_key != SELF_MAILBOX_KEY:
                self._inc("msgloom/source_target/migration_refused_count")
                raise SourceTargetMismatch(
                    "Existing source data predates target binding and therefore belongs "
                    "to the signed-in mailbox; use a new MSGLOOM_SOURCE_ID for a shared "
                    "or delegated mailbox."
                )
            method = "legacy_self_mailbox" if has_data else "auto_empty"
            connection.execute(
                insert(SourceTargetBinding).values(
                    source_id=self.source_id,
                    provider=provider,
                    resource_kind=resource_kind,
                    key_scheme=key_scheme,
                    target_key_sha256=digest,
                    binding_method=method,
                    bound_at=datetime.now(UTC).isoformat(),
                )
            )
        self._inc("msgloom/source_target/bound_count")
        return "bound"

    @staticmethod
    def _snapshot(binding: SourceTargetBinding) -> SourceTargetBindingSnapshot:
        return SourceTargetBindingSnapshot(
            provider=binding.provider,
            resource_kind=binding.resource_kind,
            key_scheme=binding.key_scheme,
            target_key_sha256=binding.target_key_sha256,
            binding_method=binding.binding_method,
            bound_at=binding.bound_at,
        )

    @staticmethod
    def _normalized(identity: SourceTargetIdentity) -> tuple[str, str, str, str]:
        provider = identity.provider.strip()
        resource_kind = identity.resource_kind.strip()
        key_scheme = identity.key_scheme.strip()
        target_key = identity.target_key
        if not provider or not resource_kind or not key_scheme:
            raise ValueError("Source target metadata must not be empty")
        if (
            not isinstance(target_key, str)
            or not target_key
            or target_key != target_key.strip()
        ):
            raise ValueError("Source target key must be non-empty without whitespace")
        material = (
            _HASH_DOMAIN
            + provider.encode()
            + b"\0"
            + resource_kind.encode()
            + b"\0"
            + key_scheme.encode()
            + b"\0"
            + target_key.encode()
        )
        return provider, resource_kind, key_scheme, hashlib.sha256(material).hexdigest()

    def _source_has_persisted_data(self, connection) -> bool:
        for table in Base.metadata.sorted_tables:
            if table in {
                RawHttpEvidence.__table__,
                SourceBinding.__table__,
                SourceTargetBinding.__table__,
            }:
                continue
            if "source_id" not in table.c:
                continue
            if (
                connection.execute(
                    select(table.c.source_id)
                    .where(table.c.source_id == self.source_id)
                    .limit(1)
                ).first()
                is not None
            ):
                return True
        return False

    def _inc(self, key: str) -> None:
        if self.stats is not None:
            self.stats.inc_value(key)


__all__ = [
    "SELF_MAILBOX_KEY",
    "SourceTargetBindingService",
    "SourceTargetBindingSnapshot",
    "SourceTargetError",
    "SourceTargetIdentity",
    "SourceTargetMismatch",
]
