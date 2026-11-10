# Spec: kotlin-support

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Specify |
| **Owner** | Product Owner (`/story-time`), Designer (`/look-and-feel`) |
| **Status** | `approved` |
| **Date** | 2026-11-10 |
| **Ticket** | #34 |
| **Gate comment** | `none` |

<!-- Handoff: read this block first, the numbered sections below by exception. Whoever
     writes to this spec updates it in the same edit that resolves a clarification or
     changes status: overwrite in place, never append. The block holds one current
     state, never a per-round log; a stale block is a defect, not a cosmetic issue. -->

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Summary:** `.kt`/`.kts` files are unparsed `File` nodes today; add a Kotlin extractor (File/Class/Function + best-effort in-repo imports), pinned grammar, tests and docs, the same way Go/Rust were added.
- **Open:** `none`
- **Binding ruling:** §4 User Stories for the current stories; §7 Clarifications for what changed since the last round and why
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

<!-- Budget: ~250 lines. This is a working document that four later phases re-read, not a design
     essay — every line here is paid for again in Plan, Act, Review and QA. If a section can't fit,
     that's a signal about the feature, not about the budget: split it into two features rather than
     growing the spec. Cut prose that restates a table, and background the reader already has. -->

## 1. Problem & Goal

- **Problem:** Code extraction covers Python, TS/JS, Java, Go and Rust (`src/aspark_graph/extractors/`, `constitution.md §9` stack). Every `.kt`/`.kts` file is recorded as an unparsed `File` node (the fallback proven by the unsupported-language test), so `impact` and `story_trace` find no `Class`/`Function` structure and no `imports` edges in Android and Kotlin/JVM repos. Only `declared` plan `files:` links work there.
- **Goal:** Add Kotlin through the existing extractor pattern (bytes in, `FileExtraction` out; per-language module plus registry entry), with best-effort in-repo `imports` edges as for Go and Rust.
- **Success signal:** (1) a built repo with `.kt`/`.kts` files has `Class`/`Function` nodes for them and no `unparsed: true` Kotlin `File` nodes; (2) `tests/test_extractor_kotlin.py` and the multi-language build test pass; (3) double build of a Kotlin repo is byte-identical; (4) `uv run pytest` stays green with no regression to the five existing languages.
- **Why now:** Ticket #34. Kotlin is the default language of Android and a common JVM choice; those repos currently get none of the tool's differentiating value. The cost is bounded by the proven per-language pattern.

## 2. Target Users

