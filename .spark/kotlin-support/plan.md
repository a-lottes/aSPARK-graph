# Plan: kotlin-support

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Plan |
| **Owner** | Engineering Manager (`/sprint-plan`) |
| **Input** | `.spark/kotlin-support/spec.md` (must be `approved`) |
| **Status** | `approved` |
| **Date** | 2026-11-11 |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Summary:** Kotlin is the sixth pure extractor (`extractors/code_kotlin.py`, tree-sitter-kotlin `==1.1.0`), modelled on Java/Go. Import resolution is in `build.py`. It refuses to link ambiguous FQNs instead of using first-writer-wins.
- **Open:** `5 tasks not done` (T6, T7, T8, T10, T11). See §3 Task Breakdown.
- **Binding ruling:** §3 Task Breakdown holds the current task status. A plan revision after review/QA findings updates §1/§3 in place, never a new section.
- **On conflict:** the numbered body below wins for everything except `Status`. Log the mismatch as a finding at the next `/peer-review` and proceed. Don't stop on it.

## 1. Architecture Decision

- **Context:** Go and Rust (v0.5.0) set the pattern for adding a language. A pure extractor (bytes in, `FileExtraction` out) is registered in `extractors/__init__.py` and `EXTENSION_LANGUAGE`. Cross-file `imports` resolution lives in `build.py`, and the grammar is pinned `==` (constitution §3, §6 determinism). Kotlin has two shapes those languages don't have. First, imports name a *fully-qualified symbol* (class or top-level `fun`) or a package wildcard. They do not name a file or directory. Second, `companion object` and extension functions have no direct `Class`/`Function` analogue. Commit 64a081b already implements most of this. This plan re-grounds it and closes the gaps found on reading it (T6–T8, T10, T11).
- **Decision:**
  1. `code_kotlin.py` folds class, data class, object, interface and enum class into `Class`. Companion members nest under the enclosing class (`Widget.make`). An extension function becomes `Receiver.name`, with its parent being where it is declared. Function bodies are not descended into. The walk recurses through `ERROR` nodes, because tree-sitter-kotlin 1.1.0 wraps some single-line class bodies (`class A { fun m() {} }`) in `ERROR`.
  2. `build.py` resolves imports from two indexes. One maps an FQN (package + class qualname, or package + top-level fun name) to its file. The other maps a package to its files. Exact match comes first, then trailing segments are stripped (`pkg.Outer.CONST` → `pkg.Outer`). A wildcard `pkg.*` fans out to every file in the package.
  3. **Changed by this plan (T6):** an FQN defined in ≥2 *different* files resolves to **no edge**. This replaces the shipped first-writer-wins `setdefault`. Android build variants (`src/debug/…/Config.kt` and `src/release/…/Config.kt`) produce exactly this collision. Constitution §1 ("an ambiguous link is omitted") and the Go/Rust precedent (A7, AC-4.3) bind here. Java's first-writer-wins is a known older precedent, not a model to copy.
- **Alternatives considered:**
  | Alternative | Why rejected |
  |---|---|
  | Resolve imports by path convention (`com/example/Foo.kt` ↔ `com.example.Foo`) | Kotlin doesn't require a file's directory to match its package, and one file holds many top-level symbols. A path rule would miss top-level-fun imports and misfire on files whose directory doesn't match the package. Indexing by declared `package` + definitions is exact and stays offline. |
  | First-writer-wins on FQN collisions (the shipped code, the Java precedent) | It silently picks one source set's file, which is a wrong link presented as `extracted`. That violates constitution §1. Refusing costs one `dict[str, list[str]]` and a length check. |
  | Model `companion object` / `object` as their own node kind, or emit `Widget.Companion.make` | It adds vocabulary to `model.py` that every query and test would have to learn, for no spec gain. AC-1.3 explicitly asks for companion members nested under the enclosing class. |
  | A different grammar (built from source, or another upstream release) | 1.1.0 is a PyPI wheel with abi3 wheels for every platform we ship, including macOS x86_64 (`uv.lock`), so it avoids a repeat of the `cryptography` problem. Building from source needs a compiler at install time. The `ERROR` quirk can be handled in about 3 lines. |
  | Skip `ERROR` subtrees (what the other extractors implicitly do) | Every single-line class body would lose its class and members, and that shape is common in Kotlin (`data class P(val x: Int) { fun f() = x }`). Recovering through `ERROR` is best-effort, and its risk is covered by T11. |
