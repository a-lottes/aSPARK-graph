"""tree-sitter Rust extractor: File, structs/enums/traits, functions, impl blocks.

Deterministic and offline. Struct/enum/trait items fold into the shared
``Class`` node kind (mirrors the Java interface/enum/record precedent). A
function inside an ``impl``/``impl Trait for`` block whose target type is
declared in *this same file* nests under that type's ``Class`` (including
when multiple ``impl`` blocks target the same type); one whose target type
lives elsewhere (or is foreign) is still captured, as a top-level
``Function`` — never a ``contains`` edge to a node id that doesn't exist
(plan §1, A2).
"""

from __future__ import annotations

import tree_sitter_rust
from tree_sitter import Language, Node, Parser

from .base import Definition, FileExtraction, Import

_LANGUAGE = Language(tree_sitter_rust.language())
_PARSER = Parser(_LANGUAGE)

_CLASS_KINDS = {"struct_item": "name", "enum_item": "name", "trait_item": "name"}
_UNWRAP_KINDS = {"generic_type", "reference_type"}


def extract(relpath: str, source: bytes) -> FileExtraction:
    tree = _PARSER.parse(source)
    result = FileExtraction(relpath=relpath, language="rust")
    root = tree.root_node

    type_names = _declared_type_names(root)

    for child in root.named_children:
        if child.type == "use_declaration":
            _collect_imports(child, result)
        elif child.type in _CLASS_KINDS:
            _add_class(child, result)
        elif child.type == "function_item":
            _add_function(child, result)
        elif child.type == "impl_item":
            _add_impl(child, type_names, result)

    return result


def _text(node: Node) -> str:
    return node.text.decode("utf-8", errors="replace")


def _is_pub(node: Node) -> bool:
    return any(c.type == "visibility_modifier" for c in node.named_children)


def _declared_type_names(root: Node) -> set[str]:
    names: set[str] = set()
    for child in root.named_children:
        if child.type not in _CLASS_KINDS:
            continue
        name_node = child.child_by_field_name(_CLASS_KINDS[child.type])
        if name_node is not None:
            names.add(_text(name_node))
    return names


def _add_class(node: Node, result: FileExtraction) -> None:
    name_node = node.child_by_field_name(_CLASS_KINDS[node.type])
    if name_node is None:
        return
    name = _text(name_node)
    result.definitions.append(
        Definition(qualname=name, kind="Class", line=node.start_point[0] + 1, parent=None, exported=_is_pub(node))
    )


def _add_function(node: Node, result: FileExtraction, parent: str | None = None) -> None:
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return
    name = _text(name_node)
    qualname = f"{parent}.{name}" if parent else name
    result.definitions.append(
        Definition(qualname=qualname, kind="Function", line=node.start_point[0] + 1, parent=parent, exported=_is_pub(node))
    )


def _add_impl(node: Node, type_names: set[str], result: FileExtraction) -> None:
    target = _unwrap_type_name(node.child_by_field_name("type"))
    body = node.child_by_field_name("body")
    if body is None:
        return
    for member in body.named_children:
        if member.type != "function_item":
            continue
        name_node = member.child_by_field_name("name")
        if name_node is None:
            continue
        name = _text(name_node)
        if target is not None and target in type_names:
            qualname = f"{target}.{name}"
            parent = target
        elif target is not None:
            # Target type not declared in this file (or foreign): still
            # captured, never nested under a Class node that doesn't exist here.
            qualname = f"{target}.{name}"
            parent = None
        else:
            qualname = name
            parent = None
        result.definitions.append(
            Definition(qualname=qualname, kind="Function", line=member.start_point[0] + 1, parent=parent, exported=_is_pub(member))
        )


def _unwrap_type_name(node: Node | None) -> str | None:
    while node is not None and node.type in _UNWRAP_KINDS and node.named_children:
        node = node.named_children[0]
    if node is not None and node.type == "type_identifier":
        return _text(node)
    return None


def _collect_imports(node: Node, result: FileExtraction) -> None:
    child = next((c for c in node.named_children if c.type != "visibility_modifier"), None)
    if child is None:
        return
    for path in _use_paths(child):
        result.imports.append(Import(module=path, relative=_is_relative(path)))


def _is_relative(path: str) -> bool:
    head = path.split("::", 1)[0]
    return head in ("crate", "self", "super")


def _use_paths(node: Node) -> list[str]:
    if node.type in ("identifier", "crate", "self", "super"):
        return [_text(node)]
    if node.type == "scoped_identifier":
        path_node = node.child_by_field_name("path")
        name_node = node.child_by_field_name("name")
        prefixes = _use_paths(path_node) if path_node is not None else [None]
        name = _text(name_node) if name_node is not None else None
        if name is None:
            return prefixes
        return [f"{p}::{name}" if p else name for p in prefixes]
    if node.type == "scoped_use_list":
        path_node = node.child_by_field_name("path")
        list_node = node.child_by_field_name("list")
        prefixes = _use_paths(path_node) if path_node is not None else [None]
        out: list[str] = []
        if list_node is not None:
            for item in list_node.named_children:
                for sub in _use_paths(item):
                    out.extend(f"{p}::{sub}" if p else sub for p in prefixes)
        return out
    if node.type == "use_wildcard":
        return _use_paths(node.named_children[0]) if node.named_children else []
    if node.type == "use_as_clause":
        path_node = node.child_by_field_name("path")
        return _use_paths(path_node) if path_node is not None else []
    return [_text(node)]
