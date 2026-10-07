"""Run reproducible E1-E4 synthetic engineering experiments."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
from typing import Any

from .alignment import Resolution, candidate_matches, resolve_candidates
from .detection import reuse_augmented_spans
from .extraction import extract_body
from .fixtures import canonical_cases, write_fixture_corpus
from .metrics import (
    FractionMetric,
    expected_calibration_error,
    match_spans,
    preservation_metric,
    reliability_bins,
    source_resolution_metrics,
)
from .models import QuoteGold, Span
from .replay import replay, replay_metrics
from .uncertainty import choose_threshold, evaluate_example, generate_examples


def _fraction(n: int, d: int) -> dict[str, int | float | None]:
    return FractionMetric(n, d).to_dict()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _detected_quote_for_gold(gold: QuoteGold, predicted: tuple[Span, ...]) -> Span | None:
    ranked = sorted(((gold.occurrence_span.iou(p), p) for p in predicted), reverse=True)
    return ranked[0][1] if ranked and ranked[0][0] >= 0.50 else None


def run_e1(root: Path) -> dict[str, Any]:
    cases = canonical_cases()
    write_fixture_corpus(root / "fixtures")
    messages = sum(len(c.messages) for c in cases)
    quotes = [q for c in cases for q in c.quotes]
    relations = [r for c in cases for r in c.relations]
    spans = [s for c in cases for s in c.spans]
    source_links = sum(len(q.source_candidates) for q in quotes)
    return {
        "status": "EXPERIMENT_EXECUTION_COMPLETE_SYNTHETIC",
        "schema_version": "topic01-engineering-v1",
        "case_count": len(cases),
        "message_count": messages,
        "families": sorted({c.family for c in cases}),
        "quote_occurrence_count": len(quotes),
        "quote_source_link_count": source_links,
        "ambiguous_quote_occurrences": sum(1 for q in quotes if q.ambiguous),
        "missing_source_quote_occurrences": sum(1 for q in quotes if q.source_missing),
        "relation_gold_count": len(relations),
        "labeled_span_count": len(spans),
        "decision_or_condition_span_count": sum(1 for s in spans if s.kind in {"decision_bearing", "condition"}),
        "replay_order_count": sum(len(c.replay_orders) for c in cases),
        "fixture_manifest_sha256": _sha(root / "fixtures" / "MANIFEST.json"),
        "claim_boundary": "Executable deterministic benchmark contract established; production representativeness is NOT established.",
    }


def run_e2() -> dict[str, Any]:
    cases = canonical_cases()
    extracted: dict[tuple[str, str], str] = {}
    extraction_exact = 0
    extraction_total = 0
    for case in cases:
        for message in case.messages:
            body = extract_body(message.raw_rfc822)
            extracted[(case.case_id, message.message_id)] = body.text
            extraction_total += 1
            extraction_exact += int(body.text == message.expected_text)

    def prior_messages(case, message):
        return tuple(m for m in case.messages if m.message_id != message.message_id and m.arrival_rank < message.arrival_rank)

    def predicted_spans(case, message, mode: str) -> tuple[Span, ...]:
        body = extract_body(message.raw_rfc822)
        if mode == "structural":
            return body.quote_spans
        if mode == "reuse_augmented":
            source_texts = tuple(extracted[(case.case_id, m.message_id)] for m in prior_messages(case, message))
            return reuse_augmented_spans(body.text, body.quote_spans, source_texts)
        raise ValueError(mode)

    def detection_metrics(mode: str) -> dict[str, Any]:
        tp = pred_total = gold_total = 0
        by_family: dict[str, dict[str, int]] = {}
        misses: list[dict[str, str]] = []
        false_positive_messages: list[dict[str, str | int]] = []
        for case in cases:
            for message in case.messages:
                gold_quotes = tuple(q for q in case.quotes if q.message_id == message.message_id)
                gold_spans = tuple(q.occurrence_span for q in gold_quotes)
                pred = predicted_spans(case, message, mode)
                result = match_spans(gold_spans, pred, min_iou=0.50)
                tp += result.recall.numerator
                pred_total += len(pred)
                gold_total += len(gold_spans)
                fam = by_family.setdefault(case.family, {"tp": 0, "pred": 0, "gold": 0})
                fam["tp"] += result.recall.numerator
                fam["pred"] += len(pred)
                fam["gold"] += len(gold_spans)
                matched_gold = {g for g, _ in result.matched_pairs}
                for gi, quote in enumerate(gold_quotes):
                    if gi not in matched_gold:
                        misses.append({
                            "case_id": case.case_id,
                            "message_id": message.message_id,
                            "occurrence_id": quote.occurrence_id,
                            "marker_style": quote.marker_style,
                        })
                if len(pred) > result.precision.numerator:
                    false_positive_messages.append({
                        "case_id": case.case_id,
                        "message_id": message.message_id,
                        "predicted": len(pred),
                        "matched": result.precision.numerator,
                    })
        return {
            "precision": _fraction(tp, pred_total),
            "recall": _fraction(tp, gold_total),
            "by_family": {
                fam: {"precision": _fraction(v["tp"], v["pred"]), "recall": _fraction(v["tp"], v["gold"])}
                for fam, v in sorted(by_family.items())
            },
            "missed_gold_occurrences": misses,
            "false_positive_messages": false_positive_messages,
        }

    def arrival_time_end_to_end(mode: str) -> dict[str, Any]:
        predicted_total = matched_predictions = unmatched_predictions = missed_gold = 0
        accepted = correct_accepted = false_accepted = 0
        available_gold_links = recovered_gold_links = 0
        eligible_unique_gold = correct_unique_gold = 0
        ambiguous_gold = false_unique_on_ambiguous = 0
        unavailable_gold = false_accept_on_unavailable = 0
        prediction_rows: list[dict[str, Any]] = []

        for case in cases:
            for message in case.messages:
                body = extract_body(message.raw_rfc822)
                predictions = predicted_spans(case, message, mode)
                gold_quotes = tuple(q for q in case.quotes if q.message_id == message.message_id)
                gold_spans = tuple(q.occurrence_span for q in gold_quotes)
                matching = match_spans(gold_spans, predictions, min_iou=0.50)
                pred_to_gold = {pi: gi for gi, pi in matching.matched_pairs}
                matched_predictions += len(pred_to_gold)
                predicted_total += len(predictions)
                unmatched_predictions += len(predictions) - len(pred_to_gold)
                missed_gold += len(gold_quotes) - len({gi for gi, _ in matching.matched_pairs})

                prior = prior_messages(case, message)
                available_ids = {m.message_id for m in prior}
                source_texts = {m.message_id: extracted[(case.case_id, m.message_id)] for m in prior}

                # Gold link denominator is defined at arrival time, independent of detector success.
                for gold in gold_quotes:
                    available_gold = {x.message_id for x in gold.source_candidates} & available_ids
                    available_gold_links += len(available_gold)
                    if gold.ambiguous and available_gold:
                        ambiguous_gold += 1
                    if not available_gold:
                        unavailable_gold += 1
                    if not gold.ambiguous and len(gold.source_candidates) == 1 and len(available_gold) == 1:
                        eligible_unique_gold += 1

                for pi, span in enumerate(predictions):
                    detected_text = span.extract(body.text)
                    # Marker handling is derived from the prediction itself, not gold metadata.
                    plain_markers = body.content_type == "text/plain" and detected_text.lstrip().startswith(">")
                    matches = candidate_matches(detected_text, source_texts, plain_markers=plain_markers, min_score=0.50)
                    resolution = resolve_candidates(matches)
                    gi = pred_to_gold.get(pi)
                    gold = gold_quotes[gi] if gi is not None else None
                    predicted_candidate_ids = {x.source_message_id for x in resolution.candidates}
                    available_gold = (
                        {x.message_id for x in gold.source_candidates} & available_ids if gold is not None else set()
                    )
                    recovered_gold_links += len(available_gold & predicted_candidate_ids)

                    is_correct_accept = False
                    error_kind = ""
                    if not resolution.abstained:
                        accepted += 1
                        if gold is None:
                            error_kind = "unmatched_predicted_occurrence"
                        elif gold.source_missing or not available_gold:
                            error_kind = "source_unavailable_at_arrival"
                            false_accept_on_unavailable += 1
                        elif gold.ambiguous:
                            error_kind = "ambiguous_gold_forced_unique"
                            false_unique_on_ambiguous += 1
                        elif len(gold.source_candidates) == 1 and resolution.accepted_source_id in available_gold:
                            is_correct_accept = True
                            correct_accepted += 1
                            correct_unique_gold += 1
                        else:
                            error_kind = "wrong_source"
                        if not is_correct_accept:
                            false_accepted += 1

                    prediction_rows.append({
                        "case_id": case.case_id,
                        "message_id": message.message_id,
                        "prediction_span": span.to_dict(),
                        "matched_gold_occurrence_id": gold.occurrence_id if gold else None,
                        "accepted_source_id": resolution.accepted_source_id,
                        "abstained": resolution.abstained,
                        "reason": resolution.reason,
                        "accepted_correct": is_correct_accept,
                        "error_kind": error_kind,
                        "candidate_ids": [x.source_message_id for x in resolution.candidates],
                        "available_source_ids": sorted(available_ids),
                    })

        return {
            "predicted_occurrences": predicted_total,
            "matched_predicted_occurrences": matched_predictions,
            "unmatched_predicted_occurrences": unmatched_predictions,
            "missed_gold_occurrences": missed_gold,
            "accepted_attributions": accepted,
            "correct_accepted_attributions": correct_accepted,
            "false_accepted_attributions": false_accepted,
            "accepted_attribution_error": _fraction(false_accepted, accepted),
            "candidate_recall_at_arrival": _fraction(recovered_gold_links, available_gold_links),
            "unique_resolution_recall_at_arrival": _fraction(correct_unique_gold, eligible_unique_gold),
            "ambiguous_gold_occurrences_with_available_source": ambiguous_gold,
            "false_unique_acceptances_on_ambiguous_gold": false_unique_on_ambiguous,
            "gold_occurrences_with_no_source_available_at_arrival": unavailable_gold,
            "false_acceptances_when_source_unavailable": false_accept_on_unavailable,
            "prediction_results": prediction_rows,
        }

    structural_detection = detection_metrics("structural")
    augmented_detection = detection_metrics("reuse_augmented")

    # Gold-conditioned, final-context capability diagnostic. This is deliberately
    # NOT called end-to-end and may use sources that arrived after the quote.
    conditional_observations = []
    source_span_ious: list[float] = []
    exact_source_boundaries = 0
    source_span_denominator = 0
    quote_text_preserved = quote_text_total = 0
    conditional_rows: list[dict[str, Any]] = []
    for case in cases:
        for gold in case.quotes:
            msg = case.message(gold.message_id)
            quote_text = gold.occurrence_span.extract(msg.expected_text)
            quote_text_total += 1
            quote_text_preserved += int(quote_text in extracted[(case.case_id, gold.message_id)])
            available_ids = {m.message_id for m in case.messages if m.message_id != gold.message_id}
            sources = {m.message_id: extracted[(case.case_id, m.message_id)] for m in case.messages if m.message_id != gold.message_id}
            plain = gold.marker_style == "plain_gt"
            matches = candidate_matches(quote_text, sources, plain_markers=plain, min_score=0.50)
            resolution = resolve_candidates(matches)
            conditional_observations.append((gold, resolution, available_ids))
            by_source = {m.source_message_id: m for m in matches}
            for source in gold.source_candidates:
                source_span_denominator += 1
                candidate = by_source.get(source.message_id)
                if candidate is None:
                    source_span_ious.append(0.0)
                    continue
                iou = candidate.source_span.iou(source.span)
                source_span_ious.append(iou)
                exact_source_boundaries += int(candidate.source_span == source.span)
            conditional_rows.append({
                "case_id": case.case_id,
                "occurrence_id": gold.occurrence_id,
                "source_semantics": gold.source_semantics,
                "marker_style": gold.marker_style,
                "accepted_source_id": resolution.accepted_source_id,
                "abstained": resolution.abstained,
                "reason": resolution.reason,
                "candidate_ids": [x.source_message_id for x in resolution.candidates],
            })

    structural_e2e = arrival_time_end_to_end("structural")
    augmented_e2e = arrival_time_end_to_end("reuse_augmented")
    return {
        "status": "EXPERIMENT_EXECUTION_COMPLETE_SYNTHETIC",
        "extraction_exact_body_match": _fraction(extraction_exact, extraction_total),
        "decision_condition_deadline_preservation": preservation_metric(
            cases, extracted, kinds={"decision_bearing", "condition", "deadline"}
        ).to_dict(),
        "unique_or_new_content_preservation": preservation_metric(cases, extracted, kinds={"unique", "new_content"}).to_dict(),
        "gold_quote_text_preservation": _fraction(quote_text_preserved, quote_text_total),
        "quote_detection": structural_detection,
        "reuse_augmented_quote_detection": augmented_detection,
        "conditional_full_context_source_resolution": {
            k: v.to_dict() for k, v in source_resolution_metrics(conditional_observations).items()
        },
        "conditional_full_context_source_span_exact_boundary": _fraction(exact_source_boundaries, source_span_denominator),
        "conditional_full_context_source_span_mean_iou": (sum(source_span_ious) / len(source_span_ious)) if source_span_ious else None,
        "conditional_full_context_rows": conditional_rows,
        "arrival_time_structural_end_to_end": structural_e2e,
        "arrival_time_reuse_augmented_end_to_end": augmented_e2e,
        "identified_failure_modes": [
            "The structural marker detector misses markerless copied content and forwarded blocks without RFC-style quote markers.",
            "Exact reuse augmentation recovers those two gold classes but produces false positive quote occurrences on repeated text.",
            "If a reply containing quoted text arrives before its historical original, exact reuse can reverse provenance and mark the later-arriving original as reuse of the earlier-observed reply.",
            "Therefore reused text is candidate evidence only; it is not proof that a span is a quotation or that provenance direction follows collection order.",
        ],
        "academic_refresh_decision": "Do not automatically reopen A2 academic Round 3. These are expected limitations of deliberately simple baselines; targeted literature refresh is conditional on later candidate-method selection or persistent failure in stronger candidates.",
        "claim_boundary": "Conditional full-context metrics are capability diagnostics given gold quote occurrences. Arrival-time end-to-end metrics use only prior-arrived sources and score every predicted occurrence, including false positives. All measurements are synthetic only.",
    }

def _final_policy_expected(gold: QuoteGold) -> str:
    if gold.source_missing or len(gold.source_candidates) != 1:
        return "unresolved"
    return "resolved"


def run_e3() -> dict[str, Any]:
    cases = canonical_cases()

    def relation_correct(relation, assessment) -> bool:
        if assessment is None:
            return False
        if relation.ambiguous:
            return (
                assessment.status in {"unresolved", "ambiguous"}
                and set(assessment.targets) == set(relation.target_ids)
            )
        if relation.missing_target_ids and not relation.target_ids:
            expected_missing = {f"MISSING:{x}" for x in relation.missing_target_ids}
            return assessment.status == "missing" and set(assessment.targets) == expected_missing
        return assessment.status == "resolved" and set(assessment.targets) == set(relation.target_ids)

    def evaluate_mode(*, preserve_id_ambiguity: bool) -> dict[str, Any]:
        per_case: dict[str, Any] = {}
        all_results = []

        parent_gold = parent_pred = parent_correct = 0
        ancestry_gold = ancestry_pred = ancestry_correct = 0
        quote_gold = quote_pred = quote_matched = quote_policy_correct = 0
        quote_false_resolved_unmatched = 0

        for case in cases:
            results = [
                replay(case, order, preserve_id_ambiguity=preserve_id_ambiguity)
                for order in case.replay_orders
            ]
            all_results.extend(results)
            metrics = replay_metrics(results)
            per_case[case.case_id] = {"orders": [list(x.order) for x in results], "metrics": metrics}

            for result in results:
                final_assessments = result.snapshots[-1].assessments

                # Reply-parent precision/recall. One predicted parent assessment per message.
                gold_parents = {r.message_id: r for r in case.relations if r.relation_type == "reply_parent"}
                pred_parents = {a.message_id: a for a in final_assessments if a.kind == "reply_parent"}
                parent_gold += len(gold_parents)
                parent_pred += len(pred_parents)
                for mid, relation in gold_parents.items():
                    parent_correct += int(relation_correct(relation, pred_parents.get(mid)))

                # Indirect ancestry is deliberately separate from direct parent.
                gold_ancestry = {r.message_id: r for r in case.relations if r.relation_type == "ancestry"}
                pred_ancestry = {a.message_id: a for a in final_assessments if a.kind == "ancestry"}
                ancestry_gold += len(gold_ancestry)
                ancestry_pred += len(pred_ancestry)
                for mid, relation in gold_ancestry.items():
                    ancestry_correct += int(relation_correct(relation, pred_ancestry.get(mid)))

                # Quote-source is occurrence-specific. Match predicted occurrence spans
                # one-to-one to gold spans within each message before evaluating source policy.
                message_ids = sorted(
                    {q.message_id for q in case.quotes}
                    | {a.message_id for a in final_assessments if a.kind == "quote_source"}
                )
                for message_id in message_ids:
                    gold_quotes = tuple(q for q in case.quotes if q.message_id == message_id)
                    pred_quotes = tuple(
                        a for a in final_assessments
                        if a.kind == "quote_source" and a.message_id == message_id and a.occurrence_span is not None
                    )
                    gold_spans = tuple(q.occurrence_span for q in gold_quotes)
                    pred_spans = tuple(a.occurrence_span for a in pred_quotes if a.occurrence_span is not None)
                    matching = match_spans(gold_spans, pred_spans, min_iou=0.50)
                    quote_gold += len(gold_quotes)
                    quote_pred += len(pred_quotes)
                    quote_matched += len(matching.matched_pairs)
                    matched_pred = {pi for _, pi in matching.matched_pairs}
                    for gi, pi in matching.matched_pairs:
                        gold = gold_quotes[gi]
                        pred = pred_quotes[pi]
                        if gold.source_missing or not gold.source_candidates or gold.ambiguous:
                            correct = pred.status == "unresolved"
                        elif len(gold.source_candidates) == 1:
                            correct = pred.status == "resolved" and pred.targets == (gold.source_candidates[0].message_id,)
                        else:
                            # Joint multi-source occurrences are not used in the current
                            # frozen corpus; if added, unique resolution is insufficient.
                            correct = False
                        quote_policy_correct += int(correct)
                    for pi, pred in enumerate(pred_quotes):
                        if pi not in matched_pred and pred.status == "resolved":
                            quote_false_resolved_unmatched += 1

        multi = [
            v["metrics"]["final_state_agreement"]
            for v in per_case.values()
            if len(v["orders"]) > 1
        ]
        return {
            "total_replay_orders": len(all_results),
            "multi_order_cases": sum(1 for v in per_case.values() if len(v["orders"]) > 1),
            "mean_final_state_agreement_multi_order_cases": sum(multi) / len(multi) if multi else None,
            "parent_relation_precision": _fraction(parent_correct, parent_pred),
            "parent_relation_recall": _fraction(parent_correct, parent_gold),
            "ancestry_precision": _fraction(ancestry_correct, ancestry_pred),
            "ancestry_recall": _fraction(ancestry_correct, ancestry_gold),
            "quote_occurrence_precision": _fraction(quote_matched, quote_pred),
            "quote_occurrence_recall": _fraction(quote_matched, quote_gold),
            "quote_source_policy_accuracy_on_matched": _fraction(quote_policy_correct, quote_matched),
            "quote_source_policy_recall_all_gold": _fraction(quote_policy_correct, quote_gold),
            "false_resolved_unmatched_quote_predictions": quote_false_resolved_unmatched,
            "per_case": per_case,
        }

    unsafe = evaluate_mode(preserve_id_ambiguity=False)
    safe = evaluate_mode(preserve_id_ambiguity=True)
    return {
        "status": "EXPERIMENT_EXECUTION_COMPLETE_SYNTHETIC",
        "case_count": len(cases),
        "unsafe_single_id_baseline": unsafe,
        "ambiguity_preserving_id_baseline": safe,
        "identified_failure_modes": [
            "Collapsing duplicate Internet Message-ID values into a one-value map makes the duplicate-id case arrival-order dependent and forces unsupported unique parent choices.",
            "Preserving the identifier collision as an alternative set removes that duplicate-id arrival-order dependency in the synthetic comparator without changing historical raw messages.",
            "Occurrence-specific quote scoring exposes detector segmentation gaps rather than allowing one correct message-level source assessment to satisfy multiple gold occurrences.",
            "Markerless/forwarded quote occurrences remain detector failures and are not hidden by replay scoring.",
        ],
        "architecture_boundary": "The comparator supports research acceptance requirements: duplicate identifiers/alternative parents must remain representable, relation histories must be replayable, and parent/ancestry/quote-source relations must remain distinct. This is not an approved persistence architecture.",
        "academic_refresh_decision": "Do not automatically reopen A7. The controlled late-parent replay mechanism can revise state when evidence arrives; the concrete baseline failures are representation/detection issues. Reconsider A7 only if later candidate implementations cannot satisfy these E3 checks.",
        "claim_boundary": "Replay metrics now score reply-parent, indirect ancestry, and quote occurrences separately with explicit precision/recall denominators. Results are deterministic synthetic diagnostics only.",
    }

def run_e4() -> dict[str, Any]:
    calibration = generate_examples(seed=20260915, count_per_family=40, variant="calibration")
    test = generate_examples(seed=20260916, count_per_family=40, variant="holdout")
    calibration_keys = {x.content_key for x in calibration}
    test_keys = {x.content_key for x in test}
    content_overlap = calibration_keys & test_keys
    calibration_templates = sorted({x.template_family for x in calibration})
    test_templates = sorted({x.template_family for x in test})
    if content_overlap:
        raise RuntimeError(f"calibration/test content overlap: {len(content_overlap)}")
    if set(calibration_templates) & set(test_templates):
        raise RuntimeError("calibration/test template families overlap")
    threshold, calibration_rows = choose_threshold(calibration, max_accepted_error=0.05)
    evaluated = [evaluate_example(x, threshold=threshold) for x in test]

    accepted = [x for x in evaluated if not x.resolution.abstained]
    wrong = [x for x in accepted if not x.accepted_correct]
    unique_gold = [x for x in evaluated if x.example.unique_gold]
    unique_correct = [x for x in unique_gold if x.accepted_correct]
    ambiguous = [x for x in evaluated if x.example.source_available and len(x.example.gold_sources) > 1]
    ambiguous_abstained = [x for x in ambiguous if x.resolution.abstained]
    missing = [x for x in evaluated if not x.example.source_available]
    missing_abstained = [x for x in missing if x.resolution.abstained]

    candidate_total = candidate_found = 0
    for item in evaluated:
        if not item.example.source_available:
            continue
        pred = {x.source_message_id for x in item.resolution.candidates}
        candidate_total += len(item.example.gold_sources)
        candidate_found += len(pred & set(item.example.gold_sources))

    reliability = [(x.resolution.confidence, x.accepted_correct) for x in accepted]
    by_family: dict[str, dict[str, int | float]] = {}
    for family in sorted({x.example.family for x in evaluated}):
        rows = [x for x in evaluated if x.example.family == family]
        acc = [x for x in rows if not x.resolution.abstained]
        wrong_f = [x for x in acc if not x.accepted_correct]
        by_family[family] = {
            "count": len(rows),
            "accepted": len(acc),
            "abstained": len(rows) - len(acc),
            "wrong_accepted": len(wrong_f),
            "coverage": len(acc) / len(rows),
            "accepted_error": len(wrong_f) / len(acc) if acc else 0.0,
        }

    return {
        "status": "EXPERIMENT_EXECUTION_COMPLETE_SYNTHETIC",
        "calibration_seed": 20260915,
        "test_seed": 20260916,
        "calibration_examples": len(calibration),
        "test_examples": len(test),
        "calibration_template_families": calibration_templates,
        "test_template_families": test_templates,
        "content_overlap_count": len(content_overlap),
        "selected_accept_threshold": threshold,
        "calibration_threshold_sweep": calibration_rows,
        "test_coverage": _fraction(len(accepted), len(evaluated)),
        "test_accepted_unique_error": _fraction(len(wrong), len(accepted)),
        "test_unique_source_recall": _fraction(len(unique_correct), len(unique_gold)),
        "test_ambiguous_abstention": _fraction(len(ambiguous_abstained), len(ambiguous)),
        "test_missing_source_abstention": _fraction(len(missing_abstained), len(missing)),
        "test_candidate_recall": _fraction(candidate_found, candidate_total),
        "accepted_prediction_reliability_bins": reliability_bins(reliability, bins=5),
        "accepted_prediction_ece": expected_calibration_error(reliability, bins=5),
        "by_family": by_family,
        "identified_failure_modes": [
            f"The disjoint held-out test produced {len(wrong)} wrong accepted unique attributions among {len(accepted)} accepted predictions in this deterministic run.",
            "A calibration split that meets an aggregate accepted-error budget does not establish zero error on unseen production or rare ambiguity strata.",
        ],
        "topic10_handoff": "General calibration/selective-prediction method selection and production reliability targets remain Topic 10. Topic 01 only establishes relation-specific plumbing and a controlled diagnostic.",
        "claim_boundary": "The threshold and reliability numbers are synthetic-distribution diagnostics only. General calibration methodology belongs to Topic 10; production calibration requires future user-reviewed domain data.",
    }


def run_all(root: Path) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    e1 = run_e1(root)
    e2 = run_e2()
    e3 = run_e3()
    e4 = run_e4()
    return {
        "run_schema": "topic01-engineering-run-v1",
        "started_at_utc": started.isoformat(),
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "production_data_used": False,
        "external_network_used": False,
        "scope": "Topic 01 E1-E4 synthetic engineering validation",
        "E1": e1,
        "E2": e2,
        "E3": e3,
        "E4": e4,
        "overall_status": "EXPERIMENT_EXECUTION_COMPLETE_SYNTHETIC_WITH_IDENTIFIED_BASELINE_FAILURES",
        "review_acceptance_status": "SEPARATE_AUDIT_ARTIFACT",
    }


def write_results(root: Path, result: dict[str, Any]) -> None:
    results_dir = root / "results"
    audit_dir = root / "audit"
    results_dir.mkdir(parents=True, exist_ok=True)
    audit_dir.mkdir(parents=True, exist_ok=True)
    result_path = results_dir / "experiment-run.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    deterministic = {
        "run_schema": result["run_schema"],
        "production_data_used": result["production_data_used"],
        "external_network_used": result["external_network_used"],
        "scope": result["scope"],
        "E1": result["E1"],
        "E2": result["E2"],
        "E3": result["E3"],
        "E4": result["E4"],
        "overall_status": result["overall_status"],
        "review_acceptance_status": result["review_acceptance_status"],
    }
    metrics_path = results_dir / "metrics.json"
    metrics_path.write_text(json.dumps(deterministic, ensure_ascii=False, indent=2, sort_keys=True) + "\n")

    e1, e2, e3, e4 = (result[x] for x in ("E1", "E2", "E3", "E4"))
    structural = e2["arrival_time_structural_end_to_end"]
    augmented = e2["arrival_time_reuse_augmented_end_to_end"]
    unsafe = e3["unsafe_single_id_baseline"]
    safe = e3["ambiguity_preserving_id_baseline"]

    md = f"""# Topic 01 engineering-validation results

