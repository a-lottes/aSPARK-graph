# Plan: kotlin-support

| | |
|---|---|
| **Phase** | Plan |
| **Owner** | Engineering Manager (`/sprint-plan`) |
| **Input** | `.spark/kotlin-support/spec.md` (`approved`) |
| **Status** | `approved` |
| **Date** | 2026-11-10 |

## 1. Architecture Decision

Repeat the proven language pattern: pure extractor `code_kotlin.py`, `EXTENSION_LANGUAGE` + registry entries, an FQN index + resolver in `build.py`. Grammar `tree-sitter-kotlin==1.1.0` (newest; 1.0.0/1.0.1 probed and parse the same shapes). Companion objects become `Class` `<Outer>.Companion`. Extension functions are qualified by receiver type (`String.shout`), top-level, like Go foreign-receiver methods. Imports index both top-level classes and top-level functions (Kotlin imports name either); nested-class imports fall back to the outer class by stripping trailing segments; duplicate FQNs are dropped as ambiguous.
Rejected: wildcard-import fan-out (package ≠ file, noisy); regex parsing (breaks the tree-sitter convention).

## 2. Task Breakdown

| # | Task | Story | Covers (AC / NFR) | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|---|
| T1 | Pin grammar; extension mapping + registry | US-3 | AC-3.1 | – | `done` | `tree-sitter-kotlin==1.1.0` pinned, `.kt`/`.kts` map to `kotlin`. |
| T2 | `code_kotlin.py` extractor | US-1 | AC-1.1, AC-1.2, AC-1.3 | T1 | `done` | Class kinds, functions, extension and companion members extracted. |
| T3 | `build.py` Kotlin import index/resolver | US-2 | AC-2.1, AC-2.2 | T2 | `done` | In-repo imports yield edges; external/wildcard/ambiguous yield none. |
| T4 | `tests/test_extractor_kotlin.py`; multi-language + determinism tests | US-3 | AC-3.2, AC-3.3 | T3 | `done` | Tests green, double build byte-identical. |
| T5 | README, test_readme, CLAUDE.md | US-3 | AC-3.4 | T4 | `done` | Docs list Kotlin. |

## 3. Risks
- R1: grammar 1.1.0 mis-parses single-line `class A { fun m() {} }` (`{}` read as enum body, yields ERROR but the function is still recovered; members of such one-liners may lose nesting). Multi-line bodies, the realistic case, parse cleanly. Documented as known limit.
