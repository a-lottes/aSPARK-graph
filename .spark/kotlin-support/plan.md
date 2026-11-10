# Plan: kotlin-support

| | |
|---|---|
| **Phase** | Plan |
| **Owner** | Engineering Manager (`/sprint-plan`) |
| **Input** | `.spark/kotlin-support/spec.md` (`approved`) |
| **Status** | `approved` |

## 3. Task Breakdown

| # | Task | Story | Covers (AC / NFR) | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|---|
| T1 | `code_kotlin.py` extractor, registry + extension map, pin `tree-sitter-kotlin==1.1.0` | US-1 | AC-1.1, AC-1.3 | – | `done` | extractor tests pass; pin in pyproject and uv.lock |
| T2 | Kotlin import resolution in `build.py` (package + top-level name index) | US-2 | AC-2.1 | T1 | `done` | build test shows resolved edge, no edge for wildcard/missing |
| T3 | Tests and README | US-1 | AC-1.4, AC-1.5 | T1 | `done` | suite green; README lists Kotlin |

---

## ✅ PLAN GATE

- [x] Spec status is `approved`
- [x] Every task maps to a user story
