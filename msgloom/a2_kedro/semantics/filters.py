"""
Versioned rule filtering for the A2 v2 filter stage (P3-03).

This module is a pure, deterministic function layer. It evaluates a
:class:`RuleSet` against one :class:`FilterInput` and returns a
:class:`FilterEvaluation`. It reads no file, clock, database or provider.

Rules
=====

A :class:`FilterRule` has a rule ID, a rule version, an effect (``include``
or ``exclude``) and one :class:`FilterPredicate`. A predicate names one
typed input field and one value:

====================  =====================================================
Field                 Test
====================  =====================================================
``sender_domain``     case-folded equality with ``sender_domain``
``folder_id``         exact equality with ``folder_id``
``label``             case-folded equality with one item of ``labels``
``subject_prefix``    case-folded prefix test on ``subject``
====================  =====================================================

Case folding is :meth:`str.casefold`. No other normalization is applied:
no trimming, no Unicode normalization and no address parsing. The caller
supplies the sender domain, not an address.

A field that is ``None`` is missing. An empty ``labels`` tuple is a known
empty label list, not a missing field.

Outcomes
========

Each rule gets one :class:`~msgloom.a2_kedro.contracts.results.RuleEvaluation`:
``matched`` (with its effect), ``not_matched``, or ``unknown`` when its
field is missing. A missing field never counts as a match.

The verdict follows the ``filter_result@2`` contract, in this order:

1. ``conflict``: an include rule and an exclude rule both match. Neither
   effect is chosen.
2. ``exclude``: an exclude rule matches and no include rule matches. This
   holds even when another rule is ``unknown``. The reasons name the rule
   IDs.
3. ``unknown``: a rule is ``unknown``, or no rule matches. This verdict
   never becomes ``include`` or ``exclude`` by default. An ``unknown``
   rule blocks ``include`` because it could have matched with the opposite
   effect.
4. ``include``: an include rule matches, no exclude rule matches and no
   rule is ``unknown``.

The contract name ``no_match`` is not used. When no rule matches, this
module reports ``unknown`` with the ``no_rule_matched`` limitation.

Limitations and status
======================

* ``missing_field``: one per missing field that a rule needed. The detail
  is the field name.
* ``no_rule_matched``: no rule matched and no rule is ``unknown``. The
  detail is fixed text.

Status is ``COMPLETE`` only when there is no limitation, else
``INCOMPLETE``. :class:`FilterEvaluation` refuses a record whose verdict is
``unknown`` without a limitation or with ``COMPLETE`` status.

Ordering and failure handling
=============================

Evaluations are sorted by rule ID and ``matched`` lists every matching rule
ID in that order. The rule order of the input never changes the output.
Two rules with one ID raise :exc:`DuplicateRuleIdError`, whose text is
fixed. A malformed model raises a pydantic error that hides the input, so
no field value is echoed.

CANDIDATE/RESEARCH, PROVISIONAL: names and limits are not frozen.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated

from pydantic import Field, model_validator

from msgloom.a2_kedro.contracts.codec import A2ContractError, Text
from msgloom.a2_kedro.contracts.result_base import (
    COMPLETE,
    Accepted,
    Effect,
    ResultPart,
    check_limitations,
    sorted_unique,
)
from msgloom.a2_kedro.contracts.results import MAX_RULES, Reason, RuleEvaluation
from msgloom.contracts import Limitation, TerminalStatus

__all__ = [
    "DuplicateRuleIdError",
    "FilterEvaluation",
    "FilterField",
    "FilterInput",
    "FilterLimitationCode",
    "FilterPredicate",
    "FilterRule",
    "FilterVerdict",
    "RuleSet",
    "evaluate_filters",
]

#: Provisional bound.
MAX_LABELS = 256

NO_MATCH_DETAIL = "no rule matched"


class DuplicateRuleIdError(A2ContractError):
    """Two rules of one rule set share a rule ID. The text is fixed."""


class FilterField(StrEnum):
    """The typed input fields that a predicate can test."""

    SENDER_DOMAIN = "sender_domain"
    FOLDER_ID = "folder_id"
    LABEL = "label"
    SUBJECT_PREFIX = "subject_prefix"


class FilterVerdict(StrEnum):
    """The four verdicts of this evaluator."""

    INCLUDE = "include"
    EXCLUDE = "exclude"
    CONFLICT = "conflict"
    UNKNOWN = "unknown"


class FilterLimitationCode(StrEnum):
    """Closed, content-free reasons that a verdict is not complete."""

    MISSING_FIELD = "missing_field"
    NO_RULE_MATCHED = "no_rule_matched"


class FilterPredicate(ResultPart):
    """One test: ``field`` against ``value``. See the module table."""

    field: FilterField
    value: Text


class FilterRule(ResultPart):
    """One versioned rule with one effect and one predicate."""

    rule_id: Text
    rule_version: Text
    effect: Effect
    predicate: FilterPredicate


class RuleSet(ResultPart):
    """A versioned set of rules. Rule order has no meaning."""

    rule_set_version: Text
    rules: Annotated[tuple[FilterRule, ...], Field(min_length=1, max_length=MAX_RULES)]


class FilterInput(ResultPart):
    """Typed message fields. ``None`` means the field is missing."""

    # Raw input values are hidden from ``repr``.
    sender_domain: Text | None = Field(default=None, repr=False)
    folder_id: Text | None = Field(default=None, repr=False)
    labels: Annotated[tuple[Text, ...], Field(max_length=MAX_LABELS)] | None = Field(
        default=None, repr=False
    )
    subject: str | None = Field(default=None, repr=False)


@dataclass(frozen=True, slots=True)
class _Folded:
    """Case-folded record values. Built once for each evaluation."""

    sender_domain: str | None
    labels: frozenset[str] | None
    subject: str | None


def _fold(record: FilterInput) -> _Folded:
    """Case-fold each record value once, so rules do not repeat the work."""
    sender = record.sender_domain
    labels = record.labels
    subject = record.subject
    return _Folded(
        sender_domain=None if sender is None else sender.casefold(),
        labels=None if labels is None else frozenset(i.casefold() for i in labels),
        subject=None if subject is None else subject.casefold(),
    )


def _test(
    predicate: FilterPredicate, record: FilterInput, folded: _Folded
) -> bool | None:
    """Return the test result, or ``None`` when the field is missing."""
    value = predicate.value
    match predicate.field:
        case FilterField.SENDER_DOMAIN:
            if folded.sender_domain is None:
                return None
            return folded.sender_domain == value.casefold()
        case FilterField.FOLDER_ID:
            if record.folder_id is None:
                return None
            return record.folder_id == value
        case FilterField.LABEL:
            if folded.labels is None:
                return None
            return value.casefold() in folded.labels
        case FilterField.SUBJECT_PREFIX:
            if folded.subject is None:
                return None
            return folded.subject.startswith(value.casefold())


def _evaluate_rule(
    rule: FilterRule, record: FilterInput, folded: _Folded
) -> RuleEvaluation:
    result = _test(rule.predicate, record, folded)
    if result is None:
        outcome, effect = "unknown", None
    elif result:
        outcome, effect = "matched", rule.effect
    else:
        outcome, effect = "not_matched", None
    return RuleEvaluation(
        rule_id=rule.rule_id,
        rule_version=rule.rule_version,
        outcome=outcome,
        effect=effect,
    )


def _verdict(
    evals: tuple[RuleEvaluation, ...],
) -> tuple[FilterVerdict, tuple[Reason, ...]]:
    """Return the verdict and reasons in the order the contract expects."""
    inc = tuple(e.rule_id for e in evals if e.effect == "include")
    exc = tuple(e.rule_id for e in evals if e.effect == "exclude")
    unk = tuple(e.rule_id for e in evals if e.outcome == "unknown")
    reasons: list[Reason] = []
    if inc and exc:
        reasons.append(Reason(code="conflict", rule_ids=(*inc, *exc)))
    if exc:
        reasons.append(Reason(code="excluded", rule_ids=exc))
    if unk:
        reasons.append(Reason(code="unknown_rule", rule_ids=unk))
    if inc and exc:
        return FilterVerdict.CONFLICT, tuple(reasons)
    if exc:
        return FilterVerdict.EXCLUDE, tuple(reasons)
    if unk or not inc:
        return FilterVerdict.UNKNOWN, tuple(reasons)
    return FilterVerdict.INCLUDE, tuple(reasons)


class FilterEvaluation(ResultPart):
    """
    The outcome of one rule-set evaluation.

    ``evaluations`` has one item for every rule, sorted by rule ID.
    ``matched`` lists every matching rule ID. ``rule_set_version`` is the
    version that was evaluated.
    """

    rule_set_version: Text
    evaluations: tuple[RuleEvaluation, ...]
    matched: tuple[Text, ...]
    verdict: FilterVerdict
    reasons: tuple[Reason, ...] = ()
    status: Accepted
    limitations: tuple[Limitation, ...] = ()

    @model_validator(mode="after")
    def _closed(self) -> FilterEvaluation:
        sorted_unique([e.rule_id for e in self.evaluations], "rule")
        check_limitations(self.status, self.limitations)
        if self.verdict is FilterVerdict.UNKNOWN and (
            self.status is COMPLETE or not self.limitations
        ):
            raise A2ContractError("unknown verdict needs a limitation")
        return self


def _limitations(
    evals: tuple[RuleEvaluation, ...],
    rules: tuple[FilterRule, ...],
    verdict: FilterVerdict,
) -> tuple[Limitation, ...]:
    unknown_ids = {e.rule_id for e in evals if e.outcome == "unknown"}
    fields = {r.predicate.field.value for r in rules if r.rule_id in unknown_ids}
    found = {Limitation(FilterLimitationCode.MISSING_FIELD.value, f) for f in fields}
    if verdict is FilterVerdict.UNKNOWN and not unknown_ids:
        found.add(
            Limitation(FilterLimitationCode.NO_RULE_MATCHED.value, NO_MATCH_DETAIL)
        )
    return tuple(sorted(found, key=lambda item: (item.code, item.detail)))


def evaluate_filters(rule_set: RuleSet, record: FilterInput) -> FilterEvaluation:
    """
    Evaluate every rule of ``rule_set`` against ``record``.

    Raise :exc:`DuplicateRuleIdError` when two rules share a rule ID. The
    result does not depend on the order of ``rule_set.rules``.
    """
    ids = [rule.rule_id for rule in rule_set.rules]
    if len(set(ids)) != len(ids):
        raise DuplicateRuleIdError("duplicate rule id in rule set")
    rules = tuple(sorted(rule_set.rules, key=lambda rule: rule.rule_id))
    folded = _fold(record)
    evals = tuple(_evaluate_rule(rule, record, folded) for rule in rules)
    verdict, reasons = _verdict(evals)
    limitations = _limitations(evals, rules, verdict)
    return FilterEvaluation(
        rule_set_version=rule_set.rule_set_version,
        evaluations=evals,
        matched=tuple(e.rule_id for e in evals if e.effect),
        verdict=verdict,
        reasons=reasons,
        status=TerminalStatus.INCOMPLETE if limitations else TerminalStatus.COMPLETE,
        limitations=limitations,
    )
