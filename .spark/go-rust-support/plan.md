# Plan: go-rust-support

| | |
|---|---|
| **Phase** | Plan |
| **Owner** | Engineering Manager (`/sprint-plan`) |
| **Input** | `.spark/go-rust-support/spec.md` (`approved`, 2026-07-19) |
| **Status** | `approved` |
| **Date** | 2026-07-19 |

## 1. Architecture Decision

<!-- Mini-ADR. The EM decides — but shows the alternatives that were rejected and why. -->

- **Context:** The codebase already has a proven, four-times-repeated pattern
  for adding a language: a pure per-language extractor module (`bytes in →
  `FileExtraction` out`, no graph access — `base.py`), a data-driven registry
  entry (`EXTENSION_LANGUAGE` in `base.py` + `_REGISTRY` in
  `extractors/__init__.py`), and a per-language branch in `build.py`'s
  `_resolve_imports`. `cli.py`/`server.py` contain zero per-language code
  (verified by grep — no matches for any language name), so NFR-4 is
  structurally satisfied as long as new work stays inside the extractor +
  `build.py` seam. `code_java.py` is the closest precedent: it folds
  `interface`/`enum`/`record` into `Class`, nests methods under their type's
  `Class`, and resolves imports via an FQN index built in `build.py`.

  The one genuinely new decision the spec resolved the *what* but not the
  *how* for is A2 (§3): a Go receiver-method or a Rust `impl`-block function
  whose target type lives in the **same file** must nest under that type's
  `Class`; one whose target type lives in a **different file** (or is a foreign
  type) must become a top-level `Function` — never a `contains` edge to a
  node id that does not exist (NFR-2). The build's `contains` wiring
  (`_add_definitions`) derives the parent id from `definition_id(relpath,
  d.parent)` using the *current file's* relpath, so a `parent` qualname that is
  not declared in that same file would point at a nonexistent node.

- **Decision:** Implement the same-file/cross-file distinction **entirely
  inside each single-file extractor**, using only that file's own declarations.
  Each extractor does a cheap per-file two-pass: first collect the set of type
  names declared in this file, then, when emitting a receiver-method /
  impl-block function, set `parent = TypeName` only if `TypeName` is in that
  same-file set, else `parent = None` (top-level `Function`). `build.py`'s
  `_add_definitions` is left **unchanged** — it keeps trusting that any
  non-`None` `parent` names a definition in the same extraction (which is now
  guaranteed by construction, exactly as it already is for Python/TS/Java).
  Node-kind folding follows the Java precedent (A1): Go `struct`/`interface`
  and Rust `struct`/`enum`/`trait` all become `Class`; no new `NodeType`.
  Import resolution adds two new `build.py` index builders + two new branches
  in `_resolve_imports`, mirroring the Java FQN-index shape (A3, best-effort,
  in-repo-only, no manifest parsing). Wiring is two lines in `base.py` and two
  in `extractors/__init__.py`; `cli.py`/`server.py` are untouched (NFR-4).

- **Alternatives considered:**
  | Alternative | Why rejected |
  |---|---|
  | **Two-pass cross-file type index in `build.py`** (parse all files first, build a repo-wide type→file index, then resolve receiver/impl targets against it so cross-file methods *nest* under their real `Class`). | Explicitly deferred by the spec (§6 "Cross-file `Class` nesting via a full type index"; A2/Q2 resolved). It is strictly more scope, changes `build.py`'s orchestration from single-pass-per-file to a two-phase resolve, and AC-1.4/AC-1.5/AC-2.4/AC-2.5 are written in literal "same file"/"different file" terms that the single-file approach satisfies exactly. YAGNI — no query need stated. |
  | **Drop cross-file receiver/impl methods entirely** (emit only same-file-nestable ones). | Loses real `extracted`-tier structure that the spec wants captured (AC-1.5/AC-2.5 require the method to *still be captured* as a top-level `Function`). Idiomatic Go splits a type's methods across files constantly; silently dropping them would leave large gaps in `impact`'s blast radius for the exact repos this feature targets. |
  | **Preserve struct/interface/trait as new `NodeType`s** (or a `kind` sub-attribute). | A1/Q1 resolved to fold into `Class`. `NodeType` is shared vocabulary consumed by every query in `queries.py`; adding kinds is a global, cross-cutting change with no stated downstream need. The Java interface/enum/record precedent already sets the folding convention — deviating would be an unrequested architecture change. |
  | **Emit `parent` unconditionally from the receiver type name, let `build.py` skip dangling edges.** | Violates NFR-2 (no silently-wrong graph) by pushing correctness into a defensive filter, and would still drop the method rather than re-home it as a top-level `Function`. The extractor already has exactly the information it needs; deciding at emit time is both simpler and stronger. |

