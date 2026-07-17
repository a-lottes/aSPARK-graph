# Release: incremental-builds

| | |
|---|---|
| **Phase** | Keep |
| **Owner** | Release Manager (`/go-live`) |
| **Input** | `review-report.md` (`passed`), QA gate (N/A — see §0) |
| **Status** | `preparing` |
| **Version** | v0.4.0 |
| **Date** | 2026-07-17 |

## 0. Gate Status

### Review gate

`review-report.md` — status: `passed` (2026-07-17). All 9 tasks confirmed done,
all Must ACs (AC-1.x, AC-2.x, AC-3.x) and Should ACs (AC-4.x) and Could ACs
(AC-5.x) verified, all NFRs verified. Two findings resolved before the gate was
closed: F1 (Minor — malformed cache-entry body caused a traceback mid-build;
fixed with a per-entry `try/except` guard degrading to a cache miss) and F2
(Nit — a comment referenced the wrong spec AC; corrected). Suite after fixes:
161 passed, 1 deselected.

### QA gate — N/A override (recorded, not a silent skip)

There is no `qa.md` for this feature. **This is an authorized override,
consistent with v0.3.0 (authorized 2026-07-16) and v0.3.1 (carried forward
2026-07-17), both by Andreas Lottes (andreas@lottes.dev).**

**Reason:** aspark-graph is a headless CLI/MCP tool with no user interface. The
`/demo-day` ceremony (browser-based QA with a human tester observing the UI) is
structurally N/A — there is nothing to observe in a browser. The QA-equivalent
for this tool — full test suite, clean-env packaged install, `serve` boot, byte-
identical double-build, and a live-repo `impact` check — was performed in
`/peer-review` (`review-report.md`, §5). The same override rationale and
authorizer applies to every aspark-graph release until the tool grows a UI
surface (explicitly Out of Scope through v0.4.0+).

**Authorizer:** Andreas Lottes (andreas@lottes.dev). First authorized for v0.3.0
(2026-07-16); carried forward to v0.3.1 (2026-07-17); explicitly carried forward
again here for v0.4.0 (2026-07-17) with the same rationale and authorizer.

---

## 1. Pre-Flight Checks

All checks run fresh on 2026-07-17 against the current working tree. The release
commit has not yet been created — the uncommitted files are the release content.

- [x] `review-report.md` status is `passed`
- [x] QA gate: N/A override recorded above with authorizer and reason (not a silent skip)
- [x] All plan tasks confirmed `done` — T1 through T9 all marked `done` in `plan.md`
- [x] Full test suite green on the release content

  ```
  uv run pytest -q
  161 passed, 1 deselected in 24.70s
  ```

  Run fresh at prepare time (2026-07-17). 161 tests passed: 134 pre-existing
  tests plus 27 new tests in `tests/test_incremental.py` (26 original + 1 for
  the F1 fix). The 1 deselected is the `@pytest.mark.slow` NFR-1 benchmark
  (`tests/test_incremental_bench.py`, T8), correctly excluded by
  `addopts = "-m 'not slow'"` in `pyproject.toml`. The benchmark was run
  separately in `/peer-review` and measured 71.5% speedup (target: ≥50%).

- [x] Current `pyproject.toml` version confirmed `0.3.1` — bump to `0.4.0` pending
- [x] No `v0.4.0` tag collision — `git tag -l v0.4.0` returned empty
- [ ] Working tree clean on release commit (PENDING — uncommitted increment files
  are the release commit content; `git status` shows 3 modified + 4 untracked
  files, all belonging to this increment)
- [ ] Release commit created (PENDING — awaiting user go)

### Version justification

**Minor bump: 0.3.1 → 0.4.0.**

Three additive, backward-compatible changes cross the minor threshold under semver:

1. **New user-visible CLI flag** (`--full` on `aspark-graph build`). Any caller
   that used `aspark-graph build .` before will get the same output; the new flag
   is strictly additive.
