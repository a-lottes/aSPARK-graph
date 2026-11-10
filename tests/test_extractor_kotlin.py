"""Kotlin extractor: classes/objects, functions, extensions, companions, imports."""

from aspark_graph import extractors
from aspark_graph.build import build_graph
from aspark_graph.extractors import code_kotlin
from aspark_graph.model import definition_id, file_id

SOURCE = b"""package com.example.app

import com.example.util.Helper
import com.example.util.Tools.Inner
import com.example.wild.*

class Widget {
    companion object {
        fun create(): Widget = Widget()
    }

    fun render(): String = ""
    private fun reset() {}
    class Nested
}

data class Point(val x: Int, val y: Int)

object Registry {
    fun lookup() {}
}

interface Shape {
    fun area(): Double
}

enum class Color {
    RED;
    fun hex(): String = ""
}

fun String.shout(): String = this

fun top() {}
"""


def _quals(r):
    return {(d.qualname, d.kind, d.parent) for d in r.definitions}


def test_kotlin_extractor_finds_package_classes_functions():
    r = code_kotlin.extract("src/Widget.kt", SOURCE)
    assert r.language == "kotlin"
    assert r.package == "com.example.app"
    q = _quals(r)
    for name in ("Widget", "Point", "Registry", "Shape", "Color"):
        assert (name, "Class", None) in q
    assert ("Widget.render", "Function", "Widget") in q
    assert ("Widget.Nested", "Class", "Widget") in q
    assert ("Registry.lookup", "Function", "Registry") in q
    assert ("Shape.area", "Function", "Shape") in q
    assert ("Color.hex", "Function", "Color") in q
    assert ("top", "Function", None) in q


def test_kotlin_companion_members_nest_under_companion():
    q = _quals(code_kotlin.extract("W.kt", SOURCE))
    assert ("Widget.Companion", "Class", "Widget") in q
    assert ("Widget.Companion.create", "Function", "Widget.Companion") in q


def test_kotlin_extension_function_is_top_level_named_by_receiver():
    q = _quals(code_kotlin.extract("W.kt", SOURCE))
    assert ("String.shout", "Function", None) in q


def test_kotlin_private_is_not_exported():
    r = code_kotlin.extract("W.kt", SOURCE)
    by = {d.qualname: d for d in r.definitions}
    assert by["Widget.reset"].exported is False
    assert by["Widget.render"].exported is True


def test_kotlin_imports_captured_with_wildcard():
    r = code_kotlin.extract("W.kt", SOURCE)
    mods = {i.module for i in r.imports}
    assert {"com.example.util.Helper", "com.example.util.Tools.Inner", "com.example.wild.*"} <= mods


def test_kotlin_script_file_extracted(tmp_path):
    (tmp_path / "build.gradle.kts").write_text("fun helper() {}\n")
    graph, _ = build_graph(tmp_path)
    assert graph.has_node(definition_id("build.gradle.kts", "helper"))


def test_build_resolves_kotlin_imports(tmp_path):
    (tmp_path / "util").mkdir()
    (tmp_path / "app").mkdir()
    (tmp_path / "util" / "Helper.kt").write_text("package com.example.util\n\nclass Helper {\n    class Inner\n}\n")
    (tmp_path / "util" / "Fns.kt").write_text("package com.example.util\n\nfun helperFn() {}\n")
    (tmp_path / "app" / "Main.kt").write_text(
        "package com.example.app\n\nimport com.example.util.Helper.Inner\n"
        "import com.example.util.helperFn\nimport com.example.util.*\nimport kotlin.collections.List\n\nfun main() {}\n"
    )
    graph, _ = build_graph(tmp_path)
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    src = file_id("app/Main.kt")
    assert (src, file_id("util/Fns.kt"), "imports") in edges
    # nested (Helper.Inner) resolves to no edge; only the plain function import does.
    assert (src, file_id("util/Fns.kt"), "imports") in edges
    assert len([e for e in edges if e[0] == src and e[2] == "imports"]) == 1


def test_build_contains_edges_for_kotlin(tmp_path):
    (tmp_path / "W.kt").write_text("class W {\n    fun m() {}\n}\n")
    graph, _ = build_graph(tmp_path)
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    assert (file_id("W.kt"), definition_id("W.kt", "W"), "contains") in edges
    assert (definition_id("W.kt", "W"), definition_id("W.kt", "W.m"), "contains") in edges


def test_kotlin_unparsed_when_extractor_cut(tmp_path, monkeypatch):
    monkeypatch.setitem(extractors._REGISTRY, "kotlin", None)
    monkeypatch.setattr(extractors, "get_extractor", lambda lang: extractors._REGISTRY.get(lang))
    (tmp_path / "K.kt").write_text("class K\n")
    graph, _ = build_graph(tmp_path)
    node = graph.get_node(file_id("K.kt"))
    assert node.get("unparsed") is True


# --- ambiguity-safe, exact import resolution (AC-2.1, 2.4, 2.5) ---------------

def _imports_from(graph, rel):
    return {e["target"] for e in graph.edges() if e["source"] == file_id(rel) and e["type"] == "imports"}


