# Spec: incremental-builds

| | |
|---|---|
| **Phase** | Specify |
| **Owner** | Product Owner (`/story-time`), Designer (`/look-and-feel`) |
| **Status** | `approved` |
| **Date** | 2026-07-17 |

## 1. Problem & Goal

- **Problem:** Every call to `aspark-graph build .` triggers a full rescan of
  every source file in the repo, regardless of how many files changed since the
  last build. On a large repo — the class of repo the gate-integration work
  (v0.3.1) is now explicitly targeting — this costs seconds to tens of seconds
  per build. In an agent workflow where the graph is rebuilt after every edit
  cycle to keep queries current, that cost multiplies by the number of loops. The
  result is that agents either tolerate the wait (friction) or skip rebuilding
  (stale graph, which the v0.2.0 staleness work explicitly warned about). The
  full-rescan-every-time model was a consciously accepted assumption in v0.1.0
  (A6: "acceptable performance for v0.1.0") and a named Tier-1 candidate for a
  future cycle; that future cycle is this spec.

- **Goal:** `aspark-graph build .` on a repo where only a subset of files changed
  since the last build completes significantly faster than a full rescan, while
  producing a result that is **identical** to what a full rescan of the same repo
  state would produce. Faster builds with no change to query correctness; the
  full-rescan path remains available as a fallback and escape hatch.

- **Success signal (observable):**
  1. On a repo with 200 or more source files where ≤10% of those files changed
     since the previous build, the incremental build command completes at least
     50% faster in wall-clock time than a full rescan on the same machine,
     as measured by timing both commands on the EM-defined benchmark fixture
     (NFR-1).
  2. The graph produced by an incremental build on a given repo state is
     byte-identical in `graph.json` to the graph a full rescan of the same state
     produces. The existing double-build determinism test stays green (A3).
  3. When no prior build state exists (first run, or after `--full`), the build
     behaves exactly as today's full-rescan build — no new failure mode, no new
     output format.

- **Why now:** gate-integration (v0.3.1) wires the graph into real agent
  workflows. The value of the integration is proportional to graph freshness;
  freshness costs a rebuild; on large repos that rebuild tax compounds. The
  feature is a named Tier-1 candidate in CLAUDE.md. Honest caveat: on the
  aspark-graph repo itself, the full rescan is already fast — the pain is
  hypothetical for future adopters on larger repos. If we never build this,
  agents tolerate the wait or query stale graphs; the tool still works correctly.
  This is an accelerant, not a correctness fix.

## 2. Target Users

- **Primary: the agent (or supervising developer) running repeated
  `aspark-graph build .` → query cycles on a repo with hundreds to thousands of
  source files**, where only a few files change per cycle. This is the user who
  pays the full-rescan tax most often and would benefit most from incremental
  caching.
- **Secondary: the CI operator** who needs a guaranteed-clean build on every run
  regardless of any cached state — they need an escape hatch (`--full`) to force
  a rescan.
- **Explicitly NOT a target this spec:** users wanting live file-watching
  (continuous rebuild on file-system events — Out of Scope), users wanting
  team-shared build caches (Out of Scope), or users on small repos where the
  full-rescan is already sub-second (they are unaffected; the feature is
  transparent).

## 3. Assumptions & Open Questions

<!-- Every assumption is a risk. Open questions block the gate until answered or explicitly accepted. -->

