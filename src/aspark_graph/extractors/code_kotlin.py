"""tree-sitter Kotlin extractor: File, package, classes/objects, functions.

Deterministic and offline. Class, data class, object, interface and enum class
all fold into the shared ``Class`` node kind (mirrors the Java/Go precedent).
A ``companion object`` is *not* a node of its own: its members nest under the
enclosing class (``Widget.make``). An extension function is captured as
``Receiver.name`` (top-level, like a Go receiver method on a foreign type).
Function bodies are not descended into, so local functions are not nodes.

The grammar can wrap a class body in an ``ERROR`` node for some single-line
shapes (``class A { fun m() {} }``); the walk looks through ``ERROR`` nodes so
those declarations are still found. Annotation processing and Kotlin
Multiplatform ``expect``/``actual`` pairing are out of scope.
"""

from __future__ import annotations

import tree_sitter_kotlin
from tree_sitter import Language, Node, Parser

from .base import Definition, FileExtraction, Import

_LANGUAGE = Language(tree_sitter_kotlin.language())
_PARSER = Parser(_LANGUAGE)

_CLASS_NODES = {"class_declaration", "object_declaration"}
_BODY_NODES = {"class_body", "enum_class_body"}


def extract(relpath: str, source: bytes) -> FileExtraction:
    tree = _PARSER.parse(source)
    result = FileExtraction(relpath=relpath, language="kotlin")
    root = tree.root_node
    _walk(root, None, result, top=True)
    return result


def _text(node: Node) -> str:
    return node.text.decode("utf-8", errors="replace")


def _walk(node: Node, parent: str | None, result: FileExtraction, top: bool = False) -> None:
    for child in node.named_children:
        t = child.type
        if t == "ERROR":
            _walk(child, parent, result)
        elif t == "package_header":
            q = next((c for c in child.named_children if c.type == "qualified_identifier"), None)
            if q is not None:
                result.package = _text(q)
        elif t == "import":
            _add_import(child, result)
        elif t in _CLASS_NODES:
            _add_class(child, parent, result)
        elif t == "companion_object":
            for body in child.named_children:
                if body.type in _BODY_NODES:
                    _walk(body, parent, result)
        elif t == "function_declaration":
            _add_function(child, parent, result)
        elif t in _BODY_NODES and not top:
            _walk(child, parent, result)


def _name(node: Node) -> str | None:
    n = node.child_by_field_name("name")
    if n is None:
        n = next((c for c in node.named_children if c.type == "identifier"), None)
    return _text(n) if n is not None else None


def _exported(node: Node) -> bool:
    for c in node.named_children:
        if c.type == "modifiers":
            for m in c.named_children:
                if m.type == "visibility_modifier" and _text(m) in ("private",):
                    return False
    return True


def _add_class(node: Node, parent: str | None, result: FileExtraction) -> None:
    name = _name(node)
    if not name:
        return
    qual = f"{parent}.{name}" if parent else name
    result.definitions.append(
        Definition(qualname=qual, kind="Class", line=node.start_point[0] + 1, parent=parent, exported=_exported(node))
    )
    for body in node.named_children:
        if body.type in _BODY_NODES:
            _walk(body, qual, result)


def _receiver(node: Node, name_node: Node) -> str | None:
    for c in node.named_children:
        if c.start_byte >= name_node.start_byte:
            break
        if c.type.endswith("_type") and c.type != "type_parameters":
            text = _text(c)
            for ch in ("<", "?", "("):
                text = text.split(ch)[0]
            return text.strip() or None
    return None


def _add_function(node: Node, parent: str | None, result: FileExtraction) -> None:
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return
    name = _text(name_node)
    recv = _receiver(node, name_node)
    local = f"{recv}.{name}" if recv else name
    qual = f"{parent}.{local}" if parent else local
    result.definitions.append(
        Definition(qualname=qual, kind="Function", line=node.start_point[0] + 1, parent=parent, exported=_exported(node))
    )


def _add_import(node: Node, result: FileExtraction) -> None:
    q = next((c for c in node.named_children if c.type == "qualified_identifier"), None)
    if q is None:
        return
    module = _text(q)
    if _text(node).split("//")[0].strip().rstrip(";").rstrip().endswith("*"):
        module += ".*"
    result.imports.append(Import(module=module, relative=False))
