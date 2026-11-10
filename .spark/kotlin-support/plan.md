# Plan: kotlin-support

| | |
|---|---|
| **Phase** | Plan |
| **Owner** | Engineering Manager (`/sprint-plan`) |
| **Input** | `.spark/kotlin-support/spec.md` (`approved`, 2026-11-10) |
| **Status** | `approved` |
| **Date** | 2026-11-10 |

## 1. Architecture Decision

Follow the Java/Go/Rust pattern: pure `code_kotlin.py` (bytes in, `FileExtraction` out), `EXTENSION_LANGUAGE` + registry entries, a `build.py` index keyed `package.Name` over top-level classes and functions, resolved exact-then-walk-up. Rejected: wildcard-import fan-out (a package is not a file; honest absence). The grammar is `tree-sitter-kotlin==1.1.0`.

## 3. Task Breakdown

| # | Task | Story | Covers (AC / NFR) | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|---|
| T1 | Pin grammar, wire `.kt`/`.kts`, write `code_kotlin.py` | US-1, US-3 | AC-1.1, AC-1.2, AC-1.3, AC-3.1 | – | `done` | Kotlin files parse to Class/Function nodes; grammar pinned `==` |
| T2 | Import resolution in `build.py` | US-2 | AC-2.1, AC-2.2 | T1 | `done` | In-repo import yields an `imports` edge; stdlib and wildcard none |
| T3 | Tests and README | US-3 | AC-3.2, AC-3.3 | T1, T2 | `done` | `tests/test_extractor_kotlin.py`, six-language build test, README updated |

## 5. Risks & Mitigations

The grammar mis-parses some single-line constructs (class bodies on one line); real multi-line code parses cleanly, and the extractor recovers definitions from `ERROR` regions.

## ✅ PLAN GATE

Approved (autonomous mode).
