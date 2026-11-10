# Review Report: kotlin-support

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | The diff of `/increment` (`dd4b994..HEAD`, commits 215a915 + 4c429a1), `.spark/kotlin-support/plan.md` |
| **Status** | `changes-requested` |
| **Round** | 1 |
| **Date** | 2026-11-10 |

<!-- Handoff: read this block first, the numbered sections below by exception. Whoever
     writes to this report — including `/increment` in fix-mode, which is not this
     report's owner — updates it in the same edit that closes or re-rules a finding:
     overwrite in place, never append. The block holds one current state, never a
     per-round log; a stale block is a defect, not a cosmetic issue.

     Re-review: bump `Round` yourself (only the owner bumps it, never `/increment`) at
     the start of the pass, then overwrite every section below in place — §1 Scope, §2
     Plan Conformance, §3 Findings, §4 Traceability, §6 Verdict and the gate checklist
     all hold exactly one current state, never a `## Round N` heading or a second gate.
     History lives in git, not in this file. -->

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Verdict:** Changes requested. Kotlin extraction (US-1) and packaging (US-3) pass, but AC-2.3 fails: imports of extension functions never resolve, so a real repo loses about half its in-repo Kotlin import edges.
- **Open:** `6 open`. Blockers: none. Majors: `F1` (Minors/Nits: see §3)
- **Binding ruling:** §6 Verdict and the gate checklist below. This is the only binding location; there is no other round to point to.
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Scope

- **Reviewed:** `git diff dd4b994..HEAD`: `code_kotlin.py` (new), `build.py` (`_kotlin_indexes`, `_resolve_kotlin_import`, the `_resolve_imports` branch), `extractors/__init__.py`, `base.py`, `pyproject.toml`, `uv.lock`, `README.md`, and the tests (`test_extractor_kotlin.py`, `test_build.py`, `test_extractor_java.py`, `test_readme.py`). Also read for context: `build.py::build_graph` dispatch and `parse_cache.py::_version_tag`.
- **Graph (accelerant):** `staleness` showed the graph was stale. I rebuilt it once over MCP. `impact --diff dd4b994..HEAD` reached 22 stories, with `build.py` linked to 19 of them, so I read all of `build.py::build_graph` and `_resolve_imports`, not only the new hunks. `unknown_files` listed only docs, `pyproject.toml` and `uv.lock`, which the graph does not index. I used `story_trace US-2 --feature kotlin-support` only to confirm T3's declared files. No verdict below rests on a graph answer.
- **Mode:** live. I ran the full suite and the slow suite, built repos through the CLI, ran probe scripts in `/tmp/rvprobe/`, and checked a real repo (square/okio @ `f0e3f479`, 327 `.kt` files). Nothing in §4 is a static read only.
- **Standard:** Anti-generosity standard applied (`/opt/aspark/standards/anti-generosity.md`). No lens files or tool file were passed. I applied the aspark-graph review slice because CLAUDE.md asks for it.
- **Not reviewed:** KMP, annotations and Gradle resolution (spec §6). I did not check a one-line class body for every declaration form; A7 is accepted as a risk.