- **Consequences:** Easier: Android/Kotlin-JVM repos get structure in `impact` and `story_trace`, and each new language is again one module plus one resolver. Harder: the `ERROR` walk-through means some declarations depend on grammar error recovery, and a grammar bump could change their shape. That makes a bump a deliberate, version-documented event (README "Design guarantees"). Wildcard detection reads the import's source text, because the grammar doesn't separate `a.b.*` from `a.b`.

## 2. Affected Components

System facts (stack, module layout, pin policy, test practice) come from `constitution.md §9` and §3. They were re-derived from source only for `build.py` and `extractors/`, under rule (a): this feature touches that area.

- **New:** `src/aspark_graph/extractors/code_kotlin.py`, `tests/test_extractor_kotlin.py`.
- **Changed:** `extractors/__init__.py` (registry), `extractors/base.py` (`.kt`/`.kts`), `build.py` (`_kotlin_indexes`, `_resolve_kotlin_import`, Kotlin branch of `_resolve_imports`), `tests/test_build.py`, `tests/test_extractor_java.py`, `README.md`, `tests/test_readme.py`, `CLAUDE.md` (T10).
- **Untouched by design:** `cli.py`, `server.py`, `queries.py`, `model.py`, `artifacts.py`. No new query, node kind or refusal.
- **New dependency:** `tree-sitter-kotlin==1.1.0`. Justification: parsing Kotlin needs a grammar, and writing one ourselves is not a "40 lines" job. It is pinned `==` under constitution §3. It ships abi3 wheels for macOS x86_64/arm64, manylinux x86_64/aarch64, musllinux and Windows (`uv.lock`).
- **Blast radius (graph `impact` on the union of the §3 `files:` paths; I read it in full):** 8 files are in the graph. `CLAUDE.md`, `README.md`, `pyproject.toml` and `uv.lock` are `unknown_files` because non-source files aren't indexed, so I scoped those by hand. It reaches 22 stories across 8 features. Apart from kotlin-support US-1–3 (`declared`), the `declared`/`extracted` hits come through `build.py` and `tests/test_build.py`: security-posture US-1/US-3 (confinement, build bounds), shallow-clone-warning US-1/2/3/4/5, current-artifact-names US-1/4/6, coverage-current-names US-2 and pypi-publish US-2. close-the-loop and distributable-install are `inferred` only. Reading `build.py` confirms that T6 only touches `_kotlin_indexes`/`_resolve_kotlin_import`, which only Kotlin extractions reach. So the main protection for those stories is the full suite plus the T8 round-trip, not new tests.

## 3. Task Breakdown

`done` was judged by reading the code and the asserting test in the repo at 64a081b. I did not run the suite in this session. `review.md` reports 396 tests green.

