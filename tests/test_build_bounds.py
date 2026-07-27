"""T8/T9: the build walk's bounds (security-posture US-3, Should).

T8 covers the entry-count bound (AC-3.1): an oversized or cyclic walk refuses
before parsing rather than hanging. T9 adds the per-file size cap (AC-3.2)
and the symlink-cycle characterisation (AC-3.3). AC-3.4/NFR-2 (bounds change
no accepted repo's graph) is exercised by the existing determinism tests in
test_build.py staying green, plus the byte-identity checks here.
"""

from pathlib import Path

import pytest

from aspark_graph import cli, confinement, queries, server
from aspark_graph.build import build_graph
from aspark_graph.graph import default_graph_path

SAMPLE_REPO = Path(__file__).parent / "fixtures" / "sample_repo"


def _tiny_repo_over_bound(tmp_path, monkeypatch, limit=5):
    """A .git-marked repo with `limit + 1` files, under a MAX_ENTRIES lowered
    to `limit` — cheap and fast rather than writing 200,001 real files."""
    monkeypatch.setattr(confinement, "MAX_ENTRIES", limit)
    repo = tmp_path / "big"
    repo.mkdir()
    (repo / ".git").mkdir()
    for i in range(limit + 1):
        (repo / f"f{i}.py").write_text("x = 1\n")
    return repo


# --- AC-3.1: entry-count bound ----------------------------------------------


def test_build_over_the_bound_raises_repo_too_large(tmp_path, monkeypatch):
    repo = _tiny_repo_over_bound(tmp_path, monkeypatch)
    with pytest.raises(confinement.RepoTooLargeError):
        build_graph(repo)


def test_cli_build_over_the_bound_refuses_cleanly_naming_limit_and_count(tmp_path, monkeypatch, capsys):
    repo = _tiny_repo_over_bound(tmp_path, monkeypatch, limit=5)
    rc = cli.main(["build", str(repo)])
    assert rc == 1
    out, err = capsys.readouterr()
    assert out == ""
    lines = [l for l in err.splitlines() if l.strip()]
    assert len(lines) == 1
    assert "5" in lines[0]  # the limit
    assert "Traceback" not in err
    assert not default_graph_path(repo).exists()


def test_mcp_build_over_the_bound_returns_too_large(tmp_path, monkeypatch):
    repo = _tiny_repo_over_bound(tmp_path, monkeypatch, limit=5)
    result = server.build_graph(path=str(repo))
    assert result["found"] is False
    assert result["reason"] == "too_large"
    assert not default_graph_path(repo).exists()


def test_no_partial_graph_written_when_over_the_bound(tmp_path, monkeypatch):
    repo = _tiny_repo_over_bound(tmp_path, monkeypatch)
    with pytest.raises(confinement.RepoTooLargeError):
        build_graph(repo)
    assert not (repo / ".aspark-graph").exists()


def test_stopping_short_of_the_bound_still_builds_normally(tmp_path, monkeypatch):
    monkeypatch.setattr(confinement, "MAX_ENTRIES", 5)
    repo = tmp_path / "small"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "a.py").write_text("x = 1\n")
    graph, report = build_graph(repo)  # 2 entries (.git dir, a.py) — under 5
    assert report.code_entities > 0


# --- AC-3.4/NFR-2: the bound changes no accepted repo's graph ---------------


def test_sample_repo_builds_unaffected_by_the_real_bound():
    graph, report = build_graph(SAMPLE_REPO)  # real MAX_ENTRIES=200_000, far above
    assert report.code_entities > 0 or report.artifact_entities > 0


def test_sample_repo_double_build_still_byte_identical():
    g1, _ = build_graph(SAMPLE_REPO)
    g2, _ = build_graph(SAMPLE_REPO)
    assert g1.to_dict() == g2.to_dict()


# --- AC-3.2: per-file size cap ----------------------------------------------


def _repo_with_oversized_file(tmp_path, monkeypatch, cap_bytes=100):
    monkeypatch.setattr(confinement, "MAX_FILE_BYTES", cap_bytes)
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "small.py").write_text("def f():\n    return 1\n")
    (repo / "big.py").write_text("x = 1\n" * (cap_bytes // 4))  # > cap_bytes
    assert (repo / "big.py").stat().st_size > cap_bytes
    return repo


def test_oversized_file_becomes_unparsed_node_with_size_and_no_hash(tmp_path, monkeypatch):
    repo = _repo_with_oversized_file(tmp_path, monkeypatch)
    graph, report = build_graph(repo)

    node = graph.get_node("file:big.py")
    assert node is not None
    assert node["unparsed"] is True
    assert node["unparsed_reason"] == "size"
    assert node["size_bytes"] == (repo / "big.py").stat().st_size
    assert "hash" not in node
    assert report.size_skipped == 1
    assert "1 file(s) skipped" in report.summary()


def test_oversized_file_bytes_are_never_read(tmp_path, monkeypatch):
    repo = _repo_with_oversized_file(tmp_path, monkeypatch)
    real_read_bytes = Path.read_bytes

    def _guarded_read_bytes(self, *a, **kw):
        if self.name == "big.py":
            raise AssertionError("oversized file contents must never be read")
        return real_read_bytes(self, *a, **kw)

    monkeypatch.setattr(Path, "read_bytes", _guarded_read_bytes)
    graph, report = build_graph(repo)
    assert report.size_skipped == 1


def test_build_with_oversized_file_still_exits_zero(tmp_path, monkeypatch, capsys):
    repo = _repo_with_oversized_file(tmp_path, monkeypatch)
    rc = cli.main(["build", str(repo)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "skipped" in out.lower()


def test_staleness_treats_oversized_file_as_neither_changed_nor_missing(tmp_path, monkeypatch):
    repo = _repo_with_oversized_file(tmp_path, monkeypatch)
    graph, _ = build_graph(repo)
    result = queries.staleness(graph, repo)
    assert "big.py" not in result["changed"]
    assert "big.py" not in result["missing"]
    assert result["stale"] is False


def test_repos_with_no_oversized_file_are_unaffected_by_the_cap():
    # AC-3.4: the real 5MB cap changes nothing for sample_repo (no file near it).
    graph, report = build_graph(SAMPLE_REPO)
    assert report.size_skipped == 0


# --- AC-3.3: a symlink to an ancestor directory terminates ------------------


def test_symlink_to_ancestor_directory_terminates_and_reports(tmp_path):
    repo = tmp_path / "cyclic"
    (repo / "a" / "b").mkdir(parents=True)
    (repo / ".git").mkdir()
    (repo / "real.py").write_text("def f():\n    return 1\n")
    (repo / "a" / "b" / "cycle").symlink_to(repo, target_is_directory=True)

    # Must terminate (no infinite descent) and produce *a* result — either a
    # normal build, or a too_large refusal if the platform's rglob follows
    # the symlink and the entry-count bound (AC-3.1) catches it first. Either
    # outcome satisfies AC-3.3; what must never happen is a hang.
    try:
        graph, report = build_graph(repo)
        assert report.code_entities > 0
    except confinement.RepoTooLargeError:
        pass
