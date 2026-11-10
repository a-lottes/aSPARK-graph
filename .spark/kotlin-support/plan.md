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
- **Summary:** Kotlin is a sixth registry entry: pure single-file `code_kotlin.py` (five type forms fold into `Class`, companion members nest under the owner, extension fns are parentless `Recv.name`) plus a package-declaration index in `build.py` for imports; adapters untouched. Written retroactively against commit 215a915.
- **Open:** `none` — all tasks T1–T6 `done` (§3)
- **Binding ruling:** §3 Task Breakdown for current task status; a plan revision after review/QA findings updates §1/§3 in place, never a new section
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Architecture Decision

<!-- Mini-ADR. The EM decides — but shows the alternatives that were rejected and why. -->

- **Context:** Adding a language is a proven five-times-repeated pattern
  (`constitution.md §9` module structure; §3 patterns): a pure extractor
  (`bytes → FileExtraction`, no graph access), an `EXTENSION_LANGUAGE` entry in
  `base.py`, a `_REGISTRY` entry in `extractors/__init__.py`, and a branch in
  `build.py::_resolve_imports`. I re-derived the extractor/build seam from source
  because the feature touches exactly that area (§9 exception (a)). `build.py`'s
  `_add_definitions` derives a parent id from the *current file's* relpath, so a
  non-`None` `parent` must name a same-file definition (NFR-2). Kotlin differs from
  Java in two ways that matter: packages need not match directories, and an import
  may name a top-level function or a member, not only a type (spec A5).
- **Decision:** One single-file extractor `code_kotlin.py` walking the
  tree-sitter-kotlin 1.1.0 tree: `class_declaration`/`object_declaration` → `Class`
  (covers class/data/enum/interface/object, A1); `companion_object` is walked
  transparently so its members get the owner as parent (A2); a `function_declaration`
  with a receiver becomes `Recv.name` with `parent=None` (A3); function bodies are
  never descended, so local functions yield nothing (A4); `private`/`internal`
  → `exported=False`. Imports resolve in `build.py` via two indexes built from
  *declared* `package` headers: `package.Qualname → file` (top-level defs and
  classes, first writer wins in sorted walk order) and `package → files`; wildcard
  fans out, otherwise trailing segments are stripped until a hit, else no edge
  (A5/A6). Grammar pinned `==1.1.0`. `cli.py`/`server.py` untouched (NFR-4).
- **Alternatives considered:**
  | Alternative | Why rejected |
  |---|---|
  | **Directory-layout resolution** (Go/Java-path style: `a.b.C` → `a/b/C.kt`). | Kotlin does not require directories to match packages (A5, C3); Android repos routinely flatten. Would miss or mis-link exactly the target repos. The declared-package index is the only layout-independent signal available without Gradle. |
  | **Gradle-aware, module-scoped resolution** (parse `settings.gradle.kts`/source sets). | Spec §6 excludes it; a build-file parser is a second language surface, and multi-module duplicate packages are rare enough to accept first-writer-wins as best-effort. YAGNI. |
  | **A separate node for `companion object`**, or parenting extension fns under the receiver `Class` via a cross-file type index. | A2/A3 resolved against both: a companion node adds qualname depth with no query value; a cross-file parent either dangles (NFR-2) or needs a two-phase build, which go-rust-support already rejected for the same reason. |
  | **New `NodeType`s / a `kind` sub-attribute** for data/object/enum/interface. | A1 folds into `Class` per the Java/Go/Rust precedent; `NodeType` is shared query vocabulary, a global change with no stated need. |
- **Consequences:**
  - *Easier:* extractor is unit-testable on raw bytes; dispatch stays data-driven so
    parity is free; determinism holds because indexes are built from the sorted walk.
  - *Harder / accepted:* first-writer-wins on duplicate `package.Name` across Gradle
    modules may link the wrong module's file (best-effort, A5); one-line class bodies
    parse as `ERROR` subtrees (A7) — the extractor walks `ERROR` nodes as bodies, so
    members are collected best-effort rather than dropped. `constitution.md §3` still
    lists five grammars; amending it to six is the user's call, not this plan's.

## 2. Affected Components

**New dependency (justified):** `tree-sitter-kotlin==1.1.0` — parsing Kotlin needs a
grammar; hand-rolling one is far beyond the 40-lines bar. Exact `==` pin per
`constitution.md §3`/§6 determinism; exposes `tree_sitter_kotlin.language()`, same
contract as the five existing grammars. No other dependency, service or pattern.

**New files:** `src/aspark_graph/extractors/code_kotlin.py`, `tests/test_extractor_kotlin.py`

**Modified files:**
- `src/aspark_graph/extractors/base.py` — `.kt`/`.kts` → `"kotlin"` in `EXTENSION_LANGUAGE`.
- `src/aspark_graph/extractors/__init__.py` — import + `_REGISTRY["kotlin"]`.
- `src/aspark_graph/build.py` — `_kotlin_indexes`, `_resolve_kotlin_import`, a `kotlin` branch in `_resolve_imports`.
- `pyproject.toml`, `uv.lock` — the pin.
- `tests/test_extractor_java.py` (all-languages build), `tests/test_build.py` (six-language double build), `tests/test_readme.py`, `README.md`.

