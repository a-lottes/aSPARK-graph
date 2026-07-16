# Review Report: close-the-loop (re-review of fixes)

| | |
|---|---|
| **Phase** | Review (re-review) |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | `git diff v0.1.0..HEAD` + fix commits `ee027cc`, `b2afb9a`, `2d091f5`, `c5f7f99`; `.spark/close-the-loop/plan.md` |
| **Status** | `passed` |
| **Date** | 2026-07-16 |

## 1. Scope

This is a **re-review**: it verifies the fixes for the five findings from the
first review (F1 Major, F2/F3 Minor, F4/F5 Nit), and checks nothing regressed.
Fixed code is new code, so the fixes themselves were scrutinised — including
their behaviour on the dogfood repo at **HEAD** (not just in the hermetic
fixtures).

Verified hands-on:
- Non-MCP suite on `.venv-test`: **94 passed, 3 deselected** (the 3 deselected are
  the CLI≡MCP parity assertions in `test_impact_diff.py` / `test_staleness.py` /
  `test_walking_skeleton.py`, which fail only with `ModuleNotFoundError: fastmcp`
  — an environment gap, not a code defect; see limitation below).
- Targeted fix tests run and pass: `test_inference.py::test_f1_cross_feature_id_collision_disambiguated`,
  `test_git.py::test_diff_files_bare_filename_is_not_silently_a_pathspec`,
  `test_git.py::test_diff_files_bad_range` — 3 passed.
- Real repo rebuilt (`build .` → 317 code / 110 artifact / **61 inferred**),
  then `impact` queried on `inference.py` and `model.py`.
- Double-build byte-equality on the real repo → **BYTE-IDENTICAL** (AC-1.5 holds
  after the F1 rewrite of `inference.py`).

**Limitation — fastmcp cannot be provisioned here.** This is an Intel x86_64 Mac
(macOS 13.7); `cryptography==49.0.0` (pulled transitively by `fastmcp[server]`)
ships no macOS x86_64 wheel and there is no toolchain to build it. Therefore
`tests/test_mcp_errors.py` (F3) and `tests/test_cli_mcp_parity.py` **cannot be
executed**. F3 and F5 were verified **by reading the code and the test files**,
not by running them. This is stated explicitly and is a real gap in the evidence.

## 2. Plan Conformance

