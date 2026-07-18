"""T8: CLI is a faithful fallback for the MCP server.

AC-5.1: for the same inputs the CLI and the MCP tool return the same answer —
asserted by driving both adapters over the shared query functions.
AC-5.2: a query before any build gives a clear 'build first' message, no trace.
"""

import json
from pathlib import Path

from aspark_graph import cli, queries, server
from aspark_graph.build import build_graph

SAMPLE_REPO = Path(__file__).parent / "fixtures" / "sample_repo"


def _cli_json(capsys, argv) -> dict:
    rc = cli.main(argv)
    assert rc == 0
    return json.loads(capsys.readouterr().out)


def _mcp_data(tool: str, params: dict):
    # The @mcp.tool() decorator leaves the underlying function directly callable,
    # and it returns the same plain dict the MCP surface serialises. Calling it
    # in-process is the faithful way to assert CLI≡MCP parity over the shared
    # query functions — no transport needed.
    return getattr(server, tool)(**params)


def _prepare(tmp_path):
    # Build the sample repo's graph into a temp .aspark-graph so both adapters
    # read the same persisted graph.
    graph, _ = build_graph(SAMPLE_REPO)
    graph.save(queries.default_graph_path(tmp_path))
    return str(tmp_path)


def test_story_trace_cli_equals_mcp(tmp_path, capsys):
    repo = _prepare(tmp_path)
    cli_out = _cli_json(capsys, ["query", "story_trace", "--repo", repo, "US-1", "--feature", "demo"])
    mcp_out = _mcp_data("story_trace", {"story": "US-1", "feature": "demo", "repo": repo})
    assert cli_out == mcp_out


def test_impact_cli_equals_mcp(tmp_path, capsys):
    repo = _prepare(tmp_path)
    cli_out = _cli_json(capsys, ["query", "impact", "--repo", repo, "src/demo/app.py", "src/demo/util.py"])
    mcp_out = _mcp_data("impact", {"files": ["src/demo/app.py", "src/demo/util.py"], "repo": repo})
    assert cli_out == mcp_out


def test_get_node_cli_equals_mcp(tmp_path, capsys):
    repo = _prepare(tmp_path)
    cli_out = _cli_json(capsys, ["query", "get_node", "--repo", repo, "file:src/demo/app.py"])
    mcp_out = _mcp_data("get_node", {"id": "file:src/demo/app.py", "repo": repo})
    assert cli_out == mcp_out


def test_find_nodes_empty_query_cli_equals_mcp(tmp_path, capsys):
    """AC-1.3 + AC-1.4: CLI and MCP both return the empty-result dict for query=""."""
    repo = _prepare(tmp_path)
    cli_out = _cli_json(capsys, ["query", "find_nodes", "--repo", repo, ""])
    mcp_out = _mcp_data("find_nodes", {"query": "", "repo": repo})
    assert cli_out == mcp_out
    assert cli_out == {"query": "", "type": None, "count": 0, "nodes": []}


def test_ac_5_2_query_before_build_is_a_clear_message(tmp_path, capsys):
    rc = cli.main(["query", "get_node", "--repo", str(tmp_path), "file:whatever.py"])
    err = capsys.readouterr().err
    assert rc == 1
    assert "build" in err.lower()
    assert "Traceback" not in err  # no stack trace leaked to the user
