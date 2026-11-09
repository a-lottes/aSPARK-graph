# Release: shallow-clone-warning

| | |
|---|---|
| **Phase** | Keep |
| **Owner** | Release Manager (`/go-live`) |
| **Input** | `review.md` (`passed`, round 2), `qa.md` (`passed`, round 1) |
| **Status** | `released` |
| **Version** | v0.7.2 (patch, spec C6: one new stderr notice, two new always-present MCP keys, no breaking change) |
| **Date** | 2026-10-03 |
| **Commit** | `39ed92cb1b04eefed53a800bed7ca1cbdeda94aa` (merge of PR #8, tagged `v0.7.2`); release commit `699b02e` |
| **PR** | https://github.com/a-lottes/aSPARK-graph/pull/8 (merged) |
| **Ticket** | none |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status` and `Version`).
- **Summary:** v0.7.2 released 2026-11-09: PR #8 merged as `39ed92c`, uploaded to PyPI, tagged, GitHub release created. The post-release smoke check found that a fresh install's MCP server crashes on pydantic 2.14 (pre-existing since 0.7.1, not caused by this release); fixed in v0.7.3.
- **Open:** `none` for this release. The MCP/pydantic incompatibility ships as hotfix v0.7.3 (branch `fix/pydantic-cap`).
- **Binding ruling:** §3 Release Actions and the KEEP GATE below carry the final ruling.
- **On conflict:** the numbered body below wins for everything except `Status`/`Version`.

## 1. Pre-Flight Checks

Run 2026-10-03 on `699b02e` (code identical to the gated `c144cb0` plus the version bump), not copied from the reports.

- [x] `review.md` `passed` (round 2, Open `none`); gate checklist complete
- [x] `qa.md` `passed` (round 1); gate checklist complete; B1, B2 and A6 deferred by the user to BACKLOG G11 (2026-10-03). QA wording unchanged: no constitution, so no declared QA method applies; the project's headless QA policy (CLAUDE.md) stands
- [x] `.venv/bin/python -m pytest -q`: 387 passed, 3 deselected (load average 19 to 25)
- [x] `-m slow`: 3 passed (load average about 10). B1 did not show this run; it stays load-sensitive (G11)
- [x] `uv build` in a fresh clone of `699b02e`: `aspark_graph-0.7.2` wheel (54363 B, sha256 9bde77b4…) and sdist (96872 B, sha256 e289c332…); wheel METADATA `Version: 0.7.2`; sdist top level only `src`, `tests`, `README.md`, `LICENSE`, `pyproject.toml` plus hatch's `.gitignore` and `PKG-INFO` (77 entries)
- [x] Version parity: `pyproject.toml` 0.7.2 == `uv.lock` 0.7.2 (`uv lock --check` OK). `__version__` stays `0.1.0` on purpose: nothing reads it, and `test_smoke.py` pins it (BACKLOG G9)
- [x] Wheel smoke: fresh 3.11 venv, wheel installed, `--depth 1` clone of `699b02e`: the shallow notice prints once, exit 0, stdout in v0.7.1's format
- [x] Working tree clean apart from the untracked `aSPARK-graph` symlink and `.spark/.guard/` (left alone)
- [x] `origin/main` is still `b215790` and the branch builds on it; open PR #7 (README) merges with this branch without conflict

## 2. Changelog

### Added
- A build on a shallow clone (for example `git clone --depth 1`, or a CI checkout) now prints one line to stderr:
  `Shallow git history: inferred links may be missing (run 'git fetch --unshallow', then rebuild).`
- A build in a folder without git history (for example a ZIP download) prints:
  `No git history: inferred links are missing (build from a full git clone to get them).`
- Both notices appear only when the project has at least one plan task, and at most one per build.
- The MCP `build_graph` tool returns two new keys, `shallow_history` and `no_git_history`. Both are always there; each is `true` exactly when the matching notice prints, never both.
- The README quotes both notices and the fix.

### Fixed
- Shallow clones no longer invent inferred links. Before, the oldest commit of a shallow clone looked as if it had touched every file, so `impact` blew up. On this repo at `--depth 1`, `impact src/aspark_graph/queries.py` went from 19 stories / 101 ACs to 2 / 8, a subset of the full clone's 4 / 17. After `git fetch --unshallow` and a rebuild, you get 4 / 17 again.

### Unchanged
- Exit code (always 0 for these notices) and the stdout format.
- graph.json on every non-shallow build is byte-for-byte the same as with 0.7.1. A shallow build only loses the links its oldest commits would have invented.

### Known limits
- With git older than 2.15, a shallow clone is not detected: no notice, and inferred links are inflated as in 0.7.1.
- Tested on macOS only; Linux and Windows are not tested.
- Deferred to BACKLOG G11: a project in a monorepo subfolder gets no inferred links and no notice; a `--filter=tree:0` clone may fetch from the network during the build; one speed benchmark in the test suite fails when the machine is busy.

## 3. Release Actions

Steps 1–2 done with the user's go (2026-10-03); steps 3–7 done step by step with the user's go (2026-11-09), after the go-live was resumed and re-verified from the repo: PR #7 (README only) had merged before #8, so the full suite (387 passed), `-m slow` (3 passed) and `uv build` (sdist allowlist only) were re-run on a fresh clone of `39ed92c`.

| Action | Result |
|---|---|
| Version bump & tag | 0.7.2 committed as `699b02e`; annotated tag `v0.7.2` on merge commit `39ed92c`, pushed |
| PR / merge | PR #8 merged by the user as `39ed92c`; GitHub release: https://github.com/a-lottes/aSPARK-graph/releases/tag/v0.7.2 (Latest) |
| Deploy | PyPI upload by the user (`uv publish`, their token; first try 403 on the token, second try OK), built from `39ed92c`; PyPI sha256 equals the local build: wheel `3e4d9e6e…`, sdist `431930e7…` |
| Post-release smoke check | **partly red.** Fresh 3.11 venv, `pip install aspark-graph==0.7.2`: `build` on a `--depth 1` clone prints the shallow notice once, exit 0 ✅. `serve` crashes on import ❌: the unlocked install resolves pydantic 2.14.3, which removed `eval_type_backport` that mcp 1.19.0 imports. Same crash with 0.7.1 + pydantic 2.14.3 (pre-existing since pydantic 2.14.0, 2026-10-08); with pydantic 2.13.4 `serve` lists 9 tools. Fix: hotfix v0.7.3 caps pydantic |

Pending commands, in order:
1. Done: `git push -u origin feat/shallow-clone-warning`
2. Done (PR #8): `gh pr create --repo a-lottes/aSPARK-graph --base main --head feat/shallow-clone-warning --title "feat(shallow-clone-warning): name shallow or missing git history (v0.7.2)" --body-file <PR body>`; then merge with a merge commit. If PR #7 merges first, run the suite on the merge again.
3. User, own shell: `git checkout main && git pull && git rev-parse HEAD` (must be the merge commit) `&& rm -rf dist && uv build && twine upload dist/*` (`rm -rf dist` because `dist/` holds the 0.7.1 files)
4. Verify: `curl -s https://pypi.org/pypi/aspark-graph/json` shows 0.7.2 with wheel and sdist
5. `git tag -a v0.7.2 <merge-sha> -m "aspark-graph v0.7.2 — name shallow or missing git history" && git push origin v0.7.2`
6. `gh release create v0.7.2 --repo a-lottes/aSPARK-graph --title "v0.7.2" --notes-file <§2 as file>` (Latest)
7. Smoke: fresh venv, `pip install aspark-graph==0.7.2`; `build` on a `--depth 1` clone shows the shallow notice; `serve` lists 9 tools

**Rollback path.**
- Now (pushed, PR open, not merged): `gh pr close 8 --delete-branch`; nothing is on main or PyPI.
- After merge: `git revert -m 1 <merge-sha>` on main through a PR; no history rewrite.
- After upload: 0.7.2 is burned on PyPI. The user yanks it in the PyPI web UI, and a fix ships as 0.7.3; `pip install aspark-graph==0.7.1` is the known-good version. Wrong tag or release: `gh release delete v0.7.2 --cleanup-tag`.

## 4. Learnings (Keep!)

- **What went well:** review F1 turned a wording question into a real fix (US-5): the evidence showed the notice was pointing the wrong way, and the user picked "fix inference" over a reworded warning. QA checked many odd shallow shapes hands-on (graft lists, SHA-256, worktrees) and found no crash.
- **What we'd do differently:** test the inference path on a non-merge tip from the start; the first evidence (2/8) was only right by luck, because the tip was a merge. Fix the B1 benchmark before the next slow-suite gate (G11), so a load spike stops being a judgement call.
- **Learned at release (2026-11-09):** the test suite runs only against `uv.lock`, so it cannot see what a fresh `pip install` resolves. An unbounded transitive dep (pydantic) broke `serve` for every new user for a month unnoticed; only the post-release smoke check on a real PyPI install caught it.
- **Patterns worth reusing (CLAUDE.md candidates):** "Truncated input should only lose answers, never invent them; when unsure, drop" (C12). For each release, check `origin/main` and open PRs for overlap before the release commit (done here: PR #7 has no conflict).

---

## ✅ KEEP GATE

- [x] All pre-flight checks passed at release time (§1, on `699b02e`)
- [x] Changelog written in user-facing language
- [x] Release actions executed and verified (§3); smoke check found a pre-existing dependency break, handed to hotfix v0.7.3
- [x] Learnings recorded
- [x] Line budget respected: Ist 99 / Soll ~100 (no HTML comments)
- [x] Status set to `released` (2026-11-09)
