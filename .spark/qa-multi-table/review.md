# Review Report: qa-multi-table

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | The diff of `/increment` (`64c533c~1..b16d4bf`; round 3 = `git diff 4633cdd..b16d4bf`), `.spark/qa-multi-table/plan.md` |
| **Status** | `passed` |
| **Round** | 3 |
| **Date** | 2026-11-12 |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Verdict:** Round 3 passes. F6 and F7 are confirmed fixed, and the T2 header rule is recorded under plan Deviations.
- **Open:** `0 open`. Blockers: none. Majors: none. Minors and Nits: none open (F8 fixed r3).
- **Binding ruling:** §6 Verdict and the gate checklist below are the only binding location. There is no other round to point to.
- **On conflict:** the numbered body below wins for everything except `Status`. Log the mismatch as a finding at the next `/peer-review` and proceed. Do not stop on it.

## 1. Scope

- **Reviewed (r3):** `git diff HEAD~1` (`b16d4bf`): the later-table skip rule in `_parse_qa` (`artifacts.py:297-298`), the new test `test_later_notes_table_mentioning_an_ac_id_is_not_a_verification_table` (`tests/test_qa_multi_table.py:97-101`), and the developer's edits to this report. Context re-read: `_qa_id_column` (:322-334), `_col` (substring match), and the drift tests at :78-89.
- **Graph (aspark-graph CLI; no MCP tools were exposed to this agent):**
  - `staleness`: stale (`artifacts.py` and the test file changed). I ran `build` once (2 files re-parsed, 65 cached).
  - `impact --diff HEAD~1..HEAD --brief` has the same reach as in r2: `qa-multi-table`, `current-artifact-names` US-1/US-4 and `coverage-current-names` US-1 via `artifacts.py`. I used the full suite as the regression net.
  - The round-1 `story_trace` results still apply because no new files were added.
- **Mode:** live probes (`/tmp/rv2/probe.py`, 6 cases), the full suite, the new test run against `4633cdd` code (worktree + `PYTHONPATH`), and an old/new byte-identity `cmp`. I did not run the slow suite because no packaging, transport or install path changed.
- **Corpus:** I re-scanned 89 QA verification tables across the 34 Core `qa.md` files (`/tmp/rv/core`), this repo and `/opt/aspark/.spark`. Every first and later table uses an exact `AC` or `Spec ID` header, and none uses a loose header.
- **Not reviewed:** the CLAUDE.md/constitution.md G6 mentions. The caller says they are intentionally left to `/go-live`.
- **Anti-generosity standard applied** (`/opt/aspark/standards/anti-generosity.md`, read in full).

