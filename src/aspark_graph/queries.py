"""The one shared query surface.

Both the CLI (`cli.py`) and the MCP server (`server.py`) are thin adapters over
these functions — they contain no query logic of their own. That is what makes
"the CLI and the MCP tool return the same answer" (AC-5.1) true by construction.

Every function takes a :class:`Graph` and returns a plain JSON-serialisable
dict, so serialisation is identical across both adapters.
"""

from __future__ import annotations

from pathlib import Path

from .graph import Graph, default_graph_path
from .model import Confidence, EdgeType, NodeType, feature_id, file_id


class GraphNotBuiltError(Exception):
    """No graph.json exists yet — the caller must build first (AC-5.2)."""


def load_graph(repo_root: str | Path) -> Graph:
    path = default_graph_path(repo_root)
    if not path.exists():
        raise GraphNotBuiltError(
            f"No graph found at {path}. Run 'aspark-graph build' first."
        )
    return Graph.load(path)


def get_node(graph: Graph, node_id: str) -> dict:
    node = graph.get_node(node_id)
    if node is None:
        return {"found": False, "id": node_id}
    return {"found": True, "node": node}


def _resolve_story(graph: Graph, story: str, feature: str | None) -> tuple[str | None, list[str]]:
    """Resolve a story argument to a node id. Returns (id, candidates).

    Accepts a full node id (``story:feat:US-1``) or a bare ``US-1``; with a bare
    id across multiple features, returns all candidates so the caller can report
    the ambiguity rather than guessing.
    """
    if graph.has_node(story) and graph.get_node(story)["type"] == NodeType.STORY.value:
        return story, [story]
    candidates = [
        n["id"]
        for n in graph.nodes(NodeType.STORY)
        if n.get("story") == story and (feature is None or n.get("feature") == feature)
    ]
    if len(candidates) == 1:
        return candidates[0], candidates
    return None, candidates


def story_trace(graph: Graph, story: str, feature: str | None = None) -> dict:
    """Full thread of a story: ACs (+latest QA verdict), tasks (+best-effort code)."""
    story_node_id, candidates = _resolve_story(graph, story, feature)
    if story_node_id is None:
        if candidates:
            return {"found": False, "story": story, "reason": "ambiguous", "candidates": sorted(candidates)}
        return {"found": False, "story": story, "reason": "not_found"}

    node = graph.get_node(story_node_id)
    result = {
        "found": True,
        "story": {
            "id": story_node_id,
            "story": node.get("story"),
            "title": node.get("title"),
            "moscow": node.get("moscow"),
            "feature": node.get("feature"),
        },
        "acceptance_criteria": [],
        "tasks": [],
    }

    # ACs (has_ac) with their most-recent QA verdict (verifies, incoming).
    for ac_node_id, _ in graph.out_edges(story_node_id, EdgeType.HAS_AC):
        ac = graph.get_node(ac_node_id)
        qa_checks = [graph.get_node(src) for src, _ in graph.in_edges(ac_node_id, EdgeType.VERIFIES)]
        latest = _latest_qa(qa_checks)
        result["acceptance_criteria"].append({
            "id": ac_node_id,
            "ac": ac.get("ac"),
            "text": ac.get("text"),
            "qa_checks": [{"result": q.get("result"), "date": q.get("date"), "order": q.get("order")} for q in _sorted_qa(qa_checks)],
            "latest_result": latest.get("result") if latest else None,
        })

    # Tasks (maps_to, incoming) with best-effort code links (implements).
    for task_node_id, _ in graph.in_edges(story_node_id, EdgeType.MAPS_TO):
        task = graph.get_node(task_node_id)
        code = [
            {"id": tgt, "type": graph.get_node(tgt).get("type"), "confidence": data.get("confidence")}
            for tgt, data in graph.out_edges(task_node_id, EdgeType.IMPLEMENTS)
        ]
        result["tasks"].append({
            "id": task_node_id,
            "task": task.get("task"),
            "status": task.get("status"),
            "code": code,  # empty when the task has no explicit reference (expected; AC-2.4)
        })

    result["acceptance_criteria"].sort(key=lambda a: a["id"])
    result["tasks"].sort(key=lambda t: t["id"])
    return result


# --- impact ----------------------------------------------------------------
# Impact propagates from a changed file outward to the stories/ACs that depend
# on it. The only code->artifact bridge is the best-effort `implements` edge; a
# file with no `implements` path (the common case in v0.1.0) correctly reports
# no affected stories — that omission is expected, not a dropped link (AC-3.2).

