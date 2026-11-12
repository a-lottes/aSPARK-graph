# Review Report: qa-multi-table

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | The diff of `/increment` (`64c533c~1..4633cdd`; round 2 = `git diff 58522cc..4633cdd`), `.spark/qa-multi-table/plan.md` |
| **Status** | `changes-requested` |
| **Round** | 2 |
| **Date** | 2026-11-12 |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Verdict:** F6 fixed: later tables are read only with an exact `AC`/`Spec ID` header; re-review needed.
- **Open:** `0 open` (F6, F7 `fixed`, awaiting re-review). Blockers: none. Majors: none.
- **Binding ruling:** §6 Verdict and the gate checklist below are the only binding location. There is no other round to point to.
- **On conflict:** the numbered body below wins for everything except `Status`. Log the mismatch as a finding at the next `/peer-review` and proceed. Do not stop on it.

## 1. Scope

- **Reviewed (r2):** `git diff HEAD~1` (`4633cdd`): `_parse_qa` (`artifacts.py:284-321`), two new/changed tests in `tests/test_qa_multi_table.py`, `.spark/BACKLOG.md:240`. Context re-read: `_qa_id_column` (:324-336) and `_col` (:417-424, substring match).
- **Graph (aspark-graph CLI; no MCP tools were exposed to this agent):**
  - `staleness`: stale (`artifacts.py` and the test file changed). I ran `build` once (2 files re-parsed).
  - `impact --diff HEAD~1..HEAD --brief` reaches `qa-multi-table` US-1/US-2, `current-artifact-names` US-1/US-4 and `coverage-current-names` US-1 via `artifacts.py`. As a result, I re-ran the full suite as the regression net.
  - Round-1 `story_trace` results still apply: no new files.
- **Mode:** live probes (`/tmp/rv2/probe.py`) plus the test suite, and the regression test run against `58522cc` code in a worktree. I did not run the slow suite: no packaging, transport or install path changed.
- **Corpus:** I re-scanned the 34 Core `qa.md` files (scratch `/tmp/rv/core`) and `/opt/aspark/.spark` for later tables with a loose `ac…` id header or no id header. There are 0 hits.
- **Not reviewed:** the CLAUDE.md/constitution.md G6 mentions. The caller says they are intentionally left to `/go-live`.
- **Anti-generosity standard applied** (`/opt/aspark/standards/anti-generosity.md`, read in full).

## 2. Plan Conformance

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 | ✅ | `_tables` + `_first_table = next(_tables(...), None)` (`artifacts.py:372-389`). Existing suite green with no edits. |
| T2 | ❌ | The r2 skip rule (`artifacts.py:297-300`) goes beyond plan §1, which skips a later table only when `_qa_id_column` is `None`. This is not recorded under Deviations (F7). The residual drift case is F6. |
| T3 | ✅ | After F2, `latest_result == "fail"` is asserted exactly for a later-table AC. |
| T4 | ✅ | Round 1 re-derived this (old/new `cmp` identical). In r2, `_parse_qa` changed only for later tables (`not is_first`), so the single-table path is untouched. I did not re-run the cmp. |
| T5 | ✅ | The marker now reads "Version: wird bei `/go-live` ergänzt" (`BACKLOG.md:240`). The version is unknowable before release, so I accept this deferral (F4). |

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Major | `src/aspark_graph/artifacts.py:289-296` (with `_qa_id_column` :317-329) | The notes-table test uses `_qa_id_column`, whose v0.7.0 prefix rule accepts any header starting with `ac`. A later notes table with a header such as `Action`, `Actual`, `Acceptance note` or `Account` therefore counts as an id column. With no Result column, the whole build fails with `TemplateDriftError … (table 2) missing a 'Result' column (found ['action','item'])` (probe output). In v0.7.3 the same file builds. This breaks the "notes table is skipped" clause of AC-2.2 and turns a working repo into a failed build (0 of 34 Core qa.md hit it today). Fix: for later tables, accept only the exact `ac`/`spec id` headers, or skip a later table in which no id cell matches `AC-\d+\.\d+`. Add a regression test using an `Action` header. r2: the reproducer (`Item \| Action`, no AC ids) now builds. `test_notes_table_with_loose_ac_prefix_header_is_skipped` fails on `58522cc` and passes now. The residual is tracked as F6. | fixed r2 |
| F2 | Minor | `tests/test_qa_multi_table.py:54-60` (orig.) | Under the pre-change parser, both gate_health assertions still passed: AC-1.2 sat in table 1, and AC-2.1 is unverified either way. Only `"fail" in str(trace)` told old and new apart. The T3 DoD (a later-table AC counted as passed) was never asserted. Fixed by the reviewer: AC-1.2 (pass) and AC-2.1 (fail) now sit in a later table, and `latest_result == "fail"` is asserted exactly. Verified failing under old code. | fixed r1 |
| F3 | Minor | `tests/test_qa_multi_table.py` | The plan's R2 mitigation says "a test pins the behaviour". Only `_first_table`/`_tables` were pinned, not `_parse_qa` reading a valid table after a malformed run. Fixed by the reviewer: `test_malformed_first_run_then_valid_table_produces_checks` (AC-2.1 at order 0). Verified failing under old code. | fixed r1 |
| F4 | Minor | `.spark/BACKLOG.md:240` | The T5 DoD says "done marker naming `qa-multi-table` and the version". r2: the marker now states that the version is added at `/go-live`. That is the first fix option, and it is accepted because the version is not fixed before release. `/go-live` must replace the text with the shipped version. (Artifact wording, capped at Minor.) | fixed r2 |
| F5 | Nit | `src/aspark_graph/artifacts.py:284,295` | `position` counts only well-formed tables. Malformed runs are dropped before `enumerate`, but notes tables are counted. So "(table N)" in the drift message can disagree with the document. r2: the code now enumerates the raw `_tables` output with an `is_first` flag (:286-290). Probe: valid, then malformed, then broken input reports "(table 3)". There is no test pinning the message (Nit, acceptable). | fixed r2 |
| F6 | Major | `src/aspark_graph/artifacts.py:297-303` | The F1 fix is content-based. A later table whose loose `ac…` column cites an AC id is still read as a verification table. Probe 1: `\| # \| Action \| Owner \|` / `\| 1 \| Re-verify AC-1.2 live \| QA \|` gives `TemplateDriftError … (table 2) missing a 'Result' column (found ['#','action','owner'])`, so a repo that builds on v0.7.3 now fails. Probe 2: `\| Action \| Result \|` / `\| Re-ran AC-1.2 \| ✅ done \|` adds a `pass` QACheck at order 2, which then becomes AC-1.2's `latest_result`. A follow-up list becomes a verdict. Either way AC-2.2 ("a later table without an AC id column … is skipped") fails for a notes table. The option-2 fix that round 1 suggested was incomplete. Fix: for tables after the first, accept only the exact `ac`/`spec id` headers and skip anything else. The corpus scan found 0 later tables with loose headers, so nothing real is lost. Add both probes as tests. | fixed |
| F7 | Minor | `src/aspark_graph/artifacts.py:297-300`, `plan.md` §1/Deviations | The skip now also applies to exact-header later tables. Probe: `\| Spec ID \| Notes \|` / `\| NFR-1 \| x \|` is skipped silently, where plan §1 and the literal AC-2.2 third clause say drift. No AC data is lost (rows without an `AC-n.m` produce no check either way), but this is an undocumented plan deviation. Fix: restrict the content check to the loose-header case, which goes away with F6's fix, or record it under plan Deviations. | fixed |