## Status

- Experiment execution: **{result['overall_status']}**
- Independent review acceptance: **tracked separately in `STATUS.md` and review audit artifacts**

No production mailbox data was used. No external network access was used by the experiment runner. These are controlled synthetic/adversarial results, not production accuracy claims.

An independent methodological review of the first engineering run rejected two claims: circular extractor gold and omission of false-positive detections from the attribution-error denominator. The current result contract fixes both issues and also addresses the review's replay, source-semantics, source-availability, and calibration-split concerns. The rejected review remains under `audit/independent-review/` as historical evidence.

## E1 — Joint benchmark contract

- Status: **{e1['status']}**.
- Cases: **{e1['case_count']}**; messages: **{e1['message_count']}**; fixture families: **{len(e1['families'])}**.
- Gold quote occurrences: **{e1['quote_occurrence_count']}**; gold source links: **{e1['quote_source_link_count']}**.
- Alternative-source ambiguous occurrences: **{e1['ambiguous_quote_occurrences']}**; deliberately missing-source occurrences: **{e1['missing_source_quote_occurrences']}**.
- Gold structural relations: **{e1['relation_gold_count']}**; labeled content spans: **{e1['labeled_span_count']}**.
- Replay orders: **{e1['replay_order_count']}**.

Fixture expected bodies are authored independently of `extract_body`; the fixture module does not invoke the extractor under test. Composite multi-parent quoted text is represented as separate source-specific occurrences instead of being mislabeled as source ambiguity.

