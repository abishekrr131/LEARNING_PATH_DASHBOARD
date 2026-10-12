"""Evaluation Metrics, Trial Effect Sizes (Cohen's d), and Synthetic Data Guards.

Conforms to Spec Section 11, 23, and Change 4:
- Formula 23: Pooled standard deviation and Cohen's d effect size between Root-Cause vs Surface arm.
- 95% Confidence intervals for Cohen's d.
- Welch's t-test p-value.
- Strict Synthetic Data Guard: Refuses metrics reporting on dataset labeled 'pipeline-test-synthetic'.
"""
from __future__ import annotations

import math
from typing import Dict, Any, List
import numpy as np
from scipy import stats


class SyntheticDataReportError(Exception):
    """Raised when evaluation metrics are requested on synthetic pipeline-test data."""
    pass


def cohens_d(group1: List[float] | np.ndarray, group2: List[float] | np.ndarray) -> Dict[str, Any]:
    """Computes Cohen's d effect size (Formula 23) between two treatment arms.

    d = (mean_1 - mean_2) / s_pooled
    where s_pooled = sqrt( ((n_1 - 1)*s_1^2 + (n_2 - 1)*s_2^2) / (n_1 + n_2 - 2) )
    """
    g1 = np.asarray(group1, dtype=float)
    g2 = np.asarray(group2, dtype=float)

    n1, n2 = len(g1), len(g2)
    if n1 < 2 or n2 < 2:
        raise ValueError("Each group must contain at least 2 observations for Cohen's d")

    m1, m2 = float(np.mean(g1)), float(np.mean(g2))
    v1, v2 = float(np.var(g1, ddof=1)), float(np.var(g2, ddof=1))

    # Pooled variance
    df = n1 + n2 - 2
    s_pooled = math.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / df)

    if s_pooled < 1e-12:
        d = 0.0
    else:
        d = (m1 - m2) / s_pooled

    # Approximate 95% Confidence Interval for Cohen's d (Hedges & Olkin 1985)
    se_d = math.sqrt((n1 + n2) / (n1 * n2) + (d ** 2) / (2 * df))
    ci_lower = d - 1.96 * se_d
    ci_upper = d + 1.96 * se_d

    # Welch's t-test
    t_stat, p_val = stats.ttest_ind(g1, g2, equal_var=False)

    return {
        "cohens_d": round(d, 4),
        "ci_95": (round(ci_lower, 4), round(ci_upper, 4)),
        "mean_arm_root_cause": round(m1, 4),
        "mean_arm_surface": round(m2, 4),
        "mean_difference": round(m1 - m2, 4),
        "pooled_std": round(s_pooled, 4),
        "t_statistic": round(float(t_stat), 4),
        "p_value": round(float(p_val), 6),
        "statistically_significant": float(p_val) < 0.05,
    }


def generate_trial_report(
    root_cause_gains: List[float],
    surface_gains: List[float],
    dataset_version: str = "rct-gat-v1.0-live",
) -> Dict[str, Any]:
    """Generates official trial effect size report.

    Guards against reporting metrics from synthetic pipeline tests (Change 4).
    """
    if "synthetic" in dataset_version.lower() or "pipeline-test" in dataset_version.lower():
        raise SyntheticDataReportError(
            f"Strict Policy Guard: Synthetic data labeled '{dataset_version}' is reserved for "
            "pipeline unit testing only and must NEVER be reported in trial evaluation metrics."
        )

    effect = cohens_d(root_cause_gains, surface_gains)
    effect["dataset_version"] = dataset_version
    return effect
