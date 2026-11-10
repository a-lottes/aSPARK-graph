"""tree-sitter Kotlin extractor: File, package, classes/objects/interfaces/enums, functions, imports.

Deterministic and offline. ``.kt`` and ``.kts`` share this extractor. Like Java, the
package header is captured on the extraction so the build can resolve fully-qualified
imports to repo files (best-effort). Out of scope: KMP ``expect``/``actual`` pairing,
annotation processing.
"""

from __future__ import annotations

import re
from bisect import bisect_right

import tree_sitter_kotlin
from tree_sitter import Language, Node, Parser

from .base import Definition, FileExtraction, Import

_LANGUAGE = Language(tree_sitter_kotlin.language())
_PARSER = Parser(_LANGUAGE)

# class, data class, interface, enum class share class_declaration; objects and
# companion objects have their own node types.
_TYPE_DECLS = {"class_declaration", "object_declaration"}
_BODIES = {"class_body", "enum_class_body"}


# The pinned grammar needs a line break between a body's `{`/`}` and its members, so
# one-line bodies (`class X { companion object { const val T = 1 } }`) parse as ERROR.
# The retry parses a same-length copy in which the spaces after `{` / before `}`
# become newlines. Comments and string, char and backtick-name literals are skipped
# verbatim: they are never rewritten (so a `{ ` inside them is inert), and the
# extractor never edits an identifier. Same byte length,
# so every offset (and therefore every original line number) is preserved.
_AFTER_OPEN = re.compile(rb"\{[ \t]+(?=[^\s}])")
_BEFORE_CLOSE = re.compile(rb"(?<=[^\s{])[ \t]+(?=\})")
_TOKENS = re.compile(
    rb"(?P<comment>//[^\n]*|/\*.*?\*/)"
    rb'|(?P<literal>"""(?:.|\n)*?"""|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])+\'|`[^`\n]*`)',
    re.DOTALL,
)


def _rewrite_code(code: bytes) -> bytes:
    code = _AFTER_OPEN.sub(lambda m: b"{\n" + m.group(0)[2:], code)
    return _BEFORE_CLOSE.sub(lambda m: b"\n" + m.group(0)[1:], code)


def _normalize_for_retry(source: bytes) -> bytes:
    out: list[bytes] = []
    pos = 0
    for m in _TOKENS.finditer(source):
        out.append(_rewrite_code(source[pos:m.start()]))
        out.append(m.group(0))
        pos = m.end()
    out.append(_rewrite_code(source[pos:]))
    return b"".join(out)


def _error_count(node: Node) -> int:
    """ERROR and MISSING nodes under ``node`` (0 means a clean parse)."""
    if node.type == "ERROR" or node.is_missing:
        return 1
    return sum(_error_count(c) for c in node.children) if node.has_error else 0


def extract(relpath: str, source: bytes) -> FileExtraction:
    tree = _PARSER.parse(source)
    errors = _error_count(tree.root_node)
    if errors:
        retry = _PARSER.parse(_normalize_for_retry(source))
        retry_errors = _error_count(retry.root_node)
        if retry_errors < errors:
            tree, errors = retry, retry_errors
    line_starts = [0] + [m.end() for m in re.finditer(rb"\n", source)]
    result = FileExtraction(relpath=relpath, language="kotlin", partial=errors > 0)
    root = tree.root_node
    for child in root.named_children:
        t = child.type
        if t == "package_header":
            qi = _first(child, "qualified_identifier", "identifier")
            if qi is not None:
                result.package = _text(qi)
        elif t == "import":
            _add_import(child, result)
    if root.type != "ERROR":  # a root ERROR is an ERROR region too: never walked (F18)
        _walk(root, None, result, line_starts)
    return result


def _line(node: Node, lines: list[int]) -> int:
    """1-based line in the ORIGINAL source (the retry parse keeps byte offsets)."""
    return bisect_right(lines, node.start_byte)


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


def _walk(node: Node, parent: str | None, result: FileExtraction, lines: list[int]) -> None:
    for child in node.named_children:
        t = child.type
        if t in _TYPE_DECLS:
            _add_type(child, parent, result, lines)
        elif t == "companion_object":
            _add_type(child, parent, result, lines, default_name="Companion")
        elif t == "function_declaration":
            _add_function(child, parent, result, lines)
        # ERROR regions are deliberately not walked: recovered members would get the
        # wrong parent (a wrong link is worse than honest absence); the file is flagged
        # `partial` instead.


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


def _add_function(node: Node, parent: str | None, result: FileExtraction, lines: list[int]) -> None:
    name = _function_name(node)
    if name is None:
        return
    qualname = f"{parent}.{name}" if parent else name
    result.definitions.append(
        Definition(qualname=qualname, kind="Function", line=_line(node, lines), parent=parent)
    )


def _add_type(
    node: Node, parent: str | None, result: FileExtraction, lines: list[int], default_name: str | None = None
) -> None:
    ident = _first(node, "identifier")
    name = _text(ident) if ident is not None else default_name
    if name is None:
        return
    qualname = f"{parent}.{name}" if parent else name
    result.definitions.append(
        Definition(qualname=qualname, kind="Class", line=_line(node, lines), parent=parent)
    )
    for body in node.named_children:
        if body.type in _BODIES:
            _walk(body, qualname, result, lines)
