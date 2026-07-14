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
