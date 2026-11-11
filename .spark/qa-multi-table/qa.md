# QA Report: qa-multi-table

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Review (hands-on) |
| **Owner** | QA Tester (`/demo-day`) |
| **Input** | Branch `factory/issue-38` at HEAD `e214c04e6f84571b14807547192e09f998153a13`, `.spark/qa-multi-table/spec.md` |
| **Status** | `passed` |
| **Round** | 1 |
| **Date** | 2026-11-11 |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Verdict:** Yes, I would demo this. Every Must AC and both NFRs were performed live; US-4 (Should) also passes. Three Minors are open (B1-B3), none caused by this feature.
- **Open:** `none` open to fix. B2 fixed (docs say 394). B1 (pre-existing benchmark flake, fails on dd4b994 too) and B3 (pre-existing pydantic-settings stderr warning) accepted as Minor on the autonomous line, not part of this change. Blockers: none; Majors: none
- **Binding ruling:** §5 Verdict and the gate checklist below.
- **On conflict:** the numbered body below wins for everything except `Status`.

## 1. Test Environment

- **App URL / browser / viewport(s):** N/A. Headless CLI/MCP tool; `.spark/constitution.md` §8 declares `Browser-observable surface: no` and names the method performed below.
- **Mode:** live runs of every command below (no code-reading verdicts). Anti-generosity standard applied (`/opt/aspark/standards/anti-generosity.md`, read in full): binary results, no rounding up.
- **Method (constitution §8), each performed:** `uv run pytest -q` (394 passed); `uv run pytest -m slow` (3 of 4 passed, see B1); wheel built with `uv build --wheel`, installed into a fresh venv without the lock, `aspark-graph serve` answered an MCP `initialize` (serverInfo 1.19.0); `tests/test_fresh_install.py` and `tests/test_packaging.py` re-run, 2 passed; byte-identical double build; real-repo `story_trace`/`gate_health`/`impact`.
- **Test data:** scratch repo under `/tmp` copied from `tests/fixtures/current_names_repo`, with a split-table `qa.md` (`### US-1`, `### US-2`, plus a `## 3` table), driven with the installed wheel's CLI. Scratch dirs and the `dd4b994` git worktree were removed afterwards.
- **Graph tools (scoping only, no Result rests on them):** `staleness` (stale, rebuilt with `build_graph`), `impact --diff dd4b994..HEAD` (`artifacts.py` and the new test file reach qa-multi-table US-1/2/3, plus coverage-current-names and current-artifact-names stories, which I treated as neighbours to re-test), `story_trace US-1`.

## 2. Acceptance Criteria Verification