## 2. Plan Conformance

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 | ✅ | `==1.1.0` pin in `pyproject.toml:46`; the `uv.lock` specifier matches; `.kt`/`.kts` are mapped in `base.py`; the registry entry exists; the adapters are untouched (diffed: `cli.py`, `server.py`, `queries.py`, `model.py`, `graph.py`, `parse_cache.py` unchanged) |
| T2 | ✅ | Matches the plan's §1 decision. `ERROR` is walked as a body (`code_kotlin.py:27`) |
| T3 | ❌ | Built as described, but the index the plan specifies (`package.Qualname`) cannot hit an extension-function import. The DoD only tested a non-extension top-level function. See F1 |
| T4 | ✅ | All-languages build, six-language double build and a Kotlin double build are present |
| T5 | ✅ | README language lists and grammar pin list updated; `test_readme.py` pins the phrase |
| T6 | ✅ | (a) to (d) are present. (e) was re-run by me (see §4). The "existing behaviour" check of R4 (`.rb` skipped) had no test; I added one (F7) |

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Major | `build.py:288-291` | `_kotlin_indexes` keys an extension function as `pkg.Recv.name`, but Kotlin imports it as `pkg.name` (`import okio.buffer`). Stripping never matches, so no edge is created. On okio @f0e3f479, 421 such imports go unresolved against 434 that resolve, so `impact` silently under-reports roughly half of the in-repo Kotlin dependents. AC-2.3 (`import a.b.topLevelFn`) fails for this whole class of top-level functions. **Fix:** for a parentless `Function` whose qualname contains `.`, also `index.setdefault(f"{prefix}{qualname.rsplit('.',1)[1]}", relpath)`. Add a build test with `fun String.shout()` and `import pkg.shout`. | open |
| F2 | Minor | `build.py:298-299` | A wildcard on a class or object (`import a.b.Reg.*`, which imports the members of an object or enum) only looks in `packages`, so it creates no edge even when `a.b.Reg` is indexed (probe confirmed). **Fix:** when `packages` misses, fall back to `index.get(module[:-2])`. | open |
| F3 | Minor | `code_kotlin.py:128-129` | The receiver name is the *first* identifier of `user_type`. `fun kotlin.String.q()` is therefore recorded as `kotlin.q`, and a function-type receiver gives the raw text `(() -> Unit).run2` (probe). Both are wrong or odd qualnames, though no edge dangles. **Fix:** use the last identifier of the `user_type`, and a stable placeholder for non-`user_type` receivers. | open |
| F4 | Minor | `parse_cache.py:37-43` | The cache version tag keys only the python, typescript and java grammars plus core. A `tree-sitter-kotlin` bump in a checkout whose package version is unchanged reuses stale extractions. The go/rust omission is inherited, but this diff repeats it. Releases are safe because they bump the version. **Fix:** add the go, rust and kotlin grammars to `_version_tag`. Note that this changes the cache tag, not `graph.json`. | open |
| F5 | Minor | `build.py:300-304` | The comment claimed stripping stops "never beyond the package-qualified name". The code strips down to one segment: probe `import com.unknown.Thing` linked to a default-package `class com`. This follows the spec's strip rule (A5), so I fixed the comment, not the behaviour. | fixed |
| F6 | Minor | `README.md:275`, `base.py:43` | Both said files in other languages "are recorded as unparsed". In fact `build.py:131-133` skips them with no node (probe: `.rb` → no node). The README sentence was rewritten in this diff. Corrected both. | fixed |
| F7 | Minor | `test_extractor_kotlin.py:121,155,169` | AC-2.4 asserted `not e[1].endswith("List")`, which a file id can never match (near-tautological). AC-1.9 never asserted zero definitions. The `.rb` half of AC-3.4 was untested. Now: exact import-target set, a zero-`def:` check, and an `r.rb` → no-node check. | fixed |
| F8 | Minor | `CLAUDE.md:8,81` | The language list and "five tree-sitter grammars" pin rule were stale. A future agent could read the Kotlin pin as outside the `==` rule. Updated to six. | fixed |
| F9 | Minor | `plan.md:22,130-131`, `spec.md:33` | Artifact drift. Plan Handoff says "1 task not done" while T6 is `done`. R4 says AC-3.4 is unsatisfiable, but its current wording is satisfiable (and now tested). R5 says T6 is `todo`. Spec §1 says `.kt` files were unparsed before this change; they had no node at all. **Fix:** EM/PO overwrite these in place. | open |
| F10 | Minor | `constitution.md:35,39` | The stack lists five grammars, and the non-negotiable covers "the five grammars". Kotlin is pinned `==`, so nothing is violated, but the constitution is now inaccurate. Plan §1 leaves the amendment to the user. | open |

## 4. Requirements Traceability

