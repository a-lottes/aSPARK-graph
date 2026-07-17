"""Tests for the incremental build feature (incremental-builds, T1-T9).

T1: walking skeleton, FileExtraction round-trip, full-then-incremental parity.
T2: change detection + reuse accounting.
T3: add / delete / rename correctness.
T4: graph.json anchor + first-build path.
T5: corrupt / unreadable cache fallback.
T6: version-tag invalidation.
T7: --full CLI flag.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from aspark_graph.build import build_graph, BuildReport
from aspark_graph.extractors.base import Definition, FileExtraction, Import
from aspark_graph.graph import default_graph_path
from aspark_graph import parse_cache


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_repo(root: Path, n_files: int = 3) -> list[Path]:
    """Write n_files simple Python source files; return their paths."""
    files = []
    for i in range(n_files):
        p = root / f"mod_{i}.py"
        p.write_text(f"def f_{i}():\n    return {i}\n")
        files.append(p)
    return files


def _full_build(root: Path) -> tuple:
    """Build and save graph.json (satisfies anchor rule for incremental path)."""
    graph, report = build_graph(root, full=True)
    graph.save(default_graph_path(root))
    return graph, report


# ---------------------------------------------------------------------------
# T1: FileExtraction round-trip (serializer contract guard)
# ---------------------------------------------------------------------------

class TestFilExtractionRoundTrip:
    def test_simple_python_file(self):
        original = FileExtraction(
            relpath="src/foo.py",
            language="python",
            definitions=[
                Definition(qualname="Foo", kind="Class", line=1),
                Definition(qualname="Foo.bar", kind="Function", line=3, parent="Foo"),
            ],
            imports=[
                Import(module="os"),
                Import(module=".utils", relative=True),
            ],
            package=None,
        )
        # Serialize into the cache dict format, then deserialize.
        serialized = parse_cache._serialize_extraction(original, sha256="deadbeef")
        restored = parse_cache._deserialize_extraction("src/foo.py", serialized)

        assert restored.relpath == original.relpath
        assert restored.language == original.language
        assert restored.package == original.package
        assert len(restored.definitions) == 2
        assert restored.definitions[0].qualname == "Foo"
        assert restored.definitions[0].kind == "Class"
        assert restored.definitions[0].line == 1
        assert restored.definitions[0].parent is None
        assert restored.definitions[0].exported is True
        assert restored.definitions[1].qualname == "Foo.bar"
        assert restored.definitions[1].parent == "Foo"
        assert len(restored.imports) == 2
        assert restored.imports[0].module == "os"
        assert restored.imports[0].relative is False
        assert restored.imports[1].module == ".utils"
        assert restored.imports[1].relative is True

    def test_java_file_with_package(self):
        original = FileExtraction(
            relpath="src/com/example/Foo.java",
            language="java",
            definitions=[Definition(qualname="Foo", kind="Class", line=5)],
            imports=[Import(module="com.example.Bar")],
            package="com.example",
        )
        serialized = parse_cache._serialize_extraction(original, sha256="abc123")
        restored = parse_cache._deserialize_extraction("src/com/example/Foo.java", serialized)
        assert restored.package == "com.example"
        assert restored.definitions[0].qualname == "Foo"

    def test_empty_file(self):
        original = FileExtraction(relpath="empty.py", language="python")
        serialized = parse_cache._serialize_extraction(original, sha256="00000000")
        restored = parse_cache._deserialize_extraction("empty.py", serialized)
        assert restored.definitions == []
        assert restored.imports == []
        assert restored.package is None


# ---------------------------------------------------------------------------
# T1: double-build determinism (the two existing tests stay green; new parity)
# ---------------------------------------------------------------------------

def test_double_build_is_deterministic_with_cache(tmp_path):
    """Existing double-build contract still holds with the cache in place."""
    _write_repo(tmp_path)
    g1, _ = _full_build(tmp_path)
    g2, _ = build_graph(tmp_path)
    assert g1.to_dict() == g2.to_dict()
    p1 = g1.save(tmp_path / "run1" / "graph.json")
    p2 = g2.save(tmp_path / "run2" / "graph.json")
    assert p1.read_text() == p2.read_text()


def test_full_then_incremental_parity(tmp_path):
    """AC-2.2: incremental build on unchanged repo == full rescan (byte-identical)."""
    _write_repo(tmp_path)
    # First build: full rescan, produces graph.json and cache.
    g_full, _ = _full_build(tmp_path)
    full_text = default_graph_path(tmp_path).read_text()

    # Second build (incremental): cache exists, no files changed.
    g_inc, report = build_graph(tmp_path)
    inc_text = g_inc.save(tmp_path / "inc" / "graph.json").read_text()

    assert inc_text == full_text, "incremental build must produce byte-identical graph.json"
    assert report.incremental is True
    assert report.cached > 0
    assert report.reparsed == 0


# ---------------------------------------------------------------------------
# T2: change detection + reuse accounting
# ---------------------------------------------------------------------------

def test_unchanged_repo_reparsed_zero(tmp_path):
    """AC-1.3: zero files reparsed when nothing changed."""
    files = _write_repo(tmp_path, n_files=4)
    _full_build(tmp_path)

    _, report = build_graph(tmp_path)
    assert report.reparsed == 0
    assert report.cached == len(files)


def test_one_changed_file_reparsed_exactly_one(tmp_path):
    """AC-1.1: exactly one file reparsed when one file changed."""
    files = _write_repo(tmp_path, n_files=4)
    _full_build(tmp_path)

    # Mutate exactly one file.
    files[0].write_text("def changed():\n    return 99\n")

    _, report = build_graph(tmp_path)
    assert report.reparsed == 1
    assert report.cached == len(files) - 1
    assert report.incremental is True


def test_changed_file_hash_updated_in_graph(tmp_path):
    """AC-1.4: after incremental build, staleness query reports current."""
    (tmp_path / "a.py").write_text("x = 1\n")
    _full_build(tmp_path)

    (tmp_path / "a.py").write_text("x = 2\n")
    graph, _ = build_graph(tmp_path)

    # The file node's hash in the graph must reflect the new content.
    import hashlib
    new_digest = hashlib.sha256(b"x = 2\n").hexdigest()[:16]
    node = graph.get_node("file:a.py")
    assert node is not None
    assert node["hash"] == new_digest


# ---------------------------------------------------------------------------
# T3: add / delete / rename correctness
# ---------------------------------------------------------------------------

def test_new_file_added_between_builds(tmp_path):
    """AC-3.4 (add): a newly-added file's nodes appear after incremental build."""
    (tmp_path / "existing.py").write_text("def f(): pass\n")
    _full_build(tmp_path)

    (tmp_path / "new_file.py").write_text("def g(): pass\n")
    graph, report = build_graph(tmp_path)

    assert graph.has_node("file:new_file.py")
    assert graph.has_node("file:existing.py")
    assert report.reparsed == 1   # only new_file.py was parsed
    assert report.cached == 1     # existing.py reused


