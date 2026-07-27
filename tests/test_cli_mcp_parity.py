"""T8: CLI is a faithful fallback for the MCP server.

AC-5.1: for the same inputs the CLI and the MCP tool return the same answer —
asserted by driving both adapters over the shared query functions.
AC-5.2: a query before any build gives a clear 'build first' message, no trace.

security-posture AC-1.7/AC-1.8: the same table now carries confinement
refusal rows alongside accepted ones (no second parity test), plus the
default repo="." regression.
"""

import json
from pathlib import Path

import pytest

from aspark_graph import cli, confinement, queries, server
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


# --- AC-1.7: one fixed table, accepted and refused rows, CLI == MCP verdict -


def _confinement_rows(tmp_path):
    """(path, accepted) — three accepted marker shapes, three refused shapes."""
    marked_git_dir = tmp_path / "marked-git-dir"
    marked_git_dir.mkdir()
    (marked_git_dir / ".git").mkdir()

    marked_git_file = tmp_path / "marked-git-file"
    marked_git_file.mkdir()
    (marked_git_file / ".git").write_text("gitdir: ../elsewhere/.git\n")

    graph_only = tmp_path / "graph-only"
    graph_only.mkdir()
    (graph_only / ".aspark-graph").mkdir()
    (graph_only / ".aspark-graph" / "graph.json").write_text(json.dumps({"nodes": [], "edges": []}))

    empty = tmp_path / "empty"
    empty.mkdir()

    missing = tmp_path / "does-not-exist"

    regular_file = tmp_path / "regular.txt"
    regular_file.write_text("x")

    return [
        (marked_git_dir, True),
        (marked_git_file, True),
        (graph_only, True),
        (empty, False),
        (missing, False),
        (regular_file, False),
    ]


@pytest.mark.parametrize("row", range(6))
def test_ac_1_7_confinement_verdict_is_identical_cli_vs_mcp(tmp_path, capsys, row):
    path, accepted = _confinement_rows(tmp_path)[row]

    rc = cli.main(["build", str(path)])
    cli_err = capsys.readouterr().err
    cli_accepted = rc == 0

    mcp_out = server.build_graph(path=str(path))
    mcp_accepted = mcp_out.get("reason") != "outside_confinement"

    assert cli_accepted == accepted, f"CLI verdict wrong for {path}: rc={rc}, err={cli_err!r}"
    assert mcp_accepted == accepted, f"MCP verdict wrong for {path}: {mcp_out!r}"
    assert cli_accepted == mcp_accepted  # the actual parity assertion


# --- AC-1.8: default repo="." keeps working, byte-for-byte -----------------


def test_ac_1_8_default_repo_dot_message_stays_relative(tmp_path, monkeypatch):
    # A marked-but-unbuilt cwd must still produce the exact pre-confinement
    # relative message — resolving "." to an absolute path would change it.
    (tmp_path / ".git").mkdir()
    monkeypatch.chdir(tmp_path)
    with pytest.raises(queries.GraphNotBuiltError) as exc_info:
        queries.load_graph(".")
    assert str(exc_info.value) == (
        "No graph found at .aspark-graph/graph.json. Run 'aspark-graph build' first."
    )


def test_ac_1_8_default_repo_accepted_from_a_real_checkout(monkeypatch):
    # The documented install runs with cwd = the aspark-graph checkout, which
    # is itself .git-marked — the default repo="." must not be refused.
    checkout_root = Path(__file__).resolve().parents[1]
    assert (checkout_root / ".git").exists()
    monkeypatch.chdir(checkout_root)
    assert confinement.ensure_repo(".") == checkout_root.resolve()
