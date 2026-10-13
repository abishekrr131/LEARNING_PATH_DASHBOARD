"""Learning Path Planning and Dynamic Prerequisite Insertion Service.

Implements Section 9.3 and Section 29 of the RCT-GAT Specification:
- Dynamic insertion of predicted root causes ahead of surface concept
- Topological ordering enforcement (prerequisites must strictly precede dependents)
"""
from __future__ import annotations

from typing import Any
from ml.graph.dag_validator import (
    SimpleDiGraph,
    find_cycle,
    is_directed_acyclic_graph,
    topological_sort,
)


def insert_remediation(
    path: list[int],
    surface_id: int,
    root_cause_id: int,
    graph: Any = None,
) -> list[int]:
    """Put the root cause immediately before the concept it explains (Spec Section 29).

    Examples:
        >>> g = SimpleDiGraph([(1, 2), (2, 3)])
        >>> insert_remediation([3, 4, 5], surface_id=3, root_cause_id=2, graph=g)
        [2, 3, 4, 5]
        >>> insert_remediation([2, 3], surface_id=3, root_cause_id=2, graph=g)
        [2, 3]
        >>> insert_remediation([1, 3, 4], surface_id=3, root_cause_id=2, graph=g)
        [1, 2, 3, 4]
    """
    if surface_id not in path:
        return path
    if surface_id == root_cause_id:
        return list(path)

    surface_index = path.index(surface_id)
    # If root_cause_id is already in path and scheduled before surface_id:
    if root_cause_id in path[:surface_index]:
        return list(path)

    out = [c for c in path if c != root_cause_id]
    surface_new_idx = out.index(surface_id)
    out.insert(surface_new_idx, root_cause_id)
    return out


def topological_order(graph: Any, concept_ids: list[int]) -> list[int]:
    """No concept may precede its own prerequisites. This is a hard constraint.

    Examples:
        >>> g = SimpleDiGraph([(1, 2), (2, 3), (1, 3)])
        >>> topological_order(g, [3, 2, 1])
        [1, 2, 3]
    """
    sub = graph.subgraph(concept_ids)
    if not is_directed_acyclic_graph(sub):
        cycle = find_cycle(sub)
        raise ValueError(f"cycle in path subgraph: {cycle}")
    
    # Topological sort of the subgraph nodes
    ordered = topological_sort(sub)
    ordered_set = set(ordered)
    # Ensure all original nodes are returned
    result = [c for c in ordered if c in set(concept_ids)]
    missing = [c for c in concept_ids if c not in ordered_set]
    return result + missing


def build_curriculum_path(
    graph: Any,
    all_target_concept_ids: list[int],
    mastered_concept_ids: set[int] | None = None,
    remediations: list[tuple[int, int]] | None = None,
) -> list[dict[str, Any]]:
    """Generates an ordered curriculum path with state markings:
    - completed: mastered
    - in_progress / remediation: active concepts
    - locked: unmet prerequisites

    remediations: list of (surface_id, root_cause_id) pairs
    """
    mastered = mastered_concept_ids or set()
    ordered_ids = topological_order(graph, all_target_concept_ids)

    # Apply any active remediations
    if remediations:
        for surface_id, root_cause_id in remediations:
            if surface_id in ordered_ids and root_cause_id in all_target_concept_ids:
                ordered_ids = insert_remediation(ordered_ids, surface_id, root_cause_id, graph)

    path_items = []
    first_incomplete_found = False

    for order_idx, c_id in enumerate(ordered_ids):
        preds = set(graph.predecessors(c_id)) if hasattr(graph, "predecessors") else set()
        unmet_preds = [p for p in preds if p in all_target_concept_ids and p not in mastered]

        is_completed = c_id in mastered
        if is_completed:
            status = "completed"
        elif not unmet_preds:
            if not first_incomplete_found:
                status = "in_progress"
                first_incomplete_found = True
            else:
                status = "available"
        else:
            status = "locked"

        path_items.append({
            "concept_id": c_id,
            "order_index": order_idx,
            "status": status,
            "unmet_prerequisites": unmet_preds,
        })

    return path_items


def build_personalized_path(
    g: Any,
    concept_names: dict[int, str],
    weak_concept_ids: list[int],
    remediation_prereq_ids: list[int] | None = None,
    limit: int = 15,
) -> list[dict[str, Any]]:
    """Builds a personalized topological roadmap prioritizing weak concepts and root cause prerequisites."""
    all_nodes = list(concept_names.keys())
    if not all_nodes:
        return []

    try:
        ordered = topological_order(g, all_nodes)
    except Exception:
        ordered = all_nodes

    remediation_set = set(remediation_prereq_ids or [])
    weak_set = set(weak_concept_ids)

    # Insert remediations before surface concepts
    if remediation_prereq_ids and weak_concept_ids:
        for s_id in weak_concept_ids:
            for r_id in remediation_prereq_ids:
                if s_id != r_id and s_id in ordered and r_id in ordered:
                    ordered = insert_remediation(ordered, s_id, r_id, g)

    nodes_out = []
    for idx, cid in enumerate(ordered[:limit]):
        is_rem = cid in remediation_set
        is_weak = cid in weak_set
        nodes_out.append({
            "concept_id": cid,
            "concept_name": concept_names.get(cid, f"Concept {cid}"),
            "step_order": idx + 1,
            "is_remediation": is_rem,
            "is_weak": is_weak,
            "status": "remediation" if is_rem else ("priority" if is_weak else "standard"),
        })
    return nodes_out
