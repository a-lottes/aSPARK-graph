"""Language -> extractor dispatch.

A language present in ``EXTENSION_LANGUAGE`` but absent from this registry is a
*known but unsupported* language: the build records its files as unparsed
``File`` nodes (AC-4.2). This is also the A9 early-cut path — a slipped
extractor simply isn't registered here.
"""

from __future__ import annotations

from collections.abc import Callable

from .base import FileExtraction, language_for
from . import code_go, code_java, code_py, code_rust, code_ts

Extractor = Callable[[str, bytes], FileExtraction]

_REGISTRY: dict[str, Extractor] = {
    "python": code_py.extract,
    "typescript": code_ts.extract,
    "javascript": code_ts.extract,
    "java": code_java.extract,
    "go": code_go.extract,
    "rust": code_rust.extract,
}


def register(language: str, extractor: Extractor) -> None:
    _REGISTRY[language] = extractor


def get_extractor(language: str) -> Extractor | None:
    return _REGISTRY.get(language)


__all__ = ["get_extractor", "register", "language_for", "FileExtraction"]
