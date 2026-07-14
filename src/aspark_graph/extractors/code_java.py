"""tree-sitter Java extractor: File, package, classes/interfaces/enums, methods, imports.

Deterministic and offline. The package declaration is captured on the extraction
so the build can resolve fully-qualified imports to repo files (best-effort).
"""

from __future__ import annotations

import tree_sitter_java
from tree_sitter import Language, Node, Parser

from .base import Definition, FileExtraction, Import

_LANGUAGE = Language(tree_sitter_java.language())
_PARSER = Parser(_LANGUAGE)

_TYPE_DECLS = {"class_declaration", "interface_declaration", "enum_declaration", "record_declaration"}


def extract(relpath: str, source: bytes) -> FileExtraction:
    tree = _PARSER.parse(source)
    result = FileExtraction(relpath=relpath, language="java")
    _walk(tree.root_node, parent=None, result=result)
    return result


def _text(node: Node) -> str:
    return node.text.decode("utf-8", errors="replace")


def _name(node: Node) -> str | None:
    name_node = node.child_by_field_name("name")
    return _text(name_node) if name_node is not None else None


def _walk(node: Node, parent: str | None, result: FileExtraction) -> None:
    for child in node.named_children:
        t = child.type
        if t == "package_declaration":
            # `package a.b.c;` — the sole non-punctuation child names the package.
            parts = [_text(c) for c in child.named_children]
            if parts:
                result.package = parts[-1]
        elif t == "import_declaration":
            names = [_text(c) for c in child.named_children if c.type in ("scoped_identifier", "identifier")]
            if names:
                result.imports.append(Import(module=names[-1], relative=False))
        elif t in _TYPE_DECLS:
            _add_type(child, parent, result)


def _add_type(node: Node, parent: str | None, result: FileExtraction) -> None:
    name = _name(node)
    if name is None:
        return
    qualname = f"{parent}.{name}" if parent else name
    result.definitions.append(
        Definition(qualname=qualname, kind="Class", line=node.start_point[0] + 1, parent=parent)
    )
    body = node.child_by_field_name("body")
    if body is None:
        return
    for member in body.named_children:
        if member.type == "method_declaration" or member.type == "constructor_declaration":
            mname = _name(member)
            if mname is not None:
                result.definitions.append(
                    Definition(
                        qualname=f"{qualname}.{mname}", kind="Function",
                        line=member.start_point[0] + 1, parent=qualname,
                    )
                )
        elif member.type in _TYPE_DECLS:
            _add_type(member, qualname, result)  # nested type
