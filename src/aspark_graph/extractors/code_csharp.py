"""tree-sitter C# extractor: File, namespace, types, methods, constructors, local functions.

Deterministic and offline. class/struct/interface/record/enum all fold into the
shared ``Class`` node kind (mirrors the Java and Go precedent). Methods,
constructors and local functions are ``Function`` nodes; a local function nests
under its enclosing method (``Method.Local``). The first ``namespace`` in the
file is recorded as ``package`` (block-scoped or file-scoped). Partial classes
across files and generics beyond the bare name are out of scope: a generic type
is named without its type parameters, and each partial declaration is simply its
own ``Class`` node in its own file.

``exported`` defaults (best-effort, from modifiers): ``public``/``internal``/
``protected`` -> True; ``private`` and ``private protected`` -> False. With no
modifier: a top-level type is True (internal), an interface member is True, and
a method, nested type or local function is False (private by default).
"""

from __future__ import annotations

import tree_sitter_c_sharp
from tree_sitter import Language, Node, Parser

from .base import Definition, FileExtraction, Import

_LANGUAGE = Language(tree_sitter_c_sharp.language())
_PARSER = Parser(_LANGUAGE)

_TYPE_KINDS = {
    "class_declaration",
    "struct_declaration",
    "interface_declaration",
    "record_declaration",
    "enum_declaration",
}
_FUNCTION_KINDS = {"method_declaration", "constructor_declaration", "local_function_statement"}


def extract(relpath: str, source: bytes) -> FileExtraction:
    tree = _PARSER.parse(source)
    result = FileExtraction(relpath=relpath, language="csharp")
    _walk_container(tree.root_node, None, result, top_level=True)
    return result


def _text(node: Node) -> str:
    return node.text.decode("utf-8", errors="replace")


def _walk_container(node: Node, parent: str | None, result: FileExtraction, top_level: bool = False) -> None:
    """Visit the members of a compilation unit, namespace or type body."""
    in_interface = node.parent is not None and node.parent.type == "interface_declaration"
    for child in node.named_children:
        t = child.type
        if t == "using_directive":
            _add_using(child, result)
        elif t in ("namespace_declaration", "file_scoped_namespace_declaration"):
            name_node = child.child_by_field_name("name")
            if name_node is not None and result.package is None:
                result.package = _text(name_node)
            body = child.child_by_field_name("body")
            # File-scoped namespaces hold their members as siblings of the
            # declaration, so they are already visited by this loop.
            if body is not None:
                _walk_container(body, parent, result)
        elif t in _TYPE_KINDS:
            _add_type(child, parent, result, top_level)
        elif t in ("method_declaration", "constructor_declaration") and parent is not None:
            _add_function(child, parent, result, in_interface)
        elif t == "global_statement" and top_level:
            for inner in child.named_children:
                if inner.type == "local_function_statement":
                    _add_function(inner, None, result, True)


def _add_using(node: Node, result: FileExtraction) -> None:
    # `using X;`, `using static X.Y;`, `using A = X.Y;`, `global using X;`
    # all carry the imported name as the last named child that is a name node.
    target = None
    for child in node.named_children:
        if child.type in ("identifier", "qualified_name", "alias_qualified_name"):
            target = child
    if target is None:
        return
    result.imports.append(Import(module=_text(target), relative=False))


def _modifiers(node: Node) -> set[str]:
    return {_text(c) for c in node.named_children if c.type == "modifier"}


def _is_exported(node: Node, default: bool) -> bool:
    mods = _modifiers(node)
    if "private" in mods:  # also `private protected`: narrowest access wins
        return False
    if mods & {"public", "internal", "protected"}:
        return True
    return default


def _add_type(node: Node, parent: str | None, result: FileExtraction, top_level_ns: bool) -> None:
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return
    name = _text(name_node)
    qualname = f"{parent}.{name}" if parent else name
    result.definitions.append(
        Definition(
            qualname=qualname,
            kind="Class",
            line=node.start_point[0] + 1,
            parent=parent,
            exported=_is_exported(node, default=parent is None),
        )
    )
    body = node.child_by_field_name("body")
    if body is not None:
        _walk_container(body, qualname, result)


def _add_function(node: Node, parent: str | None, result: FileExtraction, default_exported: bool) -> None:
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return
    name = _text(name_node)
    qualname = f"{parent}.{name}" if parent else name
    is_local = node.type == "local_function_statement"
    result.definitions.append(
        Definition(
            qualname=qualname,
            kind="Function",
            line=node.start_point[0] + 1,
            parent=parent,
            exported=False if is_local and parent else _is_exported(node, default=default_exported),
        )
    )
    body = node.child_by_field_name("body")
    if body is not None:
        _add_local_functions(body, qualname, result)


def _add_local_functions(node: Node, parent: str, result: FileExtraction) -> None:
    for child in node.named_children:
        if child.type == "local_function_statement":
            _add_function(child, parent, result, False)
        elif child.type not in _TYPE_KINDS and child.type not in _FUNCTION_KINDS:
            _add_local_functions(child, parent, result)
