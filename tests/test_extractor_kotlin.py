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
    # stdlib / unresolvable imports add no edge: Widget.kt links to exactly the two repo files
    assert {e[1] for e in edges if e[0] == w and e[2] == "imports"} == {
        file_id("src/util/Helper.kt"),
        file_id("src/util/Extras.kt"),
    }


def test_kotlin_unresolved_import_is_silent(tmp_path):
    (tmp_path / "A.kt").write_text("package a\n\nimport org.nowhere.Thing\n\nclass A {\n}\n")
    graph, _ = build_graph(tmp_path)
    assert not [e for e in graph.edges() if e["type"] == "imports"]


def test_kotlin_double_build_deterministic(tmp_path):
    (tmp_path / "A.kt").write_bytes(SOURCE)
    g1, _ = build_graph(tmp_path)
    g2, _ = build_graph(tmp_path)
    assert g1.to_dict() == g2.to_dict()


def test_kotlin_visibility_maps_to_exported():
    r = code_kotlin.extract("V.kt", b"private fun hidden() {}\n\ninternal class Inside {\n}\n\nfun shown() {}\n")
    by = {d.qualname: d.exported for d in r.definitions}
    assert by == {"hidden": False, "Inside": False, "shown": True}


def test_kotlin_package_only_and_comment_only_files(tmp_path):
    (tmp_path / "P.kt").write_text("package only.here\n")
    (tmp_path / "C.kt").write_text("// nothing but a comment\n")
    graph, _ = build_graph(tmp_path)
    for name in ("P.kt", "C.kt"):
        node = graph.get_node(file_id(name))
        assert node is not None and node["language"] == "kotlin"
        assert not node.get("unparsed")
        assert not [n for n in graph.nodes() if n["id"].startswith(f"def:{name}::")]


def test_kotlin_unregistered_extractor_is_unparsed(tmp_path, monkeypatch):
    from aspark_graph import extractors

    monkeypatch.setitem(extractors._REGISTRY, "kotlin", None)
    monkeypatch.setattr(extractors, "get_extractor", lambda lang: extractors._REGISTRY.get(lang))
    (tmp_path / "K.kt").write_text("class K {\n}\n")
    (tmp_path / "r.rb").write_text("class R; end\n")
    graph, report = build_graph(tmp_path)
    assert graph.get_node(file_id("K.kt")).get("unparsed") is True
    assert "K.kt" in report.unparsed
    # AC-3.4: an extension outside the language table is skipped, as before.
    assert graph.get_node(file_id("r.rb")) is None


def test_kotlin_malformed_source_builds_without_error(tmp_path):
    (tmp_path / "M.kt").write_text("class {{{ fun ( ) = \n")
    graph, _ = build_graph(tmp_path)
    assert graph.get_node(file_id("M.kt")) is not None


def test_build_resolves_extension_function_import_by_bare_name(tmp_path):  # review F1
    (tmp_path / "Ext.kt").write_text("package lib\n\nfun String.buffer() {}\n")
    (tmp_path / "Use.kt").write_text("package app\n\nimport lib.buffer\n\nclass Use {\n}\n")
    graph, _ = build_graph(tmp_path)
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    assert (file_id("Use.kt"), file_id("Ext.kt"), "imports") in edges


def test_kotlin_qualified_receiver_uses_last_segment():  # review F3
    r = code_kotlin.extract("Q.kt", b"fun kotlin.String.q() {}\n")
    assert [d.qualname for d in r.definitions] == ["String.q"]
