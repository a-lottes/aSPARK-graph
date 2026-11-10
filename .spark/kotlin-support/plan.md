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

The pinned grammar needs a line break after `{` and before `}` of a body: one-line bodies (`class X { companion object { const val T = 1 } }`) parse as ERROR and, unrecovered, silently erase every later definition in the file. Mitigation: retry the parse on a same-length copy with those spaces turned into newlines (original line numbers are kept); ERROR regions are never walked (recovered members would be mis-parented); the retry copy blanks comments and skips string/char/backtick literals verbatim (so braces inside them are neither rewritten nor invented and no identifier is edited); a file the grammar still cannot parse is marked `partial: true` on its `File` node, named on stderr by `build` and in the MCP `build_graph` result (`partial_files`), and documented in the README. Residual: a partial file may lack definitions (honest absence). Deviation recorded: this fix-round also made Kotlin imports fan out to every file defining the same top-level name (extension overloads).

## ✅ PLAN GATE

Approved (autonomous mode).