2. **New default build behaviour** — the incremental path is active by default
   when prior state exists. First-build behaviour is identical to pre-feature.
   No existing invocation breaks or produces different output.
3. **New public module** `parse_cache.py` exporting `ParseCache` and the named
   exception `CacheUnusable`. Public API surface is wider.

Patch would be wrong (new flag, new behaviour). Major would be wrong (no
breaking change). Semver minor is correct.

---

## 2. Changelog

### Added

- `aspark-graph build .` now completes significantly faster when only a fraction
  of source files changed since the last build. On a 200-file Python repo with
  8% of files changed, the incremental build finished in 71.5% less time than a
  full rescan on the same machine — well past the 50% target. Unchanged files'
  parse results are reused from a local sidecar cache stored at
  `.aspark-graph/parse-cache.json`; no correctness or query accuracy is traded
  for the speed gain. An incremental build produces a byte-identical `graph.json`
  to a full rescan of the same repo state — queries after an incremental build
  are as trustworthy as queries after a full rescan.

- A new `--full` flag on the build command forces a complete rescan regardless of
  any cached state: `aspark-graph build --full .`. Use it in CI to guarantee a
  clean baseline, or when diagnosing unexpected query results. A `--full` build
  replaces the cache with fresh results, so the next plain `aspark-graph build .`
  starts from a clean incremental baseline.

- The build summary now reports whether the build ran incrementally or as a full
  rescan, and how many files were re-parsed vs reused from cache. For example:
  `Built graph: 47 code entities, 12 stories, 31 ACs; incremental: 4 re-parsed,
  196 cached`. Full-rescan and fallback summaries do not report a cached count,
  so there is no ambiguity about whether caching was active.

### Changed

- `aspark-graph build .` (no flags) now defaults to incremental mode when a
  previous build exists. On a first build, after `--full`, or whenever the
  cached state is absent, corrupt, or incompatible with the installed tool
  version, it falls back to a full rescan automatically and prints one line to
  stderr naming the reason. No new error codes, no new failure modes — the
  fallback always produces the same correct graph a plain rescan would.

### Fixed

- A build could fail mid-run with an unhandled error if the parse cache contained
  a valid-JSON but internally malformed entry (for example, after a partial write
  interrupted by a crash). The build now treats any malformed cache entry as a
  per-file cache miss and re-parses that file, so a partially-corrupt cache no
  longer stops the build. (F1, fixed before release.)

---

## 3. Release Actions

All outward-facing actions are **PENDING** — awaiting the user's explicit go.

### Local, reversible work (pre-go)

The increment files are present, reviewed, and tested. The version bump,
`uv.lock` regeneration, CLAUDE.md update, release commit, and local tag are the
first pending steps. All of this is local and reversible.

### Pending commands (execute in order, after user go)

| # | Action | Status |
|---|---|---|
| 1 | Bump `pyproject.toml` version `0.3.1` → `0.4.0` | PENDING |
| 2 | Regenerate `uv.lock` | PENDING |
| 3 | Update `CLAUDE.md` to record `incremental-builds/` trail and v0.4.0 | PENDING |
| 4 | Stage all increment files + version bump + CLAUDE.md | PENDING |
| 5 | Create release commit | PENDING |
| 6 | Create annotated local tag `v0.4.0` | PENDING |
| 7 | Push `main` to `origin` | PENDING |
| 8 | Push tag `v0.4.0` to `origin` | PENDING |
| 9 | Create GitHub Release | PENDING |

**Exact commands:**

