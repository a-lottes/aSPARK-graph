# Spec: csharp-support

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Specify |
| **Owner** | Product Owner (`/story-time`), Designer (`/look-and-feel`) |
| **Status** | `approved` |
| **Date** | 2026-11-09 |
| **Ticket** | #18 (a-lottes/aSPARK-graph) |
| **Gate comment** | none |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Summary:** C# (`.cs`) files are unparsed `File` nodes, so `impact`/`story_trace` find no structure in .NET repos; goal is `File`/`Class`/`Function` nodes, `contains` edges and best-effort in-repo `imports` edges for C#, like Go and Rust.
- **Open:** `none`
- **Binding ruling:** §4 User Stories for the current stories; §7 Clarifications for what changed since the last round and why
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Problem & Goal

- **Problem:** Code extraction covers Python, TypeScript/JavaScript, Java, Go and Rust (`constitution.md §3`, `§9`). Every `.cs` file is recorded as an unparsed `File` node (the fallback proven by the unsupported-language test). On a .NET repo, or a polyglot repo with a .NET component, `story_trace` and `impact` therefore have no `extracted`-tier `Class`/`Function` structure and no `imports` edges to walk; only `declared` links from an explicit plan `files:` note work. The developer or agent asking "what breaks if I change this file?" gets an empty blast radius.
- **Goal:** `.cs` source is turned into `File`/`Class`/`Function` nodes with `contains` edges, and `using` directives into best-effort in-repo `imports` edges, with the same guarantees as the five shipped languages.
- **Success signal:**
  1. Building a repo with `.cs` files yields `Class`/`Function` nodes and no `unparsed: true` flag for them, shown by a C# extractor test module at the granularity of the Java one and the multi-language build test covering C#.
  2. A double build of an unchanged C# repo is byte-identical; a repo with no `.cs` files builds byte-identically to before this feature.
  3. `uv run pytest` is green with no regressions to the other five languages.
- **Why now:** The ticket is open, the extractor pattern is proven by Go/Rust at low per-language cost, and C# is the next most common language the tool still treats as opaque. Cost of never building: .NET repos keep getting no impact analysis; the tool stays usable only declared-tier there.

## 2. Target Users

