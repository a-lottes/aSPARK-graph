"""T9: TypeScript/JavaScript extractor + cross-file import resolution (AC-4.1)."""

from aspark_graph.build import build_graph
from aspark_graph.extractors import code_ts
from aspark_graph.model import definition_id, file_id


def test_ts_extractor_finds_classes_functions_methods_arrows():
    source = b"""
import { helper } from "./util";

export class Widget {
  render() {
    return helper(1);
  }
}

export function build() {
  return new Widget();
}

const arrow = (x) => x + 1;
"""
    r = code_ts.extract("src/app.ts", source)
    quals = {(d.qualname, d.kind) for d in r.definitions}
    assert ("Widget", "Class") in quals
    assert ("Widget.render", "Function") in quals
    assert ("build", "Function") in quals
    assert ("arrow", "Function") in quals
    modules = {i.module for i in r.imports}
    assert "./util" in modules


def test_js_is_parsed_too():
    source = b"function f() { return 1; }\nclass C {}\n"
    r = code_ts.extract("x.js", source)
    assert r.language == "javascript"
    quals = {d.qualname for d in r.definitions}
    assert {"f", "C"} <= quals


def test_build_resolves_relative_ts_import(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "util.ts").write_text("export function helper(v) { return v; }\n")
    (tmp_path / "src" / "app.ts").write_text(
        'import { helper } from "./util";\nexport function main() { return helper(1); }\n'
    )
    graph, _ = build_graph(tmp_path)
    assert graph.has_node(definition_id("src/app.ts", "main"))
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    assert (file_id("src/app.ts"), file_id("src/util.ts"), "imports") in edges


def test_bare_specifier_does_not_resolve(tmp_path):
    (tmp_path / "a.ts").write_text('import { x } from "react";\nexport const y = () => 1;\n')
    graph, _ = build_graph(tmp_path)
    imports = [e for e in graph.edges() if e["type"] == "imports"]
    assert imports == []  # npm packages are not repo files
