"""T7: staleness detection (US-4) — AC-4.1..4.3."""

from aspark_graph import queries
from aspark_graph.build import build_graph
from aspark_graph.graph import default_graph_path


def test_ac_4_2_unchanged_repo_is_current(git_backed_repo):
    graph, _ = build_graph(git_backed_repo)
    r = queries.staleness(graph, git_backed_repo)
    assert r["stale"] is False
    assert r["changed"] == [] and r["missing"] == []
    assert r["advice"] is None


def test_ac_4_1_changed_file_is_flagged(git_backed_repo):
    graph, _ = build_graph(git_backed_repo)
    (git_backed_repo / "src" / "app.py").write_text("def run():\n    return 999\n")
    r = queries.staleness(graph, git_backed_repo)
    assert r["stale"] is True
    assert "src/app.py" in r["changed"]
    assert "build" in r["advice"].lower()


def test_ac_4_1_missing_file_is_flagged(git_backed_repo):
    graph, _ = build_graph(git_backed_repo)
    (git_backed_repo / "src" / "app.py").unlink()
    r = queries.staleness(graph, git_backed_repo)
    assert r["stale"] is True
    assert "src/app.py" in r["missing"]


def test_ac_4_3_rebuild_restores_current(git_backed_repo):
    graph, _ = build_graph(git_backed_repo)
    (git_backed_repo / "src" / "app.py").write_text("def run():\n    return 2\n")
    assert queries.staleness(graph, git_backed_repo)["stale"] is True
    # Rebuild from the new state -> current again.
    graph2, _ = build_graph(git_backed_repo)
    assert queries.staleness(graph2, git_backed_repo)["stale"] is False


def test_cli_and_mcp_staleness_agree(git_backed_repo, capsys):
    import json
    from aspark_graph import cli, server

    graph, _ = build_graph(git_backed_repo)
    graph.save(default_graph_path(git_backed_repo))
    repo = str(git_backed_repo)

    rc = cli.main(["query", "staleness", "--repo", repo])
    assert rc == 0
    cli_out = json.loads(capsys.readouterr().out)

    # @mcp.tool() leaves the function directly callable, returning the MCP dict.
    assert cli_out == server.staleness(repo=repo)