**Untouched (NFR-4 guard):** `cli.py`, `server.py`, `queries.py`, `model.py`, `graph.py`,
`parse_cache.py`, `artifacts.py`, `inference.py`, `confinement.py`.

Blast radius: no tool file was passed, so no `impact` query was run; scoped by hand
from commit 215a915 and the files above.

## 3. Task Breakdown

<!-- Ordered. T1 is the walking skeleton: a .kt file becomes a parsed, language-tagged File node end-to-end. Retroactive: T1–T5 reflect commit 215a915; T6 is the gap found tracing it against the spec. -->

| # | Task | Story | Covers (AC / NFR) | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|---|
| T1 | **Walking skeleton: grammar pin + registry wiring.** Pin `tree-sitter-kotlin==1.1.0` and lock it; map `.kt`/`.kts` → `"kotlin"`; create `code_kotlin.py` that parses and returns a `FileExtraction(language="kotlin")` with `package` from `package_header`; register it in `_REGISTRY`. | US-3, US-1 | AC-3.1, AC-1.1, NFR-1, NFR-4 | – | `done` | `pyproject.toml` carries the `==` pin and `uv.lock` resolves it; `language_for("a/B.kt")` and `language_for("build.gradle.kts")` return `"kotlin"`; a built `.kt` file is a `File` node with `language="kotlin"` and no `unparsed` flag; no Kotlin string in `cli.py`/`server.py` — files: pyproject.toml, uv.lock, src/aspark_graph/extractors/base.py, src/aspark_graph/extractors/__init__.py, src/aspark_graph/extractors/code_kotlin.py |
| T2 | **Extractor: classes, functions, companion, extension, local, visibility.** Fold `class_declaration`/`object_declaration` into `Class`; nest member fns (incl. nested classes) via qualname; walk `companion_object` transparently; receiver fns → `Recv.name`, `parent=None`; never descend function bodies; `exported` false for `private`/`internal`. | US-1 | AC-1.2, AC-1.3, AC-1.4, AC-1.5, AC-1.6, AC-1.7, NFR-2, NFR-3 | T1 | `done` | `test_extractor_kotlin.py` proves: data class/interface/enum class/object/class → `Class` with `parent=None`; `Widget.Inner` nests; member fns of interface/enum/object/class nest; `Widget.make` (companion) has parent `Widget` and no companion node; `String.shout` is a parentless `Function`; `local` is absent; `.kts` top-level fn is extracted — files: src/aspark_graph/extractors/code_kotlin.py, tests/test_extractor_kotlin.py |
| T3 | **In-repo import resolution.** Extractor records imports (`a.b.*` keeps the `.*`, `as` alias dropped); `build.py` adds `_kotlin_indexes` (declared-package FQN index + package→files) and `_resolve_kotlin_import` (wildcard fan-out, trailing-segment strip, else none), emitting `imports` edges with `Confidence.EXTRACTED` only to in-graph, non-self files. | US-2 | AC-2.1, AC-2.2, AC-2.3, AC-2.4, AC-2.5, NFR-2, NFR-3 | T2 | `done` | `build_graph(tmp_path)` tests prove: `import com.example.util.Helper` links to `Helper.kt`; `import com.example.util.extra` (top-level fn) links to `Extras.kt`; `import com.example.util.*` links to both files; `kotlin.collections.List` and `org.nowhere.Thing` add no `imports` edge — files: src/aspark_graph/extractors/code_kotlin.py, src/aspark_graph/build.py, tests/test_extractor_kotlin.py |
| T4 | **Multi-language regression + determinism.** Add a `.kt` file to the all-languages build test and to the six-language double-build test; add a Kotlin double-build test. | US-3, US-1 | AC-3.2, AC-3.3, AC-1.10, NFR-1 | T2, T3 | `done` | `test_all_languages_in_one_build` asserts `kotlin` among `File` languages and no `unparsed` file; `test_double_build_six_language_repo_is_deterministic` and `test_kotlin_double_build_deterministic` assert identical `to_dict()` — files: tests/test_extractor_java.py, tests/test_build.py, tests/test_extractor_kotlin.py |
| T5 | **README: supported languages + design guarantees.** List Kotlin in "Supported languages", the pinned-grammar guarantee and the out-of-scope language sentence; pin the phrase in `test_readme.py`. | US-3 | AC-3.5 | T1 | `done` | README names "Python, TypeScript/JavaScript, Java, Go, Rust and Kotlin" and lists Kotlin among the pinned grammars; `test_readme.py` asserts the phrase — files: README.md, tests/test_readme.py |
| T6 | **Close spec-coverage gaps + verification sweep.** (a) Test `private`/`internal` → `exported=False`, default → `True`. (b) Test a package-only `.kt` builds a `File` with zero definitions, not `unparsed`. (c) Assert `definition_id("F.kt", "F")` in the all-languages test. (d) State the A7 one-line-class-body limit in README. (e) Run `uv run pytest`, `uv run pytest -m slow`, a stash round-trip on a no-Kotlin fixture, a CLI-vs-MCP `find_nodes` on a Kotlin repo, and a malformed `.kt` build. | US-1, US-3 | AC-1.8, AC-1.9, AC-3.3, AC-3.4, AC-3.5, AC-3.6, AC-3.7, NFR-1, NFR-4, NFR-5, NFR-6 | T4, T5 | `done` | Tests (a)–(c) exist and pass; README contains the one-line-class-body limit; full and slow suites green; the stash round-trip `graph.json` diff is empty; CLI and MCP `find_nodes` results are equal; a malformed `.kt` builds without a traceback — files: tests/test_extractor_kotlin.py, tests/test_extractor_java.py, README.md |