| # | Assumption / Question | Resolution |
|---|---|---|
| A1 | The idea arrived partly as a solution: "SQLite / incremental builds — persist the graph in SQLite instead of (or alongside) graph.json." This spec records the underlying need — fast incremental builds with correctness and determinism preserved — and leaves the mechanism (what data to cache, how to store it, whether SQLite is used at all) to `/sprint-plan`. The user's original phrasing is preserved here. | Accepted as assumption |
| A2 | The dominant build cost is tree-sitter parsing (per-file). Graph serialization (writing graph.json) and in-memory import resolution are expected to be fast by comparison. This is consistent with the Q2 resolution (inference caching deferred): if the `git log` subprocess were the bottleneck, parse-cache-only caching would not achieve the NFR-1 target. If the EM discovers during `/sprint-plan` that inference dominates on the specific fixture, they should surface it before committing to the implementation — the NFR-1 target is the safety valve. | Accepted as assumption; EM to validate against the benchmark fixture before sprint commit |
| A3 | **The byte-identical double-build test is a non-negotiable inherited from prior cycles (CLAUDE.md: "keep it").** This spec does NOT authorize replacing `graph.json` as the canonical graph output. Any parse/build cache introduced by this feature is supplemental to `graph.json`, not a replacement for it. A "replace graph.json with SQLite as the query store" design is a separate scope requiring its own spec. Scoping this spec to "alongside" resolves the user's "instead of (or alongside)" phrasing in favor of the side that preserves the non-negotiable. | Accepted as a binding scope constraint — "alongside" only |
| A4 | The build already computes a SHA-256 content hash per file and stores it as a graph node attribute (v0.2.0, staleness check). Hash comparison is therefore available without a new hashing step; the question is purely whether the extractor step can be skipped when the hash matches a cached result. | Accepted as assumption |
| A5 | An incremental build must produce a result **equivalent to a full rescan for the same repo state**. This is a correctness requirement, not a goal to relax. If a given caching strategy cannot guarantee this equivalence for all inputs, it must fall back to a full rescan rather than serve a wrong graph. | Binding correctness requirement (US-2) |
| A6 | When the incremental state is absent, corrupt, or incompatible with the current tool version, the build falls back to a full rescan automatically. The caller is notified (one-line message to stderr) but no error is raised. This is the correct failure mode: the user gets a valid (if slower) result, never a wrong one. | Binding reliability requirement (US-3) |
| A7 | **The parse cache covers tree-sitter extraction only.** The four steps of `build_graph()` are: (1) tree-sitter extraction per source file — **cached**; (2) import resolution over all extractions — **not cached, runs every build**; (3) `.spark/` artifact parsing — **not cached, runs every build**; (4) git inference (`infer_implements`) — **not cached, runs every build** (Q2). Steps 2–4 are cross-file or repo-level, fast relative to step 1, and cannot be safely skipped per-file without dependency tracking. This is the scope boundary for "incremental." | Binding scope constraint — see C13 |
| Q1 | **Performance target.** What concrete speedup threshold makes this feature a success? | **RESOLVED (2026-07-17):** ≥50% faster in wall-clock time on a repo with 200+ source files where ≤10% changed since the last build. NFR-1 and AC-1.2 updated accordingly. |
| Q2 | **Is git-history inference in scope for the incremental path?** The `infer_implements` step runs a `git log --no-merges --name-only` subprocess reading ALL non-merge commits from HEAD. On a repo with a deep history this may be as slow as or slower than tree-sitter parsing of changed files, making parse-cache-only insufficient for the stated goal. | **RESOLVED (2026-07-17): Out of Scope this cycle.** Only tree-sitter file-level parse caching is in scope. Inference runs unchanged on every build. Inference caching is a separate future feature. See §6. |

## 4. User Stories

<!-- MoSCoW priority: Must / Should / Could / Won't. Every story needs testable acceptance criteria.
     Story and AC IDs (US-n, AC-n.m) are stable — never renumber; add new at the end. -->

### US-1 (Must): Skip unchanged files in a rebuild

> As the agent developer, I want `aspark-graph build .` to detect which files
> changed since the last build and skip re-parsing the unchanged ones, so that
> repeated builds in an edit-then-query loop are fast on large repos.

**Acceptance criteria:**

- [ ] AC-1.1: Given a repo that has been built previously and where a subset of
  source files have changed, when I run `aspark-graph build .`, then the command
  completes and exits 0. Changed files are re-parsed via tree-sitter; unchanged
  files have their extraction results reused from cache without invoking the
  extractor.
- [ ] AC-1.2: Given the EM-defined benchmark fixture (200+ source files, ≤10%
  changed since the last build — fixture defined in `/sprint-plan`), when I
  measure the wall-clock time of `aspark-graph build .` (incremental) vs.
  `aspark-graph build --full .` (full rescan) on the same machine and Python
  interpreter, then the incremental build completes in **≤50% of the full-rescan
  wall-clock time** (i.e. at least 50% faster).
- [ ] AC-1.3: Given a repo where no source files have changed since the last
  build, when I run `aspark-graph build .`, then the build completes at least as
  fast as the single-file-changed scenario (zero files are unnecessarily
  re-parsed) and exits 0 without error.
