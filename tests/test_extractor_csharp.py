"""C# extractor: types, methods, constructors, local functions, usings, build resolution."""

from aspark_graph.build import build_graph
from aspark_graph.extractors import code_csharp, get_extractor
from aspark_graph.model import definition_id, file_id


def test_csharp_extractor_finds_namespace_types_and_methods():
    source = b"""
using System;
using Acme.Util;

namespace Acme.App
{
    public class Widget
    {
        public Widget() {}
        public string Render() { return new Helper().Format(); }
        private void Reset() {}
        public class Inner { public void Go() {} }
    }
    public struct Point {}
    public interface IShape { void Draw(); }
    public record Person(string Name);
    public enum Color { Red }
}
"""
    r = code_csharp.extract("src/Widget.cs", source)
    assert r.language == "csharp"
    assert r.package == "Acme.App"
    quals = {(d.qualname, d.kind) for d in r.definitions}
    for q in ("Widget", "Point", "IShape", "Person", "Color", "Widget.Inner"):
        assert (q, "Class") in quals
    for q in ("Widget.Widget", "Widget.Render", "Widget.Reset", "Widget.Inner.Go", "IShape.Draw"):
        assert (q, "Function") in quals
    by = {d.qualname: d for d in r.definitions}
    assert by["Widget.Inner"].parent == "Widget"
    assert by["Widget.Reset"].exported is False
    assert by["Widget.Render"].exported is True
    assert {i.module for i in r.imports} == {"System", "Acme.Util"}


def test_csharp_file_scoped_namespace_and_local_function():
    source = b"""namespace Acme.Scoped;
public class Svc
{
    public int Run()
    {
        int Helper() { return 1; }
        return Helper();
    }
}
"""
    r = code_csharp.extract("Svc.cs", source)
    assert r.package == "Acme.Scoped"
    by = {d.qualname: d for d in r.definitions}
    assert by["Svc.Run.Helper"].kind == "Function"
    assert by["Svc.Run.Helper"].parent == "Svc.Run"


def test_csharp_using_variants():
    r = code_csharp.extract("a.cs", b"using static Acme.Util.Helper;\nusing A = Acme.Other;\nglobal using Acme.G;\n")
    assert [i.module for i in r.imports] == ["Acme.Util.Helper", "Acme.Other", "Acme.G"]


def test_csharp_registered():
    assert get_extractor("csharp") is code_csharp.extract


def test_build_resolves_csharp_using(tmp_path):
    (tmp_path / "Util").mkdir()
    (tmp_path / "App").mkdir()
    (tmp_path / "Util" / "Helper.cs").write_text("namespace Acme.Util { public class Helper { public string Format() { return \"\"; } } }\n")
    (tmp_path / "App" / "Widget.cs").write_text(
        "using System;\nusing Acme.Util;\nnamespace Acme.App { public class Widget { public void Go() {} } }\n"
    )
    graph, _ = build_graph(tmp_path)
    assert graph.has_node(definition_id("App/Widget.cs", "Widget.Go"))
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    assert (file_id("App/Widget.cs"), file_id("Util/Helper.cs"), "imports") in edges
    # `using System;` is not in the repo: no edge, no failure.
    assert sum(1 for s, _, t in edges if s == file_id("App/Widget.cs") and t == "imports") == 1