| # | Task | Story | Covers (AC / NFR) | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|---|
| T1 | Pin the grammar, register `.kt`/`.kts` and the extractor in the dispatch | US-3 | AC-3.1, AC-1.1 | – | `done` | `pyproject.toml` has `tree-sitter-kotlin==1.1.0`, `uv.lock` locks 1.1.0, `language_for` maps `.kt` and `.kts` to `kotlin`, and `get_extractor("kotlin")` is not None. `test_kotlin_extension_registered` asserts the last three — files: pyproject.toml, uv.lock, src/aspark_graph/extractors/base.py, src/aspark_graph/extractors/__init__.py, tests/test_extractor_kotlin.py |
| T2 | Walking skeleton: `code_kotlin.extract` yields a `kotlin` File and top-level `fun`, end-to-end through `build_graph` | US-1 | AC-1.1 | T1 | `done` | A build of a six-language repo containing `f.kt` has a File node with `language="kotlin"` and no File is `unparsed`. `test_all_languages_in_one_build` asserts this — files: src/aspark_graph/extractors/code_kotlin.py, tests/test_extractor_java.py |
| T3 | Class extraction for class, data class, object, interface and enum class, with the walk recursing through `ERROR` | US-1 | AC-1.2 | T2 | `done` | Extractor tests assert a `Class` for `Point` (data), `Registry` (object), `Shape` (interface), `Color` (enum) and `A` (plain class in the single-line `ERROR` shape) — files: src/aspark_graph/extractors/code_kotlin.py, tests/test_extractor_kotlin.py |
| T4 | Function extraction: top-level, member, extension (`Receiver.name`), companion members nested under the enclosing class, `private` → `exported=False` | US-1 | AC-1.3 | T3 | `done` | Tests assert `top`, `Point.norm`, `Registry.lookup`, `Shape.area`, `Color.hex`, `String.shout` (parent None) and `Point.origin` (parent `Point`), plus `hidden.exported is False` — files: src/aspark_graph/extractors/code_kotlin.py, tests/test_extractor_kotlin.py |
| T5 | Import extraction (alias stripped, wildcard kept as `pkg.*`) and resolution in `build.py`: class FQN, trailing-segment strip, wildcard fan-out | US-2 | AC-2.1 | T4 | `done` | `test_kotlin_imports_including_wildcard_and_alias` and `test_build_resolves_kotlin_imports` show `Main.kt` gets exactly 2 `imports` edges (`Helper.kt` and wildcard `T.kt`) and none for `kotlin.collections.List` — files: src/aspark_graph/extractors/code_kotlin.py, src/aspark_graph/build.py, tests/test_extractor_kotlin.py |
| T6 | Ambiguous FQN gives no edge: the symbol index becomes FQN → sorted distinct files. ≥2 files means the import resolves to `[]`, with no further segment-stripping | US-2 | AC-2.1 | T5 | `done` | New test: `src/debug/Config.kt` and `src/release/Config.kt` both declare `package com.x` / `class Config`. `import com.x.Config` from `Main.kt` yields 0 `imports` edges. Same-file overloads (`fun f()` twice in one file) still resolve to 1 edge. The T5 tests stay green — files: src/aspark_graph/build.py, tests/test_extractor_kotlin.py |
| T7 | Bring tests up to the ACs' exact wording | US-1, US-2, US-3 | AC-1.1, AC-1.2, AC-1.3, AC-2.1, AC-3.1 | T6 | `done` | Tests assert five things. (a) A built `build.gradle.kts` is a `kotlin` File that is not `unparsed`. (b) A `contains` edge goes from the File to each of the 5 class kinds, and from the class to a member and to a companion member. (c) `import com.example.tools.tool` (a top-level fun) gives an edge to `T.kt`. (d) The multi-language double build compares saved `graph.json` text, not only `to_dict()`. (e) The all-languages test asserts a Kotlin `definition_id` node — files: tests/test_extractor_kotlin.py, tests/test_build.py, tests/test_extractor_java.py |
| T8 | Determinism regression against pre-change code (constitution §4): build this repo and `tests/fixtures/sample_repo` (neither has `.kt`) under `64a081b^` and under HEAD | US-3 | AC-3.1 | T6 | `done` | Both `graph.json` pairs are byte-identical (`cmp` exits 0). Base SHA, HEAD SHA and the file sizes are recorded in `review.md` |
| T9 | README states Kotlin support, its extensions and its `==` pin | US-3 | AC-3.1 | T1 | `done` | README §Supported languages, §Design guarantees and §Out of scope name Kotlin, and `test_current_names_ac_6_1_languages_stated` asserts the language list — files: README.md, tests/test_readme.py |
| T10 | `CLAUDE.md` stops saying "five languages"/"five tree-sitter grammars" and gains a `kotlin-support/` trail line | US-3 | AC-3.1 | T9 | `done` | `CLAUDE.md` lines 8, 28 and 81 name six languages/grammars including Kotlin, and the trail list mentions `kotlin-support/` — files: CLAUDE.md |
| T11 | Real-file sweep of the `ERROR` walk-through and the import rule (CLAUDE.md: "read a wide set of real files before writing a parser rule") on a scratch clone of ≥1 public Kotlin/Android repo outside this tree | US-1, US-2 | AC-1.2, AC-1.3, AC-2.1 | T6 | `done` | `review.md` records the repo URL + SHA, the `.kt`/`.kts` count, how many files contain an `ERROR` node, and a hand check of ≥10 files (definitions extracted vs. read). Every mis-nesting found becomes a test plus a fix, or a named known limit in the README |

## 4. Test Strategy

