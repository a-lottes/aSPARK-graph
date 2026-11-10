"""tree-sitter Kotlin extractor: File, package, classes/objects/interfaces/enums, functions, imports.

Deterministic and offline. ``.kt`` and ``.kts`` share this extractor. Like Java, the
package header is captured on the extraction so the build can resolve fully-qualified
imports to repo files (best-effort). Out of scope: KMP ``expect``/``actual`` pairing,
annotation processing.
"""

from __future__ import annotations

import tree_sitter_kotlin
from tree_sitter import Language, Node, Parser

from .base import Definition, FileExtraction, Import

_LANGUAGE = Language(tree_sitter_kotlin.language())
_PARSER = Parser(_LANGUAGE)

# class, data class, interface, enum class share class_declaration; objects and
# companion objects have their own node types.
_TYPE_DECLS = {"class_declaration", "object_declaration"}
_BODIES = {"class_body", "enum_class_body"}


def extract(relpath: str, source: bytes) -> FileExtraction:
    tree = _PARSER.parse(source)
    result = FileExtraction(relpath=relpath, language="kotlin")
    root = tree.root_node
    for child in root.named_children:
        t = child.type
        if t == "package_header":
            qi = _first(child, "qualified_identifier", "identifier")
            if qi is not None:
                result.package = _text(qi)
        elif t == "import":
            _add_import(child, result)
    _walk(root, parent=None, result=result)
    return result


def _text(node: Node) -> str:
    return node.text.decode("utf-8", errors="replace")


def _first(node: Node, *types: str) -> Node | None:
    for c in node.named_children:
        if c.type in types:
            return c
    return None


def _add_import(node: Node, result: FileExtraction) -> None:
    qi = _first(node, "qualified_identifier", "identifier")
    if qi is None:
        return
    module = _text(qi)
    # `import a.b.*` — the wildcard may be a sibling token of the identifier.
    if b"*" in node.text and not module.endswith(".*"):
        module += ".*"
    result.imports.append(Import(module=module, relative=False))


def _walk(node: Node, parent: str | None, result: FileExtraction) -> None:
    for child in node.named_children:
        t = child.type
        if t in _TYPE_DECLS:
            _add_type(child, parent, result)
        elif t == "companion_object":
            _add_type(child, parent, result, default_name="Companion")
        elif t == "function_declaration":
            _add_function(child, parent, result)
        elif t == "ERROR":
            # Recover definitions from a locally malformed region.
            _walk(child, parent, result)


def _function_name(node: Node) -> str | None:
    # Extension functions carry a receiver type before the name; the name is the
    # identifier child that follows it (the last identifier before the parameters).
    name = None
    for c in node.named_children:
        if c.type == "identifier":
            name = _text(c)
        elif c.type == "function_value_parameters":
            break
    return name


def _add_function(node: Node, parent: str | None, result: FileExtraction) -> None:
    name = _function_name(node)
    if name is None:
        return
    qualname = f"{parent}.{name}" if parent else name
    result.definitions.append(
        Definition(qualname=qualname, kind="Function", line=node.start_point[0] + 1, parent=parent)
    )


def _add_type(node: Node, parent: str | None, result: FileExtraction, default_name: str | None = None) -> None:
    ident = _first(node, "identifier")
    name = _text(ident) if ident is not None else default_name
    if name is None:
        return
    qualname = f"{parent}.{name}" if parent else name
    result.definitions.append(
        Definition(qualname=qualname, kind="Class", line=node.start_point[0] + 1, parent=parent)
    )
    for body in node.named_children:
        if body.type in _BODIES:
            _walk(body, qualname, result)
