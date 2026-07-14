"""tree-sitter Python extractor: File, classes, functions/methods, imports.

Deterministic and offline. Nesting is tracked so methods carry their enclosing
class in the qualname (``Foo.bar``); the build turns that into ``contains``
edges. Import *resolution* to repo files is the build's job — here we only
record what was written.
"""

from __future__ import annotations

import tree_sitter_python
from tree_sitter import Language, Node, Parser

from .base import Definition, FileExtraction, Import

_LANGUAGE = Language(tree_sitter_python.language())
_PARSER = Parser(_LANGUAGE)


def extract(relpath: str, source: bytes) -> FileExtraction:
    tree = _PARSER.parse(source)
    result = FileExtraction(relpath=relpath, language="python")
    _walk(tree.root_node, parent=None, result=result)
    return result


def _text(node: Node) -> str:
    return node.text.decode("utf-8", errors="replace")


def _walk(node: Node, parent: str | None, result: FileExtraction) -> None:
    for child in node.named_children:
        if child.type == "class_definition":
            name = _name(child)
            if name is None:
                continue
            qualname = f"{parent}.{name}" if parent else name
            result.definitions.append(
                Definition(qualname=qualname, kind="Class", line=child.start_point[0] + 1, parent=parent)
            )
            body = child.child_by_field_name("body")
            if body is not None:
                _walk(body, parent=qualname, result=result)
        elif child.type == "function_definition":
            name = _name(child)
            if name is None:
                continue
            qualname = f"{parent}.{name}" if parent else name
            result.definitions.append(
                Definition(qualname=qualname, kind="Function", line=child.start_point[0] + 1, parent=parent)
            )
            body = child.child_by_field_name("body")
            if body is not None:
                _walk(body, parent=qualname, result=result)
        elif child.type == "import_statement":
            _collect_plain_imports(child, result)
        elif child.type == "import_from_statement":
            _collect_from_import(child, result)
        else:
            # Descend into blocks (if/try/with) so top-level-ish imports and
            # defs guarded by them are still seen; but do not cross into a new
            # def/class scope here (handled above).
            if child.type in _TRANSPARENT:
                _walk(child, parent=parent, result=result)


_TRANSPARENT = {
    "if_statement", "else_clause", "elif_clause", "try_statement",
    "except_clause", "finally_clause", "with_statement", "block",
    "decorated_definition",
}


def _name(node: Node) -> str | None:
    name_node = node.child_by_field_name("name")
    return _text(name_node) if name_node is not None else None


def _collect_plain_imports(node: Node, result: FileExtraction) -> None:
    # import a.b, c as d
    for child in node.named_children:
        if child.type == "dotted_name":
            result.imports.append(Import(module=_text(child), relative=False))
        elif child.type == "aliased_import":
            name_node = child.child_by_field_name("name")
            if name_node is not None:
                result.imports.append(Import(module=_text(name_node), relative=False))


def _collect_from_import(node: Node, result: FileExtraction) -> None:
    # from [.]module import ...  — we care about the module being imported from
    module_node = node.child_by_field_name("module_name")
    if module_node is None:
        return
    if module_node.type == "relative_import":
        result.imports.append(Import(module=_text(module_node), relative=True))
    else:
        result.imports.append(Import(module=_text(module_node), relative=False))
