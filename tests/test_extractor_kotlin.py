"""Kotlin extractor + cross-file import resolution + multi-language build (issue #13)."""

from aspark_graph.build import build_graph
from aspark_graph.extractors import code_kotlin, get_extractor, language_for
from aspark_graph.model import definition_id, file_id

SOURCE = b"""package com.example.app

import com.example.util.Helper
import com.example.util.*
import com.example.util.Fmt as F

class Widget(val id: Int) : Base() {
    fun render(): String = ""
    private fun reset() {}

    companion object {
        fun make() = Widget(1)
    }

    inner class Part {
        fun go() {}
    }
}

data class Point(val x: Int, val y: Int)

object Registry {
    fun all() = 1
}

interface Shape {
    fun area(): Int
}

enum class Color {
    RED;
    fun label() = "r"
}

fun String.shout() {}

fun <T> List<T>.second() {}

fun top() {
    fun local() {}
}
"""


def _defs(relpath="W.kt", source=SOURCE):
    r = code_kotlin.extract(relpath, source)
    return r, {(d.qualname, d.kind): d for d in r.definitions}


def test_kotlin_dispatch_for_kt_and_kts():
    assert language_for("a/B.kt") == "kotlin"
    assert language_for("build.gradle.kts") == "kotlin"
    assert get_extractor("kotlin") is not None


def test_kotlin_extractor_finds_package_and_classes():
    r, defs = _defs()
    assert r.language == "kotlin"
    assert r.package == "com.example.app"
    for name in ("Widget", "Widget.Part", "Point", "Registry", "Shape", "Color"):
        assert (name, "Class") in defs, name
    assert defs[("Widget.Part", "Class")].parent == "Widget"


def test_kotlin_extractor_finds_functions():
    _, defs = _defs()
    for name in ("Widget.render", "Widget.reset", "Widget.Part.go", "Registry.all", "Shape.area",
                 "Color.label", "top"):
        assert (name, "Function") in defs, name
    assert defs[("Widget.render", "Function")].parent == "Widget"
    assert defs[("Widget.reset", "Function")].exported is False


def test_kotlin_companion_members_nest_under_enclosing_class():
    _, defs = _defs()
    assert ("Widget.make", "Function") in defs
    assert defs[("Widget.make", "Function")].parent == "Widget"
    assert not any("Companion" in q for q, _ in defs)


def test_kotlin_extension_functions_are_top_level_by_receiver():
    _, defs = _defs()
    assert defs[("String.shout", "Function")].parent is None
    assert defs[("List.second", "Function")].parent is None


def test_kotlin_local_functions_are_not_captured():
    _, defs = _defs()
    assert not any(q.endswith("local") for q, _ in defs)


def test_kotlin_imports_raw():
    r, _ = _defs()
    mods = [i.module for i in r.imports]
    assert "com.example.util.Helper" in mods
    assert "com.example.util.*" in mods
    assert "com.example.util.Fmt" in mods  # alias dropped


def test_kotlin_kts_script_parses():
    r = code_kotlin.extract("build.gradle.kts", b"import a.b.C\n\nfun helper() {}\n")
    assert ("helper", "Function") in {(d.qualname, d.kind) for d in r.definitions}


def test_kotlin_empty_file_is_not_unparsed(tmp_path):
    (tmp_path / "Empty.kt").write_text("")
    graph, report = build_graph(tmp_path)
    assert graph.get_node(file_id("Empty.kt")).get("unparsed") is not True
    assert "Empty.kt" not in report.unparsed


def _write_two_files(tmp_path):
    util = tmp_path / "src" / "com" / "example" / "util"
    app = tmp_path / "src" / "com" / "example" / "app"
    util.mkdir(parents=True)
    app.mkdir(parents=True)
    (util / "Helper.kt").write_text(
        "package com.example.util\n\nclass Helper {\n    fun format() = \"\"\n}\n\nfun slug(s: String) = s\n"
    )
    (app / "Widget.kt").write_text(
        "package com.example.app\n\nimport com.example.util.Helper\nimport com.example.util.slug\n"
        "import com.example.util.*\nimport java.util.List\n\nclass Widget {\n    fun go() {}\n}\n"
    )
    return "src/com/example/app/Widget.kt", "src/com/example/util/Helper.kt"


def test_build_resolves_kotlin_import_and_contains(tmp_path):
    widget, helper = _write_two_files(tmp_path)
    graph, _ = build_graph(tmp_path)
    assert graph.has_node(definition_id(widget, "Widget"))
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    assert (file_id(widget), file_id(helper), "imports") in edges
    assert (file_id(widget), definition_id(widget, "Widget"), "contains") in edges
    assert (definition_id(widget, "Widget"), definition_id(widget, "Widget.go"), "contains") in edges
    imports = [e for e in graph.edges() if e["type"] == "imports" and e["source"] == file_id(widget)]
    assert len(imports) == 1  # star + java.util.List resolve to nothing


def test_kotlin_unresolvable_import_makes_no_edge(tmp_path):
    (tmp_path / "A.kt").write_text("package p\n\nimport org.other.Thing\n\nclass A\n")
    graph, _ = build_graph(tmp_path)
    assert not [e for e in graph.edges() if e["type"] == "imports"]


def test_kotlin_build_is_deterministic(tmp_path):
    _write_two_files(tmp_path)
    g1, _ = build_graph(tmp_path)
    g2, _ = build_graph(tmp_path)
    assert g1.to_dict() == g2.to_dict()
