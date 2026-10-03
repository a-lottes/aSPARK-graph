"""T2: offline git helpers — correct on a real repo, graceful on a non-repo."""

import subprocess

import pytest

from aspark_graph import git as gitmod


def _git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


def _init_repo(root):
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "Test")
    _git(root, "config", "commit.gpgsign", "false")


def _commit(root, message):
    _git(root, "add", "-A")
    subprocess.run(
        ["git", "-C", str(root), "commit", "-q", "-m", message],
        check=True, capture_output=True, text=True,
        env={"GIT_AUTHOR_DATE": "2026-01-01T00:00:00", "GIT_COMMITTER_DATE": "2026-01-01T00:00:00",
             "PATH": __import__("os").environ["PATH"], "HOME": str(root)},
    )


@pytest.fixture
def repo(tmp_path):
    _init_repo(tmp_path)
    (tmp_path / "a.py").write_text("x = 1\n")
    _commit(tmp_path, "T1: add a (US-1)")
    (tmp_path / "b.py").write_text("y = 2\n")
    _commit(tmp_path, "T2: add b (US-2)")
    (tmp_path / "c.py").write_text("z = 3\n")
    _commit(tmp_path, "chore: no id here")
    return tmp_path


def test_is_git_repo(repo, tmp_path):
    assert gitmod.is_git_repo(repo) is True


def test_non_git_dir_is_graceful(tmp_path):
    d = tmp_path / "plain"
    d.mkdir()
    assert gitmod.is_git_repo(d) is False
    assert gitmod.commits_touching(d, {"T1"}) == {}
    files, err = gitmod.diff_files(d, "HEAD~1..HEAD")
    assert files == [] and err is not None


def test_commits_touching_matches_by_id(repo):
    result = gitmod.commits_touching(repo, {"T1", "US-1", "T2", "US-2"})
    assert result["T1"] == ["a.py"]
    assert result["US-1"] == ["a.py"]
    assert result["T2"] == ["b.py"]
    # c.py's commit referenced no id -> not attributed to anything.
    assert "c.py" not in {f for files in result.values() for f in files}


def test_commits_touching_word_boundary(repo, tmp_path):
    # "T1" must not match "T10"/"US-10".
    (repo / "d.py").write_text("w = 4\n")
    _commit(repo, "T10: unrelated (US-10)")
    result = gitmod.commits_touching(repo, {"T1", "US-1"})
    assert "d.py" not in result.get("T1", [])
    assert "d.py" not in result.get("US-1", [])


def test_commits_touching_empty_ids(repo):
    assert gitmod.commits_touching(repo, set()) == {}


def test_diff_files_resolves_range(repo):
    files, err = gitmod.diff_files(repo, "HEAD~1..HEAD")
    assert err is None
    assert files == ["c.py"]


def test_diff_files_bad_range(repo):
    files, err = gitmod.diff_files(repo, "not-a-real-ref..HEAD")
    assert files == [] and err is not None


def test_diff_files_empty_range(repo):
    files, err = gitmod.diff_files(repo, "   ")
    assert files == [] and "empty" in err.lower()


def test_diff_files_bare_filename_is_not_silently_a_pathspec(repo):
    # F2: a bare filename must not be read as a pathspec (empty success) — the
    # `--` separator forces it to be parsed as a revision, which fails cleanly.
    (repo / "a.py").write_text("x = 99\n")  # a.py exists as a file
    files, err = gitmod.diff_files(repo, "a.py")
    assert err is not None
    assert files == []


# --- shallow-clone-warning T2: history_state across repo shapes ------------

from conftest import full_clone, make_origin, shallow_clone  # noqa: E402


def _no_enclosing_repo(monkeypatch, tmp_path):
    """Plan R2: stop git's upward search at tmp_path, then prove the
    precondition, so a host tmp inside some work tree can't fake a result."""
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))


def _assert_not_a_work_tree(path):
    proc = subprocess.run(["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
                          capture_output=True, text=True)
    assert proc.returncode != 0 or proc.stdout.strip() != "true"


@pytest.fixture
def origin(tmp_path):
    return make_origin(tmp_path / "origin")


def test_history_state_full_repo(origin):
    assert gitmod.history_state(origin) == "full"


def test_history_state_shallow_clone(origin, tmp_path):
    assert gitmod.history_state(shallow_clone(origin, tmp_path / "c")) == "shallow"


def test_history_state_subdir_of_full_clone(origin):
    assert gitmod.history_state(origin / "src") == "full"  # A7


def test_history_state_subdir_of_shallow_clone(origin, tmp_path):
    clone = shallow_clone(origin, tmp_path / "c")
    assert gitmod.history_state(clone / "src") == "shallow"


def test_history_state_plain_dir_is_none(tmp_path, monkeypatch):
    _no_enclosing_repo(monkeypatch, tmp_path)
    plain = tmp_path / "plain"
    plain.mkdir()
    _assert_not_a_work_tree(plain)
    assert gitmod.history_state(plain) == "none"


def test_history_state_corrupt_git_is_none(tmp_path, monkeypatch):
    _no_enclosing_repo(monkeypatch, tmp_path)
    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / ".git").write_text("gitdir: /nonexistent/aspark-graph-test\n")
    _assert_not_a_work_tree(broken)
    assert gitmod.history_state(broken) == "none"


def test_history_state_without_git_binary_is_none(origin, monkeypatch):
    monkeypatch.setenv("PATH", "")  # A8: no git binary → typed result, no raise
    assert gitmod.history_state(origin) == "none"


def test_history_state_detached_head_is_full(origin):
    _git(origin, "checkout", "-q", "--detach", "HEAD~1")
    assert gitmod.history_state(origin) == "full"


def test_history_state_single_branch_full_depth_is_full(origin, tmp_path):
    clone = full_clone(origin, tmp_path / "c", "--single-branch")
    assert gitmod.history_state(clone) == "full"


def test_history_state_zero_commit_repo_is_full(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    _init_repo(empty)
    assert gitmod.history_state(empty) == "full"  # spec §6: no notice


def test_history_state_makes_exactly_one_local_git_call(origin, tmp_path, monkeypatch):
    """NFR-1/NFR-2: one call per check, and nothing that talks to a remote."""
    calls = []
    real = gitmod._run

    def spy(root, args):
        calls.append(args)
        return real(root, args)

    monkeypatch.setattr(gitmod, "_run", spy)
    for target in (origin, shallow_clone(origin, tmp_path / "c")):
        calls.clear()
        gitmod.history_state(target)
        assert len(calls) == 1
        assert calls[0][0] == "rev-parse"
        assert not any(w in a for a in calls[0] for w in ("fetch", "remote", "clone", "pull", "://"))
