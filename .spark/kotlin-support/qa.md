# QA Report: kotlin-support

| | |
|---|---|
| **Phase** | Review (hands-on) |
| **Owner** | QA Tester (`/demo-day`) |
| **Input** | Working tree, `.spark/kotlin-support/spec.md` |
| **Status** | `passed` |
| **Round** | 1 |
| **Date** | 2026-11-10 |

Headless tool: no browser surface; QA is done through the CLI on a scratch repo.

## 2. Acceptance Criteria Verification

| AC | Steps performed | Expected | Observed | Result |
|---|---|---|---|---|
| AC-1.1 | Built a scratch repo with `W.kt` and `b.gradle.kts` | Both parsed as kotlin | Two kotlin File nodes in graph.json | ✅ pass |
| AC-1.2 | Built a data class, object, interface, enum and nested class | Class nodes with contains edges | Present (test_extractor_kotlin) | ✅ pass |
| AC-1.3 | Built extension, companion and member functions | Function nodes | Present | ✅ pass |
| AC-2.1 | Cross-file `import` of a class and a top-level function | imports edge | Edge present | ✅ pass |
| AC-2.2 | Stdlib and wildcard imports | No edge | None emitted | ✅ pass |
| AC-3.1 | Two builds, the second with `--full` | graph.json byte-identical | `cmp` identical | ✅ pass |
| AC-3.2 | `uv run pytest` | Green | 393 passed | ✅ pass |
| AC-3.3 | Read the README | Kotlin listed | Listed in both places | ✅ pass |

## ✅ QA GATE

Passed.
