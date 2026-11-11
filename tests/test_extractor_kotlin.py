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
    # AC-1.2: a plain `class` (the fifth kind) also gets its File -> Class contains edge
    assert (main, definition_id("src/app/Main.kt", "Main"), "contains") in edges
    # stdlib import resolves to nothing: only the two in-repo edges
    assert len([e for e in edges if e[0] == main and e[2] == "imports"]) == 2


def _kt_import_edges(tmp_path, importer: str):
    graph, _ = build_graph(tmp_path)
    return {(e["source"], e["target"]) for e in graph.edges() if e["type"] == "imports" and e["source"] == file_id(importer)}


def test_kotlin_ambiguous_fqn_gives_no_edge(tmp_path):  # plan T6
    for variant in ("debug", "release"):
        d = tmp_path / "src" / variant
        d.mkdir(parents=True)
        (d / "Config.kt").write_text("package com.x\n\nclass Config\n")
    (tmp_path / "Main.kt").write_text("package com.app\n\nimport com.x.Config\n\nclass Main\n")
    assert _kt_import_edges(tmp_path, "Main.kt") == set()


def test_kotlin_same_file_overloads_still_resolve(tmp_path):  # plan T6
    (tmp_path / "U.kt").write_text("package com.x\n\nfun f() {}\n\nfun f(a: Int) {}\n")
    (tmp_path / "Main.kt").write_text("package com.app\n\nimport com.x.f\n\nclass Main\n")
    assert _kt_import_edges(tmp_path, "Main.kt") == {(file_id("Main.kt"), file_id("U.kt"))}


def test_kotlin_import_of_top_level_function(tmp_path):  # plan T7c
    (tmp_path / "T.kt").write_text("package com.example.tools\n\nfun tool() {}\n")
    (tmp_path / "Main.kt").write_text("package com.app\n\nimport com.example.tools.tool\n\nclass Main\n")
    assert _kt_import_edges(tmp_path, "Main.kt") == {(file_id("Main.kt"), file_id("T.kt"))}


def test_build_kotlin_script_and_contains_edges(tmp_path):  # plan T7a/b
    (tmp_path / "build.gradle.kts").write_text("fun helper() {}\n")
    (tmp_path / "App.kt").write_bytes(SOURCE)
    graph, _ = build_graph(tmp_path)
    files = {n["id"]: n for n in graph.nodes() if n["type"] == "File"}
    assert files[file_id("build.gradle.kts")]["language"] == "kotlin"
    assert not files[file_id("build.gradle.kts")].get("unparsed")
    edges = {(e["source"], e["target"]) for e in graph.edges() if e["type"] == "contains"}
    for q in ("Point", "Registry", "Shape", "Color", "top", "String.shout"):
        assert (file_id("App.kt"), definition_id("App.kt", q)) in edges
    assert (definition_id("App.kt", "Point"), definition_id("App.kt", "Point.norm")) in edges
    assert (definition_id("App.kt", "Point"), definition_id("App.kt", "Point.origin")) in edges
    assert (file_id("build.gradle.kts"), definition_id("build.gradle.kts", "helper")) in edges


def test_kotlin_annotated_constructor_class_members_absent_not_misplaced():  # review F1/F2
    # The grammar ends this class early and reads its body as an expression.
    # Honest absence: the class is found, no member is emitted with a wrong parent.
    src = (
        b"package a\n\n@Foo\nclass Ad\n  @RequiresApi(37)\n  internal constructor() : Base {\n"
        b"  override fun matches(s: Int): Boolean = true\n  fun other() {}\n}\n"
    )
    d = _defs(code_kotlin.extract("Ad.kt", src))
    assert ("Ad", "Class") in d
    assert not [q for q, k in d if k == "Function" and "." not in q]  # nothing top-level


def test_kotlin_member_after_valid_class_not_attributed_to_it():  # review F2
    src = (
        b"data class P(val x: Int)\n\n@Ann(X::class)\n@B\nclass A {\n  fun m() {}\n  class N { fun n() {} }\n}\n"
    )
    d = _defs(code_kotlin.extract("P.kt", src))
    assert not [q for q, _ in d if q.startswith("P.")]


def test_kotlin_error_recovery_flattened_class_nests_members():  # plan T11
    # Synthetic stand-in for an ERROR node holding `class X {` + members.
    r = code_kotlin.extract("A.kt", b"class A { fun m() {}\n fun n() {} }\n")
    d = _defs(r)
    assert d[("A.m", "Function")].parent == "A"
    assert d[("A.n", "Function")].parent == "A"
