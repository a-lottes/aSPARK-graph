# Spec: kotlin-support

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Specify |
| **Owner** | Product Owner (`/story-time`), Designer (`/look-and-feel`) |
| **Status** | `approved` |
| **Date** | 2026-11-10 |
| **Ticket** | #25 |
| **Gate comment** | skipped, autonomous run |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Summary:** Kotlin (`.kt`/`.kts`) is an unparsed `File` today; add it as a sixth code language (File/Class/Function + `contains`, best-effort in-repo `imports`) the same way Go/Rust were added.
- **Open:** `none`
- **Binding ruling:** §4 User Stories for the current stories; §7 Clarifications for what changed since the last round and why
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Problem & Goal

*Seeded from issue #25 (https://github.com/a-lottes/aSPARK-graph/issues/25). Pattern precedent: `.spark/go-rust-support/spec.md`. System facts (stack, extractor registry, module layout) from `constitution.md §9`; the feature touches the extractor area, so `build.py`'s import resolution was also read.*

- **Problem:** Code extraction covers Python, TS/JS, Java, Go and Rust. A `.kt`/`.kts` file is recorded as an `unparsed: true` `File` node, so `impact` and `story_trace` see no `Class`/`Function` structure and no `imports` edges in Android and Kotlin/JVM repos. Only `declared` links from a plan `files:` note work there. The developers and agents who run those two queries on such repos feel this.
- **Goal:** Kotlin source becomes `File`/`Class`/`Function` nodes with `contains` edges and best-effort in-repo `imports` edges, through the existing extractor pattern, with no new node types, edge types or adapter code.
- **Success signal:** (1) a built repo with `.kt`/`.kts` files has no `unparsed` Kotlin `File` nodes and has `Class`/`Function` nodes for them; (2) `tests/test_extractor_kotlin.py` (Java-extractor granularity) and the multi-language build test, which now includes Kotlin, pass; (3) a double build is byte-identical; (4) `uv run pytest` is green with no regression in the five existing languages.
- **Why now:** The language-addition pattern is proven twice (Go, Rust) and costs one extractor, one resolver and one pinned grammar. Not building it leaves Kotlin repos at declared-only precision. If never built: nothing breaks, Kotlin users just get the weaker tool; honest, so this stays an S-sized slice.

## 2. Target Users

- **Primary:** a developer or agent in an aSPARK-managed Android or Kotlin/JVM repo (or a polyglot repo with a Kotlin module) running `story_trace`, `impact` or `/peer-review`'s graph steps.
- **Secondary:** the aSPARK-graph maintainer, who wants the language list to grow by data-driven registry entries only.
- **Not a target:** other languages (still unparsed); Kotlin Multiplatform users needing `expect`/`actual` pairing; users wanting `calls` edges (no language emits them).

## 3. Assumptions & Open Questions