- [ ] AC-1.4: Given a built graph and then one or more source files changed on
  disk, when I run `aspark-graph build .` followed by
  `aspark-graph query staleness`, then staleness reports the graph as current —
  the incremental build correctly updates the stored content hashes for all
  changed files in the resulting `graph.json`.

### US-2 (Must): Incremental output is identical to a full rescan for the same repo state

> As the agent developer, I want the output of an incremental build to be
> indistinguishable from a full rescan of the same repo state, so that I can
> trust query results from an incremental build exactly as much as from a full
> rescan — with no silent inaccuracy.

<!-- This is the correctness story. Its ACs directly uphold the determinism
     non-negotiable (CLAUDE.md AC-1.2) and A5 above. It is a separate story from
     US-1 because it addresses a distinct user concern (trust, not speed) and the
     constraint is binding even if the EM chooses a simpler cache mechanism. -->

**Acceptance criteria:**

- [ ] AC-2.1: Given a repo whose files have not changed, when I run the build
  command twice in sequence, then the second build produces a `graph.json` that is
  **byte-identical** to the first — the existing double-build determinism test
  passes without modification. (A3: `graph.json` remains the canonical output;
  the test is kept, not replaced.)
- [ ] AC-2.2: Given a repo state S, when I run `aspark-graph build --full .` on S
  and then `aspark-graph build .` on the same state S (no files change between
  the two runs), then the resulting `graph.json` files are **byte-identical** —
  the incremental path produces the same canonical serialization as the
  full-rescan path for identical input. (This is a new test to be added to the
  suite alongside the existing double-build test — see C21.)
- [ ] AC-2.3: Given an incremental build completes successfully, when I run
  `aspark-graph query impact <any file>` or
  `aspark-graph query story_trace <any story>`, then the result is identical to
  what the same query returns after a full rescan of the same repo state — no
  story, AC, or code entity is missing or spurious due to incremental caching.
- [ ] AC-2.4: Given the tree-sitter grammar versions and core are pinned (`==`) in
  `pyproject.toml` (existing non-negotiable), when any of those pinned versions
  changes (detectable via a version tag stored in the cache — see C14), then the
  next build treats the cache as incompatible, falls back to a full rescan per
  US-3, and produces a correct graph. Parse results cached under a different
  parser version are never served.

### US-3 (Must): Automatic full-rebuild fallback when incremental state is missing, corrupt, or incompatible

> As the developer or agent, I want the build to fall back to a full rescan
> transparently when no incremental state exists, when the state is corrupt, or
> when the tool version has changed since the state was last written, so that the
> build never silently returns a wrong or partial graph due to a bad cache.

<!-- Without this story the feature is unreliable: a corrupt or stale cache could
     serve a wrong graph with no indication. The fallback makes incremental caching
     a pure optimization that never changes the failure modes the caller sees.
     This is Must, not Should, because correctness depends on it. -->

**Acceptance criteria:**

- [ ] AC-3.1: Given no previous build has been run on this repo (first-ever
  build), when I run `aspark-graph build .`, then it performs a full rescan and
  produces a correct, complete graph — identical behaviour to the current
  pre-feature `aspark-graph build .`. No error, no "missing cache" warning.
- [ ] AC-3.2: Given a corrupt or unreadable cache (e.g., the cache file is
  truncated or its content fails an integrity check), when I run
  `aspark-graph build .`, then the build discards the cache, falls back to a
  full rescan, emits **one line to stderr** naming the fallback reason (e.g.,
  "parse cache unreadable — running full rescan"), exits 0, and produces a
  correct graph. No traceback, no wrong result.
- [ ] AC-3.3: Given a cache whose stored version tag does not match the current
  aspark-graph version or any of the currently pinned grammar versions (C14),
  when I run `aspark-graph build .`, then the build detects the mismatch,
  discards the cache, falls back to a full rescan with a one-line stderr notice,
  and produces a correct graph.
- [ ] AC-3.4: Given a valid cache, when one or more source files are added,
  deleted, or renamed in the repo between builds, when I run
  `aspark-graph build .`, then the graph correctly reflects the current repo
  state: new files' nodes are added, deleted files' nodes are removed, and
  renamed files' old-path nodes are removed and new-path nodes added — all
  identical to what a full rescan of the current state would produce. No ghost
  nodes, no missing nodes. (A rename is treated as a delete of the old relpath
  and an add of the new relpath; the cache key strategy for renames is the EM's
  call, provided the observable output is correct — see C15.)