| Spec ID | Implemented at | Verdict |
|---|---|---|
| AC-1.1 | `base.py:56-57`, `build.py:166` | ✅ CLI build: `.kt` and `build.gradle.kts` are `language=kotlin`, not unparsed |
| AC-1.2 | `code_kotlin.py:26,79-89` | ✅ unit test plus probe (sealed, value, fun interface); `contains`/`extracted` seen in `graph.json` |
| AC-1.3 | `code_kotlin.py:105-106` | ✅ `top` has parent None |
| AC-1.4 | `code_kotlin.py:103-104` | ✅ interface/enum/object/class members nest |
| AC-1.5 | `code_kotlin.py:90-91` | ✅ named and unnamed companion (probe `O.make`) |
| AC-1.6 | `code_kotlin.py:101-102,114-132` | ✅ parentless; 0 dangling edges (fixture and okio). Qualname quality: F3 |
| AC-1.7 | `code_kotlin.py:76-93` (bodies not walked) | ✅ |
| AC-1.8 | `code_kotlin.py:62-66` | ✅ private/internal false; protected/default true |
| AC-1.9 | `build.py:166` | ✅ (test tightened, F7) |
| AC-1.10 | canonical `graph.py` | ✅ 3 CLI builds (incremental, `--full`, fresh) are `cmp`-identical |
| AC-2.1 | `build.py:254-258,295-308` | ✅ |
| AC-2.2 | `build.py:298-299` | ✅ package wildcard. Object wildcard: F2 |
| AC-2.3 | `build.py:288-291,305-310` | ❌ fails for extension-function imports (F1) |
| AC-2.4 | `build.py:301-308` | ✅ |
| AC-2.5 | `build.py:301-308` | ✅ per the spec rule; residual default-package match documented (F5) |
| AC-3.1 | `pyproject.toml:46`, `uv.lock:64` | ✅ |
| AC-3.2 | `tests/test_extractor_kotlin.py` | ✅ |
| AC-3.3 | `tests/test_extractor_java.py:50-67` | ✅ |
| AC-3.4 | `build.py:131-133,159-163` | ✅ unparsed path tested; `.rb` skip now tested (F7) |
| AC-3.5 | `README.md:272-276` | ✅ |
| AC-3.6 | adapters unchanged | ✅ `find_nodes` ×2, `impact`, `story_trace` and `get_node` CLI == MCP on a Kotlin repo; `grep -i kotlin` on adapters returns nothing |
| AC-3.7 | full suite | ✅ 400 passed |
| NFR-1 | pin + double build | ✅ stash-equivalent round-trip: the dd4b994 tree (no `.kt`) built by dd4b994 code vs HEAD code gives an identical 723,794-byte `graph.json` |
| NFR-2 | `build.py:256` | ✅ 0 dangling edges (fixture and okio) |
| NFR-3 | `build.py:258` | ✅ only `extracted` on code edges |
| NFR-4 | tolerant parse | ✅ `class {{{ fun ( ) =` builds via CLI, rc 0, no traceback |
| NFR-5 | slow bench | ✅ passed this run (known flaky on baseline) |
| NFR-6 | `test_fresh_install.py`, `test_packaging.py` | ✅ slow suite: 4 passed |

## 5. What Was Checked

- [x] Correctness: logic does what the acceptance criteria demand. AC-2.3 fails (F1).
- [x] Non-functional: applicable NFRs and constitution quality bars hold
- [x] Error handling: failures are handled, not swallowed
- [x] Security: no injected input trusted, no secrets in code
- [x] Tests: exist, are meaningful, and pass (after the F7 tightening)
- [x] Readability: the next developer will understand this

## 6. Verdict

Changes requested; the gate stays closed on F1 (Major). The extractor itself is sound. Every Must AC of US-1 and US-3 passes, verified live. Six-language and Kotlin double builds are byte-identical. The dd4b994-vs-HEAD round-trip on a Kotlin-free tree is byte-identical. CLI and MCP agree on a Kotlin repo. Malformed source builds cleanly, and a 327-file real repo (okio) builds with 0 unparsed files and 0 dangling edges. Import resolution, however, misses the most idiomatic Kotlin import there is: an extension function imported by its bare name. On okio that drops 421 in-repo edges against 434 kept, so `impact` under-reports Kotlin dependents with no signal that it did. That fails AC-2.3 as written, and the fix is two lines plus a test. US-2 is a Should story, so the user may waive F1 with a recorded reason, but I do not. F2–F4 and F9–F10 are open Minors. F5–F8 are low-risk doc and test fixes I applied directly. They are uncommitted in the working tree: `README.md`, `CLAUDE.md`, `base.py` and `build.py` (comments only) and `test_extractor_kotlin.py`. The suite is green after them: 400 passed, slow 4 passed.

---

## ✅ REVIEW GATE

*All boxes checked → `/demo-day` may start. Any box open → back to `/increment`. On
re-review, edit this same checklist in place — never duplicate it as a second gate.*

- [x] No open Blocker findings
- [ ] No open Major findings (F1 open; not waived)
- [x] Every Must AC traces to implementing code; no constitution non-negotiable violated
- [ ] All plan deviations documented and accepted (T3 vs F1; plan/spec drift F9 open)
- [x] Test suite runs green (400 passed; slow 4 passed)
- [x] Line budget respected: Ist 108 / Soll ~150 (excluding HTML comments) — self-reported
- [ ] Status set to `passed`
