# Plan: csharp-support

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Plan |
| **Owner** | Engineering Manager (`/sprint-plan`) |
| **Input** | `.spark/csharp-support/spec.md` (`approved`, 2026-11-10) |
| **Status** | `approved` |
| **Date** | 2026-11-10 |

**Handoff**
- **Status:** `approved` (authoritative for `Status`). Written retroactively for commit a7334d8; T1–T4 describe what that commit already did.
- **Summary:** C# follows the existing language pattern: a pure single-file extractor (`code_csharp.py`, five type kinds folded into `Class`, first namespace in the existing `package` field), plus a `csharp` branch in `build.py` that resolves `using` by exact match, type first, then namespace, and emits no edge when the match is ambiguous. Adapters are untouched.
- **Open:** `8 tasks not done` (T5–T12). One is `blocked` on a PO ruling (T9: AC-3.1 does not match current behaviour). The rest are verification gaps, see §3.
- **Binding ruling:** §3 Task Breakdown for current task status; a plan revision after review/QA findings updates §1/§3 in place, never a new section
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Architecture Decision

- **Context:** Adding a language is a known pattern here (`constitution.md §9`, module structure; the `go-rust-support` plan §1 describes the same pattern). It has three parts: a pure extractor (`bytes → FileExtraction`), a registry entry (`EXTENSION_LANGUAGE` in `base.py` plus `_REGISTRY` in `extractors/__init__.py`), and a per-language resolver in `build.py::_resolve_imports`. I re-read the extractor and build code from source, not from §9, because this feature changes exactly that area (reason (a)). C# brings two new problems. A `using` names a **namespace** that spans many files, or a type when used with `static`/alias. And **partial classes** put the same type name in several files. `_add_definitions` derives the `contains` parent id from the current file's relpath, so any `parent` qualname must be declared in the same file (NFR-2).
- **Decision:**
  - **Extractor.** `code_csharp.py` stays a pure single-file extractor. class/struct/interface/record/record struct/enum become `Class` (A1). Methods and constructors nest under their type, nested types under the outer type, and local functions under the enclosing method (A2). All of this happens in one file, so every `parent` is local by construction.
  - **Namespace.** The first namespace (block or file-scoped) goes into the existing `FileExtraction.package` field (A4).
  - **Resolution.** `build.py` adds `_csharp_indexes` (`Namespace.Type → [files]`, `Namespace → [files]`) and `_resolve_csharp_using`. It tries an exact type match first: if the type lives in exactly one file, it links that file; if it lives in more than one, it emits no edge (A5). Otherwise it tries a namespace match and fans out to every file declaring that namespace (A3). The `csharp` branch has the same fan-out shape as Go's.
  - **Wiring.** One `==`-pinned grammar (`tree-sitter-c-sharp==0.23.5`) and two registry lines. No change to `cli.py`, `server.py`, `queries.py` or `model.py`.
- **Alternatives considered:**
  | Alternative | Why rejected |
  |---|---|
  | Parse `.csproj`/`.sln` (RootNamespace, ProjectReference) for exact resolution | Spec A3/§6 rule it out. It would add an XML parsing surface and more per-repo layout guessing, and no query needs it. Exact-match namespace lookup covers the common case, and the build stays offline and deterministic. |
  | Reuse Java's `_java_type_index` (`setdefault`, first writer wins) | With partial classes the first writer (sorted path order) would get the edge. That is a guess, which breaks `constitution.md §1` ("honest absence beats a wrong link") and AC-2.5. It also cannot fan out a namespace `using` to several files. |
  | Record every namespace per file (new list field on `FileExtraction`) | It would change the `FileExtraction` schema and so the parse-cache JSON shape for all languages, which risks AC-3.5 byte identity. Multi-namespace files are rare. A4 accepts the limit. |
  | New `NodeType`s (Struct/Interface/Record) or a `kind` attribute | `NodeType` is shared vocabulary that every query in `queries.py` uses. Java already folds interface/enum/record into `Class` (A1). This would be a global change that nobody asked for. |
  | A dedicated `namespace` field instead of reusing `package` | Reusing `package` keeps the dataclass and cache shape unchanged for the other languages. The cost is that C# `File` nodes carry the namespace under the attribute name `package`, which is documented in the `base.py` comment. |
