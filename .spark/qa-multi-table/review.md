# Review Report: qa-multi-table

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | The diff of `/increment` (`d334d25..c80b394`), `.spark/qa-multi-table/plan.md` |
| **Status** | `changes-requested` |
| **Round** | 1 |
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
- **Verdict:** Code meets all six Must ACs (verified live, including on a Core clone), but T2's CLI and MCP drift tests were marked done and do not exist, so the gate stays closed.
- **Open:** `1 open`. Blockers: none. Majors: none (Minor: `F4`, see §3)
- **Binding ruling:** §6 Verdict and the gate checklist below — the only binding location; there is no other round to point to
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Scope

- **Reviewed:** `git diff d334d25..c80b394`: `src/aspark_graph/artifacts.py` (`_parse_qa`, new `_tables`), `tests/test_artifacts.py` (+69 lines), `CLAUDE.md`, `.spark/BACKLOG.md`, `.spark/constitution.md`, `plan.md` status cells. I also read the code around it: `_first_table`, `_split_row`, `_section`, `_parse_review`, `cli.py:174`, `server.build_graph`.
- **Mode:** live. I ran the full suite and `-m slow`, did in-process CLI/MCP probes, ran three mutation probes against the new tests, did a three-way byte-identity build, and built a real Core clone. Nothing below rests on a static read alone.
- **Anti-generosity standard applied** (`/opt/aspark/standards/anti-generosity.md`, read in full before the verdict).
- **No graph tool or lens was passed.** I scoped by hand with grep/Read.
- **Core-clone check (plan §4): performed, contrary to the caller's note that it was not possible offline.** The network was reachable. I ran `git clone --depth 1 github.com/a-lottes/aSPARK` at SHA `2c84ad5801db93b354eaa9a3621563944d566d12`; the `.spark/` matches `/opt/aspark/.spark` except for one extra feature.
- **Not reviewed:** release/version handling, which spec C7 leaves to `/go-live`.

## 2. Plan Conformance

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 | ⚠️ | Code is as planned: `_tables` at `artifacts.py:387`, running index at `:285`/`:294`, and `git diff` shows no line inside `_first_table`. The test does not meet the DoD: 5 AC rows instead of 6, and no `gate_health` assertion (F2). |
| T2 | ❌ | Parser-level drift test exists (`test_artifacts.py:177-189`, current and legacy name). The CLI exit/one-line/no-Traceback test and the MCP same-`str(exc)` test in the DoD are absent (F1). |
| T3 | ✅ | Prose, `###` headings, separator-less run, empty section and multi-table double build are all covered. The escaped-pipe case did not discriminate until F3 was fixed. |
| T4 | ✅ | Re-derived by me under condition (b), because this is a Must AC's verification. Plan R3 applied, since `git diff v0.7.3 d334d25` touches `build.py` (C# import resolution only). So I built under **both** `v0.7.3` (`87ad247`) and `d334d25`, and under `c80b394`. Fixtures were copies of this repo's `.spark/`, `tests/fixtures/sample_repo` and `tests/fixtures/current_names_repo`, each `.git`-marked, `--full`. `cmp` gave IDENTICAL for all 6 pairs. `-m slow` gave 3 passed and 1 failed (NFR-1 bench; see F4). |
| T5 | ✅ | BACKLOG G6 marked done; constitution §9 updated plus an Amendments row; test count 411 matches the suite. The CLAUDE.md wording was fixed by me (F5). |

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Major | `tests/test_artifacts.py:177-189` | T2 is marked `done`, but nothing calls `cli.main(["build", …])` or `server.build_graph` on a later-table drift. A grep of `tests/` finds **no** test anywhere that exercises the CLI's `TemplateDriftError` catch (`cli.py:174`). Why it matters: AC-1.3/NFR-3 and the "clean errors, never tracebacks" non-negotiable are guarded only by my live probe (rc 1, 1 stderr line, MCP raised the identical string), and a regression in the adapter edge would ship green. Fix: in the parametrised test, add a `.git` marker and assert `cli.main` returns 1, `len(err.splitlines()) == 1`, no `Traceback`, and that `server.build_graph(repo)` raises with `str(exc) == err.strip()`. | fixed |
| F2 | Minor | `tests/test_artifacts.py:134-170` | The T1 DoD asks for 6 AC rows plus a `gate_health(...)["unverified_acs"] == []` assertion. The fixture has 5 AC rows, its spec defines only `AC-1.1`, so no `verifies` edge to a later-table AC exists in the test, and `gate_health` is never called. AC-1.1's `gate_health` clause is untested. Minor rather than Major: the edge wiring is the same code path for every table, and the node-level asserts kill the index and drift mutations (M2, M3). Fix: give the fixture spec AC-1.1…3.2 and assert `gate_health` lists only non-pass ACs. | fixed |
| F3 | Minor | `tests/test_artifacts.py:170` | The escaped-pipe row asserted only `result`, which reads `pass` with or without unescaping. Mutation M1 (`unescape_pipes=False`) passed the whole new block. Fixed by asserting `date == "d"` for every row; M1 is now killed. | fixed r1 |
| F4 | Minor | `tests/test_incremental_bench.py` (NFR-1 bench) | `uv run pytest -m slow` failed at speedup 47.3% against a target of ≥50%, so T4's "slow passes" does not hold in this environment. Alternating runs: baseline `d334d25` gave 49.9 / 50.3 / 43.2 %, HEAD gave 48.5 / 45.6 / 50.3 %. Both sit on the threshold, and the diff only touches artifact parsing (not cached, negligible cost), so this is not a regression from this change. Fix: re-run `-m slow` on the developer machine before `/go-live` and record the figure; if it stays flaky, open a BACKLOG item for the bench's noise margin. | open |
| F5 | Nit | `CLAUDE.md:41-42` | The changed line read "known limits: every QA verification table per `qa.md` is read", which presents a lifted limit as a current limit. Reworded to "its known limit G6 … was lifted by `qa-multi-table`". The suite is still green. | fixed r1 |

