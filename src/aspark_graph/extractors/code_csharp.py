"""tree-sitter C# extractor: File, namespace, types, methods/constructors/local functions, usings.

Deterministic and offline. The first namespace declared in the file is captured
as ``package`` so the build can resolve ``using`` directives to repo files
(best-effort). Out of scope: partial classes across files (each file's part is
its own ``Class`` node), generics beyond naming (``List<T>`` keeps the bare
type name), Razor files.
"""

from __future__ import annotations

import tree_sitter_c_sharp
from tree_sitter import Language, Node, Parser

from .base import Definition, FileExtraction, Import

_LANGUAGE = Language(tree_sitter_c_sharp.language())
_PARSER = Parser(_LANGUAGE)

_TYPE_DECLS = {
    "class_declaration", "struct_declaration", "interface_declaration",
    "record_declaration", "record_struct_declaration", "enum_declaration",
}
_NAMESPACES = {"namespace_declaration", "file_scoped_namespace_declaration"}
_MEMBER_FUNCS = {"method_declaration", "constructor_declaration"}


def extract(relpath: str, source: bytes) -> FileExtraction:
    tree = _PARSER.parse(source)
    result = FileExtraction(relpath=relpath, language="csharp")
    _walk(tree.root_node, parent=None, result=result)
    return result


def _text(node: Node) -> str:
    return node.text.decode("utf-8", errors="replace")


def _name(node: Node) -> str | None:
    name_node = node.child_by_field_name("name")
    return _text(name_node) if name_node is not None else None


def _walk(node: Node, parent: str | None, result: FileExtraction) -> None:
    for child in node.named_children:
        t = child.type
        if t in _NAMESPACES:
            ns = _name(child)
            if ns and result.package is None:
                result.package = ns
            # Block form nests members in `body`; file-scoped form puts the
            # following declarations as siblings, handled by this same loop.
            body = child.child_by_field_name("body")
            if body is not None:
                _walk(body, parent, result)
        elif t == "using_directive":
            _add_using(child, result)
        elif t in _TYPE_DECLS:
            _add_type(child, parent, result)


def _add_using(node: Node, result: FileExtraction) -> None:
    # `using A.B;`, `using static A.B;`, `using X = A.B;`, `global using A.B;`
    # — the target is the last identifier/qualified_name child (an alias name
    # is the `name` field and comes first).
    targets = [c for c in node.named_children if c.type in ("qualified_name", "identifier")]
    if targets:
        result.imports.append(Import(module=_text(targets[-1]), relative=False))


def _add_type(node: Node, parent: str | None, result: FileExtraction) -> None:
    name = _name(node)
    if name is None:
        return
    qualname = f"{parent}.{name}" if parent else name
    result.definitions.append(
        Definition(qualname=qualname, kind="Class", line=node.start_point[0] + 1, parent=parent)
    )
    body = node.child_by_field_name("body")
    if body is None:
        return
    for member in body.named_children:
        if member.type in _MEMBER_FUNCS:
            mname = _name(member)
            if mname is not None:
                mqual = f"{qualname}.{mname}"
                result.definitions.append(
                    Definition(qualname=mqual, kind="Function", line=member.start_point[0] + 1, parent=qualname)
                )
                _add_local_functions(member, mqual, result)
        elif member.type in _TYPE_DECLS:
            _add_type(member, qualname, result)  # nested type


def _add_local_functions(node: Node, parent: str, result: FileExtraction) -> None:
    for child in node.named_children:
        if child.type == "local_function_statement":
            lname = _name(child)
            if lname is None:
                continue
            lqual = f"{parent}.{lname}"
            result.definitions.append(
                Definition(qualname=lqual, kind="Function", line=child.start_point[0] + 1, parent=parent)
            )
            _add_local_functions(child, lqual, result)
        else:
            _add_local_functions(child, parent, result)
