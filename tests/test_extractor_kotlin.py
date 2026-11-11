"""Kotlin extractor + cross-file import resolution + build integration (issue #36)."""

from aspark_graph.build import build_graph
from aspark_graph.extractors import code_kotlin, get_extractor
from aspark_graph.extractors.base import language_for
from aspark_graph.model import definition_id, file_id

SOURCE = b"""package com.example.app

import com.example.util.Helper
import com.example.tools.*
import com.example.x.Y as Z

data class Point(val x: Int) {
    fun norm(): Int = x

    companion object {
        fun origin(): Point = Point(0)
    }
}

object Registry {
    fun lookup() {}
}

interface Shape {
    fun area(): Int
}

enum class Color {
    RED;

    fun hex(): String = "x"
}

fun String.shout(): String = this

private fun hidden() {}

fun top() {}
"""


def _defs(r):
    return {(d.qualname, d.kind): d for d in r.definitions}


def test_kotlin_extension_registered():
    assert language_for("a/B.kt") == "kotlin"
    assert language_for("build.gradle.kts") == "kotlin"
    assert get_extractor("kotlin") is not None


def test_kotlin_extractor_finds_classes_and_functions():
    r = code_kotlin.extract("src/App.kt", SOURCE)
    assert r.language == "kotlin"
    assert r.package == "com.example.app"
    defs = _defs(r)
    for q in ("Point", "Registry", "Shape", "Color"):
        assert (q, "Class") in defs
    assert ("Point.norm", "Function") in defs
    assert ("Registry.lookup", "Function") in defs
    assert ("Shape.area", "Function") in defs
    assert ("Color.hex", "Function") in defs
    assert ("top", "Function") in defs


def test_kotlin_companion_members_nest_under_enclosing_class():
    d = _defs(code_kotlin.extract("App.kt", SOURCE))[("Point.origin", "Function")]
    assert d.parent == "Point"


def test_kotlin_extension_function_is_top_level_receiver_qualified():
    d = _defs(code_kotlin.extract("App.kt", SOURCE))[("String.shout", "Function")]
    assert d.parent is None


def test_kotlin_private_is_not_exported():
    defs = _defs(code_kotlin.extract("App.kt", SOURCE))
    assert defs[("hidden", "Function")].exported is False
    assert defs[("top", "Function")].exported is True


def test_kotlin_imports_including_wildcard_and_alias():
    mods = [i.module for i in code_kotlin.extract("App.kt", SOURCE).imports]
    assert "com.example.util.Helper" in mods
    assert "com.example.tools.*" in mods
    assert "com.example.x.Y" in mods


def test_kotlin_single_line_class_body_still_found():
    r = code_kotlin.extract("A.kt", b"class A { fun m() {} }\n")
    assert ("A", "Class") in _defs(r)
    assert ("A.m", "Function") in _defs(r)


def test_kotlin_script_file_kts():
    r = code_kotlin.extract("build.gradle.kts", b"fun helper() {}\n")
    assert ("helper", "Function") in _defs(r)


def test_build_resolves_kotlin_imports(tmp_path):
    util = tmp_path / "src" / "util"
    tools = tmp_path / "src" / "tools"
    app = tmp_path / "src" / "app"
    for d in (util, tools, app):
        d.mkdir(parents=True)
    (util / "Helper.kt").write_text("package com.example.util\n\nclass Helper {\n    fun f() {}\n}\n")
    (tools / "T.kt").write_text("package com.example.tools\n\nfun tool() {}\n")
    (app / "Main.kt").write_text(
        "package com.example.app\n\nimport com.example.util.Helper\nimport com.example.tools.*\n"
        "import kotlin.collections.List\n\nclass Main {\n    fun run() {}\n}\n"
    )
    graph, _ = build_graph(tmp_path)
    assert graph.has_node(definition_id("src/app/Main.kt", "Main"))
    assert graph.has_node(definition_id("src/app/Main.kt", "Main.run"))
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    main = file_id("src/app/Main.kt")
    assert (main, file_id("src/util/Helper.kt"), "imports") in edges
    assert (main, file_id("src/tools/T.kt"), "imports") in edges
    # stdlib import resolves to nothing: only the two in-repo edges
    assert len([e for e in edges if e[0] == main and e[2] == "imports"]) == 2
