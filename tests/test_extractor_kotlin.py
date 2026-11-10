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
    (util / "Helper.kt").write_text("package com.example.util\n\nclass Helper {\n    fun format() = \"\"\n}\n")
    (util / "Funcs.kt").write_text("package com.example.util\n\nfun topLevel() {}\n")
    (util / "Ext1.kt").write_text("package com.example.util\n\nfun String.toast() {}\n")
    (util / "Ext2.kt").write_text("package com.example.util\n\nfun Int.toast() {}\n")
    (app / "Widget.kt").write_text(
        "package com.example.app\n\nimport com.example.util.Helper\nimport com.example.util.topLevel\n"
        "import com.example.util.Helper.Nested\nimport com.example.util.toast\nimport kotlin.collections.List\nimport com.example.util.*\n\n"
        "class Widget\n"
    )
    graph, _ = build_graph(tmp_path)
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    src = file_id("src/com/example/app/Widget.kt")
    assert (src, file_id("src/com/example/util/Helper.kt"), "imports") in edges
    imports_from_src = {t for s, t, ty in edges if s == src and ty == "imports"}
    # class, function (own file) and overloaded function (fans out to both files);
    # stdlib/wildcard: no edge
    assert imports_from_src == {
        file_id(f"src/com/example/util/{n}.kt") for n in ("Helper", "Funcs", "Ext1", "Ext2")
    }


def test_one_line_bodies_are_recovered_with_original_line_numbers():  # review F1
    src = b'class X { companion object { const val TAG = "x" } }\n\nclass L { fun login() {} }\nfun f() {}\n'
    r = code_kotlin.extract("A.kt", src)
    by = {d.qualname: d for d in r.definitions}
    assert {"X", "X.Companion", "L", "L.login", "f"} <= set(by)
    assert by["X.Companion"].parent == "X" and by["L.login"].parent == "L"
    assert (by["X"].line, by["L"].line, by["f"].line) == (1, 3, 4)


def test_unparseable_file_is_partial_and_never_mis_parented():  # review F2
    r = code_kotlin.extract("A.kt", b"class A{fun g(){}}\nclass B{fun h(){}}\n")
    assert r.partial is True
    assert all(d.parent is None or d.parent in {x.qualname for x in r.definitions} for d in r.definitions)
    assert not any(d.kind == "Function" and d.parent is None for d in r.definitions)


def test_partial_flag_reaches_file_node_only_when_true(tmp_path):
    (tmp_path / "Bad.kt").write_text("class A{fun g(){}}\nclass B{fun h(){}}\n")
    (tmp_path / "Good.kt").write_text("class G {\n    fun g() {}\n}\n")
    graph, _ = build_graph(tmp_path)
    nodes = {n["id"]: n for n in graph.nodes()}
    assert nodes[file_id("Bad.kt")].get("partial") is True
    assert "partial" not in nodes[file_id("Good.kt")]


def test_comments_and_strings_do_not_confuse_the_retry():  # review F1/F12
    src = (
        b"class X { companion object { const val T = 1 } }\n"
        b"// e.g. items.map { it.id }\n"
        b"/// Usage: { fun sample()\n"
        b'val s = "{ fun fake() }"\n'
        b"class L {\n    fun login() {}\n}\n"
    )
    r = code_kotlin.extract("A.kt", src)
    names = {d.qualname for d in r.definitions}
    assert names == {"X", "X.Companion", "L", "L.login"}  # nothing invented from comments/strings
    assert r.partial is False


def test_valid_one_line_members_are_not_flagged_partial():  # review F13
    for body in (
        b"data class D(val a: Int) { fun f() = a }\n",
        b"enum class E { A, B; fun h() {} }\n",
        b"class X { fun y() = list.map { it + 1 } }\n",
    ):
        assert code_kotlin.extract("A.kt", body).partial is False, body


def test_partial_files_are_named_on_stderr_and_mcp(tmp_path, capsys):
    from aspark_graph import cli
    (tmp_path / ".git").mkdir()
    (tmp_path / "Bad.kt").write_text("class A{fun g(){}}\nclass B{fun h(){}}\n")
    (tmp_path / "Good.kt").write_text("class G {\n    fun g() {}\n}\n")
    assert cli.main(["build", str(tmp_path)]) == 0
    err = capsys.readouterr().err
    assert "Partially parsed Bad.kt" in err and "Good.kt" not in err
    from aspark_graph import server
    result = server.build_graph(str(tmp_path))
    assert result["partial_files"] == ["Bad.kt"]
