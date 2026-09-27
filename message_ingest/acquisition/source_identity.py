"""Bind one logical source ID to one stable external provider account."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime

from scrapy.exceptions import NotConfigured
from sqlalchemy import insert, select, update
from sqlalchemy.engine import Connection

from message_ingest.catalog.models import Base, SourceBinding
from message_ingest.extensions.catalog import CatalogService

_SERVICE_ATTR = "_msgloom_source_identity_service"
_HASH_DOMAIN = b"msgloom-source-binding-v1\0"


class SourceIdentityError(RuntimeError):
    """Base error for source-to-provider identity integrity failures."""


class SourceIdentityMismatch(SourceIdentityError):
    """The source is already bound to a different provider account."""


class SourceIdentityBootstrapRequired(SourceIdentityError):
    """Legacy data needs one explicit identity-binding confirmation."""


@dataclass(frozen=True, slots=True)
class SourceIdentity:
    """Opaque provider identity supplied by an acquisition provider."""

    provider: str
    key_scheme: str
    account_key: str


@dataclass(frozen=True, slots=True)
class SourceBindingSnapshot:
    """Non-secret persisted binding metadata used by provider selection."""

    provider: str
    key_scheme: str
    account_key_sha256: str
    binding_method: str
    bound_at: str


class SourceIdentityService:
    """
    Bind one logical msgloom source to one external provider identity.

    Provider account keys are never persisted directly. A domain-separated
    SHA-256 digest is stored with the provider/key scheme. Empty sources bind
    automatically. Existing unbound data requires an invocation-scoped exact
    source-ID confirmation so an accidental login cannot silently claim it.
    """

    def __init__(
        self,
        *,
        service: CatalogService,
        source_id: str,
        bootstrap_confirm: str,
        stats=None,
    ) -> None:
        """Borrow the crawler catalog and retain source-scoped policy."""
        if not source_id.strip():
            raise ValueError("MSGLOOM_SOURCE_ID must not be empty")
        if source_id != source_id.strip():
            raise ValueError(
                "MSGLOOM_SOURCE_ID must not contain surrounding whitespace"
            )
        self.service = service
        self.catalog = service.catalog
        self.source_id = source_id
        self.bootstrap_confirm = bootstrap_confirm
        self.stats = stats

    @classmethod
    def from_crawler(cls, crawler):
        """Return the crawler-scoped service when persistence is enabled."""
        if not crawler.settings.getbool("MSGLOOM_CATALOG_ENABLED"):
            raise NotConfigured(
                "Source identity binding requires the SQL catalog"
            )
        if (existing := getattr(crawler, _SERVICE_ATTR, None)) is not None:
            return existing
        service = cls(
            service=CatalogService.from_crawler(crawler),
            source_id=crawler.settings["MSGLOOM_SOURCE_ID"],
            bootstrap_confirm=crawler.settings.get(
                "MSGLOOM_SOURCE_IDENTITY_BOOTSTRAP_CONFIRM", ""
            ),
            stats=crawler.stats,
        )
        setattr(crawler, _SERVICE_ATTR, service)
        return service

    def get_binding(self) -> SourceBindingSnapshot | None:
        """Read the current binding without exposing a provider account key."""
        with self.catalog.Session() as session:
            binding = session.get(SourceBinding, self.source_id)
            if binding is None:
                return None
            return self._snapshot(binding)

    def bind_or_verify(self, identity: SourceIdentity) -> str:
        """Bind a new source or verify its external identity atomically."""
        provider, key_scheme, digest = self._normalized_identity(identity)
        binding_method = ""

        try:
            with self.catalog.engine.begin() as connection:
                # Acquire SQLite's writer lock before any read that influences
                # the first-binding decision. The no-op update keeps this
                # entirely inside SQLAlchemy while serializing other writers.
                connection.execute(
                    update(SourceBinding)
                    .where(SourceBinding.source_id == self.source_id)
                    .values(bound_at=SourceBinding.bound_at)
                )
                existing = connection.execute(
                    select(SourceBinding.__table__).where(
                        SourceBinding.source_id == self.source_id
                    )
                ).mappings().first()
                if existing is not None:
                    outcome = self._verify_values(
                        provider=provider,
                        key_scheme=key_scheme,
                        digest=digest,
                        stored_provider=existing["provider"],
                        stored_key_scheme=existing["key_scheme"],
                        stored_digest=existing["account_key_sha256"],
                    )
                    self._publish_verified(provider)
                    return outcome

                has_data = self._source_has_persisted_data(connection)
                if has_data and self.bootstrap_confirm != self.source_id:
                    self._inc(
                        "msgloom/source_identity/bootstrap_required_count"
                    )
                    raise SourceIdentityBootstrapRequired(
                        f"Source {self.source_id!r} already contains "
                        "acquisition data but has no provider identity "
                        "binding. Re-run once with -s "
                        "MSGLOOM_SOURCE_IDENTITY_BOOTSTRAP_CONFIRM="
                        f"{self.source_id!r} only after confirming the "
                        "selected account owns the existing data."
                    )

                binding_method = (
                    "bootstrap_attested" if has_data else "auto_empty"
                )
                connection.execute(
                    insert(SourceBinding).values(
                        source_id=self.source_id,
                        provider=provider,
                        key_scheme=key_scheme,
                        account_key_sha256=digest,
                        binding_method=binding_method,
                        bound_at=datetime.now(UTC).isoformat(),
                    )
                )
        except SourceIdentityError:
            raise
        except Exception as exc:
            self._inc("msgloom/source_identity/bind_error_count")
            raise SourceIdentityError(
                "Unable to establish source identity binding safely"
            ) from exc

        self._set("msgloom/source_identity/provider", provider)
        self._set("msgloom/source_identity/state", "bound")
        self._set("msgloom/source_identity/binding_method", binding_method)
        self._inc("msgloom/source_identity/bound_count")
        return "bound"

    def matches_binding(
        self,
        identity: SourceIdentity,
        binding: SourceBindingSnapshot | None = None,
    ) -> bool:
        """Compare an opaque provider identity with a stored binding."""
        provider, key_scheme, digest = self._normalized_identity(identity)
        binding = binding if binding is not None else self.get_binding()
        return bool(
            binding is not None
            and binding.provider == provider
            and binding.key_scheme == key_scheme
            and binding.account_key_sha256 == digest
        )

    @staticmethod
    def _snapshot(binding: SourceBinding) -> SourceBindingSnapshot:
        """Detach non-secret binding metadata from its ORM session."""
        return SourceBindingSnapshot(
            provider=binding.provider,
            key_scheme=binding.key_scheme,
            account_key_sha256=binding.account_key_sha256,
            binding_method=binding.binding_method,
            bound_at=binding.bound_at,
        )

    @staticmethod
    def _normalized_identity(identity: SourceIdentity) -> tuple[str, str, str]:
        """Validate metadata and hash the exact opaque account key."""
        provider = identity.provider.strip()
        key_scheme = identity.key_scheme.strip()
        account_key = identity.account_key
        if not provider:
            raise ValueError("Source identity provider must not be empty")
        if not key_scheme:
            raise ValueError("Source identity key scheme must not be empty")
        if not isinstance(account_key, str) or not account_key:
            raise ValueError("Provider account key must be a non-empty string")
        material = (
            _HASH_DOMAIN
            + provider.encode("utf-8")
            + b"\0"
            + key_scheme.encode("utf-8")
            + b"\0"
            + account_key.encode("utf-8")
        )
        return provider, key_scheme, hashlib.sha256(material).hexdigest()

    def _verify_values(
        self,
        *,
        provider: str,
        key_scheme: str,
        digest: str,
        stored_provider: str,
        stored_key_scheme: str,
        stored_digest: str,
    ) -> str:
        """Reject account changes without exposing account material."""
        if (
            stored_provider != provider
            or stored_key_scheme != key_scheme
            or stored_digest != digest
        ):
            self._inc("msgloom/source_identity/mismatch_count")
            raise SourceIdentityMismatch(
                "Configured source is already bound to a different external "
                "provider identity; refusing to mix acquisition data."
            )
        return "verified"

    def _source_has_persisted_data(self, connection: Connection) -> bool:
        """Detect existing source-scoped rows across registered models."""
        for table in Base.metadata.sorted_tables:
            if table is SourceBinding.__table__ or "source_id" not in table.c:
                continue
            stmt = (
                select(table.c.source_id)
                .where(table.c.source_id == self.source_id)
                .limit(1)
            )
            if connection.execute(stmt).first() is not None:
                return True
        return False

    def _publish_verified(self, provider: str) -> None:
        """Publish bounded verification diagnostics."""
        self._set("msgloom/source_identity/provider", provider)
        self._set("msgloom/source_identity/state", "verified")
        self._inc("msgloom/source_identity/verified_count")

    def _inc(self, key: str) -> None:
        """Publish only non-identifying source-integrity counters."""
        if self.stats is not None:
            self.stats.inc_value(key)

    def _set(self, key: str, value) -> None:
        """Publish bounded diagnostics without account identifiers."""
        if self.stats is not None:
            self.stats.set_value(key, value)