def test_deleted_file_nodes_gone_after_build(tmp_path):
    """AC-3.4 (delete): a deleted file's nodes are removed after incremental build."""
    (tmp_path / "keep.py").write_text("def k(): pass\n")
    (tmp_path / "delete_me.py").write_text("def d(): pass\n")
    _full_build(tmp_path)

    (tmp_path / "delete_me.py").unlink()
    graph, _ = build_graph(tmp_path)

    assert graph.has_node("file:keep.py")
    assert not graph.has_node("file:delete_me.py"), "ghost node must not remain"


def test_rename_is_delete_plus_add(tmp_path):
    """AC-3.4 (rename): rename = delete old relpath + add new relpath."""
    (tmp_path / "old_name.py").write_text("def r(): pass\n")
    (tmp_path / "other.py").write_text("def o(): pass\n")
    _full_build(tmp_path)

    (tmp_path / "old_name.py").rename(tmp_path / "new_name.py")
    graph, _ = build_graph(tmp_path)

    assert not graph.has_node("file:old_name.py"), "old node must not linger"
    assert graph.has_node("file:new_name.py")

    # Result must be byte-identical to a full rescan of the post-rename state.
    inc_text = graph.save(tmp_path / "inc" / "graph.json").read_text()
    full_graph, _ = build_graph(tmp_path, full=True)
    full_text = full_graph.save(tmp_path / "full" / "graph.json").read_text()
    assert inc_text == full_text


# ---------------------------------------------------------------------------
# T4: graph.json anchor + first-build path
# ---------------------------------------------------------------------------

def test_first_build_no_cache_no_error(tmp_path):
    """AC-3.1: first-ever build behaves exactly as the pre-feature build."""
    _write_repo(tmp_path)
    assert not default_graph_path(tmp_path).exists()

    graph, report = build_graph(tmp_path)

    assert report.code_entities > 0
    assert report.fallback_reason is None
    assert report.incremental is False  # no cache was available (first build)


