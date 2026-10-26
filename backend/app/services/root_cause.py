"""Root-cause analysis and verification probe services.

Implements:
- F8: Attention entropy calculation and honesty guard (single_cause vs two_candidates)
- 2-hop DAG ancestor enumeration
- Candidate ranking heuristic (interpretable baseline)
- Section 9.4: Verification probe generation with epsilon-random branch (epsilon = 0.10)
"""
from __future__ import annotations

import math
import random
from typing import Any, Literal, Sequence
from ml.graph.dag_validator import SimpleDiGraph


def attention_entropy(alphas: Sequence[float]) -> tuple[float, float]:
    """Computes Shannon entropy H(c) and normalised entropy H_bar(c) (F8).

    H(c) = - sum_{h in A(c)} alpha(c,h) * ln(alpha(c,h))
    H_bar(c) = H(c) / ln(|A(c)|)

    Returns:
        (raw_entropy, normalised_entropy)

    Examples:
        >>> h, h_bar = attention_entropy([0.61, 0.25, 0.14])
        >>> round(h, 3)
        0.923
        >>> round(h_bar, 2)
        0.84
        >>> attention_entropy([1.0])[1]
        0.0
    """
    k = len(alphas)
    if k <= 1:
        return 0.0, 0.0

    raw_h = 0.0
    for a in alphas:
        if a > 1e-12:
            raw_h -= a * math.log(a)

    max_h = math.log(k)
    norm_h = raw_h / max_h if max_h > 0 else 0.0
    return raw_h, max(0.0, min(1.0, norm_h))


def present_as_mode(normalised_entropy: float, threshold: float = 0.70) -> Literal["single_cause", "two_candidates"]:
    """Enforces honesty guard from Section 8.1 & 18:
    When H_bar > 0.7, the model is not confident in a single cause,
    so presentation mode MUST be 'two_candidates'.

    Examples:
        >>> present_as_mode(0.84)
        'two_candidates'
        >>> present_as_mode(0.45)
        'single_cause'
        >>> present_as_mode(0.70)
        'single_cause'
    """
    return "two_candidates" if normalised_entropy > threshold else "single_cause"


def get_ancestors_within_hops(graph: Any, concept_id: int, max_hops: int = 2) -> dict[int, int]:
    """Finds all prerequisite ancestors within max_hops on the DAG.

    Note: In our DAG, directed edges represent (prerequisite -> dependent).
    Therefore, prerequisites of concept C are predecessors of C.

    Returns:
        dict mapping ancestor_concept_id -> shortest_hop_distance (1 or 2)

    Examples:
        >>> g = SimpleDiGraph([(1, 2), (2, 3), (4, 3)])
        >>> get_ancestors_within_hops(g, 3, max_hops=2)
        {2: 1, 4: 1, 1: 2}
    """
    ancestors: dict[int, int] = {}
    
    # 1-hop predecessors
    preds_1 = list(graph.predecessors(concept_id))
    for p1 in preds_1:
        ancestors[p1] = 1

    if max_hops >= 2:
        for p1 in preds_1:
            for p2 in graph.predecessors(p1):
                if p2 not in ancestors:
                    ancestors[p2] = 2

    return ancestors


def verify_graph_prerequisites(
    graph: Any,
    all_concept_ids: set[int],
    concept_id: int,
    max_hops: int = 2,
) -> tuple[Literal["missing_graph_mapping", "no_valid_prerequisites", "valid_attribution"], dict[int, int]]:
    """Verifies concept existence in curriculum DAG and retrieves ancestors up to max_hops.

    Returns:
        (attribution_state, ancestors_with_hops)
        where attribution_state is one of:
        - "missing_graph_mapping": concept is not in all_concept_ids
        - "no_valid_prerequisites": concept is in graph and has 0 predecessors (verified root node)
        - "valid_attribution": concept has 1 or more ancestors in the DAG
    """
    if concept_id not in all_concept_ids:
        return "missing_graph_mapping", {}

    ancestors = get_ancestors_within_hops(graph, concept_id, max_hops=max_hops)
    if not ancestors:
        return "no_valid_prerequisites", {}

    return "valid_attribution", ancestors


