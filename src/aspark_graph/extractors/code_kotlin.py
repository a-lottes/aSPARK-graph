"""tree-sitter Kotlin extractor: File, package, classes/objects, functions, imports.

Deterministic and offline. ``class``, ``data class``, ``object``, ``interface``
and ``enum class`` all fold into the shared ``Class`` node kind (mirrors the
Java/Go precedent). Functions nest under their enclosing class/object; members
of a ``companion object`` nest under the class that owns the companion (no
separate node). An extension function ``fun Recv.name()`` is captured with the
qualname ``Recv.name`` and no parent — never a ``contains`` edge to a node that
doesn't exist. Local (function-body) declarations are not extracted.

Known grammar limit (tree-sitter-kotlin 1.1.0): a class body written on one
line (``class A { val x = 1 }``) parses into an error subtree; members are
still collected from it on a best-effort basis.
"""

from __future__ import annotations

import tree_sitter_kotlin
from tree_sitter import Language, Node, Parser

from .base import Definition, FileExtraction, Import

_LANGUAGE = Language(tree_sitter_kotlin.language())
_PARSER = Parser(_LANGUAGE)

_CLASS_KINDS = {"class_declaration", "object_declaration"}
_BODY_KINDS = {"class_body", "enum_class_body", "ERROR"}


def extract(relpath: str, source: bytes) -> FileExtraction:
    tree = _PARSER.parse(source)
    result = FileExtraction(relpath=relpath, language="kotlin")
    root = tree.root_node
    for child in root.named_children:
        if child.type == "package_header":
            result.package = _qualified(child)
        elif child.type == "import":
            _add_import(child, result)
    _walk(root, None, result)
    return result


def _text(node: Node) -> str:
    return node.text.decode("utf-8", errors="replace")


def _qualified(node: Node) -> str | None:
    q = next((c for c in node.named_children if c.type == "qualified_identifier"), None)
    return _text(q) if q is not None else None


def _add_import(node: Node, result: FileExtraction) -> None:
    module = _qualified(node)
    if not module:
        return
    # `import a.b.*` -> the package `a.b`; `import a.b.C as D` -> `a.b.C`.
    if any(c.type == "*" for c in node.children):
        module = module + ".*"
    result.imports.append(Import(module=module, relative=False))


def _exported(node: Node) -> bool:
    mods = next((c for c in node.named_children if c.type == "modifiers"), None)
    if mods is None:
        return True
    return not any(_text(m) in ("private", "internal") for m in mods.named_children)


def _name(node: Node) -> str | None:
    n = node.child_by_field_name("name")
    if n is None:
        n = next((c for c in node.named_children if c.type == "identifier"), None)
    return _text(n) if n is not None else None


def _walk(node: Node, parent: str | None, result: FileExtraction) -> None:
    for child in node.named_children:
        t = child.type
        if t in _CLASS_KINDS:
            name = _name(child)
            if name is None:
                continue
            qual = f"{parent}.{name}" if parent else name
            result.definitions.append(
                Definition(qualname=qual, kind="Class", line=child.start_point[0] + 1,
                           parent=parent, exported=_exported(child))
            )
            _walk(child, qual, result)
        elif t == "companion_object":
            _walk(child, parent, result)
        elif t == "function_declaration":
            _add_function(child, parent, result)
        elif t in _BODY_KINDS:
            _walk(child, parent, result)


def _add_function(node: Node, parent: str | None, result: FileExtraction) -> None:
    name = _name(node)
    if name is None:
        return
    recv = _receiver_type(node)
    if recv is not None:
        qual, par = f"{recv}.{name}", None
    elif parent:
        qual, par = f"{parent}.{name}", parent
    else:
        qual, par = name, None
    result.definitions.append(
        Definition(qualname=qual, kind="Function", line=node.start_point[0] + 1,
                   parent=par, exported=_exported(node))
    )


def _receiver_type(node: Node) -> str | None:
    """Receiver of an extension function: the type node before the ``.``."""
    seen_dot = False
    for c in node.children:
        if c.type == ".":
            seen_dot = True
            break
    if not seen_dot:
        return None
    for c in node.named_children:
        if c.type in ("user_type", "nullable_type", "parenthesized_type", "function_type"):
            inner = c
            while inner.type == "nullable_type" and inner.named_children:
                inner = inner.named_children[0]
            ident = next((x for x in inner.named_children if x.type == "identifier"), None)
            return _text(ident) if ident is not None else _text(inner)
        if c.type == "function_value_parameters":
            break
    return None