_IMPACT_STEPS = {
    NodeType.FILE.value: [(EdgeType.IMPORTS, "in"), (EdgeType.CONTAINS, "out"), (EdgeType.IMPLEMENTS, "in")],
    NodeType.CLASS.value: [(EdgeType.IMPLEMENTS, "in"), (EdgeType.CONTAINS, "out")],
    NodeType.FUNCTION.value: [(EdgeType.IMPLEMENTS, "in"), (EdgeType.CONTAINS, "out")],
    NodeType.TASK.value: [(EdgeType.MAPS_TO, "out")],
    NodeType.STORY.value: [(EdgeType.HAS_AC, "out")],
}
_RANK_CONF = {c.rank(): c.value for c in Confidence}


def _impact_steps(graph: Graph, node_id: str):
    node = graph.get_node(node_id)
    for edge_type, direction in _IMPACT_STEPS.get(node.get("type"), []):
        edges = graph.in_edges(node_id, edge_type) if direction == "in" else graph.out_edges(node_id, edge_type)
        for other, data in edges:
            yield other, Confidence(data["confidence"]).rank()


def _reach(graph: Graph, seed: str) -> dict[str, int]:
    """Widest-path (max-bottleneck) reachability: best[node] is the strongest
    weakest-edge confidence over all paths from ``seed``."""
    inf = max(_RANK_CONF) + 1
    unseen = min(_RANK_CONF) - 1  # sentinel below every real rank (inferred=0)
    best = {seed: inf}
    queue = [seed]
    while queue:
        node = queue.pop()
        base = best[node]
        for nbr, erank in _impact_steps(graph, node):
            cand = min(base, erank)
            if cand > best.get(nbr, unseen):
                best[nbr] = cand
                queue.append(nbr)
    return best


def impact(graph: Graph, files: list[str]) -> dict:
    """Blast radius of changing ``files``: affected stories and ACs, each tagged
    with the weakest-edge confidence on its strongest path (AC-3.5)."""
    per_file = []
    unknown = []
    agg_stories: dict[str, int] = {}
    agg_acs: dict[str, int] = {}

    for raw in files:
        rel = _normalise_path(raw)
        fid = file_id(rel)
        if not graph.has_node(fid):
            unknown.append(raw)
            continue
        best = _reach(graph, fid)
        stories, acs = {}, {}
        for nid, rank in best.items():
            if nid == fid:
                continue
            ntype = graph.get_node(nid).get("type")
            if ntype == NodeType.STORY.value:
                stories[nid] = rank
                agg_stories[nid] = max(agg_stories.get(nid, 0), rank)
            elif ntype == NodeType.ACCEPTANCE_CRITERION.value:
                acs[nid] = rank
                agg_acs[nid] = max(agg_acs.get(nid, 0), rank)
        code_entities = sorted(tgt for tgt, _ in graph.out_edges(fid, EdgeType.CONTAINS))
        entry = {
            "path": rel,
            "in_graph": True,
            "code_entities": code_entities,
            "affected_stories": _confidence_list(graph, stories, "story"),
            "affected_acs": _confidence_list(graph, acs, "ac"),
        }
        if not stories and not acs:
            entry["note"] = "no affected stories or acceptance criteria"
        per_file.append(entry)

    return {
        "found": True,
        "files": sorted(per_file, key=lambda f: f["path"]),
        "unknown_files": sorted(unknown),
        "affected_stories": _confidence_list(graph, agg_stories, "story"),
        "affected_acs": _confidence_list(graph, agg_acs, "ac"),
    }


def _confidence_list(graph: Graph, ranked: dict[str, int], key_attr: str) -> list[dict]:
    out = []
    for nid, rank in ranked.items():
        node = graph.get_node(nid)
        item = {"id": nid, "confidence": _RANK_CONF[rank]}
        item[key_attr] = node.get(key_attr)
        if key_attr == "ac":
            item["story"] = node.get("story")
        out.append(item)
    return sorted(out, key=lambda x: x["id"])


def _normalise_path(raw: str) -> str:
    p = raw.strip().replace("\\", "/")
    if p.startswith("./"):
        p = p[2:]
    return p


# --- gate health (US-6) ----------------------------------------------------

