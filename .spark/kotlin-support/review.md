# Review Report: kotlin-support

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | The diff of `/increment` (`git diff dd4b994..HEAD`, commit d3742d9), `.spark/kotlin-support/plan.md` |
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
- **Verdict:** Fixes applied by `/increment`, awaiting re-review (F1/F2: one-line-body retry parse, no ERROR walking, `partial` flag).
- **Open:** `2 open` — Blockers: none; Majors: none (F9 benchmark flake and F10 pre-existing cache-tag nit remain; see §3)
- **Binding ruling:** §6 Verdict and the gate checklist below — the only binding location; there is no other round to point to
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Scope

- **Reviewed:** `git diff dd4b994..HEAD` — new `extractors/code_kotlin.py`, `tests/test_extractor_kotlin.py`; modified `extractors/base.py`, `extractors/__init__.py`, `build.py`, `parse_cache.py`, `pyproject.toml`, `uv.lock`, `README.md`, `CLAUDE.md`, `tests/test_readme.py`. `cli.py`/`server.py` untouched (thin-adapter rule held). This file was a placeholder written without a reviewer run; it is fully replaced (no prior `Round` row, so this is round 1).
- **Mode:** live run — full suite, slow suite, CLI builds of scratch repos, probes of `code_kotlin.extract` against the pinned `tree-sitter-kotlin==1.1.0`, and an old-code-vs-new-code round trip; plus static read. Not degraded for any item below.
- **Standards applied:** Anti-generosity standard applied (`/opt/aspark/standards/anti-generosity.md`): AC cells are binary. Active lens: `cli` (`/opt/aspark/lenses/cli.md`).
- **Graph (aspark-graph MCP):** `staleness` fresh (65 files, nothing changed). `impact --diff dd4b994..HEAD`: `code_kotlin.py`, `parse_cache.py` and `test_extractor_kotlin.py` have no linked stories because the plan declares no `files:` notes (empty by construction, not an all-clear). `build.py`/`base.py` reach 19 stories from earlier features, so I read `build.py:197-305` and ran the determinism round trip. `test_readme.py` reaches `current-artifact-names` US-6 (declared), so I read that spec's AC-6.1 and found F5. `story_trace US-1`: T1 has `code: []`; its QA leg was not used (tool rule).
- **Not reviewed:** `qa.md` (QA's artifact). Pre-existing code outside the diff is only covered where it was observed (F9, F10).

## 2. Plan Conformance

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 | ✅ | Pure extractor, registry + `.kt`/`.kts` mapping, `==1.1.0` pin, cache tag (`parse_cache.py:44`) as planned. But plan §5 risk claim "real multi-line code parses cleanly" is false (F8). |
| T2 | ✅ | `_kotlin_symbol_index`/`_resolve_kotlin_import` (`build.py:307-335`): exact, then walk-up; wildcard gets no edge. Matches the plan. |
| T3 | ❌ | As delivered: README:318 still said "five"; the existing double-build test did not cover Kotlin, so AC-3.1 had no regression guard. Both fixed by the reviewer (F5, F7). The "six-language build test" is a copy rather than an extension of the existing test (F11). |

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Major | `extractors/code_kotlin.py:72-74` (grammar) | On the pinned grammar, a one-line `class X { companion object { const val T = "x" } }` turns the rest of the file into an ERROR node with no recoverable children. Probe: Android-style `Login.kt` with that line before `class LoginViewModel { fun login() }` and a top-level `fun formatUser` gives **0 definitions**. The build reports success and says nothing on stderr. **Why it matters:** this is a common idiom. Every type/function after it disappears silently, and imports *into* that file resolve nowhere, so `impact` under-reports. **Fix:** check `tree.root_node.has_error`, record the file as partial (e.g. `report.partial` plus a stderr line naming it, like the shallow-clone note), and list the limit in README "Supported languages". Also assess a newer grammar. This needs a design decision. | fixed |
| F2 | Major | `extractors/code_kotlin.py:72-74` | ERROR recovery walks the ERROR with the *outer* parent. When the ERROR swallowed a type header, that type's members become top-level. Probe: `package p` + `object Keys { fun key() = 1 }` + `object Other { fun o() = 2 }` yields only `key` with `parent=None` (fabricated top-level `p.key`, also entered in `_kotlin_symbol_index`); `Keys`, `Other` and `o` are lost. Same for `class A { fun g() {} }` followed by `class B { … }`. **Why it matters:** this is a wrong graph fact, not an honest absence (constitution §1). **Fix:** do not emit definitions from an ERROR that directly holds an `identifier`/type keyword before them, or emit nothing from ERROR at the top level. Add regression tests for both probes. | fixed |
| F3 | Minor | `build.py:318` | `index.setdefault` is first-writer-wins. A top-level function name defined in two files of one package (common for extension overloads: `fun String.toast()` in `Ext.kt`, `fun Int.toast()` in `MoreExt.kt`) resolves only to the first file. Probe: `import com.ex.util.toast` produced an edge to `Ext.kt` only. **Why it matters:** an incomplete blast radius. **Fix:** map name → list of files and fan out, like `_go_package_index`. | fixed |
| F4 | Minor | `tests/test_extractor_kotlin.py:91-102` | `topLevel` lives in the same file as `Helper`, so the function-import path of AC-2.1 is never isolated. A change that indexed only classes would still pass. There is also no test for ERROR recovery or one-line bodies (F1/F2). **Fix:** put `topLevel` in its own file and assert that edge. Add the F1/F2 probes as tests. | fixed |
| F5 | Minor | `README.md:318`, `tests/test_readme.py:69` | README said "Languages beyond the **five** currently supported". The diff had loosened the guard regex to `five[^.]{0,20}(languages|grammars)`, which misses this sentence. Fixed: "six", and the guard now forbids any `\bfive\b`. Mutation-checked: it fails on the unfixed README. | fixed |
| F6 | Nit | `CLAUDE.md:81` | "the five tree-sitter grammars + core" was stale after the diff updated line 8. Fixed to "six". | fixed |
| F7 | Minor | `tests/test_build.py:51`, `tests/test_extractor_kotlin.py:105` | AC-3.1 (byte-identical rebuild) had no Kotlin file in any double-build test, and AC-1.1's "not `unparsed`" was never asserted. Fixed: added `K.kt` (with a companion) to the double-build test, and added an `unparsed == set()` assertion. | fixed |
| F8 | Minor | `.spark/kotlin-support/plan.md:25` | The risk section says the issue is limited to one-line class bodies and that "real multi-line code parses cleanly" with recovery. F1/F2 show one line breaks the rest of a multi-line file, and recovery mis-parents. **Fix (EM):** correct the risk statement and record F1's limit in BACKLOG. | fixed |
| F9 | Minor | `tests/test_incremental_bench.py:97` | NFR-1 bench (slow) fails intermittently on this machine: new code 48.3/50.9/49.6 %, **pre-change code** (dd4b994) 49.4/54.3 %, against a target ≥50 %. This is not caused by this diff, but the constitution §4 bar "stays passing" is not demonstrably held here. **Fix (EM):** re-run on the release machine or revisit the margin before `/go-live`. | open |
| F10 | Nit | `parse_cache.py:38-45` | Pre-existing: the cache version tag lists the python/typescript/java/kotlin grammars but not go/rust. A go/rust pin bump without an aspark-graph version bump would reuse stale extractions. **Fix:** add both to the tag. | open |
| F11 | Nit | `tests/test_extractor_java.py:50`, `tests/test_extractor_kotlin.py:105` | Two tests named `test_all_six_languages_in_one_build`. The Java one covers five languages. The Kotlin one is a copy-paste duplicate. **Fix:** extend one, delete the other. | fixed |

## 4. Requirements Traceability

The spec has no NFRs. Anti-generosity binary grading applies to every cell.

| Spec ID | Implemented at | Verdict |
|---|---|---|
| AC-1.1 | `extractors/base.py:56-57`, `extractors/__init__.py:25` | ✅ PASS — CLI build of scratch repo: `.kt`, `build.gradle.kts`, empty, random-bytes and bad-UTF-8 `.kt` all `language=kotlin`, no `unparsed`, exit 0 |
| AC-1.2 | `extractors/code_kotlin.py:63-110` | ❌ FAIL — correct for multi-line class/data/object/interface/enum/sealed/`fun interface`/nested/inner/companion, but valid Kotlin with one-line bodies loses or mis-parents types (F1, F2) |
| AC-1.3 | `extractors/code_kotlin.py:78-96` | ❌ FAIL — extension, generic, companion, suspend/operator and backtick names are correct; the same inputs as AC-1.2 drop or fabricate functions (F1, F2) |
| AC-2.1 (Should) | `build.py:307-335` | ✅ PASS — live: class, alias (`as H`) and top-level-function imports give File→File edges; overload fan-out is missing (F3) |
| AC-2.2 (Should) | `build.py:328-329` | ✅ PASS — live: `com.ex.util.*` and `kotlinx.coroutines.launch` give no edge; a `*` inside a comment is not read as a wildcard |
| AC-3.1 | `pyproject.toml:46`, `uv.lock` | ✅ PASS — `==1.1.0`. Scratch repo: build, incremental and `--full` are byte-identical. dd4b994 fixture: old code vs new code `aafe108d…` identical |
| AC-3.2 | `tests/test_extractor_kotlin.py` | ✅ PASS — 6 tests at Java granularity, plus a multi-language build test with Kotlin (weak spots: F4, F11) |
| AC-3.3 | `README.md:272-275`, `README.md:298-299` | ✅ PASS — Kotlin is listed in "Supported languages" and the design guarantees. The stale out-of-scope count was fixed (F5) |

## 5. What Was Checked

- [x] Correctness: probed about 40 Kotlin snippets against the pinned grammar (annotations on their own line, `@file:`, generics/reified, `fun interface`, sealed class/interface, secondary/`@Inject` constructors, top-level `val`/`const`/`by lazy`, Gradle `.kts` and shebang, nested/inner/named and unnamed companion, wildcard/alias/backtick imports, enum entry bodies, expect/actual, unicode). Failures are F1/F2.
- [x] Non-functional: determinism (double build, `--full`, stash-style round trip against dd4b994). Constitution non-negotiables: none violated. NFR-1 bench: F9.
- [x] Error handling: malformed and binary `.kt` files give no traceback and exit 0. The one swallowed failure is F1 (a silent partial parse).
- [x] Security: no new input path beyond file bytes. `_text` decodes with `errors="replace"`. The 5 MB cap and entry bound still apply. No network at build time. `cli` lens: the diff adds no flags, streams, exit codes or prompts; stdout format is unchanged; stderr stays silent on malformed Kotlin (see F1's fix).
- [x] Tests: `uv run pytest` 393 passed. `-m slow`: fresh unlocked install, sdist manifest and MCP transport pass; NFR-1 is flaky (F9). Assertion gaps: F4.
- [x] Readability: the extractor is small and mirrors the Java/Rust extractors. Duplicate test name: F11.

Open questions for the user/EM:
- (a) `.spark/constitution.md` §3 still says "the five grammars" and lists five languages. The constitution is user-owned, so I left it unedited.
- (b) The placeholder `qa.md` holds `✅ pass` rows that the graph's `story_trace` already reads as QA evidence, although its gate says the QA tester has not run. Should those rows stay before `/demo-day`?

## 6. Verdict

Changes requested. The wiring, pin, import resolution and determinism are correct and verified live: AC-1.1, AC-2.1, AC-2.2 and AC-3.1–3.3 pass, and an old-vs-new round trip is byte-identical. But the Must criteria AC-1.2 and AC-1.3 fail on valid Kotlin. A single one-line `class X { companion object { … } }` silently erases every later definition in the file (F1). Two consecutive one-line types make the ERROR recovery fabricate a top-level function and drop the types (F2). That is a wrong link, which the constitution ranks below honest absence. The plan's risk section understates both (F8). F1 needs a design decision (surface partial parses, document the limit, or change the grammar). F2 is an extractor fix with regression tests. F3/F4 should be fixed in the same pass. I fixed F5, F6 and F7 directly (doc counts, a weakened README guard, missing AC-1.1/AC-3.1 assertions) and re-ran the suite green. F9 is a pre-existing flaky benchmark that the EM must settle before release, not a defect of this diff.

---

## ✅ REVIEW GATE

*All boxes checked → `/demo-day` may start. Any box open → back to `/increment`. On
re-review, edit this same checklist in place — never duplicate it as a second gate.*

- [x] No open Blocker findings
- [ ] No open Major findings (or explicitly waived by the user, with reason recorded here) — F1, F2 open
- [ ] Every Must AC traces to implementing code; no constitution non-negotiable violated — AC-1.2/AC-1.3 trace to code but FAIL on valid input; no non-negotiable violated
- [ ] All plan deviations documented and accepted — T3 deviations documented (F5/F7 fixed, F11 open); F8 awaits the EM
- [x] Test suite runs green — `uv run pytest`: 393 passed (after reviewer fixes); slow NFR-1 flaky pre-existing (F9)
- [x] Line budget respected: Ist 100 / Soll ~150 (excluding HTML comments)
- [ ] Status set to `passed` — `changes-requested`
