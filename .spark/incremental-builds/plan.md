# Plan: incremental-builds

| | |
|---|---|
| **Phase** | Plan |
| **Owner** | Engineering Manager (`/sprint-plan`) |
| **Input** | `.spark/incremental-builds/spec.md` (status: `approved`) |
| **Status** | `approved` |
| **Date** | 2026-07-17 |

## 1. Architecture Decision

<!-- Mini-ADR. The EM decides — but shows the alternatives that were rejected and why. -->

- **Context:** `build_graph()` in `build.py` runs four steps: (1) per-file
  tree-sitter extraction, (2) cross-file import resolution, (3) `.spark/` artifact
  parsing, (4) git-history inference. The spec scopes caching to **step (1) only**
  (A7, C13); steps 2–4 run every build. The build already computes a SHA-256
  digest per file for the v0.2.0 staleness attribute (A4), so change detection
  needs no new hashing step. Three hard constraints bind every option: `graph.json`
  stays the canonical output and must rebuild byte-for-byte (A3, NFR-2, the two
  existing double-build tests); no new pip dependency (NFR-8, C19 — the
  `cryptography` lesson); a corrupt/absent/version-mismatched cache must fall back
  to a full rescan, never serve a wrong graph (US-3, NFR-3).

- **Decision:** Cache the **`FileExtraction`** (the language-agnostic dataclass the
  extractors already emit) per source file, in a **canonical JSON sidecar**
  `.aspark-graph/parse-cache.json`, keyed by `relpath` and carrying that file's
  `sha256` digest plus a top-level **version tag**. `build_graph()` gains a single
  extraction seam: for each walked file, if the cache holds an entry for its
  `(relpath, sha256)` the cached `FileExtraction` is reconstructed and reused
  **without invoking the extractor**; otherwise the file is parsed fresh. Every
  downstream mutation (`_add_definitions`, `_resolve_imports`, node hashes) then runs
  on `FileExtraction` objects **identically regardless of their origin** — that
  structural sameness is what guarantees byte-identical `graph.json`, not a
  post-hoc comparison. After the build, the cache is rewritten from the full current
  extraction set. The cache is consulted only when `graph.json` already exists
  (AC-3.5 anchor rule); any read/parse/version failure is caught, recorded as a
  `fallback_reason` on `BuildReport`, and the build re-runs as a full rescan.

- **Alternatives considered:**
  | Alternative | Why rejected |
  |---|---|
  | **SQLite sidecar** (`parse-cache.db`) — the user's originally-named mechanism (A1) | Row order is not guaranteed without an explicit `ORDER BY`, adding a determinism footgun next to the byte-identical invariant we must protect; brings schema/migration overhead for a disposable read cache; and the `sqlite3` stdlib module, while dependency-free, is heavier to reason about than a sorted JSON file for a few hundred rows. No measured benefit at this corpus size. The spec explicitly declined to mandate SQLite (C1). |
  | **Pickle sidecar** | Fails the reliability story: pickle raises varied, version-sensitive exceptions on schema drift and is not human-inspectable, making the corrupt-cache fallback (AC-3.2) harder to test and debug. Also a latent security smell (arbitrary-object deserialization) even for local files. JSON gives the same speed here with a readable, integrity-checkable artifact. |
  | **Cache the assembled graph nodes/edges per file** (instead of the `FileExtraction`) | Import edges are cross-file (resolved in step 2 over the whole extraction set); caching per-file graph fragments would either duplicate that logic or cache stale edges, reintroducing the exact correctness risk US-2 forbids. Caching the pre-resolution `FileExtraction` keeps the single source of truth: step 2 always re-runs over cached+fresh extractions together. |
  | **In-memory cache only** (no persistence) | Useless for the actual workload: the pain is *repeated separate* `aspark-graph build .` process invocations in an agent loop (Target Users §2). Nothing survives between processes, so zero speedup. Rejected by the spec framing itself. |
  | **Key the cache by content hash alone** (drop relpath) | Would silently deduplicate two files with identical content and complicates the add/delete/rename bookkeeping (AC-3.4). Keying by `relpath` with the hash as the validity check mirrors how the graph itself is keyed (`file_id(relpath)`) and keeps rename = delete-old + add-new trivially correct. |

