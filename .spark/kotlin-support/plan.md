# Plan: kotlin-support

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Plan |
| **Owner** | Engineering Manager (`/sprint-plan`) |
| **Input** | `.spark/kotlin-support/spec.md` (`approved`, 2026-11-10) |
| **Status** | `approved` |
| **Date** | 2026-11-10 |

<!-- Handoff: read this block first, the numbered sections below by exception. Whoever
     writes to this plan updates it in the same edit that changes a task's status or
     the plan's own status: overwrite in place, never append. The block holds one
     current state, never a per-round log; a stale block is a defect, not a cosmetic
     issue. -->

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Summary:** Kotlin is a sixth registry-entry extractor (`code_kotlin.py`, pure, single-file) plus a `package.Name` symbol index in `build.py`; companion members flatten onto the class, extensions are top-level `Recv.name`, star imports never resolve. Already on the branch (5cc459a, 9bc4679) for T1–T5; T6–T12 close the gaps against the spec.
- **Open:** `none` — all tasks T1–T12 `done` (see §3 Task Breakdown; deviations at the end)
- **Binding ruling:** §3 Task Breakdown for current task status; a plan revision after review/QA findings updates §1/§3 in place, never a new section
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Architecture Decision

- **Context:** Adding a language has a five-times-repeated pattern (`constitution.md §9`
  module structure; re-read from source because the feature touches exactly this area,
  rule (a)): a pure extractor (`bytes in → FileExtraction out`, no graph access), an
  `EXTENSION_LANGUAGE` entry in `extractors/base.py`, a `_REGISTRY` entry in
  `extractors/__init__.py`, and a per-language branch in `build.py::_resolve_imports`.
  `cli.py`/`server.py` contain no language names (grep-verified), so NFR-3 holds as long
  as work stays in the extractor + `build.py` seam. Java is the closest precedent
  (package + FQN index); Go is the precedent for receiver-qualified top-level functions.
  The implementation already exists on this branch (5cc459a feat, 9bc4679 chore); this
  plan records its architecture and adds the tasks the spec still needs.

  Kotlin-specific *how* questions the spec left open: how a `companion object` is
  represented, how an extension function is named, and how imports address files
  (Kotlin imports name a *declaration* — class, object, top-level function — not a file,
  and a package spans many files with no directory rule).