| Spec ID | Steps performed | Expected | Observed | Result |
|---|---|---|---|---|
| AC-1.1 | Scratch repo, `qa.md` with `### US-1` (AC-1.1, AC-1.2) and `### US-2` (AC-2.1, NFR-1); `aspark-graph build .` and dumped `graph.json` QACheck nodes | QA checks of both sub-tables in the graph | Build exit 0; QACheck nodes for AC-1.1, AC-1.2 and AC-2.1 (second table) present | ✅ pass |
| AC-1.2 | Same repo: `query gate_health demo`, `query story_trace US-1` and `US-2` | AC-2.1 (later table) is not unverified; results match the cells | `story_trace US-2`: AC-2.1 `pass`; `gate_health.unverified_acs` lists only AC-1.2, whose cell is `❌ fail` (correct) | ✅ pass |
| AC-1.3 | Added `## 3` table with `\| Spec ID \| Result \| AC-1.2 \| ✅ pass \|`, then replaced its header by `Foo \| Bar` | Not read, not checked for drift | AC-1.2 stayed `fail` with one check; build with the junk header exit 0 | ✅ pass |
| AC-2.1 | Second sub-table header changed to `... Notes` (no Result), then to `Item ...` (no Spec ID); `build .` | One-line drift error naming file and column, non-zero exit, no traceback | `template drift in /tmp/.../qa.md: QA table missing a 'Result' column (...)` and `... missing an 'AC' or 'Spec ID' column (...)`, one line each, exit 1 | ✅ pass |
| AC-3.1 | Full clone of this repo at HEAD `e214c04e6f84571b14807547192e09f998153a13`, copied twice; git worktree of `dd4b994` (old code, `_all_tables` absent); `uv run --project <wt> aspark-graph build <copyA> --full` vs `uv run --project /workspace/repo aspark-graph build <copyB> --full`; `cmp` | Byte-identical (this repo's `qa.md` files are single-table) | `cmp` silent, `IDENTICAL`. sha256 old code `3ac9404df0e1720d861c3f1b6a83bf974b223952dab6c14ff30f321e8b7470a1`, new code `3ac9404df0e1720d861c3f1b6a83bf974b223952dab6c14ff30f321e8b7470a1` (650440 bytes). Re-derived by me (conditions a/b: Must AC; F5 asked for this record) | ✅ pass |
| AC-4.1 | `grep -rniE 'first (QA )?table\|only the first'` over `*.md` and `src`; read `CLAUDE.md` diff, `BACKLOG.md` G6, constitution §9 | No doc states the first-table limit as current | `CLAUDE.md:42,163` now say every table is read; constitution log line 114 says removed; `BACKLOG.md:240` banner "Umgesetzt"; its body (`:244-245`) keeps the original problem statement in present tense under that banner; `.factory/tickets.md:97` is the ticket text | ✅ pass |
| NFR-1 | Double `--full` build of the new code plus an incremental rebuild, `sha256sum` each; `git diff dd4b994..HEAD -- pyproject.toml uv.lock` | Same bytes each time; no dependency change | All three `3ac9404d...470a1`; diff of `pyproject.toml`/`uv.lock` is 0 lines | ✅ pass |
| NFR-2 | Scratch table whose first data row is `NFR-1` (non-AC), then AC rows, then a second table; dumped QACheck ids | Ids use one running row index across tables, unique; equal to today's for one table | `qa:demo:AC-1.1#1`, `AC-1.2#2`, `AC-2.1#3` (non-AC row consumed #0, second table continued); in the earlier split repo `#0,#1,#2`. Single-table equality shown by AC-3.1 | ✅ pass |

## 3. Exploratory Findings

| # | Severity | Steps to reproduce | Expected vs. observed | Status |
|---|---|---|---|---|
| B1 | Minor | `uv run pytest -m slow -q tests/test_incremental_bench.py`, repeat 3 times on HEAD and on a worktree of `dd4b994` | Expected speedup >= 50%. HEAD: 39.0%, 11.9%, 49.4% and one pass; `dd4b994` (old code): 2.6%, 49.0%, 35.6%, all fail. A timing flake in this container, present before the feature, unrelated to `artifacts.py`; but the declared slow suite is not green here | accepted |
| B2 | Minor | `uv run pytest -q`; compare with `CLAUDE.md:239` and `.spark/constitution.md:96` | Docs say 393 tests; the run reports 394 passed (394 collected). Artifact wording only | fixed |
| B3 | Minor | Fresh-venv `aspark-graph serve`, send an MCP `initialize` | stderr prints a pydantic-settings `IncompleteFieldDefinitionWarning` ("lifespan") before the valid reply; the server works. Dependency noise, not from this change | accepted |

Also probed, no defect: a pipe block without a separator row inside a sub-table is skipped, not drift (C3); building a repo whose `## 3` table has a junk header; same AC in two tables keeps two distinct checks (suite test).

## 4. Console & Network

Not applicable (no browser). Machinery watched instead: CLI stderr on every build (only the one-line drift errors above, no tracebacks); `serve` stderr warning recorded as B3.

## 5. Verdict

Yes, I would demo this to a stakeholder. Split-table reports now yield checks, `story_trace` and `gate_health` for every table; drift in any table is a one-line named error; single-table output is byte-identical to `dd4b994` (shared sha256 above). Open: B1 (slow benchmark fails on old code too), B2 (test count off by one in two docs), B3 (stderr warning). All Minor; they need acceptance by the user, which I do not set.

---

## ✅ QA GATE

*All boxes checked → `/go-live` may start. Any box open → back to `/increment`, then re-run
`/demo-day`. On re-test, edit this same checklist in place — never duplicate it as a second gate.*

- [x] Every Must-story acceptance criterion verified live (declared §8 method, no browser) and passed
- [x] Every NFR verified and passed
- [x] No open Blocker or Major bugs (Minor bugs B1-B3 listed, B2 fixed, B1 and B3 accepted as pre-existing)
- [x] Console free of errors on the tested flows (CLI: no tracebacks; B3 is a warning)
- [x] Agreed viewports: N/A (headless, constitution §8)
- [x] Line budget respected: Ist 72 / Soll ~130 (excluding HTML comments), self-reported
- [x] Status set to `passed`
