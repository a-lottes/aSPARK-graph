# Review Report: close-the-loop

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | The diff of `/increment` (`v0.1.0..HEAD`), `.spark/close-the-loop/plan.md` |
| **Status** | `changes-requested` |
| **Date** | 2026-07-14 |

## 1. Scope

Reviewed `git diff v0.1.0..HEAD` — 11 task commits (`T1..T11`) plus the bookkeeping
commit. Focus modules: `model.py`, `git.py` (new), `inference.py` (new), `build.py`,
`queries.py`, `cli.py`, `server.py`, `README.md`, and the 10 new/changed test files
under `tests/`.

Verified hands-on, not just read:
- `uv run pytest` → **99 passed** (green before and after my one fix).
- `uv run aspark-graph build .` → 307 code / 105 artifact / **155 inferred links**.
- `uv run aspark-graph query impact src/aspark_graph/inference.py --repo .` → **non-empty**
  (the exact query empty in v0.1.0). AC-1.1/AC-1.2 confirmed on the real repo.
- **Double-build byte-equality**: built `.` twice, `diff graph.json` → **byte-identical**.
  AC-1.5 holds on the real repo.
- `query staleness` (current, no false positive), `query impact --diff v0.1.0..HEAD`
  (names unknown non-source paths, still answers) — both behave as specified.

**Not reviewed / left to `/demo-day`:** AC-1.4 human-confirmation of link correctness
(a judgement call the plan assigns to a human) and AC-6.2 clean-environment install —
both correctly deferred by the plan's test strategy. MCP tool visibility inside a live
Claude Code session was exercised in-process via `fastmcp.Client` but not in a real
session.

## 2. Plan Conformance

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 | ✅ | `Confidence.INFERRED` value `"inferred"`, rank 0; `.rank()` map `{INFERRED:0, EXTRACTED:1, DECLARED:2}`. |
| T2 | ✅ | `git.py` pinned invocation `log --no-merges --name-only --format=...`, no date fields; every failure returns empty/typed, never raises. Word-boundary id match verified. |
| T3 | ✅ | `inference.infer_implements` adds `Task→File` at `INFERRED`, File-node guard, declared edges not overwritten; wired after `artifacts.extract_features`; `BuildReport.inferred_edges` added. |
| T4 | ✅ | Determinism test asserts `to_dict()` equality + byte-stable save; confirmed independently on the real repo. |
| T5 | ✅ | `story_trace` code section non-empty via inference; inferred tagged distinctly; graceful absence returns clean empty. |
| T6 | ✅ | Hermetic multi-story fixture proves correct attribution (cart→US-1 only, checkout→US-2 only). Real-repo `/demo-day` witness works (D3). |
| T7 | ✅ | `queries.staleness` compares File `hash` to on-disk sha256; CLI + MCP parity tested. |
| T8 | ✅ | Full v0.1.0 suite runs green against the three-tier enum. D1 sentinel regression caught and fixed here, not silently. |
| T9 | ✅ | `impact_diff` resolves range then reuses `impact`; unknown paths named; empty/invalid range → explicit message. See F2 for a range-ambiguity edge. |
| T10 | ✅ | README documents both link paths + tiers with examples; dangling `files:` ref safe (no crash, no fabricated edge). |
| T11 | ⚠️ | Fictional install path removed; only from-source `uv`/`uv run` documented. But the README retains a forward-looking `uvx` mention (see F4). |

