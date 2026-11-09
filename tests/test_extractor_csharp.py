"""C# extractor + cross-file `using` resolution + unparsed-path behaviour."""

from aspark_graph.build import build_graph
from aspark_graph.extractors import code_csharp
from aspark_graph.model import definition_id, file_id

SOURCE = b"""
using System;
using static Acme.Util.Helper;
using Fmt = Acme.Util.Formatter;
global using Acme.Core;

namespace Acme.App
{
    public class Widget
    {
        public Widget() {}
        public string Render()
        {
            int Local() { return 1; }
            return Local().ToString();
        }
        public class Inner { public void Go() {} }
    }
    public struct Point { public int X; public void Move() {} }
    public interface IShape { double Area(); }
    public record Person(string Name);
    public enum Color { Red, Green }
    public class Box<T> { public T Get() { return default; } }
}
"""


def test_csharp_extractor_finds_types_methods_namespace_usings():
    r = code_csharp.extract("src/Widget.cs", SOURCE)
    assert r.language == "csharp"
    assert r.package == "Acme.App"
    defs = {(d.qualname, d.kind, d.parent) for d in r.definitions}
    for cls in ("Widget", "Point", "IShape", "Person", "Color", "Box"):
        assert (cls, "Class", None) in defs
    assert ("Widget.Inner", "Class", "Widget") in defs
    assert ("Widget.Widget", "Function", "Widget") in defs  # constructor
    assert ("Widget.Render", "Function", "Widget") in defs
    assert ("Widget.Render.Local", "Function", "Widget.Render") in defs  # local function
    assert ("Widget.Inner.Go", "Function", "Widget.Inner") in defs
    assert ("Point.Move", "Function", "Point") in defs
    assert ("IShape.Area", "Function", "IShape") in defs
    assert ("Box.Get", "Function", "Box") in defs
    assert {i.module for i in r.imports} == {"System", "Acme.Util.Helper", "Acme.Util.Formatter", "Acme.Core"}


def test_csharp_file_scoped_namespace_and_record_struct():
    r = code_csharp.extract("A.cs", b"namespace Acme.Fs;\nrecord struct RS(int a);\nclass C { void M() {} }\n")
    assert r.package == "Acme.Fs"
    assert {(d.qualname, d.kind) for d in r.definitions} >= {("RS", "Class"), ("C", "Class"), ("C.M", "Function")}


def test_csharp_syntax_noise_does_not_raise():
    r = code_csharp.extract("Bad.cs", b"class { void ( \n")
    assert r.language == "csharp"


def test_build_resolves_csharp_using(tmp_path):
    (tmp_path / "Util").mkdir()
    (tmp_path / "App").mkdir()
    (tmp_path / "Util" / "Helper.cs").write_text("namespace Acme.Util { public class Helper { public static void Run() {} } }\n")
    (tmp_path / "Util" / "Other.cs").write_text("namespace Acme.Util { public class Other {} }\n")
    (tmp_path / "App" / "Widget.cs").write_text(
        "using System;\nusing Acme.Util;\nusing Newtonsoft.Json;\nnamespace Acme.App { public class Widget { public void Go() {} } }\n"
    )
    (tmp_path / "App" / "Alias.cs").write_text(
        "using static Acme.Util.Helper;\nnamespace Acme.App { public class Alias {} }\n"
    )
    graph, _ = build_graph(tmp_path)
    assert graph.has_node(definition_id("App/Widget.cs", "Widget.Go"))
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    for src in ("App/Widget.cs", "App/Alias.cs"):
        for tgt in ("Util/Helper.cs", "Util/Other.cs"):
            assert (file_id(src), file_id(tgt), "imports") in edges
    # BCL / third-party namespaces resolve to nothing; no self-edges.
    imports = [e for e in edges if e[2] == "imports"]
    assert len(imports) == 4