- **Primary:** a developer or AI agent in an aSPARK-managed .NET repo (or polyglot repo with a C# component) running `story_trace`, `impact` or `/peer-review`'s aspark-graph steps.
- **Secondary:** the aSPARK-graph maintainer, who wants one more language added as a bounded registry entry, not new architecture.
- **Not a target:** Razor/Blazor users (`.razor`/`.cshtml`), users wanting `calls` edges, users of any other still-unparsed language (C/C++, Ruby, PHP).

## 3. Assumptions & Open Questions

| # | Assumption / Question | Resolution |
|---|---|---|
| A1 | class, struct, interface, record and enum fold into the existing `Class` kind, no new `NodeType`, mirroring Java and Go/Rust. | Accepted (autonomous default) |
| A2 | `namespace` has no node kind. The first namespace in a file (block-scoped or file-scoped) is the file's package name, used for import resolution. Types nest under their enclosing type only, not under the namespace. | Accepted (autonomous default) |
| A3 | Import resolution is best-effort and in-repo only, with no `.csproj`/`.sln` parsing. A `using` name resolves to the in-repo file declaring that type, else to the in-repo file(s) declaring that namespace. BCL and NuGet namespaces match nothing and produce no edge. | Accepted (autonomous default) |
| A4 | No `calls` edges; no existing language emits any (same baseline as go-rust-support A4). | Accepted (autonomous default) |
| A5 | Malformed C# is handled by tree-sitter's tolerant parse, like every other language; no new syntax-error reporting. | Accepted (autonomous default) |
| A6 | An empty `.cs` file (or only usings/a namespace) is a known, parsed file with zero definitions, not `unparsed`. | Accepted (autonomous default) |
| A7 | C# top-level statements (a `Program.cs` with free-standing local functions) are in scope only to the extent that such functions become top-level `Function` nodes. | Accepted (autonomous default) |
| A8 | The ticket's "Function (method, constructor, local function)" is read as: a local function nests under its enclosing method (qualname `Method.Local`), so it never dangles. | Accepted (autonomous default) |
| A9 | Original request phrasing recorded: "Add C# to the code extraction", with the grammar pin, test module and README items named in the ticket. | Recorded |

## 4. User Stories

### US-1 (Must): Extract C# source into File/Class/Function nodes

> As a developer or agent tracing a story or impact in a .NET repository, I want `.cs` files parsed into `File`/`Class`/`Function` nodes with `contains` edges, so that C# source has the same `extracted`-tier structure the other five languages have, instead of showing up as unparsed.

**Acceptance criteria:**

- [ ] AC-1.1: Given a `.cs` file, when the repo is built, then a `File` node is created with `language="csharp"` and no `unparsed` flag.
- [ ] AC-1.2: Given a file containing a block-scoped (`namespace N { ... }`) or file-scoped (`namespace N;`) namespace, when built, then the `File` node's package name is the first namespace's full dotted name (e.g. `Acme.Util`).
- [ ] AC-1.3: Given a `class`, `struct`, `interface`, `record` or `enum` declaration, when built, then each becomes a `Class` node linked from its `File` node via a `contains` edge with `Confidence.EXTRACTED`.
- [ ] AC-1.4: Given a type nested inside another type, when built, then its `Class` node is nested under the outer type's `Class` node via `contains` (qualname `Outer.Inner`).
- [ ] AC-1.5: Given a method or constructor declared in a type, when built, then a `Function` node is created and nested under that type's `Class` node via `contains`.
- [ ] AC-1.6: Given a local function declared inside a method, when built, then a `Function` node is created and nested under the enclosing method's `Function` node (qualname `Method.Local`).
- [ ] AC-1.7: Given a generic type or method (`Box<T>`), when built, then it is named by its bare name without type parameters (`Box`).
- [ ] AC-1.8: Given access modifiers, when built, then `Definition.exported` is true for `public`/`internal`/`protected` members, false for `private`, and for an unmodified member follows the default (top-level types exported, other members as the extractor's documented default).
- [ ] AC-1.9: Given a `.cs` file with no type or function declarations (empty, or only `using`/`namespace`), when built, then a `File` node with zero definitions and no `unparsed` flag exists.
- [ ] AC-1.10: Given an unchanged C# repo, when built twice, then `graph.json` is byte-identical both times.

### US-2 (Should): Best-effort in-repo `using` resolution

> As a developer tracing impact in a .NET repo, I want `imports` edges between repo-local files connected by `using` directives, so that `impact`'s blast-radius walk can cross C# file boundaries without `.csproj` parsing.

**Acceptance criteria:**

- [ ] AC-2.1: Given file A with `using Acme.Util.Helper;` (a type) or `using Acme.Util;` (a namespace) that matches a type or namespace declared in in-repo file B, when built, then an `imports` edge with `Confidence.EXTRACTED` links A to B.
- [ ] AC-2.2: Given the `using static X.Y;`, `using Alias = X.Y;` and `global using X;` forms, when built, then each is read as an import of its target name and resolves under AC-2.1.
- [ ] AC-2.3: Given a `using System.Linq;` or a NuGet namespace not declared anywhere in the repo, when built, then no `imports` edge is created and no error is raised.
- [ ] AC-2.4: Given a namespace declared in several in-repo files, when a file `using`s that namespace, then an `imports` edge goes to each declaring file, in a stable order, and a build twice stays byte-identical.
- [ ] AC-2.5: Given a file with a `using` that resolves to itself, when built, then no self-referencing `imports` edge is created.

### US-3 (Must): Existing multi-language guarantees still hold

> As the aSPARK-graph maintainer, I want the existing guarantees (every language present in a mixed build, unknown extensions still unparsed, determinism, CLI≡MCP parity) to keep holding with C# added, so that this feature cannot regress what shipped.

**Acceptance criteria:**

- [ ] AC-3.1: Given a repo with at least one file each of Python, TS, JS, Java, Go, Rust and C# in one build, when built, then every file produces a language-tagged `File` node with its definitions and none is `unparsed`.
- [ ] AC-3.2: Given a file with an unsupported extension (e.g. `.rb`), when built, then it is still recorded as `unparsed: true`.
- [ ] AC-3.3: Given a repo with no `.cs` files, when built with this feature and with the pre-change code, then both `graph.json` outputs are byte-identical.
- [ ] AC-3.4: Given a C#-containing repo, when the same `find_nodes`/`impact`/`story_trace` query runs via CLI and via MCP, then results are identical, with no C#-specific branching in `cli.py` or `server.py`.
- [ ] AC-3.5: Given `uv run pytest`, when run, then it passes with the new C# tests and no regression to the other languages' extractor tests.

### US-4 (Should): Docs list C# as supported

> As a prospective user reading the README, I want C# named among supported languages and design guarantees, so that I know the tool covers my repo.

**Acceptance criteria:**

- [ ] AC-4.1: Given the README, when read, then the "Supported languages" statement and the design-guarantees list name C# alongside Python, TypeScript/JavaScript, Java, Go and Rust.
- [ ] AC-4.2: Given the README's list of pinned tree-sitter grammars, when read, then it includes the C# grammar.

## 5. Non-Functional Requirements

| # | Category | Requirement (measurable) | How it's verified |
|---|---|---|---|
| NFR-1 | Determinism (inherited) | The C# tree-sitter grammar is pinned `==` in `pyproject.toml` like the other grammars; a double build of a C# repo is byte-identical; a repo without `.cs` files is byte-identical to pre-change output (stash round-trip, not only double build). | /peer-review |
| NFR-2 | No dangling edges (inherited) | Every `contains`/`imports` edge endpoint exists as a node in the built graph for C# fixtures; an unresolved `using` yields absence, not a guessed edge. | /peer-review graph-integrity check |
| NFR-3 | Confidence consistency (inherited) | All new C# `contains`/`imports` edges carry `Confidence.EXTRACTED`; no new tier. | /peer-review: inspect `graph.json` |
| NFR-4 | CLI≡MCP parity (inherited) | Dispatch stays data-driven; zero C#-specific code in `cli.py`/`server.py`. | /peer-review: diff adapters; parity tests |
| NFR-5 | Test coverage | A C# extractor test module at the granularity of `test_extractor_java.py` (types, members, local functions, usings, empty file, resolution) plus the multi-language build test including C#. | /peer-review: `uv run pytest` |
| NFR-6 | Performance / bounds | The slow incremental-build benchmark still passes; confinement, the 5 MB per-file cap and symlink-cycle bounds apply to `.cs` files unchanged. | /peer-review: `uv run pytest -m slow` |
| NFR-7 | Packaging / install | A wheel installed fresh without the lock imports the C# extractor and boots `serve`; the sdist allowlist is unchanged. | /peer-review: `tests/test_fresh_install.py`, `tests/test_packaging.py` |
| NFR-8 | CLI lens (active) | No new command, flag, output or error path; a malformed `.cs` file never produces a traceback (tolerant parse, exit code unchanged). | /peer-review |
| NFR-9 | Security & accessibility | N/A: no new network, credential or execution surface, and no UI. | N/A |

## 6. Out of Scope

- **Partial classes across files.** Each `partial` declaration is its own `Class` node in its own file; no merging.
- **Generics beyond naming.** Type parameters, constraints and generic instantiation are not modelled.
- **Razor/Blazor files** (`.razor`, `.cshtml`): remain unparsed `File` nodes.
- **`.csproj`/`.sln`/NuGet parsing**, root-namespace or assembly-aware resolution, and external package resolution.
- **`calls` edges**, inheritance/`implements`-clause edges, and a distinct node kind for struct/interface/record/enum.
- **Lambdas and anonymous functions**; only named methods, constructors and local functions are captured.
- **Properties, fields, events, operators, destructors, indexers** as `Function` nodes.
- **Syntax-error detection or reporting** specific to C#.
- **Any further language** beyond C#.

## 7. Clarifications

| # | Date | Question | Resolution |
|---|---|---|---|
| C1 | 2026-11-09 | (Scope) Do struct/interface/record/enum need their own node kind? | No; fold into `Class` (A1). |
| C2 | 2026-11-09 | (Data) Is a namespace a node, and how does it relate to nesting? | No node; first namespace is the file's package name (A2, AC-1.2). |
| C3 | 2026-11-09 | (Integrations) Is `.csproj` parsing needed for `using` resolution? | No; best-effort in-repo type-then-namespace match (A3, US-2). |
| C4 | 2026-11-09 | (Edge) What happens to a `using` of a BCL/NuGet namespace? | No edge, no error (AC-2.3). |
| C5 | 2026-11-09 | (Edge) A namespace spread over several files? | Edge to each declaring file, stable order (AC-2.4). Differs from Go/Rust's "ambiguous gives none": a namespace is a legitimate many-file unit, not an ambiguous guess. |
| C6 | 2026-11-09 | (Edge) Malformed C#, empty files? | Tolerant parse, empty file is a known file (A5, A6, AC-1.9). |
| C7 | 2026-11-09 | (Scope) Local functions and top-level statements? | Local functions nest under their method; top-level-statement functions are top-level `Function` nodes (A7, A8, AC-1.6). |
| C8 | 2026-11-09 | (Roles/UX) Roles or UI states? | N/A: headless local tool. |
| C9 | 2026-11-09 | (Out of scope) Partial classes, generics, Razor? | Cut per ticket, see §6. |

All resolutions above are autonomous-mode defaults chosen by the Product Owner; the user confirms them by approving the spec.

## 8. Design Review

**N/A.** The feature is headless: source bytes in, a `FileExtraction` out, consumed by the build exactly like the other languages. No new command, tool or output format beyond a new `language` value (`"csharp"`). Not UI-facing.

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
- [x] Line budget respected: Ist 150 / Soll ~250 (excluding HTML comments) — self-reported, no linter checks this
- [x] Status set to `approved` by the user
