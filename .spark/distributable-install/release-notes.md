# Release: aspark-graph 0.3.0 (distributable-install + close-the-loop)

| | |
|---|---|
| **Phase** | Keep |
| **Owner** | Release Manager (`/go-live`) |
| **Input** | `distributable-install/review-report.md` (`passed`), `close-the-loop/review-report.md` (`passed`); no `qa.md` (QA-gate override — see below) |
| **Status** | `preparing` |
| **Version** | v0.3.0 |
| **Date** | 2026-07-16 |

This release **bundles two feature cycles** into a single version:

- **close-the-loop** — planned as 0.2.0, never shipped. Git-history inference of
  `implements` edges (task→code), a new `INFERRED` confidence tier, `impact --diff`,
  `staleness` detection, and the F1 cross-feature id-collision fix.
- **distributable-install** — the 0.3.0 headline. Drops the native `cryptography`
  dependency (uninstallable on Intel macOS) by moving the MCP server from `fastmcp`
  to the official `mcp` SDK; bumps 0.1.0 → 0.3.0.

Because close-the-loop never released, the true next version is **0.3.0**, and both
cycles ship together. `pyproject.toml` already reads `version = "0.3.0"`.

### QA-gate override (recorded, not a silent skip)

Neither feature has a `qa-report.md`. `/demo-day` (hands-on browser QA) is
structurally **N/A** for a headless CLI/MCP tool with no UI; design review was N/A
throughout both cycles. The **user explicitly authorized the QA-gate override in
this conversation (2026-07-16)**.

- **Override authorized by:** the user (andreas@lottes.dev), 2026-07-16.
- **Reason:** the QA-equivalent was performed hands-on during peer-review — a
  clean-env 0.3.0 wheel install (cryptography absent, both entry points working),
  `serve` stdio boot registering all 9 tools, the full 103-test suite green, a
  byte-identical double-build, and F1 verified on the real dogfood repo
  (aspark-graph-sourced inferred edges 21 → 0).
- This is recorded as an **override with reason and authorizer**, per the release
  hard rules — not treated as a passed QA gate.

## 1. Pre-Flight Checks

<!-- Verified immediately before releasing — run fresh on the release commit, not copied. -->

Run 2026-07-16 on the release commit (`a83640e` at check time; superseded by the
release commit) with `PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"`.

- [x] `distributable-install/review-report.md` status is `passed`
- [x] `close-the-loop/review-report.md` status is `passed`
- [x] `qa.md` — **N/A, override authorized by the user (2026-07-16)**; see above
- [x] Full test suite green on the release commit — `uv run pytest -q` → **103 passed** in 23.77s
- [x] Determinism holds — double `aspark-graph build .` → **BYTE-IDENTICAL** graph.json (210,885 bytes)
- [x] Build succeeds from a clean state — `uv build` → `aspark_graph-0.3.0-py3-none-any.whl` + `aspark_graph-0.3.0.tar.gz`
- [x] Clean-env install proof — wheel installed alone into a fresh Python 3.13 venv:
  - `cryptography` absent, `fastmcp` absent, `mcp` present
  - `aspark-graph` console script works
  - `aspark_graph.server` imports and registers **all 9 tools** (`build_graph`,
    `story_trace`, `impact`, `gate_health`, `staleness`, `get_node`, `find_nodes`,
    `get_neighbors`, `shortest_path`)
- [x] No uncommitted changes in the working tree (verified clean before the release commit)

**Result: all pre-flight checks pass.** No pre-flight failure; no patch on the
release commit needed.

## 2. Version

**0.3.0** — semver minor bump from the last shipped tag `v0.1.0`.

Justification (one line): this version bundles **two** feature cycles' worth of
new, backward-compatible capability and **supersedes the never-shipped 0.2.0**
(close-the-loop); the dependency change that unblocks install on a whole platform
class is the headline. No breaking API change → minor, not major.

## 3. Changelog

<!-- User-facing language. What can users do now that they couldn't before? -->

### Added

- **`impact` and `story_trace` now return real results on ordinary repos.** If your
  commits mention story or task ids (e.g. "US-2", "T3"), the tool now links code to
  the stories it implements from your git history — no hand-annotation required. Ask
  "what does this story cover?" or "what's the blast radius of changing this file?"
  and get real answers where before you got an empty result.
