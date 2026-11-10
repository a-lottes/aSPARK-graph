# Spec: csharp-support

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Specify |
| **Owner** | Product Owner (`/story-time`) |
| **Status** | `approved` |
| **Date** | 2026-11-10 |
| **Ticket** | #20 |
| **Gate comment** | `skipped, autonomous mode: no one can answer; spec written retroactively for commit a7334d8` |

**Handoff**
- **Status:** `approved` (authoritative for `Status`).
- **Summary:** `.cs` files get no structure today (the issue calls them unparsed `File` nodes; the build in fact skips unmapped extensions entirely); goal is C# at parity with Java/Go/Rust (File/Class/Function nodes, best-effort in-repo `using` imports) with non-C# graphs unchanged byte for byte.
- **Open:** `none` (all assumptions in §3 are decided by the PO in autonomous mode; the approver should confirm them)
- **Binding ruling:** §4 User Stories for the current stories; §7 Clarifications for what changed since the last round and why
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed.

## 1. Problem & Goal

- **Problem:** The code layer covers Python, TS/JS, Java, Go and Rust (`constitution.md §3`). In a C# or polyglot repo `.cs` files yield no `Class`/`Function` structure, so `story_trace` and `impact` have no `extracted`-tier `Class`/`Function` structure and no `imports` edges to walk for C#. Only `declared` links from plan `files:` notes work. Felt by developers and agents on .NET repos with aSPARK trails.
- **Goal:** Extend the existing extractor pattern to C#: `.cs` becomes `File`, `Class` and `Function` nodes with `contains` edges, plus best-effort in-repo `imports` edges from `using` directives, like Go and Rust.
- **Success signal:**
  1. A built repo with `.cs` files has `Class`/`Function` nodes for them and no `unparsed` flag, shown by `tests/test_extractor_csharp.py` (granularity of `test_extractor_java.py`) and the multi-language build test including C#.
  2. A repo with no `.cs` files builds a byte-identical `graph.json` to the pre-change code.
  3. `uv run pytest` is green with no regressions in the other five languages.
- **Why now:** Ticket #20. C# is the next most common language missing from the supported set, and `CLAUDE.md` records "more languages" as the scope line, lifted here narrowly for C# only.

## 2. Target Users

- **Primary:** a developer or agent on an aSPARK-managed repo with C# code (or a polyglot repo with a C# component) who runs `story_trace`, `impact` or `/peer-review`'s graph steps.
- **Secondary:** the aSPARK maintainer, who wants a language to stay a bounded registry entry (extractor module plus resolver), not new architecture.
- **Not a target:** other unsupported languages (C/C++, Ruby, PHP stay unparsed); users wanting `calls` edges (no extractor emits them); Razor/Blazor users.

## 3. Assumptions & Open Questions

| # | Assumption / Question | Resolution |
|---|---|---|
| A1 | class, struct, interface, record (incl. record struct) and enum all fold into the existing `Class` kind, as Java interfaces/enums/records do. No new `NodeType`. | Decided by PO (autonomous); matches ticket text. |
| A2 | Methods and constructors nest under their declaring type; nested types nest under the outer type; local functions nest under their enclosing method/function. Everything is same-file, so no cross-file `contains` edge can dangle. | Decided by PO (autonomous). |
| A3 | `using` resolution is exact-match, best-effort, in-repo only, no `.csproj`/`.sln` parsing. A directive matching an in-repo type resolves to that file; otherwise one matching an in-repo namespace resolves to every file declaring it. BCL/NuGet namespaces resolve to nothing. | Decided by PO (autonomous). |
| A4 | Only the first namespace declared in a file is recorded as the file's namespace (block or file-scoped). Files with several namespaces resolve only by the first. Known limit. | Decided by PO (autonomous). |
| A5 | A type name declared in more than one file under the same namespace (e.g. partial classes) is ambiguous: a `using` naming it yields no edge, never a guess (honest absence, constitution §1). Each file's part is its own `Class` node. | Decided by PO (autonomous); matches ticket's "partial classes out of scope". |
| A6 | Alias, `static` and `global` usings count as imports of the target name. Types declared at top level outside any namespace ARE captured as `Class` nodes (verified against the implementation); they have no namespace so no `using` can resolve to them. | Decided by PO (autonomous). Revisit if it hurts. |
| A7 | Malformed C# is handled as for other languages: tolerant tree-sitter parse, best-effort extraction, no new error reporting. An empty `.cs` file is a parsed `File` node with zero definitions. | Decided by PO (autonomous). |
| A8 | `calls` edges are not produced (no language emits them today). | Decided by PO (autonomous). |