All three recorded deviations (D1, D2, D3) are documented in plan §6. **D2 is accepted
by the plan as an honest limitation but is, in my judgement, under-severity — see F1.**

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Major | `inference.py:24-64`; observable in `queries.impact` | **Cross-feature id collision over-attributes badly on the real repo (D2).** Inference keys only on the bare `T<n>`/`US-<n>` ids in a commit message. When two `.spark/` features reuse the same numbering — this repo has `aspark-graph` and `close-the-loop`, both with `T1..`/`US-1..` — a commit like `T3: … (US-1)` links its files to **both** features' tasks/stories. On the real repo `impact(src/aspark_graph/inference.py)` reports both `aspark-graph:US-1` and `close-the-loop:US-1`, even though `inference.py` is a close-the-loop-only file that has nothing to do with the v0.1.0 story; `impact(model.py)` fans out to **10 stories across both features**. Why it matters: AC-1.4 says no "obviously wrong link presented" — attributing a close-the-loop file to a shipped v0.1.0 story is exactly an obviously wrong link, and the tool exists to answer "what must QA re-verify"; systematically doubling the story set with a wrong feature pollutes that answer. The weaker tier mitigates *trust*, not *wrongness* — every colliding link is `inferred`, so a consumer can't use tier to tell the right feature from the wrong one. A cheap, deterministic disambiguation was available and is even named in the plan's own §6 (feature-qualified commit ids, e.g. `close-the-loop/T3`) or restricting a commit's matches to the feature whose `.spark/` files that commit also touched. Neither was done; the collision ships live in the dogfood repo that is the spec's own success witness. Suggested fix: route back to `/increment`/`/sprint-plan` to add deterministic feature qualification (either read a feature marker from the commit, or intersect matched files with the touched-feature's task set). Not an obvious low-risk fix — has design impact — so left open. **Fixed** (fix-mode): `inference.py` now disambiguates by (a) **semantic pairing** — when a commit names both a task id and a story id it must match this feature's actual `task→story` mapping on *both* (so `T9 (US-3)` is close-the-loop's `T9→US-3`, never aspark-graph's `T9→US-4` nor its US-3-mapped `T7`), and (b) a **`.spark/<feature>/` co-touch tie-break** for the residual case of two features sharing the *same* pair. Verified on the real repo: aspark-graph-sourced `implements` edges dropped from 8 to **0**; `impact(model.py)` and `impact(inference.py)` are now close-the-loop-only. New test `test_f1_cross_feature_id_collision_disambiguated`. | fixed |
| F2 | Minor | `git.py:85` | **`git diff <range>` is invoked without a `--` path separator, so a bare filename passed as a range is silently misread as a pathspec.** `diff_files('.', 'README.md')` returns `([], None)` — an empty *success*, not the "invalid range" AC-3.3 promises for a malformed range. A user who types a filename instead of a range gets a silently-empty impact rather than a clear message. (Genuinely-bad refs like `no-such-ref..HEAD` are still caught correctly.) Also a minor argument-injection hardening gap: the range value reaches git's argv un-separated. Suggested fix: pass the range as `["diff", "--no-color", "--name-only", diff_range, "--"]` (or validate it resolves as a revision range via `git rev-parse` first) so pathspec interpretation can't swallow a fat-fingered range. **Fixed** (fix-mode): `diff_files` now passes `[..., diff_range, "--"]`, forcing the range to parse as a revision; a bare filename fails to resolve and is reported as an invalid range. New test `test_diff_files_bare_filename_is_not_silently_a_pathspec`. | fixed |
| F3 | Minor | `server.py:32,38,41,54,61,67,73,79,85` | **MCP query tools call `queries.load_graph(repo)` directly, so a query before any `build` raises `GraphNotBuiltError` to the MCP client, while the CLI catches it and prints a clean "run build first" message (AC-5.2).** The CLI≡MCP parity contract is about answers; this is an error-path asymmetry the parity test doesn't cover (it only tests the happy path and the CLI-side AC-5.2). Why it matters: the MCP surface is the *primary* consumer (agents), and it is the one that degrades worse. Suggested fix: catch `GraphNotBuiltError` in the MCP tools and return the same `{"found": False, ...}`-shaped dict the CLI surfaces. Touches 8 tools' error handling, so left open rather than fixed inline. **Fixed** (fix-mode): added a `_open(repo)` helper in `server.py` that returns `(graph, None)` or `(None, {"found": False, "error": …})`; every query tool now returns that clean dict on a query-before-build instead of raising. New test `test_mcp_errors.py`. | fixed |
| F4 | Nit | `README.md:49-50` | AC-6.1 asks the install section to make **no** `uvx`/PyPI claim. The install section itself is clean (only from-source `uv`; MCP via `uv run --directory`, not `uvx`), but a trailing note says "Once aspark-graph is published, a `uvx`-based one-liner will be documented here." It documents no runnable `uvx` command and creates no dead end, so it does not violate the *spirit* of US-6, but it is in tension with the letter of AC-6.1. Suggested fix: drop the sentence or move it to a clearly-labelled "Future / when published" section. | open |
| F5 | Nit | `server.py:22-28` | **(fixed by reviewer)** The MCP `build_graph` tool omitted `inferred_edges` from its return dict, while the CLI reports it in the build summary — a small CLI/MCP output-parity drift on the new build metric. Added `"inferred_edges": report.inferred_edges`. Re-ran `uv run pytest` → still 99 passed. | fixed |

