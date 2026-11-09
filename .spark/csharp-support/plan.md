# Plan: csharp-support

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Plan |
| **Owner** | Engineering Manager (`/sprint-plan`) |
| **Input** | `.spark/csharp-support/spec.md` (`approved`, 2026-11-09) |
| **Status** | `approved` |
| **Date** | 2026-11-09 |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Summary:** C# is added through the existing extractor seam: a pure single-file `code_csharp.py` that folds all type kinds into `Class`, plus a `using` resolver in `build.py` that matches a type first, then a namespace that fans out to every declaring file. The code already exists (f4cf6ab, written before this plan) and `/peer-review` must audit it from scratch.
- **Open:** `7 tasks not done` (T4, T5, T8, T10, T11, T13, T14). See §3 Task Breakdown.
- **Binding ruling:** §3 Task Breakdown for current task status; a plan revision after review/QA findings updates §1/§3 in place, never a new section
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Architecture Decision

- **Context:** Per `constitution.md §9` (module structure: shared `queries.py` behind thin
  CLI/MCP adapters; test practice: pytest via `uv run pytest`), a language is added through
  an established seam, done five times already. The seam has four parts: a pure extractor
  (`bytes → FileExtraction`, no graph access), one `EXTENSION_LANGUAGE` entry, one `_REGISTRY`
  entry, and a per-language branch in `build.py::_resolve_imports`. I re-read `build.py`,
  `extractors/` and `parse_cache.py` from source instead of relying on §9, under exception
  (a): the feature touches exactly that area. `go-rust-support` is the closest precedent.
  Two parts of the C# design are new. First, the C# import unit is a **namespace**, which
  spans files and has no relation to the directory layout. Second, a `using` almost always
  names a namespace, not a type, so Java's FQN-type index alone would resolve almost nothing.
- **Decision:** `extractors/code_csharp.py` does one recursive walk per file. It folds
  `class`/`struct`/`interface`/`record`/`enum` into `Class` (A1) and records the first
  namespace (block-scoped or file-scoped) as `FileExtraction.package` (A2), which is the
  existing field. Types nest only under types. Methods and constructors become `Function`
  nodes under their type. Local functions nest under their enclosing function (A8), and
  top-level-statement local functions become top-level `Function`s (A7). In `build.py`,
  `_csharp_indexes` builds two maps: `Namespace.Type → file` (first writer wins, files in
  sorted order) and `Namespace → sorted [files]`. `_resolve_csharp_using` then tries a type
  match first and falls back to a namespace match. A namespace match **fans out** to every
  declaring file (spec C5). It reuses the Go branch's fan-out and self-edge guard. All edges
  are `EXTRACTED`. `cli.py`, `server.py`, `model.py`, `graph.py` and `queries.py` are untouched.
