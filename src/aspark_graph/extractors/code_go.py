"""tree-sitter Go extractor: File, package, structs/interfaces, functions, methods.

Deterministic and offline. Structs and interfaces fold into the shared ``Class``
node kind (mirrors the Java interface/enum/record precedent). A receiver
method whose type is declared in *this same file* nests under that type's
``Class``; a receiver method whose type lives elsewhere (or isn't declared in
the repo at all) is still captured, as a top-level ``Function`` — never a
``contains`` edge to a node id that doesn't exist (plan §1, A2).
"""

from __future__ import annotations

import tree_sitter_go
from tree_sitter import Language, Node, Parser

from .base import Definition, FileExtraction, Import

_LANGUAGE = Language(tree_sitter_go.language())
_PARSER = Parser(_LANGUAGE)

_TYPE_KINDS = {"struct_type", "interface_type"}
_UNWRAP_KINDS = {"pointer_type", "generic_type"}


def extract(relpath: str, source: bytes) -> FileExtraction:
    tree = _PARSER.parse(source)
    result = FileExtraction(relpath=relpath, language="go")
    root = tree.root_node

    type_names = _declared_type_names(root)

    for child in root.named_children:
        if child.type == "package_clause" and child.named_children:
            result.package = _text(child.named_children[0])
        elif child.type == "import_declaration":
            _collect_imports(child, result)
        elif child.type == "type_declaration":
            _add_types(child, type_names, result)
        elif child.type == "function_declaration":
            _add_function(child, result)
        elif child.type == "method_declaration":
            _add_method(child, type_names, result)

    return result


def _text(node: Node) -> str:
    return node.text.decode("utf-8", errors="replace")


def _exported(name: str) -> bool:
    return bool(name) and name[:1].isupper()


def _declared_type_names(root: Node) -> set[str]:
    names: set[str] = set()
    for child in root.named_children:
        if child.type != "type_declaration":
            continue
        for spec in child.named_children:
            if spec.type != "type_spec":
                continue
            name_node = spec.child_by_field_name("name")
            type_node = spec.child_by_field_name("type")
            if name_node is not None and type_node is not None and type_node.type in _TYPE_KINDS:
                names.add(_text(name_node))
    return names


def _add_types(decl_node: Node, type_names: set[str], result: FileExtraction) -> None:
    for spec in decl_node.named_children:
        if spec.type != "type_spec":
            continue
        name_node = spec.child_by_field_name("name")
        type_node = spec.child_by_field_name("type")
        if name_node is None or type_node is None or type_node.type not in _TYPE_KINDS:
            continue
        name = _text(name_node)
        result.definitions.append(
            Definition(qualname=name, kind="Class", line=spec.start_point[0] + 1, parent=None, exported=_exported(name))
        )


def _add_function(node: Node, result: FileExtraction) -> None:
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return
    name = _text(name_node)
    result.definitions.append(
        Definition(qualname=name, kind="Function", line=node.start_point[0] + 1, parent=None, exported=_exported(name))
    )


def _add_method(node: Node, type_names: set[str], result: FileExtraction) -> None:
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return
    name = _text(name_node)
    recv_type = _receiver_type_name(node)
    if recv_type is not None and recv_type in type_names:
        qualname = f"{recv_type}.{name}"
        parent = recv_type
    elif recv_type is not None:
        # Receiver type not declared in this file (idiomatic Go splits a
        # struct's methods across files): still captured, never nested.
        qualname = f"{recv_type}.{name}"
        parent = None
    else:
        qualname = name
        parent = None
    result.definitions.append(
        Definition(qualname=qualname, kind="Function", line=node.start_point[0] + 1, parent=parent, exported=_exported(name))
    )


def _receiver_type_name(method_node: Node) -> str | None:
    receiver = method_node.child_by_field_name("receiver")
    if receiver is None or not receiver.named_children:
        return None
    param = receiver.named_children[0]
    type_node = param.child_by_field_name("type")
    return _unwrap_type_name(type_node)


def _unwrap_type_name(node: Node | None) -> str | None:
    while node is not None and node.type in _UNWRAP_KINDS and node.named_children:
        node = node.named_children[0]
    if node is not None and node.type == "type_identifier":
        return _text(node)
    return None


def _collect_imports(decl_node: Node, result: FileExtraction) -> None:
    specs: list[Node] = []
    for child in decl_node.named_children:
        if child.type == "import_spec":
            specs.append(child)
        elif child.type == "import_spec_list":
            specs.extend(c for c in child.named_children if c.type == "import_spec")
    for spec in specs:
        path = _import_path(spec)
        if path:
            result.imports.append(Import(module=path, relative=False))


def _import_path(spec_node: Node) -> str | None:
    for child in spec_node.named_children:
        if child.type in ("interpreted_string_literal", "raw_string_literal"):
            content = next((c for c in child.named_children if c.type.endswith("_content")), None)
            if content is not None:
                return _text(content)
            return _text(child).strip('"`')
    return None