**Conclusion:** the executable joint annotation/fixture contract is completed for synthetic engineering research. Production representativeness remains explicitly unproven.

## E2 — Preservation and quote/source alignment

### Independently authored extraction/preservation gold

- Exact body match: **{e2['extraction_exact_body_match']['numerator']}/{e2['extraction_exact_body_match']['denominator']}**.
- Decision/condition/deadline span preservation: **{e2['decision_condition_deadline_preservation']['numerator']}/{e2['decision_condition_deadline_preservation']['denominator']}**.
- Unique/new-content span preservation: **{e2['unique_or_new_content_preservation']['numerator']}/{e2['unique_or_new_content_preservation']['denominator']}**.

A regression test corrupts the extractor by deleting `Deadline: Friday.` and requires both extraction and decision-relevant preservation metrics to fall, preventing the former circular-gold failure.

### Structural detector — arrival-time end-to-end

- Detection precision: **{e2['quote_detection']['precision']['value']:.3f}**; recall: **{e2['quote_detection']['recall']['value']:.3f}**.
- Accepted source attributions: **{structural['accepted_attributions']}**; false accepted: **{structural['false_accepted_attributions']}**.
- Accepted-attribution error: **{structural['accepted_attribution_error']['value']:.3f}**.
- Candidate recall over source links available at arrival: **{structural['candidate_recall_at_arrival']['value']:.3f}**.
- Unique-resolution recall over eligible gold at arrival: **{structural['unique_resolution_recall_at_arrival']['value']:.3f}**.

