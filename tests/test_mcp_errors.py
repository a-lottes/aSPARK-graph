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


def _drifted_repo(root, name, content):
    (root / ".git").mkdir()
    feat = root / ".spark" / "demo"
    feat.mkdir(parents=True)
    (feat / "spec.md").write_text(
        "# Spec: demo\n\n## 4. User Stories\n\n### US-1 (Must): Run\n\n"
        "**Acceptance criteria:**\n\n- [ ] AC-1.1: Given x, then y.\n"
    )
    (feat / name).write_text(content)
    return feat / name


def test_build_graph_review_drift_returns_structured_result(tmp_path):
    bad = _drifted_repo(tmp_path, "review.md", "# Review\n\nno findings section\n")
    data = server.build_graph(str(tmp_path))
    assert data["built"] is False
    assert data["reason"] == "template_drift"
    assert data["file"].endswith("review.md")
    assert "Findings" in data["message"]
    assert not (tmp_path / ".aspark-graph" / "graph.json").exists()


def test_cli_drift_is_one_line_nonzero_and_matches_mcp_message(tmp_path, capsys):
    from aspark_graph import cli

    bad = _drifted_repo(tmp_path, "qa.md", "# QA\n\nnothing\n")
    mcp = server.build_graph(str(tmp_path))
    assert cli.main(["build", str(tmp_path)]) != 0
    captured = capsys.readouterr()
    err = captured.err
    assert err.strip() == mcp["message"]
    assert "\n" not in err.strip()
    assert bad.name in err and "Traceback" not in err and "Traceback" not in captured.out
    assert not (tmp_path / ".aspark-graph" / "graph.json").exists()


def test_successful_build_has_no_built_key_and_matches_cli(tmp_path):
    import shutil
    from pathlib import Path

    from aspark_graph import cli

    src = Path(__file__).parent / "fixtures" / "sample_repo"
    from aspark_graph.build import build_graph

    a, b, c = tmp_path / "a", tmp_path / "b", tmp_path / "c"
    for d in (a, b, c):
        shutil.copytree(src, d)
        (d / ".git").mkdir(exist_ok=True)
    data = server.build_graph(str(a))
    assert "built" not in data
    assert set(data) == {
        "code_entities", "artifact_entities", "inferred_edges", "unparsed",
        "ignored_legacy_files", "graph_path", "shallow_history", "no_git_history",
    }
    _, report = build_graph(c)
    assert (data["code_entities"], data["artifact_entities"], data["inferred_edges"], data["unparsed"],
            data["ignored_legacy_files"]) == (report.code_entities, report.artifact_entities,
                                              report.inferred_edges, report.unparsed, report.shadowed)
    assert cli.main(["build", str(b)]) == 0
    assert (a / ".aspark-graph" / "graph.json").read_bytes() == (b / ".aspark-graph" / "graph.json").read_bytes()
