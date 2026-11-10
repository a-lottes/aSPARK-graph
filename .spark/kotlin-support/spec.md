# Spec: kotlin-support

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Specify |
| **Owner** | Product Owner (`/story-time`), Designer (`/look-and-feel`) |
| **Status** | `approved` |
| **Date** | 2026-11-10 |
| **Ticket** | `#13` |
| **Gate comment** | `skipped, autonomous Factory run, no gh access` |

<!-- Handoff: read this block first, the numbered sections below by exception. Whoever
     writes to this spec updates it in the same edit that resolves a clarification or
     changes status: overwrite in place, never append. The block holds one current
     state, never a per-round log; a stale block is a defect, not a cosmetic issue. -->

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Summary:** Kotlin `.kt`/`.kts` files are unparsed `File` nodes today; goal is `File`/`Class`/`Function` nodes, `contains` edges and best-effort in-repo `imports` edges, like Go and Rust.
- **Open:** `none`
- **Binding ruling:** §4 User Stories for the current stories; §7 Clarifications for what changed since the last round and why
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Problem & Goal

- **Problem:** Code extraction covers Python, TypeScript/JavaScript, Java, Go and Rust (`constitution.md §3`). In an Android or Kotlin/JVM repo every `.kt`/`.kts` file is an `unparsed: true` `File` node, so `impact` and `story_trace` have no `extracted`-tier structure or `imports` edges to walk. Only `declared` links from a plan `files:` note work.
- **Goal:** Kotlin is extracted the same way the existing languages are: `File`, `Class` and `Function` nodes with `contains` edges, plus best-effort in-repo `imports` edges.
- **Success signal:** a Kotlin fixture builds with no `unparsed` Kotlin `File` nodes; `tests/test_extractor_kotlin.py` and the extended multi-language build test pass; graphs of repos without Kotlin files are byte-identical to pre-change output.
- **Why now:** Issue #13 is the open request; the extractor pattern is proven by Go and Rust, so the cost is small.

## 2. Target Users

- **Primary:** a developer or agent on an Android or Kotlin/JVM repo carrying `.spark/` trails, running `story_trace`, `impact` or `/peer-review`'s graph steps.
- **Not a target:** Kotlin Multiplatform users needing `expect`/`actual` pairing; users of any other still-unsupported language.

## 3. Assumptions & Open Questions

| # | Assumption / Question | Resolution |
|---|---|---|
| A1 | Kotlin class, data class, object, interface and enum class all fold into the existing `Class` kind (no new `NodeType`), as Java interfaces/enums and Go/Rust types already do. | Accepted (Factory, 2026-11-10) |
| A2 | Spike fact: tree-sitter-kotlin 1.1.0 parses `.kt` and `.kts`. It mis-parses a class body opened and closed on one line (`class A { fun f() {} }`). | Accepted as a documented known limit (AC-1.7) |
| A3 | Import resolution is best-effort and in-repo only, like Go/Rust: no Gradle/manifest parsing. Aliases (`import a.B as C`) resolve by the original path; the alias is ignored. Star imports (`import a.*`) are not resolved. | Accepted |
| A4 | Companion-object members nest under the enclosing class. Local functions (inside another function body) are not captured. | Accepted |
| A5 | The issue's original phrasing "added the same way the existing languages are" is read as a constraint on pattern (registry entry, no adapter changes), not a design. | Accepted |

## 4. User Stories

### US-1 (Must): Extract Kotlin source into File/Class/Function nodes and imports

> As a developer or agent tracing a story or impact in an Android or Kotlin/JVM repo, I want `.kt` and `.kts` files parsed into `File`/`Class`/`Function` nodes with `contains` edges and in-repo `imports` edges, so that Kotlin has the same `extracted`-tier structure as the other supported languages instead of showing up as unparsed.

**Acceptance criteria:**

