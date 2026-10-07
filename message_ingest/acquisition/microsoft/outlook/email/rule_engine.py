"""Pure ordered deterministic Outlook Mail acquisition RuleEngine."""

from __future__ import annotations

from dataclasses import dataclass, fields, replace

from .profile import DISCOVERY_V1, FULL_V1
from .rule_config import (
    MAIL_RULE_POLICY_FAMILY,
    MailRuleDefinition,
    MailRulePolicy,
    effective_mail_policy_digest,
    internal_mail_profile,
)
from .rule_evaluation import (
    MailRuleDecisionOutcome,
    MailRuleEvaluation,
    MailRuleEvaluationState,
    MailRuleFact,
    MailRuleFacts,
    MailRuleObservation,
    MailRuleProbeData,
    MailRuleRequiredData,
)
from .rule_predicates import (
    MailPredicateResult,
    MailTruth,
    evaluate_predicate_block,
)
from .rule_regex import MailRegexEngine


@dataclass(frozen=True, slots=True)
class _Terminal:
    selected_profile: str
    matched_rule_ids: tuple[str, ...]
    stop_rule_id: str | None = None


@dataclass(frozen=True, slots=True)
class _Pending:
    required_data: frozenset[MailRuleRequiredData]
    reason_codes: tuple[str, ...]


class DeterministicMailRuleEvaluator:
    """Evaluate one enabled immutable Mail policy without framework dependencies."""

    def __init__(
        self,
        policy: MailRulePolicy,
        *,
        regex_engine: MailRegexEngine | None = None,
    ) -> None:
        if not policy.enabled:
            raise ValueError("disabled Mail policy does not construct an evaluator")
        self.policy = policy
        self.regex_engine = regex_engine or MailRegexEngine()
        self.ruleset_id = MAIL_RULE_POLICY_FAMILY
        self.ruleset_digest = effective_mail_policy_digest(policy)
        self._rules = tuple(
            sorted(
                (rule for rule in policy.rules if rule.enabled),
                key=lambda rule: rule.sequence,
            )
        )
        self._default_profile = internal_mail_profile(policy.default_profile)

    def evaluate(
        self,
        observation: MailRuleObservation,
        *,
        probe: MailRuleProbeData | None = None,
    ) -> MailRuleEvaluation:
        """Return one terminal, one-probe request, or fail-safe result."""

        if self._default_profile == FULL_V1:
            return self._final(
                _Terminal(FULL_V1, ()),
                outcome=MailRuleDecisionOutcome.DEFAULT,
                probe_used=False,
            )

        if probe is None:
            result = self._evaluate_rules(observation.facts)
            return self._initial_result(observation, result)

        version_failure = self._probe_version_failure(observation.facts, probe.facts)
        if version_failure is not None:
            return self._unresolved(version_failure, probe_used=True)

        result = self._evaluate_rules(_merge_facts(observation.facts, probe.facts))
        if isinstance(result, _Terminal):
            return self._final(
                result,
                outcome=_outcome(result),
                probe_used=True,
            )
        reason = (
            result.reason_codes[0] if result.reason_codes else "probe_fact_unavailable"
        )
        return self._unresolved(reason, probe_used=True)

    def _initial_result(
        self,
        observation: MailRuleObservation,
        result: _Terminal | _Pending,
    ) -> MailRuleEvaluation:
        if isinstance(result, _Terminal):
            return self._final(result, outcome=_outcome(result), probe_used=False)

        if result.required_data:
            if not _trustworthy_change_key(observation.facts):
                return self._unresolved(
                    "initial_version_unavailable",
                    probe_used=False,
                )
            return MailRuleEvaluation(
                state=MailRuleEvaluationState.NEEDS_DATA,
                required_data=result.required_data,
                ruleset_id=self.ruleset_id,
                ruleset_digest=self.ruleset_digest,
            )

        reason = (
            result.reason_codes[0] if result.reason_codes else "evaluation_unresolved"
        )
        return self._unresolved(reason, probe_used=False)

    def _evaluate_rules(self, facts: MailRuleFacts) -> _Terminal | _Pending:
        selected = self._default_profile
        matched: list[str] = []
        pending_required: set[MailRuleRequiredData] = set()
        pending_reasons: list[str] = []
        unresolved_stop = False

        for rule in self._rules:
            truth = self._evaluate_rule(rule, facts)
            if truth.truth is MailTruth.FALSE:
                continue

            if truth.truth is MailTruth.UNKNOWN:
                target = internal_mail_profile(rule.profile)
                relevant = rule.stop_processing or (
                    selected != FULL_V1 and target == FULL_V1
                )
                if relevant:
                    pending_required.update(truth.required_data)
                    pending_reasons.extend(truth.reason_codes)
                if rule.stop_processing:
                    unresolved_stop = True
                continue

            matched.append(rule.id)
            selected = _stronger_profile(
                selected,
                internal_mail_profile(rule.profile),
            )
            if selected == FULL_V1:
                if unresolved_stop:
                    return _pending(pending_required, pending_reasons)
                return _Terminal(
                    selected_profile=FULL_V1,
                    matched_rule_ids=tuple(matched),
                    stop_rule_id=rule.id if rule.stop_processing else None,
                )

            if rule.stop_processing:
                if pending_required or pending_reasons:
                    return _pending(pending_required, pending_reasons)
                return _Terminal(
                    selected_profile=selected,
                    matched_rule_ids=tuple(matched),
                    stop_rule_id=rule.id,
                )

        if pending_required or pending_reasons:
            return _pending(pending_required, pending_reasons)
        return _Terminal(
            selected_profile=selected,
            matched_rule_ids=tuple(matched),
        )

    def _evaluate_rule(
        self,
        rule: MailRuleDefinition,
        facts: MailRuleFacts,
    ) -> MailPredicateResult:
        conditions = evaluate_predicate_block(
            rule.conditions,
            facts,
            regex_engine=self.regex_engine,
        )
        if conditions.truth is MailTruth.FALSE:
            return conditions
        if not rule.exceptions:
            return conditions

        unknown_exceptions: list[MailPredicateResult] = []
        for block in rule.exceptions:
            exception = evaluate_predicate_block(
                block,
                facts,
                regex_engine=self.regex_engine,
            )
            if exception.truth is MailTruth.TRUE:
                return MailPredicateResult(MailTruth.FALSE)
            if exception.truth is MailTruth.UNKNOWN:
                unknown_exceptions.append(exception)

        if conditions.truth is MailTruth.TRUE and not unknown_exceptions:
            return MailPredicateResult(MailTruth.TRUE)
        unknowns = (
            [conditions] if conditions.truth is MailTruth.UNKNOWN else []
        ) + unknown_exceptions
        return _unknown_union(unknowns)

    def _probe_version_failure(
        self,
        initial: MailRuleFacts,
        probed: MailRuleFacts,
    ) -> str | None:
        if not _trustworthy_change_key(initial):
            return "initial_version_unavailable"
        if not _trustworthy_change_key(probed):
            return "probe_version_unavailable"
        if initial.change_key != probed.change_key:
            return "source_changed_during_evaluation"
        return None

    def _final(
        self,
        terminal: _Terminal,
        *,
        outcome: MailRuleDecisionOutcome,
        probe_used: bool,
    ) -> MailRuleEvaluation:
        return MailRuleEvaluation(
            state=MailRuleEvaluationState.FINAL,
            selected_profile=terminal.selected_profile,
            outcome=outcome,
            ruleset_id=self.ruleset_id,
            ruleset_digest=self.ruleset_digest,
            matched_rule_ids=terminal.matched_rule_ids,
            stop_rule_id=terminal.stop_rule_id,
            probe_used=probe_used,
        )

    def _unresolved(self, reason: str, *, probe_used: bool) -> MailRuleEvaluation:
        return MailRuleEvaluation(
            state=MailRuleEvaluationState.UNRESOLVED,
            selected_profile=FULL_V1,
            outcome=MailRuleDecisionOutcome.UNRESOLVED,
            ruleset_id=self.ruleset_id,
            ruleset_digest=self.ruleset_digest,
            probe_used=probe_used,
            fallback_used=True,
            reason_code=reason,
        )


