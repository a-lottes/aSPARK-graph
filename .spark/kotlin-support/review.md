# Review Report: kotlin-support

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | The diff of `/increment` (`git diff dd4b994..HEAD`; fix round 8dc45c6 = `git diff 62f3a49..HEAD`), `.spark/kotlin-support/plan.md` |
| **Status** | `changes-requested` |
| **Round** | 3 |
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
- **Verdict:** Fixes applied by `/increment` for F14-F16 (retry skips string/char/backtick literals verbatim instead of blanking them; comments still blanked); awaiting re-review.
- **Open:** `2 open` — Blockers: none; Majors: none (F9, F10 pre-existing; F14, F15, F16 fixed, awaiting re-review)
- **Binding ruling:** §6 Verdict and the gate checklist below are the only binding location. There is no other round to point to.
- **On conflict:** the numbered body below wins for everything except `Status`. Log the mismatch as a finding at the next `/peer-review` and proceed; don't stop on it.

## 1. Scope

- **Reviewed:** the fix round `git diff 62f3a49..HEAD` in full (`code_kotlin.py`, `build.py`, `cli.py`, `server.py`, `parse_cache.py`, both test files, `README.md`, plan §5). Context read: `cli.py:164-187`, `server.py:21-39`, `build.py:150-176`. The thin-adapter rule holds: `report.partial` is computed in `build.py:173-174`, and each adapter only renders it.
- **Mode:** live run against the pinned `tree-sitter-kotlin==1.1.0` with `tree-sitter==0.26.0` (printed by the probe). Checks: the full and slow suites; about 40 hand probes; a seeded differential fuzz of 6,000 files that checks every definition (name, kind, parent, line) against the known set; 5 mutations; CLI and MCP builds of a git-marked six-language scratch repo; and old-vs-new graph round trips using git worktrees at dd4b994 and 62f3a49. Every fix was re-derived from source, under condition (a): this round verifies those fixes. Mode is not degraded for any item below.
- **Standards applied:** Anti-generosity standard applied (`/opt/aspark/standards/anti-generosity.md`). Active lens: `cli` (`/opt/aspark/lenses/cli.md`). Tool file: `/opt/aspark/tools/aspark-graph.md`.
- **Graph (aspark-graph MCP):** I rebuilt it with `uv run aspark-graph build .`. The cache fell back on the new `kotlin-extractor=2` tag, as intended. `staleness`: fresh, 65 files. `impact --diff 62f3a49..HEAD`:
  - `cli.py`, `server.py` and `test_cli_mcp_parity.py` reach shallow-clone-warning US-1 to US-4. As a result I read that spec's AC-1.3, AC-2.2 and NFR-5 and checked the parity test's key set (`test_cli_mcp_parity.py:213-216,297`).
  - `build.py` reaches 16 stories. As a result I re-ran the dd4b994 byte-identity round trip.
  - `code_kotlin.py`, `parse_cache.py` and `test_extractor_kotlin.py` have no linked stories. The plan declares no `files:` notes, so this is empty by construction, not an all-clear.
  - `README.md` and plan.md are in `unknown_files`, so I read them by hand.
  - `story_trace US-1`: T1 has `code: []`. The QA leg was not read (tool rule).
