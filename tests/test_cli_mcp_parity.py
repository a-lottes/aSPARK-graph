"""T8: CLI is a faithful fallback for the MCP server.

AC-5.1: for the same inputs the CLI and the MCP tool return the same answer —
asserted by driving both adapters over the shared query functions.
AC-5.2: a query before any build gives a clear 'build first' message, no trace.

security-posture AC-1.7/AC-1.8: the same table now carries confinement
refusal rows alongside accepted ones (no second parity test), plus the
default repo="." regression.
"""

import json
import shutil
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


# --- current-artifact-names T4 / AC-4.4, AC-4.5: ignored legacy files --------

CURRENT_REPO = Path(__file__).parent / "fixtures" / "current_names_repo"


def _mixed_copy(dest: Path) -> Path:
    """The current-name fixture plus two legacy files its current names shadow."""
    shutil.copytree(CURRENT_REPO, dest, ignore=shutil.ignore_patterns(".aspark-graph"))
    feature = dest / ".spark" / "demo"
    shutil.copy(feature / "qa.md", feature / "qa-report.md")
    shutil.copy(feature / "release.md", feature / "release-notes.md")
    return dest


def test_ignored_legacy_files_same_on_cli_and_mcp(tmp_path, capsys):
    a = _mixed_copy(tmp_path / "a")
    b = _mixed_copy(tmp_path / "b")

    rc = cli.main(["build", str(a)])
    err = capsys.readouterr().err
    result = _mcp_data("build_graph", {"path": str(b)})

    assert rc == 0
    assert "reason" not in result
    cli_ignored = [line.split()[1] for line in err.splitlines() if line.startswith("Ignored ")]
    assert cli_ignored == [".spark/demo/qa-report.md", ".spark/demo/release-notes.md"]
    assert "Ignored .spark/demo/qa-report.md (qa.md takes precedence)" in err
    assert result["ignored_legacy_files"] == cli_ignored
    assert (a / ".aspark-graph" / "graph.json").read_bytes() == (b / ".aspark-graph" / "graph.json").read_bytes()


def test_no_ignored_legacy_files_on_a_legacy_only_trail(tmp_path, capsys):
    a = tmp_path / "a"
    b = tmp_path / "b"
    shutil.copytree(SAMPLE_REPO, a, ignore=shutil.ignore_patterns(".aspark-graph"))
    shutil.copytree(SAMPLE_REPO, b, ignore=shutil.ignore_patterns(".aspark-graph"))

    assert cli.main(["build", str(a)]) == 0
    assert "Ignored " not in capsys.readouterr().err
    assert _mcp_data("build_graph", {"path": str(b)})["ignored_legacy_files"] == []


# --- shallow-clone-warning T7: notice ⇔ MCP key, on every US-1/US-4 fixture ---

import subprocess  # noqa: E402

from aspark_graph.build import NO_GIT_HISTORY_NOTICE, SHALLOW_HISTORY_NOTICE  # noqa: E402

from conftest import (  # noqa: E402
    full_clone, git_commit, init_git_repo, make_boundary_origin, make_origin, make_trail,
    shallow_clone,
)

_V071_BUILD_KEYS = {
    "code_entities", "artifact_entities", "inferred_edges", "unparsed",
    "ignored_legacy_files", "graph_path",
}


def _monorepo_origin(root):
    """A full repo whose .spark/ project sits in proj/ (the A7 subdirectory build)."""
    root.mkdir(parents=True)
    init_git_repo(root)
    make_trail(root / "proj")
    git_commit(root, "docs: add spark trail")
    (root / "proj" / "src").mkdir()
    (root / "proj" / "src" / "app.py").write_text("def run():\n    return 1\n")
    git_commit(root, "T1: implement app (US-1)")
    return root


def _history_fixture(shape, base, monkeypatch):
    """Build one of the nine AC-2.4 fixtures under ``base``; return the build path."""
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(base))
    if shape == "no-git" or shape == "no-git-no-task":
        path = base / "zip"
        path.mkdir(parents=True)
        make_trail(path, with_task=shape == "no-git")
        (path / "app.py").write_text("def run():\n    return 1\n")
        return path
    if shape.startswith("boundary"):
        origin = make_boundary_origin(base / "origin")
        if shape == "boundary-full":
            return full_clone(origin, base / "clone")
        depth = "1" if shape == "boundary-depth1" else "3"
        clone = shallow_clone(origin, base / "clone", "--depth", depth)
        if shape == "boundary-corrupt-marker":
            (clone / ".git" / "shallow").write_text("this is not a sha\n")
        return clone
    if shape.startswith("subdir"):
        origin = _monorepo_origin(base / "origin")
        clone = (shallow_clone if shape == "subdir-of-shallow" else full_clone)(origin, base / "clone")
        return clone / "proj"
    origin = make_origin(base / "origin", with_task=shape != "shallow-no-task")
    if shape in ("shallow", "shallow-no-task"):
        return shallow_clone(origin, base / "clone")
    if shape == "single-branch":
        return full_clone(origin, base / "clone", "--single-branch")
    clone = full_clone(origin, base / "clone")
    if shape == "detached":
        subprocess.run(["git", "-C", str(clone), "checkout", "-q", "--detach", "HEAD~1"],
                       check=True, capture_output=True, text=True)
    return clone


_SHAPES = {  # shape -> (shallow_history, no_git_history)
    "shallow": (True, False),
    "full": (False, False),
    "shallow-no-task": (False, False),
    "no-git": (False, True),
    "no-git-no-task": (False, False),
    "subdir-of-full": (False, False),
    "subdir-of-shallow": (True, False),
    "detached": (False, False),
    "single-branch": (False, False),
    "boundary-depth1": (True, False),
    "boundary-depth3": (True, False),
    "boundary-full": (False, False),
    "boundary-corrupt-marker": None,  # whatever git reports; only ⇔ and never-both are asserted
}


@pytest.mark.parametrize("shape", sorted(_SHAPES))
def test_history_notice_iff_mcp_key_on_every_fixture(tmp_path, capsys, monkeypatch, shape):
    a = _history_fixture(shape, tmp_path / "a", monkeypatch)
    b = _history_fixture(shape, tmp_path / "b", monkeypatch)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))

    assert cli.main(["build", str(a)]) == 0
    err = capsys.readouterr().err.splitlines()
    result = _mcp_data("build_graph", {"path": str(b)})

    if _SHAPES[shape] is not None:
        assert (result["shallow_history"], result["no_git_history"]) == _SHAPES[shape]
    assert (SHALLOW_HISTORY_NOTICE in err) == result["shallow_history"]
    assert (NO_GIT_HISTORY_NOTICE in err) == result["no_git_history"]
    assert not (result["shallow_history"] and result["no_git_history"])
    assert set(result) == _V071_BUILD_KEYS | {"shallow_history", "no_git_history"}
    assert (a / ".aspark-graph" / "graph.json").read_bytes() == (b / ".aspark-graph" / "graph.json").read_bytes()