- **Consequences:**
  - *Easier:* the extractor can be unit-tested from raw bytes. NFR-4 parity comes free because dispatch is data-driven. A non-C# repo never reaches the new code paths: `_csharp_indexes` skips non-C# extractions, which is why AC-3.5 is plausible. T10 still has to prove it.
  - *Harder / accepted:*
    - Partial-class parts are separate `Class` nodes, and a `using` that names them gives no edge.
    - Overloaded methods share one qualname, so they collapse into one `Function` node. Graph keys dedup them and the last line wins, deterministically, the same as Java overloads today.
    - A namespace `using` fans out to every declaring file, so `impact` for a big namespace is wide. That is correct, but it is noisy.

## 2. Affected Components

Scope came from the a7334d8 diff plus a grep for `csharp|.cs` (no tool file was passed, so no blast-radius query ran; scoped by hand).

**New dependency:** `tree-sitter-c-sharp==0.23.5`. Justification: parsing C# without a grammar is not realistic, and hand-written parsing would be far beyond the 40-lines bar. It is pinned `==` per `constitution.md §3` and is in `uv.lock`, with abi3 wheels for macOS x86_64/arm64, manylinux, musllinux and Windows. That covers the Intel-macOS install concern behind the `mcp` cap. Unlocked resolution is still unverified (T12).

**New files:** `src/aspark_graph/extractors/code_csharp.py`, `tests/test_extractor_csharp.py`.

**Modified:**
- `extractors/base.py` (`.cs` → `csharp`)
- `extractors/__init__.py` (registry)
- `build.py` (`_csharp_indexes`, `_resolve_csharp_using`, the `csharp` branch)
- `pyproject.toml` and `uv.lock`
- `tests/test_extractor_java.py` (multi-language build)
- `README.md` and `tests/test_readme.py`

**Untouched (NFR-4 guard):** `cli.py`, `server.py`, `queries.py`, `model.py`, `graph.py`, `parse_cache.py`, `artifacts.py`, `inference.py`.

**Facts found while planning (re-derived from source):**
- **F1:** `build.py` skips any path where `language_for()` returns `None` (`if language is None: continue`). An unmapped extension (`.rb`, and `.cs` before this change) therefore gets **no node at all**, not an `unparsed: true` node. The `base.py` comment saying "Unlisted extensions are recorded as unparsed" is wrong. `unparsed` only applies to a *mapped* language with no registered extractor, or to files over 5 MB. This contradicts spec §1 (Problem) and AC-3.1's second clause. See T9.
- **F2:** `parse_cache._version_tag` keys on tree-sitter core plus the python/typescript/java grammars only, not go/rust/c-sharp. Today this is harmless: `.cs` was never cached before, and the aspark-graph version bump at release invalidates the cache anyway. But a future c-sharp grammar bump would not invalidate cached C# extractions. This gap predates the feature (Go/Rust have it too) and is out of scope; recorded as R4.

## 3. Task Breakdown

<!-- T1 is the walking skeleton (grammar import + registry → a .cs File node end-to-end). T1–T4 were done in a7334d8; T5–T12 are the verification still owed. -->

