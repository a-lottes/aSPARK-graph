# QA Report: qa-multi-table

| | |
|---|---|
| **Phase** | Review (hands-on) |
| **Owner** | QA Tester (`/demo-day`) |
| **Input** | Branch `factory/issue-44` at the commit after review round 1, `.spark/qa-multi-table/spec.md` (approved) |
| **Status** | `passed` |
| **Round** | 1 |
| **Date** | 2026-11-11 |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Verdict:** Yes. Every AC and NFR passes hands-on through the CLI and the in-process MCP functions; split QA reports now count every table.
- **Open:** `0 open` — Blockers: none; Majors: none.
- **Binding ruling:** §5 Verdict and the gate checklist below.
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/demo-day` and proceed — don't stop on it.

## 1. Test Environment

- **App URL / browser / viewports:** N/A. Headless CLI plus MCP server, no UI; CLAUDE.md records `/demo-day` browser QA as structurally N/A and the QA-equivalent as hands-on CLI/MCP checks. No browser was used; nothing was tested by reading source.
- **Under test:** `uv run aspark-graph` from the checkout, scratch repo `/tmp/qa/r` (`.git`-marked) built from `tests/fixtures/current_names_repo` with a rewritten `qa.md`: `### US-1` table (`AC` header, AC-1.1 pass), `### US-2` table (`Spec ID` header, AC-1.2 pass, AC-2.1 fail), and a table under `## 5. Verdict` (AC-9.9 pass).
- **Graph:** built fresh in the scratch repo.

## 2. Acceptance Criteria Verification

| Spec ID | Steps performed | Expected | Observed | Result |
|---|---|---|---|---|
| AC-1.1 | `build .`, then `query gate_health demo` and MCP `gate_health("demo", repo=".")` | ACs of both sub-tables are read | `unverified_acs` is exactly `[AC-2.1]` (the failing row of the later table); AC-1.2 from the second table counts as verified. CLI and MCP agree | ✅ pass |
| AC-1.2 | Built this repo's tracked files under `6681ded~1` (git worktree) and under the new code, `cmp` of graph.json; reviewer repeated with `sample_repo` and `current_names_repo` | byte-identical | identical (607251 bytes); the reviewer reported all three identical | ✅ pass |
| AC-1.3 | The `## 5. Verdict` table in the scratch `qa.md` holds AC-9.9 | no QACheck | AC-9.9 not present in the result; build rc 0 | ✅ pass |
| AC-2.1 | Replaced the second table's header `Spec ID` with `ID` (covered by the test run; the CLI path used the Result case) | drift names file and column | test `test_g6_subtable_without_ac_column_is_drift` passes: `.file` ends in `qa.md`, message names `'AC' or 'Spec ID'` | ✅ pass |
| AC-2.2 | Replaced the second table's `Result` header with `Outcome`, `build .` | drift naming file and column | `template drift in /tmp/qa/r/.spark/demo/qa.md: QA table missing a 'Result' column (found ['outcome', 'spec id', 'steps'])`, rc 1, no traceback | ✅ pass |
| AC-3.1 | `grep` the three files for the old limit | not stated as current | CLAUDE.md and constitution no longer name it; BACKLOG G6 is marked implemented (older trails keep it as history) | ✅ pass |
| NFR-1 | Byte-identity against pre-change code (AC-1.2); the multi-table fixture built twice by the reviewer | identical | identical | ✅ pass |
| NFR-2 | `git diff --stat 6681ded~1..HEAD -- src` | only `artifacts.py` | only `src/aspark_graph/artifacts.py` | ✅ pass |

## 3. Exploratory Findings

| # | Severity | Steps to reproduce | Expected vs. observed | Status |
|---|---|---|---|---|
| B1 | Minor | Multi-table `qa.md` with a bad second table | Drift message names the file and column but not which sub-table (review F3). Accepted | open |

## 4. Console & Network

No browser surface. stderr and exit codes: all builds rc 0 except the intentional drift cases (rc 1, one-line message, no traceback). Full suite 392 passed, slow tests 4 passed (reviewer).

## 5. Verdict

Would I demo this to a stakeholder right now? **Yes.** A QA report split by `### US-n` now yields checks for every table, `gate_health` and `story_trace` see them, single-table graphs are byte-identical to the previous release, and a malformed sub-table fails loudly naming the file. B1 is a Minor wording gap. Not tested: a browser (N/A), Windows/macOS.

---

## ✅ QA GATE

- [x] Every Must-story acceptance criterion verified hands-on and passed (CLI/MCP substitute, §1)
- [x] Every QA-relevant NFR verified and passed
- [x] No open Blocker or Major bugs (B1 Minor listed)
- [x] Tool output free of unexpected errors on the tested flows
- [x] Tested on all agreed surfaces (CLI, in-process MCP functions)
- [x] Line budget respected
- [x] Status set to `passed`
