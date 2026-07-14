"""tree-sitter TypeScript/JavaScript extractor: File, classes, functions, imports.

Handles ``.ts``/``.js``/``.mjs``/``.cjs`` via the TypeScript grammar (a superset
of JS) and ``.tsx``/``.jsx`` via the TSX grammar. Captures class/function/method
declarations and ``const f = () => {}`` style function bindings, plus ES import
specifiers. Deterministic and offline.
"""

from __future__ import annotations

import tree_sitter_typescript
from tree_sitter import Language, Node, Parser

from .base import Definition, FileExtraction, Import

_TS = Language(tree_sitter_typescript.language_typescript())
_TSX = Language(tree_sitter_typescript.language_tsx())
_TS_PARSER = Parser(_TS)
_TSX_PARSER = Parser(_TSX)

_TSX_SUFFIXES = (".tsx", ".jsx")
_FUNCTION_VALUE_TYPES = {"arrow_function", "function_expression", "function"}


def extract(relpath: str, source: bytes) -> FileExtraction:
    parser = _TSX_PARSER if relpath.endswith(_TSX_SUFFIXES) else _TS_PARSER
    language = "typescript" if relpath.endswith((".ts", ".tsx")) else "javascript"
    tree = parser.parse(source)
    result = FileExtraction(relpath=relpath, language=language)
    _walk(tree.root_node, parent=None, exported=False, result=result)
    return result


def _text(node: Node) -> str:
    return node.text.decode("utf-8", errors="replace")


def _walk(node: Node, parent: str | None, exported: bool, result: FileExtraction) -> None:
    for child in node.named_children:
        t = child.type
        if t == "export_statement":
            # `export class/function/const …` — mark contents exported and recurse.
            _walk(child, parent=parent, exported=True, result=result)
        elif t in ("class_declaration", "abstract_class_declaration"):
            _add_class(child, parent, exported, result)
        elif t in ("function_declaration", "generator_function_declaration"):
            _add_function(child, parent, exported, result)
        elif t in ("lexical_declaration", "variable_declaration"):
            _add_bound_functions(child, parent, exported, result)
        elif t == "import_statement":
            _add_import(child, result)
        elif t in _TRANSPARENT:
            _walk(child, parent=parent, exported=exported, result=result)


_TRANSPARENT = {"statement_block", "if_statement", "else_clause", "try_statement", "namespace_export"}


def _name(node: Node) -> str | None:
    name_node = node.child_by_field_name("name")
    return _text(name_node) if name_node is not None else None


def _add_class(node: Node, parent: str | None, exported: bool, result: FileExtraction) -> None:
    name = _name(node)
    if name is None:
        return
    qualname = f"{parent}.{name}" if parent else name
    result.definitions.append(
        Definition(qualname=qualname, kind="Class", line=node.start_point[0] + 1, parent=parent, exported=exported)
    )
    body = node.child_by_field_name("body")
    if body is not None:
        for member in body.named_children:
            if member.type == "method_definition":
                mname = _name(member)
                if mname is not None:
                    result.definitions.append(
                        Definition(
                            qualname=f"{qualname}.{mname}", kind="Function",
                            line=member.start_point[0] + 1, parent=qualname, exported=exported,
                        )
                    )


def _add_function(node: Node, parent: str | None, exported: bool, result: FileExtraction) -> None:
    name = _name(node)
    if name is None:
        return
    qualname = f"{parent}.{name}" if parent else name
    result.definitions.append(
        Definition(qualname=qualname, kind="Function", line=node.start_point[0] + 1, parent=parent, exported=exported)
    )


def _add_bound_functions(node: Node, parent: str | None, exported: bool, result: FileExtraction) -> None:
    # const f = () => {} / const g = function () {}
    for declarator in node.named_children:
        if declarator.type != "variable_declarator":
            continue
        value = declarator.child_by_field_name("value")
        name_node = declarator.child_by_field_name("name")
        if value is None or name_node is None:
            continue
        if value.type in _FUNCTION_VALUE_TYPES:
            name = _text(name_node)
            qualname = f"{parent}.{name}" if parent else name
            result.definitions.append(
                Definition(qualname=qualname, kind="Function", line=declarator.start_point[0] + 1, parent=parent, exported=exported)
            )


def _add_import(node: Node, result: FileExtraction) -> None:
    source_node = node.child_by_field_name("source")
    if source_node is None:
        return
    spec = _text(source_node).strip("\"'`")
    result.imports.append(Import(module=spec, relative=spec.startswith(".")))