- **Consequences:**
  - *Easier:* extractors stay pure and single-file, so both are unit-testable
    with raw bytes and no graph (same as the existing three test files);
    `build.py`'s `_add_definitions` and its determinism/caching invariants are
    untouched; parity (NFR-4) is free because dispatch stays data-driven.
  - *Harder / accepted cost:* a receiver method and its type declared in
    different files of the same package will read as a top-level `Function`
    rather than nested under its `Class` — a known, spec-sanctioned fidelity
    gap (§6), not a bug. Import resolution stays best-effort and will miss
    manifest-dependent cases (module-path prefixes, workspaces) by design (A3).
    Each extractor carries a small per-file "types declared here" pre-pass,
    a minor departure from Python/TS's pure single-walk (but identical in
    spirit to Java's body-scoped member walk).

## 2. Affected Components

**New dependencies (each a liability — justified):**

- `tree-sitter-go` — the official tree-sitter Go grammar. Justification: parsing
  Go without a grammar is a non-starter; hand-rolling a Go parser is orders of
  magnitude more code and risk than the 40-lines-ourselves bar. Must be pinned
  `==` (NFR-1 / CLAUDE.md determinism non-negotiable) at a version whose ABI is
  compatible with the pinned `tree-sitter==0.26.0` core and that exposes
  `tree_sitter_go.language()` (same contract as the three existing grammars).
- `tree-sitter-rust` — the official tree-sitter Rust grammar. Same
  justification and same `==`-pin + ABI-compatibility requirement.

  *Exact versions are selected and verified in T1 (must import and parse under
  `tree-sitter==0.26.0`), then pinned `==` in `pyproject.toml` and locked in
  `uv.lock`.* No other new dependency, service, or pattern is introduced.

**New files:**
- `src/aspark_graph/extractors/code_go.py`
- `src/aspark_graph/extractors/code_rust.py`
- `tests/test_extractor_go.py`
- `tests/test_extractor_rust.py`

**Modified files:**
- `src/aspark_graph/extractors/base.py` — two entries in `EXTENSION_LANGUAGE`
  (`.go` → `"go"`, `.rs` → `"rust"`). No dataclass change: `Definition`,
  `Import`, `FileExtraction` (incl. the reused `package` field for Go, `None`
  for Rust) already suffice.
- `src/aspark_graph/extractors/__init__.py` — import the two modules; two
  `_REGISTRY` entries (`"go"`, `"rust"`).
- `src/aspark_graph/build.py` — add `_go_package_index` + `_rust_module_index`
  builders and two `elif` branches in `_resolve_imports` (US-3/US-4 only).
- `pyproject.toml` / `uv.lock` — the two `==`-pinned grammar deps.
- `tests/test_extractor_java.py::test_all_three_languages_in_one_build` (or a
  new sibling test) — extended to six languages for AC-5.1.
- `tests/test_build.py` determinism tests — fixture extended with `.go`/`.rs`
  for AC-1.7/AC-2.7.

**Untouched (NFR-4 guard):** `cli.py`, `server.py`, `queries.py`, `model.py`,
`graph.py`, `parse_cache.py`, `artifacts.py`, `inference.py`.

