"""Unit tests for scoring, root cause, and path planning services."""
import pytest
from backend.app.services.scoring import (
    adaptive_priority,
    expected_response_time,
    gap_band,
    gap_score,
    mastery_decay,
    readiness_score,
    review_interval,
    time_penalty,
    time_ratio,
)
from backend.app.services.root_cause import (
    attention_entropy,
    get_ancestors_within_hops,
    present_as_mode,
    rank_root_cause_candidates,
    select_verification_probes,
)
from backend.app.services.path import (
    build_curriculum_path,
    insert_remediation,
    topological_order,
)
from ml.graph.dag_validator import SimpleDiGraph


def test_scoring_formulas_exact():
    # F10
    assert expected_response_time(-1.0) == 45.0
    assert expected_response_time(0.0) == 60.0
    assert expected_response_time(1.2) == 90.0

    # F11
    tr = time_ratio(142000, 95.0)
    assert abs(tr - 1.4947) < 0.01

    # Time penalty
    assert time_penalty(0.5) == 0.0
    assert abs(time_penalty(1.49) - 0.245) < 0.001
    assert time_penalty(4.0) == 1.0

    # F12: Worked example from Spec
    g = gap_score(accuracy=0.35, time_ratio_val=1.49, skip_rate=0.25, hist_mastery=0.40)
    assert abs(g - 0.479) < 0.005
    assert gap_band(g) == "moderate"
    assert gap_band(0.20) == "strong"
    assert gap_band(0.65) == "weak"

    # F14: Worked example from Spec
    pri = adaptive_priority(gap=0.479, days_to_target=40, skill_weight=0.30, dag_distance=0, horizon=120)
    assert abs(pri - 0.096) < 0.005

    # F15: Mastery decay
    m_decay, half_life = mastery_decay(0.80, 21.0, tau=60.0)
    assert abs(m_decay - 0.564) < 0.005
    assert abs(half_life - 41.6) < 0.1

    # F16: Review interval
    dt_rev = review_interval(0.80, 0.60, tau=60.0)
    assert abs(dt_rev - 17.3) < 0.1


def test_root_cause_honesty_guard():
    # Worked example: alpha = [0.61, 0.25, 0.14] -> H_bar = 0.84 -> two_candidates
    h, h_bar = attention_entropy([0.61, 0.25, 0.14])
    assert abs(h - 0.923) < 0.005
    assert abs(h_bar - 0.84) < 0.01
    assert present_as_mode(h_bar) == "two_candidates"

    # Confident attribution: alpha = [0.95, 0.03, 0.02] -> H_bar < 0.7 -> single_cause
    _, h_bar_conf = attention_entropy([0.95, 0.03, 0.02])
    assert h_bar_conf < 0.70
    assert present_as_mode(h_bar_conf) == "single_cause"


def test_ancestor_search_and_ranking():
    g = SimpleDiGraph([(1, 2), (2, 3), (4, 3)])
    anc = get_ancestors_within_hops(g, 3, max_hops=2)
    assert anc == {2: 1, 4: 1, 1: 2}

    ranked = rank_root_cause_candidates(
        surface_concept_id=3,
        ancestors_with_hops=anc,
        concept_mastery={1: 0.8, 2: 0.2, 4: 0.6},
        concept_names={1: "C1", 2: "C2", 4: "C4"},
    )
    assert len(ranked) == 3
    # Candidate 2 has lowest mastery (0.2) and is 1 hop away -> should be top ranked
    assert ranked[0]["candidate_concept_id"] == 2
    assert ranked[0]["rank"] == 1


def test_verification_probes_epsilon_branch():
    import random
    rng = random.Random(42)
    # Target concepts: 1..10, weak: [2, 3]
    probes = select_verification_probes(
        weak_concept_ids=[2, 3],
        all_target_concept_ids=list(range(1, 11)),
        epsilon=0.10,
        rng=rng,
    )
    # Must contain the two suspected gaps
    triggers = {p[0]: p[1] for p in probes}
    assert triggers[2] == "suspected_gap"
    assert triggers[3] == "suspected_gap"


def test_path_insertion_and_cycle_prevention():
    g = SimpleDiGraph([(1, 2), (2, 3)])
    # Path without root cause
    p1 = insert_remediation([3, 4, 5], surface_id=3, root_cause_id=2, graph=g)
    assert p1 == [2, 3, 4, 5]

    # Path where root cause already precedes
    p2 = insert_remediation([2, 3, 4], surface_id=3, root_cause_id=2, graph=g)
    assert p2 == [2, 3, 4]

    # Topological order
    ordered = topological_order(g, [3, 1, 2])
    assert ordered == [1, 2, 3]

    # Cycle in path must raise ValueError
    g_cycle = SimpleDiGraph([(1, 2), (2, 1)])
    with pytest.raises(ValueError):
        topological_order(g_cycle, [1, 2])
