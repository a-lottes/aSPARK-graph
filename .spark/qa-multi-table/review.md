# Review Report: qa-multi-table

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | The diff of `/increment` (`6681ded~1..HEAD`, HEAD `d2d3480`), `.spark/qa-multi-table/plan.md` (EM revision, T5–T7) |
| **Status** | `passed` |
| **Round** | 2 |
| **Date** | 2026-11-11 |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Verdict:** Passed. T5 (the sub-table locator) and T6 (the C3 edge pin) are correct, byte identity against `6681ded~1` holds on three inputs, and F3 is fixed. The reviewer closed the T5 test-DoD gap (F5) and the stale plan Handoff (F6). Four Minors stay open (F7–F10).
- **Open:** `4 open`. Blockers: none. Majors: none. (Minors/Nits: see §3. F7, F8, F9 and F10 are open.)
- **Binding ruling:** §6 Verdict and the gate checklist below — the only binding location; there is no other round to point to
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Scope

- **Reviewed:** `git diff 6681ded~1..HEAD`, with the focus on `d2d3480` (T5–T7). Files read: `src/aspark_graph/artifacts.py:279-316` (`_parse_qa`) and `:367-440` (`_first_table`, `_all_tables`, `_group_headings`, `_pipe_groups`, `_as_table`), `tests/test_current_names.py:217-229` and `:340-433`, the docs diff (CLAUDE.md, constitution §9, BACKLOG G6), and spec (incl. C4), plan, and `qa.md`.
- **Graph (tool file `/opt/aspark/tools/aspark-graph.md`, CLI surface):** `staleness` returned `stale: true` (artifacts.py and the test file had changed). I rebuilt once and it then returned `stale: false`. `impact --diff 6681ded~1..HEAD` returned `artifacts.py` (25 entities) and the test file (38 entities). It also reached `current-artifact-names` US-1/US-4 and `coverage-current-names` US-1, so I confirmed their tests are in the green run and covered them with the byte-identity sweep. The 7 Markdown paths came back in `unknown_files` (not indexed, which is expected). `story_trace` gave US-1 → T1/T2/T4/T6/T7 and US-2 → T5 (→ `artifacts.py`, test file), and that is what scoped my reading above. Per the tool file, I did not call `gate_health`.
- **Mode:** live. I ran pytest, CLI builds, the old-code worktree round-trip, `python -I` probes against both code versions, and mutation checks. MCP was not exercised over stdio; NFR-2 parity rests on the untouched adapters plus the in-process parity tests. No AC needs more than this.
- **Standards applied:** CLAUDE.md non-negotiables and `.spark/constitution.md`. **The anti-generosity standard (`/opt/aspark/standards/anti-generosity.md`) was applied** to every verdict below. Active lenses: none.
- **Reviewer edits this round (uncommitted):** `tests/test_current_names.py` (F5: two assertions) and `.spark/qa-multi-table/plan.md:16` (F6: Handoff).

