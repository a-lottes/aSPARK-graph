"""go-rust-support T3: Rust extractor — struct/enum/trait, functions, impl blocks, pub."""

from aspark_graph.build import build_graph
from aspark_graph.extractors import code_rust
from aspark_graph.model import definition_id, file_id


def test_rust_extractor_finds_struct_enum_trait_and_functions():
    source = b"""pub struct Widget {
    name: String,
}

pub enum Shape {
    Circle,
    Square,
}

pub trait Drawable {
    fn draw(&self);
}

fn free_fn() -> i32 {
    1
}

impl Widget {
    pub fn render(&self) -> String {
        self.name.clone()
    }
}
"""
    r = code_rust.extract("widget.rs", source)
    quals = {(d.qualname, d.kind, d.parent) for d in r.definitions}
    assert ("Widget", "Class", None) in quals
    assert ("Shape", "Class", None) in quals
    assert ("Drawable", "Class", None) in quals
    assert ("free_fn", "Function", None) in quals
    assert ("Widget.render", "Function", "Widget") in quals  # AC-2.4: same-file nest


def test_rust_multiple_impl_blocks_fold_into_one_class():  # AC-2.4
    source = b"""pub struct Widget {}

pub trait Drawable {
    fn draw(&self);
}

impl Widget {
    pub fn render(&self) -> String { String::new() }
}

impl Drawable for Widget {
    fn draw(&self) {}
}
"""
    r = code_rust.extract("widget.rs", source)
    parents = {d.qualname: d.parent for d in r.definitions if d.kind == "Function"}
    assert parents["Widget.render"] == "Widget"
    assert parents["Widget.draw"] == "Widget"


def test_rust_exported_follows_pub():  # AC-2.6
    source = b"""pub fn public_fn() {}
fn private_fn() {}
"""
    r = code_rust.extract("widget.rs", source)
    exported = {d.qualname: d.exported for d in r.definitions}
    assert exported["public_fn"] is True
    assert exported["private_fn"] is False


def test_build_rust_same_file_impl_nests_under_class(tmp_path):  # AC-2.4
    (tmp_path / "widget.rs").write_text(
        "pub struct Widget {}\n\nimpl Widget {\n    pub fn render(&self) -> String { String::new() }\n}\n"
    )
    graph, _ = build_graph(tmp_path)
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    assert (
        definition_id("widget.rs", "Widget"),
        definition_id("widget.rs", "Widget.render"),
        "contains",
    ) in edges


def test_build_rust_cross_file_impl_becomes_top_level_function(tmp_path):  # AC-2.5
    (tmp_path / "widget.rs").write_text("pub struct Widget {}\n")
    (tmp_path / "render.rs").write_text(
        "use crate::widget::Widget;\n\nimpl Widget {\n    pub fn render(&self) -> String { String::new() }\n}\n"
    )
    graph, _ = build_graph(tmp_path)
    did = definition_id("render.rs", "Widget.render")
    assert graph.has_node(did)
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    assert (file_id("render.rs"), did, "contains") in edges
    assert (definition_id("widget.rs", "Widget"), did, "contains") not in edges
    node_ids = {n["id"] for n in graph.nodes()}
    for src, tgt, _ in edges:
        assert src in node_ids
        assert tgt in node_ids


def test_build_rust_impl_on_foreign_type_becomes_top_level_function(tmp_path):  # AC-2.5
    # `Foreign` is the impl target ("for" type) but is not declared in this
    # repo at all — the method must still be captured, never dropped.
    (tmp_path / "ext.rs").write_text(
        "use std::fmt;\n\nimpl fmt::Display for Foreign {\n    fn fmt(&self) {}\n}\n"
    )
    graph, _ = build_graph(tmp_path)
    did = definition_id("ext.rs", "Foreign.fmt")
    assert graph.has_node(did)
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    assert (file_id("ext.rs"), did, "contains") in edges


def test_rust_empty_file_is_not_unparsed(tmp_path):  # AC-2.8
    (tmp_path / "empty.rs").write_text("// nothing here\n")
    graph, report = build_graph(tmp_path)
    node = graph.get_node(file_id("empty.rs"))
    assert node is not None
    assert node.get("unparsed") is not True
    assert "empty.rs" not in report.unparsed


def test_build_resolves_rust_crate_import(tmp_path):  # AC-4.1
    (tmp_path / "src" / "widget").mkdir(parents=True)
    (tmp_path / "src" / "widget" / "mod.rs").write_text("pub struct Widget {}\n")
    (tmp_path / "src" / "lib.rs").write_text(
        "use crate::widget::Widget;\n\npub fn make() -> Widget { Widget {} }\n"
    )
    graph, _ = build_graph(tmp_path)
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    assert (
        file_id("src/lib.rs"),
        file_id("src/widget/mod.rs"),
        "imports",
    ) in edges


def test_build_resolves_rust_self_and_super_import(tmp_path):  # AC-4.1
    (tmp_path / "src" / "app").mkdir(parents=True)
    (tmp_path / "src" / "helper.rs").write_text("pub fn help() {}\n")
    (tmp_path / "src" / "app" / "mod.rs").write_text(
        "use super::helper::help;\n\npub fn run() { help(); }\n"
    )
    graph, _ = build_graph(tmp_path)
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    assert (
        file_id("src/app/mod.rs"),
        file_id("src/helper.rs"),
        "imports",
    ) in edges


def test_build_rust_external_crate_import_yields_no_edge(tmp_path):  # AC-4.2
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "lib.rs").write_text(
        "use serde::Serialize;\n\npub fn noop() {}\n"
    )
    graph, _ = build_graph(tmp_path)
    edges = [e for e in graph.edges() if e["type"] == "imports"]
    assert edges == []


def test_build_rust_ambiguous_import_yields_no_edge(tmp_path):  # AC-4.3
    # `src/util.rs` and `src/util/mod.rs` both map to the layout-only module
    # path `crate::util` — a genuine collision our no-manifest index can't
    # disambiguate. Resolution must not guess between them.
    (tmp_path / "src" / "util").mkdir(parents=True)
    (tmp_path / "src" / "util.rs").write_text("pub fn a() {}\n")
    (tmp_path / "src" / "util" / "mod.rs").write_text("pub fn b() {}\n")
    (tmp_path / "src" / "lib.rs").write_text("use crate::util::a;\n\npub fn run() { a(); }\n")
    graph, _ = build_graph(tmp_path)
    edges = [e for e in graph.edges() if e["type"] == "imports"]
    assert edges == []


def test_double_build_rust_is_deterministic(tmp_path):  # AC-2.7
    (tmp_path / "widget.rs").write_text(
        "pub struct Widget {}\n\nimpl Widget {\n    pub fn render(&self) -> String { String::new() }\n}\n\nfn free_fn() -> i32 { 1 }\n"
    )
    g1, _ = build_graph(tmp_path)
    g2, _ = build_graph(tmp_path)
    assert g1.to_dict() == g2.to_dict()
