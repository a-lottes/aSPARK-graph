# Review Report: qa-multi-table

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | Commit `2706861` (`git diff HEAD~1 HEAD`), `.spark/qa-multi-table/plan.md` |
| **Status** | `passed` |
| **Round** | 1 |
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
- **Verdict:** Passed. All Must ACs and both NFRs met, each with a live observable; no Blocker or Major.
- **Open:** `none`. Blockers: none; Majors: none (F2, F3 fixed in fix-mode, see §3)
- **Binding ruling:** §6 Verdict and the gate checklist below — the only binding location; there is no other round to point to
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Scope

Reviewed: `src/aspark_graph/artifacts.py` (`_parse_qa`, new `_all_tables`, unchanged `_first_table`/`_section`/`_split_row` it relies on), `tests/test_qa_multi_table.py`, doc edits in `CLAUDE.md`, `.spark/constitution.md`, `.spark/BACKLOG.md`, and the untracked trail (`spec.md`, `plan.md`).

**Mode:** live runs and tests, not a static read only. Full suite run; old-vs-new byte comparison; real-corpus probe; mutation checks.

**Graph tools used** (the graph was stale on `artifacts.py`, so I ran `build_graph` first): `staleness`; `impact --diff HEAD~1..HEAD`; `story_trace` on US-1, US-2 and US-3. `impact` also listed `current-artifact-names` US-1/US-4 and `coverage-current-names` US-1 (all `declared`) as touched through `artifacts.py`. Because of that I read the shared helpers `_first_table`, `_split_row`, `_col` and `_qa_id_column` (`artifacts.py:314-420`), and their suites passed. `story_trace` shows no `implements` link for US-2/US-3. That is expected: T1/T2 declare their files under US-1. It is not a gap.

Not reviewed: `queries.py`/`cli.py`/`server.py`, because the diff leaves them unchanged and the existing parity test covers adapter identity. I did not run the slow tests (`-m slow`): the change touches nothing they cover (sdist, transport, bench, fresh install).

**Anti-generosity standard applied** (`/opt/aspark/standards/anti-generosity.md`).

## 2. Plan Conformance

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 | ✅ | `_all_tables` splits the section into contiguous pipe chunks and runs `_first_table` on each (`artifacts.py:362-375`). `_parse_qa` checks drift per table and keeps one running index (`artifacts.py:284-311`). This matches plan §1 exactly. |
| T2 | ✅ | 5 tests. Run against the HEAD~1 code, 3 fail (sub-tables read, 2× drift) and 2 pass. The 2 that pass are by nature regression guards (AC-1.3, AC-3.1), so they cannot fail before the change. One assertion was vacuous (F1, fixed). |
| T3 | ✅ | `CLAUDE.md:41-42,163` and `constitution.md:99` no longer state the limit. `BACKLOG.md:240` is marked as implemented. Plan §2 lists all three docs, although the T3 row names only `files: CLAUDE.md`. That is cosmetic, not a deviation. |

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Minor | `tests/test_qa_multi_table.py:53-60` | **Problem:** the AC-1.3 test asserted that AC-1.2 stays unverified, but its outside table (`\| Foo \| Bar \|`) contained no AC-1.2, so that assertion could never fail. The test only failed through an incidental drift error. A narrow mutant that reads the `## 6.` table died on `TemplateDriftError`, not on the assertion. **Why it matters:** if drift checking were ever relaxed, the guard would pass silently. **Fix applied:** the outside table is now `\| Spec ID \| Result \|` with `AC-1.2 ✅ pass`, and the same mutant now dies on `assert 'ac:demo:AC-1.2' in {...}`. | fixed r1 |
| F2 | Minor | `tests/test_qa_multi_table.py` (no test), `artifacts.py:286,295` | **Problem:** no test pins NFR-2's running index across tables. A mutant that resets `index = 0` per table passed all 392 tests. With a reset, the same AC re-checked at the same row position of two tables collides on `qa:<f>:<ac>#<i>` (`model.py:89`): `add_node` overwrites the earlier check, `added` still counts 2, and `order` no longer reflects document order for `_latest` (`queries.py:422`). **Why it matters:** the current code is correct, but the guarantee is unprotected. **Fix:** add a test with `AC-1.1` as row 0 of two tables (❌ then ✅). Assert two QA checks, ids `#0` and `#1`, and `latest_result == "pass"`. | fixed (test added, 393 pass) |
| F3 | Nit | `.spark/constitution.md:96`, `CLAUDE.md:239` | **Problem:** both say "319 tests"; the suite runs 392 (+4 slow). The count was already stale at HEAD~1, and this diff edited the neighbouring constitution line without updating it. **Why it matters:** doc drift. This is artifact wording, so it is capped and changes no verdict. **Fix:** update both counts at the next release. | fixed (393) |