- **Not reviewed:** `qa.md` (QA's placeholder, left untouched). F9 and F10 were not re-examined beyond one slow run.

## 2. Plan Conformance

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 | ✅ | Matches plan §5: blanking plus a same-length retry, no ERROR walking, `partial` on the File node, stderr and `partial_files`. Its correctness gaps are F14, F15 and F16. Plan §5's "named on stderr" is false for F15 files. |
| T2 | ✅ | Unchanged since r2. The fan-out to every defining file (`build.py:248-258`, `311-327`) is a deviation, recorded in plan §5. |
| T3 | ✅ | README `:272-279` updated. The new tests cover F1, F12 and F13; there is a gap for `is_missing` (F16). |

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Major | `extractors/code_kotlin.py:36-43,58-61`; `cli.py:178-179`; `server.py:36` | Comment text was rewritten into code, so a `// … { … }` comment erased the whole file. r3: the r2 probes `// e.g. items.map { it.id }` and `// response: { "id": 1 }` now return all definitions with `partial=False`, in the fuzz and by hand. The stderr line and `partial_files` are live: on the scratch repo the CLI printed `Partially parsed src/Bad.kt …`, MCP returned `['src/Bad.kt']`, and graph.json bytes matched across the two surfaces. Mutations M1 (no blanking) and M4 (no stderr line) each fail a test. | fixed r3 |
| F2 | Major | `extractors/code_kotlin.py:97-108` | ERROR recovery walked an ERROR node with the outer parent, so members of a swallowed type became fabricated top-level definitions. Round 2: ERROR nodes are no longer walked. The `Keys`/`Other` and `A`/`B` probes are now correct, with the right parents. Restoring the ERROR walk fails `test_unparseable_file_is_partial_and_never_mis_parented` (mutation-checked). The fuzz found no mis-parented real definitions. | fixed r2 |
| F3 | Minor | `build.py:311-327` | An import resolved only to the first file defining the name (`setdefault`). Round 2: names map to a list of files. In the scratch repo, `import com.ex.util.toast` produces edges to both `Ext1.kt` and `Ext2.kt`. | fixed r2 |
| F4 | Minor | `tests/test_extractor_kotlin.py:86-134` | The function-import path was not isolated, and there were no F1/F2 tests. Round 2: `topLevel` is in its own file and the edge set is asserted by equality. The one-line-body test and the partial tests fail when the retry is removed or `partial` is never set (mutation-checked). | fixed r2 |
| F5 | Minor | `README.md:321`, `tests/test_readme.py:69-70` | Stale "five" count and a weakened guard (reviewer fix, round 1). Round 2: no `five` in the README, and the guard is still `\bfive\b`. | fixed r2 |
| F6 | Nit | `CLAUDE.md:81` | "five tree-sitter grammars" (reviewer fix, round 1). Round 2: the line now says "six". | fixed r2 |
| F7 | Minor | `tests/test_build.py:59`, `tests/test_extractor_kotlin.py` | AC-3.1/AC-1.1 assertions were missing (reviewer fix, round 1). Round 2: `K.kt` is in the double-build test and `unparsed == set()` is asserted. | fixed r2 |
| F8 | Minor | `.spark/kotlin-support/plan.md:25` | The risk statement understated F1/F2. Round 2: §5 was rewritten and the limit is in the README (this repo has no BACKLOG file). The sentence "Residual: … honest absence" is contradicted by F12; correct it together with F12. | fixed r2 |
| F9 | Minor | `tests/test_incremental_bench.py:97` | Pre-existing: the NFR-1 benchmark (slow) is flaky on this machine. r3: one `-m slow` run, 4 passed; not re-examined. **Fix (EM):** settle it on the release machine before `/go-live`. A waiver is the user's call. | open |
| F10 | Nit | `parse_cache.py:38-46` | Pre-existing: the cache tag does not include the go/rust grammar versions. r3: unchanged. **Fix:** add both to the tag. A waiver is the user's call. | open |
| F11 | Nit | `tests/test_extractor_java.py:50` | Duplicate `test_all_six_languages_in_one_build`. Round 2: the Java test is renamed `test_all_languages_in_one_build` and covers Kotlin; the Kotlin copy is deleted. | fixed r2 |
| F12 | Minor | `extractors/code_kotlin.py:36-43` | A comment with an unclosed `{` could fabricate an unflagged definition. r3: `/// Usage: { fun sample()` and `{ fun ghost() }` inside strings, raw strings, KDoc and nested block comments produce no definition in 6,000 fuzz files; the regression test is `test_comments_and_strings_do_not_confuse_the_retry`. | fixed r3 |
| F13 | Minor | `extractors/code_kotlin.py:64-80` | Valid one-liners were flagged `partial`. r3: `data class D(…) { fun f() = a }`, `enum class E { A, B; fun f() = 1 }`, `interface I { fun a(); fun b() }`, and one-line `when`, `if` and lambda bodies all give complete definitions and `partial=False`. Mutation M3 (`partial=has_error`) fails a test. The fix works through `partial=errors>0`; hidden MISSING nodes are still uncounted, and these files lose no definitions. | fixed r3 |
| F14 | Major | `extractors/code_kotlin.py:41,58-61,99-100` | **Wrong names, unflagged (regression vs 62f3a49).** When the retry tree wins, `_text` reads the **blanked copy**. The char-literal and string regexes also match inside backtick identifiers. Probe: `private class Fake { fun f() {} }` plus ``fun `user's name isn't empty`()`` gives ``UserTest.`user'          't empty` `` with `partial=False`; ``fun `returns "none" when`()`` is renamed the same way. Persisted in graph.json (`def:src/UserTest.kt::…`); 62f3a49 had the right id. **Why it matters:** a wrong graph fact (constitution §1), with a trigger that is common in Kotlin test suites. It also contradicts the README's "never guessed ones". **Fix:** read names from the original bytes (`source[n.start_byte:n.end_byte]`; same length makes this exact), and add a backtick-identifier alternative ``(`[^`\n]*`)`` first in `_LITERALS` that is kept unblanked. Add both probes as tests. | fixed |
| F15 | Minor | `extractors/code_kotlin.py:40,74-80` | **Silent loss (regression vs 62f3a49).** The string regex is not template-aware, so `"${if (a) "{" else "}"}"` or `"${ f("{ … }") }"` exposes a brace. The retry then parses with 0 errors but its top-level children stop early. On this machine the uncovered tail, `"   "\nfun real() {}`, had `has_error=False`. Everything after the line is dropped with `partial=False`: no stderr line, no `partial_files`. Scratch `Silent.kt` lost `Lost`/`Lost.lost`. All 754 unflagged losses in the fuzz trace to these two shapes. **Why it matters:** this is the false negative the flag exists to prevent, and plan §5 says such files are "named on stderr". Rated Minor, not Major, because it needs a brace literal nested in `${…}` plus a file-level one-line body; common templates (`${map["k"]}`, `${if (x) "a" else "b"}`, `joinToString(",")`) are unaffected. **Fix:** blank the `string_literal`/`comment` byte ranges from the original tree instead of a regex, or treat a non-whitespace byte not covered by a top-level child of the retry as an error. Add the probe as a test. | fixed |
| F16 | Minor | `extractors/code_kotlin.py:66`, `tests/test_extractor_kotlin.py` | Removing `or node.is_missing` passes all Kotlin and parity tests (M2). The term matters: `val x = (1` followed by `fun g() {}` has a visible MISSING `)`, loses `g`, and is flagged only because of that term. **Fix:** add this probe as a `partial is True` test. | fixed |

## 4. Requirements Traceability

The spec has no NFRs. Anti-generosity binary grading applies to every cell.

| Spec ID | Implemented at | Verdict |
|---|---|---|
| AC-1.1 | `extractors/base.py:56-57`, `extractors/__init__.py:25` | ✅ PASS — CLI build of scratch repo: `.kt`, `build.gradle.kts`, empty, random-bytes and bad-UTF-8 `.kt` all `language=kotlin`, no `unparsed`, exit 0 |
| AC-1.2 | `extractors/code_kotlin.py:58-91,121-170` | ❌ FAIL — F1's trigger is fixed. But valid Kotlin with a brace literal inside a nested template drops every later `Class` node, unflagged (F15, `Silent.kt`). |
| AC-1.3 | `extractors/code_kotlin.py:135-154` | ❌ FAIL — backtick-named functions are emitted under a **wrong** name (F14), and later functions are dropped unflagged (F15). |
| AC-2.1 (Should) | `build.py:248-258,311-341` | ✅ PASS — live: class, alias, isolated top-level-function and overloaded-function imports give File→File edges; overloads fan out to both files (F3 fixed) |
| AC-2.2 (Should) | `build.py:328-329` | ✅ PASS — live: `com.ex.util.*` and `kotlinx.coroutines.launch` give no edge; a `*` inside a comment is not read as a wildcard |
| AC-3.1 | `pyproject.toml:46`, `uv.lock` | ✅ PASS — pinned `==1.1.0`. The six-language scratch repo gave `0ac36af9…` from a fresh build, a cached build and `--full`, with identical stderr each time. A round-2 cache under HEAD falls back on the tag and gives the same bytes. The dd4b994 fixture gave `aafe108d…` under both the dd4b994 code and HEAD, with empty stderr on both. |
| AC-3.2 | `tests/test_extractor_kotlin.py` | ✅ PASS — 11 Kotlin tests, and both multi-language tests cover Kotlin. Mutations M1, M3 and M4 are caught; M2 is not (F16). |
| AC-3.3 | `README.md:272-279`, `README.md:298-299` | ✅ PASS — Kotlin is listed in "Supported languages" and the design guarantees. The "never guessed ones" claim is false until F14 is fixed. |

## 5. What Was Checked

- [x] Correctness: probed the hazards the caller asked for. Two produced wrong or lost definitions:
  - Backtick names containing a `'…'` pair or `"…"` are renamed (F14). Backtick names containing `//` are lost but flagged.
  - Nested-quote templates with a brace literal are lost, unflagged (F15).
  These produced correct definitions:
  - Char literals `'{'`, `'"'`, `'\''`, `'}'`.
  - Raw strings, including those containing `"`, `""""…""""`, multi-line, and with a template.
  - `//` in URL strings, KDoc, nested `/* /* */ */`, and `"it's { … }"`.
  An unterminated string is flagged `partial`. Fuzz, 6,000 files: 0 fabricated definitions and 0 wrong lines.
- [x] Non-functional: determinism holds (fresh, cached and `--full`), and non-Kotlin graphs are byte-identical to dd4b994 (see AC-3.1). No constitution §6 non-negotiable is violated. The §1 "honest absence beats a wrong link" principle is violated by F14.
- [x] Error handling: no tracebacks. A partial file is reported once on stderr and exit stays 0. F15 files escape the flag.
- [x] Security: no new input path. The regexes are linear and the 5 MB cap still applies.
  - `cli` lens: no new flag or exit code, and stdout is unchanged. The diagnostic goes to stderr only. It is a separate category from shallow-clone NFR-5's single history notice; AC-1.3 there is unaffected because v0.7.1 had no Kotlin.
  - MCP: `partial_files` is additive, and the parity test's key set is updated.
- [x] Tests: `uv run pytest`: 398 passed. `-m slow`: 4 passed. Mutations: M1, M3 and M4 each fail one test. M2 (F16) and M5 (`<=`, a harmless equal-count case) pass.
- [x] Readability: blanking and retry are small and commented. `kotlin-extractor=2` is a manual bump; its comment says when to bump it.

Open questions for the user/EM:
- (a) `.spark/constitution.md` §3 still says "five grammars" and lists five languages. The constitution is user-owned, so it is left unedited.
- (b) F9 and F10 are pre-existing. Waiving them is the user's call; they do not block this gate.

## 6. Verdict

Changes requested. I verified the fix round live against the pinned grammar.

Confirmed fixed (r3):
- **F1:** comment text no longer turns into code, and partial files are named on stderr and in `partial_files`, identically across CLI and MCP.
- **F12:** comments and strings no longer fabricate definitions; 0 in 6,000 fuzz files.
- **F13:** valid one-liners are complete and unflagged.

Determinism holds fresh, from cache and with `--full`, and the dd4b994 graph is byte-identical under the new code.

The regex blanking introduced two regressions that 62f3a49 did not have:
- **F14 (Major, open).** When the retry wins, names are read from the blanked copy. A Kotlin test file with a one-line fake and a backtick test name containing two apostrophes or a quoted word gets a wrong `Function` id, with `partial=False`. That is a wrong graph fact, so AC-1.3 fails.
- **F15 (Minor, open).** A brace literal inside a nested template drops the rest of the file, unflagged. AC-1.2 and AC-1.3 stay FAIL.
- **F16 (Minor, open).** The `is_missing` term has no test.

Fix F14 by reading names from the original bytes, which is a few lines, and land F15 and F16 with it. F9 and F10 are pre-existing and do not block.

---

## ✅ REVIEW GATE

*All boxes checked → `/demo-day` may start. Any box open → back to `/increment`. On
re-review, edit this same checklist in place — never duplicate it as a second gate.*

- [x] No open Blocker findings
- [ ] No open Major findings (or explicitly waived by the user, with reason recorded here) — F14 open
- [ ] Every Must AC traces to implementing code; no constitution non-negotiable violated — AC-1.2/AC-1.3 trace to code but FAIL (F14, F15); no §6 non-negotiable violated
- [x] All plan deviations documented and accepted — plan §5 records retry, blanking, `partial`, stderr/MCP and import fan-out; its "named on stderr" is false for F15 files (tracked there)
- [x] Test suite runs green — `uv run pytest`: 398 passed; `-m slow`: 4 passed
- [x] Line budget respected: Ist 133 / Soll ~150 (excluding HTML comments)
- [ ] Status set to `passed` — `changes-requested`