- **Decision:** `code_kotlin.py` walks the tree once: `class_declaration` and
  `object_declaration` (class, data/sealed/enum class, interface, object) become `Class`
  (A1); `function_declaration` becomes `Function`, nested via `parent` when inside a
  `class_body`/`enum_class_body`; a `companion_object` is walked **transparently** — its
  members get the enclosing class as `parent` (`Widget.make`), no `Companion` node; an
  extension function at top level is named `Recv.name` (generics and `?` stripped) with
  `parent=None`; function bodies are never descended (local functions, object literals
  dropped, A4). Imports are captured raw from the `qualified_identifier` (alias dropped,
  star kept as `pkg.*`). `build.py` adds `_kotlin_symbol_index` (`package.TopLevelName →
  relpath`, extensions excluded) and `_resolve_kotlin_import`: star → none; exact key →
  file; else owner fallback (`pkg.Outer.Inner`, `pkg.Obj.member` → owner's file). **T6
  changes the index from first-writer-wins to exactly-one-distinct-file**, because
  AC-1.6 requires an ambiguous path to give no edge (constitution §1 "honest absence").
  `_add_definitions`, `cli.py`, `server.py`, `queries.py`, `model.py` are unchanged.

- **Alternatives considered:**
  | Alternative | Why rejected |
  |---|---|
  | **Companion object as its own `Class` node** (`Widget.Companion`, members under it). | A4/C2 resolved that companion members nest under the enclosing class. Callers write `Widget.make()`, so `Widget.make` is the qualname a reader searches for; a `Companion` layer adds a node kind-in-disguise with no query need, and named companions (`companion object Factory`) would make qualnames unstable across a rename. |
  | **Extension functions nested under the receiver's `Class` when it is declared in the same file** (the go-rust A2 rule). | Spec C2/AC-1.3 says extensions are top-level `Function`s. Kotlin extensions are statically dispatched free functions, not members; nesting them would also collide with a real member of the same name. `Recv.name` keeps the receiver visible for search without a `contains` edge from a class that does not own it. |
  | **Extension functions as bare `name`.** | Two extensions `String.f` and `Int.f` in one file would share one node id; the receiver prefix keeps ids distinct at zero cost. |
  | **Star-import fan-out to every file of the package** (Go-style: an import addresses a package, link all its files). | A3/AC-1.6 says star imports are not resolved. A Kotlin package is not a directory, so fan-out would link every file declaring that package — on Android, often dozens — turning `impact` into noise. Go fans out because its import *is* a directory; Kotlin's is not. |
  | **Directory-path index** (resolve `a.b.C` to `**/a/b/C.kt`, Java-style source layout). | Kotlin does not require the directory to match the package, and file names need not match declarations (`Utils.kt` holding many top-level functions). Using the parsed `package_header` + declared names is exact and costs one dict. |
  | **Keep first-writer-wins on index collisions** (the shipped 5cc459a behaviour, and Java's). | Violates AC-1.6 ("a path matching more than one in-repo file … no edge"): it links to whichever file sorts first, a confident wrong edge. T6 replaces it. Java's index is left alone (out of scope). |
  | **Parse Gradle / resolve via build files.** | Out of scope (§6, A3); also network/toolchain-free determinism forbids running Gradle. |

- **Consequences:**
  - *Easier:* the extractor is unit-testable on raw bytes; determinism and the parse
    cache are untouched by construction; CLI≡MCP parity is free (data-driven dispatch).
  - *Harder / accepted:* imports of an extension function by name (`import pkg.shout`)
    do not resolve, because extensions are indexed by `Recv.name` — honest absence,
    documented in README (T11). A member and a same-file extension with the same
    `Recv.name` share one node id (two `contains` parents, no dangling edge) — rare,
    accepted (R4). The owner fallback can in theory link `import x.y.z` to a file whose
    package is `x` and which declares `y`; acceptable for a best-effort tier.

## 2. Affected Components

Scoped by hand from reading the branch's code and tests (no tool file was passed, so no
blast-radius query was run). Stack and module layout from `constitution.md §3/§9`.

**New dependency (justified):** `tree-sitter-kotlin==1.1.0` — the tree-sitter-grammars
Kotlin grammar. Hand-writing a Kotlin parser fails the "40 lines ourselves" bar by orders
of magnitude. Pinned `==` (constitution §3 off-limits rule) and locked in `uv.lock`;
1.1.0 exposes `tree_sitter_kotlin.language()` and loads under `tree-sitter==0.26.0`
(spike A2). No other new dependency, service or pattern.

**New files:** `src/aspark_graph/extractors/code_kotlin.py`, `tests/test_extractor_kotlin.py`.

**Modified files:**
- `src/aspark_graph/extractors/base.py` — `.kt`/`.kts` → `"kotlin"`.
- `src/aspark_graph/extractors/__init__.py` — import + `_REGISTRY["kotlin"]`.
- `src/aspark_graph/build.py` — `_kotlin_symbol_index`, `_resolve_kotlin_import`, one
  `elif` in `_resolve_imports` (T6 reworks the index).
- `src/aspark_graph/parse_cache.py` — T10 adds `tree-sitter-kotlin` to `_version_tag()`.
  Today the key lists only core + python/typescript/java grammars, so a Kotlin pin bump
  under an unchanged tool version would reuse stale cached extractions.
- `pyproject.toml`, `uv.lock` — the pin.
- `README.md`, `tests/test_readme.py` — Supported languages, design guarantees,
  out-of-scope, known limits (T11).
- `tests/test_extractor_java.py`, `tests/test_build.py` — multi-language and
  double-build fixtures include `.kt`.

**Untouched (NFR-3 guard):** `cli.py`, `server.py`, `queries.py`, `model.py`,
`graph.py`, `artifacts.py`, `inference.py`, `confinement.py`.

**Outside this plan (finding, not a task):** `CLAUDE.md` ("five tree-sitter grammars",
extractor list) and `constitution.md §3` ("the five grammars", stack list) go stale
when this ships; the constitution is amended only via `/charter` (R6).

## 3. Task Breakdown

<!-- T1 is the walking skeleton (a .kt file becomes a parsed File node end-to-end). T1–T5
     are verified present on the branch by reading code + tests (5cc459a); tests were not
     executed at plan time, T12 runs the full suite. T6–T12 are the spec gaps. -->

| # | Task | Story | Covers (AC / NFR) | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|---|
| T1 | **Walking skeleton: pin, registry, dispatch.** Pin `tree-sitter-kotlin==1.1.0`, lock it, map `.kt`/`.kts` to `"kotlin"`, register `code_kotlin.extract`, emit `language="kotlin"` and `package` from `package_header`. | US-1 | AC-1.1, NFR-1, NFR-3 | – | `done` | pyproject.toml pins tree-sitter-kotlin==1.1.0 and uv.lock locks it; test_kotlin_dispatch_for_kt_and_kts proves .kt and .kts map to kotlin with a registered extractor; test_kotlin_empty_file_is_not_unparsed proves an empty .kt builds as a non-unparsed File; grep finds no "kotlin" in cli.py or server.py — files: pyproject.toml, uv.lock, src/aspark_graph/extractors/base.py, src/aspark_graph/extractors/__init__.py, src/aspark_graph/extractors/code_kotlin.py, tests/test_extractor_kotlin.py |
| T2 | **Extractor definitions.** Fold class/data class/object/interface/enum class into `Class`; top-level and member `fun` into `Function`; companion members flattened onto the enclosing class; extensions as top-level `Recv.name`; nested classes nest; function bodies not descended; `private` drives `exported=False`. | US-1 | AC-1.2, AC-1.3, AC-1.4 | T1 | `done` | test_kotlin_extractor_finds_package_and_classes, test_kotlin_extractor_finds_functions, test_kotlin_companion_members_nest_under_enclosing_class (Widget.make, parent Widget, no Companion), test_kotlin_extension_functions_are_top_level_by_receiver (String.shout, List.second, parent None), test_kotlin_local_functions_are_not_captured and test_kotlin_kts_script_parses exist; test_build_resolves_kotlin_import_and_contains proves File→Class and Class→member contains edges (EXTRACTED via the shared _add_definitions) — files: src/aspark_graph/extractors/code_kotlin.py, tests/test_extractor_kotlin.py |
| T3 | **Import capture + in-repo resolution.** Capture imports raw (alias dropped, star as `pkg.*`); `_kotlin_symbol_index` over top-level non-extension names; `_resolve_kotlin_import` with star→none, exact match, owner fallback; `elif "kotlin"` branch in `_resolve_imports`. | US-1 | AC-1.5, AC-1.6 | T2 | `done` | test_kotlin_imports_raw proves Helper, util.* and the alias's original path Fmt are captured; test_build_resolves_kotlin_import_and_contains proves an imports edge Widget.kt→Helper.kt and exactly one imports edge despite a star and a java.util import; test_kotlin_unresolvable_import_makes_no_edge proves an external import yields none — files: src/aspark_graph/extractors/code_kotlin.py, src/aspark_graph/build.py, tests/test_extractor_kotlin.py |
| T4 | **README language lists.** Name Kotlin in Supported languages (`.kt`/`.kts`, kinds, star imports unresolved, no expect/actual), the Deterministic guarantee's grammar list, and Out of scope's current-support sentence. | US-1 | AC-1.10 | T1 | `done` | README.md Supported languages, Design guarantees and Out of scope each name Kotlin; test_current_names_ac_6_1_five_languages_stated asserts the six-name list and test_current_names_ac_6_1_no_six_language_count still holds — files: README.md, tests/test_readme.py |
| T5 | **Kotlin in the shared multi-language and double-build fixtures.** | US-1 | AC-1.8, AC-1.9 | T2 | `done` | test_all_languages_in_one_build includes f.kt (language kotlin, definition f, no unparsed File); test_double_build_seven_language_repo_is_deterministic and test_kotlin_build_is_deterministic include Kotlin files and compare to_dict of two builds — files: tests/test_extractor_java.py, tests/test_build.py, tests/test_extractor_kotlin.py |
| T6 | **Ambiguous imports give no edge.** Change `_kotlin_symbol_index` to map each key to the sorted set of distinct relpaths declaring it; `_resolve_kotlin_import` returns a file only when exactly one distinct relpath matches (exact key, then owner fallback under the same rule). A class and a same-named factory function in one file stay one relpath, so they still resolve. Update the docstring. | US-1 | AC-1.5, AC-1.6, NFR-2 | T3 | `done` | A build test with two files in package p both declaring top-level Dup and a third file importing p.Dup has zero imports edges from the importer; a test with class Foo plus fun Foo in one file still yields the imports edge to that file; T3's tests stay green; Java/Go/Rust/Python resolution code is unchanged in the diff — files: src/aspark_graph/build.py, tests/test_extractor_kotlin.py |
| T7 | **Aliased import resolves by its original path (build level).** | US-1 | AC-1.5 | T3 | `done` | A build test where Widget.kt contains import com.example.util.Helper as H has an imports edge Widget.kt→Helper.kt; if it fails, the fix is confined to _add_import in code_kotlin.py — files: tests/test_extractor_kotlin.py, src/aspark_graph/extractors/code_kotlin.py |
| T8 | **Malformed input and one-line class bodies never error; no dangling edges.** | US-1 | AC-1.7, NFR-7, NFR-2 | T2 | `done` | Tests prove: a repo with class A { fun f() {} } on one line builds without exception and its File node is kotlin and not unparsed (no assertion on members); a .kt of garbage tokens plus invalid UTF-8 bytes builds the same way; the CLI build command on that repo exits 0 with no "Traceback" on stderr (same harness as tests/test_walking_skeleton.py); for a build of the SOURCE fixture every contains and imports edge's source and target is a node carrying a type attribute — files: tests/test_extractor_kotlin.py |
| T9 | **Multi-language completeness and empty-file shape.** Extend the all-languages build with `.js`, `.kts` and `.rb`; assert the empty `.kt` details. | US-1 | AC-1.1, AC-1.8 | T5 | `done` | test_all_languages_in_one_build also writes g.js and h.kts (each a language-tagged File with its definition, none unparsed) and x.rb, asserted as the only unparsed File; an empty .kt File node has language kotlin and zero outgoing contains edges — files: tests/test_extractor_java.py, tests/test_extractor_kotlin.py |
| T10 | **Parse-cache key covers the Kotlin grammar.** Add `:tree-sitter-kotlin=<version>` to `_version_tag()` so a pin bump forces a full rescan. | US-1 | NFR-1 | T1 | `done` | A test asserts _version_tag() contains "tree-sitter-kotlin=1.1.0"; existing tests/test_incremental.py cache tests stay green; graph.json is not affected (key lives only in parse-cache.json) — files: src/aspark_graph/parse_cache.py, tests/test_incremental.py |
| T11 | **README known limits.** Under Supported languages state: a class body opened and closed on one line may lose or misplace members; an import alias is ignored (resolved by original path); extension functions imported by name are not resolved; ambiguous paths give no edge. | US-1 | AC-1.7, AC-1.10 | T6 | `done` | README.md Supported languages contains the four limit statements; a test_readme.py test asserts the one-line class body limit is stated; the README language-list tests still pass — files: README.md, tests/test_readme.py |
| T12 | **Regression proof and full suite.** Build a fixed non-Kotlin fixture (the six-language fixture minus f.kt, plus a git-archive export of dd4b994's tree, which has no .kt files) with pre-change code at dd4b994 (worktree or stash round-trip) and with the branch HEAD, each with `--full` into separate output dirs, and diff the two graph.json files. Run `uv run pytest`, `uv run pytest -m slow`, the CLI≡MCP parity suite, and grep the adapters. | US-1 | AC-1.9, NFR-1, NFR-3, NFR-4 | T6, T7, T8, T9, T10, T11 | `done` | Both graph.json pairs are byte-identical (cmp exit 0); the old and new SHAs, fixture description and sha256 of each graph.json are recorded in the T12 commit message; uv run pytest and uv run pytest -m slow are green; test_cli_mcp_parity.py is green; git diff dd4b994 -- src/aspark_graph/cli.py src/aspark_graph/server.py is empty |

NFR-5 (security) and NFR-6 (accessibility) are N/A per spec; confinement and build bounds
apply unchanged and are re-run by T12's full suite.

## 4. Test Strategy

Headless tool: `/demo-day` is structurally N/A (constitution §8); the QA-equivalent
(full suite + slow, clean-env wheel install, `serve` boot without the lock, byte-identical
build, real-repo `impact`) runs in `/peer-review`.

- **Unit (extractor, raw bytes, no graph)** — `test_extractor_kotlin.py`: kind folding
  (AC-1.2), top-level and extension functions (AC-1.3), member and companion nesting,
  local functions dropped (AC-1.4), raw imports incl. alias and star (AC-1.5/1.6), `.kts`.
  Primary guard against grammar node-shape surprises (R1).
- **Integration (`build_graph(tmp_path)`)** — import resolution: positive, alias (T7),
  external, star, ambiguous (T6); contains wiring; one-line body, malformed bytes, and
  an edge-integrity sweep (T8, NFR-2); empty `.kt` (T9).
- **Multi-language** — seven languages plus `.rb` unparsed in one build (AC-1.8, T9).
- **Determinism** — double-build fixtures with `.kt` (AC-1.9 first half, T5); the
  pre-change byte-identity proof for a non-Kotlin repo (AC-1.9 second half, NFR-1, T12) —
  a double build alone cannot prove that (CLAUDE.md).
- **CLI edge** — CLI `build` on malformed Kotlin exits 0 without traceback (NFR-7, T8).
- **Parity / regression** — existing parity suite unchanged (NFR-3); full and slow suites
  (NFR-4) in T12.
- **Deliberately not automated:** member capture inside a one-line class body (grammar
  limit, documented only, AC-1.7); expect/actual, Gradle, `calls` edges (out of scope).

## 5. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| **R1 — Grammar node shapes** (`companion_object`, `enum_class_body`, receiver types as `user_type`/`nullable_type`, `import` with alias) differ from assumptions or shift between grammar versions. | Missing or mis-parented definitions; alias captured as the module. | Exact `==` pin (NFR-1); unit tests written against real parses (T2/T3); T7 covers alias at build level; T10 makes a pin bump invalidate the parse cache. |
| **R2 — One-line class body mis-parse** (spike A2) is common in small data holders. | Members missing or misplaced in such files. | Accepted known limit (AC-1.7); T8 proves no error; T11 documents it. No workaround (spec §6). |
| **R3 — Package collisions in large Android repos** (same `package.Name` in flavour/variant source sets, e.g. `src/debug` and `src/release`). | With the shipped first-writer-wins index: a confident wrong `imports` edge. | T6 switches to exactly-one-file resolution: such imports give no edge (honest absence, AC-1.6). |
| **R4 — Node-id collision:** a class member `Foo.bar` and a same-file extension `fun Foo.bar()` share one definition id. | One merged node with two `contains` parents; not dangling, slightly wrong shape. | Accepted (rare; Kotlin resolves the member first anyway). Log in `.spark/BACKLOG.md` at `/peer-review` if seen in a real repo. |
| **R5 — Implementation preceded the plan** (5cc459a). Planning after the fact risks rubber-stamping. | Gaps vs. the spec slip through as `done`. | T1–T5 marked `done` only for code and tests read in this pass; every unverified AC part is a `todo` (T6–T12); T12 runs the suite and the pre-change proof. |
| **R6 — Doc drift:** CLAUDE.md and `constitution.md §3` say "five grammars" and list five languages. | Agents read a stale constraint list. | Out of spec scope; raise at `/peer-review`; constitution amendment via `/charter`, CLAUDE.md update at `/go-live`. |
| **R7 — Inherited assumptions** A1 (fold into `Class`), A3 (best-effort, no Gradle, alias ignored, star unresolved), A4 (companion flattening, local functions dropped). | Lower import coverage than a user might expect (also extension-by-name imports, §1). | User-accepted spec decisions; documented in README (T4, T11); revisit only through a new SPARK loop. |

---

## ✅ PLAN GATE

*All boxes checked → `/increment` may start. Any box open → back to `/sprint-plan`.*

- [x] Spec status is `approved` (never plan against a draft)
- [x] Architecture decision includes rejected alternatives (a decision without alternatives is a guess)
- [x] Architecture respects the constitution's technical constraints (`==` pin, no network, thin adapters, honest absence via T6; doc drift in §3 "five grammars" recorded as R6)
- [x] Every task maps to a user story — no orphan tasks, no story without tasks
- [x] Every Must AC and every applicable NFR is covered by at least one task
- [x] Every task has a checkable definition of done
- [x] Task order respects dependencies
- [x] Test strategy covers every Must story
- [x] Line budget respected: Ist 179 / Soll ~300 (excluding HTML comments) — self-reported, no linter checks this
- [x] Status set to `approved` by the user

## Deviations

- T9: an unknown extension (`.rb`) is skipped by the build entirely (no `File` node, not in `report.unparsed`); "unparsed" applies only to known-but-unsupported languages. The test asserts exactly that, which is what AC-1.8's "stays unparsed" means in practice.
- T12: pre-change proof built a git-initialised five-language fixture with `dd4b994` and with HEAD (`--full`); `graph.json` byte-identical, sha256 `cb658012de978cc0f2f2bf3c7e77f5555b2271c0090b61dc2b768f61e2fae2e7`; `cli.py`/`server.py` diff vs `dd4b994` is empty.
