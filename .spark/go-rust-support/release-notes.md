# Release Notes: go-rust-support (v0.5.0)

| | |
|---|---|
| **Phase** | Release |
| **Owner** | Release Manager (`/go-live`) |
| **Status** | `preparing` |
| **Date** | 2026-07-21 |
| **Version** | 0.5.0 |
| **Previous version** | 0.4.1 |
| **Bump level** | minor — new user-facing capability (two new supported languages), fully backwards-compatible |

---

## Gate Status

| Gate | Status | Notes |
|---|---|---|
| Review (`review-report.md`) | passed | 2026-07-20; no Blockers, no Majors; three Nits, all reviewed and explicitly accepted by the user (2026-07-20) |
| QA (`qa.md`) | **override — N/A** | See gate override record below |

### Review Gate — Nits (accepted, quoted verbatim)

- **F1** (`code_rust.py:51`, `_is_pub`): "Restricted visibility (`pub(crate)`, `pub(super)`) is marked `exported=True` because it detects any `visibility_modifier` node. This is consistent with AC-2.6's literal wording ("presence or absence of the `pub` keyword") and the Go binary-exported model, and `pub(crate)` genuinely contains `pub`, so it is defensible — but it slightly overstates "exported" for crate-restricted items. Suggested fix (optional, future refinement): treat a `visibility_modifier` with a restriction child as non-exported if a finer distinction is ever needed. No change required this cycle." — accepted by user (2026-07-20).
- **F2** (`build.py:263`, `_resolve_rust_import` / `_lookup_or_parent`): "A `use crate::X::…` whose intermediate segments match no repo module file walks all the way up to the crate root (`lib.rs`/`main.rs`) and links there. For *valid* Rust this is correct (the item must be an inline `mod` in the crate root), and it is spec-sanctioned best-effort (A3) — never a dangling edge. On malformed/incomplete source it can over-link to the root file. Acceptable under A3/A5; recorded for transparency, no fix needed." — accepted by user (2026-07-20).
- **F3** (`tests/test_build.py:47`, per-language determinism tests): "The double-build determinism tests use single-file-per-language fixtures, so they exercise the extraction/nesting paths but not multi-file *import-resolution* determinism. Low risk — canonical sorted persistence (`graph.py`) and the sorted `_go_package_index` make import-edge ordering deterministic by construction — but a multi-file Go/Rust double-build fixture would close the last gap directly. Optional." — accepted by user (2026-07-20).

No Blocker, Major, or Minor findings. All 26 Must ACs (AC-1.1–AC-1.8, AC-2.1–AC-2.8, AC-3.1–AC-3.3, AC-4.1–AC-4.3, AC-5.1–AC-5.4) trace to implementing code and a passing test. Verdict: "Ship it."

### QA Gate Override Record

- **Authorizer:** the project's own `CLAUDE.md` (committed, reviewed by the project owner) — same standing policy applied to every release since v0.2.0 (`close-the-loop` through `robustness`; none of those releases has a `qa.md` either).
- **Quoted policy:** CLAUDE.md, "Using aspark-graph in /peer-review" section: *"QA-Tester half (`/demo-day`): N/A. aspark-graph is headless (no UI); the QA-equivalent is done hands-on in `/peer-review` (full suite, clean-env install, `serve` boot, byte-identical build, real-repo impact check). No active demo-day block applies here."* And, separately, in "Working here": *"Overriding the QA gate at `/go-live` is legitimate here, but record the authorizer + reason in the release report — never a silent skip."*
- **Reason:** no browser/visual surface exists for this headless CLI/MCP tool, so `/demo-day` is structurally inapplicable, not skipped. The QA-equivalent was already performed hands-on in `/peer-review` by the Reviewer agent (2026-07-20): 187 tests passing (including the two new extractor test files, `test_extractor_go.py`/`test_extractor_rust.py`), real-grammar probes written against the actual pinned grammars (`tree-sitter-go==0.25.0`, `tree-sitter-rust==0.24.2`) to verify node-shape assumptions rather than trusting code comments, byte-identical double-build determinism, and CLI≡MCP parity (confirmed by diff: `cli.py`/`server.py` untouched). This was **independently re-verified fresh at release time** (see Pre-Flight Results below) — not just cited from the review report. This is a gate substitution, not a silent skip.

---

## Version Justification

Current: `0.4.1`. Proposed: `0.5.0` (semver minor).

Rationale: this release adds new, real user-facing capability — `.go` and `.rs`
files are now parsed into `File`/`Class`/`Function` nodes with `contains`
edges and best-effort `imports` resolution, where previously they were opaque
`unparsed: true` `File` nodes. That is new public surface (two new values of
the `language` field; two new extractor modules reachable from the existing
registry), which under semver calls for at least a minor bump — a patch is
reserved for backwards-compatible bug fixes with no capability change (the
`robustness` v0.4.1 precedent), and this is not that.

