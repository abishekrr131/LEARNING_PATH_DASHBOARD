"""Tests for IRT Calibration, Platt Scaling, and Isotonic Calibration (Spec §27)."""
from __future__ import annotations

import numpy as np
import pytest

from ml.irt.calibration import (
    fit_1pl_rasch_difficulties,
    ProbabilityCalibrator,
)


def test_fit_1pl_rasch_difficulties():
    # Synthetic response matrix: 100 learners x 4 items
    # Item 0 is very easy (p=0.9), Item 1 is medium (p=0.5), Item 2 is hard (p=0.1)
    np.random.seed(42)
    N = 150
    items = [101, 102, 103, 104]

    y0 = np.random.binomial(1, 0.90, N)
    y1 = np.random.binomial(1, 0.65, N)
    y2 = np.random.binomial(1, 0.35, N)
    y3 = np.random.binomial(1, 0.10, N)

    matrix = np.column_stack([y0, y1, y2, y3])

    difficulties = fit_1pl_rasch_difficulties(matrix, items)

    assert len(difficulties) == 4
    # Easy item should have lower difficulty b than hard item
    assert difficulties[101] < difficulties[102] < difficulties[103] < difficulties[104]

    # Mean difficulty is centered at 0.0
    mean_b = np.mean(list(difficulties.values()))
    assert np.isclose(mean_b, 0.0, atol=1e-3)


def test_platt_scaling_calibrator():
    np.random.seed(42)
    # Generate poorly calibrated probabilities (overconfident)
    raw_probs = np.random.uniform(0.1, 0.9, 100)
    true_labels = (raw_probs > 0.5).astype(int)

    calibrator = ProbabilityCalibrator(method="platt")
    calibrator.fit(raw_probs, true_labels)

    test_probs = np.array([0.2, 0.5, 0.8])
    calibrated = calibrator.predict(test_probs)

    assert calibrated.shape == (3,)
    assert (calibrated >= 0.0).all() and (calibrated <= 1.0).all()
    # Monotonically increasing
    assert calibrated[0] < calibrated[1] < calibrated[2]


def test_isotonic_calibrator():
    np.random.seed(42)
    raw_probs = np.random.uniform(0.1, 0.9, 100)
    true_labels = (raw_probs > 0.45).astype(int)

    calibrator = ProbabilityCalibrator(method="isotonic")
    calibrator.fit(raw_probs, true_labels)

    test_probs = np.array([0.1, 0.5, 0.9])
    calibrated = calibrator.predict(test_probs)

    assert calibrated.shape == (3,)
    assert (calibrated >= 0.0).all() and (calibrated <= 1.0).all()
    assert calibrated[0] <= calibrated[1] <= calibrated[2]