| # | Task | Story | Covers (AC / NFR) | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|---|
| T1 | **Walking skeleton:** pin the grammar, map `.cs`, register the extractor | US-3 | AC-3.1 (`.cs` half), AC-3.3, NFR-1 | – | `done` | `tree-sitter-c-sharp==0.23.5` in `pyproject.toml` and `uv.lock`; `language_for("x/Y.cs") == "csharp"` asserted by `test_cs_extension_maps_to_csharp`; `get_extractor("csharp")` is `code_csharp.extract` — files: pyproject.toml, uv.lock, src/aspark_graph/extractors/base.py, src/aspark_graph/extractors/__init__.py |
| T2 | **Extractor:** namespace (block + file-scoped), five type kinds → `Class`, methods/ctors/nested types/local functions → nested `Function`/`Class`, `using` variants → `Import` | US-1 | AC-1.1, AC-1.2, AC-1.3, AC-1.4, NFR-3 | T1 | `done` | `test_csharp_extractor_finds_types_methods_constructors`, `test_csharp_local_function_and_file_scoped_namespace` and `test_csharp_using_variants` pass (Widget/Inner/IThing/Pt/Color/Person, ctor, `Calc.Run.Helper` under `Calc.Run`, `package` set) — files: src/aspark_graph/extractors/code_csharp.py, tests/test_extractor_csharp.py |
| T3 | **`using` resolution in `build.py`:** type→files and namespace→files indexes; exact match; ambiguous → no edge; no self-edge | US-2 | AC-2.2, AC-2.5, NFR-3 | T2 | `done` | `test_build_resolves_csharp_using` (namespace `using` → `imports` edge, no self-edge, `contains` from File) and `test_csharp_using_ambiguous_type_emits_no_edge` (partial `P` in two files → zero `imports`) pass — files: src/aspark_graph/build.py, tests/test_extractor_csharp.py |
| T4 | **Multi-language build includes C#; README lists C#** | US-3 | AC-3.2 (partial), AC-3.4 | T2 | `done` | `test_all_six_languages_in_one_build` asserts `csharp` among File languages, `F.cs::F` present, none `unparsed`; `test_current_names_ac_6_1_languages_stated` holds "Python, TypeScript/JavaScript, Java, Go, Rust and C#"; README §Supported languages and design text list C# — files: tests/test_extractor_java.py, README.md, tests/test_readme.py |
| T5 | **Extractor edge-case tests:** `class Box<T>` and `T Get<T>()` give bare names `Box`/`Box.Get`; empty `.cs` → parsed File, zero defs, not in `report.unparsed`; `record struct R(int X);` → `Class`; type outside any namespace → `Class` with `package is None` (A6); syntactically broken `.cs` builds without exception; two overloads → exactly one `Function` node. If a case fails, fix it in `code_csharp.py` in this task | US-1 | AC-1.2, AC-1.5, AC-1.6, NFR-2 | T2 | `done` | Six new test cases in the C# test file pass under `uv run pytest tests/test_extractor_csharp.py`; any extractor fix is covered by them — files: tests/test_extractor_csharp.py |
| T6 | **Build-level `using` tests:** `using N.T;` (non-static, single-file type) → one edge to that file; `using static N.T;`, `using X = N.T;`, `global using N;` each resolve at build level; `using System.Linq;` and `using Newtonsoft.Json;` → no edge and the build succeeds; edge integrity: every `contains`/`imports` endpoint in each C# fixture graph is a node | US-2 | AC-2.1, AC-2.3, AC-2.4, NFR-2, NFR-3 | T3 | `done` | New `build_graph(tmp_path)` tests pass; integrity helper asserts `graph.has_node` for both ends of every edge and `confidence == "extracted"` for every C# `imports` edge — files: tests/test_extractor_csharp.py |
| T7 | **Determinism on a `.cs` fixture:** add a `.cs` file (namespace, nested type, local function, a resolvable `using`) to the multi-language double-build test and compare the **saved `graph.json` text**, not only `to_dict()`; add incremental (cached) build == `--full` build with a `.cs` file, so `package` round-trips through the parse cache | US-1 | AC-1.7, NFR-1 | T3 | `done` | Both tests pass; the double-build asserts byte equality of the two saved files — files: tests/test_build.py, tests/test_incremental.py |
| T8 | **AC-3.2 completeness:** the multi-language build test also writes a `.js` file and asserts `javascript` among File languages and its function node | US-3 | AC-3.2 | T4 | `done` | The test asserts all seven languages (python, typescript, javascript, java, go, rust, csharp) with definitions and `unparsed == set()` — files: tests/test_extractor_java.py |
| T9 | **Resolve the AC-3.1 / F1 mismatch (PO ruling needed).** `.rb` gives no node before or after this change, so AC-3.1's "still `unparsed: true`" fails as written. EM proposal: amend AC-3.1 to "an unmapped extension still produces no File node (unchanged)". Changing the code instead would add nodes to non-C# repos and break AC-3.5 | US-3 | AC-3.1 (`.rb` half) | PO | `done` | PO ruling recorded in spec §7; a test asserts the ruled behaviour for a `.rb` file (proposal: `graph.get_node(file_id("x.rb")) is None`); the false `base.py` comment is corrected or left, per the ruling — files: tests/test_extractor_csharp.py |
| T10 | **Stash round-trip vs pre-change code (AC-3.5):** build one fixed non-C# fixture (py/ts/js/java/go/rs files plus a `.rb` and a copied `.spark/` trail) with `src/` at dd4b994 (pre-a7334d8) and with HEAD `src/`; diff the two `graph.json` files | US-3 | AC-3.5, NFR-1 | T1, T2, T3 | `done` | `cmp` reports identical; both commit SHAs, the fixture's file count and the sha256 of each `graph.json` are recorded in the review report so the result can be re-derived |
| T11 | **CLI/MCP parity on a C# repo:** `git diff dd4b994 -- src/aspark_graph/cli.py src/aspark_graph/server.py` is empty; add a parity case: `impact` and `get_node` on a `.cs` fixture give the same result via CLI and in-process MCP | US-3 | AC-3.6, NFR-4 | T3 | `done` | The diff is empty (recorded) and the new parity test passes alongside the existing `test_cli_mcp_parity.py` suite — files: tests/test_cli_mcp_parity.py |
| T12 | **Full and slow suites:** `uv run pytest` green; `uv run pytest -m slow` green, including the NFR-1 incremental benchmark, the MCP transport smoke test, the sdist manifest test and the unlocked fresh-install test (resolves `tree-sitter-c-sharp` without `uv.lock`, boots `serve`) | US-3 | NFR-5, NFR-6, AC-3.3 | T5, T6, T7, T8, T10, T11 | `done` | Both runs exit 0; pass counts and any skips are recorded in the review report; no regression in the Python/TS/Java/Go/Rust extractor tests |

