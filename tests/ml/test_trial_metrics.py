"""Tests for RCT Trial Effect Size (Cohen's d) and Synthetic Data Reporting Guard (Spec §11, Change 4)."""
from __future__ import annotations

import pytest
import numpy as np

from ml.experiments.metrics import (
    cohens_d,
    generate_trial_report,
    SyntheticDataReportError,
)


def test_cohens_d_calculation():
    # Synthetic group data
    np.random.seed(42)
    # Root-cause intervention group has higher learning gains
    rc_gains = list(np.random.normal(loc=0.35, scale=0.10, size=50))
    # Surface control group has lower learning gains
    surface_gains = list(np.random.normal(loc=0.15, scale=0.10, size=50))

    result = cohens_d(rc_gains, surface_gains)

    assert result["cohens_d"] > 1.5  # Large effect size
    assert result["statistically_significant"] is True
    assert result["p_value"] < 0.001
    assert result["mean_difference"] > 0.15
    ci_low, ci_high = result["ci_95"]
    assert ci_low < result["cohens_d"] < ci_high


def test_synthetic_data_reporting_guard_strictly_refuses():
    rc_gains = [0.3, 0.4, 0.5]
    surface_gains = [0.1, 0.2, 0.15]

    # Valid real trial report passes
    report = generate_trial_report(rc_gains, surface_gains, dataset_version="rct-gat-v1.0-live")
    assert "cohens_d" in report

    # Synthetic dataset versions must be STRICTLY REFUSED
    with pytest.raises(SyntheticDataReportError, match="Synthetic data labeled"):
        generate_trial_report(rc_gains, surface_gains, dataset_version="pipeline-test-synthetic")

    with pytest.raises(SyntheticDataReportError, match="Synthetic data labeled"):
        generate_trial_report(rc_gains, surface_gains, dataset_version="synthetic-debug-v1")
