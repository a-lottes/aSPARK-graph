# Review Report: qa-multi-table

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | The diff of `/increment` (`d334d25..3122729`, fix-mode commit `3122729`), `.spark/qa-multi-table/plan.md` |
| **Status** | `passed` |
| **Round** | 2 |
| **Date** | 2026-11-12 |

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
- **Verdict:** Passed. All six Must ACs are met and now guarded by discriminating tests. F1/F2 are confirmed fixed only after reviewer tightening: the r2 test edits in `tests/test_artifacts.py` and `CLAUDE.md` are **uncommitted** and must be committed with this report.
- **Open:** `1 open`. Blockers: none. Majors: none (Minor: `F4`, accepted by the caller as unrelated to this diff, see §3)
- **Binding ruling:** §6 Verdict and the gate checklist below — the only binding location; there is no other round to point to
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Scope

- **Reviewed (r2):** `git show 3122729`: `tests/test_artifacts.py` (+31: fixture spec, `date` assert, `test_qa_multi_table_gate_health_sees_later_tables`, `test_qa_later_table_drift_clean_in_cli_and_mcp`), `CLAUDE.md` (F5 wording, test count), this report. `git diff c80b394 HEAD -- src/` is empty, so the code under review is unchanged since r1. Context read: `cli.py:168-176`, `server.py:20-38`, `artifacts.py:279-310`, `queries.py:390-440`, plan T1/T2 DoD.
- **Mode:** live. Full suite run, eight mutation probes against the new tests (each reverted, `git status` checked), and a fresh three-fixture byte-identity build against `v0.7.3`. `-m slow` was not re-run this round (F4 accepted; no `src/` change since r1).
- **Anti-generosity standard applied** (`/opt/aspark/standards/anti-generosity.md`, read in full before the verdict).
- **No graph tool or lens was passed.** I scoped by hand with grep/Read.
- **Cited, not re-derived:** the Core-clone counts in §4 (r1 evidence, `2c84ad5`); no condition applies, since `src/` is byte-unchanged since that run. **Re-derived under condition (b)** (Must AC verification): AC-1.5 byte identity, see §2 T4.
- **Not reviewed:** release/version handling, which spec C7 leaves to `/go-live`.

## 2. Plan Conformance

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 | ✅ | Code as planned (`_tables` `artifacts.py:387`, running index `:285`/`:294`). DoD now met after r2 tightening (F2): 6 AC rows over 3 tables plus an NFR row, `order == [0,1,3,4,5,6]`, and `gate_health` asserted to list exactly `["AC-2.1","AC-3.1"]`. |
| T2 | ✅ | DoD met after r2 tightening (F1): CLI rc 1, one stderr line, no `Traceback`, and `server.build_graph` raises with `str(exc) == err.strip()`, for both missing-`AC` and missing-`Result` tables, under `qa.md` and `qa-report.md` (4 cases). |
| T3 | ✅ | Unchanged since r1; still green with the 6-AC fixture. |
| T4 | ✅ | Re-derived r2 (condition b): `.git`-marked copies of this repo's `.spark/`, `sample_repo`, `current_names_repo`, built `--full` under `v0.7.3` (`87ad247`, worktree) and the working tree. `cmp`: IDENTICAL ×3 (292809 B / 7169 B / 6038 B). `-m slow`: see F4. |
| T5 | ✅ | BACKLOG/constitution unchanged since r1. CLAUDE.md test count updated by me to 416 to match the suite after r2 edits. |

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Major | `tests/test_artifacts.py:177-189` | T2 is marked `done`, but nothing calls `cli.main(["build", …])` or `server.build_graph` on a later-table drift. A grep of `tests/` finds **no** test anywhere that exercises the CLI's `TemplateDriftError` catch (`cli.py:174`). Why it matters: AC-1.3/NFR-3 and the "clean errors, never tracebacks" non-negotiable are guarded only by my live probe (rc 1, 1 stderr line, MCP raised the identical string), and a regression in the adapter edge would ship green. Fix: in the parametrised test, add a `.git` marker and assert `cli.main` returns 1, `len(err.splitlines()) == 1`, no `Traceback`, and that `server.build_graph(repo)` raises with `str(exc) == err.strip()`. r2: `3122729` added the test but asserted `str(exc) in err` (mutation "CLI prints `error: `+msg" survived) and only the missing-`AC` table; reviewer changed it to `==` and parametrised both tables (`test_artifacts.py:214-228`); traceback, generic-message, two-line, prefix and MCP-swallow mutations are now all killed. | fixed r2 |
| F2 | Minor | `tests/test_artifacts.py:134-170` | The T1 DoD asks for 6 AC rows plus a `gate_health(...)["unverified_acs"] == []` assertion. The fixture has 5 AC rows, its spec defines only `AC-1.1`, so no `verifies` edge to a later-table AC exists in the test, and `gate_health` is never called. AC-1.1's `gate_health` clause is untested. Minor rather than Major: the edge wiring is the same code path for every table, and the node-level asserts kill the index and drift mutations (M2, M3). r2: `3122729`'s test only checked that passed ids are absent from `json.dumps(health.get(...))`, so it passed **vacuously** with `gate_health` mutated to return `{"found": False}`, and the fixture stayed at 5 AC rows; reviewer added `AC-2.2`, asserts `found is True` and `unverified_acs == ["AC-2.1","AC-3.1"]` (`test_artifacts.py:203-211`); not-found, first-table-only-edges and fail-counts-as-verified mutations are now killed. | fixed r2 |
| F3 | Minor | `tests/test_artifacts.py:170` | The escaped-pipe row asserted only `result`, which reads `pass` with or without unescaping. Mutation M1 (`unescape_pipes=False`) passed the whole new block. Fixed by asserting `date == "d"` for every row; M1 is now killed. | fixed r1 |
| F4 | Minor | `tests/test_incremental_bench.py` (NFR-1 bench) | `uv run pytest -m slow` failed at speedup 47.3% against a target of ≥50%, so T4's "slow passes" does not hold in this environment. Alternating runs: baseline `d334d25` gave 49.9 / 50.3 / 43.2 %, HEAD gave 48.5 / 45.6 / 50.3 %. Both sit on the threshold, and the diff only touches artifact parsing (not cached, negligible cost), so this is not a regression from this change. Fix: re-run `-m slow` on the developer machine before `/go-live` and record the figure; if it stays flaky, open a BACKLOG item for the bench's noise margin. | open |
| F5 | Nit | `CLAUDE.md:41-42` | The changed line read "known limits: every QA verification table per `qa.md` is read", which presents a lifted limit as a current limit. Reworded to "its known limit G6 … was lifted by `qa-multi-table`". The suite is still green. | fixed r1 |
| F6 | Minor | `review.md` Handoff (as left by `3122729`) | Handoff/body disagreement: the Handoff verdict still said T2's CLI/MCP tests "do not exist" while §3 F1 read `fixed`. Fix-mode updated Status cells without the Handoff line. Fixed by overwriting the Handoff for r2. | fixed r2 |

