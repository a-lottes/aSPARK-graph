# Review Report: kotlin-support

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | The diff of `/increment` (`git diff dd4b994..HEAD`; fix round 62f3a49 = `git diff d3742d9..HEAD`), `.spark/kotlin-support/plan.md` |
| **Status** | `changes-requested` |
| **Round** | 2 |
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
- **Verdict:** Fixes applied by `/increment` for F1, F12, F13 (comment/string blanking in the retry copy, MISSING-aware error count, stderr + MCP `partial_files`); awaiting re-review.
- **Open:** `2 open` — Blockers: none; Majors: none (F9 benchmark flake, F10 cache-tag nit; F1, F12, F13 fixed, awaiting re-review)
- **Binding ruling:** §6 Verdict and the gate checklist below — the only binding location; there is no other round to point to
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Scope

- **Reviewed:** the fix round `git diff d3742d9..HEAD` in full: `code_kotlin.py`, `base.py`, `build.py`, `parse_cache.py`, the three test files, `README.md`, `CLAUDE.md` and plan §5. The full feature diff `dd4b994..HEAD` was read again where the fix touched it. `cli.py`/`server.py` are untouched, so the thin-adapter rule still holds.
- **Mode:** live run against the pinned `tree-sitter-kotlin==1.1.0` (with `tree-sitter==0.26.0`). This covered the full suite, the slow suite, CLI builds of a git-marked scratch Kotlin repo, about 60 hand probes, and a fuzz of 3,900 synthetic snippet combinations against `code_kotlin.extract`. I also mutation-tested the three new tests and built a dd4b994 fixture with the dd4b994 code and with the HEAD code (git worktree), then diffed the two graphs. Not degraded for any item below. Every fix was re-derived from source (condition (a): this round verifies those fixes), not taken from `/increment`'s account.
- **Standards applied:** Anti-generosity standard applied (`/opt/aspark/standards/anti-generosity.md`): AC cells are binary. Active lens: `cli` (`/opt/aspark/lenses/cli.md`). Tool file: `/opt/aspark/tools/aspark-graph.md`.
- **Graph (aspark-graph MCP):** queried after the coordinator rebuilt the graph (the qa.md drift fix). `staleness` was fresh (65 files). `impact --diff d3742d9..HEAD`:
  - `code_kotlin.py`, `parse_cache.py` and both extractor test files have no linked stories. The plan declares no `files:` notes, so this is empty by construction, not an all-clear.
  - `build.py`/`base.py` reach 16 stories from earlier features. As a result I read `build.py:150-175` and `build.py:240-345` and ran the old-vs-new round trip.
  - `test_build.py` reaches security-posture US-1 (declared). As a result I read `test_build.py:51-62`.
  - `README.md`/`CLAUDE.md` appear in `unknown_files` (not indexed), so I read them by hand.
  - `story_trace US-1 --feature kotlin-support`: T1 has `code: []`. Its QA leg was not read (tool rule).
