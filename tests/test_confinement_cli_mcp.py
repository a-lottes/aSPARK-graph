"""T3/T4: confinement enforced end-to-end on both adapters (security-posture US-1).

T3 covers the walking skeleton — `build_graph` refused on CLI and MCP
(AC-1.1, AC-1.2, AC-1.12, NFR-3). T4 extends this file with the table-driven
sweep over all eight query tools (AC-1.3) plus the direct-library check
(AC-1.9) and the graph-marker acceptance/staleness-survives cases
(AC-1.11, AC-1.13).
"""

import asyncio
import json
import time
from pathlib import Path

import pytest

from aspark_graph import cli, confinement, queries, server
from aspark_graph.build import build_graph
from aspark_graph.graph import default_graph_path

SAMPLE_REPO = Path(__file__).parent / "fixtures" / "sample_repo"

# Every query tool takes at minimum `repo`; extra required args per tool name.
_QUERY_TOOL_ARGS = {
    "get_node": {"id": "file:x.py"},
    "story_trace": {"story": "US-1"},
    "impact": {"files": ["x.py"]},
    "gate_health": {"feature": "demo"},
    "staleness": {},
    "find_nodes": {"query": "x"},
    "get_neighbors": {"id": "file:x.py"},
    "shortest_path": {"a": "file:x.py", "b": "file:y.py"},
}


def _unmarked(tmp_path):
    d = tmp_path / "unmarked"
    d.mkdir()
    return d


# --- T3: build_graph refusal on both surfaces -------------------------------


def test_cli_build_on_unmarked_dir_refuses_cleanly(tmp_path, capsys):
    target = _unmarked(tmp_path)
    start = time.monotonic()
    rc = cli.main(["build", str(target)])
    elapsed = time.monotonic() - start

    assert rc == 1
    assert elapsed < 1.0
    out, err = capsys.readouterr()
    assert out == ""  # no partial success output on stdout
    lines = [l for l in err.splitlines() if l.strip()]
    assert len(lines) == 1  # exactly one stderr line
    assert str(target.resolve()) in lines[0]
    assert "Traceback" not in err
    assert not default_graph_path(target).exists()


def test_mcp_build_graph_on_unmarked_dir_refuses_cleanly(tmp_path):
    target = _unmarked(tmp_path)
    result = server.build_graph(path=str(target))
    assert result == {
        "found": False,
        "reason": "outside_confinement",
        "message": result["message"],
    }
    assert str(target.resolve()) in result["message"]
    assert not default_graph_path(target).exists()


def test_a_prior_successful_build_elsewhere_does_not_prime_confinement(tmp_path, capsys):
    # AC-1.12: confinement is purely a property of the target path — a build
    # that succeeded against a marked repo must not leave any state that
    # admits an unrelated, still-unmarked directory.
    marked = tmp_path / "marked"
    marked.mkdir()
    (marked / ".git").mkdir()
    (marked / "a.py").write_text("def f():\n    return 1\n")
    rc = cli.main(["build", str(marked)])
    assert rc == 0
    capsys.readouterr()

    fresh = tmp_path / "still-unmarked"
    fresh.mkdir()
    rc = cli.main(["build", str(fresh)])
    assert rc == 1
    assert not default_graph_path(fresh).exists()


def test_fresh_directory_with_no_prior_build_is_refused(tmp_path):
    # AC-1.12: the third marker (graph.json) can never admit an unbuilt target.
    target = _unmarked(tmp_path)
    assert not (target / ".aspark-graph" / "graph.json").exists()
    result = server.build_graph(path=str(target))
    assert result["found"] is False
    assert result["reason"] == "outside_confinement"


# --- T4: the registered tool set + the table-driven query sweep (AC-1.3) ---


def test_registered_mcp_tools_are_exactly_the_query_set_plus_build():
    # A ninth tool added without an entry here fails this assertion first.
    tools = asyncio.run(server.mcp.list_tools())
    names = {t.name for t in tools}
    assert names == set(cli._QUERY_NAMES) | {"build_graph"}


def test_query_arg_table_covers_every_registered_query_tool():
    # Guards the table itself: a query added to cli._QUERY_NAMES without a
    # matching row here would silently skip AC-1.3 below.
    assert set(_QUERY_TOOL_ARGS) == set(cli._QUERY_NAMES)


@pytest.mark.parametrize("tool", sorted(_QUERY_TOOL_ARGS))
def test_every_query_tool_refuses_an_unmarked_repo_on_mcp(tmp_path, tool):
    target = _unmarked(tmp_path)
    params = dict(_QUERY_TOOL_ARGS[tool])
    params["repo"] = str(target)
    result = getattr(server, tool)(**params)
    assert result == {
        "found": False,
        "reason": "outside_confinement",
        "message": result.get("message"),
    }
    assert str(target.resolve()) in result["message"]


@pytest.mark.parametrize("tool", sorted(_QUERY_TOOL_ARGS))
def test_every_query_tool_refuses_an_unmarked_repo_on_cli(tmp_path, capsys, tool):
    target = _unmarked(tmp_path)
    # cli's query subcommand syntax is `query <name> --repo <repo> <positional...>`
    positional = {
        "get_node": ["file:x.py"],
        "story_trace": ["US-1"],
        "impact": [],
        "gate_health": ["demo"],
        "staleness": [],
        "find_nodes": ["x"],
        "get_neighbors": ["file:x.py"],
        "shortest_path": ["file:x.py", "file:y.py"],
    }[tool]
    rc = cli.main(["query", tool, "--repo", str(target), *positional])
    assert rc == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert str(target.resolve()) in err
    assert "Traceback" not in err


# --- T4: direct library calls refuse too (AC-1.9) ---------------------------


def test_load_graph_refuses_unmarked_repo_directly(tmp_path):
    with pytest.raises(confinement.RepoRefused):
        queries.load_graph(_unmarked(tmp_path))


def test_staleness_refuses_unmarked_repo_directly(tmp_path):
    graph, _ = build_graph(SAMPLE_REPO)
    with pytest.raises(confinement.RepoRefused):
        queries.staleness(graph, _unmarked(tmp_path))


def test_impact_diff_refuses_unmarked_repo_directly(tmp_path):
    graph, _ = build_graph(SAMPLE_REPO)
    with pytest.raises(confinement.RepoRefused):
        queries.impact_diff(graph, _unmarked(tmp_path), "HEAD~1..HEAD")


def test_build_graph_refuses_unmarked_repo_directly(tmp_path):
    with pytest.raises(confinement.RepoRefused):
        build_graph(_unmarked(tmp_path))


# --- T4: the graph-only marker (AC-1.11, AC-1.13) ----------------------------


def test_graph_only_directory_is_accepted_by_every_query_tool(tmp_path):
    # A directory holding only .aspark-graph/graph.json (no .git, no .spark) —
    # e.g. one already built, whose confinement markers were removed later.
    target = tmp_path / "graph-only"
    target.mkdir()
    (target / ".git").mkdir()  # build it while marked...
    (target / "a.py").write_text("def f():\n    return 1\n")
    graph, _ = build_graph(target)
    graph.save(default_graph_path(target))
    (target / ".git").rmdir()  # ...then remove the marker (AC-1.13)

    for tool in sorted(_QUERY_TOOL_ARGS):
        params = dict(_QUERY_TOOL_ARGS[tool])
        params["repo"] = str(target)
        result = getattr(server, tool)(**params)
        assert result.get("reason") != "outside_confinement", f"{tool} refused a graph-only dir"