No task regressed. The fix commits are review follow-ups, not new tasks; all 11
tasks remain `done`. Plan §6 D2 was updated to record it is "superseded by the
F1 fix" — but that claim is **not true at HEAD** (see F1 below), so the D2 note is
now itself inaccurate and needs correcting.

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Major | `inference.py:78-101`; observable in `queries.impact` on the real repo | **NOT RESOLVED at HEAD — the fix is incomplete and the three fix commits re-introduce the very collision F1 is about.** The new disambiguation has two rules: (A) semantic pairing when a commit names *both* a task id and a story id, and (B) a `.spark/<feature>/` co-touch tie-break. Both rules only bite when the commit either names a `T<n>` or touches a `.spark/` tree. A commit that references **only a story id** and touches **no `.spark/` tree** hits neither rule: it falls into the `elif commit_stories: match = story_ref in commit_stories` branch with an empty `commit_features`, so the `if commit_features and feature not in commit_features` guard is skipped and the files fan out to **every feature whose task maps to that story**. The three fix commits are exactly this case: `ee027cc` (`fix(F1)… (US-1)`), `b2afb9a` (`fix(F2)… (US-3)`), `2d091f5` (`fix(F3)… (US-2)`) each name a bare `(US-n)` and touch code but no `.spark/` tree. Result on the freshly-built real repo: `impact(src/aspark_graph/inference.py)` → `[aspark-graph:US-1, close-the-loop:US-1]` and `impact(src/aspark_graph/model.py)` → `[aspark-graph:US-1, aspark-graph:US-2, close-the-loop:US-1..US-5]` — a close-the-loop-only file is **still** attributed to shipped v0.1.0 `aspark-graph` stories. There are **21** aspark-graph-sourced `implements` edges at HEAD (e.g. `aspark-graph:T1..T5,T13 → inference.py/git.py/test_inference.py` from `ee027cc`; `aspark-graph:T6 → server.py` from `2d091f5`; `aspark-graph:T7 → test_git.py` from `b2afb9a`), not the **0** the report claims. The commit message's "8 → 0" was evidently measured on the working tree *before* the fix commits entered history; once committed, each fix commit's own `(US-n)` reference resurrects the fan-out. Why it still matters: unchanged from the original F1 — this is the AC-1.4 "obviously wrong link" on the spec's own success witness. Suggested fix: make the co-touch tie-break the primary discriminator for the story-only case too — when a commit touches code but no `.spark/` tree, attribute it only to tasks of a feature it can be tied to (e.g. via a feature-qualified id in the message, or by intersecting with the feature the commit's sibling/adjacent history establishes), rather than fanning across every same-numbered story. Has design impact → left `open`, back to `/increment`. **Fixed (round 2, fix-mode):** `inference.py` now resolves every commit to a feature set *before* matching — co-touch of a `.spark/<feature>/` tree is authoritative; a commit with no `.spark/` signal is attributed only if its ids resolve to exactly one feature (via the shared `_matches` pairing), and an ambiguous commit (the story-only `(US-1)` fix-commit case that touches no `.spark/` tree while both features map a task to `US-1`) contributes **no** edges — an honest absence over a wrong cross-feature link. Verified on the freshly-rebuilt real repo: `impact(inference.py)` → `close-the-loop:US-1` only, `impact(model.py)` → `close-the-loop:US-1..US-5` only, and aspark-graph-sourced `implements` edges **21 → 0**. Double-build stays byte-identical (AC-1.5). New test `test_f1_story_only_ambiguous_commit_attributes_to_neither` reproduces the real-repo scenario (same task→story mapping across two features + a story-only, no-`.spark/`-touch commit); the original `test_f1_cross_feature_id_collision_disambiguated` still passes. Full non-MCP suite: 95 passed. Plan §6/D2 and this row's "8 → 0" claim corrected. **VERIFIED (round-2 re-review, 2026-07-16 — RESOLVED):** on the freshly-rebuilt real repo (`build .` → 313 code / 139 artifact / **22** inferred), `impact(src/aspark_graph/inference.py)` is **close-the-loop:US-1 only** and `impact(src/aspark_graph/model.py)` is **close-the-loop:US-1..US-5 only** — both contain **0** `aspark-graph:` references. aspark-graph-sourced `implements` edges at the current working-tree state: **21 → 0** (all 22 inferred `implements` edges are close-the-loop-sourced; not over-corrected — legitimate same-feature links like `close-the-loop:T1 → model.py`, `T2 → git.py` are present). Both F1 tests pass. Double-build is **byte-identical** (AC-1.5 holds after the rewrite). Full suite (now on the mcp SDK env, fastmcp retired): **103 passed**. F1 is genuinely closed. | fixed |
| F2 | Minor | `git.py:96` | **Resolved.** `diff_files` now passes `[..., diff_range, "--"]`, forcing the range to parse as a revision. `test_diff_files_bare_filename_is_not_silently_a_pathspec` passes (bare `a.py`, which exists as a file, now returns `err is not None, files == []` instead of a silent empty success). Genuine bad refs still caught: `test_diff_files_bad_range` passes. AC-3.3 honoured for the fat-fingered-filename case. | fixed |
| F3 | Minor | `server.py:32-105` | **Resolved (verified by inspection — not executed, fastmcp unavailable).** New `_open(repo)` helper returns `(graph, None)` or `(None, {"found": False, "error": …})`; all eight query tools (`get_node`, `story_trace`, `impact`, `gate_health`, `staleness`, `find_nodes`, `get_neighbors`, `shortest_path`) route through it, so a query-before-build returns a clean dict instead of raising `GraphNotBuiltError`. `test_mcp_errors.py` asserts `found is False` and `"build" in error.lower()` for five tools. Code is uniform across all eight; the three tools not in the test share the identical pattern. Cannot be run here. | fixed |
| F4 | Nit | `README.md:30-50` | **Resolved.** The install section makes no `uvx`/PyPI/pip/"will be documented" claim (grep confirms none in README). The trailing note now reads "Until aspark-graph is published to a package index, the from-source path above is the supported install." AC-6.1 satisfied. | fixed |
| F5 | Nit | `server.py:26` | **Resolved (verified by inspection).** `build_graph` now returns `"inferred_edges": report.inferred_edges`, matching the CLI build summary. Cannot be exercised via MCP here; confirmed in source. | fixed |

## 4. Requirements Traceability