- **Primary:** a developer or agent in an aSPARK-managed Android or Kotlin/JVM repo (or a polyglot repo with a Kotlin component) running `story_trace`, `impact` or `/peer-review`'s graph steps.
- **Secondary:** the aSPARK maintainer, who keeps "a language is a registry entry, not new architecture".
- **Not a target:** Kotlin Multiplatform users needing `expect`/`actual` pairing; users of languages other than the six supported (C/C++, Ruby, C#, PHP stay unparsed).

## 3. Assumptions & Open Questions

| # | Assumption / Question | Resolution |
|---|---|---|
| A1 | Kotlin `class`, `data class`, `object`, `interface` and `enum class` all fold into the existing `Class` kind (no new `NodeType`), per the Java and Go/Rust precedent. | Accepted (autonomous decision, 2026-11-10) |
| A2 | `companion object` creates no node of its own; its members nest under the owning class. Rationale: companion is an implementation detail of the owner, and an extra node would add qualname depth with no query value. | Accepted (autonomous decision) |
| A3 | An extension function `fun Recv.name()` is recorded as a `Function` named `Recv.name` with no parent (the receiver type is usually declared elsewhere; a cross-file parent would be a dangling edge, as in Go/Rust A2). | Accepted (autonomous decision) |
| A4 | Local functions (declared inside another function body) are not extracted: implementation detail, same stance as Go/Rust closures. | Accepted (autonomous decision) |
| A5 | Import resolution is best-effort, in-repo only, with no Gradle/build-file parsing. `import a.b.C` resolves through the `package` declared in repo Kotlin files (the Java FQN-index approach, not directory layout, because Kotlin does not require directories to match packages). `import a.b.*` fans out to every file declaring package `a.b`. A member import (`a.b.C.member`, `a.b.topLevelFn`) strips trailing segments until a match is found. | Accepted (autonomous decision) |
| A6 | Imports of the Kotlin/Java stdlib or third-party libraries, and any import that does not resolve, add no edge: absence, not an error. | Accepted (autonomous decision) |
| A7 | Known grammar limit: with tree-sitter-kotlin 1.1.0 a one-line class body (`class A { fun f() {} }` on one line) parses as an error subtree, so its members may be missed. Accepted as best-effort, consistent with the existing tolerant-parse stance; documented, not worked around. | Accepted as risk (autonomous decision) |
| A8 | `.kts` (Gradle/Kotlin scripts) are parsed uniformly with `.kt`; top-level script statements yield no nodes, declared classes/functions do. | Accepted (autonomous decision) |
| A9 | Original phrasing of the ticket ("the same way the existing languages are added", list of node kinds) is a solution shape; it is translated here into the need (structure plus imports for Kotlin) and the shape is kept as the proven precedent. | Recorded |

## 4. User Stories

### US-1 (Must): Extract Kotlin source into File/Class/Function nodes

> As a developer or agent tracing a story or impact in a Kotlin repository, I want `.kt` and `.kts` files parsed into `File`/`Class`/`Function` nodes with `contains` edges, so that Kotlin has the same `extracted`-tier structure as the other five languages instead of unparsed files.

**Acceptance criteria:**

- [ ] AC-1.1: Given a `.kt` file, when the repo is built, then a `File` node is created with `language="kotlin"` and no `unparsed` flag; the same holds for a `.kts` file.
- [ ] AC-1.2: Given a top-level `class`, `data class`, `object`, `interface` or `enum class`, when built, then a `Class` node with that name is created and linked from its `File` node by a `contains` edge with `Confidence.EXTRACTED`.
- [ ] AC-1.3: Given a top-level `fun f()`, when built, then a `Function` node is created, linked from its `File` node by `contains` (`parent=None`).
- [ ] AC-1.4: Given a member `fun` inside a class, object or interface, when built, then a `Function` node is created nested under that class's `Class` node via `contains`.
- [ ] AC-1.5: Given a `companion object` with member functions inside class `Owner`, when built, then no node exists for the companion itself and its functions are `Function` nodes nested under `Owner`.
- [ ] AC-1.6: Given an extension function `fun Recv.name()`, when built, then a `Function` node named `Recv.name` is created with `parent=None` and a `contains` edge from its own `File` node — never an edge to a nonexistent node.
- [ ] AC-1.7: Given a function declared inside another function body, when built, then no node is created for it.
- [ ] AC-1.8: Given a Kotlin file with a `private`/`internal` declaration and a default (public) one, when built, then `Definition.exported` is false for the former and true for the latter.
- [ ] AC-1.9: Given a `.kt` file with only a `package` line or only comments, when built, then a `File` node with zero definitions and no `unparsed` flag is created.
- [ ] AC-1.10: Given an unchanged Kotlin repo, when built twice, then `graph.json` is byte-identical both times.

### US-2 (Should): Best-effort in-repo import resolution for Kotlin

> As a developer tracing impact in a Kotlin repo, I want `imports` edges between repo-local files, so that `impact`'s blast-radius walk can cross Kotlin file boundaries like it does for Python, TS, Java, Go and Rust.

**Acceptance criteria:**

- [ ] AC-2.1: Given file A with `import a.b.C` and file B declaring `package a.b` and a top-level class `C`, when built, then an `imports` edge (`Confidence.EXTRACTED`) links A to B.
- [ ] AC-2.2: Given `import a.b.*` and two repo files declaring `package a.b`, when built, then A has an `imports` edge to each of those files.
- [ ] AC-2.3: Given a member import such as `import a.b.C.member` or `import a.b.topLevelFn`, when built, then trailing segments are stripped until a repo file is matched and the edge is created to that file.
- [ ] AC-2.4: Given an import of a stdlib or third-party name (e.g. `kotlin.collections.List`, `androidx.core.app.X`) with no match in the repo, when built, then no `imports` edge is created and the build succeeds.
- [ ] AC-2.5: Given an import whose name matches no declared package in the repo after stripping, when built, then no edge is created (no guessed target).

### US-3 (Must): Packaging, tests and docs for Kotlin

> As the aSPARK maintainer, I want Kotlin shipped like the other languages (pinned grammar, tested, documented) with existing guarantees intact, so that this feature cannot regress what already shipped.

**Acceptance criteria:**

- [ ] AC-3.1: Given `pyproject.toml`, when inspected, then `tree-sitter-kotlin==1.1.0` is an exact (`==`) pin and `uv.lock` resolves it.
- [ ] AC-3.2: Given the test tree, when listed, then `tests/test_extractor_kotlin.py` exists and covers class kinds, functions, companion members, extension functions, local functions, visibility, imports (exact, wildcard, member, unresolved) and the empty file, at the granularity of `test_extractor_java.py`.
- [ ] AC-3.3: Given the multi-language build test, when run, then it includes a Kotlin file alongside Python, TS, JS, Java, Go and Rust, and every file has a language-tagged `File` node with definitions and none is `unparsed`.
- [ ] AC-3.4: Given a Kotlin extractor that is not registered (the early-cut path), when built, then `.kt` files are recorded as `unparsed: true` `File` nodes and the build succeeds; a file with an extension outside the known-language table (e.g. `.rb`) is skipped exactly as before this change.
- [ ] AC-3.5: Given the README, when read, then "Supported languages" and the design guarantees list Kotlin, and the README or CLAUDE.md states the one-line-class-body grammar limit (A7).
- [ ] AC-3.6: Given a Kotlin-containing repo, when the same `find_nodes`/`impact`/`story_trace` query runs via CLI and via MCP, then results are identical, with no Kotlin-specific code in `cli.py` or `server.py`.
- [ ] AC-3.7: Given the full suite, when `uv run pytest` runs, then it passes with zero regressions in the existing extractor tests.

## 5. Non-Functional Requirements

| # | Category | Requirement (measurable) | How it's verified |
|---|---|---|---|
| NFR-1 | Determinism (inherited) | The Kotlin grammar is pinned `==`; a double build of a Kotlin fixture is byte-identical; a stash round-trip shows a repo with no Kotlin files builds the same `graph.json` before and after the change. | /peer-review: double-build test, stash round-trip |
| NFR-2 | No dangling edges / honest absence (inherited) | Every `contains`/`imports` edge endpoint exists as a node; extension functions and unresolved imports yield no dangling edge or guessed edge (AC-1.6, AC-2.4, AC-2.5). | /peer-review: edge-integrity check on Kotlin fixtures |
| NFR-3 | Confidence consistency (inherited) | All new `contains`/`imports` edges carry `Confidence.EXTRACTED`; no new tier. | /peer-review: inspect `graph.json` |
| NFR-4 | CLI/MCP parity, CLI lens (inherited) | Dispatch stays registry-driven; no Kotlin branching in `cli.py`/`server.py`; a Kotlin file that fails to parse never produces a traceback (malformed source is handled by tolerant parse, no new error path). | /peer-review: diff adapters; parity tests; build a malformed `.kt` |
| NFR-5 | Performance | The incremental-build benchmark (slow) passes unmodified with the Kotlin extractor registered. | /peer-review: `uv run pytest -m slow` |
| NFR-6 | Reliability / install | The wheel installed in a fresh venv without the lock still boots `serve` with the Kotlin grammar present, and the sdist manifest test still passes. | /peer-review: `tests/test_fresh_install.py`, `tests/test_packaging.py` |
| NFR-7 | Security & privacy | N/A — no new network, credential or execution surface; confinement and the 5 MB per-file cap apply to `.kt` files as to all others. | N/A |
| NFR-8 | Accessibility / observability | N/A — headless tool; Kotlin files are distinguishable through the existing `language` field. | N/A |

## 6. Out of Scope

- **Kotlin Multiplatform `expect`/`actual` pairing** (ticket).
- **Annotation processing** (ticket): annotations are not interpreted or linked.
- **A `Class` sub-kind** (data/object/enum/interface distinct from class): folded into `Class` (A1).
- **A node for `companion object`**, local functions, lambdas and property-bound function values (A2, A4).
- **Extension-function parenting under the receiver type** via a cross-file type index (A3).
- **Gradle/`build.gradle.kts` module-aware import resolution**, and stdlib/third-party import resolution (A5, A6).
- **`calls` edges and inheritance/`implements` edges**: no existing language emits them.
- **Working around the one-line class-body grammar limit** (A7), or upgrading the grammar to fix it.
- **Any further language** beyond Kotlin.

## 7. Clarifications

| # | Date | Question | Resolution |
|---|---|---|---|
| C1 | 2026-11-10 | (Scope) How do Kotlin's five type declaration forms map to node kinds? | All fold into `Class` (A1). |
| C2 | 2026-11-10 | (Data) How are companion members and extension functions represented, given `contains` is file-scoped? | Companion members nest under the owner; extension functions are `Recv.name` with no parent (A2, A3, AC-1.5, AC-1.6). |
| C3 | 2026-11-10 | (Integrations) How do imports resolve without build-file parsing, since Kotlin packages need not match directories? | Via declared `package` index; wildcard fans out; member imports strip trailing segments; unresolved adds no edge (A5, A6). |
| C4 | 2026-11-10 | (Edge cases) What about grammar failures on one-line class bodies and malformed source? | Accepted best-effort tolerant parse; limit documented (A7, AC-3.5). |
| C5 | 2026-11-10 | (Data) How are `.kts` and empty files treated? | `.kts` parsed uniformly; empty file is a known, empty `File` node (A8, AC-1.9). |
| C6 | 2026-11-10 | (Roles, UX) Any auth/roles or UI states? | N/A — local headless tool. |
| C7 | 2026-11-10 | (Out of scope) Is KMP or annotation processing included? | No, per ticket (§6). |

## 8. Design Review

**N/A — headless CLI/MCP tool; no UI.**

- **Overall impression:** N/A (no visual UI)
- **Heuristics findings:** N/A
- **Accessibility notes:** N/A (no visual UI)
- **Design risks & required changes:** None

---

## ✅ SPEC GATE

*All boxes checked → `/sprint-plan` may start. Any box open → back to `/story-time` or `/look-and-feel`.*

- [x] Problem, goal and success signal are concrete (no buzzwords, no "everyone")
- [x] Every story has testable Given/When/Then acceptance criteria
- [x] Stories are prioritized (MoSCoW) and at least one is a Must
- [x] Non-functional requirements are stated and measurable (or marked N/A with reason)
- [x] Clarify pass done: no ambiguity left unresolved or unparked
- [x] Open questions are resolved or explicitly accepted as risk
- [x] Out-of-scope section is filled (something was consciously cut)
- [x] Constitution (`.spark/constitution.md`) respected, or conflicts recorded as open questions
- [x] Design review done for UI-facing features (or marked N/A with reason)
- [x] Line budget respected: Ist ~125 / Soll ~250 (excluding HTML comments) — self-reported
- [x] Status set to `approved` by the user *(autonomous mode, 2026-11-10)*