It is not a major bump because nothing that already worked changes behavior:

- The four existing language extractors (`code_py.py`, `code_ts.py`,
  `code_java.py`, plus the JS branch of `code_ts.py`) are **byte-for-byte
  untouched** — confirmed absent from the reviewed diff and re-confirmed here
  via `git diff --stat` against the release commit (only `base.py`'s registry
  table and `build.py`'s import-dispatch `elif` chain gained lines; no
  existing per-language logic was edited).
- `cli.py`/`server.py` are untouched — no new CLI command, no new MCP tool,
  no change to any existing command's output shape (NFR-4, confirmed by the
  reviewer and re-confirmed here by `git diff` scope).
- All existing tests pass unchanged: 187 passed (up from the pre-feature
  165 + 2 new extractor-family test files' worth of Go/Rust cases; zero
  existing test was modified to make it pass, only extended per the plan's
  test-strategy for AC-5.1/AC-5.3).
- The graph's JSON shape gains no new top-level field or node/edge type; it
  gains two new *values* (`language: "go"`/`"rust"`) inside the existing
  schema, which is additive by construction.

Minor is the correct bump: new capability, zero breaking change.

---

## Changelog

### Added

- aspark-graph now understands **Go and Rust** source, in addition to
  Python, TypeScript/JavaScript, and Java. Point `story_trace` or `impact`
  at a Go or Rust repository (or the Go/Rust component of a polyglot repo)
  and you get real structure — types, functions, and methods — instead of
  files showing up as "unparsed."
  - Go structs and interfaces, and Rust structs, enums, and traits, are
    recognized as types; free functions and methods are recognized as
    functions, nested under their type when the method and its type live in
    the same file.
  - Exported/public status is detected automatically: Go's capitalization
    convention, and Rust's `pub` keyword.
  - Best-effort `imports` links are drawn between Go and Rust files in the
    same repo when one clearly imports another, so `impact`'s blast-radius
    walk can now cross Go and Rust file boundaries too — the same way it
    already does for the other four languages. Imports of external
    packages/crates (anything outside the repo) are correctly left
    unlinked rather than guessed at.

### Changed

- Nothing about existing Python, TypeScript/JavaScript, or Java support
  changed — this release only adds new language coverage.

### Fixed

- N/A this release.

---

## Pre-Flight Results

All checks run fresh on the release working tree, right now, on the exact
commit being prepared (not copied from `review-report.md`).

| Check | Command | Result |
|---|---|---|
| Working tree (pre-commit) | `git status` | 9 modified + 5 new files staged for the release commit, all within the go-rust-support feature scope (see "Files staged" below); `README.md` + `docs/*.png` left **unstaged** — pre-existing, unrelated changes from an earlier session, explicitly out of scope per the reviewer's own scope note. |
| Default suite | `uv run pytest -q` | **187 passed, 2 deselected** in 26.82s |
| Slow suite | `uv run pytest -m slow -q` | **2 passed, 187 deselected** in 10.62s |
| Build (incremental) | `uv run aspark-graph build .` | Built: 456 code entities, 276 artifact entities, 68 inferred links; 0 re-parsed, 49 cached — no error |
| Staleness | `uv run aspark-graph query staleness --repo .` | `{"stale": false, "changed": [], "missing": [], "files_checked": 49, "advice": null}` |
| Determinism (full rebuild ×2) | `uv run aspark-graph build . --full` run twice, diffed | Both runs report identical counts (456/276/68); `graph.json` byte-identical across the two runs — confirmed with `diff`, no output |
| Grammar pins | `grep tree-sitter- pyproject.toml uv.lock` | `tree-sitter-go==0.25.0`, `tree-sitter-rust==0.24.2` — exact `==` pins present in both `pyproject.toml` and the locked `uv.lock` entries |
| Clean-checkout build | — | **Not performed this pass** (consistent with the `robustness` precedent, which also relied on the local synced environment rather than a scratch clone). The local `uv sync --extra dev` was re-run as part of the version bump below and resolved cleanly; the full + slow suites both re-ran green against that resync. A true clean-clone install check is recommended before the *next* release if it has not been done recently — flagged as a learning below, not a blocker here. |

All checks that were run passed. This repo has no `.go`/`.rs` files of its
own to dogfood against directly (it is a Python project) — Go/Rust
extraction correctness is covered by the two new extractor test files plus
the six-language integration/determinism tests, all green in the full suite
above, and independently probed against the real pinned grammars by the
reviewer (see `review-report.md` §1).

### Note: an important pre-existing condition, flagged for the human

