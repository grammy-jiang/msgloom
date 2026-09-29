"""Check lease time at accepted writer transaction boundaries."""

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from msgloom.contracts import (
    AttemptIdentity,
    ClaimKind,
    ExecutionIdentity,
    ExternalEffectState,
    TerminalStatus,
)
from msgloom.persistence import StaleClaimError
from msgloom.persistence import store as store_module
from msgloom.persistence.records import WORK_CLAIMS
from tests.persistence_fences.test_claim_fencing import _registries, _result, _url


class _Clock:
    value = datetime(2026, 1, 1, tzinfo=UTC)

    @classmethod
    def now(cls, timezone):
        return cls.value


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    registry, semantic_registry = _registries()
    value = store_module.Phase1Store(
        _url(tmp_path / "time.sqlite3"),
        registry=registry,
        semantic_registry=semantic_registry,
    )
    _Clock.value = datetime(2026, 1, 1, tzinfo=UTC)
    monkeypatch.setattr(store_module, "datetime", _Clock)
    try:
        yield value
    finally:
        value.close()


def _claim(store, *, lease=60):
    return store.acquire_claim(
        "prepare:time",
        ClaimKind.PREPARE,
        ExecutionIdentity("execution-time"),
        AttemptIdentity("attempt-time"),
        (),
        lease,
    )


def _advance_on_lock(store, monkeypatch):
    original = store._write_transaction

    @contextmanager
    def delayed_lock():
        with original() as connection:
            _Clock.value += timedelta(seconds=61)
            yield connection

    monkeypatch.setattr(store, "_write_transaction", delayed_lock)


def test_acquisition_starts_lease_after_waiting_for_writer(store, monkeypatch):
    _advance_on_lock(store, monkeypatch)
    token = _claim(store)
    with store.engine.connect() as connection:
        row = connection.execute(WORK_CLAIMS.select()).mappings().one()
    if row["claim_token"] != token.token:
        pytest.fail("Acquisition did not save the returned claim")
    expiry = datetime.fromisoformat(row["expires_at"])
    if expiry - _Clock.value != timedelta(seconds=60):
        pytest.fail("Waiting for the writer consumed the new claim lease")


def test_completion_checks_expiry_after_waiting_for_writer(store, monkeypatch):
    token = _claim(store)
    _advance_on_lock(store, monkeypatch)
    with pytest.raises(StaleClaimError):
        store.finish_claim(token, TerminalStatus.COMPLETE, ExternalEffectState.NONE)


@pytest.mark.parametrize("semantic", [False, True])
def test_publication_rolls_back_if_lease_expires_during_write(
    store, monkeypatch, semantic
):
    token = _claim(store)
    original = store_module.append_stage_result

    def delayed_write(*args, **kwargs):
        original(*args, **kwargs)
        _Clock.value += timedelta(seconds=61)

    monkeypatch.setattr(store_module, "append_stage_result", delayed_write)
    data_ref = (
        store.semantic_reference("data", "fenced_data", "1", "synthetic")
        if semantic
        else None
    )
    result = _result(
        "expired-during-write",
        token.execution,
        kind="fenced_data" if semantic else "fenced_result",
        semantic_data_ref=data_ref,
    )
    with pytest.raises(StaleClaimError):
        if semantic:
            store.append_result_with_data(result, "synthetic", claim=token)
        else:
            store.append_result(result, claim=token)
    if store.get_result(result.result_id) is not None:
        pytest.fail("Expired publication survived transaction rollback")
