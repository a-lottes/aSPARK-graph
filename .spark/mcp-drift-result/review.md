# Review Report: mcp-drift-result

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | The diff of `/increment` (`dd4b994..dbc4f76`), `.spark/mcp-drift-result/plan.md` |
| **Status** | `passed` |
| **Round** | 1 |
| **Date** | 2026-11-11 |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Verdict:** Passed. All Must ACs met, verified by live runs including a pre-change worktree round-trip. No Blocker or Major. 3 Minors and 1 Nit remain open.
- **Open:** `4 open` — Blockers: none; Majors: none (Minors/Nits: see §3)
- **Binding ruling:** §6 Verdict and the gate checklist below — the only binding location; there is no other round to point to
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Scope

- **Reviewed:** `git diff dd4b994..dbc4f76`. Production code is in `0c8d960` (`src/aspark_graph/artifacts.py:58-69`, `src/aspark_graph/server.py:15,29-31`). Tests, docs and the trail are in `dbc4f76` (`tests/test_mcp_errors.py`, `tests/test_cli_mcp_parity.py:301-325`, `README.md:222-227,312-316`, `CLAUDE.md:48-51,243`, `.spark/BACKLOG.md:258`, spec/plan). I also read the context needed to judge it: `build.py:103-194` (raise point vs. `parse_cache.save`), `cli.py:164-184` (parity reference), and `SECURITY.md:50-70`.
- **Graph (aspark-graph MCP):** `staleness` was stale (2 test files), so I ran `build_graph` once and the graph came back fresh. `impact --diff dd4b994..HEAD` showed declared links from `artifacts.py`/`server.py`/both test files into this feature's US-1/US-2/US-3, plus regression reach into `security-posture` US-1 (the refusal seam) and `shallow-clone-warning` US-1 (the success-dict booleans). Because of that I read the `RepoRefused` branch at `server.py:27-28` and the success dict at `server.py:33-42`. The docs were `unknown_files`, so I scoped them by hand. `story_trace` US-1/2/3 showed that T7 and T10 have no code links, so I re-derived T7 myself (see §5). I did not call `gate_health` (per the tool file).
- **Mode:** live. I ran the full suite, the slow suite, a `git worktree` round-trip against `dd4b994`, an in-process FastMCP `call_tool`, and ad-hoc probes. The real stdio transport was **not** exercised for the drift result. Its JSON serialisation was checked through `mcp.call_tool`, which returns `TextContent` JSON with the four keys.
- **Standards applied:** Anti-generosity standard applied (`/opt/aspark/standards/anti-generosity.md`). Constitution `.spark/constitution.md`: the only active lens is `cli` (NFR-6). `CLAUDE.md` non-negotiables.
- **Not reviewed:** none.

