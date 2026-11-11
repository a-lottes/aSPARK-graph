# Review Report: mcp-drift-result

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | The diff of `/increment`, `.spark/mcp-drift-result/plan.md` |
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
- **Verdict:** Passed. All 7 Must ACs and NFR-2/4/5 verified live or by test. 2 Minor plan-conformance findings stay open (F1, F2). 2 Minors fixed by the reviewer (F3, F4).
- **Open:** `2 open` — Blockers: none; Majors: none (Minors/Nits: see §3)
- **Binding ruling:** §6 Verdict and the gate checklist below — the only binding location; there is no other round to point to
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

<!-- Budget: ~150 lines. -->

## 1. Scope

- **Reviewed:** `git diff dd4b994..HEAD` (6cf4a95, 8ee1f44): `src/aspark_graph/server.py`, `tests/test_mcp_errors.py`, `README.md`, `.spark/BACKLOG.md`, and the spec and plan. Read for context: `artifacts.py:58-65` (exception class), `build.py:103-192` (confinement 110 → `extract_features` 176 → `parse_cache.save` 192), `cli.py:164-185` (`_cmd_build`), `tests/test_cli_mcp_parity.py:213-298`.
- **Graph calls (aspark-graph MCP):** `staleness` → stale (`tests/test_mcp_errors.py` changed), then `build_graph` once, then `impact --diff dd4b994..HEAD`, then `story_trace` US-1 and US-2 `--feature mcp-drift-result`. `impact` showed that `server.py` reaches 10 stories across 6 features through shared-file links. It also listed docs/specs as `unknown_files` (not indexed). Its reach is why I re-read `build.py` and `cli.py`, and why the full suite stands as the regression guard. `story_trace` showed T5/T6 declared against `tests/test_cli_mcp_parity.py`, a file the diff does not touch, which led to F1. `gate_health` was not called (tool rule).
- **Mode:** live runs plus the test suite plus a static read. Nothing was verified by reading alone.
- **Not reviewed:** the slow tests (`-m slow`: transport smoke, fresh install, sdist, bench). The diff touches no packaging, transport or dependency code, and FastMCP serialisation of a `bool`/`str` dict follows the existing `RepoRefused` path.

## 2. Plan Conformance

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 | ✅ | `server.py:29-33`: one `except artifacts.TemplateDriftError` after `RepoRefused`, before `graph.save` (`:34`). No new parameter or env var. |
| T2 | ✅ | `tests/test_mcp_errors.py:30-50`: dict, no graph, sentinel unchanged. |
| T3 | ✅ | `README.md:223-227`, `BACKLOG.md:258`. |
| T4 | ✅ | `tests/test_mcp_errors.py:65-72`. The DoD's `"Findings" in message` assertion was missing; the reviewer added it (F3). |
| T5 | ❌ | Test exists at `tests/test_mcp_errors.py:75-86`, but not in the declared `tests/test_cli_mcp_parity.py` (F1). The stderr-path and stdout-traceback asserts were missing; the reviewer added them (F3). |
| T6 | ❌ | Wrong file (F1). The DoD's exact-key and BuildReport-value asserts are absent (F2). |
| T7 | ✅ | DoD evidence was not recorded before review. The reviewer produced it (§5 evidence E2). |
| T8 | ✅ | Evidence E5 below. |

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Minor | `.spark/mcp-drift-result/plan.md` §2 + T5/T6 `files:`; `tests/test_mcp_errors.py:75-106` | Plan deviation: the T5/T6 tests landed in `test_mcp_errors.py`, but the plan declares `tests/test_cli_mcp_parity.py`, which is unchanged. So `story_trace` links T5/T6 to the wrong file, and `impact` on `test_mcp_errors.py` does not reach US-2. That is a wrong map for the next reviewer. Fix: the EM changes the `files:` notes and §2 to `tests/test_mcp_errors.py`, or the developer moves the two tests. | open |
| F2 | Minor | `tests/test_mcp_errors.py:89-106` | T6 DoD is not met as written. The test asserts only `"built" not in data` and graph bytes equal to the CLI. It does not assert `set(result) == _V071_BUILD_KEYS ∪ {shallow_history, no_git_history}`, and it does not compare the counts against `build.build_graph`'s `BuildReport`. The key set is guarded by `test_cli_mcp_parity.py:297`. Values are unguarded by any test (reviewer verified them live, E3). Fix: add the two assertions T6 specifies. | open |
| F3 | Minor | `tests/test_mcp_errors.py:71,77,82-85` | The T4/T5 DoD assertions were missing: `"Findings" in message`, drifted file name in CLI stderr, no `Traceback` in stdout. Added by the reviewer. Mutation check: with the `server.py` catch removed, 3 of 5 tests in the file fail. | fixed r1 |
| F4 | Minor | `.spark/mcp-drift-result/plan.md` Handoff | Handoff said `Open: 5 tasks not done` while §3 had all 8 tasks `done` (stale block). Artifact wording, capped at Minor. Overwritten to `none`. | fixed r1 |

## 4. Requirements Traceability