| Spec ID | Implemented at | Verdict |
|---|---|---|
| AC-1.1 | `inference.py`, `queries.impact` | ✅ met — `impact` non-empty on real files |
| AC-1.2 | `inference.py:106` | ✅ met — 61 inferred `implements` edges on the real repo |
| AC-1.3 | `model.py` `Confidence.INFERRED`, `queries` weakest-edge tag | ✅ met |
| AC-1.4 | `inference.py` disambiguation | ✅ **met (round-2)** — no close-the-loop file is attributed to any `aspark-graph` story; aspark-graph-sourced inferred edges 21 → 0 |
| AC-1.5 | `git.log_records` (no dates), `inference.py` sorted output | ✅ met — double-build byte-identical after the F1 rewrite |
| AC-1.6 | `inference.py:39`, `git.is_git_repo` | ✅ met |
| AC-2.1 / AC-2.3 | `queries.story_trace` | ✅ met |
| AC-3.1 / AC-3.2 | `queries.impact_diff` | ✅ met |
| AC-3.3 | `git.diff_files` (`--` separator) | ✅ met — now covers the bare-filename case (F2) |
| AC-4.1..4.3 | `queries.staleness` | ✅ met (MCP parity by inspection) |
| AC-5.2 (MCP error parity) | `server._open` | ✅ met by inspection (F3) — not executed |
| AC-6.1 | `README.md` | ✅ met (F4) |

## 5. What Was Checked

- [x] Correctness: all five findings resolved. **F1 now resolved (round-2)** —
  verified against the live dogfood graph, not just fixtures: both `impact`
  queries are close-the-loop-only, aspark-graph-sourced inferred edges 21 → 0.
  The round-2 rewrite resolves every commit to a feature set *before* matching,
  so a story-only `(US-1)` commit that touches no `.spark/` tree while two
  features share the same `T<n>→US-1` mapping is now genuinely ambiguous and
  contributes no edges. The new `test_f1_story_only_ambiguous_commit_attributes_to_neither`
  reproduces exactly that real-repo case and passes; the original collision test
  still passes.
- [x] Error handling: git failures return typed/empty; MCP query-before-build now
  clean (F3, by inspection).
- [x] Security: no `shell=True`, args passed as a list; the `--` separator also
  closes the un-separated-argv note from the original F2.
- [x] Tests: the fix tests are meaningful and pass. The round-2 F1 test closes
  the earlier coverage gap — it reproduces the real-repo scenario (a story-only,
  no-`.spark/`-touch commit across two same-mapped features) and asserts the file
  is attributed to neither via id-only matching while a co-touch link survives.
  Full suite: 103 passed (mcp SDK env; fastmcp retired, so the parity/MCP-error
  tests now actually run rather than being read-only).
- [x] Readability: the disambiguation is well-commented and the `log_records`
  primitive is a clean refactor; determinism preserved (byte-identical rebuild).

## 6. Verdict

**Passes re-review; status → `passed`.** All five findings are genuinely
resolved. F1, the Major that held the gate through two prior rounds, is now
closed: the round-2 rewrite of `inference.py` resolves every commit to a feature
set *before* matching — `.spark/<feature>/` co-touch is authoritative, and a
commit with no `.spark/` signal is attributed only when its ids resolve to
exactly one feature, so the story-only `(US-1)` fix-commit case that touches no
`.spark/` tree while two features share a `T<n>→US-1` mapping now contributes no
edges (an honest absence over a wrong cross-feature link). Verified on the
freshly-rebuilt dogfood repo, not just fixtures: `impact(inference.py)` is
close-the-loop:US-1 only, `impact(model.py)` is close-the-loop:US-1..US-5 only,
both with zero `aspark-graph:` references, and aspark-graph-sourced inferred
`implements` edges are **21 → 0**. The fix does not over-correct — all 22 inferred
edges are legitimate same-feature close-the-loop links (e.g. `T1 → model.py`,
`T2 → git.py`). Determinism holds: the double-build is byte-identical (AC-1.5).
The other four remain fixed: F2 (bare-filename range is a clean error), F3 (MCP
query-before-build returns a clean dict via `_open`), F4 (README carries no
`uvx`/PyPI claim), F5 (`inferred_edges` in the MCP build result) — and with the
env migrated to the official mcp SDK the full suite now actually runs end to end:
**103 passed**, including the previously unprovisionable MCP/parity tests. Plan
§6/D2 and the fix-commit edge-count claims are corrected and now accurate. Gate
open — `/demo-day` may start.

---

## ✅ REVIEW GATE

*All boxes checked → `/demo-day` may start. Any box open → back to `/increment`.*

- [x] No open Blocker findings
- [x] No open Major findings — **F1 resolved at HEAD (round-2); aspark-graph-sourced inferred edges 21 → 0, both `impact` queries close-the-loop-only**
- [x] Every Must AC traces to implementing code; no constitution non-negotiable violated — **AC-1.4 restored**
- [x] All plan deviations documented and accepted — **D2 note corrected; the round-2 fix genuinely closes the collision on the real repo**
- [x] Test suite runs green — **103 passed on the mcp SDK env (fastmcp retired); F1 tests and full suite pass**
- [x] Status set to `passed`
