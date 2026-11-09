"""tree-sitter C# extractor: File, namespace, types, methods/constructors, using directives.

Deterministic and offline. class/struct/interface/record/enum fold into the shared
``Class`` node kind (mirrors the Java and Go precedent). Methods, constructors and
local functions are ``Function`` nodes; a local function nests under its enclosing
method. The first namespace declared in a file is captured as ``package`` so the
build can resolve ``using`` directives to repo files (best-effort, like Go/Rust).

Out of scope: partial classes across files (each file's declaration stands alone),
generics beyond the bare name (``Box<T>`` is ``Box``), Razor files.
"""

from __future__ import annotations

import tree_sitter_c_sharp
from tree_sitter import Language, Node, Parser

from .base import Definition, FileExtraction, Import

_LANGUAGE = Language(tree_sitter_c_sharp.language())
_PARSER = Parser(_LANGUAGE)

_TYPE_DECLS = {
    "class_declaration", "struct_declaration", "interface_declaration",
    "record_declaration", "record_struct_declaration", "enum_declaration",
}
_MEMBER_FUNCS = {"method_declaration", "constructor_declaration"}
_NAMESPACES = {"namespace_declaration", "file_scoped_namespace_declaration"}
_NAME_TYPES = ("identifier", "qualified_name", "alias_qualified_name")


def extract(relpath: str, source: bytes) -> FileExtraction:
    tree = _PARSER.parse(source)
    result = FileExtraction(relpath=relpath, language="csharp")
    _walk(tree.root_node, namespace=None, parent=None, result=result)
    return result


def _text(node: Node) -> str:
    return node.text.decode("utf-8", errors="replace")


def _name(node: Node) -> str | None:
    name_node = node.child_by_field_name("name")
    return _text(name_node) if name_node is not None else None


def _walk(node: Node, namespace: str | None, parent: str | None, result: FileExtraction) -> None:
    for child in node.named_children:
        t = child.type
        if t == "using_directive":
            _add_using(child, result)
        elif t in _NAMESPACES:
            name = _name(child)
            full = f"{namespace}.{name}" if namespace and name else (name or namespace)
            if full and result.package is None:
                result.package = full
            # Block form nests its members in a declaration_list; the file-scoped
            # form (`namespace A;`) has them as siblings in the compilation unit,
            # which the enclosing walk reaches — set the namespace for those too.
            _walk(child, full, parent, result)
            if t == "file_scoped_namespace_declaration":
                namespace = full
        elif t in _TYPE_DECLS:
            _add_type(child, parent, result)
        elif t == "declaration_list":
            _walk(child, namespace, parent, result)


def _add_using(node: Node, result: FileExtraction) -> None:
    # `using A.B;`, `using static A.B.T;`, `global using A.B;`, `using X = A.B.T;`
    # The imported name is the last name-like child (an alias's identifier comes first).
    names = [c for c in node.named_children if c.type in _NAME_TYPES]
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
    members = body.named_children if body is not None else node.named_children
    for member in members:
        if member.type in _MEMBER_FUNCS:
            _add_function(member, qualname, result)
        elif member.type in _TYPE_DECLS:
            _add_type(member, qualname, result)


def _add_function(node: Node, parent: str, result: FileExtraction) -> None:
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
            _add_function(child, parent, result)
        else:
            _add_local_functions(child, parent, result)