- **Scope impact from a change range.** `impact --diff <range>` reports the affected
  stories and acceptance criteria for everything in a commit or branch range, so you
  no longer have to type out each changed file.
- **Staleness detection.** The tool now tells you when the graph no longer matches
  the repository it was built from, so you never act on an out-of-date `impact` or
  `story_trace` answer without knowing it.
- **An `inferred` confidence tier.** Links derived from git history are tagged
  `inferred` — visibly weaker than `declared` or `extracted` — so you can tell a
  guessed blast-radius hit from a certain one at a glance.

### Changed

- **aspark-graph now installs cleanly and toolchain-free on Intel macOS, Apple
  Silicon macOS, and Linux.** Previously the tool could not be installed on Intel
  macOS at all: a native cryptography dependency had no prebuilt wheel and required a
  build toolchain. That dependency is gone — the MCP server now runs on the official
  `mcp` SDK — so a plain install just works, no compiler required, on every supported
  platform.
- **The built package installs into a fresh, isolated environment with both entry
  points working** — the `aspark-graph` CLI and the `aspark-graph serve` MCP server
  (all 9 tools) run straight from the installed package, not just from a checkout.

### Fixed

- **Correct feature attribution.** A file belonging to one feature is no longer
  mistakenly attributed to a same-numbered story in another feature; `impact` and
  `story_trace` results are now scoped to the feature that actually owns the code.
- **A mistyped diff range is caught, not silently ignored.** Passing a bare filename
  where a range is expected now returns a clear error instead of a silent empty
  success.
- **Querying before building is a clean message.** Running an MCP query before the
  graph has been built returns a clear "build first" response instead of an error.

## 4. Release Actions

<!-- What was actually executed, with results. PREPARE-ONLY pass: local steps only. -->

| Action | Result |
|---|---|
| Version bump | `pyproject.toml` = `0.3.0` (confirmed; already set) |
| Release commit | `release: aspark-graph 0.3.0` — committed locally |
| Local tag | annotated `v0.3.0` created **locally (not pushed)** |
| Push (`git push origin main` + tag) | **PENDING — awaiting user go** (not run) |
| GitHub Release | **PENDING — awaiting user go** (not run) |
| PyPI publish | **PENDING — awaiting user go + prerequisites** (not run) |
| Post-release smoke check | **DEFERRED** — runs after deploy/publish is authorized |

This is a **PREPARE-ONLY** pass. All local, reversible work is done; every
outward-facing action is prepared and listed in §6, awaiting the user's explicit go.

## 5. Rollback Path

<!-- No release without a written way back. -->

**While still local (this state):**

1. Delete the local tag: `git tag -d v0.3.0`
2. Undo the release commit, keeping the tree:
   `git reset --soft HEAD~1` (or `git revert --no-edit HEAD` to keep history linear)
3. `git status` to confirm the tree is back to the pre-release state.

**If the push has already happened (main + tag on origin):**

1. Remove the remote tag: `git push origin :refs/tags/v0.3.0`
2. Revert the release commit on main with a new commit (never force-push a shared
   branch): `git revert --no-edit <release-commit-sha>` then `git push origin main`
3. Delete the local tag: `git tag -d v0.3.0`

**If a GitHub Release was published:** delete the release in the GitHub UI/`gh
release delete v0.3.0`, then remove the tag as above.

**If the PyPI publish already happened:** PyPI does **not** allow re-uploading a
yanked version's files. `uv publish`/`twine` uploads are effectively permanent for a
given version number. The recovery is to **yank** the release
(`pip`/PyPI project page → yank `0.3.0`, or via the API) so it is not installed by
default, then ship a corrected `0.3.1`. There is no true "delete and reuse 0.3.0".
This is why the publish is the last, deliberately-gated step.

## 6. Pending Outward Actions (prepared — DO NOT run without user go)

The repo is already on GitHub at https://github.com/a-lottes/aSPARK-graph (main
pushed). The following are prepared and await the user's explicit authorization.

**(a) Push the release commit and tag:**

```
git push origin main
git push origin v0.3.0
```

**(b) GitHub Release for v0.3.0** (after the tag is pushed):

```
gh release create v0.3.0 \
  --title "aspark-graph 0.3.0" \
  --notes-file .spark/distributable-install/release-notes.md
```

