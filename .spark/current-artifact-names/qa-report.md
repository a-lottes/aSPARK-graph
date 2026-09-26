# QA Report: current-artifact-names

| | |
|---|---|
| **Phase** | Review (hands-on) |
| **Owner** | QA Tester (`/demo-day`) |
| **Input** | Release candidate for v0.7.1 (uncommitted tree, branch `feat/current-artifact-names`), `.spark/current-artifact-names/spec.md` |
| **Status** | `passed` |
| **Round** | 2 |
| **Date** | 2026-09-25 |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Verdict:** Yes, with the known limits: every Must AC and NFR passes hands-on on the rebuilt RC, and B1 is fixed and verified on real Core/steamcore data. Release notes must name B2.
- **Open:** `0 open` — Blockers: none; Majors: none open (`B2` accepted by user, deferred to BACKLOG G6, not counted; `B1` fixed r2); Minors `B3`-`B6` deferred to G8 (see §3)
- **Binding ruling:** §5 Verdict and the gate checklist below
- **On conflict:** the numbered body below wins for everything except `Status`.

## 1. Test Environment

- **Browser:** does not apply. `aspark-graph` is a Python CLI plus an MCP stdio server with no UI (spec §8, NFR-6 N/A); the user approved hands-on CLI/MCP QA of the installed RC in its place, as in `.spark/aspark-graph/qa-report.md` §1. No constitution, so no declared QA method. Nothing was tested by reading source.
- **Artifact under test (round 2):** `uv build --wheel` re-run on the current working tree (includes the B1 fix, C14/T5c; `aspark_graph-0.7.0-py3-none-any.whl`, version bump not applied) into a fresh Python 3.11 venv, plus `uvx --from <wheel>`. Round 1 used the pre-fix wheel.
- **MCP:** real `aspark-graph serve` subprocess driven by the `mcp` stdio client (9 tools listed); each scenario built via CLI and via `build_graph`.
- **Baseline:** published `aspark-graph==0.7.0` via `uvx`.
- **Test data (scratch, 40+ repos):** current-only, legacy-only, both names (3 features), mixed, each of review/qa/release shadowed alone, malformed qa/review (drift, both names), `Spec ID` / `AC` / neither headers, result cells `⚠️ …passed…`, `❌ … pass-worthy`, plain pass, NFR rows, empty files, directory-named `qa.md`, Unicode, CRLF, release-only, symlinks. Fresh round-2 clones of Core (e1a0005) and steamcore (bf1b3e0); round-2 probes: escaped pipe, bare pipe, escaped pipe before the closing pipe (with and without a space), CRLF, escaped pipe in review.md vs legacy review-report.md on 0.7.0. A clone of this repo minus `.spark/.guard/` and the `aSPARK-graph` symlink.

## 2. Acceptance Criteria Verification