## 4. Test Strategy

Headless tool: `/demo-day` is structurally N/A (`constitution.md §8`); the
QA-equivalent runs in `/peer-review`.

- **Unit (extractor, no graph)** — `test_extractor_kotlin.py`: one source covering all
  five type forms, nested class, companion, extension, local fn, imports incl. wildcard
  and alias, and `.kts` (US-1: AC-1.2–1.7). T6 adds visibility (AC-1.8) and empty file
  (AC-1.9). These guard against grammar-shape surprises (R1).
- **Integration (`build_graph(tmp_path)`)** — import resolution: exact, top-level
  function, wildcard, stdlib and unknown (US-2: AC-2.1–2.5); node existence of `Widget`
  and `Widget.go` proves `contains` endpoints exist (NFR-2).
- **Multi-language + determinism** — all-languages build and six-language double build
  include Kotlin; Kotlin double build (US-3: AC-3.3, US-1: AC-1.10, NFR-1).
- **Regression / parity** — full suite unchanged elsewhere (AC-3.7); existing CLI≡MCP
  parity suite plus a manual `find_nodes` comparison on a Kotlin repo, and a grep that
  adapters carry no Kotlin code (AC-3.6, NFR-4); slow bench, fresh-install `serve` and
  sdist manifest (NFR-5, NFR-6); stash round-trip on a Kotlin-free fixture (NFR-1).
- **Deliberately not automated:** KMP, annotations, Gradle resolution (out of scope);
  the A7 one-line-body limit is documented, not tested as a feature.

## 5. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| **R1 — Grammar node shapes** (`object_declaration`, `companion_object`, receiver detection by a `.` token before `function_value_parameters`) differ from Java. | Mis-parented or missing definitions. | Extractor written against real parsed trees; unit tests pin each shape; grammar pinned `==` so shapes cannot drift. |
| **R2 — One-line class body → `ERROR` subtree (A7).** | Members missed or partial in compact files. | Accepted as risk by the spec; `ERROR` is walked as a body for best-effort recovery; T6 documents it in README (AC-3.5). |
| **R3 — Duplicate `package.Name` across Gradle modules.** | First-writer-wins may link the wrong module's file (a wrong, not absent, edge). | Spec A5 accepts best-effort; deterministic because the walk is sorted. Revisit only with a module-aware feature (§6). |
| **R4 — Unlisted vs. unregistered languages (resolved).** `language_for(".rb")` returns `None` and `build.py` skips such files (no node); `unparsed` is reached only for a known language with no registered extractor or the 5 MB cap. | Spec §1 and the `base.py` comment had described pre-change `.kt` files as unparsed. | Resolved: AC-3.4 as worded matches this behaviour and is tested (`.rb` skip + Kotlin-cut `unparsed`); spec §1 and `base.py` corrected (review F6/F9). |
| **R5 — Retroactive plan.** Tasks T1–T5 describe a commit that was written before the plan, so the plan did not shape the code. | Spec gaps went unnoticed (AC-1.8, AC-1.9, AC-3.5 limit note). | Traced every AC against 215a915; gaps were carried as T6 and are now `done`. |
| **R6 — Inherited spec assumptions A3–A6, A8** (parentless extension fns, no local fns, no Gradle, silent unresolved imports, uniform `.kts`). | Lower fidelity than a naive user expects. | Explicit spec decisions with §6 entries; inherited without widening scope. |

---

## ✅ PLAN GATE

*All boxes checked → `/increment` may start. Any box open → back to `/sprint-plan`.*

- [x] Spec status is `approved` (never plan against a draft)
- [x] Architecture decision includes rejected alternatives (a decision without alternatives is a guess)
- [x] Architecture respects the constitution's technical constraints (`==` pin, thin adapters, no network, determinism; `constitution.md §3` stack list still says five grammars and is recorded in §1 Consequences)
- [x] Every task maps to a user story — no orphan tasks, no story without tasks
- [x] Every Must AC and every applicable NFR is covered by at least one task (AC-3.4 is covered by T6; R4 resolved)
- [x] Every task has a checkable definition of done
- [x] Task order respects dependencies
- [x] Test strategy covers every Must story
- [x] Line budget respected: Ist ~135 / Soll ~300 (excluding HTML comments) — self-reported
- [x] Status set to `approved` (autonomous mode, recommended option)