| # | Assumption / Question | Resolution |
|---|---|---|
| A1 | Class, data class, sealed class, enum class, interface, `object` and `companion object` all fold into the existing `Class` kind (no new `NodeType`), per the Java/Go/Rust precedent. | Accepted (autonomous), see C1. |
| A2 | A `companion object` is a `Class` node (named `Companion` unless declared otherwise) nested under its host; its members nest under it (`Host.Companion.m`). | Accepted (autonomous), see C2. |
| A3 | An extension function is named `<ReceiverType>.<name>`. At top level it is a top-level `Function` on its own file (`parent=None`), never a `contains` edge to a node that does not exist (mirrors Go/Rust cross-file rule). Inside a class it nests under that class. | Accepted (autonomous), see C3. |
| A4 | `Definition.exported` is true unless the declaration carries the `private` modifier. Kotlin's default visibility is public; `internal`/`protected` count as exported. | Accepted (autonomous). |
| A5 | Import resolution is best-effort, in-repo only, no Gradle/manifest parsing. An import of a fully qualified name resolves to the file declaring that top-level class/object/function in that declared `package`. An alias (`import a.B as C`) resolves on `a.B`. An import naming a nested class resolves to nothing unless the whole qualified name is a top-level declaration. | Accepted (autonomous), see C4. |
| A6 | Wildcard imports (`import a.b.*`) resolve to **no edge**: one directive can span many files, and guessing one is a wrong link. | Accepted; known fact, AC-2.3. |
| A7 | An import whose qualified name matches more than one in-repo file resolves to no edge (honest absence; constitution §1). | Accepted, AC-2.4. |
| A8 | The pinned tree-sitter Kotlin grammar parses conventionally formatted multi-line Kotlin correctly but misparses some one-line forms (e.g. `class A { fun m() {} }`). The extractor stays error-tolerant and collects what it can; ACs are written against multi-line source. The one-line limit is documented, not fixed. | Accepted as known limit; see §6 and C5. |
| A9 | Kotlin `typealias`, top-level `val`/`var` and local/anonymous functions produce no nodes. Only `class`-like and `fun` declarations are named API surface. | Accepted, see §6. |
| A10 | The README states no language count (an existing test forbids the word "six"); Kotlin is added to the "Supported languages" list and the design-guarantees list by name. | Accepted, AC-4.1. |

## 4. User Stories

### US-1 (Must): Extract Kotlin source into File/Class/Function nodes

> As a developer or agent tracing a story or impact in a Kotlin repo, I want `.kt` and `.kts` files parsed into `File`/`Class`/`Function` nodes with `contains` edges, so that Kotlin has the same `extracted`-tier structure as the other five languages instead of showing up as unparsed.

**Acceptance criteria:**

- [ ] AC-1.1: Given a `.kt` file with a `package` directive, when the repo is built, then a `File` node exists with `language="kotlin"`, the package populated and no `unparsed` flag.
- [ ] AC-1.2: Given a `.kts` script containing a `fun` declaration, when built, then it is also a `language="kotlin"` `File` node, not unparsed, and the function is a `Function` node linked by `contains` from the file.
- [ ] AC-1.3: Given top-level `class`, `data class`, `sealed class`, `enum class`, `interface` and `object` declarations in a multi-line file, when built, then each becomes a `Class` node linked from its `File` by a `contains` edge with `Confidence.EXTRACTED`.
- [ ] AC-1.4: Given a top-level `fun`, when built, then a `Function` node is linked from its `File` via `contains` (`parent=None`).
- [ ] AC-1.5: Given a member `fun` in a class body, when built, then it is a `Function` node nested under that class's `Class` node (`parent` = class qualname), and a nested class nests under its outer class.
- [ ] AC-1.6: Given `class Host { companion object { fun make() {} } }` written multi-line, when built, then a `Class` named `Companion` is nested under `Host` and `make` is a `Function` under `Host.Companion`. A named companion uses its declared name.
- [ ] AC-1.7: Given a top-level extension function `fun String.shout()`, when built, then a `Function` named `String.shout` exists with a `contains` edge from its own `File` (`parent=None`); no edge points at a node id absent from the graph.
- [ ] AC-1.8: Given a `private` declaration and a non-private one, when built, then `Definition.exported` is false for the first and true for the second.
- [ ] AC-1.9: Given an empty `.kt` file, or one with only a `package` directive and comments, when built, then a `File` node with zero definitions exists and is not `unparsed`.
- [ ] AC-1.10: Given syntactically invalid Kotlin, when built, then the build does not raise; declarations the parser can still recognise are extracted, and no traceback or new error class is introduced.
- [ ] AC-1.11: Given an unchanged Kotlin repo, when built twice, then `graph.json` is byte-identical.

### US-2 (Should): Best-effort in-repo import resolution for Kotlin

> As a developer tracing impact in a Kotlin repo, I want `imports` edges between repo-local `.kt` files, so that `impact` can cross Kotlin file boundaries as it does for Go and Rust, without parsing Gradle files.

**Acceptance criteria:**

