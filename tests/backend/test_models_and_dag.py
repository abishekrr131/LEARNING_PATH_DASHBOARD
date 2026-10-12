import pytest
from ml.graph.dag_validator import create_graph, is_directed_acyclic_graph, find_cycle
from database.seed.seed_all import ALL_TARGETS


def test_all_seven_targets_present():
    assert len(ALL_TARGETS) == 7
    target_names = {t["target"]["name"] for t in ALL_TARGETS}
    expected = {
        "Machine Learning Engineering",
        "Full Stack Development",
        "Cyber Security",
        "Generative AI",
        "UPSC Civil Services",
        "SSC CGL",
        "Banking (IBPS PO)",
    }
    assert target_names == expected


@pytest.mark.parametrize("curriculum", ALL_TARGETS)
def test_skill_weights_sum_to_one(curriculum):
    skills = curriculum["skills"]
    total = sum(s["weight"] for s in skills)
    assert abs(total - 1.0) < 1e-6, f"{curriculum['target']['name']} skills must sum to 1.0"


@pytest.mark.parametrize("curriculum", ALL_TARGETS)
def test_prerequisite_graph_is_acyclic_dag(curriculum):
    g = create_graph()
    for p, d, w in curriculum["dependencies"]:
        g.add_edge(p, d, weight=w)
    
    assert is_directed_acyclic_graph(g), (
        f"Prerequisite cycle detected in {curriculum['target']['name']}: {find_cycle(g)}"
    )


@pytest.mark.parametrize("curriculum", ALL_TARGETS)
def test_concept_and_question_counts(curriculum):
    concepts_total = sum(len(c_list) for c_list in curriculum["concepts"].values())
    assert concepts_total >= 35, f"{curriculum['target']['name']} must have >= 35 concepts"

    questions_total = len(curriculum["questions"])
    assert questions_total >= 40, f"{curriculum['target']['name']} must have >= 40 questions"

    for q in curriculum["questions"]:
        assert len(q["options"]) == 4, "Every question must have 4 options"
        assert q["answer"] in q["options"], "Correct answer must be one of the 4 options"
        assert len(q["explanation"]) > 10, "Explanation must be present and substantive"


def test_dag_cycle_detector_catches_cycles():
    g = create_graph([("A", "B"), ("B", "C"), ("C", "A")])
    assert not is_directed_acyclic_graph(g)
    assert len(find_cycle(g)) == 3
