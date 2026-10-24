"""P3-07: replay-policy idempotency keys."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from msgloom.a2_kedro.contracts.codec import (
    A2ContractError,
    canonical_model_bytes,
    decode_model_bytes,
    domain_sha256,
)
from msgloom.a2_kedro.contracts.identity import KEY_DOMAIN, METADATA_DOMAIN
from msgloom.a2_kedro.contracts.schema_ids import is_accepted_key
from msgloom.a2_kedro.semantics.replay_policy import (
    REPLAY_KEY_DOMAIN,
    ReplayKey,
    ReplayPolicy,
    config_digest,
    derive_replay_key,
    is_replay_key,
)

INPUT = "ab" * 32
CONFIG = {"limits": {"max_parts": 8, "mode": "strict"}, "names": ["a", "b"]}
GOLDEN_KEY = (
    "a2-replay:fe50575e402921302ad7188a2f508eac213b5472578b853324b48e0e330ba831"
)
SECRET = "alice@example.invalid-SECRET-7731"


def policy(**changes: Any) -> ReplayPolicy:
    """Return a valid policy with ``changes`` applied."""
    values: dict[str, Any] = {
        "policy_id": "filter-replay",
        "policy_version": "1",
        "config_digest": config_digest(CONFIG),
        "code_version": "code-1",
        "schema_version": "2",
    }
    values.update(changes)
    return ReplayPolicy(**values)


def test_key_is_stable_for_identical_input() -> None:
    first = derive_replay_key(INPUT, policy())
    again = derive_replay_key(INPUT, policy())
    if first != again:
        pytest.fail("same input and policy gave different keys")
    if not is_replay_key(first):
        pytest.fail("key has the wrong shape")
    if first == INPUT:
        pytest.fail("key must not equal the input digest")


def test_key_golden_value_is_pinned() -> None:
    key = derive_replay_key(INPUT, policy())
    if key != GOLDEN_KEY:
        pytest.fail(f"replay key wire value changed: {key}")


@pytest.mark.parametrize(
    "changes",
    [
        {"schema_version": "3"},
        {"policy_id": "other-replay"},
    ],
    ids=["schema_version", "policy_id"],
)
def test_policy_change_gives_new_key(changes: dict[str, Any]) -> None:
    if derive_replay_key(INPUT, policy()) == derive_replay_key(
        INPUT, policy(**changes)
    ):
        pytest.fail("a policy change kept the key")


def test_policy_version_change_gives_new_key() -> None:
    old = derive_replay_key(INPUT, policy(policy_version="1"))
    new = derive_replay_key(INPUT, policy(policy_version="2"))
    if old == new:
        pytest.fail("policy version bump kept the key")


def test_config_digest_change_gives_new_key() -> None:
    changed = policy(config_digest=config_digest({**CONFIG, "extra": 1}))
    if derive_replay_key(INPUT, policy()) == derive_replay_key(INPUT, changed):
        pytest.fail("config change kept the key")


def test_code_version_change_gives_new_key() -> None:
    changed = policy(code_version="code-1+1")
    if derive_replay_key(INPUT, policy()) == derive_replay_key(INPUT, changed):
        pytest.fail("code version change kept the key")


def test_input_digest_change_gives_new_key() -> None:
    other = "cd" * 32
    if derive_replay_key(INPUT, policy()) == derive_replay_key(other, policy()):
        pytest.fail("input digest change kept the key")


def test_fields_do_not_bleed_into_each_other() -> None:
    left = policy(policy_id="a", policy_version="bc")
    right = policy(policy_id="ab", policy_version="c")
    if derive_replay_key(INPUT, left) == derive_replay_key(INPUT, right):
        pytest.fail("field boundary is ambiguous")


def test_config_key_order_does_not_matter() -> None:
    one = {"a": 1, "b": {"x": [1, 2], "y": "t"}, "c": None}
    two = {"c": None, "b": {"y": "t", "x": [1, 2]}, "a": 1}
    if config_digest(one) != config_digest(two):
        pytest.fail("mapping order changed the config digest")
    keys = {
        derive_replay_key(INPUT, policy(config_digest=config_digest(c)))
        for c in (one, two)
    }
    if len(keys) != 1:
        pytest.fail("mapping order changed the key")


def test_config_list_order_does_matter() -> None:
    if config_digest({"a": [1, 2]}) == config_digest({"a": [2, 1]}):
        pytest.fail("list order must stay significant")


@pytest.mark.parametrize("bad", [{"a": 1.5}, {"a": object()}, {1: "x"}])
def test_config_digest_rejects_non_canonical_data(bad: Any) -> None:
    with pytest.raises(A2ContractError):
        config_digest(bad)


def test_config_digest_rejects_non_mapping() -> None:
    with pytest.raises(A2ContractError):
        config_digest([("a", 1)])  # type: ignore[arg-type]


def test_domains_cannot_collide() -> None:
    pol = policy()
    value = {"input_digest": INPUT, "policy": pol.model_dump(mode="json")}
    key = derive_replay_key(INPUT, pol)
    digest = key.removeprefix("a2-replay:")
    if digest != domain_sha256(REPLAY_KEY_DOMAIN, value):
        pytest.fail("key is not the documented domain digest")
    for domain in (KEY_DOMAIN, METADATA_DOMAIN, "a2-replay-config@1"):
        if domain_sha256(domain, value) == digest:
            pytest.fail(f"domain {domain} collides with the replay domain")
    if is_accepted_key(key):
        pytest.fail("a replay key must not look like an accepted key")
    if is_replay_key("a2-accepted:" + digest):
        pytest.fail("an accepted key must not look like a replay key")


def test_config_domain_differs_from_key_domain() -> None:
    if config_digest(CONFIG) == domain_sha256(REPLAY_KEY_DOMAIN, CONFIG):
        pytest.fail("config digest shares the key domain")


def test_unknown_fields_are_rejected() -> None:
    values = policy().model_dump(mode="json")
    with pytest.raises(ValidationError):
        ReplayPolicy.model_validate({**values, "surprise": "x"})
    with pytest.raises(ValidationError):
        ReplayKey.model_validate(
            {**ReplayKey.derive(INPUT, policy()).model_dump(mode="json"), "x": 1}
        )


@pytest.mark.parametrize("missing", list(policy().model_dump()))
def test_missing_fields_are_rejected(missing: str) -> None:
    values = policy().model_dump(mode="json")
    del values[missing]
    with pytest.raises(ValidationError):
        ReplayPolicy(**values)


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "a" * 63,
        "a" * 65,
        "a" * 100_000,
        "A" * 64,
        "g" * 64,
        ("ab" * 32) + "\n",
        " " + "a" * 63,
        None,
        7,
        b"ab" * 32,
    ],
)
def test_bad_input_digest_is_rejected(bad: Any) -> None:
    with pytest.raises(A2ContractError):
        derive_replay_key(bad, policy())


def test_bad_config_digest_is_rejected() -> None:
    for bad in ("", "x" * 64, "a" * 65, "A" * 64):
        with pytest.raises(ValidationError):
            policy(config_digest=bad)


@pytest.mark.parametrize(
    "field", ["policy_id", "policy_version", "code_version", "schema_version"]
)
def test_empty_oversized_or_control_text_is_rejected(field: str) -> None:
    for bad in ("", "x" * 2049, "a\nb", "a\x00b"):
        with pytest.raises(ValidationError):
            policy(**{field: bad})


def test_policy_must_be_a_replay_policy() -> None:
    with pytest.raises(A2ContractError):
        derive_replay_key(INPUT, policy().model_dump())  # type: ignore[arg-type]


def test_unchecked_policy_is_revalidated() -> None:
    forged = ReplayPolicy.model_construct(
        policy_id="p",
        policy_version="",
        config_digest="zz",
        code_version="c",
        schema_version="1",
    )
    with pytest.raises(A2ContractError):
        derive_replay_key(INPUT, forged)


def test_policy_bump_never_mutates_or_overwrites_a_prior_key() -> None:
    old_policy = policy(policy_version="1")
    old = ReplayKey.derive(INPUT, old_policy)
    old_bytes = canonical_model_bytes(old)
    ledger = {old.key: old}
    new_policy = policy(policy_version="2")
    new = ReplayKey.derive(INPUT, new_policy)
    if new.key in ledger:
        pytest.fail("a bump reused the old key")
    ledger[new.key] = new
    if len(ledger) != 2:
        pytest.fail("a bump overwrote a prior record")
    if canonical_model_bytes(ledger[old.key]) != old_bytes:
        pytest.fail("a prior record changed")
    if derive_replay_key(INPUT, old_policy) != old.key:
        pytest.fail("the old policy no longer gives the old key")
    if old.policy.policy_version != "1":
        pytest.fail("the old record points at the new policy")


def test_records_are_frozen_values() -> None:
    record = ReplayKey.derive(INPUT, policy())
    with pytest.raises(ValidationError):
        record.key = "a2-replay:" + "0" * 64  # type: ignore[misc]
    with pytest.raises(ValidationError):
        record.policy.policy_version = "9"  # type: ignore[misc]


def test_record_round_trips_canonical_bytes() -> None:
    record = ReplayKey.derive(INPUT, policy())
    again = decode_model_bytes(ReplayKey, canonical_model_bytes(record))
    if again != record or again.key != record.key:
        pytest.fail("record did not round trip")


def test_forged_record_is_rejected() -> None:
    good = ReplayKey.derive(INPUT, policy()).model_dump(mode="json")
    other = ReplayKey.derive(INPUT, policy(policy_version="2")).key
    with pytest.raises(ValidationError):
        ReplayKey(**{**good, "key": other})
    with pytest.raises(ValidationError):
        ReplayKey(**{**good, "key": "a2-accepted:" + "0" * 64})


def test_str_subclass_text_is_rejected() -> None:
    class Loud(str):
        __slots__ = ()

    with pytest.raises(ValidationError):
        policy(policy_id=Loud("x"))
    with pytest.raises(A2ContractError):
        derive_replay_key(Loud(INPUT), policy())


def test_validation_errors_do_not_echo_input_values() -> None:
    errors: list[str] = []
    for call in (
        lambda: derive_replay_key(SECRET, policy()),
        lambda: policy(config_digest=SECRET),
        lambda: policy(policy_id="\n" + SECRET),
        lambda: policy(policy_version=SECRET * 100),
        lambda: ReplayPolicy.model_validate({**policy().model_dump(), "leak": SECRET}),
        lambda: ReplayKey(key=SECRET, input_digest=INPUT, policy=policy()),
        lambda: ReplayKey(
            key="a2-replay:" + "0" * 64, input_digest=SECRET, policy=policy()
        ),
    ):
        try:
            call()
        except (ValidationError, A2ContractError) as error:
            errors.append(repr(error) + str(error) + repr(error.__cause__))
            continue
        pytest.fail("a bad value was accepted")
    if len(errors) != 7:
        pytest.fail("not every case raised")
    for text in errors:
        if SECRET in text:
            pytest.fail("an error echoed an input value")