## 3. Task Breakdown

<!-- Ordered. T1 is the walking skeleton: a .go/.rs file becomes a parsed (non-unparsed) File node end-to-end, killing the "does the grammar import/parse under our pinned core" integration risk first. -->

| # | Task | Story | Covers (AC / NFR) | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|---|
| T1 | **Walking skeleton: grammar deps + registry wiring + empty-file path.** Select and `==`-pin `tree-sitter-go`/`tree-sitter-rust` versions that import and parse under `tree-sitter==0.26.0`; update `uv.lock`. Add `.go`→`"go"`, `.rs`→`"rust"` to `EXTENSION_LANGUAGE`. Create minimal `code_go.py`/`code_rust.py` that parse the source and return a `FileExtraction` with the correct `language` (and Go `package` from the `package_clause`) but zero definitions yet. Register both in `_REGISTRY`. | US-1, US-2, US-5 | AC-1.8, AC-2.1, AC-2.8, AC-5.2, NFR-1 | – | `done` | `uv sync` resolves; a build of a repo with a bare `package foo` `.go` file and an item-less `.rs` file produces `File` nodes with `language="go"`/`"rust"`, zero definitions, **no** `unparsed` flag; a `.rb` file still becomes `unparsed: true` (AC-5.2 unchanged). Both grammar deps pinned `==` in `pyproject.toml`. |
| T2 | **Go extractor: types, functions, same/cross-file methods, exported.** In `code_go.py`, two-pass per file: collect declared type names, then emit `Class` for each `type X struct/interface` (fold both into `Class`, A1), `Function` for each free `func` (`parent=None`), and for each `method_declaration` set `parent=ReceiverType` iff that type is declared in this same file, else `parent=None`. Set `exported` from Go capitalization (uppercase first letter). Write `test_extractor_go.py` at `test_extractor_java.py` granularity. | US-1 | AC-1.1, AC-1.2, AC-1.3, AC-1.4, AC-1.5, AC-1.6, NFR-2, NFR-3 | T1 | `done` | `test_extractor_go.py` proves: struct+interface→`Class`; free func→top-level `Function`; same-file receiver method nests under its type's `Class`; a receiver method whose type is declared in a *different* file lands as a top-level `Function` with `parent=None` (no dangling edge); `exported` matches capitalization; all `contains` edges carry `Confidence.EXTRACTED`. |
| T3 | **Rust extractor: struct/enum/trait, functions, impl blocks, `pub`.** In `code_rust.py`, same two-pass: collect declared type names (`struct_item`/`enum_item`/`trait_item`→`Class`), emit free `function_item`→`Function` (`parent=None`), and for each `impl_item`, emit its inner `function_item`s with `parent=TargetType` iff that type is declared in this same file (handling *multiple* `impl` blocks for one type), else `parent=None`. Set `exported` from presence of a `visibility_modifier` (`pub`). Write `test_extractor_rust.py`. | US-2 | AC-2.2, AC-2.3, AC-2.4, AC-2.5, AC-2.6, NFR-2, NFR-3 | T1 | `done` | `test_extractor_rust.py` proves: struct/enum/trait→`Class`; free fn→top-level `Function`; funcs from one *or more* same-file `impl` blocks nest under the type's `Class`; a func in an `impl` on a foreign/other-file type lands as a top-level `Function` (no dangling edge); `pub` drives `exported`; edges carry `Confidence.EXTRACTED`. |
| T4 | **Go in-repo import resolution.** Add `_go_package_index` (map repo directory/package path segments → the `.go` files in that dir) and a `"go"` branch in `_resolve_imports` that resolves each import path by unambiguous trailing-segment match, emitting `imports` (`EXTRACTED`) edges to the repo files in the matched package dir; standard-library/third-party paths and ambiguous (multi-candidate) matches emit no edge. | US-3 | AC-3.1, AC-3.2, AC-3.3, NFR-2, NFR-3 | T2 | `done` | `build_graph(tmp_path)` tests (Java-import-test style) prove: two in-repo Go files with a matching import path get an `imports` edge; an unresolvable stdlib/third-party import gets none; an import whose trailing segments match >1 repo dir gets none. Every emitted edge's endpoints exist in the graph. |
| T5 | **Rust in-repo import resolution.** Add `_rust_module_index` (module-path index from file/directory layout: crate root, `mod.rs`/`foo.rs`) and a `"rust"` branch resolving `crate::`/`self::`/`super::`-relative `use` paths to a repo file; external crates and ambiguous matches emit no edge. | US-4 | AC-4.1, AC-4.2, AC-4.3, NFR-2, NFR-3 | T3 | `done` | `build_graph(tmp_path)` tests prove: an in-repo `use crate::…`/`self::`/`super::` path yields an `imports` (`EXTRACTED`) edge; `use serde::…` (external) yields none; an ambiguous `use` path yields none. All edge endpoints exist. |
| T6 | **Six-language regression, determinism, parity, full suite.** Extend the "languages in one build" integration test to include a `.go` and a `.rs` file (all six languages, none `unparsed`). Extend the double-build determinism fixture (`test_build.py`) with `.go`/`.rs` files. Grep-confirm `cli.py`/`server.py` gained no per-language code; run the existing CLI≡MCP parity suite. Run the full suite incl. `-m slow`. | US-5, US-1, US-2 | AC-1.7, AC-2.7, AC-5.1, AC-5.3, AC-5.4, NFR-1, NFR-4, NFR-5, NFR-6, NFR-9 | T2, T3, T4, T5 | `done` | Six-language build test green (each file language-tagged with defs, none `unparsed`); double-build of a Go/Rust-containing repo is byte-identical; `uv run pytest` green with zero regressions to the four existing extractor tests; `uv run pytest -m slow` green (NFR-1 bench + MCP transport); `cli.py`/`server.py` diff shows only (or zero) non-language changes; `report.summary()` counts Go/Rust files (NFR-9). |

