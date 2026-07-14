"""FastMCP stdio server — thin adapter over queries.py and build.py.

Every tool delegates to the same functions the CLI uses, so MCP and CLI answers
are identical by construction (AC-5.1). Tools return plain dicts; FastMCP
serialises them.
"""

from __future__ import annotations

from fastmcp import FastMCP

from . import queries
from .build import build_graph as _build_graph

mcp = FastMCP("aspark-graph")


@mcp.tool
def build_graph(path: str = ".") -> dict:
    """(Re)scan a repository and its .spark/ artifacts and persist the graph."""
    graph, report = _build_graph(path)
    out_path = graph.save(queries.default_graph_path(path))
    return {
        "code_entities": report.code_entities,
        "artifact_entities": report.artifact_entities,
        "unparsed": report.unparsed,
        "graph_path": str(out_path),
    }


@mcp.tool
def get_node(id: str, repo: str = ".") -> dict:
    """Look up a single node by its id (e.g. 'file:src/foo.py')."""
    return queries.get_node(queries.load_graph(repo), id)


@mcp.tool
def story_trace(story: str, feature: str | None = None, repo: str = ".") -> dict:
    """Full thread of a user story: acceptance criteria (with their latest QA
    verdict), mapped plan tasks, and any best-effort code links."""
    return queries.story_trace(queries.load_graph(repo), story, feature)


@mcp.tool
def impact(files: list[str] | None = None, diff: str | None = None, repo: str = ".") -> dict:
    """Blast radius of a change: the stories and acceptance criteria that depend
    on the given files (or the files in a git `diff` range), each tagged with its
    weakest-edge confidence. Pass either `files` or `diff`, not both."""
    graph = queries.load_graph(repo)
    if diff:
        if files:
            return {"found": False, "reason": "bad_args", "message": "pass either files or diff, not both"}
        return queries.impact_diff(graph, repo, diff)
    return queries.impact(graph, files or [])


@mcp.tool
def gate_health(feature: str, repo: str = ".") -> dict:
    """The aSPARK gate invariants as data: orphan tasks, unverified acceptance
    criteria, and open findings for a feature."""
    return queries.gate_health(queries.load_graph(repo), feature)


@mcp.tool
def staleness(repo: str = ".") -> dict:
    """Report whether the built graph still matches the repo on disk (US-4)."""
    return queries.staleness(queries.load_graph(repo), repo)


@mcp.tool
def find_nodes(query: str, type: str | None = None, repo: str = ".") -> dict:
    """Find nodes whose id or name contains a substring, optionally by type."""
    return queries.find_nodes(queries.load_graph(repo), query, type)


@mcp.tool
def get_neighbors(id: str, edge_types: list[str] | None = None, depth: int = 1, repo: str = ".") -> dict:
    """Nodes within `depth` hops of a node (both directions); 'what touches this?'."""
    return queries.get_neighbors(queries.load_graph(repo), id, edge_types, depth)


@mcp.tool
def shortest_path(a: str, b: str, repo: str = ".") -> dict:
    """An ordered path connecting two nodes, or an explicit 'no path' result."""
    return queries.shortest_path(queries.load_graph(repo), a, b)


def run() -> None:
    mcp.run()


if __name__ == "__main__":
    run()
