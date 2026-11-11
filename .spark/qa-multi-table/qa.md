# QA Report: qa-multi-table

| | |
|---|---|
| **Phase** | Review (hands-on) |
| **Owner** | QA Tester (`/demo-day`) |
| **Input** | Branch `factory/issue-44` at ebe18a5 (review round 2 passed, includes T5-T7), `.spark/qa-multi-table/spec.md` (approved, incl. C4) |
| **Status** | `passed` |
| **Round** | 2 |
| **Date** | 2026-11-11 |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Verdict:** Yes. Every AC and NFR passes through the real CLI and in-process MCP functions; split QA reports count every table, malformed sub-tables are named including which one.
- **Open:** `1 open` - Blockers: none; Majors: none (Minors: see §3, B2)
- **Binding ruling:** §5 Verdict and the gate checklist below.
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/demo-day` and proceed - don't stop on it.

## 1. Test Environment

- **Mode:** live runs of the real CLI (`uv run aspark-graph`) and in-process MCP tool functions (`aspark_graph.server`), plus the test suites. No browser (N/A: headless); method is the declared one from `.spark/constitution.md` §8 (surface `no`). Nothing was verdict-ed by reading source. Anti-generosity standard applied (binary results; a partial check would be written `⚠ not-verified-live`; none was needed).
- **Under test:** checkout at ebe18a5, clean tree. Scratch repos in `/tmp/qa/` built from `tests/fixtures/current_names_repo` (each `.git`-marked, no confinement bypass) with rewritten `qa.md`: `ok` (`### US-1` table with `AC` header; `### US-2` table with `Spec ID` header, AC-1.2 pass, AC-2.1 fail; a `Foo|Bar` table with AC-9.9 under `## 3. Other`), `nores` (US-2 `Result` renamed `Outcome`), `noac` (US-2 `Spec ID` renamed `ID`), `single`, `nohead`.
- **Old code:** git worktree of `6681ded~1` (dd4b994), removed after use.
- **Network:** available; the unlocked fresh-install test ran live (5.6 s, not skipped).

## 2. Acceptance Criteria Verification

| Spec ID | Steps performed | Expected | Observed | Result |
|---|---|---|---|---|
| AC-1.1 | `build /tmp/qa/ok`; CLI `query gate_health demo`; MCP `gate_health`, `story_trace("US-2")`; same repo under the old worktree | QACheck for every row of both tables; later-table pass counts as verified | New: `unverified_acs` = `[AC-2.1]` (the failing row), AC-1.2 (table 2) verified; `story_trace` AC-2.1 `order` 2 (index runs on); CLI and MCP agree. Old code on the same file: `[AC-1.2, AC-2.1]`, i.e. the bug reproduces and is fixed | ✅ pass |
| AC-1.2 | `build --full` of 4 single-table inputs under `6681ded~1` and under HEAD, `cmp` graph.json (this repo via `git archive HEAD` + `.git`, `sample_repo`, `current_names_repo`, a valid single-table scratch `sing`); each also built twice. C4 edge (non-table block before the table) is pinned by a passing test, not byte-compared | byte-identical | all four old==new (621107 / 7169 / 6038 / 6038 bytes); double builds identical. The multi-table scratch differs from old, as intended | ✅ pass |
| AC-1.3 | `find_nodes AC-9.9` via CLI and MCP on `ok` | no QACheck from the `## 3. Other` table | `count 0` both; build rc 0 | ✅ pass |
| AC-2.1 | CLI `build` on `noac`; MCP `build_graph` on `noac`; also `single` | drift names file and column | `template drift in /tmp/qa/noac/.spark/demo/qa.md: QA table missing an 'AC' or 'Spec ID' column (found ['id', 'result', 'steps']) (table 2 of 2, under '### US-2')`, rc 1, no traceback. `single`: same message with no locator | ✅ pass |
| AC-2.2 | CLI `build` on `nores`; MCP `build_graph` on `nores` | drift names file and column | `... QA table missing a 'Result' column (found ['outcome', 'spec id', 'steps']) (table 2 of 2, under '### US-2')`, rc 1, no traceback. `nohead` (no `###` before table 2): `(table 2 of 2)` with no `under` clause | ✅ pass |
| AC-3.1 | grep `CLAUDE.md`, `.spark/constitution.md`, `.spark/BACKLOG.md` for first-table/first-QA-table wording | not stated as current | CLAUDE.md:42 says the limit "is lifted"; BACKLOG G6 `Status: umgesetzt`; constitution has no such claim | ✅ pass |
| NFR-1 | AC-1.2 round-trip plus double build of multi-table `ok` and `multi` | identical, proven against pre-change code | see AC-1.2; `multi` double-build identical | ✅ pass |
| NFR-2 | `git diff --stat 6681ded~1..HEAD -- src` | only `artifacts.py` | `src/aspark_graph/artifacts.py | 121` only | ✅ pass |

Suite evidence (declared §8 method): `uv run pytest` 395 passed; `uv run pytest -m slow` 4 passed (NFR-1 bench, MCP stdio smoke, sdist manifest, unlocked wheel install booting `serve`). Real-repo checks: `query staleness` fresh (63 files); `impact src/aspark_graph/artifacts.py` returns affected ACs; `story_trace US-2 --feature qa-multi-table` returns AC-2.1/AC-2.2 (read from the previous qa.md before this rewrite). Real Core files: `_parse_qa` over 34 `/opt/aspark/.spark/*/qa.md`: 25 parse (7 split reports yield checks), 9 raise "missing a '## ... Acceptance Criteria Verification' section" under both old and new code (unchanged, not table drift).

## 3. Exploratory Findings

| # | Severity | Steps to reproduce | Expected vs. observed | Status |
|---|---|---|---|---|
| B1 | Minor | Multi-table `qa.md` with a bad second table; `build` | Drift message should say which sub-table. r1: file and column only. r2: ends `(table 2 of 2, under '### US-2')` (CLI and MCP) | fixed r2 |
| B2 | Minor | In-process MCP `build_graph("/tmp/qa/nores")` | Expected a clean one-line error like the CLI. Observed: raw `TemplateDriftError` exception from the tool (the CLI is clean). Pre-existing, recorded in plan §5 as out of scope; outside every AC of this feature, but a user-visible CLI/MCP gap that now also carries the new drift messages | open |

## 4. Console & Network

No browser surface. Builds rc 0 except intentional drift cases (rc 1, one line, no traceback on the CLI). No unexpected stderr beyond the "No git history" notice on `.git`-marker-only scratch repos.

## 5. Verdict

Would I demo this to a stakeholder right now? **Yes.** A QA report split by `### US-n` yields checks for every table, `gate_health`/`story_trace` see them (the old code reproduced the under-count), single-table graphs are byte-identical to `6681ded~1`, and a malformed sub-table fails loudly naming file, column and which table. Open: B2 Minor (MCP raw drift exception, pre-existing). Not tested: browser (N/A), Windows/macOS, the C4 input byte-comparison (intentionally different, test-pinned).

---

## ✅ QA GATE

- [x] Every Must-story acceptance criterion verified hands-on and passed (CLI/MCP substitute, §1)
- [x] Every QA-relevant NFR verified and passed
- [x] No open Blocker or Major bugs (B2 Minor listed)
- [x] Tool output free of unexpected errors on the tested flows
- [x] Tested on all agreed surfaces (CLI, in-process MCP functions)
- [x] Line budget respected: Ist 66 / Soll ~130 (excluding HTML comments)
- [x] Status set to `passed`
