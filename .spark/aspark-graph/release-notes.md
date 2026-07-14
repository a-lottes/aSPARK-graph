# Release: aspark-graph

| | |
|---|---|
| **Phase** | Keep |
| **Owner** | Release Manager (`/go-live`) |
| **Input** | `review-report.md` (`passed`), `qa-report.md` (`passed`) |
| **Status** | `released` |
| **Version** | v0.1.0 |
| **Date** | 2026-07-14 |

## 1. Pre-Flight Checks

<!-- Verified immediately before releasing — not copied from earlier reports. -->
Run fresh on 2026-07-14 against the release commit (tag `v0.1.0`).

- [x] `review.md` status is `passed` — read `review-report.md`: status `passed`, REVIEW GATE all boxes checked, no open Blocker/Major, F1–F3 fixed, F4 accepted by the user.
- [x] `qa.md` status is `passed` — read `qa-report.md`: status `passed`, QA GATE all boxes checked, every Must-story AC verified hands-on (CLI + live MCP), no open Blocker/Major bugs.
- [x] Full test suite green on the release commit — `uv run pytest -q` → **65 passed in 1.63s**.
- [x] Build succeeds from a clean checkout — `rm -rf dist && uv build` → **`aspark_graph-0.1.0-py3-none-any.whl`** and **`aspark_graph-0.1.0.tar.gz`** built successfully into `dist/`.
- [x] **No uncommitted changes in the working tree — SATISFIED (at git-init time, as foretold).** At the prepare pass this was not verifiable (the project was not yet a git repository). The user then authorised the local, reversible steps: `git init` → `git add -A` → release commit → annotated tag `v0.1.0` (this final report is part of that commit, so its exact SHA is whatever `git rev-list -n1 v0.1.0` resolves to). `git status` is now **`nothing to commit, working tree clean`**, including after re-running `uv run aspark-graph build .` (the `.aspark-graph/` output is gitignored, so the build does not dirty the tree). The staged set was verified to contain no build artifacts, no `graph.json`, no `.venv`, no `.DS_Store` (`.DS_Store` was added to `.gitignore` before the commit).

**Extra determinism check (crown-jewel guarantee, AC-1.2), run fresh:** built the graph twice with `uv run aspark-graph build .` (239 code / 65 artifact entities each time) and compared `graph.json` — **byte-identical** (`diff` empty; SHA-1 `eada157ab0731f8b78e8ef8dad83c80cefd986d3` both runs). The `.aspark-graph/` output dir is gitignored, so it does not affect the tree-clean check. Re-confirmed post-tag: a build on the release commit still emits 239 code / 65 artifact entities and the working tree stays clean.

## 2. Changelog

<!-- User-facing language. What can they do now that they couldn't before? -->
First release. Everything here is new to users.

### Added
- **A local knowledge graph over your repo — one command.** Point `aspark-graph build .` at a repository and get a single graph of its code and its `.spark/` planning artifacts (specs, plans, review and QA reports), with a live count of what was found. No `.spark/` folder needed — you still get a code-only graph.
- **`story_trace` — follow a user story end to end.** Ask for a story (e.g. `US-1`) and get its title, all its acceptance criteria, the exact plan tasks that implement it with their status, each criterion's latest QA verdict, and the code files linked to it. Unknown stories come back as a clear "not found" instead of an error.
- **`impact` — know the blast radius before you change code.** Give it the files you're about to touch and it tells you which stories and acceptance criteria depend on them, so you know what needs re-testing. Each answer is tagged by how confident the link is — a file directly declared against a story reads as `declared`, one reached only through an import chain reads as `extracted` — and unknown paths are named back to you plainly.
- **Three languages out of the box.** TypeScript/JavaScript, Python, and Java source are all parsed in a single build, so mixed-language repositories are covered.
- **`gate_health` — aSPARK gate invariants as data.** Surface orphan tasks, unverified acceptance criteria, and open findings for a feature, so gate violations can be flagged without reading every artifact by hand.
- **Graph navigation.** Low-level lookup and traversal — `get_node`, `find_nodes`, `get_neighbors`, `shortest_path` — for exploring the graph directly.
- **Two ways in, same answers.** Use it as an MCP server (for your agent/assistant) or from the command line; both surfaces run the identical queries, so the CLI is a first-class fallback for CI or non-interactive use.
- **Deterministic, offline, and disposable.** The same repository always produces a byte-for-byte identical graph, everything runs locally with no network, and the built graph is a throwaway read model you can delete and rebuild at any time. If a planning artifact no longer matches its expected template, the build stops with one clear line naming the file and the mismatch — never a stack trace.