def _write(root, rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def test_import_of_class_object_interface_and_fun_each_resolve(tmp_path):
    _write(tmp_path, "p/A.kt", "package p\n\nclass A\n")
    _write(tmp_path, "p/B.kt", "package p\n\nobject B\n")
    _write(tmp_path, "p/C.kt", "package p\n\ninterface C\n")
    _write(tmp_path, "p/D.kt", "package p\n\nfun d() {}\n")
    _write(tmp_path, "q/Use.kt", "package q\n\nimport p.A\nimport p.B\nimport p.C\nimport p.d\n")
    graph, _ = build_graph(tmp_path)
    assert _imports_from(graph, "q/Use.kt") == {file_id(f"p/{n}.kt") for n in "ABCD"}
    ids = {n["id"] for n in graph.nodes()}
    assert all(e["source"] in ids and e["target"] in ids for e in graph.edges())


def test_extension_function_import_resolves_on_function_name(tmp_path):
    _write(tmp_path, "p/Ext.kt", "package p\n\nfun String.shout(): String = this\n")
    _write(tmp_path, "q/Use.kt", "package q\n\nimport p.shout\n")
    graph, _ = build_graph(tmp_path)
    assert _imports_from(graph, "q/Use.kt") == {file_id("p/Ext.kt")}


def test_ambiguous_import_resolves_to_no_edge(tmp_path):
    _write(tmp_path, "a/Dup1.kt", "package p\n\nclass Dup\n")
    _write(tmp_path, "b/Dup2.kt", "package p\n\nclass Dup\n")
    _write(tmp_path, "q/Use.kt", "package q\n\nimport p.Dup\n")
    graph, _ = build_graph(tmp_path)
    assert _imports_from(graph, "q/Use.kt") == set()


def test_nested_class_import_resolves_to_no_edge(tmp_path):
    _write(tmp_path, "p/Helper.kt", "package p\n\nclass Helper {\n    class Inner\n}\n")
    _write(tmp_path, "q/Use.kt", "package q\n\nimport p.Helper.Inner\n")
    graph, _ = build_graph(tmp_path)
    assert _imports_from(graph, "q/Use.kt") == set()


def test_alias_import_resolves_like_plain_import():
    r = code_kotlin.extract("U.kt", b"package q\n\nimport com.example.util.Helper as H\n")
    assert [i.module for i in r.imports] == ["com.example.util.Helper"]


def test_alias_import_builds_one_edge(tmp_path):
    _write(tmp_path, "p/Helper.kt", "package com.example.util\n\nclass Helper\n")
    _write(tmp_path, "q/Use.kt", "package q\n\nimport com.example.util.Helper as H\n")
    graph, _ = build_graph(tmp_path)
    assert _imports_from(graph, "q/Use.kt") == {file_id("p/Helper.kt")}


# --- empty / malformed files (AC-1.9, 1.10) -----------------------------------

def test_empty_and_package_only_kotlin_files_are_parsed_files(tmp_path):
    _write(tmp_path, "Empty.kt", "")
    _write(tmp_path, "Pkg.kt", "// just a comment\npackage only.pkg\n")
    graph, _ = build_graph(tmp_path)
    for rel in ("Empty.kt", "Pkg.kt"):
        node = graph.get_node(file_id(rel))
        assert node["language"] == "kotlin" and not node.get("unparsed")
        assert not [e for e in graph.edges() if e["source"] == file_id(rel) and e["type"] == "contains"]
    assert graph.get_node(file_id("Pkg.kt"))["package"] == "only.pkg"


def test_malformed_kotlin_does_not_raise_and_keeps_valid_neighbours(tmp_path, capsys):
    from aspark_graph import cli

    _write(tmp_path, "Bad.kt", "class Ok\n\nfun broken( {\n\nclass AlsoOk\n")
    (tmp_path / ".git").mkdir()
    graph, _ = build_graph(tmp_path)
    assert graph.has_node(definition_id("Bad.kt", "Ok"))
    assert not graph.get_node(file_id("Bad.kt")).get("unparsed")
    assert cli.main(["build", str(tmp_path)]) == 0
    assert "Traceback" not in capsys.readouterr().err


# --- structural hardening (AC-1.1/1.2/1.3/1.6/1.7, NFR-2/3) -------------------

HARD = """package h.k

sealed class S

class Host {
    companion object Factory {
        fun make(): Host = Host()
    }

    fun String.tag(): String = this
}

fun top() {}
"""


def test_build_level_file_node_and_kts_contains(tmp_path):
    _write(tmp_path, "H.kt", HARD)
    _write(tmp_path, "s.kts", "fun helper() {}\n")
    graph, _ = build_graph(tmp_path)
    node = graph.get_node(file_id("H.kt"))
    assert node["language"] == "kotlin" and node["package"] == "h.k" and not node.get("unparsed")
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    assert (file_id("s.kts"), definition_id("s.kts", "helper"), "contains") in edges


def test_sealed_named_companion_and_member_extension():
    q = _quals(code_kotlin.extract("H.kt", HARD.encode()))
    assert ("S", "Class", None) in q
    assert ("Host.Factory", "Class", "Host") in q
    assert ("Host.Factory.make", "Function", "Host.Factory") in q
    assert ("Host.String.tag", "Function", "Host") in q


def test_kotlin_edges_are_extracted_and_endpoints_exist(tmp_path):
    _write(tmp_path, "p/H.kt", HARD)
    _write(tmp_path, "q/Use.kt", "package q\n\nimport h.k.S\nimport h.k.top\n")
    graph, _ = build_graph(tmp_path)
    ids = {n["id"] for n in graph.nodes()}
    kt = [e for e in graph.edges() if e["type"] in ("contains", "imports") and ".kt" in e["source"]]
    assert kt
    for e in kt:
        assert e["source"] in ids and e["target"] in ids
        assert e["confidence"] == "extracted"