## 2. Plan Conformance

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 | ✅ | `_tables` + `_first_table = next(_tables(...), None)` (`artifacts.py:372-389`). Existing suite green with no edits. |
| T2 | ✅ r3 | The exact-header rule for later tables (`artifacts.py:297-298`) differs from plan §1, which skips only when `_qa_id_column` is `None`. The reviewer recorded this in plan Deviations in r3, as the caller instructed, and I accept it (F7). |
| T3 | ✅ | After F2, `latest_result == "fail"` is asserted exactly for a later-table AC. |
| T4 | ✅ | r3 re-derived this (condition (b): Must AC-2.1). I built the input tree held constant at `b16d4bf` with the `64c533c~1` code and with the HEAD code, both with `--full`. This repo gives `6f17f89e7ac0bad8…` for both and `current_names_repo` gives `07ee6b9ca8e821c2…` for both. `cmp` reports identical. |
| T5 | ✅ | The marker reads "Version: wird bei `/go-live` ergänzt" (`BACKLOG.md:240`). This deferral is accepted (F4). |

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Major | `src/aspark_graph/artifacts.py:289-296` (with `_qa_id_column` :317-329) | The notes-table test uses `_qa_id_column`, whose v0.7.0 prefix rule accepts any header starting with `ac`. A later notes table with a header such as `Action`, `Actual`, `Acceptance note` or `Account` therefore counts as an id column. With no Result column, the whole build fails with `TemplateDriftError … (table 2) missing a 'Result' column (found ['action','item'])` (probe output). In v0.7.3 the same file builds. This breaks the "notes table is skipped" clause of AC-2.2 and turns a working repo into a failed build (0 of 34 Core qa.md hit it today). Fix: for later tables, accept only the exact `ac`/`spec id` headers, or skip a later table in which no id cell matches `AC-\d+\.\d+`. Add a regression test using an `Action` header. r2: the reproducer (`Item \| Action`, no AC ids) now builds. `test_notes_table_with_loose_ac_prefix_header_is_skipped` fails on `58522cc` and passes now. The residual is tracked as F6. | fixed r2 |
| F2 | Minor | `tests/test_qa_multi_table.py:54-60` (orig.) | Under the pre-change parser, both gate_health assertions still passed: AC-1.2 sat in table 1, and AC-2.1 is unverified either way. Only `"fail" in str(trace)` told old and new apart. The T3 DoD (a later-table AC counted as passed) was never asserted. Fixed by the reviewer: AC-1.2 (pass) and AC-2.1 (fail) now sit in a later table, and `latest_result == "fail"` is asserted exactly. Verified failing under old code. | fixed r1 |
| F3 | Minor | `tests/test_qa_multi_table.py` | The plan's R2 mitigation says "a test pins the behaviour". Only `_first_table`/`_tables` were pinned, not `_parse_qa` reading a valid table after a malformed run. Fixed by the reviewer: `test_malformed_first_run_then_valid_table_produces_checks` (AC-2.1 at order 0). Verified failing under old code. | fixed r1 |
| F4 | Minor | `.spark/BACKLOG.md:240` | The T5 DoD says "done marker naming `qa-multi-table` and the version". r2: the marker now states that the version is added at `/go-live`. That is the first fix option, and it is accepted because the version is not fixed before release. `/go-live` must replace the text with the shipped version. (Artifact wording, capped at Minor.) | fixed r2 |
| F5 | Nit | `src/aspark_graph/artifacts.py:284,295` | `position` counts only well-formed tables. Malformed runs are dropped before `enumerate`, but notes tables are counted. So "(table N)" in the drift message can disagree with the document. r2: the code now enumerates the raw `_tables` output with an `is_first` flag (:286-290). Probe: valid, then malformed, then broken input reports "(table 3)". There is no test pinning the message (Nit, acceptable). | fixed r2 |
| F6 | Major | `src/aspark_graph/artifacts.py:297-303` | The F1 fix is content-based. A later table whose loose `ac…` column cites an AC id is still read as a verification table. Probe 1: `\| # \| Action \| Owner \|` / `\| 1 \| Re-verify AC-1.2 live \| QA \|` gives `TemplateDriftError … (table 2) missing a 'Result' column (found ['#','action','owner'])`, so a repo that builds on v0.7.3 now fails. Probe 2: `\| Action \| Result \|` / `\| Re-ran AC-1.2 \| ✅ done \|` adds a `pass` QACheck at order 2, which then becomes AC-1.2's `latest_result`. A follow-up list becomes a verdict. Either way AC-2.2 ("a later table without an AC id column … is skipped") fails for a notes table. Fix: for tables after the first, accept only the exact `ac`/`spec id` headers and skip anything else. Add both probes as tests. r3 (condition (a)): `artifacts.py:297-298` now skips a later table unless one header cell equals `id_col` exactly. Both probes produce only `AC-1.1@0, AC-1.2@1`, with no drift and no extra check. The new test at `tests/test_qa_multi_table.py:97` fails on `4633cdd` (`TemplateDriftError` at :303) and passes now. | fixed r3 |
| F7 | Minor | `src/aspark_graph/artifacts.py:297-300`, `plan.md` §1/Deviations | The r2 content-based skip also applied to exact-header later tables: `\| Spec ID \| Notes \|` / `\| NFR-1 \| x \|` was skipped silently, where plan §1 and AC-2.2 say drift. This was an undocumented plan deviation. r3: that probe now raises `(table 2) missing a 'Result' column`, matching plan §1. The remaining deviation (later tables ignore the `ac…` prefix rule) is recorded in plan Deviations, with its known limit (a later `AC ID` verification table is skipped; 0 of 89 corpus tables). | fixed r3 |
| F8 | Minor | `.spark/qa-multi-table/review.md` Handoff (as committed in `b16d4bf`) | The fix commit rewrote the Handoff to "F6 fixed … `0 open`", while §6 and the gate in the same file still said F6 was open. A reader of the Handoff alone would have read the r2 gate as clear. Per the conflict rule the body wins, so I proceeded on the body. Fix: `/increment` leaves the Handoff to the Reviewer and only sets `Status` cells to `fixed`. This round I rewrote the Handoff to the r3 state. (Artifact wording, capped at Minor.) | fixed r3 |