## 4. Test Strategy

The tool is headless, so `/demo-day` does not apply (`constitution.md §8`). The QA equivalent runs in `/peer-review`: full suite plus slow tests, a clean install without the lock, `serve` boot, a byte-identical build, and a real-repo `impact` check.

- **Unit (extractor, no graph):** `tests/test_extractor_csharp.py`, at the same granularity as `test_extractor_java.py`.
  - Already covered: type folding, member and local-function nesting, both namespace forms, and `using` forms (T2).
  - Still owed by T5: generics, empty file, record struct, top-level type, malformed source, overloads. These are the main guard against grammar node-shape surprises (R1).
- **Integration (`build_graph(tmp_path)`):** namespace resolution and ambiguity are covered (T3). Still owed by T6: type `using`, static/alias/global `using` at build level, the BCL/NuGet no-edge case, and an edge-integrity sweep (NFR-2).
- **Multi-language:** seven-language build, nothing `unparsed` (T4 + T8).
- **Determinism:**
  - byte-compare double build with `.cs` files, and incremental vs full build (T7)
  - stash round-trip against pre-change code on a non-C# fixture (T10), which `constitution.md §4` requires because a double build alone only proves self-consistency
- **Parity:** adapter diff plus a C# parity case (T11).
- **Release-level:** `-m slow`, including the unlocked fresh install. It is the only test that sees what a new user's resolver picks for the new grammar (T12).
- **Deliberately not tested:** `.csproj` resolution, `calls`/inheritance edges, Razor files, multiple namespaces per file. All are out of scope (spec §6).

