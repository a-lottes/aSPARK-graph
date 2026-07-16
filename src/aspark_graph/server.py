"""FastMCP stdio server — thin adapter over queries.py and build.py.

Every tool delegates to the same functions the CLI uses, so MCP and CLI answers
are identical by construction (AC-5.1). Tools return plain dicts; FastMCP
serialises them.

Uses the official `mcp` SDK's FastMCP (a local stdio server, no auth/HTTP). See
pyproject for why `mcp` is capped below the version that pulls `cryptography`.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import queries
from .build import build_graph as _build_graph

mcp = FastMCP("aspark-graph")


@mcp.tool()
def build_graph(path: str = ".") -> dict:
    """(Re)scan a repository and its .spark/ artifacts and persist the graph."""
    graph, report = _build_graph(path)
    out_path = graph.save(queries.default_graph_path(path))
    return {
        "code_entities": report.code_entities,
        "artifact_entities": report.artifact_entities,
        "inferred_edges": report.inferred_edges,
        "unparsed": report.unparsed,
        "graph_path": str(out_path),
    }


def _open(repo: str):
    """Load the graph, or return a clean 'build first' error dict — parity with
    the CLI's AC-5.2 message so a query-before-build never raises a raw error to
    the MCP client (F3). Returns (graph, None) or (None, error_dict)."""
    try:
        return queries.load_graph(repo), None
    except queries.GraphNotBuiltError as exc:
        return None, {"found": False, "error": str(exc)}


@mcp.tool()
def get_node(id: str, repo: str = ".") -> dict:
    """Look up a single node by its id (e.g. 'file:src/foo.py')."""
    graph, err = _open(repo)
    return err or queries.get_node(graph, id)


@mcp.tool()
def story_trace(story: str, feature: str | None = None, repo: str = ".") -> dict:
    """Full thread of a user story: acceptance criteria (with their latest QA
    verdict), mapped plan tasks, and any best-effort code links."""
    graph, err = _open(repo)
    return err or queries.story_trace(graph, story, feature)


@mcp.tool()
def impact(files: list[str] | None = None, diff: str | None = None, repo: str = ".") -> dict:
    """Blast radius of a change: the stories and acceptance criteria that depend
    on the given files (or the files in a git `diff` range), each tagged with its
    weakest-edge confidence. Pass either `files` or `diff`, not both."""
    graph, err = _open(repo)
    if err:
        return err
    if diff:
        if files:
            return {"found": False, "reason": "bad_args", "message": "pass either files or diff, not both"}
        return queries.impact_diff(graph, repo, diff)
    return queries.impact(graph, files or [])


@mcp.tool()
def gate_health(feature: str, repo: str = ".") -> dict:
    """The aSPARK gate invariants as data: orphan tasks, unverified acceptance
    criteria, and open findings for a feature."""
    graph, err = _open(repo)
    return err or queries.gate_health(graph, feature)


@mcp.tool()
def staleness(repo: str = ".") -> dict:
    """Report whether the built graph still matches the repo on disk (US-4)."""
    graph, err = _open(repo)
    return err or queries.staleness(graph, repo)


@mcp.tool()
def find_nodes(query: str, type: str | None = None, repo: str = ".") -> dict:
    """Find nodes whose id or name contains a substring, optionally by type."""
    graph, err = _open(repo)
    return err or queries.find_nodes(graph, query, type)


@mcp.tool()
def get_neighbors(id: str, edge_types: list[str] | None = None, depth: int = 1, repo: str = ".") -> dict:
    """Nodes within `depth` hops of a node (both directions); 'what touches this?'."""
    graph, err = _open(repo)
    return err or queries.get_neighbors(graph, id, edge_types, depth)


@mcp.tool()
def shortest_path(a: str, b: str, repo: str = ".") -> dict:
    """An ordered path connecting two nodes, or an explicit 'no path' result."""
    graph, err = _open(repo)
    return err or queries.shortest_path(graph, a, b)


def run() -> None:
    mcp.run()


if __name__ == "__main__":
    run()
