"""T1: the confinement rule in isolation (security-posture US-1).

Covers AC-1.4 (accepted marker shapes), AC-1.5 (refused/OS-error shapes, never
a raw traceback), AC-1.6 (symlink resolved before the verdict) and AC-1.11
(graph.json marker is existence-only, never opened).
"""

import os
import sys

import pytest

from aspark_graph.confinement import (
    GRAPH_DIRNAME,
    GRAPH_FILENAME,
    OutsideConfinementError,
    RepoRefused,
    RepoTooLargeError,
    ensure_repo,
)


def _unmarked(tmp_path):
    """A subdirectory with none of the three markers. `tmp_path` itself is
    auto-marked with an empty .spark/ (conftest.py, security-posture US-1),
    so tests that need a genuinely unmarked target use their own subdir."""
    d = tmp_path / "unmarked"
    d.mkdir()
    return d


# --- accepted shapes (AC-1.4, AC-1.11) --------------------------------------


def test_git_directory_is_accepted(tmp_path):
    repo = _unmarked(tmp_path)
    (repo / ".git").mkdir()
    assert ensure_repo(repo) == repo.resolve()


def test_git_file_is_accepted(tmp_path):  # worktree / submodule
    repo = _unmarked(tmp_path)
    (repo / ".git").write_text("gitdir: ../elsewhere/.git\n")
    assert ensure_repo(repo) == repo.resolve()


def test_spark_directory_is_accepted(tmp_path):
    (tmp_path / ".spark").mkdir(exist_ok=True)  # already present via the autouse fixture
    assert ensure_repo(tmp_path) == tmp_path.resolve()


def test_graph_json_file_is_accepted(tmp_path):
    repo = _unmarked(tmp_path)
    graph_dir = repo / GRAPH_DIRNAME
    graph_dir.mkdir()
    (graph_dir / GRAPH_FILENAME).write_text("{}")
    assert ensure_repo(repo) == repo.resolve()


def test_garbage_graph_json_is_still_accepted(tmp_path):  # existence only, never parsed
    repo = _unmarked(tmp_path)
    graph_dir = repo / GRAPH_DIRNAME
    graph_dir.mkdir()
    (graph_dir / GRAPH_FILENAME).write_text("not json at all {{{")
    assert ensure_repo(repo) == repo.resolve()


def test_empty_graph_json_is_still_accepted(tmp_path):
    repo = _unmarked(tmp_path)
    graph_dir = repo / GRAPH_DIRNAME
    graph_dir.mkdir()
    (graph_dir / GRAPH_FILENAME).write_text("")
    assert ensure_repo(repo) == repo.resolve()


def test_graph_json_never_opened(tmp_path, monkeypatch):
    repo = _unmarked(tmp_path)
    graph_dir = repo / GRAPH_DIRNAME
    graph_dir.mkdir()
    (graph_dir / GRAPH_FILENAME).write_text("{}")

    def _boom(*a, **kw):
        raise AssertionError("graph.json must not be opened by the confinement check")

    monkeypatch.setattr("builtins.open", _boom)
    monkeypatch.setattr("pathlib.Path.read_bytes", _boom)
    monkeypatch.setattr("pathlib.Path.read_text", _boom)
    assert ensure_repo(repo) == repo.resolve()


# --- refused shapes (AC-1.5) -------------------------------------------------


def test_aspark_graph_dir_without_graph_json_is_refused(tmp_path):
    repo = _unmarked(tmp_path)
    (repo / GRAPH_DIRNAME).mkdir()  # no graph.json inside
    with pytest.raises(OutsideConfinementError):
        ensure_repo(repo)


def test_empty_directory_is_refused(tmp_path):
    with pytest.raises(OutsideConfinementError):
        ensure_repo(_unmarked(tmp_path))


def test_missing_path_is_refused(tmp_path):
    with pytest.raises(OutsideConfinementError):
        ensure_repo(tmp_path / "does-not-exist")


def test_regular_file_is_refused(tmp_path):
    f = tmp_path / "not-a-dir.txt"
    f.write_text("hello")
    with pytest.raises(OutsideConfinementError):
        ensure_repo(f)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permission bits")
@pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses permission checks")
def test_unreadable_directory_is_refused_not_a_permission_error(tmp_path):
    locked = _unmarked(tmp_path) / "locked"
    locked.mkdir()
    locked.chmod(0o000)
    try:
        with pytest.raises(OutsideConfinementError):
            ensure_repo(locked)
    finally:
        locked.chmod(0o700)  # restore so pytest can clean up tmp_path


def test_refusal_names_path_and_rule(tmp_path):
    repo = _unmarked(tmp_path)
    with pytest.raises(OutsideConfinementError) as exc_info:
        ensure_repo(repo)
    message = str(exc_info.value)
    assert str(repo.resolve()) in message
    assert ".git" in message and ".spark" in message


def test_refused_errors_are_never_raw_os_errors(tmp_path):
    # None of the OS-level exception types this rule exists to hide leak through.
    for target in (tmp_path / "missing", _unmarked(tmp_path)):
        try:
            ensure_repo(target)
        except OutsideConfinementError:
            pass
        except (FileNotFoundError, NotADirectoryError, PermissionError):
            pytest.fail("a raw OS error leaked out of ensure_repo")


# --- symlinks (AC-1.6) -------------------------------------------------------


def test_symlink_to_marked_directory_is_accepted(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    (real / ".git").mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    assert ensure_repo(link) == real.resolve()


def test_symlink_to_unmarked_directory_is_refused(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    with pytest.raises(OutsideConfinementError):
        ensure_repo(link)


# --- reason vocabulary --------------------------------------------------------


def test_reason_values_are_distinct():
    assert OutsideConfinementError("x").reason == "outside_confinement"
    assert RepoTooLargeError("x").reason == "too_large"
    assert issubclass(OutsideConfinementError, RepoRefused)
    assert issubclass(RepoTooLargeError, RepoRefused)