- [ ] AC-3.5: Given a valid parse cache exists but `graph.json` is absent (e.g.,
  the user deleted it manually), when I run `aspark-graph build .`, then the
  build treats the missing `graph.json` as "no prior state" regardless of cache,
  performs a full rescan, and produces a correct, complete graph. The cache alone
  is never used to reconstruct a graph without `graph.json` as the anchor — this
  avoids an ill-defined consistency problem.

### US-4 (Should): Force a full rescan via `--full` flag

> As the CI operator or developer debugging unexpected results, I want a `--full`
> flag on the build command that forces a complete rescan regardless of any cached
> state, so that I can guarantee a clean build in CI pipelines or diagnose a
> suspected cache problem.

**Acceptance criteria:**

- [ ] AC-4.1: Given an existing cache (valid or otherwise), when I run
  `aspark-graph build --full .`, then the build performs a complete rescan of all
  source files, ignores the cached state entirely, exits 0, and produces a graph
  identical to what the current pre-feature `aspark-graph build .` produces today.
- [ ] AC-4.2: Given `aspark-graph build --full .` completes, when I inspect the
  cache state (e.g., by running an immediate second `aspark-graph build .`), then
  the cache reflects the fresh full-rescan results — the old cache has been
  replaced, not left alongside new results.
- [ ] AC-4.3: Given no prior build has been run (no cache, no `graph.json`), when
  I run `aspark-graph build --full .`, then it behaves identically to
  `aspark-graph build .` — full rescan, exit 0, no error or warning about a
  missing cache.

### US-5 (Could): Build summary reports incremental vs full path and files re-parsed

> As the developer, I want the build command's output to state whether it ran
> incrementally or as a full rescan, and how many files were re-parsed vs reused
> from cache, so that I can understand what the build did and diagnose unexpected
> slowness without reading source code.

**Acceptance criteria:**

- [ ] AC-5.1: Given an incremental build where M files were re-parsed and N were
  reused from cache, when the build completes, then the build summary line
  reports: the existing entity counts AND an incremental indicator AND M
  (re-parsed) AND N (cached/reused) — extending the existing
  `BuildReport.summary()` format without breaking it (e.g., appending
  `; incremental: M re-parsed, N cached` to the current line).
- [ ] AC-5.2: Given a full rescan (first build, `--full`, or any fallback path),
  when it completes, then the summary does **not** report a cached/reused count —
  nothing in the summary implies caching was active when it was not.

## 5. Non-Functional Requirements

<!-- Cross-cutting qualities the feature must meet, separate from functional behavior.
     Inherits the project's non-negotiables rather than restating them entirely. -->

| # | Category | Requirement (measurable) | How it's verified |
|---|---|---|---|
| NFR-1 | Performance | On the EM-defined benchmark fixture (200+ source files, ≤10% changed since the last build), `aspark-graph build .` (incremental) completes in **≤50% of the wall-clock time** of `aspark-graph build --full .` on the same machine and Python interpreter. Measured with an external timer (e.g. `time aspark-graph build .`) on both commands against the same fixture; the aspark-graph repo itself is too small and must not be the sole fixture. Fixture and measurement script defined in `/sprint-plan`. (Target confirmed Q1, 2026-07-17.) | /peer-review: run both commands on the EM-defined fixture; confirm ≥50% speedup |
| NFR-2 | Correctness / determinism (non-negotiable) | An incremental build on an unchanged repo produces a byte-identical `graph.json` to a full rescan of the same state (AC-2.1, AC-2.2). The existing double-build test passes without modification; a new AC-2.2 full-then-incremental parity test is added to the suite. | /peer-review: existing test green; new parity test green |
| NFR-3 | Reliability | A corrupt, absent, or version-mismatched cache never causes a wrong or partial graph; fallback to full rescan is automatic, produces a correct result, and emits a one-line stderr notice naming the reason (AC-3.2, AC-3.3). | /peer-review: inject corrupt cache file; confirm fallback, stderr notice, correct graph, exit 0 |
| NFR-4 | Observability | For each build invocation, the output contains enough information to determine (a) whether the build ran incrementally or as a full rescan and (b) if incremental, how many files were re-parsed vs cached — without reading source code beyond the build summary. If US-5 is cut as a Could, this requirement is satisfied by stderr INFO-level logging of the same counts rather than the summary line. | /peer-review: verify output for each of the seven build states enumerated in C16 |
| NFR-5 | Security & privacy | N/A — the cache stores only parse results derived from local source files already in the repo; no new data, no network, no auth surface. | N/A |
| NFR-6 | Accessibility | N/A — no visual UI; command-line tool with text output. | N/A |
| NFR-7 | CLI ≡ MCP parity (non-negotiable) | Query results (`impact`, `story_trace`, `gate_health`, `staleness`) after an incremental build are identical to those after a full rescan of the same state — the existing parity test asserts this at the query layer and must stay green. The build command is CLI-only (no MCP equivalent); no new parity surface is introduced. | /peer-review: existing CLI≡MCP parity test green after incremental build |
| NFR-8 | No new pip dependencies | The parse cache must be implementable using the existing dependency set (Python standard library + packages already in `pyproject.toml`). No new `pip install` requirement may be introduced. This directly applies the lesson from the `cryptography`-wheel incident (v0.3.0) that motivated the strict dependency policy. | /peer-review: diff `pyproject.toml` and `uv.lock`; confirm no additions |

