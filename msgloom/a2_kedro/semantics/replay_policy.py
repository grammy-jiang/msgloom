"""
Replay-policy idempotency keys for A2 v2 (P3-07).

A replay of a stage is safe only when its key says which rules produced
the result. The key therefore covers two things:

* the input identity digest, for example the digest inside a
  ``StageIdentity.logical_key``; and
* a :class:`ReplayPolicy`: policy id, policy version, configuration
  digest, code version and schema version.

A change to any one field gives a new key. The same input and the same
policy give the same key on every host and in every process. The key is a
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
    ``input_digest`` and ``policy``, so a forged or stale record fails
    validation. A new policy gives a new record; the old record stays.
    """

    key: Text
    input_digest: Digest
    policy: ReplayPolicy

    @model_validator(mode="after")
    def _key_matches_facts(self) -> Self:
        if self.key != derive_replay_key(self.input_digest, self.policy):
            raise A2ContractError("replay key does not match its inputs")
        return self

    @classmethod
    def derive(cls, input_digest: str, policy: ReplayPolicy) -> ReplayKey:
        """Return the record for ``input_digest`` under ``policy``."""
        return cls(
            key=derive_replay_key(input_digest, policy),
            input_digest=input_digest,
            policy=policy,
        )


def derive_replay_key(input_digest: str, policy: ReplayPolicy) -> str:
    """
    Return the replay idempotency key for an input under a policy.

    The function is pure. It reads no clock, host, environment or store.
    The same arguments give the same key. Raise :exc:`A2ContractError`
    for a bad digest or a value that is not a valid ``ReplayPolicy``.
    """
    digest = _clean_digest(input_digest)
    if not isinstance(policy, ReplayPolicy):
        raise A2ContractError("policy must be a ReplayPolicy")
    try:
        # Re-validate: ``model_construct`` can build an unchecked model.
        checked = ReplayPolicy.model_validate(policy.model_dump(mode="python"))
    except ValidationError:
        raise A2ContractError("replay policy is not valid") from None
    return REPLAY_KEY_PREFIX + domain_sha256(
        REPLAY_KEY_DOMAIN,
        {"input_digest": digest, "policy": checked.model_dump(mode="json")},
    )


def is_replay_key(value: str) -> bool:
    """Return whether ``value`` has the shape of a replay key."""
    if len(value) != REPLAY_KEY_LENGTH or not value.startswith(REPLAY_KEY_PREFIX):
        return False
    return all(c in "0123456789abcdef" for c in value[len(REPLAY_KEY_PREFIX) :])
