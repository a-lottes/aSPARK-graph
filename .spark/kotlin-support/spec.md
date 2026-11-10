# Spec: kotlin-support

| | |
|---|---|
| **Phase** | Specify |
| **Owner** | Product Owner (`/story-time`) |
| **Status** | `approved` |
| **Date** | 2026-11-10 |
| **Source** | Issue #29 (duplicates #13, #23 per `.factory/tickets.md`) |

## 1. Problem & Goal

Kotlin files are recorded as unparsed `File` nodes, so `impact`/`story_trace` find no structure in Android and Kotlin/JVM repos. Add Kotlin the way Go and Rust were added (`go-rust-support`).

## 2. User Stories

### US-1 (Must): Kotlin structure
As an agent working in a Kotlin repo, I want `.kt`/`.kts` files parsed into `File`/`Class`/`Function` nodes with `contains` edges, so that `impact` reaches Kotlin code.
- [ ] AC-1.1: `class`, `data class`, `object`, `interface`, `enum class` become `Class` nodes.
- [ ] AC-1.2: `fun`, extension functions and companion-object members become `Function` nodes, nested under their owner via `contains`.
- [ ] AC-1.3: `.kts` files are parsed; an empty `.kt` file is not marked unparsed.

### US-2 (Must): Kotlin imports
- [ ] AC-2.1: An `import` of an in-repo class or top-level function yields a best-effort `imports` edge (`extracted`).
- [ ] AC-2.2: External, wildcard and ambiguous imports yield no edge.

### US-3 (Must): Pinned, deterministic, documented
- [ ] AC-3.1: `tree-sitter-kotlin` is pinned with `==` in `pyproject.toml`.
- [ ] AC-3.2: Double build of a Kotlin repo is byte-identical; graphs of non-Kotlin repos are unchanged.
- [ ] AC-3.3: `tests/test_extractor_kotlin.py` exists; the multi-language build test covers Kotlin.
- [ ] AC-3.4: README "Supported languages" and design guarantees list Kotlin.

## 3. Out of scope
Kotlin Multiplatform `expect`/`actual` pairing, annotation processing, wildcard-import resolution, `typealias`.