```bash
# 1. Bump version in pyproject.toml (edit line 3: version = "0.3.1" → "0.4.0")
#    Use your editor, or:
sed -i '' 's/^version = "0.3.1"/version = "0.4.0"/' pyproject.toml

# 2. Regenerate uv.lock to reflect the version bump
export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"
uv lock

# 3. Update CLAUDE.md — two edits:
#    a) Append the incremental-builds trail entry after the gate-integration line:
#       `gate-integration/` (v0.3.1 — ...), `incremental-builds/` (v0.4.0 — incremental
#       parse cache, --full flag, 71.5% faster builds on large repos).
#    b) Change "Current shipped version: 0.3.1." → "Current shipped version: 0.4.0."

# 4. Stage all increment files
git add pyproject.toml uv.lock CLAUDE.md \
  src/aspark_graph/parse_cache.py \
  src/aspark_graph/build.py \
  src/aspark_graph/cli.py \
  tests/test_incremental.py \
  tests/test_incremental_bench.py \
  .spark/incremental-builds/

# 5. Verify the staged set before committing
git status

# 6. Release commit
git commit -m "$(cat <<'EOF'
feat(incremental-builds): ship v0.4.0 — incremental parse cache, --full flag

Builds on large repos now default to incremental mode: unchanged files reuse
their tree-sitter parse results from .aspark-graph/parse-cache.json; only
changed files are re-parsed. Measured 71.5% speedup on a 200-file / 8%-changed
fixture (target >=50%). --full forces a full rescan and replaces the cache.
Byte-identical graph.json guaranteed by structural reuse of FileExtraction
objects; all 161 tests green.
EOF
)"

# 7. Annotated local tag
git tag -a v0.4.0 -m "aspark-graph 0.4.0 — incremental parse cache, --full flag"

# 8. Push main to origin  [OUTWARD-FACING — requires user go]
git push origin main

# 9. Push tag  [OUTWARD-FACING — requires user go]
git push origin v0.4.0

# 10. Create GitHub Release  [OUTWARD-FACING — requires user go]
gh release create v0.4.0 \
  --title "aspark-graph 0.4.0 — incremental parse cache, --full flag" \
  --notes "$(cat <<'EOF'
## What's new in 0.4.0

**Significantly faster builds on large repos.** `aspark-graph build .` now defaults
to incremental mode: unchanged files reuse their tree-sitter parse results from a
local sidecar cache; only changed files are re-parsed. On a 200-file Python repo
with 8% of files changed, builds ran in 71.5% less time than a full rescan.

The result is byte-identical to a full rescan — queries after an incremental build
are as trustworthy as queries after a full rescan.

## Added
- Incremental build mode active by default when prior build state exists
- `--full` flag to force a complete rescan (`aspark-graph build --full .`)
- Build summary now reports `; incremental: M re-parsed, N cached` when running incrementally

## Changed
- Default `aspark-graph build .` falls back to full rescan automatically when cache
  is absent, corrupt, or version-mismatched — one-line stderr notice, exit 0, always correct

## Fixed
- A partially-corrupt cache no longer stops the build mid-run; malformed entries
  are treated as per-file cache misses

**No breaking changes.** First-build behaviour is identical to v0.3.1. All 161 tests green.

Full changelog: https://github.com/a-lottes/aSPARK-graph/blob/main/.spark/incremental-builds/release-notes.md
EOF
)"
```

### Post-release smoke check (run after push and GitHub Release creation)

```bash
# 1. Confirm the tag exists on the remote
git ls-remote --tags origin v0.4.0

# 2. Confirm the GitHub Release is visible and has the right title
gh release view v0.4.0

# 3. Confirm main is at the release commit
git log --oneline -1

# 4. Re-run the default suite on the released commit — must still be 161/1
export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"
uv run pytest -q

# 5. Confirm the incremental build path works end-to-end on this repo
uv run aspark-graph build .      # first build (full rescan, no cache yet)
uv run aspark-graph build .      # second build (incremental — should say "incremental:")
uv run aspark-graph query staleness   # must report graph as current

# 6. Confirm --full works
uv run aspark-graph build --full .

# 7. Confirm a live query still works after incremental build
uv run aspark-graph query story_trace US-2 --feature incremental-builds
```

---

