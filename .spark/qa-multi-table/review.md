# Review Report: qa-multi-table

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | `git diff dd4b994 HEAD` (HEAD `ebcc772`), `.spark/qa-multi-table/plan.md` (revised, 8 tasks) |
| **Status** | `passed` |
| **Round** | 2 |
| **Date** | 2026-11-11 |

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
- **Verdict:** Passed. Every Must AC and both NFRs were re-derived live at `ebcc772`. F2 and F3 are confirmed fixed. Three Minors are open, and F5 (T7 marked `done` without its record) must be closed before `/go-live`.
- **Open:** `3 open`. Blockers: none; Majors: none (Minors F4, F5, F6: see §3)
- **Binding ruling:** §6 Verdict and the gate checklist below — the only binding location; there is no other round to point to
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Scope

Reviewed `git diff dd4b994 HEAD` (4 commits), covering these files:
- `src/aspark_graph/artifacts.py` (`_parse_qa`, `_all_tables`, and the unchanged `_first_table`/`_section`/`_split_row`/`_col`/`_qa_id_column` they rely on, `:279-420`)
- `tests/test_qa_multi_table.py`
- the doc edits in `CLAUDE.md`, `.spark/constitution.md` and `.spark/BACKLOG.md`
- the revised `plan.md` and the trail's `spec.md`/`qa.md`

Round-2 focus: the F2/F3 fixes, T4, T7, the constitution amendment and the conformance of the revised task table.

**Mode:** live runs and tests at `ebcc772`, not a static read only. I ran the full suite, the old-vs-new byte comparison on one tree copy, the real-corpus probe and 4 mutants.

**Graph tools used** (`staleness`: fresh, 64 files, so no rebuild):
- `impact --diff dd4b994..HEAD`: reaches `qa-multi-table` US-1/2/3, `current-artifact-names` US-1/US-4 and `coverage-current-names` US-1 (all `declared`) through `artifacts.py`. The 7 `.md` files are `unknown_files` because Markdown is not indexed, so I scoped the docs by hand.
- `story_trace` US-1/US-2/US-3: links T1/T2/T6, T3/T4 and T5/T7. T6/T7 have no code links because they declare no `files:`, which is expected.

Because of these results, I read the shared helpers at `artifacts.py:314-420` and re-ran the other features' suites inside the full run. Graph QA-leg fields were not read (tool rule).

Not reviewed: `queries.py`/`cli.py`/`server.py`, because the diff leaves them unchanged. I did not run the slow tests: nothing they cover (sdist, transport, bench, fresh install) is touched, and they run at release.

**Anti-generosity standard applied** (`/opt/aspark/standards/anti-generosity.md`).

## 2. Plan Conformance

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 | ✅ | `_all_tables` (`artifacts.py:362-375`) feeds each contiguous pipe-run to the unchanged `_first_table`. The `_parse_qa` loop is at `:284-311`. |
| T2 | ✅ | `test_every_subtable_is_read` passes. Mutant M3 (keep only the first table) fails it. The outside-section test asserts AC-1.2 is unverified (`test_qa_multi_table.py:56-66`). |
| T3 | ✅ | Per-table drift checks are at `artifacts.py:289-293`, and both drift tests exist. That they fail on pre-change code is cited from round 1 (r1 §2), not re-derived. |
| T4 | ✅ | `test_qa_multi_table.py:46,53` assert `exc.value.file.endswith(".spark/demo/qa.md")`, plus `match=` on the column. Mutant M2 (drift names `path.parent`) fails both tests. |
| T5 | ✅ | `test_running_index_keeps_same_ac_in_two_tables_distinct` (`:76-87`). Mutant M1 (per-table reset) fails it. A separate index invariant is still unguarded (F4). |
| T6 | ✅ | Re-derived, see §4. The numbers match the DoD exactly. |
| T7 | ❌ | I re-derived the proof myself and it holds (§4). However, the DoD's record is missing: `qa.md:31` cites only the round-1 proof, made at `2706861`, and `ebcc772` changed only `qa.md`'s Status line. The task is marked `done` without its DoD being met (F5). |
| T8 | ✅ | A grep of `*.md` for the old-limit phrases hits only historical trails and this trail's own spec/plan. |

