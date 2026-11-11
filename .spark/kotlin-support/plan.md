# Plan: kotlin-support

| | |
|---|---|
| **Phase** | Engineering Manager (/sprint-plan) |
| **Owner** | approved |
| **Status** | `` |
| **Date** | 2026-11-11 |

## 1. Architecture Decision

New `extractors/code_kotlin.py` (tree-sitter-kotlin 1.1.0), registered in the dispatch and `EXTENSION_LANGUAGE`; Kotlin import resolution in `build.py` (symbol index + package fan-out). The grammar wraps some single-line class bodies in `ERROR`, so the walk looks through `ERROR` nodes.

## 3. Task Breakdown

| # | Task | Story | Covers (AC / NFR) | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|---|
| T1 | Pin grammar, register `.kt`/`.kts`, write `code_kotlin.py` and `tests/test_extractor_kotlin.py`. | US-1 | AC-1.1, AC-1.2, AC-1.3 | – | `done` | Extractor tests green. |
| T2 | Kotlin import resolution in `build.py`, with a build test. | US-2 | AC-2.1 | T1 | `done` | Build test shows in-repo edges only. |
| T3 | Multi-language and determinism tests, README. | US-3 | AC-3.1 | T1, T2 | `done` | Full suite green. |

## ✅ PLAN GATE

- [x] Approved (autonomous mode, recommended option)