The structural detector misses markerless, forwarded, and one composite multi-source display occurrence/segment under the occurrence-level gold contract. Detection and source matching remain separate metrics.

### Exact-reuse-augmented detector — arrival-time end-to-end

- Detection precision: **{e2['reuse_augmented_quote_detection']['precision']['value']:.3f}**; recall: **{e2['reuse_augmented_quote_detection']['recall']['value']:.3f}**.
- Predicted occurrences: **{augmented['predicted_occurrences']}**; unmatched predicted occurrences: **{augmented['unmatched_predicted_occurrences']}**.
- Accepted source attributions: **{augmented['accepted_attributions']}**; false accepted: **{augmented['false_accepted_attributions']}**.
- Accepted-attribution error: **{augmented['accepted_attribution_error']['value']:.3f}**.
- Candidate recall over source links available at arrival: **{augmented['candidate_recall_at_arrival']['value']:.3f}**.
- Unique-resolution recall over eligible gold at arrival: **{augmented['unique_resolution_recall_at_arrival']['value']:.3f}**.

Every predicted occurrence, including unmatched false positives, is included in the attribution-error denominator. Reuse improves candidate recall but can create repeated-boilerplate false positives and reverse provenance when a reply containing quoted text is collected before its historical original. **Text reuse is candidate evidence, not proof of quotation status or provenance direction.**

