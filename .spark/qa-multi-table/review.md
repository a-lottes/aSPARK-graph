# Review Report: qa-multi-table

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | The diff of `/increment` (`64c533c~1..58522cc`), `.spark/qa-multi-table/plan.md` |
| **Status** | `changes-requested` |
| **Round** | 1 |
| **Date** | 2026-11-12 |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Verdict:** Round-1 Major F1 fixed (later tables are skipped unless an id cell matches `AC-n.m`); re-review needed.
- **Open:** `0 open` (F1, F4, F5 `fixed`, awaiting re-review). Blockers: none. Majors: none. Minors and Nits: see §3.
- **Binding ruling:** §6 Verdict and the gate checklist below are the only binding location. There is no other round to point to.
- **On conflict:** the numbered body below wins for everything except `Status`. Log the mismatch as a finding at the next `/peer-review` and proceed. Do not stop on it.

## 1. Scope

- **Reviewed:** `git diff 64c533c~1 HEAD`, which covers `src/aspark_graph/artifacts.py` (`_parse_qa`, `_first_table`, new `_tables`/`_table_from_rows`), the new `tests/test_qa_multi_table.py`, the BACKLOG G6 marker and the plan status/Deviations edits. For context I also read `_section`, `_qa_id_column`, `_normalise_result`, `_parse_review` (a `_first_table` caller) and `queries.gate_health`.
- **Graph (aspark-graph CLI; no MCP tools were exposed to this agent):**
  - `staleness`: fresh, 67 files.
  - `impact --diff 64c533c~1..HEAD --brief` reaches `current-artifact-names` US-1/US-4 and `coverage-current-names` US-1 via `artifacts.py`. As a result, I re-ran `test_current_names.py`/`test_artifacts.py` as the regression net (green, unedited).
  - `story_trace US-1/US-2 --feature qa-multi-table` returns T1/T2 → `artifacts.py` and T2/T3 → the test file, all `declared`. Those are the locations I read.
  - The graph was fresh, so I did not run `build_graph`.
- **Mode:** live runs plus the test suite. I did not run the slow suite (`-m slow`): the diff touches no packaging, transport or install path.
- **Not reviewed:** the CLAUDE.md/constitution.md G6 mentions. The caller says they are intentionally left to `/go-live`.
- **Anti-generosity standard applied** (`/opt/aspark/standards/anti-generosity.md`, read in full).

## 2. Plan Conformance

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 | ✅ | `_tables` + `_first_table = next(_tables(...), None)` (`artifacts.py:365-383`). Existing suite green with no edits. |
| T2 | ✅ | Running offset, strict first table, notes skip, later-table drift (`artifacts.py:284-314`). The *definition* of "id column" causes F1. |
| T3 | ❌ | The DoD says to assert that gate_health counts a later-table AC as passed. The test only asserted first-table/unverified facts plus a substring match (F2, now fixed). |
| T4 | ✅ | Re-derived (condition (b): it is the Must AC-2.1 proof). Same input tree (`58522cc`), built by old code (`64c533c~1` worktree) vs new code: this repo `c91a4b353d17ec3f…` = `c91a4b353d17ec3f…`, and `current_names_repo` `07ee6b9ca8e821c2…` = same. `cmp` reports identical. The plan's Deviation ("differs by `artifacts.py` symbol entries") came from varying the source tree along with the code. With input held constant there is no deviation. |
| T5 | ❌ | The DoD requires the version in the G6 marker. The marker names the feature and #72 but no version (F4). |

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Major | `src/aspark_graph/artifacts.py:289-296` (with `_qa_id_column` :317-329) | The notes-table test uses `_qa_id_column`, whose v0.7.0 prefix rule accepts any header starting with `ac`. A later notes table with a header such as `Action`, `Actual`, `Acceptance note` or `Account` therefore counts as an id column. With no Result column, the whole build fails with `TemplateDriftError … (table 2) missing a 'Result' column (found ['action','item'])` (probe output). In v0.7.3 the same file builds. This breaks the "notes table is skipped" clause of AC-2.2 and turns a working repo into a failed build (0 of 34 Core qa.md hit it today). Fix: for later tables, accept only the exact `ac`/`spec id` headers, or skip a later table in which no id cell matches `AC-\d+\.\d+`. Add a regression test using an `Action` header. | fixed |
| F2 | Minor | `tests/test_qa_multi_table.py:54-60` (orig.) | Under the pre-change parser, both gate_health assertions still passed: AC-1.2 sat in table 1, and AC-2.1 is unverified either way. Only `"fail" in str(trace)` told old and new apart. The T3 DoD (a later-table AC counted as passed) was never asserted. Fixed by the reviewer: AC-1.2 (pass) and AC-2.1 (fail) now sit in a later table, and `latest_result == "fail"` is asserted exactly. Verified failing under old code. | fixed |
| F3 | Minor | `tests/test_qa_multi_table.py` | The plan's R2 mitigation says "a test pins the behaviour". Only `_first_table`/`_tables` were pinned, not `_parse_qa` reading a valid table after a malformed run. Fixed by the reviewer: `test_malformed_first_run_then_valid_table_produces_checks` (AC-2.1 at order 0). Verified failing under old code. | fixed |
| F4 | Minor | `.spark/BACKLOG.md:240` | The T5 DoD says "done marker naming `qa-multi-table` and the version". The marker has no version, yet T5 is marked `done`. Fix: add the release version at `/go-live`, or amend the DoD. (Artifact wording, capped at Minor.) | fixed |
| F5 | Nit | `src/aspark_graph/artifacts.py:284,295` | `position` counts only well-formed tables. Malformed runs are dropped before `enumerate`, but notes tables are counted. So "(table N)" in the drift message can disagree with the document. Fix: enumerate the raw `_tables` output and track "first valid table" with a separate flag. | fixed |