## 2. Plan Conformance

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 | ✅ | `_first_table` = first group only (`artifacts.py:367-373`); the guard test is green; `d2d3480` left `_pipe_groups`/`_as_table` untouched. |
| T2 | ✅ | All `test_g6_*` tests are present and green. The discriminating test was already re-derived in r1 (F2), and `d2d3480` does not touch it. |
| T3 | ✅ | A grep of the three docs finds no current-limit wording. BACKLOG G6 carries a "umgesetzt" status line. |
| T4 | ✅ | Re-derived this round (see T7). |
| T5 | ✅ after reviewer fix (❌ as delivered) | The locator works (`artifacts.py:290-297`). However, the DoD's `==` assert in `test_qa_table_with_neither_ac_nor_spec_id_is_drift` and the "no `heading` key on `_first_table`" check were not delivered (F5). The reviewer added both. |
| T6 | ✅ | `test_g6_non_table_pipe_block_before_the_qa_table_is_skipped` (`:425`) asserts `order` 0, and its docstring records the v0.7.3 difference. |
| T7 | ✅ | Re-derived under condition (b): see §4 AC-1.2/NFR-1. `git diff --stat 6681ded~1..HEAD -- src` lists only `artifacts.py`. The slow suite is flaky for an unrelated reason (F8). |

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Major | `src/aspark_graph/artifacts.py:363` | `_first_table` became `_all_tables(...)[0]`, so a non-table first pipe block (a single `\| note \|` line, or a block without a separator) no longer yields `None`. A *later* table gets promoted instead. Probe: old→`None`, new→the second table, for both a review findings block and a plan task block. This silently changes `_parse_review` (0 findings → N) and `_parse_plan` (drift → accepted). It contradicts plan §1 / rejected alt. (3) ("must not change review/plan parsing") and spec §6. Reviewer fix: split into `_pipe_groups` + `_as_table`. `_first_table` considers only the first pipe block (exact old semantics); `_all_tables` still skips non-tables (C3). Guarded by `test_g6_first_table_never_promotes_a_later_block`. Probe now identical to `6681ded~1`. | fixed r1 |
| F2 | Minor | `tests/test_current_names.py:352` | `gate_health` assertion: the later-table row is `❌ fail`, so "AC-1.2 unverified" also holds under the old code. AC-1.1's "counted as verified" path and C1 id continuity were not asserted. Reviewer added `test_g6_later_table_pass_counts_as_verified_and_ids_run_on` (pass in table 2 → verified; `order` 0/1). It fails under old code. | fixed r1 |
| F3 | Minor | `src/aspark_graph/artifacts.py:291-293` | With several tables, the drift message names the file and column but not *which* table. A long split `qa.md` makes the bad sub-table hard to find (only the `found [...]` header set hints). Suggested fix: include the table ordinal or preceding `###` heading in the message. Needs the section's heading positions, so it is a design choice for the developer. | fixed r2 |
| F4 | Minor | `.spark/qa-multi-table/plan.md:66` | Artifact wording/evidence: T4's increment record covers one of the four inputs its DoD names. Re-derived by the reviewer (§5), so no verdict depends on it. | fixed r1 |
| F5 | Minor | `tests/test_current_names.py:228`, `:402` | T5's DoD asks for `==` on the unchanged single-table string and for `_first_table` to carry no `heading` key. The delivered test (`:406`) checks only `startswith`/`endswith`, and nothing checks the key. Reviewer added an `==` assert and `"heading" not in _first_table(...)`. Mutation check: locator on 1 table → 3 tests fail; `heading` added to `_first_table` → the guard fails. | fixed r2 |
| F6 | Minor | `.spark/qa-multi-table/plan.md:16` | Artifact: the Handoff said `3 tasks not done (T5, T6, T7)` while §3 marks all of them `done`. Under the plan's conflict rule the body wins, so I proceeded on it. Reviewer set the Handoff to `none`. | fixed r2 |
| F7 | Minor | `.spark/qa-multi-table/qa.md:8`, `:62` | Artifact: the header `Status` is `in-review`, yet the gate box "Status set to `passed`" is checked. The report also predates T5: B1 is still `open`, and the AC-2.2 observed message (`:33`) has no locator. `/demo-day` should re-run AC-2.2 on the CLI (the reviewer observed `... (table 2 of 2, under '### US-2')`, rc 1) and settle `Status`. QA owns that report, so I did not edit it. | open |
| F8 | Minor | `tests/test_incremental_bench.py:53` | Pre-existing, not caused by this diff. In this container the NFR-1 bench is flaky at its 50% threshold: new code 26.9%/47.8%/49.7% (fail) vs 50.3–51.7% (pass); old code (`6681ded~1`) 50.8–56.5%. The fixture has no `.spark/`, so `_parse_qa` is unreachable from it. A red slow run can therefore mask or fake a regression. Suggested fix: BACKLOG item to widen the sample (median of 5+) or report the margin instead of a hard fail. | open |
| F9 | Minor | `src/aspark_graph/artifacts.py:378`, `:390-406` | `_group_headings` re-implements `_pipe_groups`'s grouping predicate, and `_all_tables` `zip`s the two lists. If the predicates ever diverge, `zip` truncates silently and later tables are dropped: the G6 under-count again, with no error. Today they agree (34-file Core sweep: 0 length mismatches). Suggested fix: have one walk yield `(group, heading)`, or at least `zip(..., strict=True)` (Python ≥3.11 is required). This is a design choice, so I left it for the developer. | open |
| F10 | Minor | `src/aspark_graph/artifacts.py:412-421` | Pre-existing edge, not a regression. A QA row missing its trailing `\|` ends the group, and the rows after it form a header-less group that C3 skips, so those ACs are silently uncounted (old code dropped them too). If that remainder contains an all-`-`/empty row, `_as_table` takes it as a separator, and drift fires with a confusing header (`found ['ac-1.3', …]`). Probe output is in §5. Suggested fix: inside the QA section, raise drift for any `\|`-prefixed line that does not end in `\|`. That widens C3, so it is a PO call. | open |

## 4. Requirements Traceability

