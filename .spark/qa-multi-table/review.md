# Review Report: qa-multi-table

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | The diff of `/increment` (`6681ded~1..HEAD`), `.spark/qa-multi-table/plan.md` |
| **Status** | `passed` |
| **Round** | 1 |
| **Date** | 2026-11-11 |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Verdict:** Multi-table QA parsing is correct and byte-stable. One Major (`_first_table` semantics silently changed for review/plan parsing) was fixed by the reviewer and re-verified.
- **Open:** `none` — Blockers: none; Majors: none (Minors/Nits: see §3, F3 open)
- **Binding ruling:** §6 Verdict and the gate checklist below — the only binding location; there is no other round to point to
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Scope

- **Reviewed:** `git diff 6681ded~1..HEAD`, i.e. `src/aspark_graph/artifacts.py` (`_parse_qa`, `_first_table`, new `_all_tables`), `tests/test_current_names.py` (3 G6 tests), `CLAUDE.md`, `.spark/constitution.md`, `.spark/BACKLOG.md` (G6), plus the spec/plan trail. Callers of `_first_table` (`_parse_plan` :206, `_parse_review` :247) were read in context.
- **Graph:** the `aspark-graph` runner exists but no `.aspark-graph/graph.json` was built. As the caller instructed, scoping was done manually with grep/Read; no tool result was used.
- **Standard applied:** `CLAUDE.md` non-negotiables, `.spark/constitution.md`. No lens or tool file was passed. The anti-generosity standard was not passed and was not applied.
- **Not reviewed:** `queries.py`/`cli.py`/`server.py`. They are untouched, as the diff stat confirms.
- **Reviewer edits (uncommitted, part of the diff now):** `src/aspark_graph/artifacts.py` (F1), `tests/test_current_names.py` (+2 tests, F1/F2).

## 2. Plan Conformance

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 | ⚠️ → ✅ | Running index and per-table drift as planned. However, "`_first_table` returns its first element" was implemented as "first *valid* table", which changed review/plan parsing (F1). Fixed by the reviewer. |
| T2 | ⚠️ → ✅ | The three tests pass. The DoD's "later-table AC verified per its result" was only shown for a `fail` row, which old code also reports (F2). The reviewer added the pass case. |
| T3 | ✅ | CLAUDE.md, constitution and BACKLOG G6 updated. |
| T4 | ⚠️ → ✅ | The increment record covers only this repo, not `sample_repo`, the Core-style fixture or the multi-table double build that the DoD names (F4). The reviewer re-derived all of them (§5). |
| — | ⚠️ | Process deviation, already recorded in the plan: the code (6681ded) predates the spec/plan trail. Accepted as documented. No further action. |

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Major | `src/aspark_graph/artifacts.py:363` | `_first_table` became `_all_tables(...)[0]`, so a non-table first pipe block (a single `\| note \|` line, or a block without a separator) no longer yields `None`. A *later* table gets promoted instead. Probe: old→`None`, new→the second table, for both a review findings block and a plan task block. This silently changes `_parse_review` (0 findings → N) and `_parse_plan` (drift → accepted). It contradicts plan §1 / rejected alt. (3) ("must not change review/plan parsing") and spec §6. Reviewer fix: split into `_pipe_groups` + `_as_table`. `_first_table` considers only the first pipe block (exact old semantics); `_all_tables` still skips non-tables (C3). Guarded by `test_g6_first_table_never_promotes_a_later_block`. Probe now identical to `6681ded~1`. | fixed r1 |
| F2 | Minor | `tests/test_current_names.py:352` | `gate_health` assertion: the later-table row is `❌ fail`, so "AC-1.2 unverified" also holds under the old code. AC-1.1's "counted as verified" path and C1 id continuity were not asserted. Reviewer added `test_g6_later_table_pass_counts_as_verified_and_ids_run_on` (pass in table 2 → verified; `order` 0/1). It fails under old code. | fixed r1 |
| F3 | Minor | `src/aspark_graph/artifacts.py:291-293` | With several tables, the drift message names the file and column but not *which* table. A long split `qa.md` makes the bad sub-table hard to find (only the `found [...]` header set hints). Suggested fix: include the table ordinal or preceding `###` heading in the message. Needs the section's heading positions, so it is a design choice for the developer. | open |
| F4 | Minor | `.spark/qa-multi-table/plan.md:66` | Artifact wording/evidence: T4's increment record covers one of the four inputs its DoD names. Re-derived by the reviewer (§5), so no verdict depends on it. | fixed r1 |

