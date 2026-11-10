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


# --- T5: extractor edge cases -------------------------------------------------

def test_generic_names_are_bare():
    r = code_csharp.extract("B.cs", b"class Box<T> { public T Get<T>() { return default; } }\n")
    q = _quals(r)
    assert ("Box", "Class") in q
    assert ("Box.Get", "Function") in q


def test_empty_file_is_parsed_with_no_definitions(tmp_path):
    (tmp_path / "Empty.cs").write_text("")
    graph, report = build_graph(tmp_path)
    node = graph.get_node(file_id("Empty.cs"))
    assert node["language"] == "csharp"
    assert not node.get("unparsed")
    assert "Empty.cs" not in report.unparsed


def test_record_struct_and_top_level_type_without_namespace():
    r = code_csharp.extract("R.cs", b"record struct Pt(int X);\nclass Top {}\n")
    assert ("Pt", "Class") in _quals(r)
    assert ("Top", "Class") in _quals(r)
    assert r.package is None


def test_broken_source_does_not_raise(tmp_path):
    (tmp_path / "Bad.cs").write_text("namespace X { class { void ( \n")
    graph, _ = build_graph(tmp_path)
    assert graph.get_node(file_id("Bad.cs"))["language"] == "csharp"


def test_overloads_yield_one_function_node(tmp_path):
    (tmp_path / "O.cs").write_text("class O { void M() {} void M(int a) {} }\n")
    graph, _ = build_graph(tmp_path)
    ids = [n["id"] for n in graph.nodes() if n["type"] == "Function" and n.get("name") == "O.M"]
    assert len(ids) == 1


# --- T6: build-level using resolution ----------------------------------------

def _repo_with_target(tmp_path, using_line):
    (tmp_path / "T.cs").write_text("namespace N { public class T {} }\n")
    (tmp_path / "U.cs").write_text(f"{using_line}\nclass U {{}}\n")
    graph, _ = build_graph(tmp_path)
    return graph


def _import_edges(graph):
    return [e for e in graph.edges() if e["type"] == "imports"]


def test_using_variants_resolve_at_build_level(tmp_path):
    for i, line in enumerate(["using N.T;", "using static N.T;", "using X = N.T;", "global using N;", "using N;"]):
        sub = tmp_path / f"r{i}"
        sub.mkdir()
        (sub / ".git").mkdir()
        graph = _repo_with_target(sub, line)
        edges = _import_edges(graph)
        assert [(e["source"], e["target"]) for e in edges] == [(file_id("U.cs"), file_id("T.cs"))], line
        assert edges[0]["confidence"] == "extracted"


def test_external_using_emits_no_edge_and_graph_is_consistent(tmp_path):
    graph = _repo_with_target(tmp_path, "using System.Linq;\nusing Newtonsoft.Json;")
    assert _import_edges(graph) == []
    for e in graph.edges():
        assert graph.has_node(e["source"]) and graph.has_node(e["target"])


# --- Review F1/F2: preprocessor blocks; AC-3.1 unmapped extension -------------

def test_declarations_inside_preprocessor_blocks_are_extracted():
    source = b"""#if NETFX
using Acme.Legacy;
#endif
namespace N
{
#if A
    class X { void M() {} }
#elif B
    class Y {}
#else
    class Z {}
#endif
    class C
    {
#if NET6_0_OR_GREATER
        void New() {}
#else
        void Old() {}
#endif
    }
}
"""
    r = code_csharp.extract("P.cs", source)
    q = _quals(r)
    for cls in ("X", "Y", "Z", "C"):
        assert (cls, "Class") in q
    for fn in ("X.M", "C.New", "C.Old"):
        assert (fn, "Function") in q
    assert [i.module for i in r.imports] == ["Acme.Legacy"]


def test_same_type_in_both_preprocessor_branches_still_resolves(tmp_path):
    (tmp_path / "T.cs").write_text("namespace N {\n#if A\n public class T {}\n#else\n public class T {}\n#endif\n}\n")
    (tmp_path / "U.cs").write_text("using static N.T;\nclass U {}\n")
    graph, _ = build_graph(tmp_path)
    assert [(e["source"], e["target"]) for e in _import_edges(graph)] == [(file_id("U.cs"), file_id("T.cs"))]


def test_unmapped_extension_gets_no_language_and_no_node(tmp_path):  # AC-3.1, second clause
    assert language_for("x.rb") is None
    (tmp_path / "x.rb").write_text("class Foo; end\n")
    (tmp_path / "A.cs").write_text("class A {}\n")
    graph, report = build_graph(tmp_path)
    assert graph.get_node(file_id("x.rb")) is None
    assert "x.rb" not in report.unparsed
    assert graph.get_node(file_id("A.cs"))["language"] == "csharp"
