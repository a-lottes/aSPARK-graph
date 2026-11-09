"""C# extractor + `using` import resolution + build integration."""

from aspark_graph.build import build_graph
from aspark_graph.extractors import code_csharp, language_for
from aspark_graph.model import definition_id, file_id

SOURCE = b"""
using System;
using static MyApp.Util.Helper;
using H = MyApp.Util;

namespace MyApp.Core
{
    public class Widget
    {
        public Widget() {}
        public string Render()
        {
            int Local() { return 1; }
            return "";
        }
        public struct Inner { public void Go() {} }
    }
    public interface IThing { void Do(); }
    public record Point(int X, int Y);
    public enum Color { Red }
}
"""


def test_csharp_extension_maps():
    assert language_for("src/A.cs") == "csharp"


def test_csharp_extractor_types_and_functions():
    r = code_csharp.extract("src/Widget.cs", SOURCE)
    assert r.language == "csharp"
    assert r.package == "MyApp.Core"
    defs = {(d.qualname, d.kind): d.parent for d in r.definitions}
    for q in ("Widget", "IThing", "Point", "Color", "Widget.Inner"):
        assert (q, "Class") in defs
    assert defs[("Widget.Inner", "Class")] == "Widget"
    assert defs[("Widget.Widget", "Function")] == "Widget"  # constructor
    assert ("Widget.Render", "Function") in defs
    assert defs[("Widget.Render.Local", "Function")] == "Widget.Render"  # local function
    assert ("Widget.Inner.Go", "Function") in defs
    assert ("IThing.Do", "Function") in defs


def test_csharp_file_scoped_namespace_and_struct():
    r = code_csharp.extract("A.cs", b"namespace Foo.Bar;\npublic struct S { public void M() {} }\nrecord struct RS(int a);\n")
    assert r.package == "Foo.Bar"
    assert {d.qualname for d in r.definitions} >= {"S", "S.M", "RS"}


def test_csharp_imports_as_written():
    r = code_csharp.extract("Widget.cs", SOURCE)
    assert {i.module for i in r.imports} == {"System", "MyApp.Util.Helper", "MyApp.Util"}


def test_build_resolves_csharp_using(tmp_path):
    (tmp_path / "Util.cs").write_text("namespace MyApp.Util;\npublic class Helper { public static void F() {} }\n")
    (tmp_path / "App.cs").write_text(
        "using System;\nusing MyApp.Util;\nusing static MyApp.Util.Helper;\nnamespace MyApp.App { class Program { static void Main() {} } }\n"
    )
    graph, report = build_graph(tmp_path)
    assert graph.has_node(definition_id("App.cs", "Program.Main"))
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    assert (file_id("App.cs"), file_id("Util.cs"), "imports") in edges
    assert (file_id("Util.cs"), definition_id("Util.cs", "Helper"), "contains") in edges
    # `using System` (BCL) resolves to nothing; no edge to an unrelated file.
    assert not any(t == "imports" and s == file_id("Util.cs") for s, _, t in edges)
    assert "App.cs" not in report.unparsed
