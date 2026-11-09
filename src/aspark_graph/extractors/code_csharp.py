"""tree-sitter C# extractor: File, types, methods/constructors/local functions, usings.

Deterministic and offline. class/struct/interface/record/enum fold into the
shared ``Class`` node kind (the Java precedent). Namespaces are not nodes: they
are transparent for qualnames, and the *first* namespace declared in a file is
captured as ``package`` so the build can resolve ``using`` directives to repo
files (best-effort). Local functions nest under their enclosing method.
Out of scope: partial classes across files, generics beyond the bare name.
"""

from __future__ import annotations

import tree_sitter_c_sharp
from tree_sitter import Language, Node, Parser

from .base import Definition, FileExtraction, Import

_LANGUAGE = Language(tree_sitter_c_sharp.language())
_PARSER = Parser(_LANGUAGE)

_TYPE_DECLS = {
    "class_declaration", "struct_declaration", "interface_declaration",
    "record_declaration", "enum_declaration",
}
_METHOD_DECLS = {"method_declaration", "constructor_declaration"}
_NAMESPACES = {"namespace_declaration", "file_scoped_namespace_declaration"}


def extract(relpath: str, source: bytes) -> FileExtraction:
    tree = _PARSER.parse(source)
    result = FileExtraction(relpath=relpath, language="csharp")
    _walk(tree.root_node, None, result)
    return result


def _text(node: Node) -> str:
    return node.text.decode("utf-8", errors="replace")


def _name(node: Node) -> str | None:
    n = node.child_by_field_name("name")
    return _text(n) if n is not None else None


def _walk(node: Node, parent: str | None, result: FileExtraction) -> None:
    for child in node.named_children:
        t = child.type
        if t == "using_directive":
            _add_using(child, result)
        elif t in _NAMESPACES:
            name = _name(child)
            if name and result.package is None:
                result.package = name
            body = child.child_by_field_name("body")
            if body is not None:
                _walk(body, parent, result)
        elif t == "declaration_list":
            _walk(child, parent, result)
        elif t in _TYPE_DECLS:
            _add_type(child, parent, result)


def _add_using(node: Node, result: FileExtraction) -> None:
    # `using A.B;` / `using static A.B.T;` / `using X = A.B;` — the namespace or
    # type is the last name child (the alias, if any, comes first).
    names = [c for c in node.named_children if c.type in ("identifier", "qualified_name")]
    if names:
        result.imports.append(Import(module=_text(names[-1]), relative=False))


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
        if member.type in _METHOD_DECLS:
            _add_method(member, qualname, result)
        elif member.type in _TYPE_DECLS:
            _add_type(member, qualname, result)


def _add_method(node: Node, parent: str, result: FileExtraction) -> None:
    name = _name(node)
    if name is None:
        return
    qualname = f"{parent}.{name}"
    result.definitions.append(
        Definition(qualname=qualname, kind="Function", line=node.start_point[0] + 1, parent=parent)
    )
    body = node.child_by_field_name("body")
    if body is not None:
        _add_local_functions(body, qualname, result)


def _add_local_functions(node: Node, parent: str, result: FileExtraction) -> None:
    for child in node.named_children:
        if child.type == "local_function_statement":
            name = _name(child)
            if name is None:
                continue
            qualname = f"{parent}.{name}"
            result.definitions.append(
                Definition(qualname=qualname, kind="Function", line=child.start_point[0] + 1, parent=parent)
            )
            body = child.child_by_field_name("body")
            if body is not None:
                _add_local_functions(body, qualname, result)
        elif child.type not in _TYPE_DECLS:
            _add_local_functions(child, parent, result)