## 4. Rollback Path

The rollback path is a `git revert` of the release commit on `main`. No migration,
no schema change to `graph.json`, no external service.

**Risk profile:** Low-medium. The incremental path adds a sidecar file
(`.aspark-graph/parse-cache.json`) that is already gitignored. Rolling back
removes the incremental behaviour but leaves `graph.json` intact and all queries
functioning identically to v0.3.1.

**Steps to roll back after push:**

```bash
# 1. Revert the release commit (new commit — safe for shared history)
git revert HEAD --no-edit
git push origin main

# 2. Delete the remote tag
git push origin :refs/tags/v0.4.0

# 3. Delete the local tag
git tag -d v0.4.0

# 4. Archive or delete the GitHub Release
gh release delete v0.4.0 --yes

# 5. Optionally remove the sidecar cache from any affected working trees
#    (it is gitignored and harmless to leave, but causes no-op overhead)
rm -f .aspark-graph/parse-cache.json
```

After rollback the repository is at v0.3.1 state. All v0.3.1 `graph.json`-based
queries work identically; the sidecar cache file is inert (gitignored and ignored
by v0.3.1 code). No data loss.

---

## 5. Learnings (Keep!)

### What went well

- **The anchor-guard design made correctness trivial to argue.** Keying the cache
  load on `graph.json` existence (`build.py:79`) meant the first-build, missing-
  graph, and no-prior-state paths all collapsed into the proven full-rescan flow
  with no special-casing. The reviewer noted it: "the `graph.json`-anchor rule is
  the quiet star of the design." A feature that reduces its own state space by
  design is a feature that earns trust fast.

- **Caching the `FileExtraction` (not the graph fragment) made byte-identity
  structural, not coincidental.** Because the same `FileExtraction` object feeds
  the same downstream steps regardless of whether it came from cache or from the
  extractor, byte-identical `graph.json` follows by construction. This is a pattern
  worth repeating: cache at the boundary where the output shape is already defined,
  not at a post-assembly layer where identity requires a separate proof.

- **The seven-state enumeration in C16 was the right forcing function.** Writing
  out all seven build states in the spec (first build, absent graph, incremental
  some-changed, incremental zero-changed, `--full`, corrupt-cache fallback,
  version-mismatch fallback) meant the test matrix was already complete before the
  first line of implementation. The reviewer found every state covered by a test.
  Enumerating states at spec time costs minutes; finding a gap at review time costs
  a reopen.

- **F1 and F2 were caught and fixed before the gate closed, not filed as follow-on
  tickets.** The discipline from v0.3.1 (fix obvious issues at review time)
  applied again: the entry-body deserialization gap (F1) was a real NFR-3 residual
  that merited a test and a guard, not a "we'll handle it later." Shipping with a
  known traceback path in new code is avoidable debt.

- **The `@pytest.mark.slow` exclusion pattern kept the fast suite fast.** The
  NFR-1 benchmark (T8) is a real wall-clock test that takes seconds and is
  machine-sensitive. Registering `slow` as a marker and excluding it from
  `addopts` preserved the per-commit feedback loop without removing the benchmark
  from the repo. This is the right pattern for any performance test that is a
  release gate rather than a commit gate.

- **The ADR's "alternatives considered" table earned its keep.** The reviewer read
  the rejected alternatives (SQLite, pickle, cached graph fragments, in-memory
  only) and found them each clearly disqualified. Writing the rejected path
  explicitly avoids re-litigating the same decisions in the next cycle and signals
  that the chosen approach was not the first idea — it was the surviving one.

### What we'd do differently