def test_first_build_without_graph_json_skips_cache(tmp_path):
    """AC-3.5 anchor: even if a cache file is left over, no graph.json -> full rescan."""
    _write_repo(tmp_path)
    # Manually write a cache without graph.json existing.
    cache_dir = tmp_path / ".aspark-graph"
    cache_dir.mkdir()
    (cache_dir / "parse-cache.json").write_text('{"version": "anything", "entries": {}}')

    _, report = build_graph(tmp_path)
    assert report.incremental is False  # graph.json absent → full rescan, cache not used


# ---------------------------------------------------------------------------
# T5: corrupt / unreadable cache fallback
# ---------------------------------------------------------------------------

def test_corrupt_cache_falls_back_to_full_rescan(tmp_path):
    """AC-3.2: corrupt cache → fallback to full rescan, exit 0, correct graph."""
    _write_repo(tmp_path)
    _full_build(tmp_path)  # produces valid cache + graph.json

    # Corrupt the cache.
    cache_path = tmp_path / ".aspark-graph" / "parse-cache.json"
    cache_path.write_text("this is not json {{{{")

    graph, report = build_graph(tmp_path)

    # Fallback fired.
    assert report.fallback_reason is not None
    assert "corrupt" in report.fallback_reason
    assert report.incremental is False
    # Graph is still correct (full rescan).
    assert report.code_entities > 0


def test_corrupt_cache_fallback_notice_on_stderr(tmp_path, capsys):
    """AC-3.2: one-line stderr notice is emitted on fallback (via CLI)."""
    from aspark_graph.cli import main as cli_main
    _write_repo(tmp_path)
    cli_main(["build", str(tmp_path)])

    # Corrupt the cache.
    (tmp_path / ".aspark-graph" / "parse-cache.json").write_text("CORRUPT")

    cli_main(["build", str(tmp_path)])
    captured = capsys.readouterr()
    assert "Cache unusable" in captured.err
    assert "fell back" in captured.err


def test_malformed_entry_body_degrades_to_cache_miss(tmp_path):
    """F1 fix: malformed entry body with valid version tag → cache miss, no traceback."""
    (tmp_path / "good.py").write_text("def g(): pass\n")
    (tmp_path / "bad.py").write_text("def b(): pass\n")
    _full_build(tmp_path)

    # Corrupt just one entry body (drop required 'language' key).
    cache_path = tmp_path / ".aspark-graph" / "parse-cache.json"
    data = json.loads(cache_path.read_text())
    entry = data["entries"].get("bad.py", {})
    entry.pop("language", None)
    data["entries"]["bad.py"] = entry
    cache_path.write_text(json.dumps(data) + "\n")

    # Must not traceback; bad.py should be re-parsed (cache miss), good.py reused.
    graph, report = build_graph(tmp_path)
    assert report.incremental is True
    assert graph.has_node("file:bad.py")
    assert graph.has_node("file:good.py")
    # bad.py was a miss, good.py was a hit → reparsed=1, cached=1
    assert report.reparsed == 1
    assert report.cached == 1


def test_truncated_cache_falls_back(tmp_path):
    """AC-3.2 variant: truncated (empty) cache file is treated as corrupt."""
    _write_repo(tmp_path)
    _full_build(tmp_path)

    (tmp_path / ".aspark-graph" / "parse-cache.json").write_bytes(b"")
    _, report = build_graph(tmp_path)
    assert report.fallback_reason is not None
    assert report.incremental is False


# ---------------------------------------------------------------------------
# T6: version-tag invalidation
# ---------------------------------------------------------------------------

def test_version_mismatch_triggers_fallback(tmp_path):
    """AC-2.4 / AC-3.3: cache with a different version tag triggers full rescan."""
    _write_repo(tmp_path)
    _full_build(tmp_path)

    # Overwrite the version tag with a stale value.
    cache_path = tmp_path / ".aspark-graph" / "parse-cache.json"
    data = json.loads(cache_path.read_text())
    data["version"] = "aspark-graph=0.0.0:tree-sitter=0.0.0:tree-sitter-python=0.0.0:tree-sitter-typescript=0.0.0:tree-sitter-java=0.0.0"
    cache_path.write_text(json.dumps(data) + "\n")

    _, report = build_graph(tmp_path)
    assert report.fallback_reason is not None
    assert "version mismatch" in report.fallback_reason
    assert report.incremental is False


