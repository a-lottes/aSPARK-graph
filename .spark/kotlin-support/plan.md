# Plan: kotlin-support

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Plan |
| **Owner** | Engineering Manager (`/sprint-plan`) |
| **Input** | `.spark/kotlin-support/spec.md` (`approved`, 2026-11-10) |
| **Status** | `approved` |
| **Date** | 2026-11-10 |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Summary:** Keep the built single-file Kotlin extractor and its `build.py` declared-package index. Change the index to exact match only, where a name declared in more than one file gives no edge. Add the missing tests, the README known limits, the parse-cache tag entry and the pre-change determinism proof.
- **Open:** `none` (all 13 tasks done). T13 unblocked (Q1 resolved, spec C9). See §3 Task Breakdown.
- **Binding ruling:** §3 Task Breakdown for current task status; a plan revision after review/QA findings updates §1/§3 in place, never a new section
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Architecture Decision

- **Context:** System facts come from `constitution.md §9`: Python/hatchling/uv stack, thin `cli.py`/`server.py` adapters over `queries.py`, and a networkx graph plus a parse-cache sidecar. I re-read the extractor and build area from source under exception (a): this feature touches it. Commit 2bcdf98 on this branch already follows the Go/Rust pattern. It adds the pure `extractors/code_kotlin.py` (bytes in, `FileExtraction` out), `.kt`/`.kts` entries in `EXTENSION_LANGUAGE` and `_REGISTRY`, and `_kotlin_symbol_index` plus `_resolve_kotlin_import` in `build.py`. It also pins `tree-sitter-kotlin==1.1.0`. I read that code against the spec and found these gaps:
  1. `_kotlin_symbol_index` keeps the first file that declares a name (`setdefault`). An ambiguous name therefore resolves to whichever file sorts first, which breaks AC-2.4 and constitution §1 ("honest absence").
  2. `_resolve_kotlin_import` drops trailing segments until something matches. `pkg.Outer.Inner` therefore links to the file that declares `Outer`, which contradicts A5 and §6. `test_build_resolves_kotlin_imports` currently asserts that wrong behaviour.
  3. Top-level extension functions are indexed as `pkg.Receiver.name`. Kotlin imports them as `pkg.name`, so they never resolve, which falls short of AC-2.1 ("…or function").
  4. No test covers aliases (AC-2.5), empty or malformed files (AC-1.9/1.10), sealed classes, named companions, the "no dangling edge" rule (AC-1.7), the incremental path (AC-3.5) or Kotlin CLI/MCP parity (AC-3.4).
  5. `parse_cache._version_tag` does not include `tree-sitter-kotlin`. After a grammar bump, the build would keep serving stale cached Kotlin extractions.
  6. The README does not state the one-line grammar limit (AC-4.3).
  7. The seven-language build test has no `.js` file (AC-3.1).
- **Decision:** Keep the extractor and dispatch as built. They are data-driven and contain no adapter code, so NFR-4 holds by construction. Change the Kotlin index to `dict[str, set[str]]`, mapping `package.simpleName` to the set of files that declare it. The key is the last segment of a top-level qualname, so an extension function `String.shout` is keyed as `pkg.shout`. An import resolves **only** when its exact FQN maps to exactly one file. A wildcard, a nested-class path, a stdlib name or an ambiguous name gives no edge. The extractor records an alias import under its original FQN, so the `as` part never reaches the index. `tree-sitter-kotlin` is added to the parse-cache version tag. Unparsed files never enter the cache (`build.py` skips them before `cache_triples.append`), so AC-3.5 needs no cache migration, only a test that proves it.
- **Alternatives considered:**
  | Alternative | Why rejected |
  |---|---|
  | Keep the code as built (first file wins, prefix stripping) | It breaks AC-2.4 and A5, and it guesses a link, which goes against constitution §1. "First writer wins" matches the Java/Python indexes but was never a spec rule there. For Kotlin the spec explicitly rules it out. |
  | Resolve by directory layout (Java-style `src/com/x/Y.java`) | Kotlin does not tie a package to a directory, and Android repos often don't mirror packages in folders. The declared `package` header is the only reliable key. |
  | Gradle-aware or source-set-aware resolution | Out of scope (§6, C4). It would also mean parsing build scripts, which adds input surface and conflicts with the dull-and-offline principle. |
  | Switch or upgrade the grammar to fix one-line misparses | Out of scope (§6, A8). It would also change the pin, and the existing tests and fixtures were written against 1.1.0. |
  | Explicitly evict "unparsed" cache entries for AC-3.5 | Not needed: unparsed files are never cached. The cost would be new cache-format code with nothing to fix. |
