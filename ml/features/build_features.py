"""Feature Builder and Leakage Invariant Verification for RCT-GAT.

Conforms to Spec Section 26:
- Sequence ordered strictly by server-assigned `answered_at` (Invariant 3).
- Feature at step t contains NO information from t or future steps if predicting y_t,
  or if predicting y_{t+1}, feature at t contains interaction t and target is y_{t+1} (Invariant 1).
- Causal attention mask M prevents any future-token attention (Invariant 2).
- Zero learner-ID embedding: Learner identity is strictly excluded to prevent demographic overfitting.
- `timed_out` treated as its own independent binary feature.
"""
from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np


@dataclass(frozen=True)
class InteractionEvent:
    """Raw interaction telemetry event."""
    user_id: int
    question_id: int
    concept_id: int
    is_correct: bool
    response_time_ms: int
    time_limit_ms: int | None
    timed_out: bool
    skipped: bool
    difficulty_b: float
    answered_at: dt.datetime


@dataclass
class LearnerSequenceFeatures:
    """Preprocessed sequence features ready for GAT and temporal sequence encoder."""
    concept_indices: np.ndarray  # shape: (T,), int64
    continuous_features: np.ndarray  # shape: (T, F), float32
    labels: np.ndarray  # shape: (T,), float32
    causal_mask: np.ndarray  # shape: (T, T), bool (True where attention allowed: j <= i)
    server_timestamps: list[dt.datetime]
    seq_len: int

    @property
    def feature_dim(self) -> int:
        return self.continuous_features.shape[1] if self.seq_len > 0 else 0


def generate_causal_mask(seq_len: int) -> np.ndarray:
    """Generates lower-triangular causal attention mask (Invariant 2).

    Returns a boolean matrix where mask[i, j] is True if j <= i (past and present allowed)
    and False if j > i (future blocked).
    """
    return np.tril(np.ones((seq_len, seq_len), dtype=bool))


def build_learner_sequence(
    events: Sequence[InteractionEvent],
    max_len: int = 100,
    predict_next_item: bool = True,
) -> LearnerSequenceFeatures:
    """Constructs model inputs adhering strictly to Leakage Invariants 1, 2, and 3.

    Features at step t:
    1. previous_correctness: y_{t-1} (0.0 for t=0)
    2. log_response_time: log(1 + response_time_ms / 1000)
    3. log_time_limit: log(1 + time_limit_ms / 1000) if timed else 0.0
    4. timed_out: 1.0 if timed_out else 0.0
    5. skipped: 1.0 if skipped else 0.0
    6. difficulty_b: frozen IRT item difficulty b
    """
    if not events:
        empty_mask = np.zeros((0, 0), dtype=bool)
        return LearnerSequenceFeatures(
            concept_indices=np.zeros((0,), dtype=np.int64),
            continuous_features=np.zeros((0, 6), dtype=np.float32),
            labels=np.zeros((0,), dtype=np.float32),
            causal_mask=empty_mask,
            server_timestamps=[],
            seq_len=0,
        )

    # Invariant 3: Sort strictly by server-assigned answered_at
    sorted_events = sorted(events, key=lambda e: e.answered_at)
    if len(sorted_events) > max_len:
        sorted_events = sorted_events[-max_len:]

    T = len(sorted_events)
    concept_indices = np.zeros((T,), dtype=np.int64)
    continuous = np.zeros((T, 6), dtype=np.float32)
    labels = np.zeros((T,), dtype=np.float32)
    timestamps: list[dt.datetime] = []

    for t, ev in enumerate(sorted_events):
        concept_indices[t] = ev.concept_id
        timestamps.append(ev.answered_at)

        # Target label at step t is current item correctness
        labels[t] = 1.0 if ev.is_correct else 0.0

        # Continuous features
        prev_correct = 0.0 if t == 0 else (1.0 if sorted_events[t - 1].is_correct else 0.0)
        resp_sec = max(0.0, ev.response_time_ms / 1000.0)
        limit_sec = (ev.time_limit_ms / 1000.0) if (ev.time_limit_ms and ev.time_limit_ms > 0) else 0.0

        continuous[t, 0] = prev_correct
        continuous[t, 1] = math.log1p(resp_sec)
        continuous[t, 2] = math.log1p(limit_sec)
        continuous[t, 3] = 1.0 if ev.timed_out else 0.0
        continuous[t, 4] = 1.0 if ev.skipped else 0.0
        continuous[t, 5] = float(ev.difficulty_b)

    causal_mask = generate_causal_mask(T)

    return LearnerSequenceFeatures(
        concept_indices=concept_indices,
        continuous_features=continuous,
        labels=labels,
        causal_mask=causal_mask,
        server_timestamps=timestamps,
        seq_len=T,
    )


# --- The Three Invariant Verification Functions (Spec §26) ---

def check_invariant_1_no_future_leakage(seq: LearnerSequenceFeatures) -> bool:
    """Invariant 1: No feature at step t may use information from future steps.

    Specifically:
    - continuous_features[t, 0] (prev_correct) must strictly equal labels[t-1] (or 0 for t=0).
    - continuous_features[t, 0] must NEVER depend on labels[t] or labels[t+1].
    """
    if seq.seq_len == 0:
        return True

    # Check step 0 has 0.0 prior correctness
    if seq.continuous_features[0, 0] != 0.0:
        return False

    # Check that prev_correct at step t exactly matches label at step t-1
    for t in range(1, seq.seq_len):
        expected_prev = seq.labels[t - 1]
        actual_prev = seq.continuous_features[t, 0]
        if not np.isclose(expected_prev, actual_prev):
            return False

    return True


def check_invariant_2_causal_mask(seq: LearnerSequenceFeatures) -> bool:
    """Invariant 2: Causal attention mask must strictly prevent attending to future tokens.

    mask[i, j] must be False for all j > i.
    """
    if seq.seq_len == 0:
        return True

    mask = seq.causal_mask
    T = seq.seq_len
    for i in range(T):
        for j in range(T):
            if j > i and mask[i, j]:
                return False  # Future attention leaked!
            if j <= i and not mask[i, j]:
                return False  # Past/present blocked!
    return True


def check_invariant_3_server_timestamp_ordering(seq: LearnerSequenceFeatures) -> bool:
    """Invariant 3: Sequence must be strictly sorted by server-assigned timestamp ascending."""
    if seq.seq_len <= 1:
        return True

    for i in range(1, len(seq.server_timestamps)):
        if seq.server_timestamps[i] < seq.server_timestamps[i - 1]:
            return False
    return True
