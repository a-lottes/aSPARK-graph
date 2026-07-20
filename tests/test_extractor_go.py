"""go-rust-support T2: Go extractor — types, functions, methods, exported."""

from aspark_graph.build import build_graph
from aspark_graph.extractors import code_go
from aspark_graph.model import definition_id, file_id


def test_go_extractor_finds_package_struct_interface_and_functions():
    source = b"""package widget

type Widget struct {
    Name string
}

type Shape interface {
    Area() float64
}

func Free() int {
    return 1
}

func (w *Widget) Render() string {
    return w.Name
}
"""
    r = code_go.extract("widget.go", source)
    assert r.package == "widget"
    quals = {(d.qualname, d.kind, d.parent) for d in r.definitions}
    assert ("Widget", "Class", None) in quals
    assert ("Shape", "Class", None) in quals
    assert ("Free", "Function", None) in quals
    assert ("Widget.Render", "Function", "Widget") in quals  # AC-1.4: same-file nest


def test_go_exported_follows_capitalization():  # AC-1.6
    source = b"""package widget

func Public() {}
func private() {}
"""
    r = code_go.extract("widget.go", source)
    exported = {d.qualname: d.exported for d in r.definitions}
    assert exported["Public"] is True
    assert exported["private"] is False


def test_build_go_same_file_method_nests_under_class(tmp_path):  # AC-1.4
    (tmp_path / "widget.go").write_text(
        "package widget\n\ntype Widget struct{}\n\nfunc (w *Widget) Render() string { return \"\" }\n"
    )
    graph, _ = build_graph(tmp_path)
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    assert (
        definition_id("widget.go", "Widget"),
        definition_id("widget.go", "Widget.Render"),
        "contains",
    ) in edges


def test_build_go_cross_file_method_becomes_top_level_function(tmp_path):  # AC-1.5
    (tmp_path / "widget.go").write_text("package widget\n\ntype Widget struct{}\n")
    (tmp_path / "render.go").write_text(
        "package widget\n\nfunc (w *Widget) Render() string { return \"\" }\n"
    )
    graph, _ = build_graph(tmp_path)
    did = definition_id("render.go", "Widget.Render")
    assert graph.has_node(did)
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    # captured from its own File, never nested under the Class in the other file
    assert (file_id("render.go"), did, "contains") in edges
    assert (definition_id("widget.go", "Widget"), did, "contains") not in edges
    # every edge endpoint must exist as a node (NFR-2)
    node_ids = {n["id"] for n in graph.nodes()}
    for src, tgt, _ in edges:
        assert src in node_ids
        assert tgt in node_ids


def test_go_empty_file_is_not_unparsed(tmp_path):  # AC-1.8
    (tmp_path / "empty.go").write_text("package widget\n")
    graph, report = build_graph(tmp_path)
    node = graph.get_node(file_id("empty.go"))
    assert node is not None
    assert node.get("unparsed") is not True
    assert "empty.go" not in report.unparsed


def test_build_resolves_go_import(tmp_path):  # AC-3.1
    (tmp_path / "internal" / "util").mkdir(parents=True)
    (tmp_path / "internal" / "app").mkdir(parents=True)
    (tmp_path / "internal" / "util" / "helper.go").write_text("package util\n\nfunc Format() string { return \"\" }\n")
    (tmp_path / "internal" / "app" / "widget.go").write_text(
        "package app\n\nimport \"example.com/myrepo/internal/util\"\n\nfunc Go() { util.Format() }\n"
    )
    graph, _ = build_graph(tmp_path)
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    assert (
        file_id("internal/app/widget.go"),
        file_id("internal/util/helper.go"),
        "imports",
    ) in edges


def test_build_go_stdlib_import_yields_no_edge(tmp_path):  # AC-3.2
    (tmp_path / "widget.go").write_text("package widget\n\nimport \"fmt\"\n\nfunc F() { fmt.Println(\"x\") }\n")
    graph, _ = build_graph(tmp_path)
    edges = [e for e in graph.edges() if e["type"] == "imports"]
    assert edges == []


def test_build_go_ambiguous_import_yields_no_edge(tmp_path):  # AC-3.3
    (tmp_path / "a" / "util").mkdir(parents=True)
    (tmp_path / "b" / "util").mkdir(parents=True)
    (tmp_path / "a" / "util" / "u.go").write_text("package util\n\nfunc A() {}\n")
    (tmp_path / "b" / "util" / "u.go").write_text("package util\n\nfunc B() {}\n")
    (tmp_path / "app.go").write_text("package main\n\nimport \"myrepo/util\"\n\nfunc Main() {}\n")
    graph, _ = build_graph(tmp_path)
    edges = [e for e in graph.edges() if e["type"] == "imports"]
    assert edges == []


def test_double_build_go_is_deterministic(tmp_path):  # AC-1.7
    (tmp_path / "widget.go").write_text(
        "package widget\n\ntype Widget struct{}\n\nfunc (w *Widget) Render() string { return \"\" }\n\nfunc Free() int { return 1 }\n"
    )
    g1, _ = build_graph(tmp_path)
    g2, _ = build_graph(tmp_path)
    assert g1.to_dict() == g2.to_dict()
