"""Kotlin extractor: classes/objects, functions, extensions, companions, imports."""

from aspark_graph import extractors
from aspark_graph.build import build_graph
from aspark_graph.extractors import code_kotlin
from aspark_graph.model import definition_id, file_id

SOURCE = b"""package com.example.app

import com.example.util.Helper
import com.example.util.Tools.Inner
import com.example.wild.*

class Widget {
    companion object {
        fun create(): Widget = Widget()
    }

    fun render(): String = ""
    private fun reset() {}
    class Nested
}

data class Point(val x: Int, val y: Int)

object Registry {
    fun lookup() {}
}

interface Shape {
    fun area(): Double
}

enum class Color {
    RED;
    fun hex(): String = ""
}

fun String.shout(): String = this

fun top() {}
"""


def _quals(r):
    return {(d.qualname, d.kind, d.parent) for d in r.definitions}


def test_kotlin_extractor_finds_package_classes_functions():
    r = code_kotlin.extract("src/Widget.kt", SOURCE)
    assert r.language == "kotlin"
    assert r.package == "com.example.app"
    q = _quals(r)
    for name in ("Widget", "Point", "Registry", "Shape", "Color"):
        assert (name, "Class", None) in q
    assert ("Widget.render", "Function", "Widget") in q
    assert ("Widget.Nested", "Class", "Widget") in q
    assert ("Registry.lookup", "Function", "Registry") in q
    assert ("Shape.area", "Function", "Shape") in q
    assert ("Color.hex", "Function", "Color") in q
    assert ("top", "Function", None) in q


def test_kotlin_companion_members_nest_under_companion():
    q = _quals(code_kotlin.extract("W.kt", SOURCE))
    assert ("Widget.Companion", "Class", "Widget") in q
    assert ("Widget.Companion.create", "Function", "Widget.Companion") in q


def test_kotlin_extension_function_is_top_level_named_by_receiver():
    q = _quals(code_kotlin.extract("W.kt", SOURCE))
    assert ("String.shout", "Function", None) in q


def test_kotlin_private_is_not_exported():
    r = code_kotlin.extract("W.kt", SOURCE)
    by = {d.qualname: d for d in r.definitions}
    assert by["Widget.reset"].exported is False
    assert by["Widget.render"].exported is True


def test_kotlin_imports_captured_with_wildcard():
    r = code_kotlin.extract("W.kt", SOURCE)
    mods = {i.module for i in r.imports}
    assert {"com.example.util.Helper", "com.example.util.Tools.Inner", "com.example.wild.*"} <= mods


def test_kotlin_script_file_extracted(tmp_path):
    (tmp_path / "build.gradle.kts").write_text("fun helper() {}\n")
    graph, _ = build_graph(tmp_path)
    assert graph.has_node(definition_id("build.gradle.kts", "helper"))


def test_build_resolves_kotlin_imports(tmp_path):
    (tmp_path / "util").mkdir()
    (tmp_path / "app").mkdir()
    (tmp_path / "util" / "Helper.kt").write_text("package com.example.util\n\nclass Helper {\n    class Inner\n}\n")
    (tmp_path / "util" / "Fns.kt").write_text("package com.example.util\n\nfun helperFn() {}\n")
    (tmp_path / "app" / "Main.kt").write_text(
        "package com.example.app\n\nimport com.example.util.Helper.Inner\n"
        "import com.example.util.helperFn\nimport com.example.util.*\nimport kotlin.collections.List\n\nfun main() {}\n"
    )
    graph, _ = build_graph(tmp_path)
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    src = file_id("app/Main.kt")
    assert (src, file_id("util/Helper.kt"), "imports") in edges
    assert (src, file_id("util/Fns.kt"), "imports") in edges
    assert len([e for e in edges if e[0] == src and e[2] == "imports"]) == 2  # stdlib/wildcard: none


def test_build_contains_edges_for_kotlin(tmp_path):
    (tmp_path / "W.kt").write_text("class W {\n    fun m() {}\n}\n")
    graph, _ = build_graph(tmp_path)
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    assert (file_id("W.kt"), definition_id("W.kt", "W"), "contains") in edges
    assert (definition_id("W.kt", "W"), definition_id("W.kt", "W.m"), "contains") in edges


def test_kotlin_unparsed_when_extractor_cut(tmp_path, monkeypatch):
    monkeypatch.setitem(extractors._REGISTRY, "kotlin", None)
    monkeypatch.setattr(extractors, "get_extractor", lambda lang: extractors._REGISTRY.get(lang))
    (tmp_path / "K.kt").write_text("class K\n")
    graph, _ = build_graph(tmp_path)
    node = graph.get_node(file_id("K.kt"))
    assert node.get("unparsed") is True
