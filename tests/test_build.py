"""T4: build command completeness — counts, determinism, code-only path.

Covers AC-1.1 (reports both counts), AC-1.2 (deterministic double-build) and
AC-1.4 (no .spark/ → code-only, zero artifact entities, no error).
"""

from aspark_graph.build import build_graph
from aspark_graph.graph import Graph, default_graph_path


def _write_code_repo(tmp_path):
    (tmp_path / "a.py").write_text("def f():\n    return 1\n")
    (tmp_path / "b.py").write_text("class B:\n    pass\n")
    return tmp_path


def test_build_reports_both_counts(tmp_path):  # AC-1.1
    _write_code_repo(tmp_path)
    _, report = build_graph(tmp_path)
    assert report.code_entities > 0
    assert hasattr(report, "artifact_entities")
    assert report.artifact_entities == 0  # no parser wired here; T5 makes it non-zero
    assert "code entities" in report.summary()
    assert "artifact entities" in report.summary()


def test_no_spark_builds_code_only(tmp_path):  # AC-1.4
    _write_code_repo(tmp_path)
    assert not (tmp_path / ".spark").exists()
    graph, report = build_graph(tmp_path)
    assert report.artifact_entities == 0
    assert graph.counts()["artifact"] == 0
    assert report.code_entities > 0  # code still present, no error raised


def test_double_build_is_deterministic(tmp_path):  # AC-1.2
    _write_code_repo(tmp_path)
    g1, _ = build_graph(tmp_path)
    g2, _ = build_graph(tmp_path)
    assert g1.to_dict() == g2.to_dict()

    p1 = g1.save(tmp_path / "run1" / "graph.json")
    p2 = g2.save(tmp_path / "run2" / "graph.json")
    assert p1.read_text() == p2.read_text()


def test_double_build_six_language_repo_is_deterministic(tmp_path):  # go-rust-support AC-5.1
    (tmp_path / "a.py").write_text("def f():\n    return 1\n")
    (tmp_path / "b.ts").write_text("export function g() { return 1; }\n")
    (tmp_path / "C.java").write_text("public class C { public void m() {} }\n")
    (tmp_path / "d.go").write_text("package main\n\ntype Widget struct{}\n\nfunc (w *Widget) M() {}\n")
    (tmp_path / "e.rs").write_text("pub struct Widget {}\n\nimpl Widget {\n    pub fn m(&self) {}\n}\n")
    g1, _ = build_graph(tmp_path)
    g2, _ = build_graph(tmp_path)
    assert g1.to_dict() == g2.to_dict()


def test_double_build_byte_identical_at_default_path(tmp_path):  # AC-1.2 via CLI path
    _write_code_repo(tmp_path)
    g1, _ = build_graph(tmp_path)
    first = g1.save(default_graph_path(tmp_path)).read_text()
    g2, _ = build_graph(tmp_path)
    second = g2.save(default_graph_path(tmp_path)).read_text()
    assert first == second
    # And a reload round-trips to the same canonical bytes.
    reloaded = Graph.load(default_graph_path(tmp_path))
    assert reloaded.save(tmp_path / "again" / "graph.json").read_text() == second
