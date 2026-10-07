"""Metrics with explicit denominators for Topic 01 synthetic validation."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable, Sequence

from .alignment import Resolution
from .models import BenchmarkCase, QuoteGold, Span


@dataclass(frozen=True)
class FractionMetric:
    numerator: int
    denominator: int

    @property
    def value(self) -> float | None:
        return self.numerator / self.denominator if self.denominator else None

    def to_dict(self) -> dict[str, int | float | None]:
        return {"numerator": self.numerator, "denominator": self.denominator, "value": self.value}


@dataclass(frozen=True)
class DetectionResult:
    precision: FractionMetric
    recall: FractionMetric
    matched_pairs: tuple[tuple[int, int], ...]


def match_spans(
    gold: Sequence[Span], predicted: Sequence[Span], *, min_iou: float = 0.50
) -> DetectionResult:
    pairs: list[tuple[float, int, int]] = []
    for gi, g in enumerate(gold):
        for pi, p in enumerate(predicted):
            iou = g.iou(p)
            if iou >= min_iou:
                pairs.append((iou, gi, pi))
    pairs.sort(reverse=True)
    used_g: set[int] = set()
    used_p: set[int] = set()
    chosen: list[tuple[int, int]] = []
    for _, gi, pi in pairs:
        if gi in used_g or pi in used_p:
            continue
        used_g.add(gi)
        used_p.add(pi)
        chosen.append((gi, pi))
    return DetectionResult(
        precision=FractionMetric(len(chosen), len(predicted)),
        recall=FractionMetric(len(chosen), len(gold)),
        matched_pairs=tuple(sorted(chosen)),
    )


def preservation_metric(cases: Iterable[BenchmarkCase], extracted: dict[tuple[str, str], str], *, kinds: set[str]) -> FractionMetric:
    total = 0
    preserved = 0
    for case in cases:
        for labeled in case.spans:
            if labeled.kind not in kinds:
                continue
            total += 1
            text = extracted[(case.case_id, labeled.message_id)]
            if labeled.text in text:
                preserved += 1
    return FractionMetric(preserved, total)


def source_resolution_metrics(
    observations: Iterable[tuple[QuoteGold, Resolution, set[str]]]
) -> dict[str, FractionMetric]:
    """Evaluate unique acceptance and candidate-set recall.

    available_source_ids is the set of sources actually present for that decision.
    If gold has multiple valid sources, accepting exactly one is an error even if
    that source is in the gold set: unique provenance is unsupported.
    """
    eligible = accepted = incorrect_accepted = correct_unique = 0
    candidate_gold_available = candidate_gold_recovered = 0
    ambiguous_gold = ambiguous_abstained = 0
    missing_gold = missing_abstained = 0
    for gold, resolution, available_source_ids in observations:
        eligible += 1
        gold_ids = {x.message_id for x in gold.source_candidates}
        available_gold = gold_ids & available_source_ids
        predicted_ids = {x.source_message_id for x in resolution.candidates}
        candidate_gold_available += len(available_gold)
        candidate_gold_recovered += len(available_gold & predicted_ids)

        if gold.source_missing or not available_gold:
            missing_gold += 1
            if resolution.abstained:
                missing_abstained += 1
        elif len(gold_ids) > 1:
            ambiguous_gold += 1
            if resolution.abstained:
                ambiguous_abstained += 1

        if not resolution.abstained:
            accepted += 1
            if len(gold_ids) == 1 and resolution.accepted_source_id in gold_ids:
                correct_unique += 1
            else:
                incorrect_accepted += 1

    return {
        "coverage": FractionMetric(accepted, eligible),
        "accepted_unique_accuracy": FractionMetric(correct_unique, accepted),
        "accepted_unique_error": FractionMetric(incorrect_accepted, accepted),
        "candidate_recall": FractionMetric(candidate_gold_recovered, candidate_gold_available),
        "ambiguous_abstention": FractionMetric(ambiguous_abstained, ambiguous_gold),
        "missing_source_abstention": FractionMetric(missing_abstained, missing_gold),
    }


def reliability_bins(outcomes: Iterable[tuple[float, bool]], *, bins: int = 5) -> list[dict[str, float | int | None]]:
    buckets: list[list[tuple[float, bool]]] = [[] for _ in range(bins)]
    for confidence, correct in outcomes:
        idx = min(bins - 1, max(0, int(confidence * bins)))
        buckets[idx].append((confidence, correct))
    result: list[dict[str, float | int | None]] = []
    for i, bucket in enumerate(buckets):
        if bucket:
            mean_conf = sum(c for c, _ in bucket) / len(bucket)
            accuracy = sum(1 for _, ok in bucket if ok) / len(bucket)
        else:
            mean_conf = accuracy = None
        result.append({
            "bin": i,
            "lower": i / bins,
            "upper": (i + 1) / bins,
            "count": len(bucket),
            "mean_confidence": mean_conf,
            "observed_accuracy": accuracy,
        })
    return result


def expected_calibration_error(outcomes: Iterable[tuple[float, bool]], *, bins: int = 5) -> float | None:
    values = list(outcomes)
    if not values:
        return None
    rb = reliability_bins(values, bins=bins)
    total = len(values)
    return sum(
        row["count"] / total * abs(float(row["mean_confidence"]) - float(row["observed_accuracy"]))
        for row in rb
        if row["count"]
    )