- [ ] AC-1.1: Given a `.kt` file and a `.kts` file, when the repo is built, then each yields a `File` node with `language="kotlin"` and no `unparsed` flag; an empty `.kt` file yields a `File` node with zero definitions.
- [ ] AC-1.2: Given top-level `class`, `data class`, `object`, `interface` and `enum class` declarations, when built, then each becomes a `Class` node linked from its `File` via a `contains` edge with `Confidence.EXTRACTED`.
- [ ] AC-1.3: Given a top-level `fun` and an extension function (`fun String.f()`), when built, then each becomes a `Function` node contained by its `File`.
- [ ] AC-1.4: Given member functions of a class, and functions in a `companion object` of that class, when built, then each is a `Function` node nested under the enclosing class's `Class` node via `contains`; a function local to another function's body produces no node.
- [ ] AC-1.5: Given an `import a.b.C` directive whose path unambiguously matches one in-repo Kotlin file's declared package plus a declaration in it, when built, then an `imports` edge (`Confidence.EXTRACTED`) links the importing `File` to that file; an aliased import resolves by its original path.
- [ ] AC-1.6: Given an import of an external or standard-library name, a star import, or a path matching more than one in-repo file, when built, then no `imports` edge is created for it, and the build does not error.
- [ ] AC-1.7: Given `class A { fun f() {} }` with the body opened and closed on one line, when built, then the build succeeds without error; the missing or misplaced member is a documented known limit (README), not a defect.
- [ ] AC-1.8: Given a repo containing Python, TS, JS, Java, Go, Rust and Kotlin files in one build, when built, then every file is language-tagged with its definitions and none is `unparsed`; a file with an unsupported extension (e.g. `.rb`) is still `unparsed: true`.
- [ ] AC-1.9: Given an unchanged repo with Kotlin files, when built twice, then `graph.json` is byte-identical; and given a repo with no Kotlin files, its `graph.json` is byte-identical to that built by the pre-change code.
- [ ] AC-1.10: Given the README, when read, then "Supported languages" and the design guarantees list Kotlin, and the existing README language-count test still passes.

## 5. Non-Functional Requirements

| # | Category | Requirement (measurable) | How it's verified |
|---|---|---|---|
| NFR-1 | Determinism | The tree-sitter Kotlin grammar is pinned `==` in `pyproject.toml` (1.1.0); AC-1.9 holds, proven against pre-change code via a stash round-trip on a non-Kotlin fixture. | /peer-review |
| NFR-2 | No dangling edges | Every `contains`/`imports` edge endpoint exists as a node in Kotlin fixtures; ambiguous or unresolved imports yield no edge. | /peer-review |
| NFR-3 | CLI ≡ MCP parity | No Kotlin-specific code is added to `cli.py` or `server.py`; the parity test stays green. | /peer-review diff + test suite |
| NFR-4 | Test coverage | `tests/test_extractor_kotlin.py` at `test_extractor_java.py` granularity; `uv run pytest` green; `pytest -m slow` (incremental benchmark, sdist manifest, fresh-install `serve` boot) green. | /peer-review |
| NFR-5 | Security & privacy | N/A — no new network, credential or execution surface; repo confinement and build bounds apply unchanged. | N/A |
| NFR-6 | Accessibility / UX | N/A — headless tool, no UI. | N/A |
| NFR-7 | CLI lens | Domain errors stay one-line messages with non-zero exit; malformed Kotlin source never produces a traceback (tolerant tree-sitter parse, same as other languages). | /peer-review |

## 6. Out of Scope

- Kotlin Multiplatform `expect`/`actual` pairing.
- Annotation processing.
- Gradle (`build.gradle(.kts)`) or manifest parsing for import resolution; star-import resolution; import-alias tracking.
- `calls` edges, inheritance/implements edges, and any new node type for object/data/enum kinds.
- Local functions, lambdas and anonymous objects as nodes.
- Working around the single-line class body mis-parse (documented only).
- Any other new language.

## 7. Clarifications

| # | Date | Question | Resolution |
|---|---|---|---|
| C1 | 2026-11-10 | (Scope) Do Kotlin kinds need new node types? | No: fold into `Class` (A1). |
| C2 | 2026-11-10 | (Edge cases) How are companion members, local functions and extension functions treated? | Companion members nest under the class; extensions are top-level `Function`s; local functions are not captured (A4, AC-1.3/1.4). |
| C3 | 2026-11-10 | (Integrations) Star imports and aliases? | Star imports unresolved; alias ignored, original path used (A3, AC-1.5/1.6). |
| C4 | 2026-11-10 | (Error cases) Single-line class body mis-parse? | Known limit, documented, no workaround (A2, AC-1.7). |
| C5 | 2026-11-10 | (Regression) Effect on non-Kotlin repos? | Graph byte-identical to pre-change (AC-1.9, NFR-1). |
| C6 | 2026-11-10 | (Roles, UX) Any auth or UI states? | N/A, local headless tool. |

## 8. Design Review

N/A — headless CLI/MCP tool: no UI, no new command or tool, and no output-format change beyond a new `language` value (`"kotlin"`).

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
- [x] Line budget respected: Ist 118 / Soll ~250 (excluding HTML comments) — self-reported, no linter checks this
- [x] Status set to `approved` by the user (Factory mode authorises it, autonomous run, 2026-11-10)