**(c) PyPI publish** — deliberately deferred by distributable-install (spec Q2) to
this Keep phase:

```
uv build            # already produced dist/aspark_graph-0.3.0-{whl,tar.gz}
uv publish          # uploads dist/* to PyPI
```

**Prerequisites / honest risk flags for (c) — this is a user decision, not an
assumption:**

- **Name ownership.** The `aspark-graph` name must be available on PyPI, or already
  owned by the user. If the name is taken by someone else, `uv publish` fails and the
  package cannot ship under that name — **unverified here.**
- **Credentials.** A PyPI API token must be configured (`UV_PUBLISH_TOKEN` /
  `--token`, or `~/.pypirc`). Without it the publish cannot authenticate —
  **unverified here.**
- **Irreversibility.** Version `0.3.0` can be uploaded only once; a mistake means
  yank + `0.3.1`, never reuse (see §5).
- **README honesty.** The README currently documents from-source install only (US-3,
  F4). If the publish succeeds, the README's install section should be updated to
  document the `uvx`/`pipx` path so the docs stay truthful — a follow-up, not part of
  this prepared step.

Because name ownership and token configuration are **unknown at prepare time**, the
PyPI publish is escalated to the user as a decision, not performed on assumption.

## 7. Post-Release Smoke Check (to run AFTER an authorized deploy/publish)

Not yet run — this is a prepare-only pass. When publish/deploy is authorized:

- Install the published artifact into a fresh env on a supported platform; confirm
  `cryptography` absent and both `aspark-graph` and `aspark-graph serve` work.
- Run the released core flow: `aspark-graph build .` then
  `aspark-graph query impact --diff <range>` / `story_trace US-1` returns real,
  correctly-tiered results.
- Confirm `serve` boots over stdio and registers all 9 tools; logs are quiet.

## 8. Learnings (Keep!)

<!-- The K in SPARK: what does the team keep from this cycle? -->

- **What went well:**
  - The tool **dogfooded itself** as the primary QA surface — F1 was proven closed
    on the live dogfood graph (aspark-graph-sourced inferred edges 21 → 0), not just
    fixtures. That real-repo witness caught two earlier "fixed" claims that were false
    at HEAD.
  - The thin-adapter convention paid off: the `fastmcp` → `mcp` SDK swap touched only
    `server.py` and the test harness, and CLI≡MCP parity held throughout.
  - Determinism stayed intact across both a query rewrite (inference.py) and a
    dependency swap — the byte-identical double-build test is a high-value guard.
- **What we'd do differently:**
  - Ship smaller: close-the-loop (0.2.0) never released and got bundled into 0.3.0.
    A stuck feature accumulates release risk; prefer shipping each green cycle.
  - The test-harness migration traded away transport-layer fidelity (F1 of
    distributable-install). A single thin transport-level smoke test over a real MCP
    client would keep arg-coercion/serialization covered as the SDK moves.
- **Patterns worth reusing** (candidates for CLAUDE.md / project memory):
  - **Resolve every commit to a feature set *before* id-matching** in git-history
    inference; `.spark/<feature>/` co-touch is authoritative, and an ambiguous
    id-only commit contributes **no** edge (honest absence over a wrong cross-feature
    link). This is the shape that finally closed F1 — worth recording.
  - **Cap the `mcp` SDK `<1.20`** is a standing liability tied to auth; lift only
    alongside an auth feature. Floor is `>=1.12` (lowest verified to expose
    `FastMCP` + `@mcp.tool()` with the directly-callable contract the harness needs).
  - A **QA-gate override for headless CLI/MCP tools** is legitimate when the
    QA-equivalent is done hands-on in review — but record authorizer + reason, never
    silently skip.

---

## ✅ KEEP GATE

*All boxes checked → the loop is closed. The feature is done-done.*

- [x] All pre-flight checks passed at release time (103 passed, byte-identical build, clean-env wheel install verified; QA gate overridden with recorded reason + authorizer)
- [x] Changelog written in user-facing language (no hashes, tickets, or jargon)
- [ ] Release actions executed and verified — **local commit + tag done; outward push/PR/publish PENDING user go (prepare-only pass)**
- [x] Learnings recorded
- [ ] Status set to `released` — currently `preparing` (awaiting go for the outward-facing steps)