### Changed
- Nothing — this is the first release.

### Fixed
- Nothing — this is the first release.

## 3. Release Actions

<!-- What was actually executed, with results. -->
The user gave explicit go for the **local, reversible** steps only — **no remote/push, no PyPI**. Steps A and B below were executed with that authorization; the outward-facing steps (C, D) were deliberately **not** run and remain pending a future decision. Publishing outward (remote/PyPI) was consciously NOT done on the user's decision; the artefact is locally committed, locally tagged, and release-ready.

| Action | Result |
|---|---|
| Version bump & tag | **Executed (local).** `pyproject.toml` already declared `version = "0.1.0"` — no bump needed. `git init` → `git add -A` → release commit ("Initial release: aspark-graph v0.1.0") → annotated tag **`v0.1.0`** (`git rev-list -n1 v0.1.0` == `HEAD`). No push. |
| PR / merge | **N/A — consciously not done.** No remote exists; the user chose not to publish to any remote this release. |
| Deploy | **N/A — consciously not done.** No deploy and no package publish (PyPI/index) on the user's explicit decision. The wheel + sdist exist locally in `dist/` (built during pre-flight) but were not published. |
| Post-release smoke check | **PASS (the tool is verifiably alive).** `git log --oneline -1` → `<HEAD> Initial release: aspark-graph v0.1.0`; `git tag` → `v0.1.0`; `git status` → working tree clean; `uv run pytest -q` → **65 passed**; `uv run aspark-graph build .` → 239 code / 65 artifact entities; `uv run aspark-graph query story_trace US-2 --repo .` returned US-2's acceptance criteria (AC-2.1..AC-2.5) each carrying its latest QA verdict (`pass`) — the "responding app" equivalent for a CLI/MCP tool. (QA had already verified the end-user install paths — release wheel in a clean venv and via `uvx` — in `qa-report.md` §5.) |

### Pending outward-facing commands — NOT run, awaiting a separate user decision

The publish *target* remains deliberately open. None of these were executed.

**Step C — publish to a remote (OUTWARD-FACING — DESTINATION NOT YET CHOSEN):**
```
# Option 1: push to an existing remote the user provides
git remote add origin <REMOTE_URL>
git push -u origin main
git push origin v0.1.0

# Option 2: create the GitHub repo and push in one step (requires gh auth + a name)
gh repo create <OWNER/NAME> --private --source=. --remote=origin --push
git push origin v0.1.0
```

**Step D — publish the package to an index (OUTWARD-FACING — NOT AUTHORISED):**
```
uv publish        # target index + credentials to be provided by the user
```

**Open decisions before Step C/D:**
1. Should this be published to a remote at all, and where (GitHub? which owner/name? public or private)?
2. Should the package be published to PyPI (or a private index), or stay source-only?

## 4. Learnings (Keep!)

<!-- The K in SPARK: what does the team keep from this cycle? -->

- **What went well:**
  - **Dogfooding paid off twice.** aspark-graph was run through aSPARK's own full SPARK loop, and its own `.spark/` trail became the tool's primary, real-world test fixture — the reviewer and QA both trace the tool's own spec/plan/reports. Building the thing on itself surfaced real behaviour (239 code / 65 artifact entities on this repo) that no synthetic fixture would have.
  - **The packaging risk was killed on day one.** The scariest v0.1.0 risk — native tree-sitter grammar wheels not installing cleanly for an end user — was retired immediately by forcing the walking skeleton to actually install all three grammars. QA later confirmed the release wheel installs and runs in a clean venv and via `uvx`. Front-loading the install risk into the skeleton is the reusable move.
  - **The thin-adapter architecture made CLI≡MCP parity essentially free.** Because both the CLI and the MCP server are thin adapters over a shared `queries.py`/`build.py` with no query logic of their own, parity is true by construction rather than by duplicated tests. This is the single most load-bearing convention in the codebase.
  - **The A9 three-extractor timebox risk did not bite.** The user-accepted risk that shipping three language extractors would blow the ~2-week target never materialised — Java parsed cleanly and all three languages landed in a single build.
  - **Gates held and stayed honest.** Review found four findings (a raw-traceback UX bug, an exact-pin gap, a QA-verdict regex gap, two nits); three were fixed and re-verified green, one was consciously accepted by the user with a reason — no red gate was waved through.

