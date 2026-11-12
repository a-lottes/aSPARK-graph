# QA Report: qa-multi-table

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Review (hands-on) |
| **Owner** | QA Tester (`/demo-day`) |
| **Input** | `.spark/qa-multi-table/spec.md` (the acceptance criteria), branch `factory/issue-74` at `6cba213` |
| **Status** | `failed` |
| **Round** | 1 |
| **Date** | 2026-11-12 |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Verdict:** Fail on one gate box only. All six ACs and NFR-1/NFR-3 pass in performed runs; NFR-2's "NFR-1 benchmark stays passing" clause did not hold in every run (B1). No code defect found.
- **Open:** `1 open`. Blockers: none. Majors: none (Minors: B1, B2, B3, see §3). The unchecked box is the NFR box, decided by B1; only the user can accept or waive it.
- **Binding ruling:** §5 Verdict and the gate checklist below, the only binding location.
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/demo-day` and proceed.

## 1. Test Environment

- **Mode:** live runs of every step below (tests, installed-wheel CLI, real stdio MCP client). No code was read in place of a run. The previous `qa.md` (written by the conductor without this ceremony) was treated as untrusted and overwritten.
- **Anti-generosity standard applied** (`/opt/aspark/standards/anti-generosity.md`, read in full before the verdict). No lens and no graph tool were passed.
- **App URL / browser / viewport:** N/A. Constitution §8 declares `Browser-observable surface: no`; the substitute method (suite, slow tests, wheel install, `serve` boot, byte-identical build, real-repo `impact`/`story_trace`) was performed.
- **Build under test:** `uv build --wheel` of HEAD `6cba213` (clean tree) installed into a fresh venv `/tmp/qa74/venv` (mcp 1.19.0, pydantic 2.13.5, no lockfile). Baseline: wheel built from tag `v0.7.3` (`ec7d671`) in `/tmp/qa74/venv073`.
- **Test data:** scratch `.git`-marked dirs under `/tmp/qa74` (`s1`, `b1-3`, `d1-6`, `e2-8`), written by me, not by the tests. Core `.spark/` snapshot at `/opt/aspark/.spark` (not a git repo here, so no SHA; 38 entries, 31 with a `spec.md`).

## 2. Acceptance Criteria Verification

| Spec ID | Steps performed | Expected | Observed | Result |
|---|---|---|---|---|
| AC-1.1 | `s1`: `qa.md` with 3 tables under `### US-1/2/3` (Spec ID\|AC\|Spec ID headers), an NFR row, a trailing non-AC `## 3` bug table. `aspark-graph build`, then `query gate_health feat`, `story_trace US-2` | Every AC row in any table is a QACheck; `gate_health` uses each table's result | v0.7.3 wheel on the same dir: 2 QACheck. New wheel: 5 (AC-1.1,1.2,2.1,2.2,3.1). `unverified_acs` = AC-1.2 (❌) and AC-2.1 (⚠️ passed); AC-2.2, AC-3.1 not listed. `story_trace US-2` shows AC-2.1 `unknown`, AC-2.2 `pass` | ✅ pass |
| AC-1.2 | Read QACheck ids/`order` from `s1` graph.json; repeat with `e8` (500 rows in table 2, 5000-emoji cell in table 1) | Index runs across tables, rows without an AC id consume one, ids unique, order strictly increasing | `s1`: `#0 #1 #3 #4 #5` (NFR row took index 2). `e8`: 501 nodes, 501 distinct ids, max order 500, sorted | ✅ pass |
| AC-1.3 | Installed wheel, `build` on `d1` (table 2 lacks AC), `d2` (lacks Result), `d3`/`d4` same as legacy `qa-report.md`, `d6` (table 3 drifts after two good tables); then in-process `server.build_graph`, then a real stdio MCP client `call_tool build_graph` | `TemplateDriftError` naming file and column; one line, rc != 0, no traceback in CLI and MCP | All 5 CLI runs: rc=1, exactly 1 stderr line, 0 `Traceback`, text e.g. `template drift in …/d2/.spark/feat/qa.md: QA table missing a 'Result' column (found ['ac', 'notes'])`. In-process: same `str(exc)`, 1 line. Real stdio: `isError=True`, `Error executing tool build_graph: <same text>`. Valid `s1` over stdio: `isError=False` | ✅ pass |
| AC-1.4 | `s1` prose/headings/blank lines between tables; `b3` no table; `e7` only a separator-less pipe run; `e6` separator-less run then a real table; `e4` header-only table; `e3` CRLF + `:---:` separators | Prose ignored; no table gives 0 QACheck, no error; separator-less run skipped | `s1` prose with a stray `\|` ignored; `b3` and `e7` rc=0, 0 QACheck; `e6` reads only the real table (AC-1.2 at order 0); `e4` header-only table adds nothing; `e3` reads both tables (orders 0,1) | ✅ pass |
| AC-1.5 | Built v0.7.3 wheel and HEAD wheel, `build --full` on identical copies, `cmp` graph.json: `b1` (qa.md, 4 result kinds), `b2` (legacy `qa-report.md`), `b3` (no table), `sample_repo`, `current_names_repo` fixtures, copy of this repo's `.spark/` | Byte-identical for exactly-one-table files | `cmp` IDENTICAL for all six: 4179 B, 3229 B, 2912 B, 7169 B, 6038 B, 295226 B. Multi-table `s1` differs, as intended | ✅ pass |
| AC-1.6 | `s1` table 2/3 cells `⚠️ passed with caveat`, `✅ a \| b`, `❌ fail`; `b1` single-table equivalents; `e4` duplicate AC in two tables | Same normalisation as table 1: marker-first, pipes unescaped, columns kept | `⚠️ passed…`→`unknown`, `❌`→`fail`, `✅ a \| b`→`pass` with `date`=`d` (column not shifted), matching `b1` results. `e4`: duplicate AC gives two nodes (`fail` #0, `pass` #1) as spec §6 says | ✅ pass |
| NFR-1 | Double `build --full` of `s1`, then `--full` vs incremental, `cmp`; stash-equivalent v0.7.3 vs HEAD on the AC-1.5 inputs; `test_qa_multi_table_double_build_identical` | Multi-table double build byte-identical; single-table and own `.spark/` identical to v0.7.3 | `s1` full/full IDENTICAL, full/incremental IDENTICAL. v0.7.3 comparison: see AC-1.5 (six IDENTICAL) | ✅ pass |
| NFR-2 | `uv run pytest`: 1 run. `uv run pytest -m slow` ×3 at HEAD, bench ×4 on a `d334d25` worktree. Drift: see AC-1.3 | Drift loud; suite green; NFR-1 benchmark "stays passing" | Suite: 416 passed. Slow (fresh-install `serve` boot, MCP stdio, sdist manifest) 4/4 passed in all 3 runs. Bench at HEAD: 51.0 %, **46.6 % (FAILED, target ≥50)**, 58.1 %. Bench at baseline `d334d25`: 52.1, 52.0, 54.4, **49.6 (FAILED)**. Drift clause holds | ❌ fail |
| NFR-3 | See AC-1.3: single stderr line, rc, traceback count, MCP text vs CLI text | One line, non-zero exit, no traceback, same text via MCP | `d2` CLI line and in-process `str(exc)` identical; stdio tool error carries the same text; no new adapter code in the diff (`git diff main -- src/` touches `artifacts.py` only) | ✅ pass |

**Spec success signal (Core snapshot, per-feature isolated builds under v0.7.3 vs HEAD wheels):** project-kickoff QACheck 6→26; graph-gates 5→30; lean-artifacts 8→15; tracker-handoff 5→21; every other building feature unchanged; the 11 features that drift do so identically under both (spec/qa shape unrelated to this change). project-kickoff `gate_health` lists 3 unverified, AC-3.4, AC-5.1, AC-5.4, whose own Result cells read `⚠️ not-verified-live`, `⚠️ pass (structural only)`, `deferred`; no passed AC is listed unverified because of table position. A1 holds on this snapshot: no multi-table Core file raised drift.

**Real-repo check (HEAD wheel on this repo):** `build --full` 729 code / 587 artifact entities; `staleness` fresh; `impact src/aspark_graph/artifacts.py --feature qa-multi-table --brief` returns `found: true`, 18 ACs across 4 stories; `story_trace US-1 --feature qa-multi-table` returns 6 ACs and 5 tasks. Its AC results derive from the previous `qa.md` and are superseded by this file.

## 3. Exploratory Findings

| # | Severity | Steps to reproduce | Expected vs. observed | Status |
|---|---|---|---|---|
| B1 | Minor | Run `uv run pytest -m slow tests/test_incremental_bench.py` 3 times at HEAD (and 4 times at `d334d25`) | Expected ≥50 % speedup every run. Observed one run below target at each commit (HEAD 46.6 %, baseline 49.6 %). Not caused by this change (diff only touches uncached artifact parsing) but it leaves NFR-2's "stays passing" clause unmet in a literal reading. Needs the user's decision: accept, or open a BACKLOG item for the bench noise margin | open |
| B2 | Minor | `mk` a repo whose `qa.md` has a valid AC table, then a fenced code block (```` ``` ````) containing `\| a \| b \|` / `\|---\|---\|` rows inside the same `## … Acceptance Criteria Verification` section; `aspark-graph build` (`e5`) | v0.7.3 builds it; HEAD fails the whole build with `QA table missing an 'AC' or 'Spec ID' column (found ['a', 'b'])` (rc=1). This is the documented spec C2/R1 trade-off (a non-verification table in the section now raises), and the message names the file; filed because the fence makes it a non-table to a human reader and the build is lost entirely | open |
| B3 | Minor | `build` any repo with a current-name `qa.md` (`s1`), read the `Feature` node's `coverage.recognized` | Expected `qa.md`; observed `qa-report.md` (identical under v0.7.3, so pre-existing and outside this feature). Not a result of this change | open |

Also probed, no defect: back-to-back tables with no blank line (`e2`) merge into one GFM table (second header and separator become data rows, AC-1.2 still read at order 3, no drift check on the second header); an exploratory-findings table in the next `##` section is not read.

## 4. Console & Network

- No browser. CLI stderr on every valid build: empty. Drift builds: one line, no traceback (AC-1.3).
- `import aspark_graph.server` prints a pydantic `IncompleteFieldDefinitionWarning` ('lifespan') to stderr from the unlocked install (pydantic 2.13.5, mcp 1.19.0); `serve` still boots and answers the stdio client. Pre-existing, outside this diff, not filed as a bug.
- Build on a dir without git history prints `No git history: inferred links are missing` (expected, v0.7.2 behaviour).

## 5. Verdict

Would I demo this to a stakeholder right now? For the feature itself, yes: the one thing it promises (read every table) works end to end on the installed wheel, drift is loud and identical across CLI and a real MCP client, and single-table output is byte-identical to v0.7.3 on six inputs. The verdict is still `failed` because NFR-2 says the benchmark "stays passing" and it failed once in 3 runs at HEAD (46.6 %), as it does on baseline (49.6 %, 1 of 4). I do not waive that; the user can accept B1 (it is not a regression) or direct a bench fix. No code change is needed from `/increment` for the ACs. Open: B1, B2, B3, all Minor.

---

## ✅ QA GATE

- [x] Every Must-story acceptance criterion verified by the §8 declared method (performed) and passed
- [ ] Every observable NFR verified and passed (NFR-2 benchmark clause: B1)
- [x] No open Blocker or Major bugs (Minor bugs B1, B2, B3 listed, not yet accepted by the user)
- [x] Console/stderr free of errors on the tested flows (N/A browser; see §4)
- [x] Tested on all agreed viewports (N/A: headless, §8)
- [x] Line budget respected: Ist ~72 / Soll ~130 (excluding HTML comments), self-reported
- [ ] Status set to `passed` (set to `failed`)