- **The benchmark fixture file size was wrong on the first attempt.** The
  synthetic benchmark started with 8-line files, produced only 12% speedup (parse
  cost was negligible vs I/O overhead), and had to be revised to 100-line files
  (10 classes × 8 methods each) to reach 56.9% / 71.5%. The A2 assumption (parse
  dominates) holds for realistic module sizes, not for trivially small files. For
  future performance-oriented features: define the benchmark fixture with
  realistic content from the start, not from whatever is fast to generate. The
  spec's A2 escape valve ("if the EM discovers inference dominates, surface it
  before sprint commit") is the right safety — but the fixture size choice should
  be validated earlier, not after a benchmark failure.

- **The stale `__version__ = "0.1.0"` in `__init__.py` is a persistent hazard.**
  The plan correctly flagged using `importlib.metadata.version(...)` instead of
  `__init__.__version__` for the cache version tag, and the implementation follows
  it. But the stale string is still there and will confuse the next engineer who
  reads it. The right outcome is a follow-up task to either remove
  `__init__.__version__` or keep it in sync — not to document the workaround in
  perpetuity.

- **`test_first_build_no_cache_no_error` needed an assertion adjustment** because
  `build_graph()` does not save `graph.json` (the CLI does). This is the second
  time a test assumed CLI behaviour in a unit context (a similar issue appeared in
  v0.2.0). The fix is easy; the pattern is worth flagging: tests of `build_graph()`
  should assert only on the `BuildReport` return value and the state of objects
  directly written by the function, not on side effects that the CLI adapter layer
  performs.

### Patterns worth reusing (CLAUDE.md / memory candidates)

- **Enumerate states at spec time, not at test time.** The C16 seven-state
  enumeration for the build turned a complex state space into a complete test
  matrix before implementation started. For any feature with a non-trivial
  fallback or branching path: enumerate all reachable states in the Clarify pass
  of the spec, number them, and reference the numbers in the plan and tests.
  Candidate for CLAUDE.md under "Spec patterns."

- **Cache at the boundary where output shape is already defined.** Caching
  `FileExtraction` (the extractor's output contract) rather than graph fragments
  (a post-assembly artifact) made correctness structural. When adding a cache to a
  pipeline: identify the layer whose output shape is stable and well-tested, and
  cache there. Caching downstream makes correctness harder to prove; caching
  upstream (before assembly) means the rest of the pipeline is unchanged.
  Candidate for CLAUDE.md under "Architecture patterns."

- **Anchor the cache load on a canonical artifact.** Requiring `graph.json` to
  exist before attempting to load the parse cache (the anchor-guard pattern) meant
  zero special-casing for "no prior state." Any feature that adds a supplemental
  sidecar (cache, index, snapshot) should identify the canonical artifact it tracks
  and gate the sidecar load on that artifact's presence. Candidate for CLAUDE.md
  under "Architecture patterns."

- **`@pytest.mark.slow` exclusion for wall-clock benchmarks.** Register a `slow`
  marker, exclude it from `addopts`, and document the explicit run command. The
  benchmark stays in the repo (reviewable, versioned, runnable on demand) without
  slowing the per-commit suite. Candidate for CLAUDE.md under "Testing patterns."

- **Fix obvious issues at review close, do not file tickets.** F1 and F2 in this
  cycle, F1–F5 in v0.3.1: the discipline of fixing Minor/Nit findings before
  setting the gate to `passed` prevents known-bad code from reaching the release
  commit. The threshold: Minor and below with a clear, non-invasive fix → fix now.
  Major or above → return to `/increment`. Already implicit in the process; worth
  making explicit in CLAUDE.md's review guidance.

---

## KEEP GATE

*All boxes checked → the loop is closed. The feature is done-done.*

- [x] All pre-flight checks passed at release time (test suite 161/1 green; version confirmed 0.3.1 → bumping to 0.4.0; no v0.4.0 tag collision; all plan tasks done; review gate `passed`; QA gate override recorded with authorizer)
- [x] Changelog written in user-facing language
- [ ] Release actions executed and verified (PENDING — awaiting user go; exact commands written above)
- [x] Learnings recorded
- [ ] Status set to `released` (update this and the header after the go is given and smoke check passes)
