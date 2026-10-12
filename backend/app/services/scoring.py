"""Psychometric and gap scoring formula services.

Implements all core mathematical formulations specified in Section 8 of the
RCT-GAT Specification:
- F10: Expected response time per difficulty band
- F11: Response-time ratio
- F12: Learning Gap Score (the interpretable cold-start baseline)
- F14: Adaptive remediation priority
- F15: Ebbinghaus mastery decay
- F16: Decay-based review scheduling
- F17: Coverage-weighted readiness score
"""
from __future__ import annotations

import math
from typing import Literal, Sequence


def expected_response_time(difficulty_b: float) -> float:
    """Expected response time in seconds based on difficulty parameter b (F10).

    Default band mapping:
    - b <= -0.5 (easy): 45.0 seconds
    - -0.5 < b <= 0.5 (medium): 60.0 seconds
    - b > 0.5 (hard): 90.0 seconds
    """
    if difficulty_b <= -0.5:
        return 45.0
    elif difficulty_b <= 0.5:
        return 60.0
    return 90.0


def time_ratio(response_time_ms: int | float, expected_time_sec: float) -> float:
    """Computes response time ratio normalised by difficulty (F11).

    TimeRatio = tau_student / ExpectedTime(b_question)

    Examples:
        >>> round(time_ratio(142000, 95.0), 2)
        1.49
        >>> round(time_ratio(38000, 95.0), 2)
        0.4
    """
    tau_sec = max(0.0, float(response_time_ms) / 1000.0)
    exp_sec = max(1e-6, float(expected_time_sec))
    return tau_sec / exp_sec


def time_penalty(time_ratio_val: float) -> float:
    """Time penalty term for Formula 12:

    TimePenalty_c = clip((TimeRatio_c - 1) / 2, 0, 1)

    Examples:
        >>> round(time_penalty(1.49), 3)
        0.245
        >>> time_penalty(0.5)
        0.0
        >>> time_penalty(3.5)
        1.0
    """
    raw = (time_ratio_val - 1.0) / 2.0
    return max(0.0, min(1.0, raw))


def gap_score(
    accuracy: float,
    time_ratio_val: float,
    skip_rate: float,
    hist_mastery: float,
    weights: tuple[float, float, float, float] = (0.40, 0.20, 0.20, 0.20),
) -> float:
    """Computes interpretable Learning Gap Score G_c (F12).

    G_c = w1*(1 - Accuracy_c) + w2*TimePenalty_c + w3*SkipRate_c + w4*(1 - M_c^hist)

    Examples:
        >>> round(gap_score(accuracy=0.35, time_ratio_val=1.49, skip_rate=0.25, hist_mastery=0.40), 3)
        0.479
    """
    w1, w2, w3, w4 = weights
    acc_term = 1.0 - max(0.0, min(1.0, accuracy))
    tp_term = time_penalty(time_ratio_val)
    skip_term = max(0.0, min(1.0, skip_rate))
    hist_term = 1.0 - max(0.0, min(1.0, hist_mastery))
    return w1 * acc_term + w2 * tp_term + w3 * skip_term + w4 * hist_term


def gap_band(score: float) -> Literal["strong", "moderate", "weak"]:
    """Discretises Learning Gap Score into standard bands:
    - < 0.30: strong (no significant gap)
    - 0.30 - 0.60: moderate (actionable gap, eligible for probe)
    - > 0.60: weak (severe gap, priority remediation)

    Examples:
        >>> gap_band(0.25)
        'strong'
        >>> gap_band(0.479)
        'moderate'
        >>> gap_band(0.68)
        'weak'
    """
    if score < 0.30:
        return "strong"
    elif score <= 0.60:
        return "moderate"
    return "weak"


def adaptive_priority(
    gap: float,
    days_to_target: int | float,
    skill_weight: float,
    dag_distance: int = 0,
    horizon: float = 120.0,
) -> float:
    """Computes priority rank for concept remediation queue (F14).

    Priority_c = Gap_c * Urgency_c * Relevance_c
    Urgency_c = clip(1 - days_to_target / H, 0.1, 1.0)
    Relevance_c = w_skill * (1 / (1 + dist_DAG(c, target)))

    Examples:
        >>> round(adaptive_priority(0.479, days_to_target=40, skill_weight=0.30, dag_distance=0, horizon=120.0), 3)
        0.096
    """
    urgency = max(0.1, min(1.0, 1.0 - float(days_to_target) / horizon))
    relevance = skill_weight * (1.0 / (1.0 + float(dag_distance)))
    return gap * urgency * relevance


def mastery_decay(
    m0: float,
    elapsed_days: float,
    tau: float = 60.0,
) -> tuple[float, float]:
    """Computes mastery retention after elapsed time and half-life (F15).

    M_c(t) = M_c(t0) * exp(-(t - t0) / tau_c)
    t_half = tau_c * ln(2)

    Returns:
        (current_mastery, half_life_days)

    Examples:
        >>> m, t_half = mastery_decay(m0=0.80, elapsed_days=21.0, tau=60.0)
        >>> round(m, 3)
        0.564
        >>> round(t_half, 1)
        41.6
    """
    m_t = m0 * math.exp(-float(elapsed_days) / tau)
    t_half = tau * math.log(2.0)
    return m_t, t_half


def review_interval(
    m_current: float,
    m_target: float = 0.60,
    tau: float = 60.0,
) -> float:
    """Computes review interval in days before mastery decays to m_target (F16).

    delta_t_review = tau_c * ln(M_current / M_target)

    Examples:
        >>> round(review_interval(m_current=0.80, m_target=0.60, tau=60.0), 1)
        17.3
    """
    if m_current <= m_target:
        return 0.0
    return tau * math.log(m_current / m_target)


def readiness_score(
    skills_data: Sequence[dict[str, float] | tuple[float, float]],
) -> float:
    """Computes coverage-weighted readiness score across target skills (F17).

    Readiness = sum_s w_s * [ sum_{c in s} cov_c * M_c / sum_{c in s} cov_c ]

    Accepts list of dicts with keys 'weight' and 'mean_mastery', or (weight, mean_mastery) tuples.

    Examples:
        >>> # Spec rounded intermediate 0.35 * 0.55 = 0.1925 to 0.193 -> 0.681; exact float is 0.6805:
        >>> round(readiness_score([(0.40, 0.72), (0.35, 0.55), (0.25, 0.80)]), 2)
        0.68
        >>> round(readiness_score([(0.40, 0.72), (0.35, 0.553), (0.25, 0.80)]), 3)
        0.682
    """
    total = 0.0
    for item in skills_data:
        if isinstance(item, tuple):
            w_s, m_s = item
        else:
            w_s = item["weight"]
            m_s = item["mean_mastery"]
        total += w_s * m_s
    return total
