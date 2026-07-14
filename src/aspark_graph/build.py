"""Full-rescan build: walk a repo, extract code, parse artifacts, link them.

Deterministic and offline (AC-1.2): files are visited in sorted order, ids are
content/location-derived, and the graph is serialised canonically. A rebuild of
an unchanged repo yields an identical graph.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from . import artifacts, extractors
from .extractors.base import FileExtraction, language_for
from .graph import Graph
from .model import (
    Confidence,
    EdgeType,
    NodeType,
    definition_id,
    file_id,
)

# Directories never worth walking for source.
_SKIP_DIRS = {
    ".git", ".aspark-graph", "node_modules", ".venv", "venv", "__pycache__",
    ".pytest_cache", "dist", "build", ".mypy_cache", ".ruff_cache", ".idea",
    ".tox", "site-packages",
}
# Common source roots stripped when computing a Python module's dotted name.
_PY_SOURCE_ROOTS = ("src/", "lib/")


@dataclass
class BuildReport:
    code_entities: int = 0
    artifact_entities: int = 0
    unparsed: list[str] = field(default_factory=list)

    def summary(self) -> str:
        line = f"{self.code_entities} code entities, {self.artifact_entities} artifact entities"
        if self.unparsed:
            line += f", {len(self.unparsed)} file(s) unparsed"
        return line


def build_graph(repo_root: str | Path) -> tuple[Graph, BuildReport]:
    repo_root = Path(repo_root).resolve()
    graph = Graph()
    report = BuildReport()

    extractions: list[FileExtraction] = []
    for path in _iter_source_files(repo_root):
        relpath = _relpath(path, repo_root)
        language = language_for(relpath)
        if language is None:
            continue  # not a source file the tool knows about
        source = path.read_bytes()
        digest = hashlib.sha256(source).hexdigest()[:16]
        extractor = extractors.get_extractor(language)
        if extractor is None:
            # Known language, no extractor (unsupported / A9 early-cut): AC-4.2.
            graph.add_node(file_id(relpath), NodeType.FILE, language=language, hash=digest, unparsed=True)
            report.unparsed.append(relpath)
            continue
        extraction = extractor(relpath, source)
        graph.add_node(file_id(relpath), NodeType.FILE, language=language, hash=digest, package=extraction.package)
        _add_definitions(graph, extraction)
        extractions.append(extraction)

    _resolve_imports(graph, extractions)

    report.code_entities = graph.counts()["code"]
    report.artifact_entities = artifacts.extract_features(repo_root, graph)
    return graph, report


def _iter_source_files(repo_root: Path):
    for path in sorted(repo_root.rglob("*")):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(repo_root).parts
        if any(part in _SKIP_DIRS for part in rel_parts[:-1]):
            continue
        yield path


def _relpath(path: Path, repo_root: Path) -> str:
    return PurePosixPath(path.relative_to(repo_root).as_posix()).as_posix()


def _add_definitions(graph: Graph, extraction: FileExtraction) -> None:
    fid = file_id(extraction.relpath)
    for d in extraction.definitions:
        did = definition_id(extraction.relpath, d.qualname)
        ntype = NodeType.CLASS if d.kind == "Class" else NodeType.FUNCTION
        graph.add_node(
            did, ntype,
            name=d.qualname, file=extraction.relpath, line=d.line, exported=d.exported,
        )
        # contains: File -> top-level def; enclosing def -> nested def.
        if d.parent is None:
            graph.add_edge(fid, did, EdgeType.CONTAINS, Confidence.EXTRACTED)
        else:
            parent_id = definition_id(extraction.relpath, d.parent)
            graph.add_edge(parent_id, did, EdgeType.CONTAINS, Confidence.EXTRACTED)


def _resolve_imports(graph: Graph, extractions: list[FileExtraction]) -> None:
    """Best-effort File -> File ``imports`` edges (static; may be incomplete)."""
    py_index = _python_module_index(extractions)
    java_index = _java_type_index(extractions)
    rel_index = {e.relpath for e in extractions}
    for e in extractions:
        src = file_id(e.relpath)
        for imp in e.imports:
            target_rel = None
            if e.language == "python":
                target_rel = _resolve_python_import(imp, e.relpath, py_index)
            elif e.language in ("typescript", "javascript"):
                target_rel = _resolve_ts_import(imp, e.relpath, rel_index)
            elif e.language == "java":
                target_rel = java_index.get(imp.module)
            # Only emit an edge when we resolve to a file that is in the graph.
            if target_rel and target_rel in rel_index and target_rel != e.relpath:
                graph.add_edge(src, file_id(target_rel), EdgeType.IMPORTS, Confidence.EXTRACTED)


def _python_module_index(extractions: list[FileExtraction]) -> dict[str, str]:
    """Map candidate dotted module names -> relpath for Python files."""
    index: dict[str, str] = {}
    for e in extractions:
        if e.language != "python":
            continue
        rel = e.relpath
        stripped = rel
        for root in _PY_SOURCE_ROOTS:
            if stripped.startswith(root):
                stripped = stripped[len(root):]
                break
        without_ext = stripped[:-3] if stripped.endswith(".py") else stripped
        parts = without_ext.split("/")
        if parts[-1] == "__init__":
            parts = parts[:-1]  # package -> its dir name
        if not parts:
            continue
        dotted = ".".join(parts)
        # First writer wins for determinism (files visited in sorted order).
        index.setdefault(dotted, rel)
    return index


def _java_type_index(extractions: list[FileExtraction]) -> dict[str, str]:
    """Map fully-qualified Java type names (``package.Class``) -> relpath."""
    index: dict[str, str] = {}
    for e in extractions:
        if e.language != "java":
            continue
        prefix = f"{e.package}." if e.package else ""
        for d in e.definitions:
            if d.kind == "Class" and d.parent is None:
                index.setdefault(f"{prefix}{d.qualname}", e.relpath)
    return index


def _resolve_python_import(imp, importer_rel: str, index: dict[str, str]) -> str | None:
    if imp.relative:
        return _resolve_relative_python(imp.module, importer_rel, index)
    module = imp.module
    if module in index:
        return index[module]
    # `import a.b.c` may reference module a.b (importing a submodule attribute).
    while "." in module:
        module = module.rsplit(".", 1)[0]
        if module in index:
            return index[module]
    return None


_TS_EXTS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")


def _resolve_ts_import(imp, importer_rel: str, rel_index: set[str]) -> str | None:
    """Resolve a relative TS/JS import specifier to a repo file (best-effort).

    Bare specifiers (npm packages) never resolve to a repo file, so they emit no
    edge — which is correct."""
    if not imp.relative:
        return None
    base = PurePosixPath(importer_rel).parent
    target = base
    for part in imp.module.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            target = target.parent
        else:
            target = target / part
    stem = target.as_posix()
    # Try direct extensions, then index files in a directory of that name.
    for ext in _TS_EXTS:
        if f"{stem}{ext}" in rel_index:
            return f"{stem}{ext}"
    for ext in _TS_EXTS:
        if f"{stem}/index{ext}" in rel_index:
            return f"{stem}/index{ext}"
    return None


def _resolve_relative_python(spec: str, importer_rel: str, index: dict[str, str]) -> str | None:
    # spec looks like ".", ".mod", "..pkg.mod"
    level = len(spec) - len(spec.lstrip("."))
    tail = spec[level:]
    base_dir = PurePosixPath(importer_rel).parent
    for _ in range(level - 1):
        base_dir = base_dir.parent
    target = base_dir
    if tail:
        for part in tail.split("."):
            target = target / part
    module_py = f"{target.as_posix()}.py"
    init_py = f"{(target / '__init__').as_posix()}.py"
    rel_files = set(index.values())
    if module_py in rel_files:
        return module_py
    if init_py in rel_files:
        return init_py
    return None
