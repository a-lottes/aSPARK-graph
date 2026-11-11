# Spec: kotlin-support

| | |
|---|---|
| **Phase** | Specify |
| **Owner** | Product Owner (/story-time) |
| **Status** | `approved` |
| **Date** | 2026-11-11 |

## 1. Problem & Goal

Kotlin files (`.kt`, `.kts`) are unparsed `File` nodes, so `impact` and `story_trace` see no structure in Android and Kotlin/JVM repos (issue #36). Add Kotlin the way Go and Rust were added.

## 4. User Stories

### US-1 (Must): Extract Kotlin source into File/Class/Function nodes

- [ ] AC-1.1: Given a `.kt` or `.kts` file, when the repo is built, then a `File` node with `language="kotlin"` exists and is not flagged unparsed.
- [ ] AC-1.2: Given class, data class, object, interface and enum class declarations, then each becomes a `Class` node with a `contains` edge from its `File`.
- [ ] AC-1.3: Given `fun` declarations (top-level, member, extension, companion object members), then each becomes a `Function` node; companion members nest under the enclosing class and extension functions are `Receiver.name`.

### US-2 (Should): Best-effort in-repo Kotlin imports

- [ ] AC-2.1: Given an `import` that resolves to a class or top-level function in the repo, then an `imports` edge links the files; wildcard imports link the package's files; stdlib/third-party imports yield no edge.

### US-3 (Must): Existing guarantees still hold

- [ ] AC-3.1: The Kotlin grammar is pinned `==` in `pyproject.toml`, a double build of a repo including Kotlin is byte-identical, and the README lists Kotlin.

## 6. Out of Scope

Kotlin Multiplatform `expect`/`actual` pairing and annotation processing.

## ✅ SPEC GATE

- [x] Approved (autonomous mode, recommended option)
