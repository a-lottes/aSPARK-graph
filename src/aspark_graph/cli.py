"""Thin CLI over build.py and queries.py — the MCP fallback (US-5).

Uses stdlib ``argparse`` only (no CLI framework: the surface is two verbs).
Every query subcommand loads the graph and calls the matching function in
``queries.py``; it never computes an answer itself. Output is JSON on stdout so
it is trivially machine-consumable in CI.
"""

from __future__ import annotations

import argparse
import json
import sys

from . import artifacts, queries
from .build import build_graph
from .graph import default_graph_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="aspark-graph",
        description="A lean, local code-and-artifact knowledge graph that speaks SPARK.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser("build", help="(Re)scan a repo + .spark/ and persist the graph.")
    p_build.add_argument("path", nargs="?", default=".", help="Repo root (default: .)")
    p_build.add_argument("--full", action="store_true", default=False,
                         help="Force a full rescan, ignoring any cached parse results.")

    sub.add_parser("serve", help="Run the MCP stdio server.")

    p_query = sub.add_parser("query", help="Query the persisted graph.")
    _add_query_subcommands(p_query)

    args = parser.parse_args(argv)

    if args.command == "build":
        return _cmd_build(args)
    if args.command == "serve":
        return _cmd_serve()
    if args.command == "query":
        return _cmd_query(args)
    parser.error(f"unknown command {args.command!r}")
    return 2


def _add_query_subcommands(p_query: argparse.ArgumentParser) -> None:
    qsub = p_query.add_subparsers(dest="query_name", required=True)
    for name in _QUERY_NAMES:
        qp = qsub.add_parser(name)
        qp.add_argument("--repo", default=".", help="Repo root (default: .)")
        _QUERY_ARGS[name](qp)


# --- query registry --------------------------------------------------------
# Each entry: argument-adder + handler(graph, args) -> dict. Adding a query is a
# localised edit here; the CLI plumbing never changes.

def _args_get_node(qp: argparse.ArgumentParser) -> None:
    qp.add_argument("id", help="Node id, e.g. file:src/foo.py")


def _handle_get_node(graph, args) -> dict:
    return queries.get_node(graph, args.id)


def _args_story_trace(qp: argparse.ArgumentParser) -> None:
    qp.add_argument("story", help="Story id, bare (US-2) or full (story:feat:US-2)")
    qp.add_argument("--feature", default=None, help="Disambiguate a bare story id")


def _handle_story_trace(graph, args) -> dict:
    return queries.story_trace(graph, args.story, args.feature)


def _args_impact(qp: argparse.ArgumentParser) -> None:
    qp.add_argument("files", nargs="*", help="One or more changed file paths")
    qp.add_argument("--diff", default=None, metavar="RANGE",
                    help="A git range (e.g. HEAD~2..HEAD) to derive the files from")


def _handle_impact(graph, args) -> dict:
    if args.diff:
        if args.files:
            return {"found": False, "reason": "bad_args",
                    "message": "pass either files or --diff, not both"}
        return queries.impact_diff(graph, args.repo, args.diff)
    if not args.files:
        return {"found": False, "reason": "bad_args", "message": "no files given (pass files or --diff)"}
    return queries.impact(graph, args.files)


def _args_find_nodes(qp: argparse.ArgumentParser) -> None:
    qp.add_argument("query", help="Substring to match against id/name")
    qp.add_argument("--type", default=None, help="Filter by node type (e.g. Function)")


def _handle_find_nodes(graph, args) -> dict:
    return queries.find_nodes(graph, args.query, args.type)


def _args_get_neighbors(qp: argparse.ArgumentParser) -> None:
    qp.add_argument("id", help="Node id")
    qp.add_argument("--edge-type", action="append", dest="edge_types", default=None, help="Restrict to edge type (repeatable)")
    qp.add_argument("--depth", type=int, default=1, help="Hops (default: 1)")


def _handle_get_neighbors(graph, args) -> dict:
    return queries.get_neighbors(graph, args.id, args.edge_types, args.depth)


def _args_shortest_path(qp: argparse.ArgumentParser) -> None:
    qp.add_argument("a", help="Start node id")
    qp.add_argument("b", help="End node id")


def _handle_shortest_path(graph, args) -> dict:
    return queries.shortest_path(graph, args.a, args.b)


def _args_gate_health(qp: argparse.ArgumentParser) -> None:
    qp.add_argument("feature", help="Feature name (the .spark/<feature> directory)")


def _handle_gate_health(graph, args) -> dict:
    return queries.gate_health(graph, args.feature)


def _args_staleness(qp: argparse.ArgumentParser) -> None:
    pass  # --repo (added for every query) is all it needs


def _handle_staleness(graph, args) -> dict:
    return queries.staleness(graph, args.repo)


_QUERY_ARGS = {
    "get_node": _args_get_node,
    "story_trace": _args_story_trace,
    "impact": _args_impact,
    "gate_health": _args_gate_health,
    "staleness": _args_staleness,
    "find_nodes": _args_find_nodes,
    "get_neighbors": _args_get_neighbors,
    "shortest_path": _args_shortest_path,
}
_QUERY_HANDLERS = {
    "get_node": _handle_get_node,
    "story_trace": _handle_story_trace,
    "impact": _handle_impact,
    "gate_health": _handle_gate_health,
    "staleness": _handle_staleness,
    "find_nodes": _handle_find_nodes,
    "get_neighbors": _handle_get_neighbors,
    "shortest_path": _handle_shortest_path,
}
_QUERY_NAMES = list(_QUERY_ARGS)


# --- command implementations -----------------------------------------------

def _cmd_build(args) -> int:
    try:
        graph, report = build_graph(args.path, full=args.full)
    except artifacts.TemplateDriftError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if report.fallback_reason:
        print(f"Cache unusable ({report.fallback_reason}); fell back to full rescan.", file=sys.stderr)
    out_path = default_graph_path(args.path)
    graph.save(out_path)
    print(f"Built graph: {report.summary()}")
    print(f"Saved to {out_path}")
    return 0


def _cmd_serve() -> int:
    from .server import run

    run()
    return 0


def _cmd_query(args) -> int:
    try:
        graph = queries.load_graph(args.repo)
    except queries.GraphNotBuiltError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    result = _QUERY_HANDLERS[args.query_name](graph, args)
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