### Gold-conditioned final-context diagnostic

- Conditional full-context candidate recall: **{e2['conditional_full_context_source_resolution']['candidate_recall']['value']:.3f}**.
- Conditional accepted unique error: **{e2['conditional_full_context_source_resolution']['accepted_unique_error']['value']:.3f}**.
- Conditional source-span exact boundary: **{e2['conditional_full_context_source_span_exact_boundary']['value']:.3f}**; mean IoU: **{e2['conditional_full_context_source_span_mean_iou']:.3f}**.

These numbers are explicitly capability diagnostics **given gold occurrence locations and final case context**. They are not end-to-end or arrival-time performance.

## E3 — Arrival replay, correction, ancestry, and duplicate identity

### Deliberately unsafe single-value Message-ID baseline

- Mean final-state agreement across multi-order cases: **{unsafe['mean_final_state_agreement_multi_order_cases']:.3f}**.
- Parent precision/recall: **{unsafe['parent_relation_precision']['value']:.3f} / {unsafe['parent_relation_recall']['value']:.3f}**.
- Ancestry precision/recall: **{unsafe['ancestry_precision']['value']:.3f} / {unsafe['ancestry_recall']['value']:.3f}**.
- Quote occurrence precision/recall: **{unsafe['quote_occurrence_precision']['value']:.3f} / {unsafe['quote_occurrence_recall']['value']:.3f}**.
- Quote source-policy accuracy on matched occurrences: **{unsafe['quote_source_policy_accuracy_on_matched']['value']:.3f}**.
- Quote source-policy recall over all gold occurrences: **{unsafe['quote_source_policy_recall_all_gold']['value']:.3f}**.
- Duplicate-ID case final-state agreement: **{unsafe['per_case']['duplicate-message-id']['metrics']['final_state_agreement']:.3f}**.