| Spec ID | Implemented at | Verdict |
|---|---|---|
| AC-1.1 | `server.py:29-33`; tests `test_mcp_errors.py:30,65` | ✅ met: live E1 returned the 4-key dict with `file` = the drifted `qa.md` |
| AC-1.2 | `build.py:176` raises before `server.py:34` save | ✅ met: live E1, no `.aspark-graph/` at all afterwards |
| AC-1.3 | same ordering | ✅ met: live E1, graph SHA-256 `82dc72d6…` before = after; parse cache also unchanged (`cmp`) |
| AC-1.4 | `server.py:35-44` unchanged | ✅ met: live E3, success dict identical old vs new; keys `test_cli_mcp_parity.py:297` |
| AC-2.1 | `cli.py:170-172` (unchanged) | ✅ met: live E4, rc=1, 1 stderr line naming the file, empty stdout, no traceback |
| AC-2.2 | E5 | ✅ met |
| AC-2.3 | `README.md:223-227`, `BACKLOG.md:258` | ✅ met: both state the shape; G7 "umgesetzt (Issue #40)" |
| NFR-2 | `build.py:110` confinement before parse | ✅ met: `file` is `str(path)` under the confined root (E1). No new param or env var (diff read). |
| NFR-4 | no change to the build path | ✅ met: E2 round-trip plus double build |
| NFR-5 | `cli.py:170-172` | ✅ met: E4 plus `test_mcp_errors.py:75` |

## 5. What Was Checked

- [x] Correctness: logic does what the acceptance criteria demand
- [x] Non-functional: applicable NFRs and constitution quality bars hold
- [x] Error handling: failures are handled, not swallowed
- [x] Security: no injected input trusted, no secrets in code
- [x] Tests: exist, are meaningful, and pass
- [x] Readability: the next developer will understand this

QA-equivalent evidence (headless tool). Base `dd4b994ab52007f5badc63efdc23c873c1c1ebe7`, HEAD `8ee1f4437fe130bb556275ff6efd5517548f1cc0`:
- **E1 (AC-1.1–1.3):** scratch `git clone` of this repo. A clean MCP build gave graph `82dc72d6905921b4…`. With `.spark/shallow-clone-warning/qa.md` replaced by a non-template body, MCP `build_graph` returned `{"built": false, "reason": "template_drift", "file": "/tmp/rv/clone/.spark/shallow-clone-warning/qa.md", "message": "template drift in … missing a '## … Acceptance Criteria Verification' section …"}`. Graph hash unchanged. With `.aspark-graph/` deleted first, the directory did not exist after the call.
- **E2 (NFR-4/T7):** `git worktree` at dd4b994 vs HEAD, MCP `server.build_graph` on fresh `.git`-marked copies, `cmp` byte-identical (old = new = new again). `sample_repo` `7a82e69cb3454eb970dcdfe3c4d26ef42dcde2895bcc5b451b362085112d2296`. `current_names_repo` `07ee6b9ca8e821c2a8b077903419dff98ce3138288c4c45202fafe2a3ea1f5aa`. Live-repo clone, old vs new: both `82dc72d6905921b4…`. Warm-cache CLI double build: byte-identical.
- **E3 (AC-1.4):** success dict minus `graph_path`, old vs new on the clone: identical (`code_entities` 688, `artifact_entities` 555, `inferred_edges` 187, rest empty/false). No `built` key.
- **E4 (AC-2.1):** `uv run aspark-graph build` on the drifted clone: rc=1, stdout empty, stderr exactly 1 line naming the file, 0 `Traceback`.
- **E5 (AC-2.2/T8):** `TemplateDriftError` is raised only in `artifacts.py` (170-292). `except artifacts.TemplateDriftError` appears once in `cli.py:170` and once in `server.py:29`. There are no hits in `queries.py`/`build.py` (grep rc=1). `git show 6cf4a95 --stat`: only `server.py` under `src/`.
- **Suite:** `uv run pytest`: 391 passed, 4 deselected (before and after the reviewer edits).
- **Security note (not a finding, predates this change):** artifact reads follow symlinks, and a drift message can echo header names (`found [...]`). The CLI has done this since before this diff, and the graph already exposes symlinked artifact content to MCP clients, so this is not a new class of exposure.

## 6. Verdict

Anti-generosity standard applied (`/opt/aspark/standards/anti-generosity.md`). Every row above was decided by a live run, a test run or a `file:line` read; none rests on a graph answer. The change does what US-1 and US-2 demand. One `except` branch in the adapter returns the specified dict, the shared modules are untouched, and the ordering in `build.py` guarantees nothing is written on drift. I confirmed all of this live, including byte-identity against the pre-change code. No Blocker or Major is open, so the gate passes. Two Minors remain open and are real. F1: the T5/T6 tests live in a file other than the one the plan declares, so this feature's graph trail points at the wrong file. F2: the T6 test is weaker than its DoD, and no test pins the success-path values; only this review's live check covers them. Both should be closed in the next `/increment` touch or by an EM plan edit. I fixed F3 (missing T4/T5 assertions, confirmed by mutation) and F4 (stale plan Handoff) myself, and the suite is green after the fixes.

---

## ✅ REVIEW GATE

*All boxes checked → `/demo-day` may start. Any box open → back to `/increment`. On
re-review, edit this same checklist in place — never duplicate it as a second gate.*

- [x] No open Blocker findings
- [x] No open Major findings (or explicitly waived by the user, with reason recorded here)
- [x] Every Must AC traces to implementing code; no constitution non-negotiable violated
- [x] All plan deviations documented and accepted (F1/F2 documented as open Minors; Minors do not block the gate)
- [x] Test suite runs green
- [x] Line budget respected: Ist ~95 / Soll ~150 (excluding HTML comments) — self-reported, no linter checks this; an overage is recorded here with a reason or explicitly waived by the user
- [x] Status set to `passed`