## 4. Requirements Traceability

| Spec ID | Implemented at | Verdict |
|---|---|---|
| AC-1.1 | `artifacts.py:284-321`. Tests `test_every_table_row_…`; Core corpus: graph-gates 5→30, lean-artifacts 8→15, project-kickoff 6→26, tracker-handoff 5→21 checks | ✅ met |
| AC-1.2 | `queries.gate_health`/`story_trace` unchanged. Hands-on scratch per-story qa.md (4 tables incl. a `### Notes` table): new `unverified_acs: []`, US-2 AC-2.1 `latest_result: pass`; old code listed AC-1.2 and AC-2.1 as unverified | ✅ met |
| AC-1.3 | `artifacts.py:304,320` (`start=offset`, offset += rows). Test `test_ac_in_two_tables_…` | ✅ met |
| AC-2.1 | `artifacts.py:374` + offset 0 for the first table. T4 old/new `cmp` is identical (§2). The other 22 non-erroring Core qa.md files parse identically under old and new | ✅ met |
| AC-2.2 | `artifacts.py:293-303`. First-table drift and later id-without-Result drift hold. A loose-header notes table without AC ids is skipped (r2), but one that cites an AC id still drifts or is read (F6) | ❌ missing |
| AC-3.1 | `.spark/BACKLOG.md:240`. README never stated the limit (grep) | ✅ met (version per F4) |

## 5. What Was Checked

- [x] Correctness: logic does what the acceptance criteria demand. Exception: AC-2.2 (F6).
- [x] Non-functional: the single-table path is unchanged in r2, and the double-build test is green.
- [x] Error handling: drift still raises loudly, naming the file. No swallowed errors.
- [x] Security: no new input surface.
- [x] Tests: 413 pass. The new F1 test fails on pre-fix code. F6's probes are not yet tests.
- [x] Readability: the `is_first` flag is clear. The skip comment at :300 says "loose" but the rule also applies to exact headers (F7).

## 6. Verdict

Round 2 does not pass.

What the developer fixed:
- **F1.** The reported input now builds, and its regression test discriminates: it fails on `58522cc` and passes now.
- **F5.** Table numbering in the drift message now counts every pipe run.
- **F4.** The BACKLOG marker defers the version to `/go-live`. I accept that, because the version cannot be known earlier.
- **Suite.** Green: 413 passed, 4 slow deselected.

What still fails: the fix keys on cell content rather than the header. A later `Action` table that mentions an AC id still breaks a build that works on v0.7.3. If that table also has a `Result` column, a follow-up row becomes the AC's latest verdict. So Must AC-2.2 still fails, which is F6 (Major, open). F7 (an undocumented widening of the skip rule) is open as a Minor, and F6's suggested fix removes it.

Status is `changes-requested`. This goes back to `/increment`.

---

## ✅ REVIEW GATE

- [x] No open Blocker findings
- [ ] No open Major findings (or explicitly waived by the user, with reason recorded here). F6 is open.
- [ ] Every Must AC traces to implementing code; no constitution non-negotiable violated. AC-2.2 is ❌ (F6); no non-negotiable violated.
- [ ] All plan deviations documented and accepted. The T2 skip-rule widening is undocumented (F7).
- [x] Test suite runs green (413 passed, 4 slow deselected)
- [x] Line budget respected: Ist ~85 / Soll ~150 (excluding HTML comments)
- [ ] Status set to `passed`
