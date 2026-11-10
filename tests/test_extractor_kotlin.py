"""Kotlin extractor + cross-file import resolution (issue #23)."""

from aspark_graph.build import build_graph
from aspark_graph.extractors import code_kotlin
from aspark_graph.model import definition_id, file_id

SOURCE = b"""
package com.example.app

import com.example.util.Helper
import com.example.wild.*
import com.example.util.Foo as Bar

class Widget {
    fun render(): String = ""
    companion object {
        fun make() = Widget()
    }
    object Inner {
        fun q() {}
    }
}

data class Point(val x: Int)
object Registry {
    fun all() {}
}

interface Shape {
    fun area(): Int
}

enum class Color {
    RED;
    fun hex() = ""
}

fun String.shout() {}
fun top() {}
"""


def test_kotlin_extractor_finds_package_types_functions():
    r = code_kotlin.extract("src/Widget.kt", SOURCE)
    assert r.language == "kotlin"
    assert r.package == "com.example.app"
    quals = {(d.qualname, d.kind, d.parent) for d in r.definitions}
    for cls in ("Widget", "Point", "Registry", "Shape", "Color", "Widget.Inner"):
        assert any(q[0] == cls and q[1] == "Class" for q in quals), cls
    assert ("Widget.render", "Function", "Widget") in quals
    assert ("Widget.make", "Function", "Widget") in quals  # companion member
    assert ("Widget.Inner.q", "Function", "Widget.Inner") in quals
    assert ("Registry.all", "Function", "Registry") in quals
    assert ("Color.hex", "Function", "Color") in quals
    assert ("shout", "Function", None) in quals  # extension function
    assert ("top", "Function", None) in quals


def test_kotlin_imports_skip_wildcards_and_keep_alias_target():
    r = code_kotlin.extract("a.kt", SOURCE)
    mods = {i.module for i in r.imports}
    assert mods == {"com.example.util.Helper", "com.example.util.Foo"}


def test_kts_is_parsed(tmp_path):
    (tmp_path / "build.gradle.kts").write_text("fun helper() {}\n")
    graph, _ = build_graph(tmp_path)
    assert graph.has_node(definition_id("build.gradle.kts", "helper"))


def test_build_resolves_kotlin_import(tmp_path):
    (tmp_path / "util").mkdir()
    (tmp_path / "app").mkdir()
    (tmp_path / "util" / "Helper.kt").write_text(
        "package com.example.util\nclass Helper { fun format() = \"\" }\nfun slug() {}\n"
    )
    (tmp_path / "app" / "Widget.kt").write_text(
        "package com.example.app\nimport com.example.util.Helper\nimport com.example.util.slug\n"
        "import com.example.nowhere.Missing\nimport com.example.util.*\nclass Widget\n"
    )
    graph, _ = build_graph(tmp_path)
    assert graph.has_node(definition_id("app/Widget.kt", "Widget"))
    imports = {(e["source"], e["target"]) for e in graph.edges() if e["type"] == "imports"}
    assert imports == {(file_id("app/Widget.kt"), file_id("util/Helper.kt"))}
