"""The in-memory typed graph and its on-disk persistence.

Wraps a ``networkx.MultiDiGraph`` so traversal algorithms (neighbours, shortest
path, reachability) come for free, and serialises to a *canonical* ``graph.json``
so an unchanged repo round-trips byte-for-byte (AC-1.2). Determinism is enforced
at save time by sorting nodes and edges — insertion order never leaks into the
file.
"""

from __future__ import annotations

import json
from pathlib import Path

import networkx as nx

from .model import Confidence, EdgeType, NodeType

GRAPH_DIRNAME = ".aspark-graph"
GRAPH_FILENAME = "graph.json"


class Graph:
    """Typed multigraph. Edge key is the edge type, so at most one edge of a
    given type exists between an ordered pair of nodes (deterministic dedupe)."""

    def __init__(self) -> None:
        self._g = nx.MultiDiGraph()

    # --- mutation ----------------------------------------------------------

    def add_node(self, node_id: str, node_type: NodeType, **attrs) -> str:
        clean = {k: v for k, v in attrs.items() if v is not None}
        self._g.add_node(node_id, type=NodeType(node_type).value, **clean)
        return node_id

    def add_edge(
        self,
        source: str,
        target: str,
        edge_type: EdgeType,
        confidence: Confidence,
        **attrs,
    ) -> None:
        clean = {k: v for k, v in attrs.items() if v is not None}
        self._g.add_edge(
            source,
            target,
            key=EdgeType(edge_type).value,
            type=EdgeType(edge_type).value,
            confidence=Confidence(confidence).value,
            **clean,
        )

    # --- access ------------------------------------------------------------

    @property
    def nx(self) -> nx.MultiDiGraph:
        """The underlying networkx graph, for query algorithms."""
        return self._g

    def has_node(self, node_id: str) -> bool:
        return self._g.has_node(node_id)

    def get_node(self, node_id: str) -> dict | None:
        if not self._g.has_node(node_id):
            return None
        return {"id": node_id, **self._g.nodes[node_id]}

    def nodes(self, node_type: NodeType | None = None) -> list[dict]:
        want = NodeType(node_type).value if node_type is not None else None
        out = []
        for nid, data in self._g.nodes(data=True):
            if want is None or data.get("type") == want:
                out.append({"id": nid, **data})
        return sorted(out, key=lambda n: n["id"])

    def edges(self) -> list[dict]:
        out = []
        for src, dst, data in self._g.edges(data=True):
            out.append({"source": src, "target": dst, **data})
        return _sorted_edges(out)

    def out_edges(self, node_id: str, edge_type: EdgeType | None = None) -> list[tuple[str, dict]]:
        """Outgoing (target, data) pairs, optionally filtered by edge type."""
        if not self._g.has_node(node_id):
            return []
        want = EdgeType(edge_type).value if edge_type is not None else None
        out = [
            (dst, data)
            for _, dst, data in self._g.out_edges(node_id, data=True)
            if want is None or data.get("type") == want
        ]
        return sorted(out, key=lambda e: (e[1].get("type", ""), e[0]))

    def in_edges(self, node_id: str, edge_type: EdgeType | None = None) -> list[tuple[str, dict]]:
        """Incoming (source, data) pairs, optionally filtered by edge type."""
        if not self._g.has_node(node_id):
            return []
        want = EdgeType(edge_type).value if edge_type is not None else None
        out = [
            (src, data)
            for src, _, data in self._g.in_edges(node_id, data=True)
            if want is None or data.get("type") == want
        ]
        return sorted(out, key=lambda e: (e[1].get("type", ""), e[0]))

    def counts(self) -> dict[str, int]:
        """Node counts split into the two layers the build command reports."""
        code_types = {NodeType.FILE.value, NodeType.CLASS.value, NodeType.FUNCTION.value}
        code = artifact = 0
        for _, data in self._g.nodes(data=True):
            if data.get("type") in code_types:
                code += 1
            else:
                artifact += 1
        return {"code": code, "artifact": artifact, "edges": self._g.number_of_edges()}

    # --- persistence -------------------------------------------------------

    def to_dict(self) -> dict:
        """Canonical, sorted representation — the byte-stability contract."""
        return {"nodes": self.nodes(), "edges": self.edges()}

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(self.to_dict(), indent=2, ensure_ascii=False, sort_keys=True)
        path.write_text(text + "\n", encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: str | Path) -> "Graph":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        g = cls()
        for node in data.get("nodes", []):
            node = dict(node)
            nid = node.pop("id")
            ntype = node.pop("type")
            g.add_node(nid, NodeType(ntype), **node)
        for edge in data.get("edges", []):
            edge = dict(edge)
            src = edge.pop("source")
            dst = edge.pop("target")
            etype = edge.pop("type")
            conf = edge.pop("confidence")
            g.add_edge(src, dst, EdgeType(etype), Confidence(conf), **edge)
        return g


def _sorted_edges(edges: list[dict]) -> list[dict]:
    return sorted(edges, key=lambda e: (e["source"], e["target"], e.get("type", "")))


def default_graph_path(repo_root: str | Path) -> Path:
    return Path(repo_root) / GRAPH_DIRNAME / GRAPH_FILENAME
