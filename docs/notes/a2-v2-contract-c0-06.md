# A2 v2 contract C0-06: native_relations@1 (PROVISIONAL)

Code: `msgloom/a2_kedro/contracts/relations.py`.
Tests: `tests/a2_kedro/test_c0_06.py`.

All names and limits below are PROVISIONAL. The wire-form test fails on
any change.

- Record fields: `header`, `nodes`, `relations`.
- Node fields: `scope_kind`, `scope_id`, `node_id`.
- Scope kinds: `mailbox`, `thread`, `channel`.
- Relation fields: `kind`, `source`, `target`, `status`, `basis`.
- Relation kinds: `reply_to`, `ancestor`, `reference`.
- `status` is always `hypothesis`. A relation is never a fact here.
- Limits: 1024 nodes, 4096 relations.
- Rules: both endpoints are declared nodes of the same scope. No self
  relation. No duplicate `(kind, source, target)`. `reply_to` and
  `ancestor` edges have no cycle. `reference` cycles are legal. Nodes and
  relations are sorted for one canonical byte form.

Direction: `reply_to` and `ancestor` both point from the later node
(`source`) to the earlier node (`target`). `ancestor` means `target` is an
ancestor of `source` at any distance. `reference` has no time direction.
The code checks no timestamps. The direction is a convention that keeps the
joined cycle check meaningful.

Open: the vocabulary of `basis` (evidence reference) is not decided.
Open: whether a cross-scope relation needs a separate explicit kind.
