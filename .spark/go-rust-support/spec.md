# Spec: go-rust-support

| | |
|---|---|
| **Phase** | Specify |
| **Owner** | Product Owner (`/story-time`) |
| **Status** | `approved` |
| **Date** | 2026-07-19 |

## 1. Problem & Goal

- **Problem:** aspark-graph's code layer today only understands Python,
  TypeScript/JavaScript and Java (`src/aspark_graph/extractors/`:
  `code_py.py`, `code_ts.py`, `code_java.py`, dispatched via
  `EXTENSION_LANGUAGE`/the extractor registry). On a Go or Rust repository —
  or a polyglot repo with a Go or Rust component — every `.go`/`.rs` file is
  recorded today as an **unparsed `File` node** (the same fallback path
  proven by `test_ac_4_2_unsupported_language_becomes_unparsed_file_node`).
  That means `story_trace` and `impact`, the two questions this tool exists
  to answer (README), have no `extracted`-tier `Class`/`Function` structure
  and no `imports` edges to walk for that language: `declared`-tier links
  from an explicit plan `files:` note still work, but the tool's actual
  differentiator — deterministic structure plus impact analysis — is simply
  unavailable. `CLAUDE.md`'s v0.3.0 Out-of-Scope line ("more languages") is
  what this feature deliberately and narrowly lifts, for Go and Rust only —
  not a general "any language" claim.

- **Goal:** Extend the extractor pattern (bytes-in, `FileExtraction`-out;
  `base.py` + per-language module + registry entry) to Go and Rust, so their
  source is turned into `File`/`Class`/`Function` nodes and `contains` edges
  the same way the four existing languages already are, with best-effort
  in-repo `imports` edges as a stretch (not core) slice.

- **Success signal (observable):**
  1. A repo containing `.go`/`.rs` files, when built, produces `Class`/
     `Function` nodes for those files instead of `unparsed: true` `File`
     nodes — verified by two new extractor test files
     (`test_extractor_go.py`, `test_extractor_rust.py`) at the same
     granularity as `test_extractor_java.py`, plus the existing
     "languages in one build" integration test extended to six languages.
  2. A double build of an unchanged Go/Rust repo produces a byte-identical
     `graph.json` (the existing determinism test pattern, extended).
  3. `uv run pytest` stays green with zero regressions to the four existing
     languages' extractor tests.

- **Why now:** This is feature 1 of 2 in a two-feature sequence the user has
  already scoped (feature 2, Windows platform/packaging compatibility,
  follows as its own SPARK loop). Building language support first, platform
  support second, keeps each loop's blast radius contained to one concern.

## 2. Target Users

- **Primary:** a developer or agent working in an aSPARK-managed Go or Rust
  repository (or a polyglot repo with a Go/Rust component) who runs
  `story_trace`, `impact`, or `/peer-review`'s aspark-graph steps, and today
  gets only artifact-declared links plus unparsed `File` nodes for that
  language.
- **Secondary:** the aSPARK maintainer, who wants the "more languages"
  scope boundary lifted deliberately and narrowly — Go and Rust specifically,
  keeping the per-language cost of the extractor pattern bounded and
  auditable (a "language" is a data-driven registry entry, not new
  architecture).
- **Explicitly NOT a target this spec:** repos in any language other than
  the now six supported ones (C/C++, Ruby, C#, PHP, etc. still fall back to
  unparsed `File` nodes); users wanting `calls` (Function→Function) edges —
  no existing language extractor produces those today, so this feature does
  not introduce them either; users on Windows wanting the tool to install/run
  there — that is feature 2, out of scope here.

## 3. Assumptions & Open Questions

