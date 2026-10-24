"""
Replay-policy idempotency keys for A2 v2 (P3-07).

A replay of a stage is safe only when its key says which rules produced
the result and which scope and workset it belongs to. The key covers
three things:

* the input identity digest, for example the digest inside a
  ``StageIdentity.logical_key``;
* an explicit ``scope_key`` and ``workset``, the same two fields that
  ``StageIdentity`` carries. Two worksets with equal content must not
  share a key, so the caller must pass both. Each is non-empty, bounded
  text; an empty or missing value raises :exc:`A2ContractError`; and
* a :class:`ReplayPolicy`: policy id, policy version, configuration
  digest, code version and schema version.

A change to any one field gives a new key. The hash material is a
canonical JSON object with named fields. JSON string quoting makes every
boundary unambiguous, so ``("a|b", "c")`` and ``("a", "b|c")`` give
different keys. The same input, scope and policy give the same key on
every host and in every process. The key is a
value. A policy bump creates a new key and leaves every earlier key and
record as it was. Nothing in this module stores state.

Reuse, no new hash scheme: canonical bytes and the NUL-delimited domain
separator come from
:func:`~msgloom.a2_kedro.contracts.codec.domain_sha256`. The key domain
differs from the stage-identity domains, so a replay key never equals an
accepted stage key (``a2-accepted:``) built from the same bytes. The
``a2-replay:`` prefix also fails
:func:`~msgloom.a2_kedro.contracts.schema_ids.is_accepted_key`.

Errors never echo an input value. Models hide pydantic input values, and
:exc:`~msgloom.a2_kedro.contracts.codec.A2ContractError` messages are
fixed text.

CANDIDATE/RESEARCH: the domains and the prefix are provisional until
C0-00 freezes them.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Self

from pydantic import ValidationError, model_validator

from msgloom.a2_kedro.contracts.codec import (
    A2ContractError,
    Digest,
    Text,
    domain_sha256,
)
from msgloom.a2_kedro.contracts.result_base import ResultPart

#: Domain of the replay idempotency key digest.
REPLAY_KEY_DOMAIN = "a2-replay-idempotency-key@1"
#: Domain of a configuration digest made by :func:`config_digest`.
CONFIG_DOMAIN = "a2-replay-config@1"
#: Prefix of a replay key; it differs from ``a2-accepted:`` on purpose.
REPLAY_KEY_PREFIX = "a2-replay:"
REPLAY_KEY_LENGTH = len(REPLAY_KEY_PREFIX) + 64


class _DigestBox(ResultPart):
    """Validate one digest without echoing the rejected value."""

    value: Digest


def _clean_digest(value: object) -> str:
    try:
        return _DigestBox.model_validate({"value": value}).value
    except ValidationError:
        raise A2ContractError("input digest is not a SHA-256 hex digest") from None


def config_digest(config: Mapping[str, Any]) -> str:
    """
    Return the domain-separated digest of a configuration mapping.

    The digest uses canonical JSON, so the order of mapping keys at any
    depth does not matter. Floats and other non-JSON values raise
    :exc:`A2ContractError`; write such a value as text.
    """
    if not isinstance(config, Mapping):
        raise A2ContractError("configuration must be a mapping")
    return domain_sha256(CONFIG_DOMAIN, dict(config))


class ReplayScope(ResultPart):
    """
    The scope and workset that a replay key belongs to.

    Both fields are required, non-empty and bounded by the A2 text rules.
    They mirror ``StageIdentity.scope_key`` and ``StageIdentity.workset``.
    The caller supplies them; this module does not check that they
    exist in any store.
    """

    scope_key: Text
    workset: Text


def _clean_scope(scope_key: object, workset: object) -> ReplayScope:
    try:
        return ReplayScope.model_validate({"scope_key": scope_key, "workset": workset})
    except ValidationError:
        raise A2ContractError("scope key or workset is not valid text") from None


class ReplayPolicy(ResultPart):
    """
    Frozen description of the rules that a replay runs under.

    Equal fields give equal keys. A change to any field gives a new key.
    Use :func:`config_digest` for ``config_digest``.
    """

    policy_id: Text
    policy_version: Text
    config_digest: Digest
    code_version: Text
    schema_version: Text


class ReplayKey(ResultPart):
    """
    A derived key kept with the facts that produced it.

    The record is a value. ``key`` must equal the key derived from
    ``input_digest``, ``scope_key``, ``workset`` and ``policy``, so a
    forged or stale record fails validation. A new policy gives a new record; the old record stays.
    """

    key: Text
    input_digest: Digest
    scope_key: Text
    workset: Text
    policy: ReplayPolicy

    @model_validator(mode="after")
    def _key_matches_facts(self) -> Self:
        expected = derive_replay_key(
            self.input_digest,
            self.policy,
            scope_key=self.scope_key,
            workset=self.workset,
        )
        if self.key != expected:
            raise A2ContractError("replay key does not match its inputs")
        return self

    @classmethod
    def derive(
        cls,
        input_digest: str,
        policy: ReplayPolicy,
        *,
        scope_key: str,
        workset: str,
    ) -> ReplayKey:
        """Return the record for ``input_digest`` in a scope under ``policy``."""
        return cls(
            key=derive_replay_key(
                input_digest, policy, scope_key=scope_key, workset=workset
            ),
            input_digest=input_digest,
            scope_key=scope_key,
            workset=workset,
            policy=policy,
        )


def derive_replay_key(
    input_digest: str,
    policy: ReplayPolicy,
    *,
    scope_key: str,
    workset: str,
) -> str:
    """
    Return the replay idempotency key for an input, scope and policy.

    ``scope_key`` and ``workset`` are required keyword arguments. The
    function is pure. It reads no clock, host, environment or store. The
    same arguments give the same key. Raise :exc:`A2ContractError` for a
    bad digest, an empty, oversized or non-text scope key or workset, or
    a value that is not a valid ``ReplayPolicy``.
    """
    digest = _clean_digest(input_digest)
    scope = _clean_scope(scope_key, workset)
    if not isinstance(policy, ReplayPolicy):
        raise A2ContractError("policy must be a ReplayPolicy")
    try:
        # Re-validate: ``model_construct`` can build an unchecked model.
        checked = ReplayPolicy.model_validate(policy.model_dump(mode="python"))
    except ValidationError:
        raise A2ContractError("replay policy is not valid") from None
    return REPLAY_KEY_PREFIX + domain_sha256(
        REPLAY_KEY_DOMAIN,
        {
            "input_digest": digest,
            "scope": scope.model_dump(mode="json"),
            "policy": checked.model_dump(mode="json"),
        },
    )


def is_replay_key(value: str) -> bool:
    """Return whether ``value`` has the shape of a replay key."""
    if len(value) != REPLAY_KEY_LENGTH or not value.startswith(REPLAY_KEY_PREFIX):
        return False
    return all(c in "0123456789abcdef" for c in value[len(REPLAY_KEY_PREFIX) :])