The revised table splits the old T1/T2 into one story per row (R6), which fixes US-2/US-3 having no task links. No commit message in the range cites a `T`/`US` id, so the renumbering cannot shift inferred edges.

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Minor | `tests/test_qa_multi_table.py:53-60` | **Problem:** the AC-1.3 test asserted that AC-1.2 stays unverified, but its outside table (`\| Foo \| Bar \|`) contained no AC-1.2, so that assertion could never fail. The test only failed through an incidental drift error. **Why it matters:** if drift checking were ever relaxed, the guard would pass silently. **Fix applied:** the outside table is now `\| Spec ID \| Result \|` with `AC-1.2 ✅ pass`. | fixed r1 |
| F2 | Minor | `tests/test_qa_multi_table.py:76-87`, `artifacts.py:286,295` | **Problem:** no test pinned NFR-2's running index across tables. A per-table `index = 0` mutant passed all tests, and the same AC at the same row of two tables collides on `qa:<f>:<ac>#<i>`. **Why it matters:** the guarantee was unprotected. **Fix:** a test with the same AC at row 0 of two tables. **Confirmed r2** (condition a): mutant M1 now fails it. | fixed r2 |
| F3 | Nit | `.spark/constitution.md:96`, `CLAUDE.md:239` | **Problem:** both docs stated a stale test count (319). **Why it matters:** doc drift. **Fix:** update the count. **Confirmed r2:** both now say 393, and `uv run pytest -q` reports `393 passed, 4 deselected`. | fixed r2 |
| F4 | Minor | `artifacts.py:295`, `tests/test_qa_multi_table.py:68-73` | **Problem:** nothing tests that the index advances on **every** data row, including non-AC rows (`NFR-1`), the way the old `enumerate` did. Mutant M4 moves the increment below the `if not m: continue`. It passes the full suite (393) and leaves this repo's 74 `QACheck` ids unchanged. `test_single_table_unchanged_checks` cannot see it because its only non-AC row is the last row. **Why it matters:** this is AC-3.1/NFR-2's byte-identity guarantee, and it is real. Under M4, Core's `campaign-notice-statuses/qa.md` gets different ids than under `dd4b994`. **Fix:** add a test whose table has a non-AC row before an AC row (e.g. `NFR-1` row 0, `AC-1.1` row 1) and assert `qa:demo:AC-1.1#1`. | open |
| F5 | Minor | `.spark/qa-multi-table/qa.md:21,31`, `plan.md:24,58` | **Problem:** T7 is `done`, and the plan Handoff says "all tasks done", but the DoD's record is absent. `qa.md` records neither sha256 nor the HEAD SHA, and still cites the round-1 proof at `2706861`, which predates the F2 fix and this trail's `qa.md`. **Why it matters:** a false `done` on a determinism task. `/go-live` re-verifies from artifacts, and this one points at a stale proof. It changes no Must-AC verdict, because §4 re-derives AC-3.1 at `ebcc772`. **Fix:** record in `qa.md` AC-3.1 the result `ebcc772`, `cmp` identical, sha256 `158d649d…20108f2` (both builds), with 393 tests green. Alternatively, amend T7's DoD to cite review.md §4. | open |
| F6 | Minor | `.spark/qa-multi-table/plan.md:10,96` | **Problem:** the header Status is `approved`, but the PLAN GATE box "Status set to `approved` by the user" is unchecked. The spec records the approval as an autonomous line. **Why it matters:** the gate and the status disagree, so a reader cannot tell who approved the revision. This is artifact wording, so the severity is capped. **Fix:** check the box with the approver named (autonomous line), or set Status back to match. | open |
| F7 | Minor | `.spark/qa-multi-table/review.md` (round-1 state) | **Problem:** in the round-1 report, the Handoff said "Open: none" and §3 showed F2/F3 as `fixed`. Meanwhile §6 still said "Two findings stay open" and the gate said "392 passed". Fix-mode had updated §3 and the Handoff but not §6. **Why it matters:** this is a stale binding verdict. **Fix:** overwritten in place this round. | fixed r2 |

## 4. Requirements Traceability

| Spec ID | Implemented at | Verdict |
|---|---|---|
| AC-1.1 | `artifacts.py:284-311`, `362-375` | ✅ met. `test_every_subtable_is_read`; real Core corpus: `graph-gates` 5→30, `lean-artifacts` 8→15, `project-kickoff` 6→26, `tracker-handoff` 5→21 checks (4 of 34 `qa.md` changed) |
| AC-1.2 | unchanged `queries.story_trace`/`gate_health` over the new nodes | ✅ met. Same test asserts `unverified_acs == []` and `latest_result` pass for AC-1.2 from the 2nd table |
| AC-1.3 | `_section` stops at the next `#`/`##` (`artifacts.py:355-358`); `_all_tables` only gets the section | ✅ met. `test_tables_outside_the_section_are_not_read` (strengthened, F1) |
| AC-2.1 | `artifacts.py:289-293`, per table | ✅ met. 2 drift tests now assert both the file (`exc.value.file`) and the column, and M2 fails them r2 |
| AC-3.1 | `artifacts.py:286,295` (index identical to old `enumerate`) | ✅ met. Live at `ebcc772`, below; test gap is F4 |
| AC-4.1 | `CLAUDE.md:41-42,163`, `constitution.md:99` | ✅ met. Grep over `*.md` (excluding historical trails and `.factory/tickets.md`) finds no statement of the old limit; README/SECURITY never mentioned it |
| NFR-1 | no new import/dep; no new I/O | ✅ met. AC-3.1 `cmp`; diff adds no dependency |
| NFR-2 | `artifacts.py:286,295` | ✅ met. M1 is now caught (F2 fixed); the non-AC-row case is F4 r2 |