- **Consequences:**
  - *Easier:* the resolver becomes a pure exact lookup with no fallback chain. Ambiguity handling is the same `len == 1` check that the Go resolver already uses.
  - *Harder / accepted cost:* nested-class imports and overloads split across files lose an edge they would get today (lower recall, by design under A5/A7). Index order no longer matters because sets are used. The output must still be deterministic, and T10 proves it with the double build.

## 2. Affected Components

*Scoped by hand: no tool file was passed, so no blast-radius query was run. Stack and module facts come from `constitution.md §9`. The extractor and build seam were re-read from source under exception (a).*

**Dependency (already added in 2bcdf98, justified here):** `tree-sitter-kotlin==1.1.0` is the only tree-sitter Kotlin grammar on PyPI with an `abi3` wheel for every platform we ship (see `uv.lock`). Writing our own Kotlin parser is not a realistic alternative. It is pinned with `==` like the other grammars (NFR-1). The constitution's §3 text still says "five grammars". Amending it is the user's call via `/charter`, and this plan does not block on it.

**Built (2bcdf98):** `src/aspark_graph/extractors/code_kotlin.py`, `extractors/base.py` (2 extension entries), `extractors/__init__.py` (1 registry entry), `build.py` (index and resolver), `tests/test_extractor_kotlin.py`, `tests/test_extractor_java.py` (multi-language test), `tests/test_build.py` (double build with `.kt`), `tests/test_readme.py`, `README.md`, `pyproject.toml`, `uv.lock`.