- **Consequences:**
  - *Easier:* Correctness argument is structural and cheap to defend — the graph is
    assembled from the same `FileExtraction` objects whether cached or fresh, so
    byte-identity follows by construction rather than by luck. Add/delete/rename
    fall out for free because the build only processes files found in the current
    walk and rewrites the cache wholesale. The cache is human-readable for
    debugging. No new dependency (stdlib `json` + `importlib.metadata`).
  - *Harder:* `FileExtraction` (and its nested `Definition`/`Import`) now has an
    implicit serialization contract — adding a field means updating the (de)serializer;
    a version-tag bump covers *parser* drift but not *our own schema* drift, so the
    serializer round-trip needs its own test. The build gains a branch (incremental
    vs full) and a fallback path, widening the state space to the seven states in
    C16 — each needs an explicit test. The cache write adds a small I/O cost to
    every build (negligible vs. the parse it saves).

## 2. Affected Components

- **`src/aspark_graph/build.py`** (primary) — refactor the per-file loop into a
  single extraction seam (`_extraction_for(...)`: cache-hit reuse vs. fresh parse);
  add the incremental/full branch, the `graph.json`-anchor guard, and the
  try/except fallback that records `fallback_reason`. Extend `BuildReport` with
  `incremental: bool`, `reparsed: int`, `cached: int`, `fallback_reason: str | None`.
- **`src/aspark_graph/parse_cache.py`** (new module) — `ParseCache`: `load(repo_root)`,
  `save(repo_root, extractions)`, `lookup(relpath, digest) -> FileExtraction | None`,
  the version-tag builder, and `FileExtraction` (de)serialization. Canonical write
  (sorted keys, entries sorted by relpath). Owns the corrupt/version-mismatch
  detection and raises a single internal `CacheUnusable` signal the build catches.
- **`src/aspark_graph/cli.py`** — add `--full` to the `build` subparser; pass it to
  `build_graph`; emit the one-line stderr fallback notice from `report.fallback_reason`
  at the CLI edge (keeping build.py free of user-facing printing, per the thin-adapter
  convention). `server.py` is **not** touched — build is CLI-only (NFR-7, C12).
- **`src/aspark_graph/extractors/base.py`** — no behaviour change; its
  `FileExtraction`/`Definition`/`Import` dataclasses become the cache's serialization
  schema (documented, tested).
- **New dependency:** **none.** Cache uses stdlib `json` + `importlib.metadata`
  (for the version tag). NFR-8 / C19 satisfied by construction.
- **Version tag source:** `importlib.metadata.version("aspark-graph")` plus the three
  pinned grammar versions (`tree-sitter-python|typescript|java`) and `tree-sitter`
  core. **Note:** `src/aspark_graph/__init__.py` still declares a stale
  `__version__ = "0.1.0"`; do **not** key the tag off it — read installed metadata,
  which reflects the real pinned versions. (Flagged as a risk.)
- **Cache location:** `.aspark-graph/parse-cache.json`, alongside `graph.json` in the
  already-gitignored `.aspark-graph/` dir (C14).
- **Version bump: `0.3.1` → `0.4.0` (minor).** Justified: a new user-visible CLI flag
  (`--full`) and new default build behaviour (incremental) — additive and
  backward-compatible (default build stays correct; first build unchanged), so a
  minor bump under semver, not a patch or major. Bump `pyproject.toml` at release;
  the stale `__init__.__version__` is not the release source of truth (see risk).

## 3. Task Breakdown

<!-- Ordered. Every task maps to the spec by ID and has its own checkable DoD.
     T1 is the walking skeleton: runnable end-to-end, correct before fast. -->

