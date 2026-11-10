"""Kotlin extractor + best-effort in-repo import resolution."""

from aspark_graph.build import build_graph
from aspark_graph.extractors import code_kotlin, language_for
from aspark_graph.model import definition_id, file_id

SOURCE = b"""package com.example.app

import com.example.util.Helper
import com.example.util.Helper as H
import com.example.other.*

@Deprecated("x")
class Widget(val n: Int) : Base() {
    companion object Factory {
        fun create(): Widget = Widget(1)
    }
    fun render(): String = ""
    private fun reset() {}
    class Inner {
        fun deep() {}
    }
}

data class Point(val x: Int, val y: Int)

object Registry {
    fun register() {}
}

interface Shape {
    fun area(): Double
}

enum class Color {
    RED, GREEN;
    fun hex(): String = ""
}

fun String.shout(): String = uppercase()

fun <T> List<T>.second(): T = this[1]

fun top() {
    fun local() {}
}
"""


def _defs(source=SOURCE, path="src/App.kt"):
    return code_kotlin.extract(path, source)


def test_extensions_map_to_kotlin():
    assert language_for("a/B.kt") == "kotlin"
    assert language_for("build.gradle.kts") == "kotlin"


def test_package_and_class_kinds():
    r = _defs()
    assert r.language == "kotlin"
    assert r.package == "com.example.app"
    quals = {(d.qualname, d.kind) for d in r.definitions}
    for name in ("Widget", "Widget.Inner", "Point", "Registry", "Shape", "Color"):
        assert (name, "Class") in quals


def test_functions_methods_companion_and_extensions():
    r = _defs()
    by = {d.qualname: d for d in r.definitions}
    assert by["Widget.render"].kind == "Function" and by["Widget.render"].parent == "Widget"
    assert by["Widget.create"].parent == "Widget"  # companion member nests under the class
    assert "Widget.Factory" not in by
    assert by["Widget.Inner.deep"].parent == "Widget.Inner"
    assert by["Registry.register"].kind == "Function"
    assert by["Shape.area"].kind == "Function"
    assert by["Color.hex"].kind == "Function"
    assert by["String.shout"].parent is None
    assert by["List.second"].parent is None
    assert by["top"].parent is None
    assert "local" not in by and "top.local" not in by  # local functions skipped
    assert by["Widget.reset"].exported is False
    assert by["Widget.render"].exported is True


def test_imports_collected():
    mods = [i.module for i in _defs().imports]
    assert "com.example.util.Helper" in mods
    assert mods.count("com.example.util.Helper") == 2  # alias form too
    assert "com.example.other.*" in mods


def test_kts_script_extracts():
    r = code_kotlin.extract("build.gradle.kts", b"fun helper() {}\n")
    assert [(d.qualname, d.kind) for d in r.definitions] == [("helper", "Function")]


def test_build_resolves_kotlin_import(tmp_path):
    util = tmp_path / "src" / "com" / "example" / "util"
    app = tmp_path / "src" / "com" / "example" / "app"
    util.mkdir(parents=True)
    app.mkdir(parents=True)
    (util / "Helper.kt").write_text("package com.example.util\n\nclass Helper {\n    fun format() = \"\"\n}\n\nfun topHelper() {}\n")
    (app / "Widget.kt").write_text(
        "package com.example.app\n\nimport com.example.util.Helper\nimport com.example.util.topHelper\nimport kotlin.collections.List\n\nclass Widget {\n    fun go() {}\n}\n"
    )
    graph, _ = build_graph(tmp_path)
    w, h = "src/com/example/app/Widget.kt", "src/com/example/util/Helper.kt"
    assert graph.has_node(definition_id(w, "Widget.go"))
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    assert (file_id(w), file_id(h), "imports") in edges
    assert (file_id(w), definition_id(w, "Widget"), "contains") in edges
    # external import produces no edge
    assert len([e for e in edges if e[0] == file_id(w) and e[2] == "imports"]) == 1