## 4. Requirements Traceability

| Spec ID | Implemented at | Verdict |
|---|---|---|
| AC-1.1 | `artifacts.py:284-311`, `362-375` | ✅ met. `test_every_subtable_is_read`; real Core corpus: `graph-gates` 5→30, `lean-artifacts` 8→15, `project-kickoff` 6→26, `tracker-handoff` 5→21 checks (4 of 34 `qa.md` changed) |
| AC-1.2 | unchanged `queries.story_trace`/`gate_health` over the new nodes | ✅ met. Same test asserts `unverified_acs == []` and `latest_result` pass for AC-1.2 from the 2nd table |
| AC-1.3 | `_section` stops at the next `#`/`##` (`artifacts.py:355-358`); `_all_tables` only gets the section | ✅ met. `test_tables_outside_the_section_are_not_read` (strengthened, F1) |
| AC-2.1 | `artifacts.py:290-293`, per table | ✅ met. 2 drift tests; message names the file path and the missing column (same text as before) |
| AC-3.1 | `artifacts.py:286,295` (index identical to old `enumerate`) | ✅ met. Live, below |
| AC-4.1 | `CLAUDE.md:41-42,163`, `constitution.md:99` | ✅ met. Grep over `*.md` (excluding historical trails and `.factory/tickets.md`) finds no statement of the old limit; README/SECURITY never mentioned it |
| NFR-1 | no new import/dep; no new I/O | ✅ met. AC-3.1 `cmp`; diff adds no dependency |
| NFR-2 | `artifacts.py:286,295` | ✅ met in code (running index across tables, equal to `enumerate` for one table); test gap is F2 |

**AC-3.1 evidence (re-derived; condition b, a Must AC).** I created a worktree at HEAD~1 (`dd4b994`) and imported its `src/` via `PYTHONPATH`, after confirming `artifacts.__file__` pointed at the worktree and that `_all_tables` was absent. I ran `build --full /workspace/repo` under the old code and under the new code. `cmp` reported IDENTICAL, both sha256 `7edd1c60d0c7…b53`, with 68 `QACheck` nodes in this repo's graph. **Real-corpus probe** (constitution's "read a wide set of real files" rule): I ran `_parse_qa` on all 34 Core `qa.md` files in `/opt/aspark/.spark` under the old and new code. Results: 30 identical outputs, 4 with gained checks only, no new `TemplateDriftError`. The 9 pre-existing errors have the same message under both codes. No duplicate AC ids appeared in the multi-table files.

## 5. What Was Checked

- [x] Correctness: the logic does what the ACs demand. Live: suite, `cmp`, real-corpus probe.
- [x] Non-functional: NFR-1 and NFR-2 hold. Determinism is proven against the pre-change code, not by a double-build.
- [x] Error handling: drift is raised per table through the existing `TemplateDriftError` seam. Nothing is swallowed. A pipe chunk without a separator row is skipped, as C3 decides.
- [x] Security: no new input path, file access or subprocess. Markdown is parsed into data only.
- [x] Tests: 392 pass. 3/5 new tests fail on the old code. F1 is fixed; F2 fixed afterwards.
- [x] Readability: `_all_tables` is 13 lines and reuses `_first_table`; the running-index line is commented.

## 6. Verdict

**Passed.** Every Must AC (AC-1.1, 1.2, 1.3, 2.1, 3.1) and both NFRs are met, each decided by a live observable. The strongest evidence: the graph of this repo is byte-identical to the one HEAD~1 builds. The real Core corpus gains checks in exactly the 4 split-table reports and in no other file, with no new drift errors. One known behaviour change is intended: R1 in the plan accepts that a later verification table with a deviating header now fails the build. Today no real Core file trips it. I fixed one vacuous test assertion (F1) and re-ran the suite green. Two findings stay open, neither blocking. F2 (Minor): no test guards the cross-table running index, which is NFR-2's uniqueness guarantee, and a per-table reset mutant passes the full suite. F3 (Nit): the documented test count is stale. F2 should be fixed before `/go-live` so NFR-2 cannot regress silently.

---

## ✅ REVIEW GATE

*All boxes checked → `/demo-day` may start. Any box open → back to `/increment`. On
re-review, edit this same checklist in place — never duplicate it as a second gate.*

- [x] No open Blocker findings
- [x] No open Major findings (or explicitly waived by the user, with reason recorded here)
- [x] Every Must AC traces to implementing code; no constitution non-negotiable violated
- [x] All plan deviations documented and accepted (none; the T3 `files:` note is cosmetic, see §2)
- [x] Test suite runs green (392 passed, 4 deselected, after the reviewer's F1 edit)
- [x] Line budget respected: Ist ~85 / Soll ~150 (excluding HTML comments)
- [x] Status set to `passed`
