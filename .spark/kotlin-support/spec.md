# Spec: kotlin-support

| | |
|---|---|
| **Phase** | Specify |
| **Owner** | Product Owner (`/story-time`) |
| **Status** | `approved` |
| **Source** | Issue #23 |

## 1. Problem & Goal

Kotlin files are unparsed `File` nodes, so `impact`/`story_trace` find no structure in Android and Kotlin/JVM repos. Add Kotlin the way Go and Rust were added.

## 4. User Stories

### US-1 (Must): Extract Kotlin source into File/Class/Function nodes

**Acceptance criteria:**

- [ ] AC-1.1: Given `.kt` and `.kts` files, when the repo is built, then `File`, `Class` (class, data class, object, interface, enum class) and `Function` (fun, extension, companion members) nodes exist with `contains` edges.
- [ ] AC-1.3: The `tree-sitter-kotlin` grammar is pinned `==` in `pyproject.toml`.
- [ ] AC-1.4: README "Supported languages" and the design guarantees list Kotlin.
- [ ] AC-1.5: `tests/test_extractor_kotlin.py` exists and the multi-language build test covers Kotlin.

### US-2 (Should): Best-effort in-repo import resolution for Kotlin

**Acceptance criteria:**

- [ ] AC-2.1: Given an `import` naming a class or top-level function declared in a repo file, when built, then an `imports` edge links the files; wildcard and unresolvable imports yield no edge.

## 6. Out of Scope

Kotlin Multiplatform `expect`/`actual` pairing, annotation processing.

---

## ✅ SPEC GATE

- [x] Problem, goal and success signal are concrete
- [x] Every story has testable acceptance criteria
- [x] Out-of-scope section is filled
