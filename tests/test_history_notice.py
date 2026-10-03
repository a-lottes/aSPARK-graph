"""shallow-clone-warning: the build names truncated or absent git history.

A shallow clone or a directory without git silently loses `inferred` links.
When the graph has >=1 plan task, the CLI prints one approved stderr line and
MCP `build_graph` returns two booleans (spec US-1, US-2, US-4). Everything
else about the build — exit code, stdout, graph.json bytes — is unchanged.
"""

import os
import shutil
import subprocess

import pytest

from aspark_graph import cli, git, queries, server
from aspark_graph.build import NO_GIT_HISTORY_NOTICE, SHALLOW_HISTORY_NOTICE, build_graph

from conftest import full_clone, make_origin, make_trail, shallow_clone

NOTICES = (SHALLOW_HISTORY_NOTICE, NO_GIT_HISTORY_NOTICE)


def _cli_build(capsys, *argv):
    rc = cli.main(["build", *map(str, argv)])
    out, err = capsys.readouterr()
    return rc, out, err


def test_t1_shallow_clone_names_truncated_history_on_cli_and_mcp(tmp_path, capsys):
    origin = make_origin(tmp_path / "origin")
    clone = shallow_clone(origin, tmp_path / "clone")
    assert git.history_state(clone) == "shallow"  # R4: the fixture really is shallow

    rc, _out, err = _cli_build(capsys, clone)
    assert rc == 0
    assert err.splitlines().count(SHALLOW_HISTORY_NOTICE) == 1
    assert NO_GIT_HISTORY_NOTICE not in err

    resp = server.build_graph(path=str(clone))
    assert resp["shallow_history"] is True
    assert resp["no_git_history"] is False


def _graph_bytes(root):
    return (root / ".aspark-graph" / "graph.json").read_bytes()


def _no_git_dir(path, monkeypatch, ceiling, *, with_task=True):
    """US-4 fixture: a .spark/-marked directory outside any work tree (a ZIP).
    Plan R2: the ceiling stops git's upward search; the precondition is checked."""
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(ceiling))
    path.mkdir(parents=True)
    make_trail(path, with_task=with_task)
    (path / "src").mkdir()
    (path / "src" / "app.py").write_text("def run():\n    return 1\n")
    assert git.history_state(path) == "none"
    return path


@pytest.fixture
def history_spy(monkeypatch):
    calls = []
    real = git.history_state

    def spy(root):
        calls.append(root)
        return real(root)

    monkeypatch.setattr(git, "history_state", spy)
    return calls


# --- T3: the task gate (C5, A9) ---------------------------------------------

@pytest.mark.parametrize("shape", ["shallow", "no-git"])
def test_t3_no_plan_task_means_no_check_no_notice_keys_false(tmp_path, capsys, monkeypatch, history_spy, shape):
    if shape == "shallow":
        target = shallow_clone(make_origin(tmp_path / "origin", with_task=False), tmp_path / "clone")
    else:
        target = _no_git_dir(tmp_path / "zip", monkeypatch, tmp_path, with_task=False)
    history_spy.clear()

    _graph, report = build_graph(target)
    assert report.git_history is None
    rc, _out, err = _cli_build(capsys, target)
    assert rc == 0
    assert not any(n in err for n in NOTICES)
    resp = server.build_graph(path=str(target))
    assert resp["shallow_history"] is False
    assert resp["no_git_history"] is False
    assert history_spy == []


def test_t3_with_a_plan_task_exactly_one_check_per_build(tmp_path, history_spy):
    clone = shallow_clone(make_origin(tmp_path / "origin"), tmp_path / "clone")
    history_spy.clear()
    build_graph(clone)
    assert len(history_spy) == 1


# --- T4: no git history end to end (US-4) -----------------------------------

def test_t4_no_git_dir_names_missing_history_on_cli_and_mcp(tmp_path, capsys, monkeypatch):
    a = _no_git_dir(tmp_path / "zip_a", monkeypatch, tmp_path)
    b = tmp_path / "zip_b"
    shutil.copytree(a, b)

    rc, _out, err = _cli_build(capsys, a)
    assert rc == 0
    assert err.splitlines().count(NO_GIT_HISTORY_NOTICE) == 1
    assert SHALLOW_HISTORY_NOTICE not in err

    resp = server.build_graph(path=str(b))
    assert resp["no_git_history"] is True
    assert resp["shallow_history"] is False
    assert _graph_bytes(a) == _graph_bytes(b)


# --- T5: the CLI output contract -------------------------------------------

def test_t5_stdout_unchanged_notice_on_stderr_only(tmp_path, capsys):
    clone = shallow_clone(make_origin(tmp_path / "origin"), tmp_path / "clone")
    rc, out, _err = _cli_build(capsys, clone)
    assert rc == 0
    lines = out.splitlines()
    assert len(lines) == 2
    assert lines[0].startswith("Built graph: ") and lines[1].startswith("Saved to ")
    assert not any(n in out for n in NOTICES)


def test_t5_full_clone_has_empty_stderr(tmp_path, capsys):
    clone = full_clone(make_origin(tmp_path / "origin"), tmp_path / "clone")
    rc, _out, err = _cli_build(capsys, clone)
    assert rc == 0
    assert err == ""


def test_t5_notice_on_first_full_and_incremental_builds(tmp_path, capsys):
    clone = shallow_clone(make_origin(tmp_path / "origin"), tmp_path / "clone")
    for argv in ([clone], ["--full", clone], [clone]):  # first, --full, incremental (graph present)
        rc, out, err = _cli_build(capsys, *argv)
        assert rc == 0
        assert err.splitlines().count(SHALLOW_HISTORY_NOTICE) == 1
    assert "incremental" in out  # the last run really took the incremental path


def test_t5_notices_are_plain_text_without_paths():
    for notice in NOTICES:  # NFR-3 / NFR-5
        assert "\x1b" not in notice
        assert os.sep not in notice


# --- T6: the remedy round-trip and clone shapes with no notice ---------------

def test_t6_unshallow_then_rebuild_clears_notice_and_matches_full_clone(tmp_path, capsys):
    origin = make_origin(tmp_path / "origin")
    clone = shallow_clone(origin, tmp_path / "clone")
    full = full_clone(origin, tmp_path / "full")

    _rc, _out, err = _cli_build(capsys, clone)
    assert SHALLOW_HISTORY_NOTICE in err
    subprocess.run(["git", "-C", str(clone), "fetch", "-q", "--unshallow"],
                   check=True, capture_output=True, text=True)
    rc, _out, err = _cli_build(capsys, clone)
    assert rc == 0
    assert not any(n in err for n in NOTICES)

    unshallowed, _ = build_graph(clone)
    reference, _ = build_graph(full)
    assert queries.impact(unshallowed, ["src/app.py"]) == queries.impact(reference, ["src/app.py"])
    assert queries.impact(reference, ["src/app.py"])["affected_acs"]  # the comparison is not vacuous


@pytest.mark.parametrize("shape", ["detached", "single-branch"])
def test_t6_detached_head_and_single_branch_print_no_notice(tmp_path, capsys, shape):
    origin = make_origin(tmp_path / "origin")
    if shape == "detached":
        target = full_clone(origin, tmp_path / "clone")
        subprocess.run(["git", "-C", str(target), "checkout", "-q", "--detach", "HEAD~1"],
                       check=True, capture_output=True, text=True)
    else:
        target = full_clone(origin, tmp_path / "clone", "--single-branch")
    rc, _out, err = _cli_build(capsys, target)
    assert rc == 0
    assert not any(n in err for n in NOTICES)