### Ambiguity-preserving identifier comparator

- Mean final-state agreement across multi-order cases: **{safe['mean_final_state_agreement_multi_order_cases']:.3f}**.
- Parent precision/recall: **{safe['parent_relation_precision']['value']:.3f} / {safe['parent_relation_recall']['value']:.3f}**.
- Ancestry precision/recall: **{safe['ancestry_precision']['value']:.3f} / {safe['ancestry_recall']['value']:.3f}**.
- Quote occurrence precision/recall: **{safe['quote_occurrence_precision']['value']:.3f} / {safe['quote_occurrence_recall']['value']:.3f}**.
- Quote source-policy recall over all gold occurrences: **{safe['quote_source_policy_recall_all_gold']['value']:.3f}**.
- Duplicate-ID case final-state agreement: **{safe['per_case']['duplicate-message-id']['metrics']['final_state_agreement']:.3f}**.

The one-value identifier map is arrival-order dependent and forces unsupported unique parents under Message-ID collision. Preserving alternatives removes that specific synthetic failure. Replay now records occurrence spans, scores quotes one-to-one, distinguishes direct parent from indirect ancestry, and reports relations removed before the final snapshot instead of a tautological stale=0 metric.

**Conclusion:** future candidate implementations must preserve identifier collisions/alternative parent evidence or abstain, and must keep reply-parent, ancestry, and quote-source relations independently testable. This is an evidence-backed acceptance requirement for later design work, not an approved persistence architecture.