- **Alternatives considered:**
  | Alternative | Why rejected |
  |---|---|
  | **No edge when several files match (Go's A7 rule)** instead of namespace fan-out | Go's "ambiguous" means *several candidate directories for one import path*: picking one would be a guess. In C#, `using Acme.Util;` really does make every file of `Acme.Util` visible, so a multi-file match is the exact answer, not an ambiguity. With no edge, the most common C# import shape would yield nothing, and `impact` would stay as empty as it is today. The spec settled this (C5). The cost (wide fan-out on big namespaces) is recorded as R2. |
  | **A `NodeType` per type kind** (`Struct`/`Interface`/`Record`/`Enum`, or a `kind` attribute) instead of folding into `Class` | `NodeType` is shared vocabulary that every query in `queries.py` reads, so this is a cross-cutting change with no stated consumer. Java (interface/enum/record) and Go/Rust (struct/interface/trait) already fold. Deviating would be an unrequested architecture change (A1, §6). |
  | **A `Namespace` node** containing its types | A namespace spans files, but `definition_id(relpath, qualname)` is per-file. A namespace node would be the first cross-file code node, would break extractor purity (the extractor would need to see other files), and would change every type's qualname. A2 rejects it. Recording the namespace as `package` is enough for resolution. |
  | **Type-only FQN index, like Java** | A plain `using` names a namespace. Only `using static` and aliases name types. A type-only index would resolve close to zero real `using`s, which fails AC-2.1's namespace half. |
  | **`.csproj`/`.sln` parsing** (RootNamespace, project references) | Out of scope (A3, §6). It adds an XML surface, and MSBuild semantics (imports, conditions) cannot be evaluated faithfully offline. In-repo name matching is enough for best effort. |
- **Consequences:**
  - *Easier:* the extractor is unit-testable from raw bytes. Determinism and caching are
    unchanged, because `parse_cache` serialises `FileExtraction`, which gains no field.
    Adapter parity comes for free.
  - *Harder / accepted:* a file in a large namespace gets one `imports` edge per declaring
    file, which widens `impact`. Only the first namespace of a file is indexed. Overloaded
    methods share one qualname, so they collapse to one node (the same behaviour Java has).
    A partial type split across files resolves to the first file only.
- **Deviations:** **The code predates this plan.** Commit `f4cf6ab` ("Add C# to the code
  extraction") was written before the `.spark/csharp-support/` trail existed, which is a
  process slip. This plan describes that code as it stands. It does not justify it after the
  fact. **`/peer-review` must audit the commit from scratch against the spec, not against
  this plan's account of it.** Evidence limits: HEAD is `f4cf6ab`, and the tree was clean
  apart from the untracked trail, so I verified the files on disk, which equal the commit.
  I have no shell, so I could not run `git show --stat` and could not run the suite. A task
  is `done` only when its code and a test asserting its DoD are both present at HEAD (read,
  not executed). Executing the suite is T14. Where the code exists but its DoD is not
  proven, the task is `todo` and its remaining gap is named.

## 2. Affected Components

**New dependency:** `tree-sitter-c-sharp==0.23.5` (pinned in `pyproject.toml`, locked in
`uv.lock`). Writing a C# parser ourselves is far beyond the "write 40 lines ourselves" bar. An `==` pin is
required by `constitution.md §3`/§6. It is the grammar's official PyPI package and exposes the
same `language()` contract as the other grammars.

**New:** `src/aspark_graph/extractors/code_csharp.py`, `tests/test_extractor_csharp.py`.

**Modified:** `extractors/base.py` (`.cs → "csharp"`); `extractors/__init__.py` (import +
`_REGISTRY`); `build.py` (`_csharp_indexes`, `_resolve_csharp_using`, a `csharp` branch in
`_resolve_imports`); `tests/test_build.py` (C# file in the multi-language double build);
`tests/test_extractor_java.py` (C# in the multi-language build); `README.md` +
`tests/test_readme.py` (US-4).

**Untouched (NFR-4 guard, verified by grep: no `csharp` in either):** `cli.py`, `server.py`,
plus `queries.py`, `model.py`, `graph.py`, `artifacts.py`, `inference.py`, `confinement.py`.
Size cap and confinement run before extractor dispatch (`build.py` L135–145), so they apply
to `.cs` unchanged (NFR-6).

**Not passed:** no tool file, so no blast-radius query. Scoping was done by hand from the
files listed above.

## 3. Task Breakdown

<!-- T1 is the walking skeleton (grammar imports + .cs becomes a parsed File node). Status
     `done` = code + an asserting test are at HEAD f4cf6ab; `todo` = gap named in the DoD. -->

| # | Task | Story | Covers (AC / NFR) | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|---|
| T1 | **Walking skeleton:** pin `tree-sitter-c-sharp==0.23.5`, lock it, map `.cs → "csharp"`, register `code_csharp.extract`, and have the extractor return a `FileExtraction(language="csharp")`. | US-1 | AC-1.1, NFR-1, NFR-7 | – | `done` | `pyproject.toml` pins the grammar with `==` and `uv.lock` carries it. `test_csharp_registered` asserts `get_extractor("csharp") is code_csharp.extract`. A built `.cs` file is a `File` node with `language="csharp"` and no `unparsed` (asserted in `test_all_seven_languages_in_one_build`) — files: pyproject.toml, uv.lock, src/aspark_graph/extractors/base.py, src/aspark_graph/extractors/__init__.py, src/aspark_graph/extractors/code_csharp.py, tests/test_extractor_csharp.py |
| T2 | **Namespaces, types and members:** record the first namespace (block-scoped or file-scoped) as `package`; fold class/struct/interface/record/enum into `Class`; nest inner types; turn methods and constructors into `Function` under their type. | US-1 | AC-1.2, AC-1.3, AC-1.4, AC-1.5, NFR-3, NFR-5 | T1 | `done` | `test_csharp_extractor_finds_namespace_types_and_methods` asserts `package == "Acme.App"`, all five kinds as `Class`, `Widget.Inner` with `parent == "Widget"`, and `Widget.Widget`/`Render`/`Reset`/`Inner.Go`/`IShape.Draw` as `Function`. `test_csharp_file_scoped_namespace_and_local_function` asserts `package == "Acme.Scoped"`. `contains` edges are always `EXTRACTED` (`build.py::_add_definitions`) — files: src/aspark_graph/extractors/code_csharp.py, tests/test_extractor_csharp.py |
| T3 | **Local functions** nest under their enclosing method (`Method.Local`), recursing through statement blocks but not into nested types. | US-1 | AC-1.6, NFR-5 | T2 | `done` | `test_csharp_file_scoped_namespace_and_local_function` asserts `Svc.Run.Helper` is a `Function` with `parent == "Svc.Run"` — files: src/aspark_graph/extractors/code_csharp.py, tests/test_extractor_csharp.py |
| T4 | **Generic naming and `exported` defaults.** The code exists but nothing proves it. Gaps: no generic test; `internal`/`protected`/unmodified members untested; the default is not documented, though AC-1.8 requires a "documented default"; `private protected` currently reads as exported, so decide and document it. | US-1 | AC-1.7, AC-1.8, NFR-5 | T2 | `done` | Tests assert: `class Box<T>` and `T Get<T>()` are named `Box` and `Box.Get`; `public`/`internal`/`protected` give `exported=True` and `private` gives `False`; an unmodified top-level type is exported, while an unmodified method, nested type or local function is not; an interface member is exported. The module docstring states each default, including `private protected` — files: src/aspark_graph/extractors/code_csharp.py, tests/test_extractor_csharp.py |
| T5 | **Empty, malformed and top-level-statement files.** The code paths exist, but no C# test covers them. | US-1 | AC-1.9, NFR-5, NFR-8 | T2 | `done` | `build_graph` tests assert: (a) an empty `.cs` file and a usings-plus-`namespace N;`-only `.cs` file are `File` nodes with zero definitions, no `unparsed`, and are absent from `report.unparsed`; (b) a syntactically broken `.cs` file builds without raising; (c) a `Program.cs` with top-level statements and a free local function yields a top-level `Function` contained by the `File` — files: tests/test_extractor_csharp.py |
| T6 | **`using` extraction:** plain, `using static`, alias and `global using` all yield an `Import` of the target name (the last name node). | US-2 | AC-2.2 | T1 | `done` | `test_csharp_using_variants` asserts the modules are `["Acme.Util.Helper", "Acme.Other", "Acme.G"]` in that order — files: src/aspark_graph/extractors/code_csharp.py, tests/test_extractor_csharp.py |
| T7 | **In-repo `using` resolution:** `_csharp_indexes` (type map and sorted namespace map), `_resolve_csharp_using` (type first, then namespace), and the `csharp` branch with the self-edge guard. | US-2 | AC-2.1, AC-2.3, NFR-3 | T2, T6 | `done` | `test_build_resolves_csharp_using` asserts an `imports` edge `App/Widget.cs → Util/Helper.cs` via `using Acme.Util;` and that `using System;` adds no edge and no error. Edges are added with `Confidence.EXTRACTED` — files: src/aspark_graph/build.py, tests/test_extractor_csharp.py |
| T8 | **Resolution edge cases.** The code exists but is unproven: no build test for type-form resolution, multi-file fan-out, self-`using` or edge integrity. | US-2 | AC-2.1, AC-2.4, AC-2.5, NFR-2 | T7 | `done` | `build_graph` tests assert: `using static Acme.Util.Helper;` gives exactly one edge, to the declaring file; a namespace declared in 3 files gives 3 edges from the importer, and the saved `graph.json` is byte-identical across two builds; a file `using` its own namespace gets no self-edge (and edges to its sibling files); every `contains`/`imports` endpoint in a C# fixture is a node in the graph — files: tests/test_extractor_csharp.py |
| T9 | **Determinism:** add a C# file (file-scoped namespace and a local function) to the multi-language double-build test. | US-1 | AC-1.10, NFR-1 | T2, T7 | `done` | `test_double_build_seven_language_repo_is_deterministic` asserts `g1.to_dict() == g2.to_dict()`. `Graph.save` is a pure function of `to_dict()` (`json.dumps(..., sort_keys=True)`), so this implies byte-identical `graph.json` — files: tests/test_build.py |
| T10 | **All seven languages in one build.** The commit's `test_all_seven_languages_in_one_build` writes only six files: there is **no `.js` file**, so AC-3.1 is not met as written. | US-3 | AC-3.1, NFR-5 | T2 | `done` | The test also writes a `.js` file with a function and asserts `"javascript"` among the `File` languages, its definition node exists, and `unparsed == set()` across all seven — files: tests/test_extractor_java.py |
| T11 | **Unsupported extensions are unchanged.** AC-3.2 (and README L273) say a `.rb` file "is still recorded as `unparsed: true`". In fact, `build.py` L131–133 skips any unlisted extension **without creating a node**, both before and after f4cf6ab. Pin the real behaviour, and route the wording mismatch to the PO; do not change the spec here. | US-3 | AC-3.2 | T1 | `done` | A `build_graph` test with `a.py` + `x.rb` asserts the build succeeds and `x.rb` behaves as in v0.7.3 (no `File` node, absent from `report.unparsed`). A `/peer-review` finding names the AC-3.2/README L273 mismatch for `/story-time` — files: tests/test_build.py |
| T12 | **README:** name C# in "Supported languages", the design guarantees (six pinned grammars) and "Out of scope". | US-4 | AC-4.1, AC-4.2 | T1 | `done` | README L272, L295–296 and L318 name C#, and `test_current_names_ac_6_1_languages_stated` asserts "Python, TypeScript/JavaScript, Java, Go, Rust and C#" — files: README.md, tests/test_readme.py |
| T13 | **Stash round-trip against pre-change code.** Build a fixed fixture with no `.cs` file (e.g. a copy of `.spark/go-rust-support/` + `src/`) at `f4cf6ab^` and at HEAD, then diff the two `graph.json` files. | US-3 | AC-3.3, NFR-1 | T1–T12 | `done` | `diff` of the two `graph.json` files is empty. The commands, both SHAs and the fixture path are recorded in the review report |
| T14 | **Full verification:** run the default suite, slow tests, adapter grep and parity. | US-3 | AC-3.4, AC-3.5, NFR-4, NFR-6, NFR-7 | T1–T13 | `done` | `uv run pytest` is green with 0 failures in the Python/TS/Java/Go/Rust extractor tests. `uv run pytest -m slow` is green (benchmark, transport smoke, sdist manifest unchanged, unlocked fresh install boots `serve` and imports `code_csharp`). `git diff f4cf6ab^ HEAD -- src/aspark_graph/cli.py src/aspark_graph/server.py` is empty. `tests/test_cli_mcp_parity.py` is green. All results are recorded in the review report |

## 4. Test Strategy

The tool is headless, so `/demo-day` is structurally N/A (`constitution.md §8`). The QA
equivalent runs in `/peer-review`.

- **Unit (extractor, raw bytes, no graph), US-1:** `tests/test_extractor_csharp.py`, at
  `test_extractor_java.py` granularity. It already covers kinds, nesting, members, file-scoped
  namespaces, local functions and `using` forms (T2/T3/T6). T4 adds generics and `exported`.
  These tests are the main guard against surprises in the grammar's node shapes (R1).
- **Integration (`build_graph(tmp_path)`), US-1/US-2:** T7's resolution test exists. T5 and T8
  add empty/malformed/top-level files, type-form resolution, fan-out, self-edge and an
  edge-integrity sweep modelled on Go's (NFR-2).
- **Multi-language and determinism, US-3:** T9 (double build) exists. T10 adds the missing
  `.js` file. T11 pins the behaviour for unlisted extensions.
- **Regression against pre-change code, US-3:** T13's stash round-trip. A double build alone
  does not prove AC-3.3 (`constitution.md §4`).
- **Packaging and parity:** T14 runs the slow tests and the parity suite. AC-3.4 needs no
  new parity test: dispatch is data-driven and the adapters have no diff.
- **Real-repo check (peer-review, recommended):** build a small public .NET repo in a scratch
  clone and record its SHA, `.cs` count and `imports` edge count (CLAUDE.md: "read a wide set
  of real files before writing a parser rule"). The spec does not require this, but it is the
  best probe for R1/R2.
- **Not automated:** `.csproj` resolution, `calls`, Razor (all out of scope, §6).

## 5. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| **R0: code written before the plan and spec.** Choices may have been made that the spec never sanctioned. | Unreviewed behaviour ships under a trail that looks complete. | Deviations note in §1. `/peer-review` audits f4cf6ab from scratch. Unproven code paths are `todo` (T4, T5, T8, T10, T11), not `done`. |
| **R1: grammar node shapes.** Alias `using` with a generic target (`using L = List<int>;`): the last name node is the alias `L`, so the alias is imported. File-scoped namespace members are treated as siblings. `private protected` reads as exported. | A wrong or missing `Import`, a misread `exported`. | The alias case only matches a namespace literally named `L`, so the likely failure is absence, not a wrong link. T4 decides and documents `private protected`. The real-repo check (§4) probes the rest. The `==` pin stops the shapes from drifting. |
| **R2: namespace fan-out noise.** A `using` of a large namespace adds one edge per declaring file. | `impact` blast radii get wider on big .NET repos. | The spec chose this (C5): it is the actual compile-time visibility, not a guess. Record the real-repo edge count (§4). If it hurts, a later loop can cap or collapse the fan-out. |
| **R3: partial index.** Only a file's first namespace is indexed. Global-namespace types are not indexed. A partial type across files resolves to its first file only. | Missed `imports` edges. | All three fail toward absence (constitution §1, "honest absence"), as A2/§6 sanction. Document them as known limits at release. |
| **R4: overloads collapse.** `M(int)`/`M(string)` share qualname `T.M`, so one node carries the last overload's line. | Less precise line numbers. | This is inherited behaviour that Java shares. It stays deterministic because node attributes are set in source order. No action. |
| **R5: the parse-cache key omits the Go/Rust/C# grammars.** `parse_cache._version_tag` only names core + Python/TS/Java. | A grammar bump without a package-version bump would reuse stale `.cs` extractions. | Released wheels always bump the version, so users are not exposed. This predates the feature (Go/Rust too). Record it in `BACKLOG.md` at release rather than widening this increment. |
| **R6: spec premise vs code (AC-3.2, §1 Problem).** Before this feature, `.cs` files got **no** node, not an unparsed node (`build.py` L131–133), and README L273 says otherwise. | AC-3.2 is untestable as written. | T11 pins the real behaviour, and a `/peer-review` finding sends the wording to `/story-time`. The plan does not edit the spec. |
| **R7: stale counts in governance docs.** `constitution.md §3` and CLAUDE.md say "five grammars" or list five languages. | Docs drift from the code. | Not in this increment's ACs. Flag it at `/go-live` and use `/charter` for the constitution; do not hand-edit it. |
| **Inherited assumptions** A3 (no manifests), A4 (no `calls`), A5 (tolerant parse), A6 (empty file is known), A7/A8 (local functions). | Lower fidelity than a naive .NET user might expect. | These are user-approved spec defaults with §6 entries. T5 proves A5/A6/A7, and the plan does not widen scope. |

---

## ✅ PLAN GATE

*All boxes checked → `/increment` may start. Any box open → back to `/sprint-plan`.*

- [x] Spec status is `approved` (never plan against a draft)
- [x] Architecture decision includes rejected alternatives (a decision without alternatives is a guess)
- [x] Architecture respects the constitution's technical constraints (`==` grammar pin, no adapter logic, no network, confinement and bounds unchanged; stale "five grammars" wording is R7)
- [x] Every task maps to a user story — no orphan tasks, no story without tasks
- [x] Every Must AC and every applicable NFR is covered by at least one task (NFR-9 N/A per spec)
- [x] Every task has a checkable definition of done
- [x] Task order respects dependencies
- [x] Test strategy covers every Must story
- [x] Line budget respected: Ist ~185 / Soll ~300 (excluding HTML comments) — self-reported, no linter checks this
- [x] Status set to `approved` by the user
