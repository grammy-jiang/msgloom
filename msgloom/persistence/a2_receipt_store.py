"""
Bounded receipt-coverage proof and publisher claim history, outside SQL.

CANDIDATE/RESEARCH (C0-14a). Every wire name, file name, domain string
and limit here is PROVISIONAL until the C0 schema review freezes it. Tests
use ``tmp_path`` directories. Nothing touches a real database.

Schema 5 has no column for the receipt proof or the claim history (see
``docs/notes/a2-v2-db-store.md``). This store keeps both as small
write-once files under a caller-owned directory. It adds no table. It binds
to the accepted-stage records in SQL by digest only.

:class:`ReceiptProof` holds one :class:`CoverageItem` (role, position,
result id, digest) for each occurrence of a :class:`CompletionReceipt`:
``root`` or ``baseline`` items by position, then ``transition`` items by
position. A root or baseline digest is ``AcceptedStage.record_sha256()``. A
transition digest binds the accepted batch record, the position and the
exact transition. A self digest makes a flipped stored byte fail closed.
:func:`verify_receipt_proof` rebuilds the expected proof and refuses a
missing, extra, duplicate, out-of-order or altered item.

Claim history: :meth:`ReceiptStore.append_claim` stores the publisher's
original :class:`ClaimEntry` events, one file per sequence, chained by
SHA-256. There is no update or delete function. A different entry at a
stored sequence raises :exc:`A2ReceiptConflict`. The same entry replays.

Head anchor: the chain alone cannot show that its tail was removed. A
reader that deletes ``claim-00002.json`` leaves a valid shorter chain.
Without an anchor, tail truncation or rollback is NOT detectable.
:meth:`ReceiptStore.claim_history` and :meth:`ReceiptStore.append_claim`
accept an optional ``expected_head_sha256``. It is the ``entry_sha256`` of
the newest claim (``GENESIS`` for an empty history). A different stored
head raises ``claim-head-mismatch``. The caller must take the anchor from a
trusted place, the SQL claim table. That cross-check is a later task and is
not implemented here. With no anchor, behavior is unchanged.

Atomicity: a file is written in full under a private temporary name, flushed
with ``fsync`` and published with ``os.link``, which fails if the final name
exists. The directory is then flushed with ``fsync``. A short write, an
error before the link or a failed size check leaves no final file. Readers
ignore a leftover ``.tmp-*`` file. See :mod:`msgloom.persistence.a2_receipt_io`.

Bounds fail closed and are never clamped. Errors are :exc:`A2ReceiptError`
with a fixed ``reason`` code and never carry a path, id, digest, claim
value or pydantic text. Directory names are digests of the workset ref.
Concurrent appenders of one sequence are safe (one link wins). There is no
wider cross-process lock. Durability needs a local POSIX file system.
:meth:`ReceiptStore.get_receipt_proof` checks only the self digest of the
proof. A caller must run :func:`verify_receipt_proof` against the receipt and
the accepted-stage records.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, model_validator

from msgloom.a2_kedro.contracts.codec import (
    A2ContractError,
    A2Model,
    Digest,
    Text,
    canonical_model_bytes,
    decode_canonical_json,
    domain_sha256,
)
from msgloom.a2_kedro.contracts.identity import AttemptProof
from msgloom.a2_kedro.contracts.receipt import CompletionReceipt
from msgloom.a2_kedro.contracts.schema_ids import is_accepted_key, require_stage_schema
from msgloom.contracts import ResultRef
from msgloom.persistence.a2_acceptance_models import AcceptedStage
from msgloom.persistence.a2_receipt_errors import (
    A2ReceiptBoundError,
    A2ReceiptConflict,
    A2ReceiptError,
)
from msgloom.persistence.a2_receipt_io import (
    create_once,
    fsync_directory,
    read_bounded,
)

#: PROVISIONAL limits. Roots and transitions are each bounded by 1024.
MAX_COVERAGE_ITEMS = 2048
MAX_PROOF_BYTES = 1024 * 1024
MAX_CLAIMS = 256
MAX_CLAIM_BYTES = 8 * 1024
GENESIS = "0" * 64

PutOutcome = Literal["inserted", "replayed"]
Role = Literal["root", "baseline", "transition"]

_PROOF_DOMAIN = "a2-receipt-proof@1"
_ITEM_DOMAIN = "a2-receipt-transition-item@1"
_CLAIM_DOMAIN = "a2-claim-history-entry@1"
_DIR_DOMAIN = "a2-receipt-store-workset@1"
_PROOF_FILE = "receipt-proof.json"
_CLAIM_FILE = re.compile(r"claim-(\d{5})\.json")
_RANK = {"root": 0, "baseline": 0, "transition": 1}


class CoverageItem(A2Model):
    """One covered occurrence, referenced by id and digest."""

    role: Role
    position: Annotated[int, Field(ge=0, le=1023)]
    item_id: Text
    item_sha256: Digest


def check_structure(items: Sequence[CoverageItem]) -> None:
    """Raise unless ``items`` are bounded, unique and in canonical order."""
    if len(items) > MAX_COVERAGE_ITEMS:
        raise A2ReceiptBoundError("coverage-too-many")
    if len({item.role for item in items} & {"root", "baseline"}) > 1:
        raise A2ReceiptError("coverage-role-mix")
    if len({(item.role, item.position) for item in items}) != len(items):
        raise A2ReceiptError("coverage-duplicate")
    keys = [(_RANK[item.role], item.position) for item in items]
    if keys != sorted(keys):
        raise A2ReceiptError("coverage-order")


class ReceiptProof(A2Model):
    """Bounded, self-digested coverage proof for one completion receipt."""

    workset: ResultRef
    receipt_sha256: Digest
    policy_version: Text
    items: tuple[CoverageItem, ...] = Field(max_length=MAX_COVERAGE_ITEMS)
    proof_sha256: Digest

    @model_validator(mode="after")
    def _sealed(self) -> ReceiptProof:
        try:
            check_structure(self.items)
        except A2ReceiptError:
            raise A2ContractError("proof structure") from None
        if self.proof_sha256 != _proof_digest(self.model_dump(mode="json")):
            raise A2ContractError("proof digest")
        return self


def _proof_digest(data: Mapping[str, object]) -> str:
    body = {name: value for name, value in data.items() if name != "proof_sha256"}
    return domain_sha256(_PROOF_DOMAIN, body)


def seal_proof(
    workset: ResultRef,
    receipt_sha256: str,
    policy_version: str,
    items: Sequence[CoverageItem],
) -> ReceiptProof:
    """
    Build a proof and seal its self digest.

    Raises :exc:`A2ReceiptError` for duplicate or out-of-order items. This
    does not check the receipt; :func:`verify_receipt_proof` does.
    """
    check_structure(items)
    body = {
        "workset": asdict(workset),
        "receipt_sha256": receipt_sha256,
        "policy_version": policy_version,
        "items": [item.model_dump(mode="json") for item in items],
    }
    try:
        return ReceiptProof.model_validate_json(
            json.dumps({**body, "proof_sha256": _proof_digest(body)})
        )
    except (ValueError, TypeError):
        raise A2ReceiptError("proof-invalid") from None


def _accepted(
    accepted: Mapping[str, AcceptedStage], ref: ResultRef, status: object
) -> AcceptedStage:
    stage = accepted.get(ref.result_id)
    if stage is None:
        raise A2ReceiptError("accepted-result-missing")
    if stage.output != ref or stage.status is not status:
        raise A2ReceiptError("accepted-result-mismatch")
    return stage


def expected_items(
    receipt: CompletionReceipt, accepted: Mapping[str, AcceptedStage]
) -> tuple[CoverageItem, ...]:
    """
    Derive the only coverage a receipt may carry.

    ``accepted`` maps a logical key to its verified accepted-stage record.
    Extra entries are ignored. A missing or mismatched record raises.
    """
    items: list[CoverageItem] = []
    for root in receipt.roots:
        stage = _accepted(accepted, root.result, root.status)
        items.append(
            CoverageItem(
                role="baseline" if root.baseline_selection is not None else "root",
                position=root.workset_selection_index,
                item_id=root.result.result_id,
                item_sha256=stage.record_sha256(),
            )
        )
    batch = receipt.transition_batch
    if batch is None:
        return tuple(items)
    stage = _accepted(accepted, batch.result, batch.status)
    for position, transition in enumerate(batch.transitions):
        digest = domain_sha256(
            _ITEM_DOMAIN,
            {
                "batch": stage.record_sha256(),
                "position": position,
                "transition": transition.model_dump(mode="json"),
            },
        )
        items.append(
            CoverageItem(
                role="transition",
                position=position,
                item_id=batch.result.result_id,
                item_sha256=digest,
            )
        )
    return tuple(items)


def build_receipt_proof(
    receipt: CompletionReceipt, accepted: Mapping[str, AcceptedStage]
) -> ReceiptProof:
    """Build the proof a receipt must have, from accepted-stage records."""
    return seal_proof(
        receipt.workset,
        receipt.digest(),
        receipt.policy_version,
        expected_items(receipt, accepted),
    )


def verify_receipt_proof(
    proof: ReceiptProof,
    receipt: CompletionReceipt,
    accepted: Mapping[str, AcceptedStage],
) -> None:
    """Raise :exc:`A2ReceiptError` unless ``proof`` is exactly the coverage."""
    want = expected_items(receipt, accepted)
    if proof.workset != receipt.workset:
        raise A2ReceiptError("proof-workset-mismatch")
    header = (proof.receipt_sha256, proof.policy_version)
    if header != (receipt.digest(), receipt.policy_version):
        raise A2ReceiptError("proof-receipt-mismatch")
    have = {(item.role, item.position): item for item in proof.items}
    need = {(item.role, item.position): item for item in want}
    if need.keys() - have.keys():
        raise A2ReceiptError("coverage-missing")
    if have.keys() - need.keys():
        raise A2ReceiptError("coverage-extra")
    for key, item in need.items():
        if have[key].item_id != item.item_id:
            raise A2ReceiptError("coverage-id-mismatch")
        if have[key].item_sha256 != item.item_sha256:
            raise A2ReceiptError("coverage-digest-mismatch")
    if proof.items != want:
        raise A2ReceiptError("coverage-order")


class ClaimEntry(A2Model):
    """One raw publisher event: who claimed, published or released."""

    event: Literal["claimed", "published", "released"]
    proof: AttemptProof
    result: ResultRef | None = None

    @model_validator(mode="after")
    def _shape(self) -> ClaimEntry:
        if (self.event == "published") != (self.result is not None):
            raise A2ContractError("result belongs to published only")
        if self.result is not None:
            require_stage_schema(self.result.kind, self.result.schema_version)
            if not is_accepted_key(self.result.result_id):
                raise A2ContractError("result is not an accepted key")
        return self


class StoredClaim(A2Model):
    """A claim entry with its sequence and hash-chain links."""

    seq: Annotated[int, Field(ge=0, lt=MAX_CLAIMS)]
    prev_sha256: Digest
    entry: ClaimEntry
    entry_sha256: Digest

    @model_validator(mode="after")
    def _chained(self) -> StoredClaim:
        if self.entry_sha256 != _claim_digest(self.seq, self.prev_sha256, self.entry):
            raise A2ContractError("claim digest")
        return self


def _claim_digest(seq: int, prev: str, entry: ClaimEntry) -> str:
    body = {"seq": seq, "prev_sha256": prev, "entry": entry.model_dump(mode="json")}
    return domain_sha256(_CLAIM_DOMAIN, body)


def _decode[M: A2Model](
    model: type[M], data: bytes | None, limit: int, reason: str
) -> M:
    """Decode canonical bytes into ``model``; any failure gives ``reason``."""
    try:
        if data is None:
            raise A2ReceiptError(reason)
        decode_canonical_json(data, max_bytes=limit)
        return model.model_validate_json(data)
    except ValueError:
        raise A2ReceiptError(reason) from None


def _canonical(model: A2Model, limit: int) -> bytes:
    """Return canonical bytes of ``model``; an oversize payload is a bound error."""
    try:
        return canonical_model_bytes(model, max_bytes=limit)
    except A2ContractError:
        raise A2ReceiptBoundError("payload-too-large") from None


class ReceiptStore:
    """Write-once receipt proofs and append-only claim histories."""

    def __init__(self, root: Path) -> None:
        if root.is_symlink() or not root.is_dir():
            raise A2ReceiptError("store-root-invalid")
        self._root = root

    def _flush(self, workset: ResultRef) -> None:
        """Flush the workset directory; an ``OSError`` is ``write-failed``."""
        try:
            fsync_directory(self._directory(workset))
        except OSError:
            raise A2ReceiptError("write-failed") from None

    def _directory(self, workset: ResultRef, *, create: bool = False) -> Path:
        name = domain_sha256(
            _DIR_DOMAIN, [workset.result_id, workset.kind, workset.schema_version]
        )
        path = self._root / name
        try:
            if create:
                path.mkdir(exist_ok=True)
        except OSError:
            raise A2ReceiptError("write-failed") from None
        if path.is_symlink():
            raise A2ReceiptError("store-root-invalid")
        if create:
            try:
                fsync_directory(self._root)  # make a new directory name durable
            except OSError:
                raise A2ReceiptError("write-failed") from None
        return path

    def put_receipt_proof(
        self,
        proof: ReceiptProof,
        receipt: CompletionReceipt,
        accepted: Mapping[str, AcceptedStage],
    ) -> PutOutcome:
        """
        Verify ``proof`` against the receipt and store it once.

        Returns ``inserted`` or ``replayed`` for an identical proof. Another
        proof for the same workset raises :exc:`A2ReceiptConflict`.
        """
        verify_receipt_proof(proof, receipt, accepted)
        data = _canonical(proof, MAX_PROOF_BYTES)
        directory = self._directory(proof.workset, create=True)
        if create_once(directory, _PROOF_FILE, data):
            return "inserted"
        if read_bounded(directory / _PROOF_FILE, MAX_PROOF_BYTES) != data:
            raise A2ReceiptConflict("receipt-proof-conflict", ("proof",))
        return "replayed"

    def get_receipt_proof(self, workset: ResultRef) -> ReceiptProof | None:
        """Return the stored proof after a full integrity check."""
        data = read_bounded(self._directory(workset) / _PROOF_FILE, MAX_PROOF_BYTES)
        if data is None:
            return None
        proof = _decode(ReceiptProof, data, MAX_PROOF_BYTES, "stored-proof-corrupt")
        if proof.workset != workset:
            raise A2ReceiptError("stored-proof-corrupt")
        return proof

    def claim_history(
        self, workset: ResultRef, *, expected_head_sha256: str | None = None
    ) -> tuple[StoredClaim, ...]:
        """
        Return the verified claim chain, oldest first.

        With ``expected_head_sha256`` the stored head must match it, or
        ``claim-head-mismatch`` is raised. This detects a removed tail or an
        empty history. Without it a removed tail is NOT detectable.
        """
        directory = self._directory(workset)
        try:
            names = sorted(n for n in os.listdir(directory) if n.startswith("claim-"))
        except FileNotFoundError:
            names = []
        except OSError:
            raise A2ReceiptError("read-failed") from None
        if len(names) > MAX_CLAIMS:
            raise A2ReceiptBoundError("claim-history-too-long")
        claims: list[StoredClaim] = []
        prev = GENESIS
        for index, name in enumerate(names):
            if not (found := _CLAIM_FILE.fullmatch(name)) or int(found[1]) != index:
                raise A2ReceiptError("claim-history-corrupt")
            data = read_bounded(directory / name, MAX_CLAIM_BYTES)
            stored = _decode(
                StoredClaim, data, MAX_CLAIM_BYTES, "claim-history-corrupt"
            )
            if stored.seq != index or stored.prev_sha256 != prev:
                raise A2ReceiptError("claim-history-corrupt")
            claims.append(stored)
            prev = stored.entry_sha256
        if expected_head_sha256 is not None and expected_head_sha256 != prev:
            raise A2ReceiptError("claim-head-mismatch")
        return tuple(claims)

    def append_claim(
        self,
        workset: ResultRef,
        entry: ClaimEntry,
        expected_seq: int,
        *,
        expected_head_sha256: str | None = None,
    ) -> PutOutcome:
        """
        Append ``entry`` at ``expected_seq``; never rewrite history.

        The same entry at a stored sequence replays, after the workset
        directory is flushed again. A failed flush raises ``write-failed``
        and never returns ``replayed``. A different entry raises :exc:`A2ReceiptConflict`. A sequence past the end raises
        ``claim-gap``. A full history raises :exc:`A2ReceiptBoundError`.

        ``expected_head_sha256`` is checked against the stored head before
        this call changes anything (see :meth:`claim_history`). After an
        append the new head is the ``entry_sha256`` of the new claim.
        """
        if not 0 <= expected_seq < MAX_CLAIMS:
            raise A2ReceiptBoundError("claim-history-too-long")
        history = self.claim_history(workset, expected_head_sha256=expected_head_sha256)
        if (outcome := _replay(history, entry, expected_seq)) is not None:
            # The stored name may not be durable yet: flush it before replaying.
            self._flush(workset)
            return outcome
        prev = history[-1].entry_sha256 if history else GENESIS
        stored = StoredClaim(
            seq=expected_seq,
            prev_sha256=prev,
            entry=entry,
            entry_sha256=_claim_digest(expected_seq, prev, entry),
        )
        claim_data = _canonical(stored, MAX_CLAIM_BYTES)
        directory = self._directory(workset, create=True)
        name = f"claim-{expected_seq:05d}.json"
        if create_once(directory, name, claim_data):
            return "inserted"
        # Lost a race for this sequence: the winner decides.
        outcome = _replay(self.claim_history(workset), entry, expected_seq)
        if outcome is None:
            raise A2ReceiptError("claim-history-corrupt")
        return outcome


def _replay(
    history: tuple[StoredClaim, ...], entry: ClaimEntry, seq: int
) -> PutOutcome | None:
    """Return ``replayed`` for a match, ``None`` for the next free slot."""
    if seq > len(history):
        raise A2ReceiptError("claim-gap")
    if seq < len(history) and history[seq].entry != entry:
        raise A2ReceiptConflict("claim-history-rewrite", ("entry",))
    return "replayed" if seq < len(history) else None