def gate_health(graph: Graph, feature: str) -> dict:
    """The aSPARK gate invariants as data: orphan tasks, unverified ACs, open
    findings for a feature."""
    name = feature.split(":", 1)[1] if feature.startswith("feature:") else feature
    fid = feature_id(name)
    if not graph.has_node(fid):
        return {"found": False, "feature": name, "reason": "not_found"}

    orphan_tasks = []
    for node in graph.nodes(NodeType.TASK):
        if node.get("feature") != name:
            continue
        if not graph.out_edges(node["id"], EdgeType.MAPS_TO):  # AC-6.1
            orphan_tasks.append({"id": node["id"], "task": node.get("task"), "status": node.get("status")})

    unverified_acs = []
    for node in graph.nodes(NodeType.ACCEPTANCE_CRITERION):
        if node.get("feature") != name:
            continue
        qa = [graph.get_node(src) for src, _ in graph.in_edges(node["id"], EdgeType.VERIFIES)]
        if not any(q.get("result") == "pass" for q in qa):  # AC-6.2
            unverified_acs.append({"id": node["id"], "ac": node.get("ac"), "story": node.get("story")})

    open_findings = []
    for node in graph.nodes(NodeType.FINDING):
        if node.get("feature") != name:
            continue
        if (node.get("status") or "").lower() == "open":  # AC-6.3
            open_findings.append({
                "id": node["id"], "finding": node.get("finding"),
                "severity": node.get("severity"), "location": node.get("location"),
            })

    return {
        "found": True,
        "feature": name,
        "healthy": not (orphan_tasks or unverified_acs or open_findings),
        "orphan_tasks": sorted(orphan_tasks, key=lambda t: t["id"]),
        "unverified_acs": sorted(unverified_acs, key=lambda a: a["id"]),
        "open_findings": sorted(open_findings, key=lambda f: f["id"]),
    }


# --- general graph navigation (US-7) ---------------------------------------

_SEARCHABLE_ATTRS = ("name", "title", "story", "ac", "task", "finding")


def find_nodes(graph: Graph, query: str, type: str | None = None) -> dict:
    """Find nodes whose id or a searchable attribute contains ``query``."""
    q = query.lower()
    want = type.lower() if type else None
    matches = []
    for node in graph.nodes():
        if want and node["type"].lower() != want:
            continue
        haystacks = [node["id"]] + [str(node[a]) for a in _SEARCHABLE_ATTRS if node.get(a)]
        if any(q in h.lower() for h in haystacks):
            matches.append(node)
    return {"query": query, "type": type, "count": len(matches), "nodes": matches}


def get_neighbors(graph: Graph, node_id: str, edge_types: list[str] | None = None, depth: int = 1) -> dict:
    """Nodes within ``depth`` hops of ``node_id`` (both directions), optionally
    restricted to the given edge types. Answers 'what touches this?'."""
    if not graph.has_node(node_id):
        return {"found": False, "id": node_id, "reason": "not_found"}
    wanted = {e.lower() for e in edge_types} if edge_types else None
    seen = {node_id: 0}
    neighbours: dict[str, dict] = {}
    frontier = [node_id]
    for level in range(1, max(depth, 1) + 1):
        nxt = []
        for current in frontier:
            for other, data, direction in _both_edges(graph, current):
                if wanted is not None and data.get("type") not in wanted:
                    continue
                if other not in seen:
                    seen[other] = level
                    neighbours[other] = {
                        "id": other,
                        "type": graph.get_node(other).get("type"),
                        "edge": data.get("type"),
                        "direction": direction,
                        "depth": level,
                    }
                    nxt.append(other)
        frontier = nxt
        if not frontier:
            break
    return {
        "found": True,
        "id": node_id,
        "neighbors": sorted(neighbours.values(), key=lambda n: (n["depth"], n["id"])),
    }


def shortest_path(graph: Graph, a: str, b: str) -> dict:
    """An ordered path of nodes and edges connecting ``a`` and ``b`` (undirected),
    or an explicit 'no path' result."""
    import networkx as nx

    if not graph.has_node(a):
        return {"found": False, "reason": "not_found", "missing": a}
    if not graph.has_node(b):
        return {"found": False, "reason": "not_found", "missing": b}
    undirected = graph.nx.to_undirected(as_view=True)
    try:
        node_path = nx.shortest_path(undirected, a, b)
    except nx.NetworkXNoPath:
        return {"found": False, "reason": "no_path", "from": a, "to": b}
    steps = []
    for src, dst in zip(node_path, node_path[1:]):
        steps.append({"from": src, "to": dst, "edge": _edge_label(graph, src, dst)})
    return {"found": True, "from": a, "to": b, "nodes": node_path, "steps": steps}


def _both_edges(graph: Graph, node_id: str):
    for other, data in graph.out_edges(node_id):
        yield other, data, "out"
    for other, data in graph.in_edges(node_id):
        yield other, data, "in"


def _edge_label(graph: Graph, src: str, dst: str) -> str | None:
    for other, data in graph.out_edges(src):
        if other == dst:
            return data.get("type")
    for other, data in graph.in_edges(src):
        if other == dst:
            return data.get("type")
    return None


def _sorted_qa(qa_checks: list[dict]) -> list[dict]:
    return sorted(qa_checks, key=lambda q: ((q.get("date") or ""), q.get("order") or 0))


def _latest_qa(qa_checks: list[dict]) -> dict | None:
    ordered = _sorted_qa(qa_checks)
    return ordered[-1] if ordered else None