## 2. Plan Conformance

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 | ✅ | `artifacts.py:64` class attr `reason`. `server.py:29-31` has one catch that reads `exc.reason`, so the reason is not a literal. `cli.py` is untouched by the diff |
| T2 | ✅ | `README.md:222-227` |
| T3 | ✅ | `tests/test_mcp_errors.py:63-87`: (a) exact keys, (b) `== str(exc)`/`file == exc.file`, (c) no graph, (d) valid prior graph byte-identical, (e) second call `== data` |
| T4 | ⚠️ | The test exists (`REVIEW_DRIFT`, `:56`), but it never asserts the "findings table missing" mismatch that the DoD names. See F3 |
| T5 | ⚠️ | `tests/test_cli_mcp_parity.py:301-325` covers only the no-prior-graph case. The DoD's "byte-identical when one existed before" branch is untested. See F2. I probed it by hand and it passes |
| T6 | ✅ | `tests/test_mcp_errors.py:90-95` pins the key set. `test_confinement_cli_mcp.py`/`test_confinement_guards.py` are unedited (not in the diff) and green |
| T7 | ⚠️ | Marked `done`, but the DoD's "commands, SHAs and outputs recorded in review.md" did not exist. I re-performed it (§5) and it passes. See F1 |
| T8 | ✅ | `README.md:312-316`. `test_readme`/`test_security_doc`/`test_integration_docs` are green |
| T9 | ⚠️ | The CLAUDE.md entry and the count (392 = observed) are correct. The G7 note was in German, against T9/R6 and constitution §5. Reviewer fixed it (F5) |
| T10 | ✅ | Suite 392 passed. Slow suite 3/4 on the first run, with the bench flake failing on base too (F4). `aspark-graph build .` parses this trail |

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Minor | `.spark/mcp-drift-result/plan.md:53` (T7) | T7 was set `done`, but its DoD evidence (worktree commands, SHAs, outputs) was recorded nowhere. A done status with no evidence is a claim, not a check. Fix: record evidence where the DoD says, at the time the task is done. The reviewer re-derived it and recorded it in §5 | fixed |
| F2 | Minor | `tests/test_cli_mcp_parity.py:325` | The CLI drift test asserts only `graph.json` absent. The T5 DoD and AC-3.1 ("not written **or changed**") also require byte-identity when a prior graph exists, and that is not pinned for the CLI. A future reorder in `_cmd_build` (save before build) would pass. Fix: add a prior-valid-graph case mirroring `test_mcp_errors.py:79-87` and assert bytes unchanged | open |
| F3 | Minor | `tests/test_mcp_errors.py:56-75` | The `review` case asserts `file.endswith("review.md")` and `message == str(exc)`, but not which mismatch. Any review.md drift (e.g. a missing Findings section) passes, so AC-1.3's "missing a required column" case is not pinned. Fix: `assert "findings table missing" in data["message"]` | open |
| F4 | Minor | `tests/test_incremental_bench.py:97` | The NFR-1 bench is flaky and was **not** caused by this diff. At HEAD: 27.9% (fail), then 52.4/53.0/57.0% (pass). At base `dd4b994`: 62.2% (pass), 49.9% and 46.4% (fail). The gate result depends on load. Fix: a BACKLOG entry (more samples or a CPU-time measure). Out of scope here | open |
| F5 | Minor | `.spark/BACKLOG.md:258` | The G7 done-note was written in German, against plan T9/R6 and constitution §5 (English). Reviewer translated it in place. Historical G7 body left untouched as R6 says | fixed |
| F6 | Nit | `tests/test_mcp_errors.py:37-39` | `import pytest` / `from aspark_graph import artifacts, build` were placed mid-file. Reviewer moved them to the top import block. Suite still 392 passed | fixed |
| F7 | Nit | `tests/test_cli_mcp_parity.py:303-312` | The drift fixture bodies and repo setup duplicate `QA_DRIFT`/`REVIEW_DRIFT`/`_drift_repo` in `test_mcp_errors.py:46-59`, so the two can drift apart. Fix: import the fixtures from one place (e.g. a `conftest.py` helper) | open |

## 4. Requirements Traceability

| Spec ID | Implemented at | Verdict |
|---|---|---|
| AC-1.1 | `server.py:29-31`; test `test_mcp_errors.py:69-71` | ✅ met (exact 4 keys, no raise; the test fails on `dd4b994`) |
| AC-1.2 | `build.py:176` raises before `:192` save and before `server.py:32`; test `test_mcp_errors.py:75,79-87` | ✅ met (absent and byte-identical; parse-cache also unchanged in probe) |
| AC-1.3 | test `test_mcp_errors.py` `[review]` | ✅ met (probe: `findings table missing a 'severity' column`; weak assertion F3) |
| AC-1.4 | `server.py:31` `str(exc)`; test `:74` | ✅ met |
| AC-2.1 | `server.py:33-42` unchanged; test `:90-95` | ✅ met: worktree round-trip, `cmp` identical for MCP dict and `graph.json` on sample repo and HEAD-tree export |
| AC-2.2 | `server.py:27-28` unchanged | ✅ met (`test_confinement_cli_mcp.py` green, unedited; probe returned `found:false, reason:outside_confinement`) |
| AC-3.1 | `cli.py:170-172` unchanged; test `test_cli_mcp_parity.py:301-325` | ✅ met: rc/stdout/stderr identical to `dd4b994`; prior graph and cache byte-identical by probe (untested in suite, F2) |
| AC-4.1 | `artifacts.py:64`; `cli.py:170`; `server.py:29` | ✅ met (one catch each, render-only) |
| AC-4.2 | `README.md:222-227,312-316` | ✅ met |
| AC-4.3 | `CLAUDE.md:48-51`; `BACKLOG.md:258` | ✅ met (version not chosen yet; note says "set at /go-live" per C5) |
| NFR-1 | success path untouched | ✅ (bench passed 3 of 4 at HEAD; the failure reproduces on base, F4) |
| NFR-2 | `build.py:110` `ensure_repo` precedes parsing; result = CLI message | ✅ |
| NFR-4 | `test_mcp_errors.py:86` equal dicts; round-trip §5 | ✅ |
| NFR-5 | `server.py:31` `exc.reason` | ✅ |
| NFR-6 (`cli` lens) | `test_cli_mcp_parity.py:319-322` | ✅ (stderr == MCP `message`, one line, exit 1, stdout empty) |

