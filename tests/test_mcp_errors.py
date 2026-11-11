"""F3: MCP query tools return a clean 'build first' dict, never a raw error.

Parity with the CLI's AC-5.2 behaviour (which prints a clean message and exits
1) — the MCP client must not receive a raised GraphNotBuiltError.
"""

from aspark_graph import server


def _call(tool, params):
    # @mcp.tool() leaves the function directly callable; it returns the same
    # dict the MCP surface serialises (a clean 'build first' dict on error).
    return getattr(server, tool)(**params)


def test_query_before_build_returns_clean_error(tmp_path):
    # No graph built in tmp_path.
    for tool, params in [
        ("get_node", {"id": "file:x.py", "repo": str(tmp_path)}),
        ("story_trace", {"story": "US-1", "repo": str(tmp_path)}),
        ("impact", {"files": ["x.py"], "repo": str(tmp_path)}),
        ("staleness", {"repo": str(tmp_path)}),
        ("gate_health", {"feature": "demo", "repo": str(tmp_path)}),
    ]:
        data = _call(tool, params)
        assert data["found"] is False
        assert "build" in data["error"].lower()


def test_build_graph_template_drift_returns_structured_result(tmp_path):
    repo = tmp_path / "r"
    feat = repo / ".spark" / "demo"
    feat.mkdir(parents=True)
    (repo / ".git").mkdir()
    (feat / "qa.md").write_text("# QA\n\nno verification section\n")
    gpath = repo / ".aspark-graph" / "graph.json"

    data = server.build_graph(str(repo))
    assert data["built"] is False
    assert data["reason"] == "template_drift"
    assert data["file"].endswith("qa.md")
    assert "template drift" in data["message"]
    assert not gpath.exists()

    gpath.parent.mkdir()
    gpath.write_text("old")
    assert server.build_graph(str(repo))["built"] is False
    assert gpath.read_text() == "old"