- [ ] AC-2.1: Given file A has `import com.example.util.Helper` and file B declares `package com.example.util` with a top-level `Helper` class, object, interface or function, when built, then an `imports` edge (`Confidence.EXTRACTED`) links A's `File` to B's `File`.
- [ ] AC-2.2: Given an import of a stdlib or third-party name not declared in the repo (e.g. `kotlinx.coroutines.launch`), when built, then no `imports` edge is created and no error is raised.
- [ ] AC-2.3: Given a wildcard import `import com.example.util.*`, when built, then no `imports` edge is created for it.
- [ ] AC-2.4: Given an import whose qualified name matches declarations in more than one repo file, when built, then no `imports` edge is created for it.
- [ ] AC-2.5: Given `import com.example.util.Helper as H`, when built, then the edge resolves on `com.example.util.Helper`, same as the un-aliased form.

### US-3 (Must): Existing multi-language guarantees still hold

> As the maintainer, I want the shipped guarantees to keep holding once Kotlin is added, so that this feature cannot regress what already shipped.

**Acceptance criteria:**

- [ ] AC-3.1: Given a repo with at least one file each of Python, TS, JS, Java, Go, Rust and Kotlin, when built once, then every file is a language-tagged `File` node with its `Class`/`Function` definitions, none `unparsed`.
- [ ] AC-3.2: Given a file with an extension no extractor knows (e.g. `.rb`), when built, then it is handled exactly as before this change (no `File` node, build succeeds); only a known language with no registered extractor is an `unparsed: true` `File`.
- [ ] AC-3.3: Given the full suite, when `uv run pytest` runs, then it passes with no regression in the existing extractor tests.
- [ ] AC-3.4: Given a repo containing Kotlin, when the same `find_nodes`/`impact`/`story_trace` query runs through the CLI and the MCP tool, then both return identical results, with no Kotlin-specific branch in `cli.py` or `server.py`.
- [ ] AC-3.5: Given a repo already built before this change, when rebuilt incrementally after Kotlin is registered, then a `.kt` file is parsed once (no stale unparsed entry survives from the parse cache) and unchanged files of other languages produce unchanged graph entries.

### US-4 (Must): Kotlin is documented and pinned

> As a user choosing whether aspark-graph fits my repo, I want the README to list Kotlin, so that I know it is supported.

**Acceptance criteria:**

- [ ] AC-4.1: Given the README, when read, then "Supported languages" and the design-guarantees list both name Kotlin (`.kt`, `.kts`), and neither states a numeric language count (the existing doc test passes).
- [ ] AC-4.2: Given `pyproject.toml`, when read, then the Kotlin grammar dependency is pinned with `==`, like the other grammars, and `uv.lock` agrees.
- [ ] AC-4.3: Given the README, when read, then the one-line-form grammar limit (A8) and the wildcard-import non-resolution (A6) are stated as known limits.

## 5. Non-Functional Requirements

