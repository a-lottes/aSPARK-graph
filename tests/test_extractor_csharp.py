"""C# extractor + cross-file `using` resolution."""

from aspark_graph.build import build_graph
from aspark_graph.extractors import code_csharp, language_for
from aspark_graph.model import definition_id, file_id


def _quals(r):
    return {(d.qualname, d.kind) for d in r.definitions}


def test_csharp_extractor_finds_types_methods_constructors():
    source = b"""
using System;
using Acme.Util;

namespace Acme.App
{
    public class Widget
    {
        public Widget() {}
        public string Render() { return ""; }
        private void Reset() {}
        public class Inner { public void Go() {} }
    }
    public interface IThing { void Do(); }
    public struct Pt { public int X; }
    public enum Color { Red }
    public record Person(string Name);
}
"""
    r = code_csharp.extract("src/Widget.cs", source)
    assert r.language == "csharp"
    assert r.package == "Acme.App"
    q = _quals(r)
    for cls in ("Widget", "Widget.Inner", "IThing", "Pt", "Color", "Person"):
        assert (cls, "Class") in q
    for fn in ("Widget.Widget", "Widget.Render", "Widget.Reset", "Widget.Inner.Go", "IThing.Do"):
        assert (fn, "Function") in q
    inner = next(d for d in r.definitions if d.qualname == "Widget.Inner")
    assert inner.parent == "Widget"
    assert {i.module for i in r.imports} == {"System", "Acme.Util"}


def test_csharp_local_function_and_file_scoped_namespace():
    source = b"""
namespace Acme.Core;

class Calc
{
    int Run()
    {
        int Helper() { return 1; }
        return Helper();
    }
}
"""
    r = code_csharp.extract("Calc.cs", source)
    assert r.package == "Acme.Core"
    q = _quals(r)
    assert ("Calc", "Class") in q
    assert ("Calc.Run.Helper", "Function") in q
    helper = next(d for d in r.definitions if d.qualname == "Calc.Run.Helper")
    assert helper.parent == "Calc.Run"


def test_csharp_using_variants():
    r = code_csharp.extract(
        "a.cs", b"using static Acme.Util.Helper;\nusing H = Acme.Util.Helper;\nglobal using Acme.Core;\nclass A {}\n"
    )
    assert [i.module for i in r.imports] == ["Acme.Util.Helper", "Acme.Util.Helper", "Acme.Core"]


def test_cs_extension_maps_to_csharp():
    assert language_for("x/Y.cs") == "csharp"


def test_build_resolves_csharp_using(tmp_path):
    (tmp_path / "Util").mkdir()
    (tmp_path / "App").mkdir()
    (tmp_path / "Util" / "Helper.cs").write_text("namespace Acme.Util { public class Helper { public string Format() { return \"\"; } } }\n")
    (tmp_path / "App" / "Widget.cs").write_text(
        "using System;\nusing Acme.Util;\nnamespace Acme.App { public class Widget { public void Go() { } } }\n"
    )
    graph, _ = build_graph(tmp_path)
    assert graph.has_node(definition_id("App/Widget.cs", "Widget"))
    assert graph.has_node(definition_id("App/Widget.cs", "Widget.Go"))
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    assert (file_id("App/Widget.cs"), file_id("Util/Helper.cs"), "imports") in edges
    assert (file_id("App/Widget.cs"), file_id("App/Widget.cs"), "imports") not in edges
    contains = {(e["source"], e["target"]) for e in graph.edges() if e["type"] == "contains"}
    assert (file_id("App/Widget.cs"), definition_id("App/Widget.cs", "Widget")) in contains


def test_csharp_using_ambiguous_type_emits_no_edge(tmp_path):
    (tmp_path / "A1.cs").write_text("namespace N { public partial class P {} }\n")
    (tmp_path / "A2.cs").write_text("namespace N { public partial class P {} }\n")
    (tmp_path / "U.cs").write_text("using static N.P;\nclass U {}\n")
    graph, _ = build_graph(tmp_path)
    assert not [e for e in graph.edges() if e["type"] == "imports"]