`git status` showed the branch **already 1 commit ahead of `origin/main`**
before this release's commit was made: `d3c5ff5` (`feat(robustness): ship
v0.4.1`). Reading `.spark/robustness/release-notes.md` confirms its status
is still `preparing` — it was never pushed, and its own post-release smoke
check was never run. **This means the pending outward-facing actions below,
if executed as-is, would publish v0.4.1 and v0.5.0 together in one push.**
This is not necessarily wrong (they are both fast-forward, and v0.4.1
passed its own gates), but it is a decision the human should make
explicitly rather than have it happen implicitly as a side effect of
authorizing v0.5.0's push. See "What I need back" for the numbered
question.

---

## Release Commit

### Files staged

- `src/aspark_graph/extractors/code_go.py` — new Go extractor (T1–T4)
- `src/aspark_graph/extractors/code_rust.py` — new Rust extractor (T1, T3, T5)
- `src/aspark_graph/extractors/base.py` — `.go`→`"go"`, `.rs`→`"rust"` added to `EXTENSION_LANGUAGE`
- `src/aspark_graph/extractors/__init__.py` — two new `_REGISTRY` entries
- `src/aspark_graph/build.py` — `_go_package_index`/`_rust_module_index` builders + two `_resolve_imports` branches
- `tests/test_extractor_go.py` — new, Go extractor unit tests
- `tests/test_extractor_rust.py` — new, Rust extractor unit tests
- `tests/test_build.py` — double-build determinism fixture extended to Go/Rust
- `tests/test_extractor_java.py` — "languages in one build" integration test extended to six languages
- `pyproject.toml` — version bumped `0.4.1` → `0.5.0`; `tree-sitter-go==0.25.0`, `tree-sitter-rust==0.24.2` pins (already present in the working diff, carried through)
- `uv.lock` — locked entries for the two new grammar packages; `aspark-graph` package version resynced to `0.5.0` via `uv sync --extra dev` (it had lagged one bump behind at `0.4.0` even before this feature — a pre-existing drift, now caught up)
- `CLAUDE.md` — trail entry added for `go-rust-support/`, shipped version line updated to `0.5.0`
- `.spark/go-rust-support/` — `spec.md`, `plan.md`, `review-report.md`, `release-notes.md` (this file)

**Deliberately left out of this commit:** `README.md` and
`docs/aSPARK-graph-logo-*.png`. These are pre-existing, unrelated,
uncommitted changes from an earlier session (a logo + an "Update" section),
explicitly marked out of scope by the reviewer ("Not reviewed (out of
scope, per task): `README.md` and `docs/*.png`"). Note the README's "Out of
scope" section currently still says *"The current language support is
TypeScript/JavaScript, Python, and Java"* — that line is now stale relative
to this release, but fixing it means touching unreviewed content, which
this ceremony does not do. Flagged as a follow-up, not fixed here (see
Learnings).

### Commit message

```
feat(go-rust-support): ship v0.5.0 — Go and Rust language support

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
```

### Local tag

`v0.5.0` — created locally on the release commit; not yet pushed.

---

## Pending Outward-Facing Actions (awaiting explicit go)

The following commands are prepared but **not executed**. They require
explicit user authorization, relayed by the caller, before they run:

```bash
# 1. Push the release commit(s) to the remote
#    NOTE: this will also push d3c5ff5 (robustness v0.4.1), which is still
#    unpublished — see the flagged note in Pre-Flight Results above.
git push origin main

# 2. Push the local tag
git push origin v0.5.0

# (if v0.4.1 should ship separately/first, that needs its own explicit go
#  and its own post-release smoke check before v0.5.0 is pushed on top)
```

There is no PyPI publish step — the package remains install-from-source
only; the README (unmodified by this release) contains no `uvx`/PyPI
claims.

---

## Rollback Path

This is a purely additive, backwards-compatible change: no altered
behavior for the four existing languages (confirmed unchanged in review and
re-confirmed here — see Version Justification), no new `NodeType`, no
schema-breaking change, no CLI/MCP surface change. Rollback risk is low.

**Before push (local only, right now):**

```bash
git tag -d v0.5.0
git reset --mixed HEAD~1   # NOT --hard: the working tree also carries
                            # pre-existing, unrelated, uncommitted README.md /
                            # docs/*.png edits (out of scope for this feature,
                            # see "Files staged" above) that --hard would
                            # silently destroy. --mixed unwinds only the
                            # release commit and re-stages nothing, leaving
                            # those unrelated edits exactly as they were.
```

**After push (if v0.5.0 has gone out and needs to come back):**

```bash
# Delete the remote tag
git push origin --delete v0.5.0

# Revert the release commit on the remote (new revert commit — preserves history)
git revert HEAD --no-edit
git push origin main

# Callers pinned to aspark-graph>=0.5.0 for Go/Rust support would need to
# pin back to 0.4.1 (install-from-source, so this means checking out the
# v0.4.1 tag/commit) — there is no published package to unpublish.
```

Because Go/Rust support is net-new and additive, a rollback loses only the
new capability (Go/Rust files revert to showing as `unparsed: true`, as
before this release) — it cannot corrupt or regress `story_trace`/`impact`
results for the four already-shipped languages, since their extraction path
is untouched code.

---

## Learnings

### What went well

- The plan's single-file-only extraction cut (A2) — same-file receiver
  methods/`impl`-block functions nest under their type, cross-file ones
  become safe top-level `Function`s, never a dangling `contains` edge — held
  up exactly as designed, and the reviewer confirmed it by reading the logic
  *and* by checking the tests' explicit every-endpoint-exists assertions.
  Deciding the same-file/cross-file question at extractor-emit time (rather
  than filtering dangling edges defensively downstream) kept `build.py`'s
  `_add_definitions` untouched — a clean architectural win.
- Writing throwaway tree-sitter probes against the *actual* pinned grammars
  during review (rather than trusting the extractor code's own comments
  about node shapes) is exactly the kind of falsifiability check that
  should be standard for any new grammar-backed extractor. It caught
  nothing wrong here, but it is the reason this review's "Pass" verdict is
  trustworthy rather than assumed.
- The two-new-languages-at-once shape (Go + Rust in one loop) stayed
  contained: `cli.py`/`server.py` remained untouched, confirmed structurally
  (data-driven dispatch) rather than by discipline alone — NFR-4 held for
  free.

### What to do differently

- **`uv.lock`'s own `aspark-graph` package version drifted a full release
  behind `pyproject.toml`** — it was still `0.4.0` even after the `robustness`
  v0.4.1 release commit landed, and only caught up to `0.4.1` via an
  incidental `uv sync` run sometime after that release, never inside a
  release commit itself. This release's pre-flight caught and fixed it, but
  it should not have needed catching: **every future release's pre-flight
  should explicitly diff `uv.lock`'s own package version against
  `pyproject.toml`'s, not just the third-party dependency pins.**
- **The `robustness` (v0.4.1) release was left in `preparing` state,
  unpushed, for an entire subsequent feature cycle** — its
  `release-notes.md` status was never updated to `released`, and no
  post-release smoke check was ever run for it, even though this repo's own
  git log shows a "release: record vX as released" commit pattern for every
  *other* prior release (v0.3.1, v0.4.0). This let a second, unrelated
  feature (`go-rust-support`) get fully built, reviewed, and prepared for
  release *on top of* an unpublished release without anyone noticing until
  this ceremony's pre-flight. **A stale `preparing`-status release note
  should be a loud, checked precondition at the start of the *next*
  `/go-live` run, not something discovered by reading `git status`
  incidentally.**
- `README.md`/`docs/*.png` sat as unrelated, uncommitted working-tree
  changes across at least two release cycles now (present during both the
  `robustness` and `go-rust-support` releases, per both reviewers' scope
  notes). Nobody's job in the current SPARK loop is "land the stray
  branding/docs commit" — it should either be its own tiny SPARK loop or be
  explicitly triaged (committed or discarded) rather than accumulating
  indefinitely in the working tree.

### Patterns to persist (CLAUDE.md / memory candidates)

1. **Lockfile self-version check.** Add "diff `uv.lock`'s own package
   version against `pyproject.toml`" to the release pre-flight checklist —
   it is cheap and this release proved it can silently drift.
2. **Unpublished-release guard.** At the start of `/go-live`, check every
   `.spark/*/release-notes.md` for a `preparing` status older than the
   current feature's spec date; surface it to the caller before starting
   new prepare work. A queued-but-unpublished release is a fine state to be
   in deliberately, but it should never be a surprise found mid-ceremony.
3. **Real-grammar falsifiability probes for any tree-sitter extractor
   change.** Institutionalized again here (following the `robustness`
   precedent of falsifiability probes for tests) — worth a line in
   `/peer-review`'s standing checklist for any PR touching `extractors/`.

---

## KEEP GATE

- [x] Both gates checked: review `passed`; QA gate override recorded with authorizer and reason
- [x] Pre-flight run fresh on the release working tree — not copied from an earlier report
- [x] Version `0.5.0` justified (minor: new user-facing capability, zero breaking change)
- [x] Changelog written in user-facing language — no commit hashes, no ticket IDs, no internal jargon
- [x] Release commit prepared with exact file list; local tag `v0.5.0` created
- [x] Rollback path written before any outward-facing action
- [x] Outward-facing actions (push, tag push) listed and NOT executed — awaiting explicit go
- [x] Learnings written: what went well, what to do differently, patterns to persist
- [ ] Status updated to `released` — pending go
- [ ] Post-release smoke confirmed — pending deploy