## 4. Requirements Traceability

| Spec ID | Implemented at | Verdict |
|---|---|---|
| AC-1.1 | `artifacts.py:284-313`. Tests `test_every_table_row_…`; Core corpus: graph-gates 5→30, lean-artifacts 8→15, project-kickoff 6→26, tracker-handoff 5→21 checks | ✅ met |
| AC-1.2 | `queries.gate_health`/`story_trace` unchanged. Hands-on scratch per-story qa.md (4 tables incl. a `### Notes` table): new `unverified_acs: []`, US-2 AC-2.1 `latest_result: pass`; old code listed AC-1.2 and AC-2.1 as unverified | ✅ met |
| AC-1.3 | `artifacts.py:298,314` (`start=offset`, offset += rows). Test `test_ac_in_two_tables_…` | ✅ met |
| AC-2.1 | `artifacts.py:368` + offset 0 for the first table. T4 old/new `cmp` is identical (§2). The other 22 non-erroring Core qa.md files parse identically under old and new | ✅ met |
| AC-2.2 | `artifacts.py:289-296`. First-table drift and later id-without-Result drift hold; the notes-table skip fails for `ac…` headers (F1) | ❌ missing |
| AC-3.1 | `.spark/BACKLOG.md:240`. README never stated the limit (grep) | ✅ met (version per F4) |

## 5. What Was Checked

- [x] Correctness: logic does what the acceptance criteria demand. Exception: AC-2.2 (F1).
- [x] Non-functional: determinism is proven by the old/new `cmp` and the double-build test (green).
- [x] Error handling: drift still raises loudly, naming the file. No swallowed errors.
- [x] Security: no new input surface; parsing is pure string handling of an already-read file.
- [x] Tests: they exist and pass (412 after the reviewer's edits). Two weak spots fixed (F2, F3). 7 of 8 tests fail under the old parser.
- [x] Readability: `_tables`/`_table_from_rows` split is clear; no dead code.

## 6. Verdict

The increment does what issue #72 asks on real data:
- **Core corpus.** On a scratch copy of the 34 Core `qa.md` files, exactly the four per-story reports named in G6 now yield their later ACs, with verdicts that follow the marker rule (graph-gates' `⚠ partial` rows read `unknown`, its `❌ not-verified-live` rows read `fail`). The other 22 parseable files are unchanged, and no new drift error appears.
- **Byte-identity.** It holds against the pre-change code when the input tree is held constant.
- **Suite.** Green: 411 passed before my edits, 412 after.

It does not pass. Must AC-2.2 promises that a later table without an AC id column is skipped. A notes table headed `Item | Action` (or any header starting with `ac`) is instead treated as a verification table and fails the entire build. A repo that builds under v0.7.3 would stop building after this change. That is F1 (Major), and it goes back to `/increment`.

I fixed two test weaknesses myself (F2, F3). Both new assertions were confirmed to fail under the old parser. F4 (version missing from the G6 marker) and F5 (table numbering in the drift message) stay open as Minor and Nit.

Status is `changes-requested`.

---

## ✅ REVIEW GATE

- [x] No open Blocker findings
- [ ] No open Major findings (or explicitly waived by the user, with reason recorded here). F1 is open.
- [ ] Every Must AC traces to implementing code; no constitution non-negotiable violated. AC-2.2 is ❌ (F1); no non-negotiable violated.
- [x] All plan deviations documented and accepted. The T4 Deviation was re-derived as no deviation (§2).
- [x] Test suite runs green (412 passed, 4 slow deselected)
- [x] Line budget respected: Ist ~75 / Soll ~150 (excluding HTML comments)
- [ ] Status set to `passed`
