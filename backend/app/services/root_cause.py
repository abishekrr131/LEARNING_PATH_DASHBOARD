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


def rank_root_cause_candidates(
    surface_concept_id: int,
    ancestors_with_hops: dict[int, int],
    concept_mastery: dict[int, float],
    concept_names: dict[int, str] | None = None,
) -> list[dict[str, Any]]:
    """Heuristic / interpretable candidate ranking baseline.
    Ranks prerequisite candidates by gap/weakness and DAG proximity.

    Returns ranked candidate list with root_score, attention_alpha, mastery, and error_evidence.
    """
    if not ancestors_with_hops:
        return []

    names = concept_names or {}
    raw_scores = []

    for c_id, hops in ancestors_with_hops.items():
        mastery = concept_mastery.get(c_id, 0.5)
        # Weaker mastery in ancestor + closer hop distance -> higher root cause suspicion
        closeness = 1.0 / float(hops)
        error_evidence = 1.0 - mastery
        score = error_evidence * 0.7 + closeness * 0.3
        raw_scores.append((c_id, score, mastery, error_evidence))

    # Compute simulated softmax alpha over candidates
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
