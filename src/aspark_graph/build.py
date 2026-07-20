"""Build: walk a repo, extract code, parse artifacts, link them.

Deterministic and offline (AC-1.2): files are visited in sorted order, ids are
content/location-derived, and the graph is serialised canonically. A rebuild of
an unchanged repo yields an identical graph.

Incremental path: on repeated builds, unchanged files are reused from
.aspark-graph/parse-cache.json without re-invoking the tree-sitter extractors.
The cache is supplemental — graph.json stays canonical. A corrupt, absent, or
version-mismatched cache silently falls back to a full rescan (US-3).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from . import artifacts, extractors, inference, parse_cache
from .extractors.base import FileExtraction, language_for
from .graph import Graph, default_graph_path
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
    inferred_edges: int = 0
    unparsed: list[str] = field(default_factory=list)
    # Incremental-build accounting (T1+):
    incremental: bool = False     # True when the cache was used for this build
    reparsed: int = 0             # files that went through the extractor
    cached: int = 0               # files reused from the parse cache
    fallback_reason: str | None = None  # set when incremental was attempted but fell back

    def summary(self) -> str:
        line = f"{self.code_entities} code entities, {self.artifact_entities} artifact entities"
        if self.inferred_edges:
            line += f", {self.inferred_edges} inferred link(s)"
        if self.unparsed:
            line += f", {len(self.unparsed)} file(s) unparsed"
        if self.incremental:
            line += f"; incremental: {self.reparsed} re-parsed, {self.cached} cached"
        else:
            line += "; full rescan"
        return line


def build_graph(repo_root: str | Path, *, full: bool = False) -> tuple[Graph, BuildReport]:
    """Build (or incrementally update) the knowledge graph for a repo.

    When full=True, ignore any cached parse results and rescan every file.
    When full=False (the default), reuse cached FileExtraction objects for
    unchanged files; fall back to a full rescan if the cache is unusable.
    """
    repo_root = Path(repo_root).resolve()
    graph = Graph()
    report = BuildReport()

    # Incremental path: only attempted when graph.json already exists (anchor
    # rule) and full rescan was not requested. First builds always scan everything.
    cache: parse_cache.ParseCache | None = None
    if not full and default_graph_path(repo_root).exists():
        try:
            cache = parse_cache.load(repo_root)
        except parse_cache.CacheUnusable as exc:
            report.fallback_reason = str(exc)

    report.incremental = cache is not None

    extractions: list[FileExtraction] = []
    # Triples for cache write after the build: (relpath, sha256, extraction).
    cache_triples: list[tuple[str, str, FileExtraction]] = []

    for path in _iter_source_files(repo_root):
        relpath = _relpath(path, repo_root)
        language = language_for(relpath)
        if language is None:
            continue
        source = path.read_bytes()
        digest = hashlib.sha256(source).hexdigest()[:16]

        # Cache-or-parse seam: the only place that decides whether to invoke the
        # extractor. Everything downstream is identical regardless of origin.
        extraction: FileExtraction | None = None
        if cache is not None:
            extraction = cache.lookup(relpath, digest)

        if extraction is not None:
            report.cached += 1
        else:
            extractor = extractors.get_extractor(language)
            if extractor is None:
                # Known language, no extractor registered yet (unsupported extension).
                graph.add_node(file_id(relpath), NodeType.FILE, language=language, hash=digest, unparsed=True)
                report.unparsed.append(relpath)
                continue
            extraction = extractor(relpath, source)
            report.reparsed += 1

        graph.add_node(file_id(relpath), NodeType.FILE, language=language, hash=digest, package=extraction.package)
        _add_definitions(graph, extraction)
        extractions.append(extraction)
        cache_triples.append((relpath, digest, extraction))

    _resolve_imports(graph, extractions)

    report.code_entities = graph.counts()["code"]
    report.artifact_entities = artifacts.extract_features(repo_root, graph)
    # Best-effort inferred implements edges from git history. No-op if git
    # is unavailable (AC-1.6). Inference is out of scope for incremental
    # caching this cycle — it runs on every build (unchanged from prior versions).
    report.inferred_edges = inference.infer_implements(graph, repo_root)

    # Always rewrite the cache after a successful build (full or incremental).
    # This means --full replaces the cache with fresh state (AC-4.2) and first
    # builds leave a cache ready for the next incremental run.
    parse_cache.save(repo_root, cache_triples)

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
    go_index = _go_package_index(extractions)
    rust_index = _rust_module_index(extractions)
    rel_index = {e.relpath for e in extractions}
    for e in extractions:
        src = file_id(e.relpath)
        for imp in e.imports:
            if e.language == "go":
                # A Go import addresses a package (a directory), not a single
                # file, so an unambiguous match can fan out to several files.
                for target_rel in _resolve_go_import(imp, e.relpath, go_index):
                    if target_rel in rel_index and target_rel != e.relpath:
                        graph.add_edge(src, file_id(target_rel), EdgeType.IMPORTS, Confidence.EXTRACTED)
                continue
            target_rel = None
            if e.language == "python":
                target_rel = _resolve_python_import(imp, e.relpath, py_index)
            elif e.language in ("typescript", "javascript"):
                target_rel = _resolve_ts_import(imp, e.relpath, rel_index)
            elif e.language == "java":
                target_rel = java_index.get(imp.module)
            elif e.language == "rust":
                target_rel = _resolve_rust_import(imp, e.relpath, rust_index)
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


def _go_package_index(extractions: list[FileExtraction]) -> dict[str, list[str]]:
    """Map a repo directory path (the Go package it holds) -> its .go files."""
    index: dict[str, list[str]] = {}
    for e in extractions:
        if e.language != "go":
            continue
        dir_path = PurePosixPath(e.relpath).parent.as_posix()
        if dir_path in (".", ""):
            continue  # root-level "main" packages are not meaningfully importable
        index.setdefault(dir_path, []).append(e.relpath)
    for files in index.values():
        files.sort()
    return index


def _resolve_go_import(imp, importer_rel: str, dir_index: dict[str, list[str]]) -> list[str]:
    """Trailing-path-segment match of an import path against repo directories.

    No `go.mod` parsing (A3): a stdlib/third-party import simply matches no
    repo directory. An import path matching more than one candidate directory
    is ambiguous and resolves to no edge (A7) rather than a guess.
    """
    path = imp.module
    candidates = [d for d in dir_index if d == path or path.endswith(f"/{d}")]
    if len(candidates) != 1:
        return []
    return [f for f in dir_index[candidates[0]] if f != importer_rel]


def _rust_module_index(extractions: list[FileExtraction]) -> dict[str, list[str]]:
    """Map a crate-relative module path (``crate::foo::bar``) -> its .rs file(s).

    Layout-only (no `Cargo.toml`/workspace awareness, A3): `src/lib.rs` and
    `src/main.rs` are the crate root; `src/foo.rs` and `src/foo/mod.rs` are
    module `foo`; `src/foo/bar.rs` is `foo::bar`. More than one file mapping
    to the same module path is a genuine collision our no-manifest index
    can't disambiguate — recorded as multiple candidates so resolution can
    refuse to guess (AC-4.3), never a silent first-writer-wins pick.
    """
    index: dict[str, list[str]] = {}
    for e in extractions:
        if e.language != "rust":
            continue
        key = f"crate::{_rust_module_path_of(e.relpath)}" if _rust_module_path_of(e.relpath) else "crate"
        index.setdefault(key, []).append(e.relpath)
    return index


def _resolve_rust_import(imp, importer_rel: str, index: dict[str, list[str]]) -> str | None:
    """Resolve a ``crate::``/``self::``/``super::``-relative ``use`` path.

    External crates (any other leading segment) never resolve to a repo file
    — correctly emitting no edge (AC-4.2). ``self``/``super`` are resolved
    relative to the importing file's own module path.
    """
    path = imp.module
    head, _, rest = path.partition("::")
    if head == "crate":
        candidate = f"crate::{rest}" if rest else "crate"
        return _lookup_or_parent(candidate, index)
    if head in ("self", "super"):
        importer_module = _rust_module_path_of(importer_rel)
        base_parts = importer_module.split("::") if importer_module else []
        if head == "super":
            base_parts = base_parts[:-1]
        candidate_parts = base_parts + ([rest] if rest else [])
        candidate = "::".join(["crate", *candidate_parts]) if candidate_parts else "crate"
        return _lookup_or_parent(candidate, index)
    return None  # external crate — no repo file, correctly unresolved


def _rust_module_path_of(relpath: str) -> str:
    stripped = relpath[4:] if relpath.startswith("src/") else relpath
    without_ext = stripped[:-3] if stripped.endswith(".rs") else stripped
    parts = without_ext.split("/")
    if parts and parts[-1] in ("mod", "lib", "main"):
        parts = parts[:-1]
    return "::".join(p for p in parts if p)


def _lookup_or_parent(candidate: str, index: dict[str, list[str]]) -> str | None:
    # `use crate::foo::Bar` addresses the *item* Bar inside module foo; try the
    # full path first, then walk up to the nearest enclosing module file. A
    # key with more than one candidate file is ambiguous — no edge (A7).
    while True:
        files = index.get(candidate)
        if files is not None:
            return files[0] if len(files) == 1 else None
        if "::" not in candidate:
            return None
        candidate = candidate.rsplit("::", 1)[0]


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
