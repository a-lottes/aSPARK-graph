# Spec — Kotlin support (issue #13)

| | |
|---|---|
| Status | approved |

## US-1 Kotlin structure in the graph
- AC-1.1 `.kt`/`.kts` files yield `File`, `Class` (class, data/sealed/enum class, object, interface) and `Function` nodes (incl. extension and companion members) with `contains` edges.
- AC-1.2 `import` directives yield best-effort in-repo `imports` edges (star imports and out-of-repo imports yield none).
- AC-1.3 `tree-sitter-kotlin` pinned `==1.1.0`; rebuild stays byte-identical.
- AC-1.4 README "Supported languages" and design guarantees list Kotlin.

Out of scope: `expect`/`actual` pairing, annotation processing.
Known limit: the pinned grammar mis-parses one-line class bodies (`class A { fun f() {} }`).