## E4 — Structural uncertainty / abstention

Calibration and test use disjoint authored template families and have **{e4['content_overlap_count']}** identical-content overlaps.

- Calibration examples: **{e4['calibration_examples']}**; held-out test examples: **{e4['test_examples']}**.
- Calibration template families: **{', '.join(e4['calibration_template_families'])}**.
- Held-out template families: **{', '.join(e4['test_template_families'])}**.
- Selected threshold: **{e4['selected_accept_threshold']:.2f}**.
- Test coverage: **{e4['test_coverage']['value']:.3f}**.
- Accepted unique-link error: **{e4['test_accepted_unique_error']['value']:.3f}**.
- Unique-source recall: **{e4['test_unique_source_recall']['value']:.3f}**.
- Ambiguous-case abstention: **{e4['test_ambiguous_abstention']['value']:.3f}**.
- Missing-source abstention: **{e4['test_missing_source_abstention']['value']:.3f}**.
- Candidate recall: **{e4['test_candidate_recall']['value']:.3f}**.
- Accepted-prediction ECE (synthetic diagnostic): **{e4['accepted_prediction_ece']:.3f}**.

This is a relation-specific synthetic diagnostic. A clean held-out result does not establish production calibration, rare-stratum safety, or general selective-prediction methodology; those remain Topic 10/future domain validation.