## 4. Requirements Traceability

| Spec ID | Implemented at | Verdict |
|---|---|---|
| AC-1.1 | `artifacts.py:286-310` | ✅ met. Live probe: 3 tables / 6 ACs gives 6 QAChecks and `unverified_acs == []`. On Core, project-kickoff goes from 6 to 26 QAChecks for 26 ACs, and its 3 unverified ACs are exactly its 3 `unknown` results. |
| AC-1.2 | `artifacts.py:285,294-295` | ✅ met. Test orders `[0,1,3,4,5]`; mutation M2 (per-table reset) is killed; 0 duplicate ids on all 4 Core files. |
| AC-1.3 | `artifacts.py:288-292`, `cli.py:174` | ✅ met (live: CLI rc 1, one line, MCP identical `str`). Test coverage is incomplete (F1). |
| AC-1.4 | `artifacts.py:387-409` | ✅ met (prose, `###`, separator-less run, no-table cases tested). |
| AC-1.5 | unchanged single-table path | ✅ met. `cmp` IDENTICAL against v0.7.3 and d334d25, 3 fixtures (§2 T4). |
| AC-1.6 | `artifacts.py:286` (`unescape_pipes=True`) | ✅ met. Test is discriminating after the F3 fix. |
| NFR-1 | canonical save | ✅ (multi-table double-build test; stash round-trip) |
| NFR-2 | `artifacts.py:288-292` | ❌ The bench clause failed in this environment (F4; baseline equally). Loud drift ✅; 411 default tests green ✅. |
| NFR-3 | existing seam, no new plumbing | ✅ (live probe). Test gap is F1. |
| NFR-4/5 | — | N/A per spec |

Core clone `2c84ad5`: 26 of 37 features build under both versions. The other 11 drift identically under both, on unrelated spec/qa shape. QAChecks went from 322 to 390, the entire +68 coming from the 4 multi-table files: graph-gates 5→30, lean-artifacts 8→15, project-kickoff 6→26, tracker-handoff 5→21. No feature newly drifts, so A1/R1 hold at this SHA.

## 5. What Was Checked

- [x] Correctness: logic does what the acceptance criteria demand
- [ ] Non-functional: applicable NFRs and constitution quality bars hold (NFR-2 bench clause, F4)
- [x] Error handling: failures are handled, not swallowed
- [x] Security: no injected input trusted, no secrets in code
- [ ] Tests: exist, are meaningful, and pass (pass: 411; T2's CLI/MCP tests missing, F1; F2)
- [x] Readability: the next developer will understand this

## 6. Verdict

Changes requested. The parser change is correct, and I verified that by running it, not by reading it:
- every table in the verification section is read, with a running index;
- drift in a later table fails loudly with the same message through CLI and MCP;
- single-table graphs are byte-identical to both v0.7.3 and the pre-change HEAD;
- on a real Core clone, the four per-story `qa.md` files now report 26/26, 30/30, 15/15 and 21/21 QAChecks with no new drift.

The gate stays closed on F1. T2 is marked `done`, but its CLI and MCP tests do not exist, and no test in the suite covers the drift-to-CLI seam that a constitution non-negotiable depends on.

F2 (T1's `gate_health` assertion) and F4 (a flaky NFR-1 bench that fails equally on the baseline) are open Minors. I fixed F3, a non-discriminating escaped-pipe test, and F5, CLAUDE.md wording; the suite is green at 411 after both.

---

## ✅ REVIEW GATE

*All boxes checked → `/demo-day` may start. Any box open → back to `/increment`. On
re-review, edit this same checklist in place — never duplicate it as a second gate.*

- [x] No open Blocker findings
- [ ] No open Major findings (or explicitly waived by the user, with reason recorded here): F1 open
- [x] Every Must AC traces to implementing code; no constitution non-negotiable violated
- [ ] All plan deviations documented and accepted: T1/T2 DoD shortfalls documented (F1, F2), not yet resolved
- [x] Test suite runs green (default 411 passed; `-m slow` 3/4, see F4)
- [x] Line budget respected: Ist ~80 / Soll ~150 (excluding HTML comments)
- [ ] Status set to `passed`