## 4. Test Strategy

Headless tool — there is no browser QA; the QA-equivalent runs in
`/peer-review` (full suite, clean-env install, `serve` boot, byte-identical
build, real-repo `impact`). `/demo-day` is structurally N/A (CLAUDE.md).

- **Unit (per-extractor, no graph)** — `test_extractor_go.py` /
  `test_extractor_rust.py`, at `test_extractor_java.py` granularity. Cover, per
  language: type folding into `Class` (AC-1.2/AC-2.2), free functions
  (AC-1.3/AC-2.3), same-file method/impl nesting incl. multiple Rust `impl`
  blocks (AC-1.4/AC-2.4), cross-file/foreign method → top-level `Function`
  with no dangling edge (AC-1.5/AC-2.5), `exported` via Go capitalization /
  Rust `pub` (AC-1.6/AC-2.6), and empty/bare files (AC-1.8/AC-2.8). These are
  the primary guard against grammar-node-shape surprises (top risk R1).
- **Integration (`build_graph(tmp_path)`)** — import-resolution tests in the
  same style as `test_build_resolves_java_import`: positive in-repo resolve,
  external non-resolve, and ambiguous non-resolve, for both Go (AC-3.1–3.3) and
  Rust (AC-4.1–4.3); plus a graph-integrity assertion (every emitted edge
  endpoint exists) covering NFR-2.
- **Multi-language integration** — extend the "languages in one build" test to
  six languages (AC-5.1): every file gets a language-tagged `File` node with
  its definitions, none `unparsed`; `.rb` still `unparsed` (AC-5.2).
- **Determinism** — extend `test_build.py`'s double-build byte-identical
  fixtures with `.go`/`.rs` files (AC-1.7/AC-2.7/NFR-1).
