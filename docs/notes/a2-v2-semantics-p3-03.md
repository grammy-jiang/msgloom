# A2 v2 P3-03 filter verdict (CANDIDATE/RESEARCH, PROVISIONAL)

`msgloom/a2_kedro/semantics/filters.py` uses the verdict domain of
`filter_result@2`: `include`, `exclude`, `conflict`, `unknown`, `no_match`.

- `_expected` in `msgloom/a2_kedro/contracts/results.py` is the only
  mapping from evaluations to verdict and reasons. P3-03 calls it.
- `no_match`: no rule matched and no rule is `unknown`. Earlier P3-03
  code reported `unknown` here (review finding F7). That verdict made a
  `FilterResult` fail with "verdict or reasons differ from evaluations".
- `no_rule_matched` limitation: kept for `no_match`. `FilterResult`
  accepts it, so a `no_match` result has status `INCOMPLETE`.
- `FilterEvaluation` recomputes verdict, reasons and `matched` from its
  evaluations and refuses a forged record (review F15(d), first part).

## Open items

- Subject with tab or newline (F15(d), second part): not done.
  `FilterInput` is an `A2Model`. It raises on a control character in any
  field at construction. An `unknown` outcome needs a policy decision to
  relax that base rule for `subject`. That change is not small.
- Decision for the owner: whether a `no_match` result should be
  `COMPLETE` without the `no_rule_matched` limitation.
