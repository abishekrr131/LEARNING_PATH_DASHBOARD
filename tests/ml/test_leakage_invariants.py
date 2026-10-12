"""Tests for ML Feature Builder and Leakage Invariants (Spec §26)."""
from __future__ import annotations

import datetime as dt
import pytest
import numpy as np

from ml.features.build_features import (
    InteractionEvent,
    build_learner_sequence,
    check_invariant_1_no_future_leakage,
    check_invariant_2_causal_mask,
    check_invariant_3_server_timestamp_ordering,
)


@pytest.fixture
def sample_events():
    t0 = dt.datetime(2026, 10, 12, 10, 0, 0, tzinfo=dt.timezone.utc)
    return [
        InteractionEvent(
            user_id=42,
            question_id=101,
            concept_id=1,
            is_correct=True,
            response_time_ms=12500,
            time_limit_ms=30000,
            timed_out=False,
            skipped=False,
            difficulty_b=0.25,
            answered_at=t0 + dt.timedelta(seconds=15),
        ),
        InteractionEvent(
            user_id=42,
            question_id=102,
            concept_id=2,
            is_correct=False,
            response_time_ms=29800,
            time_limit_ms=30000,
            timed_out=True,
            skipped=False,
            difficulty_b=0.85,
            answered_at=t0 + dt.timedelta(seconds=45),
        ),
        InteractionEvent(
            user_id=42,
            question_id=103,
            concept_id=3,
            is_correct=False,
            response_time_ms=1100,
            time_limit_ms=None,
            timed_out=False,
            skipped=True,
            difficulty_b=-0.10,
            answered_at=t0 + dt.timedelta(seconds=60),
        ),
        InteractionEvent(
            user_id=42,
            question_id=104,
            concept_id=4,
            is_correct=True,
            response_time_ms=8500,
            time_limit_ms=20000,
            timed_out=False,
            skipped=False,
            difficulty_b=0.15,
            answered_at=t0 + dt.timedelta(seconds=90),
        ),
    ]


def test_invariant_1_no_future_leakage(sample_events):
    seq = build_learner_sequence(sample_events)
    assert check_invariant_1_no_future_leakage(seq) is True

    # Col 0 at step 0 is 0.0
    assert seq.continuous_features[0, 0] == 0.0
    # Col 0 at step 1 is label from step 0 (1.0)
    assert seq.continuous_features[1, 0] == 1.0
    # Col 0 at step 2 is label from step 1 (0.0)
    assert seq.continuous_features[2, 0] == 0.0
    # Col 0 at step 3 is label from step 2 (0.0)
    assert seq.continuous_features[3, 0] == 0.0

    # Deliberate future leak injection: replace feature[1, 0] with future label[2]
    corrupted_features = seq.continuous_features.copy()
    corrupted_features[1, 0] = 999.0
    seq.continuous_features = corrupted_features
    assert check_invariant_1_no_future_leakage(seq) is False


def test_invariant_2_causal_mask(sample_events):
    seq = build_learner_sequence(sample_events)
    assert check_invariant_2_causal_mask(seq) is True

    T = seq.seq_len
    assert seq.causal_mask.shape == (T, T)

    # All upper-triangle entries must be False
    for i in range(T):
        for j in range(i + 1, T):
            assert not seq.causal_mask[i, j]

    # Corrupt mask by allowing attention from step 0 to step 2 (future)
    seq.causal_mask[0, 2] = True
    assert check_invariant_2_causal_mask(seq) is False


def test_invariant_3_server_timestamp_ordering(sample_events):
    # Feed events deliberately in scrambled order
    scrambled = [sample_events[2], sample_events[0], sample_events[3], sample_events[1]]
    seq = build_learner_sequence(scrambled)

    # Must be sorted ascending by server timestamp
    assert check_invariant_3_server_timestamp_ordering(seq) is True
    assert seq.server_timestamps[0] < seq.server_timestamps[1] < seq.server_timestamps[2] < seq.server_timestamps[3]

    # Corrupt timestamp order
    seq.server_timestamps[1] = seq.server_timestamps[0] - dt.timedelta(hours=1)
    assert check_invariant_3_server_timestamp_ordering(seq) is False


def test_timed_out_and_skip_independence(sample_events):
    seq = build_learner_sequence(sample_events)
    # Event 1 was timed_out
    assert seq.continuous_features[1, 3] == 1.0  # timed_out col
    assert seq.continuous_features[1, 4] == 0.0  # skipped col

    # Event 2 was skipped
    assert seq.continuous_features[2, 3] == 0.0  # timed_out col
    assert seq.continuous_features[2, 4] == 1.0  # skipped col


def test_zero_learner_id_leakage(sample_events):
    seq = build_learner_sequence(sample_events)
    # Ensure learner ID (42) does not appear in any feature column or concept indices
    assert 42 not in seq.concept_indices
    assert 42.0 not in seq.continuous_features