- **Not reviewed:** `qa.md` (QA's artifact, left untouched). Pre-existing code is covered only where I observed it (F9, F10). Note for QA: the parse-cache tag (`parse_cache.py:38-45`) is the same at d3742d9 and HEAD (both 0.7.3 with the same grammar). A scratch repo built during round 1 will reuse round-1 Kotlin extractions, so build QA fixtures fresh or with `--full`.

## 2. Plan Conformance

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 | ✅ | Implemented as the rewritten plan §5 describes: same-length retry, no ERROR walking, `partial` flag. Its correctness gaps are tracked in §4 and F1/F12/F13. |
| T2 | ✅ | Exact name first, then walk-up; wildcards get no edge. The fan-out to every defining file (`build.py:248-258`, `311-327`) is a deviation, recorded in plan §5. |
| T3 | ✅ | README limit added (`README.md:275-278`). Duplicate test removed and the Java test renamed (F11). AC-3.1 guard in `test_build.py:59`. |

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Major | `extractors/code_kotlin.py:32-38,51-54`; `cli.py:162-184` | Round 2: the retry repairs the round-1 probe (`Login.kt`: all 5 definitions, line numbers correct). But the regex also rewrites `//` comments, which turns comment text into code. Probe: `class Keys { companion object { const val A = "a" } }` plus `// e.g. items.map { it.id }` (or `// response: { "id": 1 }`) anywhere in the file, before or inside a class, gives **0 definitions for the whole file**, including `Keys`. The retry has 1 error and the original has 1, so the original parse is kept. The file gets `partial: true`, but the build prints nothing and `impact` does not surface the flag. Only `get_node`/`find_nodes` show it. **Why it matters:** this is the same silent under-reporting as in round 1, triggered by a common comment pattern. **Fix:** (a) in the retry copy, overwrite the bodies of `//`/`/* */` comments and string literals with spaces (same length, offsets kept) before normalising. This also fixes F12. (b) Name partial files on stderr, as the shallow-clone notice does (cli lens §2), and expose them in the MCP `build_graph` result. | fixed |
| F2 | Major | `extractors/code_kotlin.py:97-108` | ERROR recovery walked an ERROR node with the outer parent: members of a swallowed type became fabricated top-level definitions. Round 2: ERROR nodes are no longer walked. The `Keys`/`Other` and `A`/`B` probes are now correct, with the right parents. Restoring the ERROR walk fails `test_unparseable_file_is_partial_and_never_mis_parented` (mutation-checked). The fuzz found no mis-parented real definitions. | fixed r2 |
| F3 | Minor | `build.py:311-327` | An import resolved only to the first file defining the name (`setdefault`). Round 2: names map to a list of files. In the scratch repo, `import com.ex.util.toast` produces edges to both `Ext1.kt` and `Ext2.kt`. | fixed r2 |
| F4 | Minor | `tests/test_extractor_kotlin.py:86-134` | The function-import path was not isolated, and there were no F1/F2 tests. Round 2: `topLevel` is in its own file and the edge set is asserted by equality. The one-line-body test and the partial tests fail when the retry is removed or `partial` is never set (mutation-checked). | fixed r2 |
| F5 | Minor | `README.md:321`, `tests/test_readme.py:69-70` | Stale "five" count and a weakened guard (reviewer fix, round 1). Round 2: no `five` in the README, and the guard is still `\bfive\b`. | fixed r2 |
| F6 | Nit | `CLAUDE.md:81` | "five tree-sitter grammars" (reviewer fix, round 1). Round 2: the line now says "six". | fixed r2 |
| F7 | Minor | `tests/test_build.py:59`, `tests/test_extractor_kotlin.py` | AC-3.1/AC-1.1 assertions were missing (reviewer fix, round 1). Round 2: `K.kt` is in the double-build test and `unparsed == set()` is asserted. | fixed r2 |
| F8 | Minor | `.spark/kotlin-support/plan.md:25` | The risk statement understated F1/F2. Round 2: §5 was rewritten and the limit is in the README (this repo has no BACKLOG file). The sentence "Residual: … honest absence" is contradicted by F12; correct it together with F12. | fixed r2 |
| F9 | Minor | `tests/test_incremental_bench.py:97` | Pre-existing: the NFR-1 benchmark (slow) is flaky on this machine. Round 2: two full slow runs passed, then the benchmark alone failed once and passed once. **Fix (EM):** settle it on the release machine before `/go-live`. | open |
| F10 | Nit | `parse_cache.py:38-45` | Pre-existing: the cache tag does not include the go/rust grammar versions. Round 2: unchanged. **Fix:** add both to the tag. | open |
| F11 | Nit | `tests/test_extractor_java.py:50` | Duplicate `test_all_six_languages_in_one_build`. Round 2: the Java test is renamed `test_all_languages_in_one_build` and covers Kotlin; the Kotlin copy is deleted. | fixed r2 |
| F12 | Minor | `extractors/code_kotlin.py:32-38` | The retry can **fabricate** a definition from a comment and not flag the file. Probe: a one-line companion plus `/// Usage: { fun sample()` (an opening brace in the comment with no closing `}` on that line) emits a top-level Function `sample` with `partial=False`. In the fuzz, 1,338 of 3,900 combinations containing such a comment fabricated `ghost`/`H.ghost`. **Why it matters:** a wrong graph fact (constitution §1). Rated Minor, not Major, because it needs an unclosed `{ decl…` comment. A closed `{ … }` comment loses data instead (F1). **Fix:** the same as F1(a); add the probe as a test. | fixed |
| F13 | Minor | `extractors/code_kotlin.py:41-46,53,56` | `_error_count` never counts MISSING nodes, because the grammar's hidden `_class_member_semi` is not returned by `children` or by a cursor. Valid one-liners such as `data class D(val a: Int) { fun f() = a }`, `enum class E { A, B; fun f() = 1 }`, `interface I { fun a(); fun b() }`, and one-line `when`/`if-else`/lambda bodies score 0 versus 0. The clean retry is rejected and the file is flagged `partial: true`, although the definitions are complete. **Why it matters:** false positives make the flag meaningless, and README:276 says such a file "cannot parse". **Fix:** prefer the retry when `not retry.root_node.has_error`. Land this only after F1(a): until then, a clean retry can carry a fabricated `object Fake` from a comment. | fixed |

## 4. Requirements Traceability

The spec has no NFRs. Anti-generosity binary grading applies to every cell.

| Spec ID | Implemented at | Verdict |
|---|---|---|
| AC-1.1 | `extractors/base.py:56-57`, `extractors/__init__.py:25` | ✅ PASS — CLI build of scratch repo: `.kt`, `build.gradle.kts`, empty, random-bytes and bad-UTF-8 `.kt` all `language=kotlin`, no `unparsed`, exit 0 |
| AC-1.2 | `extractors/code_kotlin.py:49-67,97-146` | ❌ FAIL — the round-1 probes now pass, but valid Kotlin with a one-line companion and a `// … { … }` comment yields no `Class` nodes at all (F1) |
| AC-1.3 | `extractors/code_kotlin.py:111-130` | ❌ FAIL — the same input drops every function (F1), and a comment can produce a fabricated `Function` node (F12) |
| AC-2.1 (Should) | `build.py:248-258,311-341` | ✅ PASS — live: class, alias, isolated top-level-function and overloaded-function imports give File→File edges; overloads fan out to both files (F3 fixed) |
| AC-2.2 (Should) | `build.py:328-329` | ✅ PASS — live: `com.ex.util.*` and `kotlinx.coroutines.launch` give no edge; a `*` inside a comment is not read as a wildcard |
| AC-3.1 | `pyproject.toml:46`, `uv.lock` | ✅ PASS — `==1.1.0`. Scratch repo with a partial file: build, cached rebuild and `--full` all give `8ff4ef96…`, and `partial` survives the cache. dd4b994 fixture: dd4b994 code and HEAD code both give `fb4e60cc…` |
| AC-3.2 | `tests/test_extractor_kotlin.py` | ✅ PASS — 8 Kotlin tests plus Kotlin in both multi-language tests; the new tests fail under the mutations listed in §5 |
| AC-3.3 | `README.md:272-278`, `README.md:298-299` | ✅ PASS — Kotlin is listed in "Supported languages" and the design guarantees. The stale out-of-scope count was fixed (F5) |

## 5. What Was Checked

- [x] Correctness: probed one-line bodies, `${ x }` templates, lambdas `{ x -> }`, `when`, `if/else`, enum and data class bodies, strings containing braces, `'{'`, regex strings, block/KDoc comments, line comments and commented-out callbacks. Line numbers follow the original source. Failures are F1, F12 and F13. No case produced a wrong parent for a real definition.
- [x] Non-functional: byte-identical rebuild, including the cache round trip. The dd4b994 graph is unchanged under the new code, so non-Kotlin graphs are untouched. No constitution §6 non-negotiable is violated; the §1 principle is violated by F12. NFR-1: F9.
- [x] Error handling: no tracebacks. The silent partial parse is still not surfaced (F1(b)).
- [x] Security: no new input path. Regexes are linear (no nested quantifiers), and the 5 MB cap still applies. `cli` lens: no new flags or exit codes, stdout unchanged. Diagnostics: the partial-parse notice is missing from stderr (F1).
- [x] Tests: `uv run pytest`: 395 passed. `-m slow`: 4 passed twice; the benchmark alone is flaky (F9). Mutations: restoring the ERROR walk, removing the retry, or never setting `partial` each fail at least one new test.
- [x] Readability: the extractor is small and its comments state why ERROR nodes are skipped. `_error_count` hides the MISSING blind spot (F13).

Open questions for the user/EM:
- (a) `.spark/constitution.md` §3 still says "five grammars" and lists five languages. The constitution is user-owned, so it is left unedited.

## 6. Verdict

Changes requested. The fix round is real progress, verified live against the pinned grammar:
- ERROR nodes are no longer walked, which closes the round-1 fabrication (F2).
- The one-line-body retry restores the round-1 `Login.kt`, `Keys`/`Other` and `A`/`B` probes with correct parents and original line numbers.
- Imports fan out to every defining file (F3), and the tests now catch the regressions they claim to guard (F4, F11).
- Determinism holds: a scratch repo with a partial file builds byte-identically fresh, from cache and with `--full`, and the dd4b994 graph is identical under the old and new code.

The retry is not lexically aware, though:
- **F1 (Major, open).** A file with a one-line `companion object { … }` and an ordinary comment such as `// e.g. items.map { it.id }` loses every definition. The only trace is a `partial` attribute that neither the build output nor `impact` shows. That is the round-1 harm with a common trigger, so AC-1.2 and AC-1.3 stay FAIL.
- **F12 (Minor).** The same root cause can fabricate an unflagged definition from an unclosed `{` in a comment.
- **F13 (Minor).** The flag fires falsely on common valid one-liners.

**Fix for F1:**
- Blank out comments and string literals in the retry copy (same length, offsets kept). This also fixes F12.
- Then name partial files on stderr and in the MCP build result. The cli lens and this repo's shallow-clone precedent call for that; README text plus a graph attribute alone is not enough.
- Then apply F13's fix.

F9 and F10 are pre-existing and do not block this gate.

---

## ✅ REVIEW GATE

*All boxes checked → `/demo-day` may start. Any box open → back to `/increment`. On
re-review, edit this same checklist in place — never duplicate it as a second gate.*

- [x] No open Blocker findings
- [ ] No open Major findings (or explicitly waived by the user, with reason recorded here) — F1 open
- [ ] Every Must AC traces to implementing code; no constitution non-negotiable violated — AC-1.2/AC-1.3 trace to code but FAIL on valid input (F1); no §6 non-negotiable violated
- [x] All plan deviations documented and accepted — plan §5 records the retry, `partial` and import fan-out; the F8 wording follows F12
- [x] Test suite runs green — `uv run pytest`: 395 passed; `-m slow`: 4 passed (benchmark flaky, pre-existing, F9)
- [x] Line budget respected: Ist 122 / Soll ~150 (excluding HTML comments)
- [ ] Status set to `passed` — `changes-requested`