| Spec ID | Implemented at | Verdict |
|---|---|---|
| AC-1.1 | `artifacts.py:284-316` (`_all_tables` loop, running `index`) | ✅ met. Multi-table fixture yields `qa:demo:AC-1.1#0` and `#1`; old code yields `#0` only. Real Core: `graph-gates` 5→30, `lean-artifacts` 8→15, `project-kickoff` 6→26, `tracker-handoff` 5→21 checks. |
| AC-1.2 | same; `index` increments before the AC match (`:300-301`) | ✅ met r2 (scope narrowed by C4). Re-derived under condition (b): a `6681ded~1` worktree vs `d2d3480`, `--full`, run through `PYTHONPATH` with the import path asserted. Inputs: this repo as a **real clone with history**, 650554 B; `sample_repo`, 7169 B; `current_names_repo`, 6038 B (both `.git`-marked). All `cmp`-identical. |
| AC-1.3 | `_section` (unchanged) bounds the block at the next `#`/`##` | ✅ met. `## 3. Other` table contributes no check, and its non-QA header would raise drift if read, so the test discriminates. |
| AC-2.1 | `artifacts.py:294-295` | ✅ met r2. Names file, column and now `(table 2 of 2, under '### US-2')` (`test_g6_subtable_without_ac_column_is_drift`). |
| AC-2.2 | `artifacts.py:296-297` | ✅ met r2. Live CLI: `template drift in …/qa.md: QA table missing a 'Result' column (found ['outcome', 'spec id', 'steps']) (table 2 of 2, under '### US-2') (supported: aspark/0.1.0)`, rc 1, no traceback. |
| AC-3.1 | `CLAUDE.md:41`, constitution §9, BACKLOG G6 | ✅ met. No doc states the limit as current. |
| NFR-1 | as AC-1.2 | ✅ met r2. Multi-table fixture (two `###` tables) built twice under `--full`: 5722 B, `cmp`-identical; it yields `qa:demo:AC-1.1#0` and `qa:demo:AC-1.2#1`. |
| NFR-2 | diff touches only `artifacts.py` in `src/` | ✅ met. Adapters and `queries.py` untouched; parity unaffected. |

## 5. What Was Checked

- [x] Correctness: locator text for 2+ tables, with and without a heading; the heading carries over to a later heading-less table (probe `carry` → both `### US-1`, matching "nearest preceding"); the single-table message is byte-equal to pre-change (F5).
- [x] Non-functional: old-code round-trip on three inputs plus the multi-table double build (§4). Core sweep: all 34 `/opt/aspark/.spark/**/qa.md` (no git metadata, no SHA) under old and new code. 30 unchanged, the 4 G6 files gained checks, 0 drift, and 0 `_pipe_groups`/`_group_headings` length mismatches.
- [x] Error handling: drift rides the existing `TemplateDriftError` → CLI seam. The MCP `build_graph` gap is pre-existing and is tracked as BACKLOG G7.
- [x] Security: parser only. The heading text is echoed into a local error message; there is no new input surface.
- [x] Tests: `uv run --extra dev pytest -q` → 395 passed (before and after my edits). `-m slow` → 1 run with 1 failure while my builds ran in parallel, then 3 isolated runs: 1 failure, 2 with 4/4 passed (F8). Mutation checks: see F5.
- [x] Readability: helpers small and documented; duplicated predicate noted (F9).
- [x] Edge probes (`python -I`, old vs new): `split` → table 2 header `['AC-1.3','c','✅']` (F10); a heading inside a ``` fence is taken as the locator (cosmetic; it only affects the message text).

## 6. Verdict

The round-2 increment does what the revised plan asks. When a section holds more than one table, a bad sub-table's drift message now ends with `(table n of m, under '### …')`, and with no heading it ends with only the ordinal. A single-table message is unchanged character for character, which I now pin with an exact `==`. The C3 edge (a non-table pipe block before the QA table) is pinned by a test that records its difference from v0.7.3, in line with spec C4. I re-derived AC-1.2 myself against `6681ded~1`: all three inputs are byte-identical, including a real-history clone of this repo, and the multi-table fixture double-builds identically. F3 is fixed. As delivered, T5 missed two of its own DoD assertions (F5); I added them and mutation-checked both. The plan Handoff was stale (F6), and I corrected it. Four Minors stay open for their owners: `qa.md` needs a `/demo-day` re-run after T5 and a consistent `Status` (F7); the NFR-1 benchmark is flaky at its threshold in this container on old and new code alike (F8, pre-existing, unreachable from this diff); `_group_headings` duplicates the grouping predicate behind an unchecked `zip` (F9); and a row missing its trailing pipe still silently drops the rows after it, which old code did too (F10). No Blocker or Major is open, the default suite is 395/395, and the slow suite's only failure is the pre-existing timing flake, so the review passes. My two edits are uncommitted and need to be committed with the trail.

---

## ✅ REVIEW GATE

*All boxes checked → `/demo-day` may start. Any box open → back to `/increment`. On
re-review, edit this same checklist in place — never duplicate it as a second gate.*

- [x] No open Blocker findings
- [x] No open Major findings (F1 fixed r1; nothing new above Minor in r2)
- [x] Every Must AC traces to implementing code; no constitution non-negotiable violated
- [x] All plan deviations documented and accepted (T5 gap closed via F5; trail-after-code slip recorded in plan §1)
- [x] Test suite runs green: 395/395 default. Slow: 4/4 in 2 of 3 isolated runs; the failing test is the pre-existing NFR-1 timing flake (F8), which this diff cannot reach.
- [x] Line budget respected: Ist ~100 / Soll ~150 (excluding HTML comments)
- [x] Status set to `passed`