**AC-3.1 evidence (re-derived; condition b, a Must AC, and a different HEAD than round 1).**
- Setup: a `git worktree` of `dd4b994` (its `artifacts.py` has no `_all_tables`) and one `cp -a` copy of this working tree at `ebcc772`.
- Builds: `uv run --project <old-wt> aspark-graph build <copy> --full`, then the same command with `--project /workspace/repo`. Each build used the full rescan (692 code entities, 565 artifact entities, 187 inferred links).
- Result: `cmp` IDENTICAL, both sha256 `158d649da37159232ec8e2c08a2b12f738b4488e973eda95c5309a42820108f2`. The graph has 1257 nodes, including 74 `QACheck` (6 from this trail's single-table `qa.md`, `#0`–`#5`).

**Real-corpus probe (T6; condition b).** I ran `_parse_qa` on all 34 Core `qa.md` files in `/opt/aspark/.spark`, under the old and the new code:
- 30 outputs identical, including 9 `TemplateDriftError`s with the same message under both codes.
- 4 outputs are strict supersets: the 4 files listed under AC-1.1.
- 0 new errors.

**Mutants** (applied in the copy with `PYTHONPATH=<copy>/src`; the baseline is 6/6 passing):

| Mutant | Change | Result |
|---|---|---|
| M1 | per-table index reset | killed |
| M2 | drift error names the wrong file | killed |
| M3 | only the first table is read | killed |
| M4 | index advances only on AC rows | **survives** (F4) |

## 5. What Was Checked

- [x] Correctness: the logic does what the ACs demand. Live: suite, `cmp` at `ebcc772`, corpus probe, mutants.
- [x] Non-functional: NFR-1 and NFR-2 hold in code. Determinism is proven against the `dd4b994` code, not by a double-build. The guarantee left without a test is F4.
- [x] Error handling: drift is raised per table through the existing `TemplateDriftError` seam. Nothing is swallowed, and a pipe chunk without a separator row is skipped (C3).
- [x] Security: no new input path, file access or subprocess. Markdown is parsed into data only.
- [x] Tests: 393 pass. M1–M3 are killed; the M4 gap is recorded as F4.
- [x] Readability: `_all_tables` is 13 lines and reuses `_first_table`; the running-index line is commented.

## 6. Verdict

**Passed: no open Blocker or Major.**

Every Must AC (AC-1.1, 1.2, 1.3, 2.1, 3.1), the Should AC-4.1 and both NFRs are met. Each was decided by a live observable at `ebcc772`. The strongest evidence: the same tree builds a byte-identical `graph.json` under `dd4b994` and under HEAD. The Core corpus gains checks only in the 4 split-table reports, with no new drift errors.

The round-1 fixes hold. F2's test kills the per-table-reset mutant, F3's counts match the 393-test run, and T4's file assertions kill a wrong-file mutant.

Three Minors stay open:
- **F4:** no test pins that non-AC rows advance the index. A mutant breaking that passes the suite, and it would change ids in a real Core report.
- **F5:** T7 is marked `done`, but `qa.md` never received the sha256/HEAD record its DoD requires and still cites a pre-fix proof.
- **F6:** the plan gate's approval box contradicts its `approved` status.

F5 is a documented deviation that has not been accepted, so the gate's deviation box stays open. Close F5 before `/go-live`, which must not resume on the stale `qa.md` proof; recording the numbers above is enough. F4 should be fixed in the same pass.

`qa.md` is currently `in-review`. The release notes must name R1 (a later verification table with a deviating header now fails the build) as a behaviour change.

---

## ✅ REVIEW GATE

*All boxes checked → `/demo-day` may start. Any box open → back to `/increment`. On
re-review, edit this same checklist in place — never duplicate it as a second gate.*

- [x] No open Blocker findings
- [x] No open Major findings (or explicitly waived by the user, with reason recorded here)
- [x] Every Must AC traces to implementing code; no constitution non-negotiable violated
- [ ] All plan deviations documented and accepted. T7 is documented (F5) but neither closed nor accepted by the user.
- [x] Test suite runs green (393 passed, 4 deselected, `ebcc772`)
- [x] Line budget respected: Ist ~105 / Soll ~150 (excluding HTML comments)
- [x] Status set to `passed`