| # | Assumption / Question | Resolution |
|---|---|---|
| A1 | Go structs and interfaces, and Rust structs/enums/traits, fold into the existing `Class` node kind (no new `NodeType` values). This mirrors the direct precedent already shipped for Java: `interface_declaration`/`enum_declaration`/`record_declaration` are all folded into `Class` in `code_java.py`. `NodeType` is a shared vocabulary consumed by every query (`queries.py`), so adding new kinds is a global change with no stated user need behind it yet. | Accepted by user (2026-07-19) |
| A2 | `contains` (parent→child) edges are file-scoped today: `_add_definitions` builds a parent id via `definition_id(extraction.relpath, d.parent)`, using the *current file's* relpath. Go idiomatically splits a struct's receiver methods across multiple files in the same package; Rust can have multiple `impl` blocks for one type, including in a different file. Naively parenting a cross-file method under its type's qualname (as if declared in the same file) would create a `contains` edge to a node id that doesn't exist — a silently wrong graph. This spec's proposed cut: a receiver method / `impl`-block function whose target type **is** declared in the same file nests under that type's `Class` node (same as Java methods do); one whose target type is declared **elsewhere** is still captured, as a top-level `Function` node on its own file — never a dangling edge. A full cross-file type index (mirroring Java's FQN index) is deferred. | Accepted by user (2026-07-19) |
| A3 | Import-edge resolution for Go/Rust follows the same *best-effort, in-repo-only* bar already established per language (Python: dotted-module index; TS/JS: relative-specifier resolution only, bare packages unresolved; Java: FQN index from declared `package` + directory). Proposed: Go resolves via a trailing-path-segment match of the import path against the repo's directory/package layout (no `go.mod` parsing, no module-path-prefix awareness); Rust resolves `crate::`/`self::`/`super::`-relative `use` paths via a module-path index built from file/directory layout (no `Cargo.toml`/workspace parsing). External/third-party packages are expected to go unresolved, same as today's third-party Python/npm imports. | Accepted by user (2026-07-19) |
| A4 | `calls` (Function→Function) edges are not produced for Go or Rust. Verified against the live code: no existing extractor (`code_py.py`, `code_ts.py`, `code_java.py`) emits `EdgeType.CALLS` today — it is defined in `model.py` as "best-effort, may be absent" but is currently a zero-implementation baseline across all four shipped languages. Holding Go/Rust to a higher bar than the existing languages would be new, unscoped work. | Accepted by user (2026-07-19) |
| A5 | Malformed or mid-edit (syntactically invalid) Go/Rust source is handled exactly as malformed source already is for every other language: tree-sitter parses tolerantly (it does not throw; unrecognized constructs are simply not matched), and extraction proceeds best-effort over whatever nodes are recognized. No language extractor today detects or reports syntax errors distinctly. Introducing that selectively for Go/Rust would be inconsistent new behavior outside this feature's scope. | Accepted by user (2026-07-19) |
| A6 | An empty Go/Rust file (e.g. only a `package foo` clause, or a Rust file with no items) still produces a `File` node with zero definitions — it is a *known, successfully parsed, just-empty* file, not `unparsed: true`. This mirrors how an empty `.py`/`.ts` file behaves today (no special-casing needed; the walk simply finds nothing). | Accepted — directly resolved into AC-1.8/AC-2.8, no open question. |
| A7 | An ambiguous in-repo import match (an import path's trailing segments match more than one directory candidate in the repo) resolves to **no edge**, not a guessed one. This mirrors the git-inference non-negotiable already in `CLAUDE.md` ("an ambiguous id-only commit contributes no edge... honest absence beats a wrong cross-feature link"). | Accepted — directly resolved into AC-3.3/AC-4.3, no open question. |
| Q1 | **Node-kind mapping:** should Go structs/interfaces and Rust structs/enums/traits fold into the existing `Class` kind (A1's proposal), or does the team want the struct/interface/trait distinction preserved via a new node type or a `kind` sub-attribute? | **RESOLVED (2026-07-19): CONFIRMED — fold into `Class`.** A1's proposal accepted; no new `NodeType` introduced for Go/Rust. |
| Q2 | **Cross-file methods:** is A2's proposed cut acceptable — same-file receiver methods/impl-block functions nest under their type's `Class`, cross-file ones land as top-level `Function` nodes (never a dangling edge) — or should cross-file methods be dropped entirely for this cycle, or is a cross-file type index (bigger scope) actually wanted now given how common file-splitting is in idiomatic Go? | **RESOLVED (2026-07-19): CONFIRMED — A2's proposed cut accepted.** Same-file receiver methods/impl-block functions nest under their type's `Class`; cross-file ones become top-level `Function` nodes, never a dangling edge. A full cross-file type index remains deferred. |
| Q3 | **Import-resolution ambition:** is A3's best-effort, no-manifest-parsing bar (no `go.mod`/`Cargo.toml` parsing) acceptable for this cycle, or is manifest-aware resolution required for import edges to be useful enough to ship? | **RESOLVED (2026-07-19): CONFIRMED — A3's best-effort, no-manifest-parsing bar accepted.** No `go.mod`/`Cargo.toml` parsing this cycle. |
| Q4 | **`calls` edges:** confirm Go/Rust should not be held to a different bar than the four existing languages (all of which currently produce zero `calls` edges). | **RESOLVED (2026-07-19): CONFIRMED — no `calls` edges for Go/Rust.** Matches the zero-implementation baseline already shared by Python/TS/JS/Java (A4 accepted). |
| Q5 | **Malformed source:** confirm no new fail-loud/error-detection mechanism is expected for Go/Rust beyond tree-sitter's existing tolerant behavior, shared with every other language. | **RESOLVED (2026-07-19): CONFIRMED — no new malformed-source/syntax-error detection mechanism.** tree-sitter's existing tolerant behavior applies uniformly, same as every other language (A5 accepted). |

## 4. User Stories

### US-1 (Must): Extract Go source into File/Class/Function nodes

> As a developer or agent tracing a story or impact in a Go repository, I
> want `.go` files parsed into `File`/`Class`/`Function` nodes with
> `contains` edges, so that Go source has the same `extracted`-tier
> structure Python/TS/Java already have, instead of showing up as unparsed.

**Acceptance criteria:**

- [ ] AC-1.1: Given a `.go` file with a `package` clause, when the repo is
  built, then a `File` node is created with `language="go"`, the Go package
  name populated, and no `unparsed` flag.
- [ ] AC-1.2: Given a top-level `type X struct {...}` or `type X interface
  {...}` declaration, when built, then a `Class` node (`name=X`) is created,
  linked from its `File` node via a `contains` edge with
  `Confidence.EXTRACTED`.
- [ ] AC-1.3: Given a top-level free function (`func F(...) {...}`, no
  receiver), when built, then a `Function` node is created, linked from its
  `File` node via `contains` (`parent=None`).
- [ ] AC-1.4: Given a method with a receiver naming a struct/interface type
  declared in the **same file** (`func (w *Widget) Render() {...}`), when
  built, then a `Function` node is created and nested under that type's
  `Class` node via `contains` (`parent` = the receiver type's qualname).
- [ ] AC-1.5: Given a method with a receiver naming a type declared in a
  **different file**, when built, then the method is still captured as a
  `Function` node with a `contains` edge from its own `File` node
  (`parent=None`) — never a `contains` edge pointing at a node id that does
  not exist in the graph.
- [ ] AC-1.6: Given a Go identifier's capitalization (uppercase first letter
  = exported, per Go convention), when built, then the corresponding
  `Definition.exported` field is set accordingly for that struct, interface,
  function, or method.
- [ ] AC-1.7: Given an unchanged Go file/repo, when built twice, then the
  resulting `graph.json` is byte-identical both times.
- [ ] AC-1.8: Given a `.go` file containing only a `package` clause (or
  otherwise no struct/interface/function declarations), when built, then a
  `File` node is created with zero definitions and no `unparsed` flag — an
  empty file is not an error.

### US-2 (Must): Extract Rust source into File/Class/Function nodes

> As a developer or agent tracing a story or impact in a Rust repository, I
> want `.rs` files parsed into `File`/`Class`/`Function` nodes with
> `contains` edges, so that Rust source has the same `extracted`-tier
> structure Python/TS/Java already have, instead of showing up as unparsed.

**Acceptance criteria:**

- [ ] AC-2.1: Given a `.rs` file, when built, then a `File` node is created
  with `language="rust"` and no `unparsed` flag.
- [ ] AC-2.2: Given a top-level `struct`, `enum`, or `trait` item, when
  built, then a `Class` node is created, linked from its `File` node via
  `contains` (`Confidence.EXTRACTED`).
- [ ] AC-2.3: Given a top-level free function (`fn f() {}`, not inside any
  `impl` block), when built, then a `Function` node is created, linked from
  its `File` node via `contains` (`parent=None`).
- [ ] AC-2.4: Given a function inside an `impl TypeName { ... }` or `impl
  Trait for TypeName { ... }` block whose `TypeName` is declared in the
  **same file** — including when multiple `impl` blocks for the same type
  appear in that file — when built, then each such function is a `Function`
  node nested under `TypeName`'s `Class` node via `contains`.
- [ ] AC-2.5: Given a function inside an `impl` block whose target type is
  declared in a **different file** (or not declared in the repo at all —
  e.g. an extension impl on a foreign/external type), when built, then the
  function is still captured as a `Function` node with a `contains` edge
  from its own `File` node (`parent=None`) — never a dangling edge.
- [ ] AC-2.6: Given the presence or absence of the `pub` keyword on an item,
  when built, then the corresponding `Definition.exported` field is set
  accordingly.
- [ ] AC-2.7: Given an unchanged Rust file/repo, when built twice, then the
  resulting `graph.json` is byte-identical both times.
- [ ] AC-2.8: Given a `.rs` file with no items (or only comments), when
  built, then a `File` node is created with zero definitions and no
  `unparsed` flag.

### US-3 (Should): Best-effort in-repo import resolution for Go

> As a developer tracing impact in a Go repo, I want `imports` edges between
> repo-local files that reference each other via Go import paths, so that
> `impact`'s blast-radius walk can cross Go file boundaries the way it
> already does for Python/TS/Java — without requiring `go.mod` parsing.

**Acceptance criteria:**

- [ ] AC-3.1: Given two Go files in the same repo where one's `import`
  clause references a path whose trailing segments unambiguously match the
  other file's directory/package location, when built, then an `imports`
  edge (`Confidence.EXTRACTED`) links the importing `File` to the imported
  `File`.
- [ ] AC-3.2: Given a Go file that imports a standard-library or
  third-party package not present in the repo, when built, then no
  `imports` edge is created for that import — absence, not an error.
- [ ] AC-3.3: Given an import path whose trailing segments match more than
  one directory candidate in the repo, when built, then no `imports` edge
  is guessed for that import — an ambiguous match produces absence, not a
  wrong link.

### US-4 (Should): Best-effort in-repo import resolution for Rust

> As a developer tracing impact in a Rust repo, I want `imports` edges
> between repo-local files connected via `crate::`/`self::`/`super::`
> `use` paths, so that `impact` can cross Rust file boundaries — without
> requiring `Cargo.toml`/workspace parsing.

**Acceptance criteria:**

- [ ] AC-4.1: Given two Rust files where one's `use crate::...` /
  `use self::...` / `use super::...` path resolves, via a module-path index
  built from file/directory layout, to another file in the repo, when
  built, then an `imports` edge (`Confidence.EXTRACTED`) links them.
- [ ] AC-4.2: Given a Rust file that `use`s an external crate (e.g. `use
  serde::Serialize;`) not present in the repo, when built, then no
  `imports` edge is created for that import.
- [ ] AC-4.3: Given a `use` path that matches more than one candidate
  module location in the repo, when built, then no `imports` edge is
  guessed — same ambiguity-over-wrong-link ethos as AC-3.3.

### US-5 (Must): Existing multi-language guarantees still hold

> As the aSPARK maintainer, I want the guarantees the four shipped languages
> already provide — no language goes missing from a mixed build, unknown
> extensions still fall back to unparsed, determinism, CLI≡MCP parity — to
> keep holding once Go and Rust are added, so this feature cannot regress
> what already shipped.

**Acceptance criteria:**

- [ ] AC-5.1: Given a repo containing at least one file each of Python, TS,
  JS, Java, Go and Rust in a single build, when built, then every file
  produces a language-tagged `File` node with its `Class`/`Function`
  definitions present — none is `unparsed`.
- [ ] AC-5.2: Given a file with an extension not in `EXTENSION_LANGUAGE`
  (e.g. `.rb`), when built, then it is still recorded as `unparsed: true` —
  unchanged from current behavior.
- [ ] AC-5.3: Given the full test suite (existing 165+ tests plus new
  Go/Rust tests), when `uv run pytest` runs, then it passes green with zero
  regressions to the Python/TS/JS/Java extractor tests.
- [ ] AC-5.4: Given a Go/Rust-containing repo, when the same
  `story_trace`/`impact`/`find_nodes` query is run via the CLI and via the
  MCP tool, then both return identical results — parity holds because
  language dispatch is data-driven (`EXTENSION_LANGUAGE` + the extractor
  registry), with no Go/Rust-specific branching added to `cli.py` or
  `server.py`.

## 5. Non-Functional Requirements

| # | Category | Requirement (measurable) | How it's verified |
|---|---|---|---|
| NFR-1 | Determinism (non-negotiable, inherited) | New tree-sitter grammar dependencies (Go, Rust) are pinned exact (`==`) in `pyproject.toml`, same discipline as the existing three grammars. A double build of an unchanged repo containing Go/Rust files produces byte-identical `graph.json`. | /peer-review: extend the existing double-build determinism test with Go/Rust fixtures |
| NFR-2 | No dangling edges / never a silently wrong graph (fail-loud ethos, inherited) | Every `contains`/`imports` edge's source and target node ids exist in the built graph. Cross-file receiver-method/impl-block cases resolve to a safe top-level `Function` rather than an edge to a nonexistent node (AC-1.5, AC-2.5); ambiguous import matches produce absence, not a guessed edge (AC-3.3, AC-4.3). | /peer-review: a graph-integrity check (every edge endpoint exists as a node) run against Go/Rust fixtures |
| NFR-3 | Confidence tier consistency (non-negotiable, inherited) | All new Go/Rust `contains`/`imports` edges carry `Confidence.EXTRACTED`; no new confidence tier is introduced. | /peer-review: inspect edge confidence values in `graph.json` for Go/Rust fixtures |
| NFR-4 | CLI ≡ MCP parity (non-negotiable, inherited) | Dispatch stays data-driven; zero Go/Rust-specific code paths are added to `cli.py`/`server.py` beyond registry wiring. | /peer-review: diff `cli.py`/`server.py`; run the existing parity test suite |
| NFR-5 | Test coverage | Two new per-language extractor test files (`test_extractor_go.py`, `test_extractor_rust.py`) at the same granularity as `test_extractor_java.py` (type/method/import/empty-file/cross-file cases), plus the existing "languages in one build" integration test extended to six languages. | /peer-review: `uv run pytest` green; new test files present |
| NFR-6 | Performance | No new performance target introduced. The existing v0.4.0 NFR-1 incremental-build benchmark continues to pass unmodified with Go/Rust extractors registered. | /peer-review: `uv run pytest -m slow` |
| NFR-7 | Security & privacy | N/A — no new network, credential, or execution surface; parsing stays offline/local, identical threat profile to the four existing languages. | N/A |
| NFR-8 | Accessibility | N/A — headless CLI/MCP tool, no UI, consistent with every prior feature. | N/A |
| NFR-9 | Observability | Go/Rust files are distinguishable in `BuildReport`/graph counts via the existing `language` field, same as the other four languages — no new logging mechanism needed. | /peer-review: `aspark-graph build` against a mixed fixture; inspect `report.summary()` |

## 6. Out of Scope

- **`go.mod`/`Cargo.toml` parsing.** Manifest-aware, module-path-prefix-
  correct import resolution, workspace/multi-module layout awareness, and
  external/third-party crate or package import resolution are all out of
  scope this cycle (A3/Q3, confirmed). Import edges are best-effort and
  in-repo-only, matching the existing per-language variance in resolution
  depth.
- **`calls` (Function→Function) edges for Go/Rust.** No existing language
  extractor emits these today (a zero-implementation baseline across
  Python/TS/JS/Java); holding Go/Rust to a higher bar is new, unscoped work
  (A4/Q4, confirmed).
- **Cross-file `Class` nesting via a full type index.** Go's convention of
  splitting a struct's methods across multiple files, and Rust `impl`
  blocks in a different file than their target type, are captured as
  top-level `Function` nodes this cycle rather than nested under their
  `Class` (A2/Q2, confirmed). A cross-file type index (mirroring Java's FQN
  index) is deferred.
- **New node types for Struct/Interface/Trait distinct from Class.** Folds
  into the existing `Class` kind per the Java-interface precedent (A1/Q1,
  confirmed). A distinguishing `kind`/subtype attribute is a future
  refinement if a concrete query need for it emerges.
- **Inheritance/composition/trait-implementation edges** (Go struct
  embedding, Rust `impl Trait for X` as a relationship distinct from method
  containment, Java `extends`/`implements` clauses). No existing language
  models this either — consistent baseline, not a new gap introduced here.
- **Closures and function literals bound to local variables** (Go `f :=
  func() {}`, Rust `let f = |x| {}`). Treated as implementation detail, not
  named API surface — deliberately different from the TS/JS
  `export const f = () => {}` pattern, which only captures top-level or
  exported bindings.
- **Go build-tag or `_test.go`-aware file handling** (`//go:build`
  constraints, special-casing test files). Every `.go`/`.rs` file is parsed
  uniformly, same as `.spec.ts`/`test_*.py` files today.
- **Malformed/syntax-error detection or reporting specific to Go/Rust.**
  tree-sitter's existing tolerant partial-parse behavior applies uniformly
  across all six languages; no new fail-loud mechanism is introduced
  selectively here (A5/Q5, confirmed).
- **Windows platform/packaging compatibility.** Explicitly sequenced as a
  separate, later feature (feature 2 of 2) per the user's own framing — not
  folded into this spec.
- **Any language beyond Go and Rust.** `CLAUDE.md`'s "more languages"
  out-of-scope line is lifted narrowly for these two, not generally.

## 7. Clarifications

| # | Date | Question | Resolution |
|---|---|---|---|
| C1 | 2026-07-19 | (Functional scope) Does folding Go structs/interfaces and Rust structs/enums/traits into the existing `Class` node kind preserve enough meaning for downstream queries, or is a new node type/`kind` attribute needed? | **RESOLVED (2026-07-19):** fold into `Class`, mirroring the shipped Java interface/enum/record precedent (A1). Confirmed by the user; no new node type introduced. |
| C2 | 2026-07-19 | (Data & edge cases) How should methods/`impl`-block functions whose receiver/target type is declared in a *different* file be represented, given `contains` edges are file-scoped by construction (`definition_id(relpath, qualname)`)? | **RESOLVED (2026-07-19):** same-file nests under `Class`; cross-file lands as a top-level `Function`, never a dangling edge (A2). Confirmed by the user. |
| C3 | 2026-07-19 | (Integrations) Should import-edge resolution require parsing `go.mod`/`Cargo.toml` for module-path-prefix accuracy, or is a best-effort in-repo directory/path match sufficient for this cycle? | **RESOLVED (2026-07-19):** best-effort, no manifest parsing (A3), matching existing per-language variance. Confirmed by the user. |
| C4 | 2026-07-19 | (Functional scope) Should Go/Rust be held to a different (higher) bar for `calls` edges than the four existing languages, none of which emit any today? | **RESOLVED (2026-07-19):** no — same zero baseline as the four existing languages (A4). Confirmed by the user. |
| C5 | 2026-07-19 | (Error/edge-case behavior) How should malformed or mid-edit Go/Rust source be handled? | **RESOLVED (2026-07-19):** same tolerant tree-sitter behavior as every other language, no new detection/reporting (A5). Confirmed by the user. |
| C6 | 2026-07-19 | (Data & content) What happens to an empty `.go`/`.rs` file (no definitions)? | Resolved directly: a `File` node with zero definitions, not `unparsed` — mirrors existing empty-file handling for other languages (A6, AC-1.8/AC-2.8). |
| C7 | 2026-07-19 | (Roles & permissions) Does this feature introduce any auth/role concept? | N/A — local dev tool, no auth/roles, consistent with every prior feature. |
| C8 | 2026-07-19 | (Out-of-scope confirmation) Is Windows compatibility folded into this spec? | No — explicitly deferred to feature 2 of 2, per the user's own framing. See §6. |
| C9 | 2026-07-19 | (Error/edge-case behavior) What happens when an import path's trailing segments match more than one directory candidate in the repo? | Resolved directly: no edge is guessed — absence over a wrong link, mirroring the git-inference non-negotiable's ambiguity rule (A7, AC-3.3/AC-4.3). |
| C10 | 2026-07-19 | (UX flows) Does this feature have any UI states to define? | N/A — headless CLI/MCP tool; output is the same JSON/graph surface that already exists. |

## 8. Design Review

**N/A — with reason.** Both extractors are headless: source bytes in, a
`FileExtraction` dataclass out (`base.py`'s existing contract), consumed by
`build.py` exactly as the four existing languages already are. No new CLI
command, no new MCP tool, no change to output format beyond additional
`language` values (`"go"`, `"rust"`) already extensible in the model's JSON.
There is no graphical UI, so this section stays N/A unless a future
Go/Rust-specific query surface is added.

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
- [x] Clarify pass done: no ambiguity left unresolved or unparked *(all ambiguities are recorded and resolved by the user on 2026-07-19, see §3/§7)*
- [x] Open questions are resolved or explicitly accepted as risk *(Q1–Q5 all resolved by the user on 2026-07-19 — see §3)*
- [x] Out-of-scope section is filled (something was consciously cut)
- [x] Constitution (`.spark/constitution.md`) respected — N/A, no constitution exists for this project
- [x] Design review done for UI-facing features (or marked N/A with reason)
- [x] Status set to `approved` by the user *(2026-07-19)*