## Current completion decision

E1–E4 experiment execution is complete at the synthetic level. Whether that evidence is accepted for Topic 01 closure is a separate independent-review decision recorded outside `metrics.json`; experiment execution status must not be read as review acceptance. Even after review acceptance, this does **not** mean msgloom has a production-ready reconstruction implementation.

The engineering results do **not** automatically trigger Topic 01 Academic Round 3:

- A2: current failures are concrete detection/provenance limitations of deliberately simple baselines; targeted literature refresh remains conditional on candidate-method selection or persistent failure of stronger candidates.
- A7: controlled late-parent replay can revise structural state. The concrete failure found here is duplicate-identifier representation plus quote detection, not evidence that modern/LLM literature is required. A7 remains open and can be revisited by separate decision.

## Deferred / handed off

- Production representativeness and user-reviewed domain validation: deferred until suitable real/domain data becomes available; current work does not wait for it.
- Semantic response / partial agreement: Topic 04.
- General selective-prediction / calibration methodology: Topic 10.
- E5 code/data/license/reproduction: after a concrete external method is selected.
- E6 Raspberry Pi performance: after correctness, preservation, and uncertainty behavior are established.
- Cross-independent-group Topic identity: Topic 03 / Phase 2.
"""
    (root / "RESULTS.md").write_text(md)

    audit = {
        "result_path": str(result_path),
        "result_sha256": _sha(result_path),
        "deterministic_metrics_path": str(metrics_path),
        "deterministic_metrics_sha256": _sha(metrics_path),
        "fixture_manifest_sha256": _sha(root / "fixtures" / "MANIFEST.json"),
        "source_files": {},
    }
    for path in sorted((root / "src" / "topic01_validation").glob("*.py")):
        audit["source_files"][str(path.relative_to(root))] = _sha(path)
    (audit_dir / "experiment-manifest.json").write_text(json.dumps(audit, indent=2) + "\n")

def main() -> int:
    root = Path(__file__).resolve().parents[2]
    result = run_all(root)
    write_results(root, result)
    print(json.dumps({
        "overall_status": result["overall_status"],
        "review_acceptance_status": result["review_acceptance_status"],
        "E1": result["E1"]["status"],
        "E2": result["E2"]["status"],
        "E3": result["E3"]["status"],
        "E4": result["E4"]["status"],
        "results": str(root / "results" / "experiment-run.json"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
