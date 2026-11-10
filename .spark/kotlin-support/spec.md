# Spec: kotlin-support

| | |
|---|---|
| **Phase** | Specify |
| **Owner** | Product Owner (`/story-time`) |
| **Status** | `approved` |
| **Date** | 2026-11-10 |

## 1. Problem & Goal

- **Problem:** Kotlin files (`.kt`, `.kts`) are recorded as unparsed `File` nodes, so `impact` and `story_trace` find no structure in Android and Kotlin/JVM repos (issue #31).
- **Goal:** Add Kotlin the same way Go and Rust were added: a pure extractor, a registry entry, best-effort in-repo `imports` resolution, an exactly pinned grammar.

## 4. User Stories

### US-1 (Must): Extract Kotlin source into File/Class/Function nodes

- [ ] AC-1.1: Given `.kt` and `.kts` files, when the repo is built, then each is a parsed `File` node (not `unparsed`) with `language="kotlin"`.
- [ ] AC-1.2: Class, data class, object, interface and enum class declarations become `Class` nodes with `contains` edges; nested types nest under their parent.
- [ ] AC-1.3: `fun` declarations become `Function` nodes, including extension functions (named by function name) and companion object members, with `contains` edges.

### US-2 (Should): Best-effort in-repo import resolution

- [ ] AC-2.1: Given an `import` of a top-level class or function defined in another repo file, when built, then a File -> File `imports` edge is emitted.
- [ ] AC-2.2: Stdlib, third-party and wildcard imports emit no edge.

### US-3 (Must): Pinning, tests and docs

- [ ] AC-3.1: `tree-sitter-kotlin` is pinned with `==` in `pyproject.toml`; the rebuild stays byte-identical.
- [ ] AC-3.2: `tests/test_extractor_kotlin.py` exists at the granularity of `test_extractor_java.py`; the multi-language build test covers Kotlin.
- [ ] AC-3.3: README "Supported languages" and the design guarantees list Kotlin.

## 6. Out of Scope

Kotlin Multiplatform `expect`/`actual` pairing, annotation processing.

## ✅ SPEC GATE

Approved (autonomous mode, recommended option).