def _outcome(terminal: _Terminal) -> MailRuleDecisionOutcome:
    return (
        MailRuleDecisionOutcome.MATCHED
        if terminal.matched_rule_ids
        else MailRuleDecisionOutcome.DEFAULT
    )


def _stronger_profile(current: str, candidate: str) -> str:
    if current == FULL_V1 or candidate == FULL_V1:
        return FULL_V1
    return DISCOVERY_V1


def _pending(
    required_data: set[MailRuleRequiredData],
    reasons: list[str],
) -> _Pending:
    return _Pending(
        required_data=frozenset(required_data),
        reason_codes=tuple(dict.fromkeys(reasons)),
    )


def _unknown_union(results: list[MailPredicateResult]) -> MailPredicateResult:
    return MailPredicateResult(
        MailTruth.UNKNOWN,
        required_data=frozenset().union(*(result.required_data for result in results)),
        reason_codes=tuple(
            dict.fromkeys(
                reason for result in results for reason in result.reason_codes
            )
        ),
    )


def _trustworthy_change_key(facts: MailRuleFacts) -> bool:
    return (
        MailRuleFact.CHANGE_KEY in facts.available_facts
        and isinstance(facts.change_key, str)
        and bool(facts.change_key)
    )


_FACT_ATTRS = frozenset(fact.value for fact in MailRuleFact)


def _merge_facts(initial: MailRuleFacts, probed: MailRuleFacts) -> MailRuleFacts:
    updates: dict[str, object] = {}
    for fact in probed.available_facts:
        name = fact.value
        if name in _FACT_ATTRS:
            updates[name] = getattr(probed, name)
    updates["available_facts"] = initial.available_facts | probed.available_facts
    allowed = {field.name for field in fields(MailRuleFacts)}
    if not set(updates).issubset(allowed):
        raise ValueError("Mail probe contained an unknown fact")
    return replace(initial, **updates)
