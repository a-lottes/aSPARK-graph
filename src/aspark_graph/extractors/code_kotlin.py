"""tree-sitter Kotlin extractor: File, package, classes/objects, functions, imports.

Deterministic and offline. Classes, data/sealed/enum classes, interfaces and
objects all fold into the shared ``Class`` node kind (the Java/Go precedent).
A ``companion object``'s members nest directly under the enclosing class
(``Foo.make``) — the companion itself is not a node. An extension function is a
top-level ``Function`` qualified by its receiver type (``String.ext``), like a
Go receiver method. Local functions and object literals inside bodies are not
descended into.

Known limit of the pinned grammar: a class body opened and closed on one line
(``class A { fun f() {} }``) parses with errors; bodies opened on their own
line, the normal layout, are fine.
"""

from __future__ import annotations

import tree_sitter_kotlin
from tree_sitter import Language, Node, Parser

from .base import Definition, FileExtraction, Import

_LANGUAGE = Language(tree_sitter_kotlin.language())
_PARSER = Parser(_LANGUAGE)

_TYPE_DECLS = {"class_declaration", "object_declaration"}
_BODIES = {"class_body", "enum_class_body"}


def extract(relpath: str, source: bytes) -> FileExtraction:
    tree = _PARSER.parse(source)
    result = FileExtraction(relpath=relpath, language="kotlin")
    root = tree.root_node
    for child in root.named_children:
        if child.type == "package_header":
            ident = _first(child, "qualified_identifier") or _first(child, "identifier")
            if ident is not None:
                result.package = _text(ident)
        elif child.type == "import":
            _add_import(child, result)
    _walk(root, parent=None, result=result)
    return result


def _text(node: Node) -> str:
    return node.text.decode("utf-8", errors="replace")


def _first(node: Node, type_: str) -> Node | None:
    return next((c for c in node.named_children if c.type == type_), None)


def _exported(node: Node) -> bool:
    mods = _first(node, "modifiers")
    if mods is None:
        return True
    return not any(c.type == "visibility_modifier" and _text(c) in ("private",) for c in mods.named_children)


def _add_import(node: Node, result: FileExtraction) -> None:
    ident = _first(node, "qualified_identifier")
    if ident is None:
        return
    module = _text(ident)
    if _text(node).rstrip().endswith("*"):
        module += ".*"  # star import: kept raw, the build does not resolve it
    result.imports.append(Import(module=module, relative=False))


def _walk(node: Node, parent: str | None, result: FileExtraction) -> None:
    for child in node.named_children:
        t = child.type
        if t in _TYPE_DECLS:
            _add_type(child, parent, result)
        elif t == "function_declaration":
            _add_function(child, parent, result)
        elif t == "companion_object":
            _walk_bodies(child, parent, result)  # members belong to the enclosing class


def _walk_bodies(node: Node, parent: str | None, result: FileExtraction) -> None:
    for body in node.named_children:
        if body.type in _BODIES:
            _walk(body, parent, result)


def _add_type(node: Node, parent: str | None, result: FileExtraction) -> None:
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return
    name = _text(name_node)
    qualname = f"{parent}.{name}" if parent else name
    result.definitions.append(
        Definition(qualname=qualname, kind="Class", line=node.start_point[0] + 1, parent=parent,
                   exported=_exported(node))
    )
    _walk_bodies(node, qualname, result)


def _receiver(node: Node, name_node: Node) -> str | None:
    """Base type name of an extension function's receiver, if any."""
    for child in node.named_children:
        if child.start_byte >= name_node.start_byte:
            break
        if child.type in ("user_type", "nullable_type", "parenthesized_type"):
            text = _text(child).rstrip("?")
            return text.split("<", 1)[0].strip() or None
    return None


def _add_function(node: Node, parent: str | None, result: FileExtraction) -> None:
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return
    name = _text(name_node)
    receiver = _receiver(node, name_node) if parent is None else None
    if receiver:
        qualname = f"{receiver}.{name}"
    else:
        qualname = f"{parent}.{name}" if parent else name
    result.definitions.append(
        Definition(qualname=qualname, kind="Function", line=node.start_point[0] + 1, parent=parent,
                   exported=_exported(node))
    )
