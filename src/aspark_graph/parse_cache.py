"""Parse cache: per-file FileExtraction persistence to skip re-parsing unchanged files.

Stored at .aspark-graph/parse-cache.json alongside graph.json. The cache is
supplemental — graph.json remains canonical (A3). When the cache is absent,
corrupt, or version-mismatched, CacheUnusable is raised; build_graph catches it
and falls back to a full rescan (US-3).
"""

from __future__ import annotations

import json
from importlib.metadata import PackageNotFoundError, version as pkg_version
from pathlib import Path

from .extractors.base import Definition, FileExtraction, Import
from .graph import GRAPH_DIRNAME

CACHE_FILENAME = "parse-cache.json"


class CacheUnusable(Exception):
    """Raised when the cache cannot be used (corrupt, absent, version mismatch)."""


def _version_tag() -> str:
    """Build a cache invalidation key from installed package + parser versions.

    Keyed on the tool itself and all four parse-affecting dependencies so that
    any grammar or core upgrade triggers a full rescan (AC-2.4, AC-3.3).
    Read from importlib.metadata — never from __init__.__version__ which is stale.
    """
    def v(pkg: str) -> str:
        try:
            return pkg_version(pkg)
        except PackageNotFoundError:
            return "unknown"

    return (
        f"aspark-graph={v('aspark-graph')}"
        f":tree-sitter={v('tree-sitter')}"
        f":tree-sitter-python={v('tree-sitter-python')}"
        f":tree-sitter-typescript={v('tree-sitter-typescript')}"
        f":tree-sitter-java={v('tree-sitter-java')}"
    )


def _cache_path(repo_root: Path) -> Path:
    return repo_root / GRAPH_DIRNAME / CACHE_FILENAME


# --- serialization -----------------------------------------------------------

def _serialize_extraction(e: FileExtraction, sha256: str) -> dict:
    return {
        "definitions": [
            {
                "exported": d.exported,
                "kind": d.kind,
                "line": d.line,
                "parent": d.parent,
                "qualname": d.qualname,
            }
            for d in e.definitions
        ],
        "imports": [
            {"module": i.module, "relative": i.relative}
            for i in e.imports
        ],
        "language": e.language,
        "package": e.package,
        "sha256": sha256,
    }


def _deserialize_extraction(relpath: str, data: dict) -> FileExtraction:
    definitions = [
        Definition(
            qualname=d["qualname"],
            kind=d["kind"],
            line=d["line"],
            parent=d.get("parent"),
            exported=d.get("exported", True),
        )
        for d in data.get("definitions", [])
    ]
    imports = [
        Import(module=i["module"], relative=i.get("relative", False))
        for i in data.get("imports", [])
    ]
    return FileExtraction(
        relpath=relpath,
        language=data["language"],
        definitions=definitions,
        imports=imports,
        package=data.get("package"),
    )


# --- public API --------------------------------------------------------------

class ParseCache:
    """Loaded cache for one build pass."""

    def __init__(self, entries: dict[str, dict]) -> None:
        self._entries = entries

    def lookup(self, relpath: str, sha256: str) -> FileExtraction | None:
        """Return the cached FileExtraction when relpath+sha256 match, else None.

        Returns None (cache miss) on any deserialization error so a malformed
        entry body never propagates a traceback into the build (NFR-3).
        """
        entry = self._entries.get(relpath)
        if entry is None or entry.get("sha256") != sha256:
            return None
        try:
            return _deserialize_extraction(relpath, entry)
        except (KeyError, TypeError, ValueError):
            return None


def load(repo_root: Path) -> ParseCache:
    """Load and validate the cache, or raise CacheUnusable."""
    path = _cache_path(repo_root)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise CacheUnusable("no cache file")
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        raise CacheUnusable(f"corrupt cache: {exc}")

    stored_tag = data.get("version", "")
    current_tag = _version_tag()
    if stored_tag != current_tag:
        raise CacheUnusable(
            f"version mismatch: cache={stored_tag!r}, current={current_tag!r}"
        )

    entries = data.get("entries", {})
    if not isinstance(entries, dict):
        raise CacheUnusable("cache 'entries' is not a dict")

    return ParseCache(entries=entries)


def save(
    repo_root: Path,
    extraction_triples: list[tuple[str, str, FileExtraction]],
) -> None:
    """Write a canonical cache from (relpath, sha256, extraction) triples."""
    entries = {
        relpath: _serialize_extraction(extraction, sha256)
        for relpath, sha256, extraction in sorted(extraction_triples, key=lambda t: t[0])
    }
    payload = {"entries": entries, "version": _version_tag()}
    path = _cache_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
