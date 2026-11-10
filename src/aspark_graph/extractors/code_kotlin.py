"""tree-sitter Kotlin extractor: File, package, classes/objects, functions.

Deterministic and offline. ``class`` (incl. data/enum/sealed), ``interface``,
``fun interface`` and ``object`` all fold into the shared ``Class`` node kind.
Companion-object members nest directly under the enclosing class (the
companion itself is not a node). An extension function is a top-level
``Function`` named ``Receiver.name``. Local functions (inside a function body)
are not captured. ``.kt`` and ``.kts`` share this extractor.

Known grammar limit: tree-sitter-kotlin needs a newline or ``;`` between a
class header and members; single-line ``class A { fun f() {} }`` parses with
errors and may yield fewer definitions. Real code is multi-line.
"""

from __future__ import annotations

import tree_sitter_kotlin
from tree_sitter import Language, Node, Parser

from .base import Definition, FileExtraction, Import

_PARSER = Parser(Language(tree_sitter_kotlin.language()))

_CLASS_KINDS = {"class_declaration", "object_declaration"}
_BODY_KINDS = {"class_body", "enum_class_body"}


def extract(relpath: str, source: bytes) -> FileExtraction:
    root = _PARSER.parse(source).root_node
    result = FileExtraction(relpath=relpath, language="kotlin")
    for child in root.named_children:
        if child.type == "package_header":
            qi = next((c for c in child.named_children if c.type == "qualified_identifier"), None)
            if qi is not None:
                result.package = _text(qi)
        elif child.type == "import":
            _add_import(child, result)
        else:
            _visit(child, None, result)
    return result


def _text(node: Node) -> str:
    return node.text.decode("utf-8", errors="replace")


def _name(node: Node) -> str | None:
    n = node.child_by_field_name("name")
    if n is None:
        n = next((c for c in node.named_children if c.type == "identifier"), None)
    return _text(n) if n is not None else None


def _exported(node: Node) -> bool:
    mods = next((c for c in node.named_children if c.type == "modifiers"), None)
    if mods is None:
        return True
    words = _text(mods).split()
    return "private" not in words


def _visit(node: Node, parent: str | None, result: FileExtraction) -> None:
    if node.type in _CLASS_KINDS:
        name = _name(node)
        if name is None:
            return
        qual = f"{parent}.{name}" if parent else name
        result.definitions.append(
            Definition(qualname=qual, kind="Class", line=node.start_point[0] + 1, parent=parent, exported=_exported(node))
        )
        _visit_body(node, qual, result)
    elif node.type == "function_declaration":
        name = _name(node)
        if name is None:
            return
        if parent is None:
            recv = _receiver(node)
            qual = f"{recv}.{name}" if recv else name
        else:
            qual = f"{parent}.{name}"
        result.definitions.append(
            Definition(qualname=qual, kind="Function", line=node.start_point[0] + 1, parent=parent, exported=_exported(node))
        )


def _visit_body(node: Node, owner: str, result: FileExtraction) -> None:
    for body in node.named_children:
        if body.type not in _BODY_KINDS:
            continue
        for member in body.named_children:
            if member.type == "companion_object":
                # Members live under the enclosing class, not a Companion node.
                for cb in member.named_children:
                    if cb.type in _BODY_KINDS:
                        for m in cb.named_children:
                            _visit(m, owner, result)
            else:
                _visit(member, owner, result)


def _receiver(fn: Node) -> str | None:
    """Receiver type's simple name for ``fun Recv.name()``, else None."""
    name_node = fn.child_by_field_name("name")
    if name_node is None:
        return None
    for c in fn.named_children:
        if c.start_byte >= name_node.start_byte:
            break
        if c.type in ("user_type", "nullable_type", "parenthesized_type"):
            ident = c
            while ident is not None and ident.type != "identifier":
                ident = next((x for x in ident.named_children if x.type in ("identifier", "user_type", "nullable_type", "parenthesized_type")), None)
            return _text(ident) if ident is not None else None
    return None


def _add_import(node: Node, result: FileExtraction) -> None:
    qi = next((c for c in node.named_children if c.type == "qualified_identifier"), None)
    if qi is None:
        return
    module = _text(qi)
    if any(not c.is_named and c.type == "*" for c in node.children):
        module += ".*"
    result.imports.append(Import(module=module, relative=False))