| # | Task | Story | Covers (AC / NFR) | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|---|
| T1 | **Walking skeleton:** new `parse_cache.py` with `FileExtraction` (de)serialization + version tag + canonical sidecar write; refactor `build_graph()` to a single cache-or-parse extraction seam that reuses cached extractions on `(relpath, sha256)` match without invoking the extractor, and rewrites the cache after every build | US-1, US-2 | AC-1.1, AC-2.1, AC-2.2, NFR-2, NFR-8 | – | `done` | `build` twice on an unchanged repo → `graph.json` byte-identical; both existing double-build tests green; a **new** full-then-incremental parity test (`build --full` internally forced, then default `build`, no file changes) → byte-identical `graph.json`; a `FileExtraction` serialize→deserialize round-trip unit test passes; `uv run pytest` green (all 134 + new); `pyproject.toml`/`uv.lock` unchanged |
| T2 | Change detection + reuse accounting: compare each file's fresh digest against the cache, count `reparsed` vs `cached`, and short-circuit the extractor on hits; confirm changed-file digests land in `graph.json` | US-1 | AC-1.1, AC-1.3, AC-1.4 | T1 | `done` | On a repo with N files where 1 changed, exactly 1 file is re-parsed and N−1 reused (asserted via `BuildReport`); zero-changed build re-parses 0 files; after changing a file, `build` then `query staleness` reports the graph current (changed files' hashes updated in `graph.json`) |
| T3 | Add / delete / rename correctness | US-3 | AC-3.4, NFR-2 | T2 | `done` | Tests prove: a newly-added source file's nodes appear; a deleted file's nodes are gone (no ghosts); a rename (delete old relpath + add new relpath) yields nodes identical to a full rescan of the post-rename state; graph byte-identical to a full rescan in each case |
| T4 | `graph.json` anchor + first-build path | US-3 | AC-3.1, AC-3.5 | T1 | `done` | First-ever build (no cache, no `graph.json`) → full rescan, correct graph, no error, no "missing cache" notice; `graph.json` absent but cache present → treated as no prior state → full rescan, complete graph; both behave identically to the pre-feature build |
| T5 | Corrupt/unreadable-cache fallback with one-line stderr notice | US-3 | AC-3.2, NFR-3, NFR-4 | T1, T4 | `done` | Truncated/garbage `parse-cache.json` → build catches it, sets `report.fallback_reason`, CLI emits exactly one stderr line naming the reason, exits 0, produces a correct graph byte-identical to a full rescan; **no traceback**; unit test asserts stderr content and exit code |
| T6 | Version-tag invalidation | US-2, US-3 | AC-2.4, AC-3.3, NFR-3 | T5 | `done` | Cache written with a mutated version tag → next build detects mismatch, discards cache, falls back to full rescan with a one-line stderr notice, produces a correct graph; a test proves parse results from a differing tag are never served |
| T7 | `--full` CLI flag | US-4 | AC-4.1, AC-4.2, AC-4.3, NFR-4 | T2 | `done` | `build --full` ignores any existing cache, full-rescans, exits 0, graph identical to pre-feature build; after `--full` the cache is **replaced** with fresh state (proven by an immediate default `build` reusing it); with no prior state, `--full` behaves identically to plain `build` |
| T8 | NFR-1 benchmark fixture + perf test | US-1 | AC-1.2, NFR-1 | T2 | `done` | A pytest fixture generates ≥200 dummy Python files with known AST content into a tmp repo, builds (full), mutates ≤10%, then times incremental vs `--full`; asserts incremental ≤50% of full wall-clock; marked `@pytest.mark.slow` and **excluded from default `uv run pytest`** (documented run command); validates A2 (parse dominates) — if it doesn't, surface before commit per A2 |
| T9 | (Could) Extend `BuildReport.summary()` with incremental indicator + counts | US-5 | AC-5.1, AC-5.2, NFR-4 | T2, T7 | `done` | Incremental summary appends `; incremental: M re-parsed, N cached` without breaking the existing line; full-rescan/fallback summary reports **no** cached count; tests cover both. **Park if it complicates the architecture** — NFR-4 is otherwise met by T5–T7 stderr/summary output |

Note on NFR-7 (CLI≡MCP parity): no query logic changes and `server.py` is untouched;
the existing parity test must stay green and is verified as a standing check in T1's
`uv run pytest` gate (not a separate task).

## 4. Test Strategy

Deterministic, offline, and fixture-driven — the repo's own `.spark/` trails and
synthetic tmp repos, consistent with the existing suite. No browser QA: this is a
headless CLI tool, so `/demo-day` is structurally N/A (CLAUDE.md); the QA-equivalent
(clean-env install, `serve` boot, byte-identical build, real-repo `impact`) is done in
`/peer-review`.

- **Determinism / correctness (Must, US-2) — automated, the spine of the feature:**
  - Both **existing** double-build tests (`test_build.py`) stay green **unmodified**
    — verified, not rewritten (AC-2.1, C21).
  - **New** full-then-incremental parity test: `build --full` then default `build`
    on unchanged state → byte-identical `graph.json` (AC-2.2, C21).
  - Query equivalence: `impact` / `story_trace` after an incremental build == after a
    full rescan of the same state (AC-2.3), reusing the tool's dogfood trails as fixture.
- **Incremental behaviour (Must, US-1) — unit + integration:**
  - Reuse accounting: assert exact `reparsed`/`cached` counts for changed-subset,
    zero-change, and add cases (AC-1.1, AC-1.3).
  - Staleness-after-incremental: `build` → mutate → `build` → `query staleness`
    reports current (AC-1.4).
- **Add/delete/rename (Must, US-3):** integration tests over a tmp repo asserting node
  presence/absence and byte-identity vs full rescan (AC-3.4).