## 6. Out of Scope

Consciously cut from this spec (each is a real candidate — the answer is "not now"):

- **Replacing `graph.json` with SQLite as the canonical query store.** The user
  named SQLite as a possible mechanism; this spec confines any cache (SQLite or
  otherwise) to a supplemental build-time artifact alongside `graph.json`, not a
  replacement for it. Replacing `graph.json` requires addressing the byte-identical
  double-build test non-negotiable (A3) and is its own spec.
- **Incremental caching of the git-inference step** (`inference.py` /
  `git.log_records`). **Q2 resolved (2026-07-17): Out of scope this cycle.**
  Inference caching is a separate, larger feature. The `infer_implements` step runs
  unchanged on every build. If the `git log` subprocess is the bottleneck on a
  specific large repo, that is a signal for the EM to surface in `/sprint-plan`
  (see A2); the resolution there is a future inference-caching spec, not scope
  expansion here.
- **Caching of `.spark/` artifact parsing** (`artifacts.extract_features`).
  Artifact files are few in number and their parsing is fast relative to
  tree-sitter. Caching them would require tracking dependencies between artifact
  files (a spec/plan reference updates the story graph layer, not the code layer).
  Complexity-to-gain ratio is unfavorable. Out of scope.
- **Caching of import resolution** (`_resolve_imports`). Import resolution is an
  in-memory, cross-file step that runs over the full set of file extraction results
  (cached + freshly parsed). It cannot be cached per-file without tracking
  inter-file import dependencies. It runs on every build. Out of scope.
- **Live file-watching / continuous rebuild mode.** The build is triggered
  explicitly by `aspark-graph build .`; no file-system event listener is
  introduced. An always-on background process is a separate feature with a
  different reliability and security surface.
- **Cross-branch or cross-worktree caching.** The cache is valid only for the repo
  state it was built on. Switching branches, checking out a different worktree, or
  rebasing invalidates the cache; the next build falls back to a full rescan. No
  attempt is made to carry cached extraction results across branch transitions.
- **Team-shared or remote build caches.** The cache is local, per-repo, per-user,
  stored in `.aspark-graph/`. No remote cache, no CI artifact sharing, no cache
  locking. The offline guarantee is unchanged.
- **Concurrent build safety.** Two simultaneous `aspark-graph build .` invocations
  on the same repo may race on the cache. This is out of scope: the tool is a
  single-user local tool and concurrent builds are not a supported use case. No
  cache locking is introduced.
- **Faster query load times.** Loading `graph.json` into a networkx graph for
  queries is not the stated pain point. If it becomes one on extremely large repos,
  that is a separate spec.
- **Any change to the `staleness` query semantics.** The `staleness` query
  compares on-disk file hashes with those stored in `graph.json`. After an
  incremental build, `graph.json` holds current hashes for all files (changed and
  unchanged). Staleness correctly reports the graph as current with no change to
  its semantics. Out of scope.
- **More languages, LLM/NL layer, precise call-graph resolution, visualization,
  exports, HTTP/team mode, published PyPI release.** Unchanged from prior cycles.

## 7. Clarifications

<!-- The record of the Specify-phase Clarify pass. Unresolved → §3 and gate stays closed. -->

