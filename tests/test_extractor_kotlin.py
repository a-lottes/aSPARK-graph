"""Issue #29: Kotlin extractor + cross-file import resolution + unparsed-path removal."""

from aspark_graph.build import build_graph
from aspark_graph.extractors import code_kotlin, language_for
from aspark_graph.model import definition_id, file_id

SOURCE = b"""package com.example.app

import com.example.util.Helper
import com.example.util.format
import com.example.util.*
import com.example.other.Thing as Renamed

data class Widget(val name: String) {
    fun render(): String = name

    companion object {
        fun create(): Widget = Widget("x")
    }

    class Inner {
        fun go() {}
    }

    private fun reset() {
    }
}

object Registry {
    fun all(): List<Widget> = emptyList()
}

interface Shape {
    fun area(): Double
}

enum class Color {
    RED;

    fun hex(): String = "#f00"
}

fun String.shout(): String = this.uppercase()

private fun helper() {
}
"""


def _extract():
    return code_kotlin.extract("src/Widget.kt", SOURCE)


def test_extensions_map_to_kotlin():
    assert language_for("a/B.kt") == "kotlin"
    assert language_for("build.gradle.kts") == "kotlin"


def test_kotlin_extractor_finds_package_and_class_kinds():
    r = _extract()
    assert r.language == "kotlin"
    assert r.package == "com.example.app"
    classes = {d.qualname for d in r.definitions if d.kind == "Class"}
    assert {"Widget", "Widget.Companion", "Widget.Inner", "Registry", "Shape", "Color"} <= classes


def test_kotlin_extractor_finds_functions_and_nesting():
    r = _extract()
    by_name = {d.qualname: d for d in r.definitions}
    assert by_name["Widget.render"].kind == "Function" and by_name["Widget.render"].parent == "Widget"
    assert by_name["Widget.Companion.create"].parent == "Widget.Companion"
    assert by_name["Widget.Inner.go"].parent == "Widget.Inner"
    assert by_name["Registry.all"].kind == "Function"
    assert by_name["Shape.area"].kind == "Function"
    assert by_name["Color.hex"].parent == "Color"
    assert by_name["helper"].parent is None


def test_kotlin_extension_function_is_qualified_by_receiver():
    by_name = {d.qualname: d for d in _extract().definitions}
    assert by_name["String.shout"].kind == "Function"
    assert by_name["String.shout"].parent is None


def test_kotlin_exported_follows_private():
    by_name = {d.qualname: d for d in _extract().definitions}
    assert by_name["Widget.render"].exported is True
    assert by_name["Widget.reset"].exported is False
    assert by_name["helper"].exported is False


def test_kotlin_imports_alias_stripped_wildcard_skipped():
    mods = {i.module for i in _extract().imports}
    assert mods == {"com.example.util.Helper", "com.example.util.format", "com.example.other.Thing"}


def test_kotlin_script_file_is_parsed():
    r = code_kotlin.extract("build.gradle.kts", b"fun configure() {\n}\n")
    assert ("configure", "Function") in {(d.qualname, d.kind) for d in r.definitions}


def test_kotlin_empty_file_is_not_unparsed(tmp_path):
    (tmp_path / "Empty.kt").write_text("")
    graph, _ = build_graph(tmp_path)
    node = graph.get_node(file_id("Empty.kt"))
    assert node["language"] == "kotlin"


def test_build_creates_kotlin_nodes_and_contains_edges(tmp_path):
    (tmp_path / "Widget.kt").write_text(SOURCE.decode())
    graph, _ = build_graph(tmp_path)
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    assert (file_id("Widget.kt"), definition_id("Widget.kt", "Widget"), "contains") in edges
    assert (definition_id("Widget.kt", "Widget"), definition_id("Widget.kt", "Widget.render"), "contains") in edges
    assert (
        definition_id("Widget.kt", "Widget.Companion"),
        definition_id("Widget.kt", "Widget.Companion.create"),
        "contains",
    ) in edges
    assert (file_id("Widget.kt"), definition_id("Widget.kt", "String.shout"), "contains") in edges


def test_build_resolves_kotlin_import_of_class_and_function(tmp_path):
    util = tmp_path / "src" / "util"
    app = tmp_path / "src" / "app"
    util.mkdir(parents=True)
    app.mkdir(parents=True)
    (util / "Helper.kt").write_text("package com.example.util\n\nclass Helper {\n    fun f() {}\n}\n")
    (util / "Fmt.kt").write_text("package com.example.util\n\nfun format(s: String): String {\n    return s\n}\n")
    (app / "Main.kt").write_text(
        "package com.example.app\n\nimport com.example.util.Helper\nimport com.example.util.format\n\nfun main() {\n}\n"
    )
    graph, _ = build_graph(tmp_path)
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    src = file_id("src/app/Main.kt")
    assert (src, file_id("src/util/Helper.kt"), "imports") in edges
    assert (src, file_id("src/util/Fmt.kt"), "imports") in edges


def test_build_resolves_nested_class_import_to_outer_file(tmp_path):
    (tmp_path / "Outer.kt").write_text("package a\n\nclass Outer {\n    class Inner {\n    }\n}\n")
    (tmp_path / "Use.kt").write_text("package b\n\nimport a.Outer.Inner\n\nclass U {\n}\n")
    graph, _ = build_graph(tmp_path)
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    assert (file_id("Use.kt"), file_id("Outer.kt"), "imports") in edges


def test_build_kotlin_external_and_wildcard_imports_yield_no_edge(tmp_path):
    (tmp_path / "Helper.kt").write_text("package com.example.util\n\nclass Helper {\n}\n")
    (tmp_path / "Use.kt").write_text(
        "package x\n\nimport kotlinx.coroutines.launch\nimport com.example.util.*\n\nclass U {\n}\n"
    )
    graph, _ = build_graph(tmp_path)
    assert not [e for e in graph.edges() if e["type"] == "imports"]


def test_build_kotlin_ambiguous_import_yields_no_edge(tmp_path):
    (tmp_path / "A1.kt").write_text("package p\n\nclass Dup {\n}\n")
    (tmp_path / "A2.kt").write_text("package p\n\nclass Dup {\n}\n")
    (tmp_path / "Use.kt").write_text("package q\n\nimport p.Dup\n\nclass U {\n}\n")
    graph, _ = build_graph(tmp_path)
    assert not [e for e in graph.edges() if e["type"] == "imports"]


def test_double_build_kotlin_is_deterministic(tmp_path):
    (tmp_path / "Widget.kt").write_text(SOURCE.decode())
    g1, _ = build_graph(tmp_path)
    g2, _ = build_graph(tmp_path)
    assert g1.save(tmp_path / "r1" / "graph.json").read_text() == g2.save(tmp_path / "r2" / "graph.json").read_text()