## 4. Requirements Traceability

| Spec ID | Implemented at | Verdict |
|---|---|---|
| AC-1.1 | `artifacts.py:286-310` | ✅ met. Live probe: 3 tables / 6 ACs gives 6 QAChecks and `unverified_acs == []`. On Core, project-kickoff goes from 6 to 26 QAChecks for 26 ACs, and its 3 unverified ACs are exactly its 3 `unknown` results. `gate_health` clause now test-guarded (F2) r2. |
| AC-1.2 | `artifacts.py:285,294-295` | ✅ met. Test orders `[0,1,3,4,5,6]`; mutation M2 (per-table reset) is killed; 0 duplicate ids on all 4 Core files. |
| AC-1.3 | `artifacts.py:288-292`, `cli.py:174` | ✅ met and test-guarded at parser, CLI and MCP edge, both columns, both file names (F1) r2. |
| AC-1.4 | `artifacts.py:387-409` | ✅ met (prose, `###`, separator-less run, no-table cases tested). |
| AC-1.5 | unchanged single-table path | ✅ met. `cmp` IDENTICAL against v0.7.3 and d334d25, 3 fixtures (§2 T4). |
| AC-1.6 | `artifacts.py:286` (`unescape_pipes=True`) | ✅ met. Test is discriminating after the F3 fix. |
| NFR-1 | canonical save | ✅ (multi-table double-build test; stash round-trip) |
| NFR-2 | `artifacts.py:288-292` | ❌ The bench clause failed in this environment (F4; baseline equally). Loud drift ✅; 416 default tests green ✅. |
| NFR-3 | existing seam, no new plumbing | ✅ test-guarded (F1) r2. |
| NFR-4/5 | — | N/A per spec |

Core clone `2c84ad5` (r1 evidence, cited): 26 of 37 features build under both versions; the other 11 drift identically under both on unrelated spec/qa shape. QAChecks 322→390, the +68 all from graph-gates 5→30, lean-artifacts 8→15, project-kickoff 6→26, tracker-handoff 5→21. No feature newly drifts, so A1/R1 hold at this SHA.

## 5. What Was Checked

- [x] Correctness: logic does what the acceptance criteria demand
- [ ] Non-functional: applicable NFRs and constitution quality bars hold (NFR-2 bench clause, F4)
- [x] Error handling: failures are handled, not swallowed
- [x] Security: no injected input trusted, no secrets in code
- [x] Tests: exist, are meaningful, and pass (416 passed; new tests mutation-checked, F1/F2)
- [x] Readability: the next developer will understand this

## 6. Verdict

Passed. The parser change was already shown correct in r1 by live runs, and `src/` has not changed since. This round's question was whether the fix-mode tests guard it. As committed in `3122729` they did not fully: the `gate_health` test passed vacuously when `gate_health` returned not-found, and the CLI/MCP test used `in`, so a prefixed CLI message survived and the missing-`Result` table was never run through the adapters. I tightened both tests, a direct test-only fix of my own findings. All eight mutation probes are now killed, the suite is green at 416, and AC-1.5 byte identity against v0.7.3 was re-run and holds on three fixtures. The only open finding is F4, a Minor NFR-1 bench flake that fails equally on the baseline and that the caller accepted as unrelated. It still needs a recorded `-m slow` figure before `/go-live`. My r2 edits to `tests/test_artifacts.py` and `CLAUDE.md` are uncommitted and must be committed with this report.

---

## ✅ REVIEW GATE

*All boxes checked → `/demo-day` may start. Any box open → back to `/increment`. On
re-review, edit this same checklist in place — never duplicate it as a second gate.*

- [x] No open Blocker findings
- [x] No open Major findings (or explicitly waived by the user, with reason recorded here): F1 fixed r2
- [x] Every Must AC traces to implementing code; no constitution non-negotiable violated
- [x] All plan deviations documented and accepted: T1/T2 DoD shortfalls resolved (F1, F2 fixed r2)
- [x] Test suite runs green (default 416 passed; `-m slow` not re-run r2, 3/4 in r1, see F4)
- [x] Line budget respected: Ist ~85 / Soll ~150 (excluding HTML comments)
- [x] Status set to `passed`
