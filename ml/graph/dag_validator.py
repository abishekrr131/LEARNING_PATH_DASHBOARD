"""DAG Validation and Graph Traversal Utilities
Provides NetworkX integration with pure-Python fallbacks for DAG validation,
cycle finding, topological sorting, and ancestor search.
"""
from __future__ import annotations
from typing import Any, Iterable

try:
    import networkx as nx
    HAS_NX = True
except ImportError:
    HAS_NX = False
    nx = None


class SimpleDiGraph:
    """Lightweight pure-Python directed graph compatible with NetworkX DiGraph API."""

    def __init__(self, incoming_graph_data: Iterable[tuple[Any, Any]] | None = None):
        self._adj: dict[Any, dict[Any, dict[str, Any]]] = {}
        self._pred: dict[Any, dict[Any, dict[str, Any]]] = {}
        if incoming_graph_data is not None:
            for edge in incoming_graph_data:
                u, v = edge[0], edge[1]
                w = edge[2] if len(edge) > 2 else 1.0
                self.add_edge(u, v, weight=w)

    def add_node(self, n: Any) -> None:
        if n not in self._adj:
            self._adj[n] = {}
            self._pred[n] = {}

    def add_edge(self, u: Any, v: Any, weight: float = 1.0) -> None:
        self.add_node(u)
        self.add_node(v)
        self._adj[u][v] = {"weight": weight}
        self._pred[v][u] = {"weight": weight}

    def successors(self, n: Any) -> list[Any]:
        return list(self._adj.get(n, {}).keys())

    def predecessors(self, n: Any) -> list[Any]:
        return list(self._pred.get(n, {}).keys())

    @property
    def nodes(self) -> list[Any]:
        return list(self._adj.keys())

    def reverse(self, copy: bool = True) -> SimpleDiGraph:
        rev = SimpleDiGraph()
        for u in self._adj:
            rev.add_node(u)
            for v, attr in self._adj[u].items():
                rev.add_edge(v, u, weight=attr.get("weight", 1.0))
        return rev

    def subgraph(self, nodes: Iterable[Any]) -> SimpleDiGraph:
        node_set = set(nodes)
        sub = SimpleDiGraph()
        for u in node_set:
            if u in self._adj:
                sub.add_node(u)
                for v, attr in self._adj[u].items():
                    if v in node_set:
                        sub.add_edge(u, v, weight=attr.get("weight", 1.0))
        return sub


def is_directed_acyclic_graph(g: Any) -> bool:
    """Checks whether the directed graph is a DAG."""
    if HAS_NX and isinstance(g, nx.DiGraph):
        return nx.is_directed_acyclic_graph(g)
    
    # Pure Python DFS cycle detection
    # 0 = unvisited, 1 = visiting (in call stack), 2 = visited
    state: dict[Any, int] = {n: 0 for n in g.nodes}

    def dfs(node: Any) -> bool:
        state[node] = 1
        for neighbor in g.successors(node):
            n_state = state.get(neighbor, 0)
            if n_state == 1:
                return False  # Back-edge found -> cycle!
            if n_state == 0 and not dfs(neighbor):
                return False
        state[node] = 2
        return True

    for node in g.nodes:
        if state[node] == 0:
            if not dfs(node):
                return False
    return True


def find_cycle(g: Any) -> list[tuple[Any, Any]]:
    """Returns a cycle as a list of edge tuples if one exists."""
    if HAS_NX and isinstance(g, nx.DiGraph):
        return nx.find_cycle(g)

    visited = set()
    stack = []
    stack_set = set()

    def dfs(node: Any) -> list[tuple[Any, Any]] | None:
        visited.add(node)
        stack.append(node)
        stack_set.add(node)

        for neighbor in g.successors(node):
            if neighbor in stack_set:
                idx = stack.index(neighbor)
                cycle_nodes = stack[idx:] + [neighbor]
                return [(cycle_nodes[i], cycle_nodes[i + 1]) for i in range(len(cycle_nodes) - 1)]
            if neighbor not in visited:
                res = dfs(neighbor)
                if res is not None:
                    return res

        stack.pop()
        stack_set.remove(node)
        return None

    for n in g.nodes:
        if n not in visited:
            c = dfs(n)
            if c:
                return c
    return []


def topological_sort(g: Any) -> list[Any]:
    """Computes a topological sort of nodes using Kahn's algorithm."""
    if HAS_NX and isinstance(g, nx.DiGraph):
        return list(nx.topological_sort(g))

    in_degree = {n: len(g.predecessors(n)) for n in g.nodes}
    queue = [n for n, deg in in_degree.items() if deg == 0]
    order = []

    while queue:
        n = queue.pop(0)
        order.append(n)
        for s in g.successors(n):
            in_degree[s] -= 1
            if in_degree[s] == 0:
                queue.append(s)

    if len(order) != len(g.nodes):
        raise ValueError("Graph contains a cycle; topological sort impossible.")
    return order


# Make DiGraph alias available
def create_graph(edges=None):
    if HAS_NX:
        return nx.DiGraph(edges) if edges else nx.DiGraph()
    return SimpleDiGraph(edges)