- **US-1 (Must), unit:** pure-extractor tests on byte fixtures in `tests/test_extractor_kotlin.py` cover each declaration kind, companion and extension naming, `private`, the single-line `ERROR` shape and `.kts` (T3, T4). **Integration:** `build_graph` on `tmp_path` repos (auto-marked by `conftest.py`, so no confinement bypass) checks the File language, the `unparsed` flag and the `contains` edges (T2, T7). **Real-world:** the T11 sweep, because synthetic fixtures don't exercise grammar error recovery.
- **US-2 (Should), integration:** a multi-file `build_graph` test checks class, top-level-fun and wildcard edges, no edge for stdlib, and no edge for an ambiguous FQN (T5, T6, T7).
- **US-3 (Must):** the pin is checked by reading `pyproject.toml`/`uv.lock` in review. Determinism is checked by a byte-compared multi-language double build (T7d) and the pre-change round-trip (T8). The README is checked by `test_readme.py`. `pytest -m slow` runs for release, including `test_fresh_install.py` (the new wheel resolves without the lock).
- **`/demo-day`:** N/A (constitution §8: no browser surface). The QA-equivalent goes in `qa.md` per AC: full suite, the slow suite, a clean-env wheel install, a `serve` boot, a byte-identical build, and a real-repo `impact`/`story_trace` run against the T11 Kotlin repo. The current `qa.md` rows ("tests green") don't name the steps performed or the observations, so they must be redone after T6–T11.

## 5. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| `ERROR` walk-through mis-nests members (wrong parent after a broken body) | Wrong `contains` edges presented as `extracted` | T11 sweep on real code. Each defect found becomes a test, a fix or a documented limit |
| A grammar bump changes node types (`qualified_identifier`, `class_body`, `companion_object`) | Silent loss of nodes, broken byte-identity | Pinned `==` (T1). A bump is a versioned event (README). The extractor tests pin each shape |
| FQN collision across source sets (debug/release, main/test) | A wrong `imports` edge | T6 refuses to link (constitution §1) |
| Wildcard detection reads source text. A trailing `/* … */` comment hides the `*` | The wildcard is treated as an FQN, so it gives at most one edge via segment-stripping. Edges are only missed, never wrong | Accepted known limit. Recorded in §1 Consequences |
| `build.py` is a hub shared by 8 features' stories (§2 blast radius) | A Kotlin change regresses confinement, bounds or shallow-clone behaviour | T6 is confined to the Kotlin functions. Full suite plus the T8 round-trip |
| The constitution (§3 stack, "the five grammars") and the external tool guide (indexed extensions) still describe five languages | Docs drift. A reader might think the Kotlin pin is outside the `==` rule | The pin is honoured in substance (T1). A §3 amendment is the user's call via `/charter`, and the tool guide belongs to aSPARK Core. Both are flagged, not edited here |
| Inherited spec premise: before this change, `.kt` files were not "unparsed File nodes"; they were skipped entirely (not in `EXTENSION_LANGUAGE`) | None for scope | T8 proves graphs without `.kt` are unchanged |
| Done status rests on reading the code, not on a run in this session | A red test I didn't see | `/increment` runs `uv run pytest` before starting T6 |

---

## ✅ PLAN GATE

*All boxes checked → `/increment` may start. Any box open → back to `/sprint-plan`.*

- [x] Spec status is `approved` (never plan against a draft)
- [x] Architecture decision includes rejected alternatives (a decision without alternatives is a guess)
- [x] Architecture respects the constitution's technical constraints (or a conflict is recorded). The `==` pin is kept, there's no network or adapter change, and the §3 "five grammars" wording drift is recorded in §5
- [x] Every task maps to a user story — no orphan tasks, no story without tasks
- [x] Every Must AC and every applicable NFR is covered by at least one task (the spec defines no NFRs)
- [x] Every task has a checkable definition of done
- [x] Task order respects dependencies
- [x] Test strategy covers every Must story
- [x] Line budget respected: Ist 92 / Soll ~300 (excluding HTML comments)
- [ ] Status set to `approved` by the user

## Deviations

- **T8:** `git archive 64a081b^` of this repo (no `.kt`, no kotlin trail) built with `--full` under the old source (PYTHONPATH to a worktree at dd4b994) and under HEAD source: `graph.json` byte-identical, 597391 bytes each (`cmp` exit 0).
- **T11:** scratch clone of `https://github.com/square/okhttp` @ `4162e9da32f636442bc789a7576144fe5972d0a5`: 575 `.kt` + 44 `.kts` = 619 files, 8 with a tree-sitter `ERROR` node. 17 files hand-compared (extractor functions/classes vs a regex over the source): the 11 error-free files matched exactly; the error files lost definitions (e.g. `Settings.kt` functions after a property getter, `Http2Stream.kt` nested classes, `Android17SocketAdapter.kt` entirely: the grammar reads an annotated class header as an expression). Two recovery rules were added (class keyword/name flattened inside `ERROR`; body-less class followed by a mis-parsed body) with tests; the remainder is a named known limit in the README. No wrong nesting was seen, only missing definitions.