**To modify:** `build.py` (index and resolver), possibly `code_kotlin.py` (alias, only if T5's test shows the alias leaks into the module), `parse_cache.py` (1 tag line), `README.md` (known limits), and the tests `test_extractor_kotlin.py`, `test_incremental.py`, `test_cli_mcp_parity.py`, `test_extractor_java.py` and `test_readme.py`.

**Untouched (NFR-4 guard):** `cli.py`, `server.py`, `queries.py`, `model.py`, `graph.py`, `artifacts.py`, `inference.py`, `confinement.py`.

## 3. Task Breakdown

<!-- T1-T3 are the built walking skeleton (2bcdf98). /increment starts at T4. -->

| # | Task | Story | Covers (AC / NFR) | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|---|
| T1 | **Walking skeleton: grammar pin and registry wiring.** `tree-sitter-kotlin==1.1.0` is pinned and locked. `.kt`/`.kts` map to `"kotlin"`. `code_kotlin.extract` is registered and fills in `language` and `package`. | US-1, US-4 | AC-1.1, AC-1.2, AC-4.2, NFR-1 | – | `done` | `pyproject.toml` pins `tree-sitter-kotlin==1.1.0` and `uv.lock` agrees. `test_kotlin_extractor_finds_package_classes_functions` asserts `language`/`package`. `test_kotlin_script_file_extracted` builds a `.kts` file and finds its function node — files: pyproject.toml, uv.lock, src/aspark_graph/extractors/base.py, src/aspark_graph/extractors/__init__.py, src/aspark_graph/extractors/code_kotlin.py |
| T2 | **Extractor structure.** Class, data, enum and interface types and `object` fold into `Class`. Top-level and member `fun`. Nested classes. `companion object` becomes `Companion` (or its declared name). Extension functions become `Receiver.name` with `parent=None`. `private` controls `exported`. | US-1 | AC-1.3, AC-1.4, AC-1.5, AC-1.6, AC-1.7, AC-1.8 | T1 | `done` | These tests are green: `test_kotlin_extractor_finds_package_classes_functions`, `test_kotlin_companion_members_nest_under_companion`, `test_kotlin_extension_function_is_top_level_named_by_receiver`, `test_kotlin_private_is_not_exported` and `test_build_contains_edges_for_kotlin`. The sealed-class, named-companion and dangling-edge assertions are still missing and are added in T7 — files: src/aspark_graph/extractors/code_kotlin.py, tests/test_extractor_kotlin.py |
| T3 | **Baseline import capture and resolution, plus multi-language and double-build fixtures.** Imports are captured, with a wildcard marked `.*`. The resolver gives no edge for a wildcard or a stdlib name. `.kt` is in the multi-language and double-build tests. | US-2, US-1, US-3 | AC-2.2, AC-2.3, AC-1.11 | T1 | `done` | `test_build_resolves_kotlin_imports` asserts that `import com.example.util.*` and `import kotlin.collections.List` add no edge. `test_double_build_six_language_repo_is_deterministic` includes `f.kt` and is green — files: src/aspark_graph/build.py, tests/test_extractor_kotlin.py, tests/test_build.py |
| T4 | **Exact, ambiguity-safe Kotlin index.** `_kotlin_symbol_index` returns `dict[str, set[str]]` keyed `package.<last qualname segment>` for top-level definitions. `_resolve_kotlin_import` returns a relpath only for an exact key that maps to exactly one file, with no prefix stripping. Change the nested-class line of `test_build_resolves_kotlin_imports` to expect **no** edge (A5). | US-2 | AC-2.1, AC-2.4, NFR-2 | T3 | `done` | New build tests prove these cases. (a) Two files both declaring `package p` + `class Dup`, imported as `p.Dup`, give 0 `imports` edges. (b) `import p.shout` of a top-level `fun String.shout()` in another file gives 1 edge. (c) `import p.Helper.Inner` gives 0 edges. (d) A class, an object, an interface and a plain `fun` each resolve with 1 edge. Every edge endpoint is a node in the graph. The existing Kotlin tests stay green — files: src/aspark_graph/build.py, tests/test_extractor_kotlin.py |
| T5 | **Alias imports.** Add a test for `import com.example.util.Helper as H`. If the captured module is not exactly `com.example.util.Helper`, change `_add_import` to take only the `qualified_identifier` that comes before `as`. | US-2 | AC-2.5 | T4 | `done` | An extractor test asserts `Import.module == "com.example.util.Helper"` for the aliased form. A build test asserts exactly one `imports` edge to the file declaring `Helper`, the same as the un-aliased form — files: src/aspark_graph/extractors/code_kotlin.py, tests/test_extractor_kotlin.py |
| T6 | **Empty and malformed files.** Add tests for an empty `.kt` file, a `.kt` file with only a package and comments, and malformed Kotlin. The malformed fixture is multi-line and holds one valid `class Ok` next to `fun broken( {`. | US-1 | AC-1.9, AC-1.10, NFR-8 | T1 | `done` | The empty and package-only files are `File` nodes with `language="kotlin"`, no `unparsed` flag and 0 definitions (package still set on the second). Building the malformed file raises nothing, `Ok` is a `Class` node, and the `File` is not unparsed. `cli.main(["build", <dir>])` on that dir returns 0, and stderr has no `Traceback` — files: tests/test_extractor_kotlin.py |
| T7 | **Structural test hardening.** Add a build-level assertion for AC-1.1: the `File` node has `language`, `package` and no `unparsed` flag. Assert the `.kts` `contains` edge (AC-1.2). Add `sealed class`, a named `companion object Factory` and a member extension. Assert every Kotlin `contains`/`imports` edge is `EXTRACTED` and that its endpoints exist. | US-1 | AC-1.1, AC-1.2, AC-1.3, AC-1.6, AC-1.7, NFR-2, NFR-3, NFR-5 | T2 | `done` | New tests are green for each assertion above. The `sealed class S` → `Class` assertion, the `Host.Factory.make` under `Host.Factory` assertion and the endpoint-integrity loop all pass on the multi-line fixture. If any of them fails, `code_kotlin.py` is fixed in this task — files: tests/test_extractor_kotlin.py, src/aspark_graph/extractors/code_kotlin.py |
| T8 | **Parse-cache tag and incremental rebuild.** Add `:tree-sitter-kotlin={v('tree-sitter-kotlin')}` to `_version_tag`. Test the path from "Kotlin unregistered" to "Kotlin registered": build with `_REGISTRY["kotlin"]=None`, then rebuild incrementally with it restored. | US-3 | AC-3.5 | T1 | `done` | The test shows the second build has the `.kt` `File` without `unparsed` and with its `Class`. `report.reparsed` counts the `.kt` file exactly once, and `report.cached` covers the unchanged `.py` file. The `.py` node and its definitions are equal (dict compare) across both builds. `test_version_mismatch_triggers_fallback` stays green — files: src/aspark_graph/parse_cache.py, tests/test_incremental.py |
| T9 | **All seven languages in one build.** Add a `.js` file to `test_all_seven_languages_in_one_build` and assert `"javascript"` in the languages plus its function node. | US-3 | AC-3.1 | T3 | `done` | The test asserts all seven languages (python, typescript, javascript, java, go, rust, kotlin), one definition per file, and an empty unparsed set — files: tests/test_extractor_java.py |
| T10 | **Kotlin CLI/MCP parity.** Copy `fixtures/sample_repo` into `tmp_path`, add a `.kt` file, build, then compare the CLI and MCP results for `find_nodes`, `impact` (on the `.kt` file) and `story_trace`. | US-3 | AC-3.4, NFR-4 | T4 | `done` | The three new parity assertions are green. `grep -i kotlin src/aspark_graph/cli.py src/aspark_graph/server.py` finds nothing — files: tests/test_cli_mcp_parity.py |
| T11 | **README known limits.** Under "Supported languages", state these Kotlin limits: one-line forms such as `class A { fun m() {} }` may be misparsed (A8); wildcard imports give no edge (A6); nested-class and ambiguous imports give no edge (A5, A7). | US-4 | AC-4.1, AC-4.3 | T4 | `done` | `test_readme.py` asserts that the README names `.kt`, `.kts`, "one-line" and "wildcard" in the Kotlin paragraph. The existing no-"six" test and language-list test stay green — files: README.md, tests/test_readme.py |
| T12 | **Verification sweep (peer-review evidence, no code).** (1) Pre-change determinism proof: copy `tests/fixtures/sample_repo` (no `.kt` files, `.git`-marked) and build it under pre-change `dd4b994` (via `git worktree`) and under branch HEAD; the two `graph.json` files must be identical. (2) `uv run pytest`. (3) `uv run pytest -m slow` (benchmark, transport, sdist manifest, fresh install). (4) A 6 MB `.kt` file gives `unparsed_reason="size"`. | US-3, US-1 | AC-1.11, AC-3.3, NFR-1, NFR-6, NFR-7, NFR-9 | T4–T11, T13 | `done` | The diff of the two `graph.json` files is empty, and the SHAs and file sizes are recorded in the review. The full suite and the slow suite are green. The oversize `.kt` file is recorded as unparsed by size. The diff of `graph.json`'s node keys shows only the new `"kotlin"` language value (NFR-9) |
| T13 | **Unsupported-extension guard.** Q1 resolved as option (a) (spec C9). Add a `.rb` regression test asserting today's behaviour (no node, build succeeds), and correct the README line "Files in other languages are recorded as unparsed `File` nodes". | US-3 | AC-3.2 | T9 | `done` | Under option (a), a test builds a repo with `x.rb` and asserts the build succeeds and that there is no `File` node for `x.rb`. The README no longer claims "unparsed" for unsupported extensions. Under option (b), the plan is revised before this task starts — files: tests/test_extractor_java.py, README.md |

## 4. Test Strategy

The tool is headless, so `/demo-day` does not apply here (constitution §8). The QA-equivalent runs in `/peer-review`: the full suite, a clean-environment install, booting `serve`, a byte-identical build, and a real-repo `impact`.

- **US-1 (Must), unit level, no graph:** `test_extractor_kotlin.py` covers the class kinds including sealed classes, top-level and member functions, nesting, plain and named companions, top-level and member extension functions, `exported`, alias and wildcard capture, and empty input (T2, T5, T6, T7). The tests use multi-line fixtures only (A8).
- **US-1, integration with `build_graph(tmp_path)`:** File node attributes, the `.kts` `contains` edge, malformed input that does not raise, the CLI `build` exit code and stderr (T6, T7), and edge-endpoint integrity plus `EXTRACTED` confidence (NFR-2, NFR-3).
- **US-2 (Should), integration:** one positive case per declaration kind, plus stdlib, wildcard, nested-class, ambiguous and alias cases (T3, T4, T5).
- **US-3 (Must):** the seven-language build (T9), incremental registration (T8), Kotlin parity (T10), and `.rb` handling (T13, after Q1). For determinism, the double-build test (already present) proves the new code is self-consistent. The pre-change comparison in T12 proves the change did not alter a non-Kotlin repo's graph (constitution §4).
- **US-4 (Must):** README assertions in `test_readme.py` (T11). For the pin, a reviewer reads `pyproject.toml` and `uv.lock` (T1).
- **Left manual on purpose:** the T12 comparison against the pre-change graph (it needs two checkouts, which a unit test cannot do without depending on git state) and the size-cap check (it runs through the existing tested `MAX_FILE_BYTES` path).

## 5. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| **R1: The spec's premise is wrong (Q1).** §1 and AC-3.2 say an unsupported extension becomes an `unparsed: true` `File` node. In code, `language_for` returns `None` for any extension not listed, and `build.py` L131–133 then `continue`s: no node is created. README L277 repeats the wrong claim. | AC-3.2 cannot pass as written without a change to every repo's graph, and that change would break the NFR-1 pre-change comparison. | Sent back to the PO as Q1. Recommended **(a)**: read AC-3.2 as "unsupported extensions handled as today" and correct the README. Option **(b)** creates unparsed nodes for every unsupported extension, which is out of scope and changes every graph. T13 stays blocked until Q1 is answered; nothing else depends on it except T12. |
| **R2: Recall drops when nested-class imports and split overloads lose their edges (T4).** | `impact` crosses fewer Kotlin file boundaries than the code currently does. | The spec requires this (A5, A7, §6) and it follows constitution §1. The README states it (T11). If real repos show the loss hurts, raise it with the PO in a later SPARK loop. |
| **R3: Grammar node shapes (alias, named companion, sealed class) differ from what the code assumes.** The code was written against 1.1.0 trees, but these cases are not tested yet. | A test in T5 or T7 fails. | Each of those tasks includes fixing `code_kotlin.py` in the same task. The pin keeps the node shapes stable. |
| **R4: The one-line misparse (A8) shows up in real repos.** | Some declarations go missing. | This is an accepted limit (C5), documented in T11. The parser tolerates errors, and the code walks `ERROR` nodes, so the declarations around a misparse are still collected. |
| **R5: The parse-cache tag change (T8) makes every user's cache fail its next version check.** | One full rescan per user. `graph.json` is unchanged. | This already happens on every `aspark-graph` version bump. `CacheUnusable` falls back to a full rescan (v0.4.0). |
| **R6: `_version_tag` also leaves out the Go and Rust grammars** (gap since v0.5.0). | A Go/Rust grammar bump without a tool version bump would serve stale extractions. | Not in this spec's scope, so it is not fixed here. Flagged for BACKLOG at `/peer-review`. |
| **R7: Inherited spec assumptions:** A4 (`internal`/`protected` count as exported), A9 (no nodes for `typealias` or properties), no Gradle support. | Results are less precise than a Kotlin expert might expect. | These are explicit spec rulings with §6 entries, and the plan takes them over unchanged. |

---

## ✅ PLAN GATE

*All boxes checked → `/increment` may start. Any box open → back to `/sprint-plan`.*

- [x] Spec status is `approved` (never plan against a draft)
- [x] Architecture decision includes rejected alternatives (a decision without alternatives is a guess)
- [x] Architecture respects the constitution's technical constraints. Constitution §3's "five grammars" wording is now out of date and is the user's to amend via `/charter`. The `==` pin itself is honoured.
- [x] Every task maps to a user story — no orphan tasks, no story without tasks
- [x] Every Must AC and every applicable NFR is covered by at least one task. AC-3.2 (T13) is unblocked: spec reworded (C9).
- [x] Every task has a checkable definition of done
- [x] Task order respects dependencies
- [x] Test strategy covers every Must story
- [x] Line budget respected: Ist ~120 / Soll ~300 (excluding HTML comments; the caller's target was ~250)
- [x] Status set to `approved` (autonomous run: recommended option taken)
