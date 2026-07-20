"""T10: Java extractor + cross-file import resolution + AC-4.2 unparsed path."""

from aspark_graph import extractors
from aspark_graph.build import build_graph
from aspark_graph.extractors import code_java
from aspark_graph.model import definition_id, file_id


def test_java_extractor_finds_package_classes_methods():
    source = b"""
package com.example.app;

import com.example.util.Helper;

public class Widget {
    public String render() {
        return new Helper().format();
    }
    private void reset() {}
}
"""
    r = code_java.extract("src/com/example/app/Widget.java", source)
    assert r.package == "com.example.app"
    quals = {(d.qualname, d.kind) for d in r.definitions}
    assert ("Widget", "Class") in quals
    assert ("Widget.render", "Function") in quals
    assert ("Widget.reset", "Function") in quals
    assert "com.example.util.Helper" in {i.module for i in r.imports}


def test_build_resolves_java_import(tmp_path):  # AC-4.1 Java
    util_dir = tmp_path / "src" / "com" / "example" / "util"
    app_dir = tmp_path / "src" / "com" / "example" / "app"
    util_dir.mkdir(parents=True)
    app_dir.mkdir(parents=True)
    (util_dir / "Helper.java").write_text("package com.example.util;\npublic class Helper { public String format() { return \"\"; } }\n")
    (app_dir / "Widget.java").write_text(
        "package com.example.app;\nimport com.example.util.Helper;\npublic class Widget { public void go() { new Helper(); } }\n"
    )
    graph, _ = build_graph(tmp_path)
    assert graph.has_node(definition_id("src/com/example/app/Widget.java", "Widget"))
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    assert (
        file_id("src/com/example/app/Widget.java"),
        file_id("src/com/example/util/Helper.java"),
        "imports",
    ) in edges


def test_all_six_languages_in_one_build(tmp_path):  # AC-4.1 / go-rust-support AC-5.1: none may be missing
    (tmp_path / "a.py").write_text("def f():\n    return 1\n")
    (tmp_path / "b.ts").write_text("export function g() { return 1; }\n")
    (tmp_path / "C.java").write_text("public class C { public void m() {} }\n")
    (tmp_path / "d.go").write_text("package main\n\nfunc D() int { return 1 }\n")
    (tmp_path / "e.rs").write_text("pub fn e() -> i32 { 1 }\n")
    graph, _ = build_graph(tmp_path)
    langs = {n.get("language") for n in graph.nodes() if n["type"] == "File"}
    assert {"python", "typescript", "java", "go", "rust"} <= langs
    assert graph.has_node(definition_id("a.py", "f"))
    assert graph.has_node(definition_id("b.ts", "g"))
    assert graph.has_node(definition_id("C.java", "C"))
    assert graph.has_node(definition_id("d.go", "D"))
    assert graph.has_node(definition_id("e.rs", "e"))
    unparsed = {n["id"] for n in graph.nodes() if n["type"] == "File" and n.get("unparsed")}
    assert unparsed == set()


def test_ac_4_2_unsupported_language_becomes_unparsed_file_node(tmp_path, monkeypatch):
    """A known source language with no registered extractor (the A9 early-cut
    path) is recorded as an unparsed File node; the build does not fail."""
    # Simulate Java's extractor being cut from the release.
    monkeypatch.setitem(extractors._REGISTRY, "java", None)
    monkeypatch.setattr(extractors, "get_extractor", lambda lang: extractors._REGISTRY.get(lang))
    (tmp_path / "a.py").write_text("def ok():\n    return 1\n")
    (tmp_path / "Cut.java").write_text("public class Cut {}\n")
    graph, report = build_graph(tmp_path)
    node = graph.get_node(file_id("Cut.java"))
    assert node is not None
    assert node.get("unparsed") is True
    assert "Cut.java" in report.unparsed
    # Build still succeeded and the supported language is fully parsed.
    assert graph.has_node(definition_id("a.py", "ok"))
