"""tree-sitter Kotlin extractor: File, package, classes/objects, functions, imports.

Deterministic and offline. ``class`` (incl. data/enum/sealed), ``interface`` and
``object`` fold into the shared ``Class`` node kind (mirrors the Java/Go
precedent). Extension functions are top-level ``Function`` nodes named by their
bare function name; members of a ``companion object`` nest directly under the
enclosing class (``A.make``), since the companion itself is not a node.
Wildcard imports (``a.b.*``) are dropped: they name a package, not a file.
Kotlin Multiplatform ``expect``/``actual`` pairing is out of scope.
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
        t = child.type
        if t == "package_header":
            qi = _first(child, "qualified_identifier") or _first(child, "identifier")
            if qi is not None:
                result.package = _text(qi)
        elif t == "import":
            _add_import(child, result)
        elif t in _TYPE_DECLS:
            _add_type(child, None, result)
        elif t == "function_declaration":
            _add_function(child, None, result)
    return result


def _text(node: Node) -> str:
    return node.text.decode("utf-8", errors="replace")


def _first(node: Node, type_: str) -> Node | None:
    return next((c for c in node.named_children if c.type == type_), None)


def _name(node: Node) -> str | None:
    # No field names in this grammar: the declared name is the first direct
    # ``identifier`` child (an extension receiver is a ``user_type``, not one).
    n = _first(node, "identifier")
    return _text(n) if n is not None else None


def _add_import(node: Node, result: FileExtraction) -> None:
    if any(not c.is_named and c.type == "*" for c in node.children) or "*" in _text(node).split("as")[0]:
        return  # wildcard: names a package, not a file
    qi = _first(node, "qualified_identifier")
    if qi is not None:
        result.imports.append(Import(module=_text(qi), relative=False))


def _add_type(node: Node, parent: str | None, result: FileExtraction) -> None:
    name = _name(node)
    if name is None:
        return
    qualname = f"{parent}.{name}" if parent else name
    result.definitions.append(Definition(qualname=qualname, kind="Class", line=node.start_point[0] + 1, parent=parent))
    body = next((c for c in node.named_children if c.type in _BODIES), None)
    if body is not None:
        _add_members(body, qualname, result)


def _add_members(body: Node, owner: str, result: FileExtraction) -> None:
    for member in body.named_children:
        if member.type == "function_declaration":
            _add_function(member, owner, result)
        elif member.type in _TYPE_DECLS:
            _add_type(member, owner, result)
        elif member.type == "companion_object":
            inner = _first(member, "class_body")
            if inner is not None:
                _add_members(inner, owner, result)


def _add_function(node: Node, owner: str | None, result: FileExtraction) -> None:
    name = _name(node)
    if name is None:
        return
    qualname = f"{owner}.{name}" if owner else name
    result.definitions.append(Definition(qualname=qualname, kind="Function", line=node.start_point[0] + 1, parent=owner))