| # | Category | Requirement (measurable) | How it's verified |
|---|---|---|---|
| NFR-1 | Determinism | Kotlin grammar is exact-pinned (`==`); double build of a Kotlin fixture is byte-identical; a stash round-trip build of a fixed repo with no Kotlin files yields a `graph.json` identical to pre-change code. | /peer-review (double-build test; stash round-trip) |
| NFR-2 | No dangling edges | Every `contains`/`imports` edge endpoint exists as a node in a Kotlin fixture graph; ambiguous or wildcard imports yield absence. | /peer-review (edge-endpoint integrity check) |
| NFR-3 | Confidence consistency | All new Kotlin `contains`/`imports` edges are `Confidence.EXTRACTED`; no new tier. | /peer-review (inspect `graph.json`) |
| NFR-4 | CLI/MCP parity | Zero Kotlin-specific code in `cli.py`/`server.py`; parity test passes. | /peer-review (diff, parity suite) |
| NFR-5 | Test coverage | `tests/test_extractor_kotlin.py` covers class kinds, functions, companion, extension, imports, empty file and malformed input at `test_extractor_java.py` granularity; multi-language build test includes Kotlin. | /peer-review (`uv run pytest`) |
| NFR-6 | Performance | The slow incremental-build benchmark passes unmodified with the Kotlin extractor registered. | /peer-review (`pytest -m slow`) |
| NFR-7 | Security | Offline parse only; no new network/exec surface; confinement and the 5 MB per-file cap apply to `.kt`/`.kts` like other files; the sdist allowlist and `test_packaging.py` still pass. | /peer-review |
| NFR-8 | CLI lens: ergonomics | No new command, flag or exit code. `build` results stay on stdout and diagnostics on stderr, exactly as today; `--help` is unchanged. A malformed `.kt` file never causes a traceback or a non-zero exit (AC-1.10). | /peer-review (run `build` on a fixture with a malformed `.kt`; check streams and exit code 0) |
| NFR-9 | CLI lens: machine output | Kotlin only adds the value `"kotlin"` to the existing `language` field; JSON output shape is otherwise unchanged. | /peer-review (diff of output schema) |
| NFR-10 | Accessibility / observability | N/A: no UI; Kotlin files are distinguishable via the existing `language` field. | N/A |

## 6. Out of Scope

- Kotlin Multiplatform `expect`/`actual` pairing (issue).
- Annotation processing (issue).
- Gradle / `build.gradle(.kts)` / module-path-aware import resolution; external library resolution.
- Wildcard-import resolution (A6) and nested-class import resolution (A5).
- Fixing the grammar's one-line misparse (A8); upgrading or switching grammar to cure it.
- `calls` edges, inheritance/`implements` edges, `typealias`, top-level properties, local and anonymous functions, lambdas (A9).
- Treating Kotlin `internal`/`protected` as distinct from public (A4).
- Any additional language.

## 7. Clarifications

| # | Date | Question | Resolution |
|---|---|---|---|
| C1 | 2026-11-10 | (Scope) New node kinds for object/interface/data/enum? | No: fold into `Class` per Java/Go/Rust precedent (A1). |
| C2 | 2026-11-10 | (Data) How are companion object members represented? | Companion is a nested `Class`; members under `Host.Companion` (A2, AC-1.6). |
| C3 | 2026-11-10 | (Edge cases) Extension functions have no declaring class in the same file; where do they live? | Named `Receiver.name`, top-level on own file, never a dangling edge (A3, AC-1.7). |
| C4 | 2026-11-10 | (Integrations) Gradle-aware import resolution? | No; best-effort declared-package index, ambiguity and wildcards give no edge (A5-A7). |
| C5 | 2026-11-10 | (Error behavior) One-line Kotlin forms are misparsed by the grammar; block the feature? | No; documented known limit, ACs target multi-line source (A8, AC-4.3). |
| C9 | 2026-11-10 | (Q1 from plan) Does an unknown extension become an unparsed `File`? | No: `build.py` skips it today (code-verified). AC-3.2 reworded to "unchanged behaviour"; README claim corrected. Option (a), autonomous run. |
| C6 | 2026-11-10 | (Data) Empty or malformed files? | Empty: zero-definition `File`, not unparsed. Malformed: tolerant, no new error mechanism (AC-1.9, AC-1.10). |
| C7 | 2026-11-10 | (Docs) Language count in README? | No count stated; list by name (A10, AC-4.1). |
| C8 | 2026-11-10 | (Roles/UX) Auth or UI states? | N/A: local headless tool. |

## 8. Design Review

**N/A: not UI-facing.** Headless extractor (bytes in, `FileExtraction` out) behind the existing `build`/query surface; no new command, flag, MCP tool or output format beyond the `language` value `"kotlin"`.

- **Overall impression:** N/A (no UI)
- **Heuristics findings:** N/A
- **Accessibility notes:** N/A (no UI)
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
- [x] Line budget respected: Ist ~165 / Soll ~250 (excluding HTML comments), self-reported
- [x] Status set to `approved` (autonomous run: recommended option taken)