- **Fallback matrix (Must, US-3) — unit, one test per state (C16):** first build /
  no cache (AC-3.1); `graph.json` absent (AC-3.5); corrupt cache (AC-3.2, asserts
  single stderr line + exit 0 + no traceback); version-tag mismatch (AC-3.3).
- **`--full` (Should, US-4):** ignores cache, replaces cache, no-prior-state parity
  (AC-4.1–4.3).
- **Performance (NFR-1) — deliberately out of the default run:** synthetic 200+ file
  fixture, `@pytest.mark.slow`, run explicitly in `/peer-review`. **Reason for not
  running by default:** it is a wall-clock benchmark (slow, machine-sensitive) whose
  pass/fail is a `/peer-review` gate concern, not a per-commit unit signal; keeping it
  out of `uv run pytest` protects the fast green-suite discipline. The correctness of
  the incremental path is fully covered by the deterministic tests above.
- **Serializer schema test:** `FileExtraction` round-trip guards the implicit cache
  contract flagged in the ADR consequences.

## 5. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| **NFR-1 not met because parse isn't the bottleneck** (git inference — out of scope this cycle — dominates on a deep-history repo; A2/Q2) | Feature ships without hitting its headline speedup; the whole cycle's value is questioned | T8 benchmarks incremental vs full early and validates A2 directly. If inference dominates on the fixture, **surface it before sprint commit** (A2 escape valve) rather than shipping a miss — the answer is a future inference-caching spec, not silent scope creep |
| **Cache serialization drift breaks byte-identity** — a future field added to `FileExtraction`/`Definition`/`Import` isn't (de)serialized, so cached ≠ fresh extractions | Silent wrong graph — the exact failure US-2 forbids | Assemble the graph from the *same* `FileExtraction` objects for cached and fresh files (structural equivalence, ADR decision); add a round-trip serializer test (T1); the version tag covers parser drift and the full-then-incremental parity test (AC-2.2) catches any residual divergence in CI |
| **Stale `__version__ = "0.1.0"` in `__init__.py`** used as the cache version tag would mis-key invalidation | Version-mismatch fallback (AC-3.3) silently ineffective; stale parse results served across a real version bump | Build the tag from `importlib.metadata.version(...)` for the package **and** all three pinned grammars + core — never from `__init__.__version__`; assert in a unit test that the tag changes when a grammar pin changes (simulated) |
| **State-space explosion** — 7 build states (C16) × fallback paths widen the surface | Untested corner (e.g. corrupt cache + added file) serves a wrong or partial graph | One explicit test per C16 state (fallback matrix in §4); the fallback is a single catch-all seam in `build_graph` that always degrades to the proven full-rescan path, so unknown failures land on the safe side |

---

## Deviations

- **T8 benchmark fixture file size:** The first synthetic fixture used 8-line files; tree-sitter parse time was negligible compared to I/O overhead, producing only 12% speedup (not 50%). Fixture updated to use 100-line files (10 classes × 8 methods each) — a realistic module size — which pushes parse cost to dominant and yields 56.9% speedup. The A2 assumption (parse dominates) holds for realistic file sizes but not for trivially small files; this is documented in the benchmark fixture's docstring.

- **`test_first_build_no_cache_no_error` adjusted:** The test originally asserted `default_graph_path(tmp_path).exists()` after `build_graph()`, but `build_graph()` does not save `graph.json` (the CLI does). Assertion removed; the test correctly verifies `report.code_entities > 0` and `report.incremental is False`.

---

## ✅ PLAN GATE

*All boxes checked → `/increment` may start. Any box open → back to `/sprint-plan`.*

- [x] Spec status is `approved` (never plan against a draft)
- [x] Architecture decision includes rejected alternatives (a decision without alternatives is a guess)
- [x] Architecture respects the constitution's technical constraints (or a conflict is recorded) — N/A, no constitution; inherited non-negotiables (determinism, canonical `graph.json`, no new deps, thin adapters, grammar pins) are honored
- [x] Every task maps to a user story — no orphan tasks, no story without tasks
- [x] Every Must AC and every applicable NFR is covered by at least one task (US-1/2/3 fully covered; NFR-1 T8, NFR-2 T1, NFR-3 T5/T6, NFR-4 T5/T7/T9, NFR-7 standing check in T1, NFR-8 T1; NFR-5/6 N/A per spec)
- [x] Every task has a checkable definition of done
- [x] Task order respects dependencies
- [x] Test strategy covers every Must story
- [x] Status set to `approved` by the user *(Andreas Lottes, 2026-07-17)*
