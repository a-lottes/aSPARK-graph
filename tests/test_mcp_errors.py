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
    (tmp_path / ".git").mkdir()
    feat = tmp_path / ".spark" / "demo"
    feat.mkdir(parents=True)
    (feat / "spec.md").write_text("# Spec: demo\n\n## 4. User Stories\n\n### US-1 (Must): Run\n\n**Acceptance criteria:**\n\n- [ ] AC-1.1: Given x, then y.\n")
    qa = feat / "qa.md"
    qa.write_text("# QA\n\nnothing recognisable here\n")
    graph_file = tmp_path / ".aspark-graph" / "graph.json"

    data = server.build_graph(str(tmp_path))
    assert data["built"] is False
    assert data["reason"] == "template_drift"
    assert data["file"].endswith("qa.md")
    assert "template drift" in data["message"]
    assert not graph_file.exists()

    # An existing graph stays unchanged by a later failed build.
    graph_file.parent.mkdir(exist_ok=True)
    graph_file.write_text("sentinel")
    assert server.build_graph(str(tmp_path))["reason"] == "template_drift"
    assert graph_file.read_text() == "sentinel"
