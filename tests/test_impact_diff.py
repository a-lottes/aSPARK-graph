"""T9: impact --diff <range> (US-3) — AC-3.1..3.3."""

from aspark_graph import queries
from aspark_graph.build import build_graph
from aspark_graph.model import story_id


def test_ac_3_1_diff_equals_explicit_files(git_backed_repo):
    graph, _ = build_graph(git_backed_repo)
    # The last commit (T1 ...) touched src/app.py.
    by_diff = queries.impact_diff(graph, git_backed_repo, "HEAD~1..HEAD")
    by_files = queries.impact(graph, ["src/app.py"])
    assert {s["id"] for s in by_diff["affected_stories"]} == {s["id"] for s in by_files["affected_stories"]}
    assert story_id("demo", "US-1") in {s["id"] for s in by_diff["affected_stories"]}


def test_ac_3_3_invalid_range_is_clear_message(git_backed_repo):
    graph, _ = build_graph(git_backed_repo)
    r = queries.impact_diff(graph, git_backed_repo, "no-such-ref..HEAD")
    assert r["found"] is False
    assert r["reason"] == "bad_range"
    assert "range" in r["message"].lower()


def test_ac_3_3_empty_range_message(git_backed_repo):
    graph, _ = build_graph(git_backed_repo)
    r = queries.impact_diff(graph, git_backed_repo, "   ")
    assert r["found"] is False
    assert "empty" in r["message"].lower()


def test_ac_3_2_diff_unknown_paths_named_via_impact(git_backed_repo, git_tools):
    # A commit touching a non-source file: it won't be a graph node, so impact
    # names it unknown while still answering. Add + commit a .txt file.
    (git_backed_repo / "notes.txt").write_text("hello\n")
    git_tools["commit"](git_backed_repo, "chore: add notes")
    graph, _ = build_graph(git_backed_repo)
    r = queries.impact_diff(graph, git_backed_repo, "HEAD~1..HEAD")
    assert "notes.txt" in r["unknown_files"]


def test_cli_impact_diff_matches_mcp(git_backed_repo, capsys):
    import json
    from aspark_graph import cli, server
    from aspark_graph.graph import default_graph_path

    graph, _ = build_graph(git_backed_repo)
    graph.save(default_graph_path(git_backed_repo))
    repo = str(git_backed_repo)

    rc = cli.main(["query", "impact", "--repo", repo, "--diff", "HEAD~1..HEAD"])
    assert rc == 0
    cli_out = json.loads(capsys.readouterr().out)

    # @mcp.tool() leaves the function directly callable, returning the MCP dict.
    assert cli_out == server.impact(diff="HEAD~1..HEAD", repo=repo)