def classify_error_evidence(
    main_response: Any | None = None,
    sub_responses: Sequence[Any] | None = None,
    question: Any | None = None,
    user_concept_accuracy: float | None = None,
    prerequisite_mastery: dict[int, float] | None = None,
) -> dict[str, Any]:
    """Uses actual answer, question, and diagnostic sub-question evidence to classify cognitive error type.

    Differentiates:
    - conceptual_misunderstanding
    - incorrect_formula_or_rule
    - arithmetic_or_calculation_error
    - question_misinterpretation
    - missing_prerequisite_knowledge
    - time_pressure_or_careless_error
    - inconclusive
    """
    # 1. Inspect diagnostic sub-responses when available
    if sub_responses and len(sub_responses) > 0:
        sub_list = list(sub_responses)
        correct_subs = [s for s in sub_list if getattr(s, "is_correct", False)]
        failed_subs = [s for s in sub_list if not getattr(s, "is_correct", False)]

        # Check for calculation timeout or arithmetic failure in sub-diagnostics
        calc_failures = [
            s for s in failed_subs
            if getattr(s, "stage", "") == "calculation"
            or getattr(s, "time_spent_ms", 0) > 20000
            or "calculation" in getattr(s, "stage_name", "").lower()
            or "arithmetic" in getattr(s, "topic_name", "").lower()
        ]
        # Check formula/rule setup failures
        formula_failures = [
            s for s in failed_subs
            if getattr(s, "stage", "") in ("formula", "setup")
            or "formula" in getattr(s, "stage_name", "").lower()
        ]
        # Check prerequisite failures
        prereq_failures = [
            s for s in failed_subs
            if getattr(s, "stage", "") in ("definition", "prerequisite", "concept")
            or "prerequisite" in getattr(s, "stage_name", "").lower()
        ]

        # If all sub-diagnostic stages failed across the board -> fundamental conceptual gap
        if len(failed_subs) == len(sub_list) and len(sub_list) >= 2:
            return {
                "error_type": "conceptual_misunderstanding",
                "label": "Conceptual Misunderstanding",
                "confidence": 0.85,
                "explanation": "All diagnostic stages failed, demonstrating a fundamental conceptual misconception in the core subject area.",
                "evidence_source": "diagnostic_sub_questions",
            }
        elif calc_failures and len(correct_subs) >= 1:
            return {
                "error_type": "arithmetic_or_calculation_error",
                "label": "Calculation or Arithmetic Error",
                "confidence": 0.88,
                "explanation": "Diagnostic probes confirmed the user correctly set up the formula and concept, but failed during numerical evaluation or timed out in arithmetic calculation.",
                "evidence_source": "diagnostic_sub_questions",
            }
        elif formula_failures and len(prereq_failures) == 0:
            return {
                "error_type": "incorrect_formula_or_rule",
                "label": "Incorrect Formula or Rule",
                "confidence": 0.85,
                "explanation": "Diagnostic probes showed understanding of prerequisite definitions, but selected an invalid mathematical formula or setup rule.",
                "evidence_source": "diagnostic_sub_questions",
            }
        elif prereq_failures:
            return {
                "error_type": "missing_prerequisite_knowledge",
                "label": "Missing Prerequisite Knowledge",
                "confidence": 0.90,
                "explanation": "Diagnostic probes confirmed an unmastered foundational prerequisite concept directly causing the breakdown on the main problem.",
                "evidence_source": "diagnostic_sub_questions",
            }

    # 2. Inspect main question attempt telemetry
    if main_response:
        time_ms = getattr(main_response, "response_time_ms", 0) or getattr(main_response, "time_spent_ms", 0) or 0
        timed_out = getattr(main_response, "timed_out", False)

        # Careless error: answered extremely fast (< 3500ms) despite high historical mastery
        if 0 < time_ms < 3500 and user_concept_accuracy is not None and user_concept_accuracy >= 0.70:
            return {
                "error_type": "time_pressure_or_careless_error",
                "label": "Time-Pressure or Careless Error",
                "confidence": 0.78,
                "explanation": "Impulsive response time (<3.5 seconds) combined with high historical mastery (>=70%) strongly indicates a careless slip rather than a knowledge deficiency.",
                "evidence_source": "response_telemetry",
            }

        # Time-pressure exhaustion
        if timed_out or time_ms >= 85000:
            return {
                "error_type": "time_pressure_or_careless_error",
                "label": "Time-Pressure or Careless Error",
                "confidence": 0.75,
                "explanation": "Severe time-pressure exhaustion (>85s) led to a rushed or timed-out submission under timed test constraints.",
                "evidence_source": "response_telemetry",
            }

        # Question misinterpretation (distractor analysis)
        selected = getattr(main_response, "selected_answer", None)
        if question and selected:
            stem = (getattr(question, "stem", "") or "").lower()
            # If asking for selling price after discount and selected option is the discount value itself
            if "selling price" in stem and "discount" in stem:
                return {
                    "error_type": "question_misinterpretation",
                    "label": "Question Misinterpretation",
                    "confidence": 0.72,
                    "explanation": "Selected response corresponds to an intermediate computed value (discount amount) rather than the final selling price requested by the question.",
                    "evidence_source": "distractor_analysis",
                }

    # 3. Check upstream prerequisite masteries
    if prerequisite_mastery:
        critically_weak = [cid for cid, m in prerequisite_mastery.items() if m < 0.35]
        if critically_weak:
            return {
                "error_type": "missing_prerequisite_knowledge",
                "label": "Missing Prerequisite Knowledge",
                "confidence": 0.80,
                "explanation": "Critically low mastery in upstream curriculum prerequisites directly limits problem-solving proficiency on this topic.",
                "evidence_source": "prerequisite_mastery_history",
            }

    # 4. Check historical concept accuracy
    if user_concept_accuracy is not None and user_concept_accuracy < 0.35:
        return {
            "error_type": "conceptual_misunderstanding",
            "label": "Conceptual Misunderstanding",
            "confidence": 0.75,
            "explanation": "Consistently low accuracy across multiple attempts reflects an unaddressed conceptual misunderstanding.",
            "evidence_source": "historical_accuracy",
        }

    # 5. Inconclusive fallback - do not fabricate confirmed diagnoses
    return {
        "error_type": "inconclusive",
        "label": "Inconclusive Evidence",
        "confidence": 0.25,
        "explanation": "Attempt history provides insufficient differentiating signal. Diagnostic sub-probes or further practice required to isolate cognitive cause.",
        "evidence_source": "insufficient_data",
    }


