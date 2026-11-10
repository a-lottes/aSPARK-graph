"""Kotlin extractor + cross-file import resolution + multi-language build."""

from aspark_graph.build import build_graph
from aspark_graph.extractors import code_kotlin, language_for
from aspark_graph.model import definition_id, file_id

SOURCE = b"""package com.example.app

import com.example.util.Helper
import com.example.shared.*
import com.example.other.Foo as Bar

data class Point(val x: Int)

interface Shape {
    fun area(): Int
}

enum class Color {
    RED;
    fun label() = "r"
}

object Registry {
    fun lookup() {}
}

class Widget {
    fun render(): String = ""

    class Inner {
        fun go() {}
    }

    companion object {
        fun make() = Widget()
    }
}

fun String.shout() {}

fun top() {
    fun local() {}
}
"""


def test_kotlin_extensions():
    assert language_for("a/B.kt") == "kotlin"
    assert language_for("build.gradle.kts") == "kotlin"


def test_kotlin_extractor_finds_classes_and_functions():
    r = code_kotlin.extract("src/Widget.kt", SOURCE)
    assert r.language == "kotlin"
    assert r.package == "com.example.app"
    quals = {(d.qualname, d.kind): d.parent for d in r.definitions}
    for cls in ("Point", "Shape", "Color", "Registry", "Widget"):
        assert quals[(cls, "Class")] is None
    assert quals[("Widget.Inner", "Class")] == "Widget"
    assert quals[("Shape.area", "Function")] == "Shape"
    assert quals[("Color.label", "Function")] == "Color"
    assert quals[("Registry.lookup", "Function")] == "Registry"
    assert quals[("Widget.render", "Function")] == "Widget"
    assert quals[("Widget.Inner.go", "Function")] == "Widget.Inner"
    assert quals[("top", "Function")] is None
    assert ("local", "Function") not in quals


def test_kotlin_companion_member_nests_under_owner():
    r = code_kotlin.extract("W.kt", SOURCE)
    d = next(d for d in r.definitions if d.qualname == "Widget.make")
    assert d.parent == "Widget" and d.kind == "Function"


def test_kotlin_extension_function_captured_without_parent():
    r = code_kotlin.extract("E.kt", SOURCE)
    d = next(d for d in r.definitions if d.qualname == "String.shout")
    assert d.kind == "Function" and d.parent is None


def test_kotlin_imports_recorded():
    r = code_kotlin.extract("W.kt", SOURCE)
    assert {i.module for i in r.imports} == {
        "com.example.util.Helper",
        "com.example.shared.*",
        "com.example.other.Foo",
    }


def test_kts_script_parses():
    r = code_kotlin.extract("build.gradle.kts", b"fun helper() {}\n")
    assert [d.qualname for d in r.definitions] == ["helper"]


def test_build_resolves_kotlin_imports(tmp_path):
    util = tmp_path / "src" / "util"
    app = tmp_path / "src" / "app"
    util.mkdir(parents=True)
    app.mkdir(parents=True)
    (util / "Helper.kt").write_text("package com.example.util\n\nclass Helper {\n    fun f() {}\n}\n")
    (util / "Extras.kt").write_text("package com.example.util\n\nfun extra() {}\n")
    (app / "Widget.kt").write_text(
        "package com.example.app\n\n"
        "import com.example.util.Helper\n"
        "import com.example.util.extra\n"
        "import kotlin.collections.List\n\n"
        "class Widget {\n    fun go() {}\n}\n"
    )
    (app / "Star.kt").write_text("package com.example.app\n\nimport com.example.util.*\n\nclass Star {\n}\n")
    graph, _ = build_graph(tmp_path)
    assert graph.has_node(definition_id("src/app/Widget.kt", "Widget"))
    assert graph.has_node(definition_id("src/app/Widget.kt", "Widget.go"))
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    w = file_id("src/app/Widget.kt")
    assert (w, file_id("src/util/Helper.kt"), "imports") in edges
    assert (w, file_id("src/util/Extras.kt"), "imports") in edges
    s = file_id("src/app/Star.kt")
    assert (s, file_id("src/util/Helper.kt"), "imports") in edges
    assert (s, file_id("src/util/Extras.kt"), "imports") in edges
    # stdlib / unresolvable imports add no edge
    assert not [e for e in edges if e[0] == w and e[1].endswith("List")]


def test_kotlin_unresolved_import_is_silent(tmp_path):
    (tmp_path / "A.kt").write_text("package a\n\nimport org.nowhere.Thing\n\nclass A {\n}\n")
    graph, _ = build_graph(tmp_path)
    assert not [e for e in graph.edges() if e["type"] == "imports"]


def test_kotlin_double_build_deterministic(tmp_path):
    (tmp_path / "A.kt").write_bytes(SOURCE)
    g1, _ = build_graph(tmp_path)
    g2, _ = build_graph(tmp_path)
    assert g1.to_dict() == g2.to_dict()
