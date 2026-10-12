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
    # Ensure all original nodes are returned
    return [c for c in ordered if c in set(concept_ids)]


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
