"""shallow-clone-warning US-5: truncated history never invents inferred links.

In a shallow clone git lists every tracked file as added by the grafted
boundary commit. Inference skips those commits, so a shallow build can only
lose `inferred` edges compared with a full clone, never gain any.
"""

import json

from aspark_graph import cli

from conftest import full_clone, make_boundary_origin, shallow_clone


def _inferred(root):
    """The (task, file) pairs of every `inferred` implements edge in graph.json."""
    data = json.loads((root / ".aspark-graph" / "graph.json").read_text())
    return {
        (e["source"].split(":")[-1], e["target"].removeprefix("file:"))
        for e in data["edges"]
        if e.get("type") == "implements" and e.get("confidence") == "inferred"
    }


def test_t10_depth1_boundary_tip_adds_no_inferred_edge(tmp_path, capsys):
    origin = make_boundary_origin(tmp_path / "origin")
    shallow = shallow_clone(origin, tmp_path / "shallow")
    full = full_clone(origin, tmp_path / "full")

    assert cli.main(["build", str(full)]) == 0
    assert ("T1", "src/a.py") in _inferred(full)  # the check below is not vacuous

    for argv in (["--full", str(shallow)], [str(shallow)]):  # full, then incremental
        assert cli.main(["build", *argv]) == 0
        assert not any(task == "T1" for task, _ in _inferred(shallow))
    capsys.readouterr()


# --- T12: subset, kept commits, genuine root commit, determinism ------------

import shutil  # noqa: E402

import pytest  # noqa: E402

from aspark_graph import git, server  # noqa: E402
from aspark_graph.build import NO_GIT_HISTORY_NOTICE, SHALLOW_HISTORY_NOTICE  # noqa: E402

from conftest import git_commit, init_git_repo, make_trail  # noqa: E402


def _edges(root, *, inferred):
    data = json.loads((root / ".aspark-graph" / "graph.json").read_text())
    return sorted(
        json.dumps(e, sort_keys=True) for e in data["edges"]
        if (e.get("confidence") == "inferred") == inferred
    )


def _build(capsys, *argv):
    rc = cli.main(["build", *map(str, argv)])
    out, err = capsys.readouterr()
    return rc, out, err


def test_t12_shallow_inferred_is_subset_and_other_edges_equal(tmp_path, capsys):
    origin = make_boundary_origin(tmp_path / "origin")
    shallow = shallow_clone(origin, tmp_path / "shallow")
    full = full_clone(origin, tmp_path / "full")
    _build(capsys, shallow)
    _build(capsys, full)
    assert _inferred(shallow) <= _inferred(full)                          # AC-5.2
    assert _edges(shallow, inferred=False) == _edges(full, inferred=False)


def test_t12_depth3_keeps_exactly_the_newer_commits_links(tmp_path, capsys):
    origin = make_boundary_origin(tmp_path / "origin")
    depth3 = shallow_clone(origin, tmp_path / "d3", "--depth", "3")
    full = full_clone(origin, tmp_path / "full")
    _build(capsys, depth3)
    _build(capsys, full)
    assert _inferred(depth3) == {("T1", "src/a.py"), ("T2", "src/c.py")}  # AC-5.3
    assert ("T2", "src/b.py") in _inferred(full)                          # only the boundary c3 gave it
    assert _inferred(depth3) <= _inferred(full)


def test_t12_genuine_root_commit_of_a_full_repo_still_counts(tmp_path, capsys):
    repo = tmp_path / "rooted"
    repo.mkdir()
    init_git_repo(repo)
    make_trail(repo)
    (repo / "src").mkdir()
    (repo / "src" / "x.py").write_text("X = 1\n")
    git_commit(repo, "T1: initial (US-1)")                                # the root, not a graft
    _build(capsys, repo)
    assert ("T1", "src/x.py") in _inferred(repo)                          # AC-5.5


@pytest.mark.parametrize("depth", ["1", "3"])
def test_t12_shallow_builds_are_deterministic(tmp_path, capsys, depth):
    clone = shallow_clone(make_boundary_origin(tmp_path / "origin"), tmp_path / "c", "--depth", depth)
    graph = clone / ".aspark-graph" / "graph.json"
    _build(capsys, "--full", clone)
    first = graph.read_bytes()
    _build(capsys, "--full", clone)
    assert graph.read_bytes() == first


# --- T13: an undeterminable boundary drops all inferred edges (C12) ---------

def test_t13_stubbed_unreadable_boundary_adds_no_inferred_edge(tmp_path, capsys, monkeypatch):
    clone = shallow_clone(make_boundary_origin(tmp_path / "origin"), tmp_path / "c", "--depth", "3")
    monkeypatch.setattr(git, "read_history", lambda root: git.GitHistory("shallow", None))
    rc, _out, err = _build(capsys, clone)
    assert rc == 0
    assert _inferred(clone) == set()
    assert err.splitlines().count(SHALLOW_HISTORY_NOTICE) == 1


def test_t13_corrupt_shallow_file_never_raises_and_invents_nothing(tmp_path, capsys):
    a = shallow_clone(make_boundary_origin(tmp_path / "origin"), tmp_path / "a", "--depth", "3")
    b = tmp_path / "b"
    shutil.copytree(a, b)
    for clone in (a, b):
        (clone / ".git" / "shallow").write_text("this is not a sha\n")

    rc, _out, err = _build(capsys, a)
    assert rc == 0
    assert "Traceback" not in err
    assert _inferred(a) == set()
    notices = [n for n in (SHALLOW_HISTORY_NOTICE, NO_GIT_HISTORY_NOTICE) if n in err.splitlines()]
    assert len(notices) <= 1
    resp = server.build_graph(path=str(b))
    assert (SHALLOW_HISTORY_NOTICE in err) == resp["shallow_history"]
    assert (NO_GIT_HISTORY_NOTICE in err) == resp["no_git_history"]
    # R9, observed with git 2.39: rev-parse itself fails on a corrupt graft
    # list, so the build reads "none" and names it as missing history.
    assert (resp["shallow_history"], resp["no_git_history"]) == (False, True)
