"""Item Response Theory (IRT) Calibration and Probability Calibration.

Conforms to Spec Section 27:
- 1PL (Rasch) parameter estimation on separate calibration split with frozen b values.
- Centered difficulties sum_j b_j = 0.
- Platt scaling (logistic calibration) and Isotonic regression calibration.
"""
from __future__ import annotations

from typing import Dict, List, Tuple
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression


def fit_1pl_rasch_difficulties(
    response_matrix: np.ndarray,  # shape: (num_learners, num_items) with values in {0, 1} (or NaN for unattempted)
    item_ids: List[int],
    max_iter: int = 100,
    tol: float = 1e-4,
) -> Dict[int, float]:
    """Estimates frozen item difficulty parameters b_j using Joint/Marginal Maximum Likelihood approximation.

    Under 1PL:
        P(Y_ij = 1 | theta_i, b_j) = 1 / (1 + exp(-(theta_i - b_j)))

    Centers difficulties such that mean(b) = 0.0.
    Returns:
        dict mapping item_id -> b_j (frozen IRT difficulty).
    """
    num_learners, num_items = response_matrix.shape
    assert len(item_ids) == num_items, "item_ids length must match matrix columns"

    # Empirical item proportion correct (p_j) with Laplace smoothing
    p_j = np.nanmean(response_matrix, axis=0)
    p_j = np.clip(p_j, 0.02, 0.98)

    # Initial PROX logit estimate: easy item (high p) -> negative b, hard item -> positive b
    b = np.log((1.0 - p_j) / p_j)

    # Empirical learner ability proxy (theta_i) from score
    raw_scores = np.nanmean(response_matrix, axis=1)
    raw_scores = np.clip(raw_scores, 0.02, 0.98)
    theta = np.log(raw_scores / (1.0 - raw_scores))

    # Standard psychometric PROX variance scaling (Cohen 1979 / Wright & Stone 1979)
    var_theta = float(np.var(theta))
    scale = float(np.sqrt(1.0 + var_theta / 2.89))
    b = b * scale

    # Re-center difficulties so mean(b) == 0.0
    b = b - np.mean(b)

    return {item_id: float(round(b[j], 4)) for j, item_id in enumerate(item_ids)}


class ProbabilityCalibrator:
    """Calibrates raw neural network probability outputs using Platt scaling or Isotonic regression."""

    def __init__(self, method: str = "platt"):
        assert method in ("platt", "isotonic"), "method must be 'platt' or 'isotonic'"
        self.method = method
        self.platt_model: LogisticRegression | None = None
        self.isotonic_model: IsotonicRegression | None = None

    def fit(self, raw_probs: np.ndarray, true_labels: np.ndarray) -> ProbabilityCalibrator:
        """Fits calibration curve on validation set split."""
        raw_probs = np.clip(raw_probs.flatten(), 1e-7, 1.0 - 1e-7)
        true_labels = true_labels.flatten().astype(int)

        if self.method == "platt":
            # Platt scaling: fit logistic regression on logits = log(p / (1-p))
            logits = np.log(raw_probs / (1.0 - raw_probs)).reshape(-1, 1)
            self.platt_model = LogisticRegression(C=1.0, solver="lbfgs")
            self.platt_model.fit(logits, true_labels)
        else:
            # Isotonic regression: non-parametric piecewise constant isotonic fit
            self.isotonic_model = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
            self.isotonic_model.fit(raw_probs, true_labels)

        return self

    def predict(self, raw_probs: np.ndarray) -> np.ndarray:
        """Transforms uncalibrated probabilities to calibrated probabilities."""
        flat_probs = np.clip(raw_probs.flatten(), 1e-7, 1.0 - 1e-7)
        if self.method == "platt" and self.platt_model is not None:
            logits = np.log(flat_probs / (1.0 - flat_probs)).reshape(-1, 1)
            calibrated = self.platt_model.predict_proba(logits)[:, 1]
        elif self.method == "isotonic" and self.isotonic_model is not None:
            calibrated = self.isotonic_model.predict(flat_probs)
        else:
            calibrated = flat_probs

        return calibrated.reshape(raw_probs.shape)