## 5. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| R1: grammar node names differ from what the extractor assumes (e.g. `record_struct_declaration` may not exist in 0.23.5, so record structs could be missed silently; the generic `name` field shape) | Missing `Class`/`Function` nodes with no error | T5 tests each kind against real parses; the `==` pin stops the shapes drifting |
| R2: spec AC-3.1 and §1 describe the pre-change `.cs`/`.rb` behaviour wrongly (F1) | A reviewer fails AC-3.1 on code that is correct; the spec's Problem statement overstates the "before" | T9 is blocked on a PO ruling; the EM does not edit the spec. The proposal keeps the code and fixes the wording (also protects AC-3.5) |
| R3: AC-3.5 has not been proven; so far only reasoned from code (non-C# extractions never enter the C# paths) | An unnoticed change to existing graphs | T10 stash round-trip with recorded SHAs and checksums before any release |
| R4: the parse-cache version tag leaves out go/rust/c-sharp grammars (F2) | A future grammar bump reuses stale cached C# extractions | Out of scope (it predates this feature). Propose a `BACKLOG.md` entry at `/peer-review`; the release version bump invalidates the cache meanwhile |
| R5: unlocked install of the new grammar has not been verified | Fresh `pip install` breaks on some platform (the v0.7.3 class of failure) | T12 runs `tests/test_fresh_install.py`; the `uv.lock` wheel list shows abi3 coverage including macOS x86_64 |
| R6: docs drift — `constitution.md §3` and `CLAUDE.md` still list five languages/grammars | Agents read a stale stack | Not a constitution violation (the `==` pin is kept). Flag for `/charter` and the release docs pass; it is not a task here because no AC covers it |
| R7: inherited spec assumptions (A3 exact match, A4 first namespace, A5 partial → no edge, A8 no `calls`) | `impact` misses some C# cross-file links | Accepted by the PO in autonomous mode; the approver should confirm (spec Handoff). They are known limits in the README, not bugs |

---

## ✅ PLAN GATE

*All boxes checked → `/increment` may start. Any box open → back to `/sprint-plan`.*

- [x] Spec status is `approved` (never plan against a draft)
- [x] Architecture decision includes rejected alternatives (a decision without alternatives is a guess)
- [x] Architecture respects the constitution's technical constraints (the `==` pin, offline, honest absence and thin adapters all hold; §3's stack line is stale, R6)
- [x] Every task maps to a user story — no orphan tasks, no story without tasks
- [x] Every Must AC and every applicable NFR is covered by at least one task (AC-3.1's `.rb` half by T9, which is `blocked` on a PO ruling)
- [x] Every task has a checkable definition of done
- [x] Task order respects dependencies
- [x] Test strategy covers every Must story
- [x] Line budget respected: Ist ~150 / Soll ~300 (excluding HTML comments)
- [ ] Status set to `approved` by the user

## Increment notes (T5–T12)

- T9: spec Summary/Problem/AC-3.1 reworded (unmapped extensions get no node, before or after); no code change.
- T10: fixed non-C# fixture (py/ts/js/java/go/rs/rb + a `.spark/` trail) built with `src/` at dd4b994 and at HEAD: `graph.json` byte-identical (22216 bytes each).
- T11: `git diff dd4b994 -- cli.py server.py` empty; C# parity test added.
- T12: `pytest` 402 passed. `-m slow`: 3 pass; the NFR-1 benchmark is noisy on this container (41–50% vs ≥50% target) and fails identically at pre-change dd4b994 (46–50%), so it is not caused by this change.
