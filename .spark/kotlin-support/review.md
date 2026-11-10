# Review Report: kotlin-support

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | The diff of `/increment` (`git diff dd4b994..HEAD`; fix round ff6a910 = `git diff 8dc45c6..HEAD`), `.spark/kotlin-support/plan.md` |
| **Status** | `changes-requested` |
| **Round** | 4 |
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
- **Verdict:** Changes requested (r4). F14, F15 and F16 are confirmed fixed. The reviewer fixed F18 (Major), F19 and F20 in the working tree; these fixes are uncommitted. F17 (Minor) is still open, and it keeps AC-1.2 and AC-1.3 at FAIL.
- **Open:** `3 open` — Blockers: none; Majors: none (F17 Minor; F9 Minor and F10 Nit are pre-existing and non-blocking)
- **Binding ruling:** §6 Verdict and the gate checklist below are the only binding location. There is no other round to point to.
- **On conflict:** the numbered body below wins for everything except `Status`. Log the mismatch as a finding at the next `/peer-review` and proceed; don't stop on it.

## 1. Scope

- **Reviewed:** the fix round `git diff 8dc45c6..HEAD` in full (`code_kotlin.py`, `test_extractor_kotlin.py`, plan §5). `/increment`'s edit to this report was also checked. Context: all of `code_kotlin.py`, `parse_cache.py:38-46`, and `README.md:272-278`.
- **Mode:** live run with the pinned `tree-sitter-kotlin==1.1.0` and `tree-sitter==0.26.0` (versions printed). Checks:
  - the full suite and the slow suite (slow ×3);
  - 16 hand probes;
  - the r3 seeded fuzz re-run (seed 31, 6,000 files), plus an extended fuzz of 26,000 files (seeds 31, 4 and 77). The extended fuzz adds backtick names containing `{ }`, `//`, `'` and `"`, one-line backtick bodies, and nested-quote templates holding `/*`, `*/`, `//`, `'`, `` ` `` and `{ `. Every definition's (name, kind, parent, line) is checked against the known set;
  - 10 mutations;
  - CLI ×3 (fresh, cached, `--full`) and MCP builds of a git-marked six-language scratch repo;
  - a dd4b994-worktree vs working-tree round trip on `tests/fixtures/sample_repo`.

  Each fix was re-derived from source under condition (a): this round verifies those fixes. Mode is not degraded for any item below.
- **Standards applied:** Anti-generosity standard applied (`/opt/aspark/standards/anti-generosity.md`). Active lens: `cli` (`/opt/aspark/lenses/cli.md`). Tool file: `/opt/aspark/tools/aspark-graph.md`.
- **Graph (aspark-graph):** I rebuilt it with `uv run aspark-graph build .` (2 files re-parsed, 63 cached). `staleness`: fresh, 65 files. `impact --diff 8dc45c6..HEAD`:
  - It reaches `code_kotlin.py` and `test_extractor_kotlin.py`, each with no linked stories. The plan has no `files:` notes, so this is empty by construction, not an all-clear. As a result I read all of `code_kotlin.py` and traced its `extract()` paths.
  - plan.md and review.md are in `unknown_files`, so I read them by hand.
  - `story_trace US-1`: T1 has `code: []`, and there are no QA checks. The QA leg was not read (tool rule).
- **Not reviewed:** `qa.md` (QA's placeholder, left untouched). The adapters and `build.py` are unchanged since r3 and were not re-examined beyond the scratch builds.

## 2. Plan Conformance

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 | ✅ | Matches plan §5 as reworded by ff6a910: comments are blanked, literals are skipped verbatim, ERROR regions are not walked, and `partial` is reported on stderr and in `partial_files`. Plan §5 says "never walked" and "named on stderr". F18 (fixed) and F17 (open) were exceptions to those claims. |
| T2 | ✅ | Unchanged since r2. The import fan-out is a deviation, recorded in plan §5. |
| T3 | ✅ | The new tests cover F14, F15 and F16. The F20 test gap was closed by the reviewer. README `:276-278` is unchanged; its "is marked `partial`" claim is false for F17 files. |

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
| F9 | Minor | `tests/test_incremental_bench.py:97` | Pre-existing: the NFR-1 benchmark (slow) is flaky on this machine. r4: 1 of 3 `-m slow` runs failed it (`49.7% faster`, needs 50%); the other two passed 4/4. **Fix (EM):** settle it on the release machine before `/go-live`. A waiver is the user's call. | open |
| F10 | Nit | `parse_cache.py:38-46` | Pre-existing: the cache tag does not include the go/rust grammar versions. r4: unchanged. **Fix:** add both to the tag. A waiver is the user's call. | open |
| F11 | Nit | `tests/test_extractor_java.py:50` | Duplicate `test_all_six_languages_in_one_build`. Round 2: the Java test is renamed `test_all_languages_in_one_build` and covers Kotlin; the Kotlin copy is deleted. | fixed r2 |
| F12 | Minor | `extractors/code_kotlin.py:36-43` | A comment with an unclosed `{` could fabricate an unflagged definition. r3: `/// Usage: { fun sample()` and `{ fun ghost() }` inside strings, raw strings, KDoc and nested block comments produce no definition in 6,000 fuzz files; the regression test is `test_comments_and_strings_do_not_confuse_the_retry`. | fixed r3 |
| F13 | Minor | `extractors/code_kotlin.py:64-80` | Valid one-liners were flagged `partial`. r3: `data class D(…) { fun f() = a }`, `enum class E { A, B; fun f() = 1 }`, `interface I { fun a(); fun b() }`, and one-line `when`, `if` and lambda bodies all give complete definitions and `partial=False`. Mutation M3 (`partial=has_error`) fails a test. The fix works through `partial=errors>0`; hidden MISSING nodes are still uncounted, and these files lose no definitions. | fixed r3 |
| F14 | Major | `extractors/code_kotlin.py:37-61` | When the retry won, names were read from the blanked copy, so backtick names were renamed without a flag. r4: literals, including backtick names, are now kept verbatim (`:58`). The r3 probes ``UserTest.`user's name isn't empty` `` and ``UserTest.`returns "none" when` `` are correct with `partial=False`, by hand, in the scratch graph.json and in 26,000 fuzz files. Mutation M6 (blank literal interiors again) fails `test_retry_never_rewrites_identifiers_or_literals`. | fixed r4 |
| F15 | Minor | `extractors/code_kotlin.py:37-61` | A brace literal inside a nested template dropped the rest of the file without a flag. r4: `"${if (a) "{" else "}"}"` and `"${ f("{ x }") }"` give every definition with `partial=False`, by hand and in the scratch `Silent.kt` (`Lost`, `Lost.lost` are present). The r3 fuzz (seed 31) has 0 unflagged losses. The test's `… or r.partial` disjunction is weak but adequate for "never unflagged". | fixed r4 |
| F16 | Minor | `extractors/code_kotlin.py:66`, `tests/test_extractor_kotlin.py:185-186` | The `is_missing` term was untested. r4: removing `or node.is_missing` (M2) fails `test_missing_nodes_flag_the_file_partial`. | fixed r4 |
| F17 | Minor | `extractors/code_kotlin.py:37-41,58` | **The comment regex is not a lexer.** It is not template-aware: a `"` inside `${…}` desyncs it. It is also not nesting-aware (`/\*.*?\*/`).<br>(a) **Silent loss:** in `val g = "${dir("/*")}"` / `fun top1() {}` / `class S3 {…}` / `val h = "${dir("*/")}"` / `class X4 { companion object { const val T = 1 } }`, the text from `/*` to `*/` is blanked as one comment. The retry then parses with 0 errors and drops `top1`, `S3` and `S3.s` with `partial=False`, so nothing appears on stderr or in `partial_files` (scratch `Desync.kt`). All 43 unflagged losses in 26,000 fuzz files need this `/*` … `*/` pair.<br>(b) **Flagged loss, regression vs 62f3a49:** a valid nested comment `/* a /* b */ c */` in a file with a one-line body is half-blanked. The file is then flagged `partial` and loses definitions that 62f3a49 recovered.<br>**Why it matters:** (a) is the false negative the flag exists to prevent. It is Minor, not Major, because it needs two nested-quote templates holding comment markers plus a one-line body.<br>**Limit:** valid Kotlin without a `/*` or `*/` inside a nested-quote template has no unflagged loss in the fuzz.<br>**Fix:** keep comments verbatim like literals (`out.append(m.group(0))`) — they are already tokens, so they are never rewritten. Measured as mutation M9: 0 unflagged, 0 wrong and 103 flagged files in 26,000, against 43, 0 and 4,374 now. All 402 tests pass, `Desync.kt` is complete, and F1 and F12 stay fixed. Update plan §5 and add the `Desync.kt` repro as a test. | fixed |
| F18 | Major | `extractors/code_kotlin.py:90-91` | **Wrong fact: a mis-parented definition from a root ERROR.** When the chosen tree's root is itself `ERROR`, `_walk(root, …)` walks it, which is the F2 class through the root node. Repro (`test_root_error_is_never_walked`): `object O1 { fun o() = 1 }` followed by two `/* outer /* inner */ … */` lines and a companion one-liner emitted top-level `Function o` (parent `None`) with `partial=True`. Latent since d3742d9; it is exposed because F17(b)'s blanking makes the retry lose. **Reviewer fix:** `if root.type != "ERROR":` guards the walk. Now 0 wrong definitions in 26,000 fuzz files; scratch `RootErr.kt` is flagged and has no `o`. Mutation M10 (unguarded) fails the new test, and so would a regression. The test passes under F17's suggested fix. | fixed r4 |
| F19 | Minor | `parse_cache.py:45` | ff6a910 changed `code_kotlin`'s output for the same bytes (F14 names), and so does F18. The tag stayed `kotlin-extractor=2`, against its own comment ("bump when … output for the same bytes changes"), so a cache from 8dc45c6 would keep serving the wrong names. **Reviewer fix:** bumped to `3`. Scratch builds are fresh, cached and `--full`, byte-identical. | fixed r4 |
| F20 | Minor | `tests/test_extractor_kotlin.py:189-199` | Test gap: dropping the backtick token (M7) or rewriting inside literals (M8) passed every test. Both make ``fun `given { x } then`()`` flagged and lossy. **Reviewer fix:** `test_retry_keeps_backtick_names_with_braces_and_slashes` asserts the exact definition set; M7 and M8 now fail it. | fixed r4 |

## 4. Requirements Traceability

The spec has no NFRs. Anti-generosity binary grading applies to every cell.

| Spec ID | Implemented at | Verdict |
|---|---|---|
| AC-1.1 | `extractors/base.py:56-57`, `extractors/__init__.py:25` | ✅ PASS — CLI build of scratch repo: `.kt`, `build.gradle.kts`, empty, random-bytes and bad-UTF-8 `.kt` all `language=kotlin`, no `unparsed`, exit 0 |
| AC-1.2 | `extractors/code_kotlin.py:53-91,157-170` | ❌ FAIL — the F14/F15 triggers are fixed. Valid Kotlin with a `/*` … `*/` pair in nested-quote templates still drops the `Class` node `S3` without a flag (F17a, scratch `Desync.kt`). |
| AC-1.3 | `extractors/code_kotlin.py:135-154` | ❌ FAIL — names are now exact (F14 fixed; 0 wrong in 26,000 files). `top1` and `S3.s` are still dropped without a flag in the F17a repro. |
| AC-2.1 (Should) | `build.py:248-258,311-341` | ✅ PASS — live: class, alias, isolated top-level-function and overloaded-function imports give File→File edges; overloads fan out to both files (F3 fixed) |
| AC-2.2 (Should) | `build.py:328-329` | ✅ PASS — live: `com.ex.util.*` and `kotlinx.coroutines.launch` give no edge; a `*` inside a comment is not read as a wildcard |
| AC-3.1 | `pyproject.toml:46`, `uv.lock` | ✅ PASS — pinned `==1.1.0`. The six-language scratch repo gave `0ac36af9…` from a fresh build, a cached build and `--full`, with identical stderr each time. A round-2 cache under HEAD falls back on the tag and gives the same bytes. The dd4b994 fixture gave `aafe108d…` under both the dd4b994 code and HEAD, with empty stderr on both. |
| AC-3.2 | `tests/test_extractor_kotlin.py` | ✅ PASS — 15 Kotlin tests; both multi-language tests cover Kotlin. Mutations M2, M6, M7, M8 and M10 each fail a test. M9 passes, but M9 is F17's fix, not a defect. |
| AC-3.3 | `README.md:272-279`, `README.md:298-299` | ✅ PASS — Kotlin is listed in "Supported languages" and in the design guarantees. "Never guessed ones" now holds (F18 fixed). "Is marked `partial`" is false for F17a files, and that is tracked there. |

## 5. What Was Checked

- [x] Correctness: the caller's shapes are correct with `partial=False` under HEAD and the reviewer fixes:
  - backtick names containing `'…'`, `"…"`, `{ x }` or `// /* */`, inside one-line bodies and as class names;
  - extension functions;
  - ``"${if (a) "{" else "}"}"`` and `"${ f("{ x }") }"`;
  - nested-quote templates holding `//`, `'` and `` ` ``.

  Fuzz results:
  - r3 fuzz (seed 31): 5,420 exact, 578 flagged, 0 wrong, 0 unflagged.
  - Extended fuzz (26,000 files): 0 wrong names, parents or lines after F18; 43 unflagged losses, all F17a; 4,374 flagged.
- [x] Non-functional:
  - The scratch repo gave `769dd4b9…` from a fresh build, a cached build, `--full` and MCP, with identical stderr each time.
  - The non-Kotlin `sample_repo` gave `7a82e69c…` under both the dd4b994 worktree and the working tree, with identical stderr.
  - No constitution §6 non-negotiable is violated. §1 "honest absence" is violated only by F17a.
- [x] Error handling: no tracebacks. Partial files are reported once on stderr and in MCP `partial_files` (`['src/Bad.kt', 'src/RootErr.kt']`), and exit is 0. F17a files escape the flag.
- [x] Security: no new input path. The token regex is linear; the 5 MB cap still applies.
  - `cli` lens: no flag, exit-code or stdout change this round. Diagnostics stay on stderr.
- [x] Tests: `uv run pytest`: 402 passed. `-m slow`: 1 of 3 runs failed the F9 benchmark at 49.7%; the other two passed 4/4. There are 10 mutations, listed in §3 and §4.
- [x] Readability: the tokenizer is small and commented. The F18 guard carries its own comment.

Open questions for the user/EM:
- (a) `.spark/constitution.md` §3 still says "five grammars" (`:39`). The constitution is user-owned, so it is left unedited.
- (b) F9 and F10 are pre-existing. Waiving them is the user's call; they do not block this gate.
- (c) F17 can instead be accepted as a documented limit. That is the user's call; the limit would then go in plan §5 and the README.
- (d) The reviewer fixes F18, F19 and F20 are uncommitted in the working tree: `code_kotlin.py`, `parse_cache.py` and `test_extractor_kotlin.py`.

## 6. Verdict

Changes requested. I verified round 4 live against the pinned grammar.

Confirmed fixed (r4):
- **F14:** backtick and other literal names are exact.
- **F15:** brace literals in nested templates no longer drop the rest of the file.
- **F16:** the MISSING term is tested.

The extended fuzz found a Major the earlier rounds missed. **F18:** a root `ERROR` node was walked, which fabricated a top-level function. It is latent since d3742d9 and exposed by the comment regex. I fixed it with a one-line guard and a test, together with the stale cache tag (F19) and a test gap (F20). After these fixes, 26,000 fuzz files contain no wrong definition.

**F17 (Minor, open)** is the one remaining defect. The regex comment blanking is neither nesting-aware nor template-aware:
- A `/*` … `*/` pair inside nested-quote templates silently drops definitions.
- Valid nested comments now lose definitions in a flagged file, where 62f3a49 kept them.

The trigger is narrow, so the severity is Minor. It is still a silent loss on valid Kotlin, so AC-1.2 and AC-1.3 stay FAIL under binary grading. The measured fix is one line: keep comments verbatim, like literals. It clears all 43 silent cases and cuts flagged files from 4,374 to 103. Alternatively, the user can accept F17 as a documented limit. F9 and F10 are pre-existing and do not block.

---

## ✅ REVIEW GATE

*All boxes checked → `/demo-day` may start. Any box open → back to `/increment`. On
re-review, edit this same checklist in place — never duplicate it as a second gate.*

- [x] No open Blocker findings
- [x] No open Major findings (or explicitly waived by the user, with reason recorded here) — F14 fixed r4, F18 fixed r4 (reviewer)
- [ ] Every Must AC traces to implementing code; no constitution non-negotiable violated — AC-1.2/AC-1.3 trace to code but FAIL (F17a); no §6 non-negotiable violated
- [x] All plan deviations documented and accepted — plan §5 records retry, comment blanking, verbatim literals, `partial`, stderr/MCP and import fan-out; its "named on stderr" is false for F17a files (tracked there)
- [x] Test suite runs green — `uv run pytest`: 402 passed; `-m slow`: 4 passed in 2 of 3 runs, the 3rd failed only the pre-existing F9 bench
- [x] Line budget respected: Ist 147 / Soll ~150 (excluding HTML comments)
- [ ] Status set to `passed` — `changes-requested`