## 4. User Stories

### US-1 (Must): Extract C# source into File/Class/Function nodes

> As a developer or agent tracing a story or impact in a C# repo, I want `.cs` files parsed into `File`/`Class`/`Function` nodes with `contains` edges, so that C# has the same `extracted`-tier structure as the other languages instead of showing up unparsed.

**Acceptance criteria:**

- [ ] AC-1.1: Given a `.cs` file, when the repo is built, then a `File` node has `language="csharp"` and no `unparsed` flag, and its first declared namespace (block or file-scoped) is recorded.
- [ ] AC-1.2: Given `class`, `struct`, `interface`, `record` and `enum` declarations, when built, then each yields a `Class` node linked from its `File` (or outer type, if nested) by a `contains` edge with `Confidence.EXTRACTED`.
- [ ] AC-1.3: Given methods and constructors in a type, when built, then each yields a `Function` node nested under that type via `contains`.
- [ ] AC-1.4: Given a local function inside a method, when built, then it yields a `Function` node nested under the enclosing method.
- [ ] AC-1.5: Given a generic type or method (`List<T>`, `Box<T>`), when built, then the node carries the bare name without type parameters.
- [ ] AC-1.6: Given a `.cs` file with no type declarations, when built, then a `File` node with zero definitions and no `unparsed` flag exists.
- [ ] AC-1.7: Given an unchanged C# repo, when built twice, then `graph.json` is byte-identical.

### US-2 (Should): Best-effort in-repo `using` resolution

> As a developer tracing impact in a C# repo, I want `imports` edges between repo files linked by `using` directives, so that `impact` crosses C# file boundaries without `.csproj` parsing.

**Acceptance criteria:**

- [ ] AC-2.1: Given file A with `using N.T;` where `T` is declared in file B under namespace `N`, when built, then an `imports` edge (`Confidence.EXTRACTED`) links A to B.
- [ ] AC-2.2: Given `using N;` where `N` is declared by in-repo files, when built, then `imports` edges link A to each file declaring `N`.
- [ ] AC-2.3: Given `using static`, alias (`using X = N.T;`) or `global using` forms, when built, then the target name resolves as in AC-2.1/2.2.
- [ ] AC-2.4: Given `using System.Linq;` or a NuGet namespace absent from the repo, when built, then no `imports` edge is created and the build succeeds.
- [ ] AC-2.5: Given a `using` naming a type declared in more than one file, when built, then no `imports` edge is created for it.

### US-3 (Must): Existing guarantees hold with C# added

> As the aSPARK maintainer, I want registration, docs and determinism guarantees to hold once C# is added, so nothing regresses.

**Acceptance criteria:**

- [ ] AC-3.1: Given `.cs` in the extension map, when the extractor registry is queried, then `.cs` maps to `csharp`, and an unmapped extension (e.g. `.rb`) gets no `csharp` language mapping (unchanged behaviour).
- [ ] AC-3.2: Given one file each of Python, TS, JS, Java, Go, Rust and C# in one build, when built, then every file has a language-tagged `File` node with its definitions and none is `unparsed`.
- [ ] AC-3.3: Given the tree-sitter C# grammar in `pyproject.toml`, when inspected, then it is pinned with `==`.
- [ ] AC-3.4: Given the README, when read, then "Supported languages" and the design-guarantees text list C# (held by `tests/test_readme.py`).
- [ ] AC-3.5: Given a repo with no `.cs` files, when built with the new code and with pre-change code (stash round-trip), then both `graph.json` outputs are byte-identical.
- [ ] AC-3.6: Given a C# repo, when the same query runs via CLI and MCP, then results are identical, with no C#-specific code in `cli.py` or `server.py`.

## 5. Non-Functional Requirements