## 4. Requirements Traceability

| Spec ID | Implemented at | Verdict |
|---|---|---|
| AC-1.1 | `artifacts.py:284-321`. Tests `test_every_table_row_…`; Core corpus: graph-gates 5→30, lean-artifacts 8→15, project-kickoff 6→26, tracker-handoff 5→21 checks | ✅ met |
| AC-1.2 | `queries.gate_health`/`story_trace` unchanged. Hands-on scratch per-story qa.md (4 tables incl. a `### Notes` table): new `unverified_acs: []`, US-2 AC-2.1 `latest_result: pass`; old code listed AC-1.2 and AC-2.1 as unverified | ✅ met |
| AC-1.3 | `artifacts.py:304,320` (`start=offset`, offset += rows). Test `test_ac_in_two_tables_…` | ✅ met |
| AC-2.1 | `artifacts.py:374` + offset 0 for the first table. T4 old/new `cmp` re-run in r3 is identical (§2). The other 22 non-erroring Core qa.md files parse identically under old and new | ✅ met |
| AC-2.2 | `artifacts.py:292-301`. First-table drift is tested at :86. A later table with no id or a loose id header is skipped (:72, :91, :97, probes 1-2). A later exact-id table without Result raises drift (:78, probes 4-6). | ✅ met r3 |
| AC-3.1 | `.spark/BACKLOG.md:240`. README never stated the limit (grep) | ✅ met (version per F4) |

## 5. What Was Checked

- [x] Correctness: every Must AC traces to code and a test. AC-2.2 was re-probed live in r3.
- [x] Non-functional: the first-table path is untouched (`not is_first` short-circuits). The r3 old/new `cmp` is identical, and the double-build test is green.
- [x] Error handling: drift still raises loudly, naming the file and the table position. No swallowed errors.
- [x] Security: no new input surface.
- [x] Tests: 414 pass. The new F6 test fails on pre-fix code.
- [x] Readability: the skip comment at :298 now matches the rule.

## 6. Verdict

Round 3 passes.

Evidence:
- **F6 fixed.** Later tables are read only when a header cell is exactly `AC` or `Spec ID`. Both F6 reproducers now build without drift and without a spurious check, and the new regression test fails on `4633cdd`.
- **F7 fixed.** The `Spec ID | Notes` case drifts again, as plan §1 requires. The narrower header rule for later tables is recorded under plan Deviations.
- **Accepted known limit.** A later verification table headed with a loose id such as `AC ID` is skipped silently. This is an undercount, never a wrong verdict, and none of the 89 corpus tables uses such a header.
- **AC-2.1 re-derived.** Byte-identity against the pre-change code holds on this repo and on `current_names_repo`.
- **Suite.** Green: 414 passed, 4 slow deselected.
- **F8.** I logged the Handoff/body mismatch introduced by the fix commit and fixed it by rewriting this report.

No finding is open.

---

## ✅ REVIEW GATE

- [x] No open Blocker findings
- [x] No open Major findings (or explicitly waived by the user, with reason recorded here). F1 and F6 are fixed and verified.
- [x] Every Must AC traces to implementing code; no constitution non-negotiable violated (§4: all ✅)
- [x] All plan deviations documented and accepted (T4 re-derived as none; T2 header rule recorded in r3)
- [x] Test suite runs green (414 passed, 4 slow deselected)
- [x] Line budget respected: Ist ~90 / Soll ~150 (excluding HTML comments)
- [x] Status set to `passed`
