# Release: current-artifact-names

| | |
|---|---|
| **Phase** | Keep |
| **Owner** | Release Manager (`/go-live`) |
| **Input** | `review-report.md` (`passed`, round 2), `qa-report.md` (`passed`, round 2) — legacy names on purpose (plan R2) |
| **Status** | `preparing` |
| **Version** | v0.7.1 (patch, user ruling 2026-09-26: all changes additive — MCP key `ignored_legacy_files`; `coverage` on every Feature node; `coverage` and `coverage_note` in `gate_health`) |
| **Date** | 2026-09-26 |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status` and `Version`).
- **Summary:** aspark-graph v0.7.1 reads Core's current artifact names; PR #3 merged (crashed next to PR #2, repaired by `coverage-current-names`); nothing published or tagged remotely.
- **Open:** `1 outstanding` — publish (§3) waits for the user's explicit go; the PyPI upload is run by the maintainer, no agent holds a credential.
- **Binding ruling:** §3 Release Actions and the KEEP GATE below carry the final ruling.
- **On conflict:** the numbered body below wins for everything except `Status`/`Version`.

## 1. Pre-Flight Checks

**Re-run on the repair commit `8b7a1b3` (fresh clone, 2026-09-26) — this certifies the release:**
- [x] `review-report.md` and `qa-report.md` of `coverage-current-names` `passed` (review r2, QA r1); `current-artifact-names` review r2 / QA r2 `passed`
- [x] `uv run --extra dev pytest`: 328 passed; `-m slow`: 3 passed
- [x] `uv build`: `aspark_graph-0.7.1` wheel and sdist; sdist top level only `src`, `tests`, `README.md`, `LICENSE`, `pyproject.toml` plus hatch's `.gitignore` and `PKG-INFO`
- [x] Version parity: `pyproject.toml` 0.7.1 == `uv.lock` 0.7.1
- [x] Byte-identity vs the previous main `ad83eae` on this repo's own trail: `cmp` no difference (sha1 5f7785f0b6a3, 527113 bytes), stderr empty on both
- [x] Core `e1a0005`: exit 0, QACheck pass 143 / unknown 11 / fail 11, Finding 170. steamcore `bf1b3e0`: exit 0, pass 251 / unknown 10, Finding 138
- [x] No `review.md`, `qa.md` or `release.md` under this repo's `.spark/`

> **Superseded (2026-09-26).** The checks below ran on `e57ce6d`, which merged next to PR #2 and crashed as `1b62da0`. They are kept as history and do **not** certify the release. Pre-flight is re-run on the repair commit (`coverage-current-names` T4); the byte-identity baseline is the previous main `ad83eae`, not v0.7.0 (C1).

Run on `e57ce6d`, 2026-09-26, not copied from the reports.

- [x] `review-report.md` `passed` (round 2) and `qa-report.md` `passed` (round 2); QA has no declared method, the project's headless-QA-in-review policy is unchanged
- [x] `uv run pytest`: 319 passed. `-m slow`: 3 passed on a quiet machine. The first run failed NFR-1 (47.4% vs 50%, then 42.8%) while load average was 13 to 21; reruns gave 55.7% and 54.1%, and 3 of 3 passed. Timing flake under load, not a regression
- [x] No lint or type-check config in the repo (no ruff, mypy, pyright); none run
- [x] `uv build` from the tree: wheel and sdist build; sdist top level is only `src`, `tests`, `README.md`, `LICENSE`, `pyproject.toml` plus hatch's automatic `.gitignore` and `PKG-INFO`; no `.claude`, `.spark`, `docs`, `CLAUDE.md`, `SECURITY.md`, `uv.lock`, `aSPARK-graph` symlink (73 entries)
- [x] Repo state read directly: base `dc3a94c` == `origin/main`; tags up to `v0.7.0`; GitHub `v0.7.0` is Latest; no `v0.7.1` tag or release
- [x] Working tree: only the intended paths staged; untracked `aSPARK-graph` symlink and `.spark/.guard/` left alone
- [x] Version parity: `pyproject.toml` 0.7.1 == `uv.lock` self-entry 0.7.1 == intended tag `v0.7.1`
- [x] T8 release evidence (fresh clone of the release commit, RC vs published 0.7.0):
  - (a) AC-5.1: `uvx --from aspark-graph==0.7.0 aspark-graph build . --full` vs RC `build --full`, `cmp` no difference (sha1 7cab3da0, 595 code, 428 artifact entities), stderr empty, no `Ignored` lines; clone of the release commit, final report present
  - (b) AC-5.4 Core (e1a0005, branch feat/ticket-import): exit 0, no drift, no notices; 818 artifact entities; QACheck 165 (pass 143, unknown 11, fail 11); Finding 170
  - (b) AC-5.4 steamcore (bf1b3e0): exit 0, no drift, no notices; 893 artifact entities; QACheck 261 (pass 251, unknown 10); Finding 138; `gate_health` `unverified_acs: []` on game-loop, rendering-core, start-screen, text-rendering
  - (c) slow suite in the clone: 3 passed (plus 319 in the clone)
  - (d) no `review.md`, `qa.md` or `release.md` under this repo's `.spark/`: glob empty (0 found in the clone)

## 2. Changelog

### Added
- aspark-graph now reads the artifact names aSPARK Core writes today: `review.md`, `qa.md` and `release.md`. Projects that follow current Core show their QA checks, findings and release state in the graph, so `story_trace` and `gate_health` work on them.
- When a feature folder holds both a current file and an old one (for example `qa.md` and `qa-report.md`), the current file wins. The build names each ignored old file (`Ignored ... (qa.md takes precedence)` on stderr; `ignored_legacy_files` from the MCP `build_graph` tool). Ignored files leave no trace in the graph.
- The README has an "Artifacts read" section listing both name sets.
- Coverage statement (contributed in PR #2, aSPARK #61): every Feature node records which artifacts parsed (`coverage`: recognized, skipped, near-misses), and `gate_health` returns it with a `coverage_note` when the verdict rests on a partial trail. Each artifact kind is named by its legacy spelling (`qa-report.md` etc.) whichever file was read, so a rename never changes the graph.

### Changed
- QA result cells are read by their marker first: ❌ is fail, ⚠ is unverified, ✅ is pass; words like "pass" only count when a cell has no marker. A cell such as `✅ pass (was ❌ fail)` therefore reads fail.
- A QA cell containing an escaped pipe now keeps its columns instead of shifting the row.
- README and CLAUDE.md now say five supported languages (Python, TypeScript/JavaScript, Java, Go, Rust).
- Repos that only use the old names build the same graph as before, plus the new `coverage` field on each Feature node. Without that field, nothing changes for them (checked byte-for-byte against the previous main, `ad83eae`).

### Fixed
- Acceptance criteria that passed QA no longer show as unverified just because the project uses `qa.md`.
- Result cells whose text merely contains a marker word (for example `⚠️ ... passed`) no longer read as pass.

### Visible behaviour changes (numbers you may have seen)
- Some rows that read `pass` under 0.7.0 now read unknown or fail. On Core, two rows are newly `fail` (situational-lenses AC-5.2 and AC-6.1), both real failed rows that were hidden. Core's artifact count rises from 483 to 818, steamcore's from 494 to 893.

### Known limits
- **Repair before release:** PR #2 and PR #3 were merged in parallel, and `main` at `1b62da0` crashed on build (`'NoneType' object has no attribute 'exists'`). Nothing was uploaded from that state. The fix (`coverage-current-names`) is part of 0.7.1.
- **B2:** only the first QA verification table per `qa.md` is read. 4 of 13 Core `qa.md` files split by story (for example project-kickoff: 6 QACheck for 26 ACs), so their later ACs show as unverified. Accepted by the user; BACKLOG G6.
- **G7:** MCP `build_graph` does not return template drift as a structured result; it surfaces as a tool error. The CLI exits non-zero with one line.
- **G8:** a directory named like an artifact gives a traceback; `✅ pass (was ❌ fail)` reads fail; an AC line without a colon after the id gets no AC node; a symlinked `qa.md` outside the repo is read (as in 0.7.0); an escaped pipe is handled only in the QA table.
- **Coverage names (C4):** `coverage.recognized`/`skipped` name each kind by its legacy spelling. On a current-name trail without a QA file, `skipped` says `qa-report.md` (e.g. Core `lean-rounds`). Deliberate, so a rename never changes the graph; BACKLOG G10.
- **G10:** near-miss detection is a substring match (`explanation.md` is flagged); `QA.md` on macOS is read and also listed as a near-miss; a graph built before 0.7.1 shows `coverage: {}` until rebuilt.
- Tested on macOS only; Linux and Windows are not tested.

## 3. Release Actions

Prepared locally; the outward-facing rows are pending the user's go.

| Action | Result |
|---|---|
| Version bump & tag | Bump done (0.7.0 to 0.7.1, `uv lock`). The earlier local tag on `e57ce6d` is to be dropped (`git tag -d v0.7.1`); `v0.7.1` goes on the merge commit of the repair PR, after the upload |
| PR / merge | PR #3 merged as `1b62da0` next to PR #2; the combination crashed. Repair PR from `fix/coverage-current-names` pending review, QA and merge |
| Deploy | Pending. Publish to PyPI, run by the maintainer (below) |
| Post-release smoke check | Pending, after publish |

Pending commands, in order, each needing the go:
1. `git push -u origin fix/coverage-current-names`, then `gh pr create --base main --head fix/coverage-current-names`, merge (merge commit); PR #3 (`feat/current-artifact-names`) is already merged
2. Maintainer's own shell (token stays theirs): `cd <clean checkout of the repair merge commit> && rm -rf dist && uv build && uv publish` (`rm -rf dist` because the old 0.7.0 files sit in `dist/`)
3. Verify live: `curl -s https://pypi.org/pypi/aspark-graph/json` shows 0.7.1 with wheel and sdist, byte sizes equal to the local build
4. `git push origin v0.7.1`, then `gh release create v0.7.1` (minimal notes first, then `gh release edit --notes-file`, per CLAUDE.md)
5. Smoke: fresh venv, `pip install aspark-graph==0.7.1`, `aspark-graph build` on a repo with a `qa.md`; `serve` handshake lists 9 tools