| # | Date | Question | Resolution |
|---|---|---|---|
| C1 | 2026-07-17 | Is SQLite a hard requirement, or a means to an end? | Resolved in A1/A3: SQLite is a possible mechanism, not a requirement. The spec focuses on observable outcomes (faster builds, correct output). Storage-format choice is /sprint-plan's call, constrained by A3 (graph.json must remain canonical to keep the byte-identical test). |
| C2 | 2026-07-17 | What does "deterministic" mean for an incremental build? | Resolved in A5/US-2/AC-2.1–2.2: an incremental build on an unchanged repo must produce byte-identical `graph.json` to a full rescan of the same state. The existing double-build test is the expression of this invariant and must stay green (A3). |
| C3 | 2026-07-17 | What is the fallback when the incremental state is corrupt or missing? | Resolved in A6/US-3: automatic full rescan, one-line stderr notice, exit 0. Never a wrong result, never a traceback. |
| C4 | 2026-07-17 | Does the `staleness` query need to change? | Resolved: no. After an incremental build, `graph.json` holds current content hashes for all files. Staleness correctly reports the graph as current. No semantic change needed. See Out of Scope. |
| C5 | 2026-07-17 | Should `aspark-graph build` default to incremental, or require an opt-in flag? | Resolved: default to incremental when a previous valid state exists (transparent to the caller). `--full` is the opt-out. Mirrors standard build-tool behaviour and minimises friction in the agent loop. |
| C6 | 2026-07-17 | Does the "instead of graph.json" part of the user's phrasing conflict with the byte-identical determinism test? | Resolved in A3: this spec confines the feature to "alongside" — the cache supplements `graph.json`, never replaces it this cycle. "Instead of" requires a separate spec. |
| C7 | 2026-07-17 | Add/delete of files between builds — does the incremental path handle them? | Yes — AC-3.4 covers add/delete/rename. A missed delete would leave ghost nodes in the graph. |
| C8 | 2026-07-17 | What about parser version changes (e.g. upgraded tree-sitter grammar pin)? | AC-2.4 and AC-3.3: cache entries from a prior parser version are incompatible; the build falls back to a full rescan. The cache must store a version tag (see C14). |
| C9 | 2026-07-17 | Performance target and test fixture — what's the reference corpus? | Resolved via Q1 (2026-07-17): ≥50% faster at ≤10% changed files on a 200+ file repo. The aspark-graph repo itself is too small; /sprint-plan must define a synthetic or real large-repo fixture for the NFR-1 acceptance test. |
| C10 | 2026-07-17 | Is git inference (`infer_implements`) expected to benefit from the incremental path? | Resolved via Q2 (2026-07-17): Out of Scope this cycle. Inference caching is a future feature. Inference runs unchanged on every build. See §6. |
| C11 | 2026-07-17 | Does the `--full` flag replace the cache or just ignore it? | AC-4.2: `--full` replaces the cache with fresh state after the rescan. Leaving a stale cache in place after `--full` would confuse the next incremental build. |
| C12 | 2026-07-17 | Does this feature touch the CLI ≡ MCP parity contract? | No new query logic is added. The build command is CLI-only (no MCP equivalent). The parity test covers queries only; the existing test stays green (NFR-7). |
| C13 | 2026-07-17 | (Clarify pass) What exactly does "incremental" mean — does it skip ALL build steps for unchanged files? | No. Only step (1), tree-sitter extraction per source file, is cached. Steps (2) import resolution, (3) artifact parsing, and (4) git inference run on every build regardless of cache state (A7). They are cross-file or repo-level, fast relative to step (1), and cannot be safely skipped per-file without dependency tracking this cycle. |
| C14 | 2026-07-17 | (Clarify pass) Where is the cache stored and what does it contain at minimum? | The cache is stored in `.aspark-graph/` (already gitignored), alongside `graph.json`. Filename and format are the EM's call. At minimum the cache must contain: per source file — the relpath, content hash, and tree-sitter extraction result (code entities, imports, package/language info). It must also store a **version tag** (aspark-graph version string + all three pinned grammar version strings) to enable version-incompatibility detection (AC-2.4, AC-3.3). The cache is consulted only during `aspark-graph build`; query commands (`query impact`, `story_trace`, etc.) read `graph.json` exclusively and are unaware of the cache. |
| C15 | 2026-07-17 | (Clarify pass) How are renamed or moved source files handled? | Observable requirement in AC-3.4: rename = delete old relpath + add new relpath. The graph must correctly remove old-path nodes and add new-path nodes, identical to a full rescan. Whether the cache is keyed by (relpath, hash) or by content hash alone is the EM's call, provided the observable AC-3.4 requirement is met. |
| C16 | 2026-07-17 | (Clarify pass) What are all the distinct build states and which ACs cover them? | Seven states: (1) First build / no cache → AC-3.1. (2) `graph.json` absent with or without cache → AC-3.5. (3) Incremental: some files changed → AC-1.1, AC-1.2. (4) Incremental: zero files changed → AC-1.3. (5) `--full` flag → AC-4.1–4.3. (6) Fallback: corrupt cache → AC-3.2. (7) Fallback: version mismatch → AC-3.3. NFR-4 requires the build output to distinguish each state without source inspection. |
| C17 | 2026-07-17 | (Clarify pass) What if `graph.json` is absent but a valid cache exists? | AC-3.5: `graph.json` absence is "no prior state" regardless of cache. The build runs a full rescan and produces a complete graph. The cache is not used to reconstruct a graph without `graph.json` as anchor — this avoids an ill-defined consistency problem and keeps the invariant simple. |
| C18 | 2026-07-17 | (Clarify pass) Are orphaned cache entries (for files no longer in the repo) pruned? | Not a correctness concern — orphaned entries for deleted files are never used (the build only looks up files found in the current walk). Explicit pruning is a disk-hygiene decision left to the EM. No AC needed. |
| C19 | 2026-07-17 | (Clarify pass) Does the cache introduce any new pip dependency? | No — NFR-8 prohibits new dependencies. The cache must be implemented with the existing dependency set. This applies the lesson from the `cryptography`-wheel incident (v0.3.0) that motivated the strict dependency policy. |
| C20 | 2026-07-17 | (Clarify pass) How is "50% faster" measured — is there timing output in the existing build command? | No existing timing output. Measurement is an external wall-clock timer (`time aspark-graph build .`) applied to both the incremental and full-rescan commands on the EM-defined fixture. The EM defines the benchmark script in /sprint-plan (NFR-1). |
| C21 | 2026-07-17 | (Clarify pass) Does AC-2.2 require a new automated test? | Yes. AC-2.2 is a new test: `build --full` then `build` (no changes) must produce byte-identical `graph.json`. This extends the existing double-build test (which currently runs two plain `build` calls) with a full-then-incremental variant. The EM adds this test to the suite alongside the existing test; the existing test is not removed or modified. |