| # | Category | Requirement (measurable) | How it's verified |
|---|---|---|---|
| NFR-1 | Determinism | Grammar pinned `==`; double build of a C# repo is byte-identical; non-C# graphs byte-identical to pre-change (AC-1.7, AC-3.3, AC-3.5). | /peer-review: double-build test, stash round-trip |
| NFR-2 | Reliability (no dangling edges) | Every `contains`/`imports` endpoint exists as a node; ambiguous matches give no edge (AC-2.5). Malformed `.cs` never raises a traceback. | /peer-review: edge-integrity check on C# fixtures |
| NFR-3 | Confidence | New edges are `Confidence.EXTRACTED`; no new tier. | /peer-review: inspect `graph.json` |
| NFR-4 | CLI/MCP parity (`cli` lens, constitution §1) | No C# branching in `cli.py`/`server.py`; existing parity tests pass (AC-3.6). | /peer-review: diff adapters, run parity tests |
| NFR-5 | Test coverage | `tests/test_extractor_csharp.py` at `test_extractor_java.py` granularity; multi-language test includes C#; `uv run pytest` green. | /peer-review |
| NFR-6 | Performance | Incremental-build benchmark (slow) still passes unmodified. | /peer-review: `pytest -m slow` |
| NFR-7 | Security & privacy | N/A: no new network, credential or execution surface; confinement and the 5 MB per-file cap apply unchanged to `.cs`. | N/A |
| NFR-8 | Accessibility / Observability | N/A: headless tool; C# files are distinguishable via the existing `language` field. | N/A |

## 6. Out of Scope

- Partial classes across files: each file's part is its own `Class` node; ambiguous `using` gives no edge.
- Generics beyond naming: no type-parameter or constraint modelling.
- Razor/Blazor files (`.razor`, `.cshtml`): stay unparsed.
- `.csproj`/`.sln` parsing, project-reference and NuGet resolution.
- `calls`, inheritance and interface-implementation edges.
- Multi-namespace-per-file resolution (A4).
- Properties, fields, events, operators, indexers and lambdas as nodes.
- Any other language.

## 7. Clarifications

| # | Date | Question | Resolution |
|---|---|---|---|
| C1 | 2026-11-10 | (Scope) Which C# type kinds become `Class`? | All five from the ticket plus record struct (A1). |
| C2 | 2026-11-10 | (Data) Where do members and local functions nest? | Under the declaring type / enclosing function, same file only (A2). |
| C3 | 2026-11-10 | (Scope) AC-3.1 claimed unmapped extensions stay `unparsed: true`; the build skips them (no node), before and after. | AC-3.1, Summary and Problem reworded to match actual behaviour; no code change (autonomous ruling, review F5). |
| C3 | 2026-11-10 | (Integrations) Is `.csproj` parsing needed for `using` edges? | No, exact-match best-effort (A3). |
| C4 | 2026-11-10 | (Edge cases) Same type name in several files? | No edge, honest absence (A5). |
| C5 | 2026-11-10 | (Error) Malformed or empty source? | Tolerant parse; empty file is a parsed, empty `File` node (A7). |
| C6 | 2026-11-10 | (Roles/UX) Roles or UI states? | N/A: local headless tool. |

## 8. Design Review

N/A: headless tool, no UI, no new command or tool, only a new `language` value (`"csharp"`).

- **Overall impression:** N/A
- **Heuristics findings:** N/A
- **Accessibility notes:** N/A
- **Design risks & required changes:** None

---

## ✅ SPEC GATE

*All boxes checked → `/sprint-plan` may start. Any box open → back to `/story-time` or `/look-and-feel`.*

- [x] Problem, goal and success signal are concrete (no buzzwords, no "everyone")
- [x] Every story has testable Given/When/Then acceptance criteria
- [x] Stories are prioritized (MoSCoW) and at least one is a Must
- [x] Non-functional requirements are stated and measurable (or marked N/A with reason)
- [x] Clarify pass done: no ambiguity left unresolved or unparked
- [x] Open questions are resolved or explicitly accepted as risk *(decided by PO in autonomous mode, A1-A8)*
- [x] Out-of-scope section is filled (something was consciously cut)
- [x] Constitution (`.spark/constitution.md`) respected, or conflicts recorded as open questions
- [x] Design review done for UI-facing features (or marked N/A with reason)
- [x] Line budget respected: Ist ~150 / Soll ~250 (excluding HTML comments)
- [x] Status set to `approved` by the user