## 4. What Was Checked

- [x] Correctness: logic does what the acceptance criteria demand — AC-1.1/1.2/1.5/1.6,
  2.1/2.2/2.3, 3.1/3.2/3.3, 4.1/4.2/4.3, 5.2/5.3 all verified in tests and (where
  applicable) by hand on the real repo. **AC-1.4 attribution correctness is compromised
  by F1.** AC-6.1 has a Nit tension (F4).
- [x] Error handling: git failures return typed/empty, never raise (verified on a non-git
  dir end-to-end). Build fails loud on template drift without leaking a traceback. One
  error-path asymmetry on the MCP side (F3) and one silent-empty range case (F2).
- [x] Security: no `shell=True`, no `os.system`, no shell interpolation anywhere; all
  subprocess args passed as a list. `diff_range`/`ids` reach git as argv, not a shell
  string. No secrets in code or logs. One minor un-separated-argv hardening note (F2).
- [x] Tests: exist, are meaningful (word-boundary `US-1`≠`US-10` explicitly asserted,
  correct-attribution asserted both ways, double-build byte-equality, graceful-absence,
  declared-beats-inferred no-regression), and pass — 99 green. Gap: no test covers the
  cross-feature collision of F1 (the fixtures use a single feature, so they can't).
- [x] Readability: the next developer will understand this — small, boring modules,
  derived/sorted ordering documented, deviations recorded.

## 5. Verdict

This is strong, disciplined work: the git-inference path is genuinely deterministic
(byte-identical double-build confirmed on the real repo, not just asserted in a
fixture), the offline/no-`shell=True` contract holds, the `inferred` tier is threaded
in as rank-0 so it can only ever lower a path's confidence and never mask a declared or
extracted result, the D1 sentinel regression was caught and fixed openly, and the two
Musts (US-1, US-2) demonstrably return non-empty, correctly-tiered results where v0.1.0
returned nothing. But it does not pass as-is. **D2 is under-graded: the cross-feature id
collision is not a benign tolerated false positive — on the tool's own dogfood repo it
systematically attributes close-the-loop files to shipped v0.1.0 stories (`model.py`
fans out to 10 stories across both features), and the weaker tier hides none of that
wrongness because every colliding link is `inferred`.** A deterministic fix was
available and is named in the plan's own deviation note; shipping the collision live on
the spec's own success witness makes F1 a Major, not a Minor. That single open Major
holds the gate. Fix F1 (route to `/increment` for feature-qualified disambiguation),
ideally address the F2/F3 minors, and this passes.

---

## ✅ REVIEW GATE

*All boxes checked → `/demo-day` may start. Any box open → back to `/increment`.*

- [x] No open Blocker findings
- [ ] No open Major findings (or explicitly waived by the user, with reason recorded here) — **F1 (D2 over-attribution) is open; only the user may waive a Major**
- [ ] All plan deviations documented and accepted — D1/D3 accepted; **D2 documented but its severity is disputed (F1)**
- [x] Test suite runs green
- [ ] Status set to `passed` — **status is `changes-requested`**