def test_stale_version_results_not_served(tmp_path):
    """AC-3.3: parse results from a different version tag are never served."""
    (tmp_path / "a.py").write_text("def a(): pass\n")
    _full_build(tmp_path)

    # Mutate the file AND stamp the cache with a stale version so the cache
    # would be consulted by a naive implementation.
    (tmp_path / "a.py").write_text("def b(): pass\n")  # different content
    cache_path = tmp_path / ".aspark-graph" / "parse-cache.json"
    data = json.loads(cache_path.read_text())
    data["version"] = "stale-version"
    cache_path.write_text(json.dumps(data) + "\n")

    graph, report = build_graph(tmp_path)
    # Must have fallen back and re-parsed with the new content.
    assert report.incremental is False
    assert graph.has_node("file:a.py")
    # The node must reflect the *new* content (def b, not def a).
    assert not graph.has_node("def:a.py::a"), "stale cached extraction must not be served"
    assert graph.has_node("def:a.py::b")


# ---------------------------------------------------------------------------
# T7: --full CLI flag
# ---------------------------------------------------------------------------

def test_full_flag_ignores_cache(tmp_path):
    """AC-4.1: build --full rescans everything regardless of cached state."""
    _write_repo(tmp_path, n_files=3)
    _full_build(tmp_path)

    _, report = build_graph(tmp_path, full=True)
    assert report.incremental is False
    assert report.reparsed == 3
    assert report.cached == 0


def test_full_flag_replaces_cache(tmp_path):
    """AC-4.2: after --full, cache holds fresh state for the next incremental build."""
    _write_repo(tmp_path, n_files=2)
    _full_build(tmp_path)

    # Corrupt the cache to prove --full overwrites it.
    cache_path = tmp_path / ".aspark-graph" / "parse-cache.json"
    cache_path.write_text("CORRUPT")

    build_graph(tmp_path, full=True)  # --full should replace the corrupt cache

    # Now an incremental build must succeed and use the fresh cache.
    _, report = build_graph(tmp_path)
    assert report.incremental is True
    assert report.reparsed == 0


def test_full_flag_no_prior_state(tmp_path):
    """AC-4.3: build --full with no prior state behaves identically to plain build."""
    _write_repo(tmp_path)
    assert not default_graph_path(tmp_path).exists()

    _, report_full = build_graph(tmp_path, full=True)
    assert report_full.code_entities > 0
    assert report_full.fallback_reason is None


def test_full_flag_via_cli(tmp_path, capsys):
    """AC-4.1: --full via CLI produces correct graph and no fallback notice."""
    from aspark_graph.cli import main as cli_main
    _write_repo(tmp_path)
    cli_main(["build", str(tmp_path)])           # warm cache
    cli_main(["build", "--full", str(tmp_path)]) # force full rescan
    captured = capsys.readouterr()
    assert "Cache unusable" not in captured.err
    assert "Built graph" in captured.out


# ---------------------------------------------------------------------------
# T1: incremental path produces correct graph for all prior queries
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# T9: BuildReport.summary() extension (AC-5.1, AC-5.2)
# ---------------------------------------------------------------------------

def test_summary_full_rescan_says_full(tmp_path):
    """AC-5.2: full-rescan summary says 'full rescan', no 'cached' count."""
    _write_repo(tmp_path)
    _, report = build_graph(tmp_path)  # first build → full rescan
    s = report.summary()
    assert "full rescan" in s
    assert "cached" not in s


def test_summary_incremental_reports_counts(tmp_path):
    """AC-5.1: incremental summary reports re-parsed and cached counts."""
    files = _write_repo(tmp_path, n_files=3)
    _full_build(tmp_path)
    files[0].write_text("def mutated(): pass\n")  # change one file

    _, report = build_graph(tmp_path)
    s = report.summary()
    assert "incremental" in s
    assert "1 re-parsed" in s
    assert "2 cached" in s
    assert "full rescan" not in s


def test_summary_fallback_not_labeled_incremental(tmp_path):
    """AC-5.2: fallback-to-full summary does not say 'cached'."""
    _write_repo(tmp_path)
    _full_build(tmp_path)
    (tmp_path / ".aspark-graph" / "parse-cache.json").write_text("CORRUPT")

    _, report = build_graph(tmp_path)
    s = report.summary()
    assert "full rescan" in s
    assert "cached" not in s


# ---------------------------------------------------------------------------
# AC-2.3: incremental path produces correct graph for all prior queries
# ---------------------------------------------------------------------------

def test_incremental_build_queries_correct(tmp_path):
    """AC-2.3: query results after incremental build match full rescan."""
    (tmp_path / "a.py").write_text("from b import g\ndef f(): pass\n")
    (tmp_path / "b.py").write_text("def g(): pass\n")
    _full_build(tmp_path)

    # Incremental build (nothing changed).
    graph, report = build_graph(tmp_path)
    assert report.incremental is True

    # Full rescan for comparison.
    full_graph, _ = build_graph(tmp_path, full=True)

    assert graph.to_dict() == full_graph.to_dict()