- **What we'd do differently:**
  - **Pin determinism-affecting deps exactly from the start.** F2 caught that the tree-sitter grammars were pinned with `>=` while the plan demanded exact pins for AC-1.2 determinism; the committed `uv.lock` compensated, but the pins are now `==` and documented. Encode "anything that can change the serialised graph is pinned exactly" as a rule, not a review catch.
  - **Bake the CLI-UX contract into the code earlier.** F1 was a `TemplateDriftError` traceback leaking to the user on the tool's headline failure path. The spec's "clean error, not a stack trace" contract should have a shared error-boundary in the adapters from T1, so no new command can regress it.
  - **Broaden human-authored-text parsing defensively up front.** F3 (`\bpass\b` not matching "passed") shows artifact parsers should tolerate reasonable human phrasing beyond the exact template glyphs from the first version, since silent misreads quietly weaken `story_trace`/`gate_health`.

- **Patterns worth reusing:** <!-- candidates for CLAUDE.md / project memory -->
  - **Thin adapters over a shared core** — CLI and MCP (and any future surface) must contain no domain logic; they call into `queries.py`/`build.py`. Parity is then structural. *(Candidate for CLAUDE.md.)*
  - **Determinism contract, written down** — canonical sorted `sort_keys` JSON persistence + exact pins on anything that affects the bytes + `uv.lock` ships; verify with a byte-identical double-build test in CI. *(Candidate for CLAUDE.md.)*
  - **Retire the scariest install/packaging risk in the walking skeleton**, not at release. *(Candidate for project memory.)*
  - **Dogfood as the primary fixture** — a self-describing tool should be run against its own artifact trail; it is the most honest test data available. *(Candidate for CLAUDE.md.)*
  - **Single error boundary in each adapter** so expected failure modes read as one clean stderr line + non-zero exit, never a traceback. *(Candidate for CLAUDE.md.)*

## Rollback Path

The release is committed and tagged **locally only** — nothing has left the machine — so rollback is trivial and fully local:

- **Current state (committed + tagged, unpublished):** to undo, `git tag -d v0.1.0` removes the local tag; `git reset` / `git update-ref -d HEAD` (or simply discarding the `.git` directory) removes the initial commit. Because there is no remote and no published package, **no external party has seen anything** — the reversal is complete and leaves no trace.
- **If Step C (push) is later run — the first hard-to-unwind step:** the way back is `git push origin :refs/tags/v0.1.0` to delete the pushed tag, plus deleting the remote repo if it was created solely for this. Gated on explicit user go and a chosen destination.
- **If Step D (index publish) is later run:** a package index generally won't accept a re-upload of the same version; recovery is to *yank* `0.1.0` and publish a fixed `0.1.1`. This is the genuinely irreversible step and must not run without explicit authorisation.

---

## ✅ KEEP GATE

*All boxes checked → the loop is closed. The feature is done-done.*

- [x] All pre-flight checks passed at release time — both gates `passed`; `uv run pytest -q` 65 passed; clean `uv build` produced wheel + sdist; byte-stable double-build byte-identical; working tree clean on the release commit (tag `v0.1.0`).
- [x] Changelog written in user-facing language
- [x] Release actions executed and verified — version already `0.1.0`, local release commit + annotated tag `v0.1.0` created and verified; outward-facing publish (remote/PyPI) consciously **not done on the user's explicit decision** and recorded as such (a valid release state, not a gap); post-release smoke check passed (build + `story_trace US-2` return correct data — the tool is verifiably alive).
- [x] Learnings recorded
- [x] Status set to `released`