- **Parity & regression** — existing CLI≡MCP parity suite must stay green
  unchanged (NFR-4, no new per-language adapter code); full `uv run pytest`
  green with zero regressions to the four existing languages (AC-5.3); the
  v0.4.0 slow benchmark + MCP transport smoke via `-m slow` (NFR-6).
- **Deliberately not automated:** no browser/manual step — the tool is
  headless; no `calls`-edge or manifest-parsing tests (both out of scope,
  A3/A4).

## 5. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| **R1 — Grammar node-type shapes differ from the existing three grammars.** Go's `method_declaration` `receiver` field, `type_spec` under `type_declaration`, and Rust's `impl_item`/`declaration_list` nesting + `visibility_modifier` are structurally unlike Python/TS/Java trees. | Extractor reads wrong fields → missing or mis-parented definitions. | Write extractors against real parsed trees, not assumptions; the per-language unit test files (T2/T3) are the acceptance guard and are written alongside the extractor. Pin grammars `==` so shapes can't shift under us (NFR-1). |
| **R2 — Grammar/ABI incompatibility with pinned `tree-sitter==0.26.0`.** A chosen grammar version may target a different core ABI. | Build/import fails or parses garbage. | T1 (walking skeleton) verifies import + parse under the pinned core *before* any extractor logic is written — integration risk dies first. Version selection is a T1 DoD gate. |
| **R3 — Rust `impl` block complexity.** `impl Trait for Type`, generic/`where` bounds, multiple `impl`s per type, inherent vs trait impls all funnel functions to one `Class`. | Impl functions mis-parented or dropped. | AC-2.4 explicitly requires multiple same-file `impl` blocks to fold into the one `Class`; a dedicated multi-impl test case in T3. Trait-implementation *as a relationship* is out of scope (§6) — only method containment is modeled. |
| **R4 — Go package-name vs directory-name mismatch / package fan-out.** Go import paths address a *package* (a directory of files), and a package name can differ from its dir name; the edge model is File→File. | Over- or under-linking; ambiguous or noisy `imports` edges. | A3 fixes the bar at trailing-path-segment directory matching (no `go.mod`); T4 emits edges to the files in the matched package directory and, per A7/AC-3.3, emits **no** edge on any multi-candidate ambiguity — honest absence over a wrong link. Scoped as Should. |
| **R5 — Cross-file same-file heuristic surprises a user** who expects a split-across-files Go type's methods to nest under its `Class`. | Perceived "missing" nesting. | Spec-sanctioned (§6, A2/Q2 resolved by the user): cross-file methods are captured as top-level `Function`s, never dropped, never dangling. Documented as an accepted consequence in §1. |
| **R6 — Inherited assumptions from the spec.** A3 (best-effort, no-manifest imports), A4 (no `calls`), A5 (tolerant malformed parse) are all inherited as-is. | If any proves insufficient in real repos, import coverage/fidelity is lower than a naive user expects. | These are explicit, user-confirmed spec decisions (Q3/Q4/Q5, 2026-07-19) with §6 out-of-scope entries; the plan inherits them without silently widening scope. Revisit only via a new SPARK loop if a concrete need emerges. |

---

## ✅ PLAN GATE

*All boxes checked → `/increment` may start. Any box open → back to `/sprint-plan`.*

- [x] Spec status is `approved` (never plan against a draft)
- [x] Architecture decision includes rejected alternatives (a decision without alternatives is a guess)
- [x] Architecture respects the constitution's technical constraints (no constitution exists; CLAUDE.md non-negotiables — determinism/`==`-pins, fail-loud/no-dangling-edges, `EXTRACTED` confidence tier, thin-adapter/data-driven dispatch — are all honored)
- [x] Every task maps to a user story — no orphan tasks, no story without tasks
- [x] Every Must AC and every applicable NFR is covered by at least one task
- [x] Every task has a checkable definition of done
- [x] Task order respects dependencies
- [x] Test strategy covers every Must story
- [x] Status set to `approved` by the user *(2026-07-19)*
