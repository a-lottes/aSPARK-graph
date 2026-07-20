"""Extractor protocol and language dispatch by file extension.

An extractor turns one source file's bytes into a language-agnostic
``FileExtraction`` — the build orchestrator (``build.py``) is what actually adds
nodes and edges to the graph and resolves imports across files. Keeping the
extractors pure (bytes in, dataclass out) makes them trivial to unit-test per
language (AC-4.1) without a graph.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Definition:
    """A class, function or method defined in a file."""

    qualname: str          # e.g. "Foo" or "Foo.bar"
    kind: str              # "Class" | "Function"
    line: int              # 1-based start line
    parent: str | None = None  # enclosing qualname, or None for top level
    exported: bool = True      # best-effort; languages that lack the notion say True


@dataclass
class Import:
    """A raw import as written; resolution to a repo file happens in the build."""

    module: str            # dotted/relative module or specifier as written
    relative: bool = False  # Python "from . import x" / TS "./foo"


@dataclass
class FileExtraction:
    relpath: str
    language: str
    definitions: list[Definition] = field(default_factory=list)
    imports: list[Import] = field(default_factory=list)
    package: str | None = None  # Java package; None for languages without the notion


# extension -> language name; the build uses this to pick an extractor and to
# label File nodes. Unlisted extensions are recorded as unparsed (AC-4.2).
EXTENSION_LANGUAGE = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
}


def language_for(relpath: str) -> str | None:
    from pathlib import PurePosixPath

    return EXTENSION_LANGUAGE.get(PurePosixPath(relpath).suffix)
