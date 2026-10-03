# QA Report: shallow-clone-warning

| | |
|---|---|
| **Phase** | Review (hands-on) |
| **Owner** | QA Tester (`/demo-day`) |
| **Input** | Wheel of `feat/shallow-clone-warning` at `5a1e3c5` (clean tree), `.spark/shallow-clone-warning/spec.md` (approved, round 2) |
| **Status** | `passed` |
| **Round** | 1 |
| **Date** | 2026-10-03 |

<!-- Handoff: read this block first, the numbered sections below by exception. Whoever
     writes to this report updates it in the same edit that closes or re-rules a bug:
     overwrite in place, never append. The block holds one current state, never a
     per-round log; a stale block is a defect, not a cosmetic issue.

     Re-test: bump `Round` yourself (only the owner bumps it) at the start of the pass,
     then overwrite every section below in place — §1 Test Environment, §2 AC
     Verification, §3 Exploratory Findings, §4 Console & Network, §5 Verdict and the
     gate checklist all hold exactly one current state, never a `## Round N` heading or
     a second gate. History lives in git, not in this file. -->

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Verdict:** Yes. Every AC and every QA-owned NFR passes hands-on over the installed wheel, CLI and live MCP; a shallow build now only loses `inferred` links, and every non-shallow build is byte-identical to published 0.7.1.
- **Open:** `2 open` — Blockers: none; Majors: none (Minors: see §3; both pre-existing on v0.7.1 code)
- **Binding ruling:** §5 Verdict and the gate checklist below — the only binding location; there is no other round to point to
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/demo-day` and proceed — don't stop on it.

## 1. Test Environment

- **App URL / browser / viewports:** N/A. `aspark-graph` is a Python CLI plus an MCP stdio server with no UI. No constitution exists, so no §8 QA method is declared. **Override:** on 2026-10-03, at the plan gate, the user approved hands-on CLI/MCP QA in place of the browser check, as in the v0.7.1 loops (`.spark/current-artifact-names/qa-report.md` §1). Nothing was tested by reading source.
- **Under test:** `uv build --wheel` (Python 3.11) of `5a1e3c5` → `aspark_graph-0.7.1-py3-none-any.whl` (version not yet bumped to 0.7.2), installed in a fresh 3.11 venv under `/private/tmp/claude-501/…/scratchpad/qa/new`. **Baseline:** PyPI `aspark-graph==0.7.1` in a second venv (`…/qa/old`); `uvx --from aspark-graph==0.7.1` gave byte-identical graph.json on a check fixture. git 2.39.2, macOS 13.
- **MCP:** a real `aspark-graph serve` subprocess per call batch, driven by the `mcp` stdio client; `build_graph` always ran on a twin copy of the CLI's input.
- **Test data (all scratch):** own fixtures, not the suite's: US-1 origin (3 commits, `T1` in commit 2), US-5 origin (6 commits, 4 files; tip `T1: implement a` touches only `a.py`; c4 `T2: work on b` is the depth-3 boundary), monorepo origin (`proj/` subproject), root-commit repo (`T1: initial import`), merge-tip origin, SHA-256 origin. Clones of this repo at `5a1e3c5` (non-merge, message names no task) and at `c83517a` (non-merge, names T3, T10–T16).
- **aspark-graph tool file:** graph stale, treated as absent; scoped by hand from the spec.

## 2. Acceptance Criteria Verification

| Spec ID | Steps performed | Expected | Observed | Result |
|---|---|---|---|---|
| AC-1.1 | `--depth 1` clone of US-1 origin; `build . --full` | notice line exactly once on stderr | stderr bytes == the AC-1.1 line + `\n`, count 1, ASCII only | ✅ pass |
| AC-1.2 | Same, plus US-5 depth 1/3, vs 0.7.1 on twin clones | rc 0; v0.7.1 stdout format; only inferred count differs | rc 0 everywhere; 2 stdout lines; US-1 shallow stdout identical; US-5 d1 `4 inferred link(s)` segment gone (0.7.1 omits it at 0 too), d3 5→2; nodes and non-inferred edges equal 0.7.1 | ✅ pass |
| AC-1.3 | Full clone of US-1 origin, new vs 0.7.1 | stderr equals 0.7.1 | both empty | ✅ pass |
| AC-1.4 | Shallow clones: `--full`, `--full` again, then incremental | notice each run | 1 notice on each of 3 runs (US-1, US-5 d1/d3, subdir-of-shallow) | ✅ pass |
| AC-1.5 | This repo `--depth 1` at `5a1e3c5` and at `c83517a`; `git fetch --unshallow`; incremental rebuild, then `--full` | no notice; `impact src/aspark_graph/queries.py` equals full clone | stderr empty; 4 stories / 17 ACs, lists incl. confidence equal; graph.json `cmp`-equal to the full clone, both rebuild modes, both tips. Same on US-5 d1/d3 | ✅ pass |
| AC-1.6 | Detached `HEAD~1`; `--single-branch --branch main` (origin has `side`); also `--filter=blob:none` | no notice | none; bytes equal 0.7.1 | ✅ pass |
| AC-1.7 | `--depth 1` clone of an origin with spec but no plan | no notice | none; MCP both `false`; 0 git calls (shim) | ✅ pass |
| AC-2.1 | `build_graph` on twin of US-1 shallow | `shallow_history: true`, `no_git_history: false` | exactly that (JSON booleans) | ✅ pass |
| AC-2.2 | `build_graph` on full clone, new vs 0.7.1 server | both `false`; v0.7.1 keys/values unchanged | 6 v0.7.1 keys, same values (bar `graph_path`), 2 new keys appended, both `false`; same on all 17 fixtures except `inferred_edges` on US-5 shallow | ✅ pass |
| AC-2.3 | `build_graph` on shallow no-task twin | both `false` | both `false` | ✅ pass |
| AC-2.4 | 17 fixtures × 3 CLI runs vs MCP twin, checked by script; plus this repo d1, spaces path, missing git, GIT_DIR | notice ⇔ key, never both, bytes equal | 0 violations; graph.json CLI≡MCP on all 17 and on this repo d1 | ✅ pass |
| AC-3.1 | Real stderr of US-5 d3 and no-git fixture vs `git show HEAD:README.md` | both quoted exactly; names keys and remedy | both lines are substrings; `shallow_history`, `no_git_history`, `git fetch --unshallow` present; text says shallow shows fewer links, never extra | ✅ pass |
| AC-4.1 | Copy of US-1 origin without `.git`, `build .` | no-git line once, rc 0 | exact bytes, once, rc 0 | ✅ pass |
| AC-4.2 | `build_graph` on twin | `no_git_history: true`, bytes equal | `(false, true)`, `cmp` equal | ✅ pass |
| AC-4.3 | No-git copy without plan | no notice, key `false` | none; both `false` | ✅ pass |
| AC-4.4 | Build `proj/` of a full monorepo clone | no notice, keys `false` | none; both `false`; bytes equal 0.7.1 | ✅ pass |
| AC-5.1 | US-5 `--depth 1`: `--full`, `--full`, incremental | no inferred edge from T1 | 0 inferred edges each run (0.7.1: T1→a,b,c,d) | ✅ pass |
| AC-5.2 | US-5 d1 and d3 vs full clone at same HEAD | inferred ⊆ full; non-inferred equal | d1 ∅ ⊆, d3 {T1→a, T2→c} ⊆ {T1→a, T2→b, T2→c, T3→d}; non-inferred lists equal | ✅ pass |
| AC-5.3 | US-5 `--depth 3` (shallow file = c4 `T2: work on b`) | c4 adds nothing; c5/c6 as on full | exactly {T1→a (c6), T2→c (c5)}; no T2→b (0.7.1: T2→a,b,c,d) | ✅ pass |
| AC-5.4 | Full, detached, single-branch, blob:none, subdir-of-full, no-git (±task), US-5 full, root-commit, this repo full: new vs 0.7.1 | byte-identical | `cmp` equal 10/10; stdout equal; stderr equal minus notice | ✅ pass |
| AC-5.5 | Full clone whose root commit `T1: initial import` adds x/y/z.py | edges present, bytes = 0.7.1 | T1→x,y,z inferred; byte-identical | ✅ pass |
| AC-5.6 | Re-derived (condition b, Must AC). This repo `--depth 1` at `c83517a…` (1 parent `19a5bef`) and at `5a1e3c5…` (1 parent `c83517a`); `query impact src/aspark_graph/queries.py` | subset of full clone | both tips 2 stories / 8 ACs ⊆ 4 / 17 (set check, both levels). 0.7.1 on the `c83517a` d1 clone: 1470 inferred, 19 / 101, not a subset. At `5a1e3c5` 0.7.1 also gives 2/8 (tip names no task) | ✅ pass |
| NFR-1 | `git` shim on PATH logging argv; timing on a full clone of this repo, 2 warm-ups, 7 interleaved `build --full` | ≤ v0.7.1 calls + 1, once; < 5% | Task build 3 calls (new `rev-parse … --git-path shallow`, `rev-parse`, `log`) vs 0.7.1's 3; no-Task 0 (0.7.1: 3). Median 0.744 → 0.766 s, +3.0% (load avg ~5) | ✅ pass |
| NFR-2 | Origin set to `https://user:s3cret@github.com/…`; `sandbox-exec (deny network*)` (control: curl 200 outside, rc 6 inside); build US-5 d1/d3, US-1 shallow, subdir-shallow, `--full` and incremental | builds offline; no URL/path in notice or keys | rc 0 all 8, notice shown, d3 still 2 inferred; notices are constants, keys booleans; `s3cret`/`github.com` absent from `.aspark-graph/` | ✅ pass |
| NFR-3 | Searched captured stderr for `\x1b` | plain text | 0 ESC bytes, ASCII only | ✅ pass |
| NFR-4 | All fixtures: `Traceback` search; shallow builds twice + incremental; edges diffed vs 0.7.1 | non-shallow bytes = 0.7.1; shallow only loses inferred; deterministic; never raises | see AC-5.4; shallow: 0 edges gained, nodes and non-inferred equal 0.7.1; bytes equal across runs; no traceback in any CLI run or MCP log | ✅ pass |
| NFR-5 | Every CLI run: count notice lines; stdout grep; shallow + legacy `qa-report.md` | ≤ 1 notice, stderr only, stdout untouched | ≤ 1 history notice always; stdout always 2 lines, never a notice; `Ignored …` line then shallow line, MCP `ignored_legacy_files` intact | ✅ pass |
| NFR-6 | Same as AC-2.4 (behavioural parity; layering is Review's) | CLI ≡ MCP | 0 violations | ✅ pass |

## 3. Exploratory Findings

| # | Severity | Steps to reproduce | Expected vs. observed | Status |
|---|---|---|---|---|
| B1 | Minor | Full or `--depth 1` clone of this repo at `5a1e3c5` (or `b215790`); `uv run --extra dev pytest -q -m slow tests/test_incremental_bench.py` on a busy Mac (load avg ~5) | Expected the 3 slow tests green (review: "slow 3 passed"); observed `test_nfr1_incremental_at_least_50_percent_faster` fails 7/7 at HEAD (37–40%) and 3/3 at `b215790` (37–39%). Load-sensitive benchmark, pre-existing, not a regression. Main suite: 387 passed in both the full and the depth-1 checkout | open |
| B2 | Minor | Monorepo: commit `T1: implement p` touching `proj/src/p.py`; full clone; `build proj` (0.7.1 the same) | Expected T1→`src/p.py` inferred; observed none: git paths are top-level-relative (`proj/src/p.py`), node ids build-root-relative (`file:src/p.py`). A subproject never gets inferred links and gets no notice either. Pre-existing, outside this spec (§6); BACKLOG candidate | open |

Probed, no bug: path with spaces and Unicode; `cd clone && build .`; symlink to a clone; linked worktree of a depth-3 clone (boundary resolved, same 2 edges); `--shallow-since` with real dates; `--shallow-exclude`; `--depth 1000` (git reports not shallow, no notice); `--deepen=2` then incremental (edges match depth 3); a full clone re-shallowed by `fetch --depth 1` with an existing graph (incremental drops the inferred edges, notice shown); a 2-line graft list from `--no-single-branch` (both tips skipped); a grafted merge tip `T1: merge feature` (new ∅, 0.7.1 T1→a,b,c); SHA-256 repo depth 2 (64-hex boundary skipped). C12 graft lists: non-hex → no-git notice, `(false, true)`, 0 edges (R9 ruling); 40 zeros or empty → shallow notice, 0 edges; no traceback. Zero-commit repo: no notice, bytes = 0.7.1 (§6). No `git` on PATH: no-git notice and `no_git_history: true` on a shallow clone (A8). `GIT_DIR` at a shallow `.git`: shallow notice even on a no-git dir, which follows git's own view; no crash. `build_graph` on a missing path: `outside_confinement` answer, unchanged.

## 4. Console & Network

No browser, console or network surface. Equivalent: stderr, exit codes, MCP results. Every build exited 0 except an intentional malformed-`qa.md` fixture (drift error, same on 0.7.1). The MCP server log (`…/qa/mcp-stderr.log`) holds only the pydantic-settings `IncompleteFieldDefinitionWarning` (0.7.1 the same) and `Processing request` lines, 0 tracebacks. No `isError` result. Network: none needed; the build passes under a network-deny sandbox (NFR-2).

## 5. Verdict

Would I demo this to a stakeholder right now? **Yes.** On a `--depth 1` clone of this repo at a non-merge tip that names tasks, 0.7.1 inflates `impact src/aspark_graph/queries.py` to 19 stories / 101 ACs. The new build prints the approved notice, MCP says `shallow_history: true`, and the answer is 2 / 8, a subset of the full clone's 4 / 17. `git fetch --unshallow` plus a rebuild restores 4 / 17, with graph.json byte-equal to the full clone. Every non-shallow input I built is byte-identical to the published 0.7.1. The git call budget is unchanged. The build works offline and never crashed, however odd the input. B1 and B2 are Minor and pre-existing on v0.7.1 code. Not tested: Linux and Windows, git < 2.15 (R1), `--filter=tree:0` (A6), and the 0.7.2 version bump, since `pyproject.toml` still says 0.7.1 and that belongs to `/go-live`.

---

## ✅ QA GATE

*All boxes checked → `/go-live` may start. Any box open → back to `/increment`, then re-run
`/demo-day`. On re-test, edit this same checklist in place — never duplicate it as a second gate.*

- [x] Every Must-story acceptance criterion verified hands-on (installed wheel, CLI and live MCP; user-approved substitute for the browser, §1) and passed
- [x] Every QA-relevant NFR verified and passed (NFR-1–6)
- [x] No open Blocker or Major bugs. Minors B1 and B2 are listed. Both are pre-existing on v0.7.1 code; the user deferred both to BACKLOG G11 at this gate (2026-10-03), together with A6
- [x] Tool output free of unexpected errors on the tested flows (no traceback; MCP log has only the known pydantic warning)
- [x] Tested on all agreed surfaces (CLI, MCP stdio, wheel venv, `uvx` baseline; no viewports apply)
- [x] Line budget respected: Ist 92 / Soll ~130 (excluding HTML comments)
- [x] Status set to `passed`