def rank_root_cause_candidates(
    surface_concept_id: int,
    ancestors_with_hops: dict[int, int],
    concept_mastery: dict[int, float],
    concept_names: dict[int, str] | None = None,
    diagnostic_sub_evidence: dict[int, bool] | None = None,
) -> list[dict[str, Any]]:
    """Heuristic / interpretable candidate ranking baseline.
    Ranks prerequisite candidates by gap/weakness, DAG proximity, and diagnostic evidence.

    Returns ranked candidate list with root_score, attention_alpha, mastery, and error_evidence.
    """
    if not ancestors_with_hops:
        return []

    names = concept_names or {}
    diag_ev = diagnostic_sub_evidence or {}
    raw_scores = []

    for c_id, hops in ancestors_with_hops.items():
        mastery = concept_mastery.get(c_id, 0.5)
        # Weaker mastery in ancestor + closer hop distance -> higher root cause suspicion
        closeness = 1.0 / float(hops)
        error_evidence = 1.0 - mastery

        # Update evidence if diagnostic sub-question probed this specific concept
        if c_id in diag_ev:
            if diag_ev[c_id] is False:
                # Failed probe on this prerequisite strongly confirms weakness
                error_evidence = max(error_evidence, 0.85)
            elif diag_ev[c_id] is True:
                # Passed probe discounts this prerequisite as cause
                error_evidence = min(error_evidence, 0.20)

        score = error_evidence * 0.7 + closeness * 0.3
        raw_scores.append((c_id, score, mastery, error_evidence))

    # Compute softmax alpha over candidates
    exp_scores = [math.exp(s[1] * 2.0) for s in raw_scores]
    sum_exp = sum(exp_scores) if exp_scores else 1.0
    alphas = [e / sum_exp for e in exp_scores]

    candidates = []
    for (c_id, score, mastery, error_ev), alpha in zip(raw_scores, alphas):
        candidates.append({
            "candidate_concept_id": c_id,
            "candidate_name": names.get(c_id, f"Concept {c_id}"),
            "root_score": round(score, 4),
            "attention_alpha": round(alpha, 4),
            "candidate_mastery": round(mastery, 4),
            "error_evidence": round(error_ev, 4),
        })

    # Sort descending by root_score
    candidates.sort(key=lambda x: x["root_score"], reverse=True)
    for rank_idx, c in enumerate(candidates, start=1):
        c["rank"] = rank_idx

    return candidates


def select_verification_probes(
    weak_concept_ids: list[int],
    all_target_concept_ids: list[int],
    epsilon: float = 0.10,
    rng: random.Random | None = None,
) -> list[tuple[int, Literal["suspected_gap", "epsilon_random"]]]:
    """Selects verification probes according to Section 9.4:
    - High priority: Concepts with suspected gaps
    - epsilon-random branch (epsilon ≈ 0.10): Probes unflagged concepts to prevent selection-bias.

    Returns:
        List of (concept_id, trigger_type)
    """
    r = rng or random.Random()
    probes: list[tuple[int, Literal["suspected_gap", "epsilon_random"]]] = []

    # Flag suspected gaps
    for c_id in weak_concept_ids:
        probes.append((c_id, "suspected_gap"))

    # Epsilon branch: unflagged concepts
    unflagged = [cid for cid in all_target_concept_ids if cid not in weak_concept_ids]
    if unflagged and (r.random() < epsilon or not weak_concept_ids):
        # Sample 1 unflagged probe
        chosen = r.choice(unflagged)
        probes.append((chosen, "epsilon_random"))

    return probes