## 4. Requirements Traceability

| Spec ID | Implemented at | Verdict |
|---|---|---|
| AC-1.1 | `artifacts.py:284-312` (`_all_tables` loop, running `index`) | ✅ met. Multi-table fixture yields `qa:demo:AC-1.1#0` and `#1`; old code yields `#0` only. Real Core: `graph-gates` 5→30, `lean-artifacts` 8→15, `project-kickoff` 6→26, `tracker-handoff` 5→21 checks. |
| AC-1.2 | same; index counts every row as before | ✅ met. Re-derived under condition (b). Old (`6681ded~1` worktree) vs new build, `--full`, `.git`-marked copies: this repo 607251 B, `sample_repo` 7169 B, `current_names_repo` 6038 B, all `cmp`-identical. Re-run after the F1 fix: identical. |
| AC-1.3 | `_section` (unchanged) bounds the block at the next `#`/`##` | ✅ met. `## 3. Other` table contributes no check, and its non-QA header would raise drift if read, so the test discriminates. |
| AC-2.1 | `artifacts.py:290-291` | ✅ met. Raised per table, before any row of that table. Test asserts the message. |
| AC-2.2 | `artifacts.py:292-293` | ✅ met. Test asserts the file and `'Result'`. |
| AC-3.1 | `CLAUDE.md:41`, constitution §9, BACKLOG G6 | ✅ met. No doc states the limit as current. |
| NFR-1 | as AC-1.2 | ✅ met. Multi-table fixture double build is byte-identical, before and after the F1 fix. |
| NFR-2 | diff touches only `artifacts.py` in `src/` | ✅ met. Adapters and `queries.py` untouched; parity unaffected. |

## 5. What Was Checked

- [x] Correctness: index continuity (ids `#0`, `#1` across tables), drift on any bad table, `_first_table` semantics (F1)
- [x] Non-functional: determinism proven against pre-change code (worktree round-trip), not only a double build (CLAUDE.md non-negotiable)
- [x] Error handling: drift is raised, never skipped; it uses the existing `TemplateDriftError` → adapter seam, no new plumbing
- [x] Security: parser only; no new input surface, path, or subprocess
- [x] Tests: `uv run --extra dev pytest -q` → 392 passed (390 + 2 reviewer tests); `-m slow` → 4 passed, before and after the fix
- [x] Readability: helpers small and documented
- [x] Real-file sweep (CLAUDE.md "read a wide set of real files"): all 34 `qa.md` under `/opt/aspark/.spark/` (aSPARK Core copy, no git metadata, so no SHA) were parsed with old and new code. 30 were unchanged, the 4 G6 files gained checks, and 0 hit drift, so the new "every table must be a QA table" rule breaks no real Core report.

## 6. Verdict

The feature does what the spec asks. Every table of the QA verification section is now read, ids run on across tables, a single-table report builds byte-identical graphs under old and new code (re-derived on three inputs), and a malformed sub-table raises named drift. The real Core corpus confirms exactly the four G6 files gain checks and none newly fail. The increment did ship one real defect (F1). Implementing `_first_table` as "first valid table" silently changed review and plan parsing for an edge input, and that was the one thing the plan's architecture decision forbade. I fixed it directly because the correct answer was unambiguous (restore the exact old semantics) and added a guard test. The F2 test gap is fixed the same way. Both reviewer edits are uncommitted and are part of the diff now, so they need to be committed with the trail. F3 (drift message doesn't name the sub-table) stays open as a Minor for the developer. With no open Blocker or Major and the full and slow suites green, the review passes.

---

## ✅ REVIEW GATE

*All boxes checked → `/demo-day` may start. Any box open → back to `/increment`. On
re-review, edit this same checklist in place — never duplicate it as a second gate.*

- [x] No open Blocker findings
- [x] No open Major findings (F1 fixed by the reviewer and re-verified, r1)
- [x] Every Must AC traces to implementing code; no constitution non-negotiable violated
- [x] All plan deviations documented and accepted (T1/T2/T4 resolved via F1/F2/F4; trail-after-code slip recorded in plan)
- [x] Test suite runs green (392 + 4 slow)
- [x] Line budget respected: Ist ~85 / Soll ~150 (excluding HTML comments)
- [x] Status set to `passed`
