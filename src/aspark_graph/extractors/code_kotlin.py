"""tree-sitter Kotlin extractor: File, package, classes/objects, functions, imports.

Deterministic and offline. ``class``, ``data class``, ``object``, ``interface``
and ``enum class`` all fold into the shared ``Class`` node kind (mirrors the
Java interface/enum/record and Go struct precedent). A ``companion object``
becomes a ``Class`` named ``<Outer>.Companion`` (or its explicit name) so its
members nest under it. Extension functions are ``Function`` nodes qualified by
their receiver type (``String.ext``); a top-level one is never nested under a
class node that may not exist. Functions local to a function body are ignored.

Known limits (out of scope per issue #29): Kotlin Multiplatform
``expect``/``actual`` pairing, annotation processing. Wildcard imports
(``a.b.*``) and ``typealias`` are not resolved/recorded.
"""

from __future__ import annotations

import tree_sitter_kotlin
from tree_sitter import Language, Node, Parser

from .base import Definition, FileExtraction, Import

_LANGUAGE = Language(tree_sitter_kotlin.language())
_PARSER = Parser(_LANGUAGE)

_CLASS_BODIES = {"class_body", "enum_class_body"}


def extract(relpath: str, source: bytes) -> FileExtraction:
    tree = _PARSER.parse(source)
    result = FileExtraction(relpath=relpath, language="kotlin")
    root = tree.root_node
    for child in root.named_children:
        if child.type == "package_header":
            ident = _first(child, "qualified_identifier", "identifier")
            if ident is not None:
                result.package = _text(ident)
        elif child.type == "import":
            _add_import(child, result)
    _walk(root, None, result)
    return result


def _text(node: Node) -> str:
    return node.text.decode("utf-8", errors="replace")


def _first(node: Node, *types: str) -> Node | None:
    return next((c for c in node.named_children if c.type in types), None)


def _private(node: Node) -> bool:
    mods = _first(node, "modifiers")
    if mods is None:
        return False
    return any(m.type == "visibility_modifier" and _text(m) == "private" for m in mods.named_children)


def _walk(container: Node, parent: str | None, result: FileExtraction) -> None:
    """Collect declarations directly inside a file or a class body."""
    for node in container.named_children:
        if node.type in ("class_declaration", "object_declaration"):
            name_node = _first(node, "identifier")
            if name_node is None:
                continue
            _add_class(node, _text(name_node), parent, result)
        elif node.type == "companion_object":
            name_node = _first(node, "identifier")
            name = _text(name_node) if name_node is not None else "Companion"
            _add_class(node, name, parent, result)
        elif node.type == "function_declaration":
            _add_function(node, parent, result)


def _qual(parent: str | None, name: str) -> str:
    return f"{parent}.{name}" if parent else name


def _add_class(node: Node, name: str, parent: str | None, result: FileExtraction) -> None:
    qualname = _qual(parent, name)
    result.definitions.append(
        Definition(qualname=qualname, kind="Class", line=node.start_point[0] + 1, parent=parent, exported=not _private(node))
    )
    body = _first(node, *_CLASS_BODIES)
    if body is not None:
        _walk(body, qualname, result)


def _add_function(node: Node, parent: str | None, result: FileExtraction) -> None:
    name_node = None
    receiver: str | None = None
    # `fun Recv.name(...)`: children before the name are the receiver type.
    idents = [c for c in node.children if c.type == "identifier"]
    if not idents:
        return
    name_node = idents[0]
    for c in node.children:
        if c.type == "identifier":
            break
        if c.type in ("user_type", "nullable_type", "parenthesized_type", "function_type"):
            receiver = _receiver_name(c)
    name = _text(name_node)
    if receiver is not None and parent is None:
        qualname = f"{receiver}.{name}"
    elif receiver is not None:
        qualname = f"{parent}.{receiver}.{name}"
    else:
        qualname = _qual(parent, name)
    result.definitions.append(
        Definition(qualname=qualname, kind="Function", line=node.start_point[0] + 1, parent=parent, exported=not _private(node))
    )


def _receiver_name(node: Node) -> str:
    text = _text(node).strip()
    # drop generic arguments and nullability: `List<T>?` -> `List`
    for cut in ("<", "?"):
        text = text.split(cut, 1)[0]
    return text.strip()


def _add_import(node: Node, result: FileExtraction) -> None:
    ident = _first(node, "qualified_identifier")
    if ident is None:
        return
    # `import a.b.*` carries a trailing wildcard token: not resolvable to one file.
    if any(c.type == "*" for c in node.children):
        return
    # an `as Alias` rename is a sibling identifier, not part of the path.
    result.imports.append(Import(module=_text(ident), relative=False))