**Rollback path.**
- Before publish: nothing is on PyPI; `main` can be repaired or `git revert`-ed; the local tag on `e57ce6d` is deleted and re-cut on the repair merge commit.
- After publish: a PyPI version number is burned. Yank 0.7.1 in the PyPI web UI (maintainer only; hides it from "latest", exact pins still work), then ship 0.7.2 as the fix. `pip install aspark-graph==0.7.0` remains the known-good version.
- After push: `git revert` the merge on main (no history rewrite); delete the GitHub release and tag `v0.7.1` (`gh release delete v0.7.1 --cleanup-tag`) if the release itself is wrong.

## 4. Learnings (Keep!)

- **What went well:** scratch clones of Core and steamcore found what fixtures could not (escaped pipe B1, `⚠️ ... passed` read as pass); the trail under legacy names (R2) kept a byte-identical proof possible (against v0.7.0 for `e57ce6d`, against the previous main `ad83eae` after PR #2 added `coverage`); QA re-derived its evidence in round 2.
- **What we'd do differently:** check `origin/main` for other merges before cutting the release commit (PR #2 landed in parallel and the combination crashed); read real files before writing the parser rule (B2 was known at plan time and still shipped as a limit); the NFR-1 benchmark fails under machine load, so run the slow suite on a quiet machine; `__version__` in `__init__.py` is stale (0.1.0) and pinned by a test.
- **Patterns worth reusing:** (in CLAUDE.md now) old-names trail until the reader ships, wide real-data read before parser rules, marker-first result cells, version from package metadata not `__init__`.

---

## ✅ KEEP GATE

- [x] All pre-flight checks passed at release time — re-run on the repair commit `8b7a1b3` (§1, top block)
- [x] Changelog written in user-facing language
- [ ] Release actions executed and verified — prepared only; push, PR, publish, tag push and smoke check await the user's go
- [x] Learnings recorded
- [x] Line budget respected: Ist 101 / Soll ~100 (no HTML comments; blank lines counted)
- [ ] Status set to `released` — stays `preparing` until the publish steps are done
