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


# --- T4: generic naming and exported defaults -------------------------------

def test_csharp_generics_named_without_type_parameters():
    r = code_csharp.extract("Box.cs", b"public class Box<T> { public T Get<T>() { return default; } }\n")
    quals = {(d.qualname, d.kind) for d in r.definitions}
    assert ("Box", "Class") in quals
    assert ("Box.Get", "Function") in quals


def test_csharp_exported_defaults():
    source = b"""
class Plain {
    void Implicit() {}
    public void Pub() {}
    internal void Int() {}
    protected void Prot() {}
    private void Priv() {}
    private protected void PrivProt() {}
    class Nested {}
}
interface IFace { void Member(); }
"""
    by = {d.qualname: d.exported for d in code_csharp.extract("P.cs", source).definitions}
    assert by["Plain"] is True          # unmodified top-level type is internal
    assert by["Plain.Pub"] and by["Plain.Int"] and by["Plain.Prot"]
    assert by["Plain.Implicit"] is False
    assert by["Plain.Priv"] is False
    assert by["Plain.PrivProt"] is False
    assert by["Plain.Nested"] is False
    assert by["IFace.Member"] is True


# --- T5: empty, malformed, top-level statements -----------------------------

def test_csharp_empty_and_declaration_free_files_are_known_files(tmp_path):
    (tmp_path / "Empty.cs").write_text("")
    (tmp_path / "OnlyUsings.cs").write_text("using System;\nnamespace N;\n")
    graph, report = build_graph(tmp_path)
    for rel in ("Empty.cs", "OnlyUsings.cs"):
        node = graph.get_node(file_id(rel))
        assert node is not None and node["language"] == "csharp" and not node.get("unparsed")
        assert rel not in report.unparsed
    assert not [n for n in graph.nodes() if n["type"] in ("Class", "Function")]


def test_csharp_malformed_file_builds_without_raising(tmp_path):
    (tmp_path / "Bad.cs").write_text("public class { void ( \n namespace ;;; }}}\n")
    graph, _ = build_graph(tmp_path)
    assert graph.get_node(file_id("Bad.cs")) is not None


def test_csharp_top_level_statements_local_function(tmp_path):
    (tmp_path / "Program.cs").write_text("using System;\nConsole.WriteLine(Twice(2));\nint Twice(int x) { return x * 2; }\n")
    graph, _ = build_graph(tmp_path)
    fn = definition_id("Program.cs", "Twice")
    assert graph.has_node(fn)
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    assert (file_id("Program.cs"), fn, "contains") in edges


# --- T8: resolution edge cases ----------------------------------------------

def _imports(graph):
    return {(e["source"], e["target"]) for e in graph.edges() if e["type"] == "imports"}


def test_csharp_using_static_resolves_to_declaring_file_only(tmp_path):
    (tmp_path / "Helper.cs").write_text("namespace Acme.Util { public static class Helper { public static void H() {} } }\n")
    (tmp_path / "Other.cs").write_text("namespace Acme.Util { public class Other {} }\n")
    (tmp_path / "Use.cs").write_text("using static Acme.Util.Helper;\nnamespace Acme.App { public class Use {} }\n")
    graph, _ = build_graph(tmp_path)
    assert _imports(graph) == {(file_id("Use.cs"), file_id("Helper.cs"))}


def test_csharp_namespace_fans_out_to_every_declaring_file_deterministically(tmp_path):
    for n in ("A", "B", "C"):
        (tmp_path / f"{n}.cs").write_text(f"namespace Acme.Util {{ public class {n} {{}} }}\n")
    (tmp_path / "Use.cs").write_text("using Acme.Util;\nnamespace Acme.App { public class Use {} }\n")
    g1, _ = build_graph(tmp_path)
    g2, _ = build_graph(tmp_path)
    assert _imports(g1) == {(file_id("Use.cs"), file_id(f"{n}.cs")) for n in "ABC"}
    assert g1.to_dict() == g2.to_dict()


def test_csharp_own_namespace_using_has_no_self_edge(tmp_path):
    (tmp_path / "A.cs").write_text("using Acme.Util;\nnamespace Acme.Util { public class A {} }\n")
    (tmp_path / "B.cs").write_text("namespace Acme.Util { public class B {} }\n")
    graph, _ = build_graph(tmp_path)
    assert _imports(graph) == {(file_id("A.cs"), file_id("B.cs"))}


def test_csharp_edges_end_on_real_nodes(tmp_path):
    (tmp_path / "A.cs").write_text("using Acme.Util;\nnamespace Acme.App { public class A { public void M() { void L() {} } public class In {} } }\n")
    (tmp_path / "B.cs").write_text("namespace Acme.Util { public struct B { public B() {} } }\n")
    graph, _ = build_graph(tmp_path)
    for e in graph.edges():
        if e["type"] in ("contains", "imports"):
            assert graph.has_node(e["source"]) and graph.has_node(e["target"]), e