## 8. Design Review

**N/A — with reason.** Like all prior cycles, this feature adds no graphical or
human-visual interface. Its only new surfaces are a `--full` flag on the existing
`build` command and an extended summary line from `BuildReport.summary()` — both
are text, covered by falsifiable acceptance criteria (AC-4.x, AC-5.x, NFR-4).
There is no layout, visual hierarchy, or accessibility surface to review. If a
build progress indicator or incremental-coverage visualization is ever brought in
scope, this section must be reopened.

- **Overall impression:** N/A (no visual UI)
- **Heuristics findings:** N/A — CLI error-handling heuristics covered by ACs (AC-3.2, AC-3.3, AC-5.2)
- **Accessibility notes:** N/A (no visual UI)
- **Design risks & required changes:** None for a non-UI tool

---

## ✅ SPEC GATE

*All boxes checked → `/sprint-plan` may start. Any box open → back to `/story-time` or `/look-and-feel`.*

- [x] Problem, goal and success signal are concrete (no buzzwords, no "everyone")
- [x] Every story has testable Given/When/Then acceptance criteria
- [x] Stories are prioritized (MoSCoW) and at least one is a Must
- [x] Non-functional requirements are stated and measurable (or marked N/A with reason)
- [x] Clarify pass done: no ambiguity left unresolved or unparked *(C1–C21 resolved; Q1 and Q2 resolved 2026-07-17)*
- [x] Open questions are resolved or explicitly accepted as risk *(Q1: ≥50% / ≤10% / 200+ files; Q2: inference caching Out of Scope — both resolved 2026-07-17)*
- [x] Out-of-scope section is filled (something was consciously cut)
- [x] Constitution (`.spark/constitution.md`) respected — N/A, no constitution exists
- [x] Design review done for UI-facing features (or marked N/A with reason)
- [x] Status set to `approved` by the user *(Andreas Lottes, 2026-07-17)*
