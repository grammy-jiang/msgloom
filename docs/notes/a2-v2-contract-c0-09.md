# A2 v2 contract C0-09: a2_input_disposition@1 review (PROVISIONAL)

Code: `msgloom/a2_kedro/contracts/held.py`.
Tests: `tests/a2_kedro/test_c0_09.py`.

The wire names stay as in `docs/decisions/a2-v2-schema-ids.md`. This task
changes no name and no value. The serialized output is unchanged.

Review result. The module already met the goal. A held record carries a
closed `reason` and an explicit `repair_class` (`operator_repair`). It has
no content field. Held-only, context-only and approved-baseline worksets
do not force a body. The receipt treats an A2-held root as a legal
INCOMPLETE terminal.

Gaps fixed:

- `repair_class` had a default. A payload without the field decoded. The
  field is now required. The dump is the same, because the dump always
  held the field. `from_root` passes it explicitly.
- No check tied a stored record to its root. `validate_against(root)` now
  compares the selection, index, digest, release entry and approved
  baseline fields with a verified `FrozenRoot`.
- The model now hides input values in pydantic error text.

Rules kept: every `HeldReason` maps to `operator_repair`. The record has
no body, text or part field (`extra="forbid"`). An incremental record has
a release entry and no baseline field. A baseline record has the approved
source and approval and no release entry.

Open: only one `repair_class` exists. A second class needs a decision
record and a reason-to-class table. Until then the pairing is trivial.
Open: `validate_against` proves consistency with a root the caller
supplies. It cannot prove that the root was verified against A1.