| AC | Steps performed | Expected | Observed | Result |
|---|---|---|---|---|
| AC-1.1 | Built `current` (qa.md, `Spec ID` header, no qa-report.md); `query story_trace US-1` | AC-1.1 has a passing QA check | `latest_result: pass`, one QACheck | ✅ pass |
| AC-1.2 | `gate_health demo` on `current` | `unverified_acs` empty | `[]` (also `[]` on steamcore game-loop, rendering-core, start-screen, text-rendering) | ✅ pass |
| AC-1.3 | Built `failing` (AC-1.2 `❌ fail`); `gate_health` | AC-1.2 listed unverified | `[AC-1.2]`; story_trace shows `fail` | ✅ pass |
| AC-1.4 | `get_node feature:demo` on `current` | qa_status passed | `qa_status: passed` | ✅ pass |
| AC-2.1 | `gate_health` on `current` (F1 open, F2 fixed) | open_findings lists F1 only | `[F1]` | ✅ pass |
| AC-2.2 | `get_neighbors finding:demo:F1` on current and legacy repos | `found_in` edge to `file:src/demo/app.py`, same as legacy | identical edge in both | ✅ pass |
| AC-2.3 | `get_node feature:demo` | review_status passed | `review_status: passed` | ✅ pass |
| AC-3.1 | `get_node` on `current` and on `only_release` | release_status handed-off | `handed-off` in both | ✅ pass |
| AC-3.2 | Prose Version cell in release.md vs release-notes.md; Unicode version | verbatim, identical | `v0.12.0 (proposed, pr mode — no tag)` in both; `v1.0.0 — 日本語 🚀` verbatim | ✅ pass |
| AC-4.1 | `both`: qa.md all pass vs qa-report.md all fail; `gate_health` and find_nodes | only qa.md counts | `unverified_acs: []`, three `pass` checks, no `fail` check | ✅ pass |
| AC-4.2 | Same repo: legacy review has F7-F9 open, legacy release is `blocked`/`v9.9.9` | none of it in graph | F5/F7/F8/F9 count 0; release `handed-off`, `v0.12.0` | ✅ pass |
| AC-4.3 | `mixed` (qa.md + review-report.md + release-notes.md) | QA checks, findings and release present, no notice | 3 QACheck, F1 open, release read; stderr empty | ✅ pass |
| AC-4.4 | CLI build of `both` (3 features, dirs created zeta, demo, alpha), repeated, plus a copy created in reverse order | exit 0; one `Ignored` line per shadowed file, stable order | exit 0; 7 lines sorted alpha, demo, zeta, then review, qa, release; identical on every run and in the reverse-created copy | ✅ pass |
| AC-4.5 | Same repos through MCP `build_graph` | `ignored_legacy_files` equals the CLI's paths | equal on `both`, `both_a` and each single-file shadow; `[]` where nothing shadowed | ✅ pass |
| AC-4.6 | `both_a` vs `both_current_only`, `cmp` graph.json | byte-identical | identical (sha 61a8b1de…) | ✅ pass |
| AC-5.1 | Fresh clone of tree + own legacy trail (minus `.spark/.guard/`, symlink); `uvx --from aspark-graph==0.7.0 … build . --full` vs RC wheel `build . --full`; `cmp`; re-run with the final round-2 reports (see §5) | byte-identical | identical with the final qa-report.md and review-report.md in the trail; 1071 code / ~428 artifact entities, both stderr empty, no `Ignored` lines (sha not quoted: it changes with every edit of this report) | ✅ pass |
| AC-5.2 | qa.md without section, with `Foo` header, `Criterion` header; review.md without Findings; empty file; each also under legacy name; CLI and MCP | named drift error, exit 1 | `template drift in …/qa.md: … missing an 'AC' or 'Spec ID' column` (or missing section), path names qa.md/review.md; legacy names give the same text; MCP `isError` with same message | ✅ pass |
| AC-5.3 | `current` vs `legacy_specid` (same content renamed), plus `crlf`, `crlf_lf`, `mixed` | byte-identical | all sha 61a8b1de… | ✅ pass |
| AC-5.4 | RC on fresh Core and steamcore copies (`build <copy> --full`), then `gate_health` per feature | no drift, QACheck and Finding > 0 | Core: 818 artifact entities, 165 QACheck = pass 143 / unknown 11 / fail 11 (dev's counts confirmed). steamcore: 893, 261 QACheck = pass 251 / unknown 10. Exit 0, no notices; MCP `build_graph` bytes equal CLI on both. Situational-lenses AC-5.2 and AC-6.1 now `fail` (real ❌ rows); analog-joystick-input AC-1.5 now `pass`, its AC-3.1-3.4 stay unverified (rows are `⛔ blocked`, legitimate). Of 24 Core rows with an escaped pipe, those in the first table now read their real result steamcore game-loop, game-state-management, highscore-system, rendering-core, start-screen, text-rendering: `unverified_acs: []`. B2 still applies (accepted) | ✅ pass |
| AC-6.1 | Read README and CLAUDE.md for language statements and "six" | five languages named, no "six" count | README 231-235, 256, 276-278 name the five; no "six" (CLAUDE.md:32 "six non-guarantees" is SECURITY.md) | ✅ pass |
| AC-6.2 | Read `CLAUDE.md` lines 8 and 28 | five languages | line 8 lists the five; line 28 "five languages supported" | ✅ pass |
| AC-6.3 | Read README "Artifacts read"; compared its message text with real CLI stderr | file names, current wins, message matches | table names all six files; `Ignored … (qa.md takes precedence)` and `ignored_legacy_files` match the real output character for character | ✅ pass |
| C13 rows | `find_nodes` QACheck for the five named rows | no longer `pass` | metrics-script-removal AC-1.2/4.1, situational-lenses AC-6.1, steamcore highscore-system AC-1.5: `unknown`; project-kickoff AC-5.1 has no QACheck (B2) but is listed unverified; situational-lenses AC-6.1 is now `fail` (a ❌ row, correct); synthetic `⚠️ …passed`, `❌ … pass-worthy` read unknown/fail, plain `pass` reads pass | ✅ pass |
| NFR-1 | `--full`, incremental and `--full` builds twice on `current` and `both`; removed/restored qa.md between incremental builds | identical bytes and notice order | identical; incremental picked up the swap both ways | ✅ pass |
| NFR-2 | AC-5.1 byte-identity; `pytest` in the clone via `uv run --extra dev`; `git diff --numstat tests/` | legacy identical, suite green, tests only added | 319 passed in the clone; existing test files show 0 deleted lines (43 and 25 lines added) | ✅ pass |
| NFR-3 | Every scenario built via CLI then MCP; compared `graph.json` bytes and ignored lists | equal | equal on all 30+ building scenarios | ✅ pass |
| NFR-4 | `uv run --extra dev pytest -m slow` in the clone | passes unmodified | 3 passed | ✅ pass |
| NFR-5 | Feature folders only; symlinked qa.md pointing outside the repo, on 0.7.0 and RC | no new read surface | same symlink-following as 0.7.0 for the legacy name (see B6) | ✅ pass |
| NFR-6 | N/A, headless | N/A | N/A | N/A |
| NFR-7 | Notices per shadowed file; artifact count on current-name trail | named per file; count rises | one line per file; 0.7.0 vs RC on the same copies: 8 vs 13 entities (demo), 483 vs 818 (Core), 494 vs 893 (steamcore) | ✅ pass |

## 3. Exploratory Findings

| # | Severity | Steps to reproduce | Expected vs. observed | Status |
|---|---|---|---|---|
| B1 | Major | Fixed by C14/T5c. Round-1 repro: a `qa.md` verification row whose Steps or Observed cell holds a GFM escaped pipe and ends in a `✅ pass` result cell; build; `gate_health`. Real: steamcore analog-joystick-input AC-1.5 | Round 2, CLI and MCP: the round-1 row reads `pass`; steamcore AC-1.5 `pass` (not in `unverified_acs`); shifted Core rows read their real result. Bare (unescaped) pipe still separates cells (row reads `unknown`); escaped pipe before the closing pipe, with and without a space, reads `pass`; CRLF identical to LF (sha 61a8b1de…); an escaped pipe in a review.md Finding cell keeps v0.7.0 behaviour (status shifted, same bytes as 0.7.0 on the legacy name), so the scope guard holds | fixed r2 (verified) |
| B2 | Major | Build Core copy; `gate_health project-kickoff` | expected the passed ACs of US-2..US-5 verified; observed only the first verification table is read (6 QACheck for 26 ACs), 20 passed ACs listed unverified; same for graph-gates, lean-artifacts, situational-lenses. Known: plan Q1, BACKLOG G6. Re-confirmed round 2 (project-kickoff: 6 QACheck for 26 ACs); not a regression | accepted by user (G6); release notes name it |
| B3 | Minor | `mkdir .spark/demo/qa.md` (or `review.md`/`release.md`), run `build` | expected a clean one-line error; observed uncaught `IsADirectoryError` traceback (CLI exit 1), raw MCP error. 0.7.0 does the same for `qa-report.md`; new: a directory `qa.md` now also blocks a valid `qa-report.md` beside it | deferred to G8 |
| B4 | Minor | Result cell `✅ pass (was ❌ fail)` | observed `fail` because `❌` wins anywhere in the cell (matches C13 and README wording, conservative); a natural re-test phrase, so worth a doc hint | deferred to G8 |
| B5 | Minor | steamcore `highscore-system` spec line `- [ ] AC-1.5 (Should, hardware-gated…): …` (no colon after the id) | expected an AC node; observed none, so the `⚠️` AC-1.5 is not shown by `gate_health` (its QACheck is `unknown`). Pre-existing spec parsing; 1 line each in Core and steamcore | deferred to G8 |
| B6 | Minor | Symlink `.spark/demo/qa.md` to a file outside the repo, build | observed the outside file is read and reaches the graph; identical on 0.7.0 with `qa-report.md`; not new, noted for security-posture | deferred to G8 |

Round 2 note, not a bug: Core `situational-lenses` AC-3.3 is a `❌ fail` row that reads `unknown`, because its Steps cell holds a bare pipe inside a code span (six cells, header has five), exactly the C14 rule and the same in GFM. Other probes, no bug: empty qa.md drifts loudly (same as legacy); empty qa.md beside a valid legacy file drifts (current wins); release-only folder builds; CRLF, Unicode title/version and NFR/unknown-AC rows behave; on the case-insensitive macOS filesystem `QA.md` is read (out of scope, would not be on Linux).

## 4. Console & Network

No browser, console or network (offline tool). Equivalent surface, stderr and exit codes, round 2: 35 generated repos plus 6 probe repos built via CLI and via live MCP `build_graph`; graph bytes and `ignored_legacy_files` equal on every building repo. Drift errors are one clean line, exit 1, `isError` over MCP. `Ignored …` notices go to stderr, exit 0. The only tracebacks are B3 (deferred). MCP server stderr only carries the pydantic-settings warning and `Processing request` lines.

## 5. Verdict

Would I demo this to a stakeholder right now? **Yes.** Every Must AC and NFR passes again on the wheel rebuilt from the current tree, over CLI and live MCP: current names are read, the current name wins, notices are named and stable, CLI and MCP agree, and this repo's own trail is byte-identical to v0.7.0 (AC-5.1, re-run with the final reports: `cmp` identical, both stderr empty). B1 is fixed: on fresh Core and steamcore the pass-marked rows with escaped pipes read `pass`, the two newly visible Core fails are real (`situational-lenses` AC-5.2, AC-6.1), and the scope guard, bare pipe, edge-of-row escaped pipe and CRLF probes behave as specified. The demo caveat is B2 (only the first QA table is read; accepted by the user, G6): Core `project-kickoff`, `graph-gates`, `lean-artifacts` and `situational-lenses` still show passed ACs as unverified, so the release notes must say so. Not tested: Linux, Windows, the version bump (still `0.7.0` in pyproject) and any PyPI publish. AC-5.1 stays true only while this repo's own §2 tables carry no escaped pipe (review F9); this report follows that.

---

## ✅ QA GATE

- [x] Every Must-story acceptance criterion verified by running the installed RC (CLI and MCP) and passed
- [x] Every relevant NFR verified and passed (NFR-6 N/A; NFR-2/4 also run via pytest: 319 and 3 passed)
- [x] No open Blocker or Major bugs (B1 fixed r2; B2 accepted by the user, deferred to G6)
- [x] Tool output free of unexpected errors on the tested flows (B3 only, Minor, deferred to G8)
- [x] Tested on all agreed surfaces (CLI, MCP stdio, wheel venv, `uvx`; no viewports apply)
- [x] Line budget respected: Ist 93 / Soll ~130
- [x] Status set to `passed`