## 5. What Was Checked

- [x] Correctness: logic does what the acceptance criteria demand
- [x] Non-functional: applicable NFRs and constitution quality bars hold
- [x] Error handling: failures are handled, not swallowed. The catch is narrow (`TemplateDriftError` only), with no catch-all
- [x] Security: no injected input trusted, no secrets in code. Confinement runs first, no bypass added
- [x] Tests: exist, are meaningful, and pass. All 4 new drift cases **fail** when run against `dd4b994` code
- [x] Readability: the next developer will understand this

**Evidence (re-derived; trigger: condition (b), a Must-AC verification, plus T7 evidence absent):**
- `uv run pytest`: `392 passed, 4 deselected` (before and after the reviewer's fixes).
- `uv run pytest -m slow`: `1 failed, 3 passed`, where the failure is the bench (27.9%). Bench re-runs at HEAD gave 52.4/53.0/57.0% (pass). At base `dd4b994` they gave 62.2% (pass) and 49.9%/46.4% (fail). The flake predates this change (F4). The transport smoke test, sdist manifest and unlocked fresh-install `serve` test passed.
- Round-trip (T7): `git worktree add /tmp/rv-base dd4b994` against HEAD `dbc4f76`, on the same absolute targets: a `.git`-marked copy of `tests/fixtures/sample_repo`, a `git archive HEAD` export (marked), and a qa.md drift fixture. `cmp` reported IDENTICAL for the MCP success dict and `graph.json` on both targets (sample `7a82e69c…`, self `bad8a012…`), for the in-process CLI drift `{rc, out, err}`, and for the real `aspark-graph build` drift stderr+rc (`rc=1`, one line).
- Probes: CLI drift with a prior graph gave rc 1, empty stdout, 1 stderr line, and `graph.json` + `parse-cache.json` byte-identical. FastMCP `call_tool("build_graph")` on drift returned `TextContent` JSON with the 4 keys and left the graph unchanged.
- `uv run aspark-graph build .` succeeds and parses this trail.

## 6. Verdict

Passed. The production change is two narrow lines in the shared-exception/adapter seam (`artifacts.py:64`, `server.py:29-31`) and does what US-1 requires. I verified it live, not just by reading. The new tests fail on pre-change code. A worktree round-trip against `dd4b994` shows the success dict, `graph.json` and the CLI drift output are byte-identical, which covers US-2 and US-3. A probe confirmed that a prior graph and parse cache survive a failed build on both adapters. No Blocker or Major is open. Open Minors: F2 (CLI prior-graph byte-identity is not pinned in the suite) and F3 (the review.md case does not pin which mismatch). F4 is a pre-existing NFR-1 benchmark flake that failed on base too and belongs in BACKLOG, not in this feature. F7 (duplicated fixtures) is an open Nit. I fixed F1 (recorded the T7 evidence here), F5 (G7 note now in English) and F6 (import placement) directly, and the suite is still green at 392. The real stdio transport was not exercised for the drift result. Its serialisation was checked in-process only, which the plan accepted.

---

## ✅ REVIEW GATE

*All boxes checked → `/demo-day` may start. Any box open → back to `/increment`. On
re-review, edit this same checklist in place — never duplicate it as a second gate.*

- [x] No open Blocker findings
- [x] No open Major findings (or explicitly waived by the user, with reason recorded here)
- [x] Every Must AC traces to implementing code; no constitution non-negotiable violated
- [x] All plan deviations documented and accepted (T4/T5/T7/T9 deviations recorded as F1-F3, F5; none affects a Must AC verdict)
- [x] Test suite runs green (392 passed; slow bench flake pre-existing, F4)
- [x] Line budget respected: Ist ~95 / Soll ~150 (excluding HTML comments)
- [x] Status set to `passed`
