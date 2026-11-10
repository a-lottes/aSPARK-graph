"""Kotlin extractor + cross-file import resolution + multi-language build."""

from aspark_graph import extractors
from aspark_graph.build import build_graph
from aspark_graph.extractors import code_kotlin
from aspark_graph.model import definition_id, file_id

SOURCE = b"""package com.example.app

import com.example.util.Helper
import com.example.util.*
import com.example.util.Fmt as F

@Deprecated("x")
data class Widget(val id: Int) {
    companion object {
        fun create() = Widget(1)
    }

    fun render(): String = ""
}

object Registry {
    fun all() {}
}

interface Shape {
    fun area()
}

enum class Color {
    RED, GREEN;

    fun hex() {}
}

fun String.shout(): String = this

fun main() {}
"""


def test_kotlin_extractor_finds_package_types_functions_imports():
    r = code_kotlin.extract("src/Widget.kt", SOURCE)
    assert r.language == "kotlin"
    assert r.package == "com.example.app"
    quals = {(d.qualname, d.kind) for d in r.definitions}
    for q in ("Widget", "Registry", "Shape", "Color"):
        assert (q, "Class") in quals
    assert ("Widget.render", "Function") in quals
    assert ("Widget.Companion", "Class") in quals
    assert ("Widget.Companion.create", "Function") in quals
    assert ("Registry.all", "Function") in quals
    assert ("Shape.area", "Function") in quals
    assert ("Color.hex", "Function") in quals
    assert ("shout", "Function") in quals  # extension function named by its name
    assert ("main", "Function") in quals
    mods = {i.module for i in r.imports}
    assert {"com.example.util.Helper", "com.example.util.*", "com.example.util.Fmt"} <= mods


def test_kotlin_nested_class_and_parent_links():
    r = code_kotlin.extract("A.kt", b"class Outer {\n    inner class In {\n        fun z() {}\n    }\n}\n")
    by = {d.qualname: d for d in r.definitions}
    assert by["Outer"].parent is None
    assert by["Outer.In"].parent == "Outer"
    assert by["Outer.In.z"].parent == "Outer.In"


def test_kts_and_kt_are_dispatched():
    assert extractors.language_for("build.gradle.kts") == "kotlin"
    assert extractors.language_for("A.kt") == "kotlin"
    assert extractors.get_extractor("kotlin") is not None


def test_build_kotlin_nodes_and_contains(tmp_path):
    (tmp_path / "Widget.kt").write_text(SOURCE.decode())
    (tmp_path / "script.kts").write_text("fun helper() {}\n")
    graph, _ = build_graph(tmp_path)
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    assert (file_id("Widget.kt"), definition_id("Widget.kt", "Widget"), "contains") in edges
    assert (definition_id("Widget.kt", "Widget"), definition_id("Widget.kt", "Widget.render"), "contains") in edges
    assert (file_id("script.kts"), definition_id("script.kts", "helper"), "contains") in edges


def test_build_resolves_kotlin_import(tmp_path):
    util = tmp_path / "src" / "com" / "example" / "util"
    app = tmp_path / "src" / "com" / "example" / "app"
    util.mkdir(parents=True)
    app.mkdir(parents=True)
    (util / "Helper.kt").write_text("package com.example.util\n\nclass Helper {\n    fun format() = \"\"\n}\n\nfun topLevel() {}\n")
    (app / "Widget.kt").write_text(
        "package com.example.app\n\nimport com.example.util.Helper\nimport com.example.util.topLevel\n"
        "import com.example.util.Helper.Nested\nimport kotlin.collections.List\nimport com.example.util.*\n\n"
        "class Widget\n"
    )
    graph, _ = build_graph(tmp_path)
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    src = file_id("src/com/example/app/Widget.kt")
    assert (src, file_id("src/com/example/util/Helper.kt"), "imports") in edges
    imports_from_src = {t for s, t, ty in edges if s == src and ty == "imports"}
    assert imports_from_src == {file_id("src/com/example/util/Helper.kt")}  # stdlib/wildcard: no edge


def test_all_six_languages_in_one_build(tmp_path):
    (tmp_path / "a.py").write_text("def f():\n    return 1\n")
    (tmp_path / "b.ts").write_text("export function g() { return 1; }\n")
    (tmp_path / "C.java").write_text("public class C { public void m() {} }\n")
    (tmp_path / "d.go").write_text("package main\n\nfunc D() int { return 1 }\n")
    (tmp_path / "e.rs").write_text("pub fn e() -> i32 { 1 }\n")
    (tmp_path / "K.kt").write_text("class K {\n    fun k() {}\n}\n")
    graph, _ = build_graph(tmp_path)
    langs = {n.get("language") for n in graph.nodes() if n["type"] == "File"}
    assert {"python", "typescript", "java", "go", "rust", "kotlin"} <= langs
    assert graph.has_node(definition_id("K.kt", "K"))
    assert graph.has_node(definition_id("K.kt", "K.k"))
