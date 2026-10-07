"""Synthetic uncertainty/calibration plumbing for E4.

This is not a claim of production calibration. Calibration and held-out test
sets use different authored template families and deterministic content keys so
no exact example is shared across splits.
"""
from __future__ import annotations

from dataclasses import dataclass
import random

from .alignment import candidate_matches, resolve_candidates, Resolution


@dataclass(frozen=True)
class UncertaintyExample:
    example_id: str
    family: str
    template_family: str
    quote: str
    sources: dict[str, str]
    gold_sources: frozenset[str]
    source_available: bool = True

    @property
    def unique_gold(self) -> bool:
        return self.source_available and len(self.gold_sources) == 1

    @property
    def content_key(self) -> tuple:
        return (
            self.quote,
            tuple(sorted(self.sources.items())),
            tuple(sorted(self.gold_sources)),
            self.source_available,
        )


@dataclass(frozen=True)
class EvaluatedExample:
    example: UncertaintyExample
    resolution: Resolution

    @property
    def accepted_correct(self) -> bool:
        return (
            not self.resolution.abstained
            and self.example.unique_gold
            and self.resolution.accepted_source_id in self.example.gold_sources
        )


def generate_examples(
    *, seed: int, count_per_family: int = 30, variant: str = "calibration"
) -> tuple[UncertaintyExample, ...]:
    if variant not in {"calibration", "holdout"}:
        raise ValueError(f"unknown template variant: {variant}")
    rng = random.Random(seed)
    examples: list[UncertaintyExample] = []
    prefix = "CAL" if variant == "calibration" else "HOLD"

    for i in range(count_per_family):
        token = rng.randint(1000, 9999)
        key = f"{prefix}-{seed}-{i}-{token}"
        source_qty = 100 + i * 3 + rng.randint(0, 2)
        quote_qty = source_qty + 1

        if variant == "calibration":
            exact_quote = f"Approve item {key} before Friday."
            exact_sources = {
                "target": f"Context. {exact_quote} End.",
                "distractor": f"Reject item {key}-other next week.",
            }
            edited_quote = f"Ship order {key}: {quote_qty} units Monday."
            edited_sources = {
                "target": f"Ship order {key}: {source_qty} units Monday.",
                "distractor": f"Cancel order {key} entirely.",
            }
            ambiguous_quote = f"Please review request {key}."
            ambiguous_sources = {
                "source_a": ambiguous_quote + " Alpha decision.",
                "source_b": ambiguous_quote + " Beta decision.",
            }
            near_quote = f"Limit for request {key} is AUD {token + 1}."
            near_sources = {
                "source_a": f"Limit for request {key} is AUD {token}.",
                "source_b": f"Limit for request {key} is AUD {token + 2}.",
            }
            missing_quote = f"Escalate case {key} now."
            missing_sources = {"distractor": f"Escalate case {key}-other tomorrow."}
            template_names = {
                "exact": "cal-approval-deadline",
                "edited": "cal-shipment-quantity",
                "ambiguous": "cal-review-boilerplate",
                "near": "cal-limit-near-collision",
                "missing": "cal-escalation-missing",
            }
        else:
            exact_quote = f"Friday deadline: record {key} has final approval."
            exact_sources = {
                "target": f"Notice: {exact_quote} Archive this decision.",
                "distractor": f"Monday deadline: record {key}-other remains pending.",
            }
            edited_quote = f"Tuesday dispatch for batch {key}: quantity {quote_qty}."
            edited_sources = {
                "target": f"Tuesday dispatch for batch {key}: quantity {source_qty}.",
                "distractor": f"Batch {key} is cancelled and will not dispatch.",
            }
            ambiguous_quote = f"Status update for ticket {key}."
            ambiguous_sources = {
                "source_a": ambiguous_quote + " Path A context.",
                "source_b": ambiguous_quote + " Path B context.",
            }
            near_quote = f"Budget ceiling for case {key}: AUD {token + 1}."
            near_sources = {
                "source_a": f"Budget ceiling for case {key}: AUD {token}.",
                "source_b": f"Budget ceiling for case {key}: AUD {token + 2}.",
            }
            missing_quote = f"Immediate follow-up required for incident {key}."
            missing_sources = {"distractor": f"Routine follow-up for incident {key}-other next month."}
            template_names = {
                "exact": "holdout-final-approval",
                "edited": "holdout-dispatch-quantity",
                "ambiguous": "holdout-status-boilerplate",
                "near": "holdout-budget-near-collision",
                "missing": "holdout-incident-missing",
            }

        examples.extend(
            [
                UncertaintyExample(
                    f"{prefix.lower()}-exact-{i}", "exact_unique", template_names["exact"],
                    exact_quote, exact_sources, frozenset({"target"}),
                ),
                UncertaintyExample(
                    f"{prefix.lower()}-edited-{i}", "edited_unique", template_names["edited"],
                    edited_quote, edited_sources, frozenset({"target"}),
                ),
                UncertaintyExample(
                    f"{prefix.lower()}-ambiguous-{i}", "ambiguous_exact", template_names["ambiguous"],
                    ambiguous_quote, ambiguous_sources, frozenset({"source_a", "source_b"}),
                ),
                UncertaintyExample(
                    f"{prefix.lower()}-near-{i}", "near_collision", template_names["near"],
                    near_quote, near_sources, frozenset({"source_a", "source_b"}),
                ),
                UncertaintyExample(
                    f"{prefix.lower()}-missing-{i}", "missing_source", template_names["missing"],
                    missing_quote, missing_sources, frozenset({"missing_target"}), source_available=False,
                ),
            ]
        )
    return tuple(examples)


def evaluate_example(example: UncertaintyExample, *, threshold: float, margin: float = 0.08) -> EvaluatedExample:
    matches = candidate_matches(example.quote, example.sources, plain_markers=False, min_score=0.50)
    resolution = resolve_candidates(matches, accept_threshold=threshold, ambiguity_margin=margin)
    return EvaluatedExample(example, resolution)


def choose_threshold(
    calibration: tuple[UncertaintyExample, ...],
    *,
    max_accepted_error: float = 0.05,
    candidates: tuple[float, ...] = (0.60, 0.65, 0.70, 0.75, 0.80, 0.82, 0.85, 0.88, 0.90, 0.92, 0.95),
) -> tuple[float, list[dict[str, float | int]]]:
    rows: list[dict[str, float | int]] = []
    best = candidates[-1]
    best_coverage = -1.0
    for threshold in candidates:
        evaluated = [evaluate_example(x, threshold=threshold) for x in calibration]
        accepted = [x for x in evaluated if not x.resolution.abstained]
        wrong = [x for x in accepted if not x.accepted_correct]
        error = len(wrong) / len(accepted) if accepted else 0.0
        coverage = len(accepted) / len(evaluated) if evaluated else 0.0
        rows.append({"threshold": threshold, "accepted": len(accepted), "wrong": len(wrong), "accepted_error": error, "coverage": coverage})
        if error <= max_accepted_error and coverage > best_coverage:
            best = threshold
            best_coverage = coverage
    return best, rows
