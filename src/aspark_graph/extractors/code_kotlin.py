"""tree-sitter Kotlin extractor: File, package, classes/objects, functions, imports.

Deterministic and offline. Classes, data/sealed/enum classes, interfaces and
objects fold into the shared ``Class`` node kind (mirrors the Java/Go
precedent). A ``companion object`` becomes a ``Class`` named ``Companion`` (or
its declared name) nested under its host, so its members are
``Host.Companion.member``. An extension function is named after its receiver
type (``String.shout``) and stays a top-level ``Function`` — never a
``contains`` edge to a node that does not exist. Kotlin Multiplatform
``expect``/``actual`` pairing and annotation processing are out of scope.

The grammar is error-tolerant: declarations that land inside an ``ERROR`` node
are still collected, so one odd construct does not hide its neighbours.
"""

from __future__ import annotations

import tree_sitter_kotlin
from tree_sitter import Language, Node, Parser

from .base import Definition, FileExtraction, Import

_LANGUAGE = Language(tree_sitter_kotlin.language())
_PARSER = Parser(_LANGUAGE)

_CLASS_LIKE = {"class_declaration", "object_declaration"}
_PRIVATE = b"private"


def extract(relpath: str, source: bytes) -> FileExtraction:
    tree = _PARSER.parse(source)
    result = FileExtraction(relpath=relpath, language="kotlin")
    _walk(tree.root_node, parent=None, result=result)
    return result


def _text(node: Node) -> str:
    return node.text.decode("utf-8", errors="replace")


def _name(node: Node) -> str | None:
    n = node.child_by_field_name("name")
    return _text(n) if n is not None else None


def _exported(node: Node) -> bool:
    for c in node.named_children:
        if c.type == "modifiers":
            return b"private" not in c.text.split()
    return True


def _walk(node: Node, parent: str | None, result: FileExtraction) -> None:
    for child in node.named_children:
        t = child.type
        if t == "package_header":
            q = next((c for c in child.named_children if c.type == "qualified_identifier"), None)
            if q is not None:
                result.package = _text(q)
        elif t == "import":
            _add_import(child, result)
        elif t in _CLASS_LIKE:
            _add_class(child, _name(child), parent, result)
        elif t == "companion_object":
            _add_class(child, _name(child) or "Companion", parent, result)
        elif t == "function_declaration":
            _add_function(child, parent, result)
        elif t in ("class_body", "enum_class_body", "ERROR", "script"):
            _walk(child, parent, result)  # transparent containers
        elif t == "statements" and parent is None:
            _walk(child, parent, result)  # .kts scripts


def _add_class(node: Node, name: str | None, parent: str | None, result: FileExtraction) -> None:
    if name is None:
        return
    qualname = f"{parent}.{name}" if parent else name
    result.definitions.append(
        Definition(qualname=qualname, kind="Class", line=node.start_point[0] + 1,
                   parent=parent, exported=_exported(node))
    )
    _walk(node, qualname, result)


def _add_function(node: Node, parent: str | None, result: FileExtraction) -> None:
    name = _name(node)
    if name is None:
        return
    receiver = _receiver_name(node)
    if receiver and parent is None:
        qualname, owner = f"{receiver}.{name}", None
    elif receiver:
        # Member extension (`fun String.x()` inside a class): keep under the host.
        qualname, owner = f"{parent}.{receiver}.{name}", parent
    else:
        qualname, owner = (f"{parent}.{name}" if parent else name), parent
    result.definitions.append(
        Definition(qualname=qualname, kind="Function", line=node.start_point[0] + 1,
                   parent=owner, exported=_exported(node))
    )


def _receiver_name(node: Node) -> str | None:
    """Receiver type of an extension function: the type node before the name."""
    for c in node.named_children:
        if c == node.child_by_field_name("name"):
            return None
        if c.type == "user_type":
            ids = [_text(i) for i in c.named_children if i.type == "identifier"]
            return ".".join(ids) or None
        if c.type == "nullable_type":
            inner = next((i for i in c.named_children if i.type == "user_type"), None)
            if inner is not None:
                return ".".join(_text(i) for i in inner.named_children if i.type == "identifier") or None
    return None


def _add_import(node: Node, result: FileExtraction) -> None:
    q = next((c for c in node.named_children if c.type == "qualified_identifier"), None)
    if q is None:
        return
    module = _text(q)
    if any(not c.is_named and c.type == "*" for c in node.children) or b".*" in node.text.replace(b" ", b""):
        module += ".*"
    result.imports.append(Import(module=module, relative=False))
