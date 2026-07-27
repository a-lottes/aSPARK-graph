# Plan: security-posture

| | |
|---|---|
| **Phase** | Plan |
| **Owner** | Engineering Manager (`/sprint-plan`) |
| **Input** | `.spark/security-posture/spec.md` (`approved`, 2026-07-26) |
| **Status** | `approved` |
| **Date** | 2026-07-26 |

## 1. Architecture Decision

- **Context:** Three entry surfaces reach a repo root: `build.py:build_graph()` (walks the
  tree), `queries.load_graph()` (resolves `<root>/.aspark-graph/graph.json`) and the two
  `queries.*` functions that take a root themselves (`staleness`, `impact_diff`). `cli.py`
  and `server.py` are thin adapters and must stay that way (NFR-7). They already have a
  worked precedent for exactly this shape: `queries.GraphNotBuiltError` is raised in the
  shared module and rendered twice — one stderr line + exit 1 at `cli.py:189`, a
  `{"found": false, …}` dict at `server.py:41`. Confinement is the same problem again, so it
  gets the same solution rather than a new one. The one genuinely new decision is **how the
  ~20 bare-`tmp_path` build fixtures survive enforcement** (Q3/A11) — that is decided below
  and is the item most worth the user's veto at this gate.

- **Decision:** One new stdlib-only module `confinement.py` owns the rule and the two
  bounds. It exposes `ensure_repo(path) -> Path` (resolve symlinks, then accept iff the
  resolved directory holds `.git` as file *or* directory, `.spark/` as directory, or
  `.aspark-graph/graph.json` as an existing regular file — never opened), plus one exception
  base `RepoRefused` with `.reason` and two subclasses (`OutsideConfinementError` →
  `outside_confinement`, `RepoTooLargeError` → `too_large`). Enforcement sits **below** the
  adapters, at four call sites: `build_graph()`, `queries.load_graph()`, `queries.staleness()`
  and `queries.impact_diff()` (AC-1.9). The adapters gain only rendering: `cli.py` catches
  `RepoRefused` next to `TemplateDriftError`/`GraphNotBuiltError`; `server.py`'s `_open()` and
  the `build_graph` tool return `{"found": False, "reason": exc.reason, "message": str(exc)}`.
  No rule, no marker string and no constant appears in either adapter — a test asserts that
  (NFR-7). **There is no bypass.** The ~20 bare-`tmp_path` fixtures are *marked* instead: one
  autouse fixture in `tests/conftest.py` creates an empty `.spark/` directory in `tmp_path`,
  which is graph-neutral (the walk yields only files, and `artifacts.extract_features` returns
  0 for a `.spark/` with no feature dirs), so every existing test then exercises the **shipped**
  path. One rule for all nine tools — build included — so an already-built directory stays
  rebuildable (AC-1.13) while a fresh one is still refused (AC-1.12, it has no `graph.json`).

- **Alternatives considered:**
  | Alternative | Why rejected |
  |---|---|
  | **The internal test-only bypass the spec accepts (Q3/A11).** A module-private flag or context manager that the fixtures switch off. | Two shapes, both worse than marking. *Autouse* bypass disables the check for the **whole** suite, so parity, transport and sample-repo tests all run code users never run — the maximum A11 cost. *Per-test* bypass has to be requested at each of the ~60 `build_graph(tmp_path)`/query call sites, i.e. **exactly the same diff size as marking**, in exchange for strictly weaker evidence. Marking retires A11 entirely, and satisfies AC-1.10/NFR-9 in their strongest form (no second path exists to be reachable, and nothing to compare against) rather than merely constraining a second path. **The spec accepted a bypass; it did not require one** — but this reverses a user-resolved question, so it is raised at the gate (see §5, R1). |
  | **Enforce at the adapter edge only** (one check in `cli.py`, one in `server.py`). | Violates AC-1.9 (library must refuse) and duplicates the rule in two places, which is what NFR-7 forbids. Cheaper to write, impossible to keep honest. |
  | **Env var escape hatch** (`ASPARK_GRAPH_ALLOW_ANY_PATH=1`) as the test mechanism. | Explicitly forbidden by AC-1.10 (an env var is reachable from both surfaces) and by §6 Out of Scope ("no documented escape hatch"). Not an option. |
  | **A separate `build`-only marker rule** (build requires `.git`/`.spark`; queries also accept `graph.json`). | Two rules to state, document and test, to buy a distinction A12 already gets for free: a *fresh* directory has no `graph.json`, so the third marker can never admit an unbuilt target even when the rule is shared. One rule, one function, one paragraph in `SECURITY.md`. |
  | **Prune `_SKIP_DIRS` during traversal** (`os.walk`) so the entry count excludes `.git`/`node_modules` and the walk is faster. | Rewrites the determinism-critical `_iter_source_files` for a performance win nobody asked for, and would make the pinned bound inconsistent with the measurement basis in §3/T8 (which counted raw `rglob` entries). YAGNI. |

- **Consequences:**
  - *Easier:* the refusal renderings are free — they reuse the existing exception→adapter
    seam, so CLI↔MCP parity for refusals is true by construction and the parity test only
    needs new rows (AC-1.7). Every existing test becomes evidence for confinement, because
    every one of them now runs the real check on a marked path.
  - *Harder / accepted cost:* a new test that builds from a raw `tmp_path` **and** opts out of
    the autouse fixture will be refused, and the author must understand why — mitigated by a
    legible message that names the path and the rule, and by the conftest fixture's docstring.
    One existing test (`test_build.py::test_no_spark_builds_code_only`, base AC-1.4) asserts
    `.spark` does **not** exist; it moves to its own `.git`-marked subdirectory so its premise
    survives verbatim. `SECURITY.md`'s limits paragraph (AC-2.9) depends on US-3 shipping —
    see §5 R4.

## 2. Affected Components

**New dependencies: none.** `confinement.py` is `pathlib` + one exception hierarchy; the
bounds are two module constants. Adding a package here would have to beat ~60 lines of stdlib
— it doesn't. `mcp>=1.12,<1.20` untouched (NFR-4).

**New files:** `src/aspark_graph/confinement.py`, `tests/test_confinement.py`,
`tests/test_confinement_cli_mcp.py`, `tests/test_confinement_guards.py`,
`tests/test_build_bounds.py`, `tests/test_security_doc.py`, `SECURITY.md`.

**Modified:** `src/aspark_graph/build.py` (call `ensure_repo`; bounded, sorted file
collection; 5 MB per-file skip), `src/aspark_graph/queries.py` (`load_graph`, `staleness`,
`impact_diff` call `ensure_repo`; `staleness` skips hash-less nodes),
`src/aspark_graph/cli.py` + `server.py` (catch/render only), `tests/conftest.py` (autouse
marker), `tests/test_build.py`, `tests/test_cli_mcp_parity.py`, `README.md`, `CLAUDE.md`,
`docs/aspark-integration.md`.

**Untouched (NFR-4 guard):** `model.py`, `graph.py`, `parse_cache.py`, `artifacts.py`,
`inference.py`, `git.py`, `extractors/`, `pyproject.toml` dependencies.

**Blast radius — `aspark-graph query impact` over the 12 paths above**, graph fresh
(`staleness: false`, 100 files checked). `found: true`; 9 of 12 paths are in the graph.
`README.md`, `CLAUDE.md` and `docs/aspark-integration.md` came back in `unknown_files` — they
are not code nodes, so **T10/T11/T12 get no graph coverage and stay scoped by hand**.
`tests/test_build.py` *is* in the graph but reports **no** affected stories or ACs: an
inference gap, not a safety signal — it holds the byte-identity tests AC-3.4/NFR-2 rest on and
the one test T2 relocates.

Aggregate: 7 affected stories / 27 ACs, **every one at `inferred` confidence**, all from two
past features (`close-the-loop` 5/18, `distributable-install` 2/9). Nothing `declared` or
`extracted`, so by this repo's own tiering the whole radius is a git-history hint, not a
structural finding — it scopes reading, it does not settle anything. No `go-rust-support`,
`incremental-builds` or `robustness` links came back at all; that is the inference missing
them, not evidence those features are unaffected.

The result **confirms** the design and changed nothing in §1. `queries.py` (20 defs) carries
three of the four enforcement call sites plus `GraphNotBuiltError`, the rendering seam being
reused. `server.py` (11 defs) is exactly `{8 query tools} ∪ {build_graph, run, _open}` — the
invariant T4's table-driven test asserts. `cli.py` (21 defs) confirms the `_args_*`/`_handle_*`
pair per query that T3/T5 touch. `build.py` (17 defs, incl. `_iter_source_files` — the
unbounded walk T8 bounds) has the widest radius of any file: all five `close-the-loop` stories
plus both `distributable-install` stories. `graph.py` is reachable but still needs **no** edit:
`add_node` already drops `None`, which is what lets T9 add `unparsed_reason`/`size_bytes`
without perturbing existing graphs. One scoping consequence: `tests/conftest.py` links to all
six `close-the-loop` US-1 ACs, so **T2 is a higher-radius edit than a test-only change usually
is** — reflected in T2's DoD and in §5 R2.

## 3. Task Breakdown

**Walking skeleton = T1→T3:** after T3 a refusal is real end-to-end on both surfaces *and* the
whole existing suite runs under real enforcement. That kills the one integration risk that
could invalidate the design (does marking hold the 165-test suite green?) before any doc or
bounds work starts.

| # | Task | Story | Covers (AC / NFR) | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|---|
| T1 | **`confinement.py`: the rule, alone.** `ensure_repo(path) -> Path` resolves symlinks then accepts on any of the three markers; refuses non-existent / regular-file / unreadable / marker-less paths with `OutsideConfinementError` naming the path and the rule. `RepoRefused` base carries `.reason`; `RepoTooLargeError` subclass added (unused until T8). `MAX_ENTRIES = 200_000`, `MAX_FILE_BYTES = 5 * 1024 * 1024` as module constants with the basis in the docstring. | US-1 | AC-1.4, AC-1.5, AC-1.6, AC-1.11, NFR-1, NFR-7 | – | `done` | Unit tests prove: `.git` file, `.git` dir, `.spark/` dir, `.aspark-graph/graph.json` each accepted; `.aspark-graph/` without `graph.json`, empty dir, missing path, regular file, chmod-000 dir each raise `OutsideConfinementError` (never `FileNotFoundError`/`NotADirectoryError`/`PermissionError`); a symlink to a marked dir is accepted; a `graph.json` that is empty or garbage is still accepted — files: src/aspark_graph/confinement.py, tests/test_confinement.py |
| T2 | **Mark the test fixtures (no bypass).** Autouse fixture in `conftest.py` creating an empty `.spark/` in every `tmp_path`, with a docstring saying why. Move `test_no_spark_builds_code_only` to a `.git`-marked subdirectory so its "no `.spark/`" premise is unchanged. Higher radius than a normal test edit — `conftest.py` links to all six `close-the-loop` US-1 ACs (§2). | US-1 | NFR-9 | – | `done` | `uv run pytest` green **before** any enforcement is wired (marking is a no-op at this point); `test_no_spark_builds_code_only` still asserts its repo has no `.spark/`; no test's assertions on counts, `artifact_entities`, `files_checked` or graph bytes changed — files: tests/conftest.py, tests/test_build.py |
| T3 | **Walking skeleton: enforce on `build_graph()` + both renderings.** `build_graph()` starts with `ensure_repo()` (replacing its own `.resolve()`). `cli.py:_cmd_build` catches `RepoRefused` → one stderr line, exit 1. `server.py:build_graph` catches → `{"found": false, "reason": …, "message": …}`. | US-1 | AC-1.1, AC-1.2, AC-1.12, NFR-3 | T1, T2 | `done` | `aspark-graph build <unmarked dir>` exits 1 in <1 s, prints one stderr line naming path+rule, no traceback, and creates **no** `.aspark-graph/` in the target; MCP `build_graph(path=<unmarked dir>)` returns the AC-1.2 dict and creates nothing; a fresh unmarked dir is refused even after a prior build elsewhere (AC-1.12); full suite green — files: src/aspark_graph/build.py, src/aspark_graph/cli.py, src/aspark_graph/server.py, tests/test_confinement_cli_mcp.py |
| T4 | **Enforce on the query path + the table-driven nine-tool test.** `ensure_repo()` in `queries.load_graph()` (keeping `default_graph_path(repo_root)` on the *original* argument so the existing `GraphNotBuiltError` message stays byte-identical), `queries.staleness()` and `queries.impact_diff()`. `server._open()` renders `RepoRefused`. Test iterates the tool list derived from `cli._QUERY_NAMES` and asserts the registered MCP tool set equals `set(_QUERY_NAMES) | {"build_graph"}`. | US-1 | AC-1.3, AC-1.5, AC-1.9, AC-1.11, AC-1.13, NFR-3, NFR-6 | T3 | `done` | Each of the eight query tools on an unmarked dir returns exactly `{"found": false, "reason": "outside_confinement", "message": …}` — driven by iteration, so a ninth tool added without a row fails the registry assertion; a dir holding only `.aspark-graph/graph.json` is accepted by all eight (AC-1.11) including one whose `.git`/`.spark` was deleted after the build (AC-1.13); calling `queries.load_graph`/`staleness`/`impact_diff` directly on an unmarked dir raises `RepoRefused`, not a traceback (AC-1.9); `test_mcp_errors.py::test_query_before_build_returns_clean_error` still passes unchanged — files: src/aspark_graph/queries.py, src/aspark_graph/server.py, tests/test_confinement_cli_mcp.py |
| T5 | **Extend the existing parity test with refusal rows.** One fixed path table in `tests/test_cli_mcp_parity.py`, driven through its existing `_cli_json`/`_mcp_data`/`_prepare` helpers, carrying accepted **and** refused rows. Plus the AC-1.8 regression: default `repo="."` from the aspark-graph checkout. | US-1 | AC-1.7, AC-1.8, NFR-4 | T4 | `done` | The table (marked dir, `.git`-file dir, graph-only dir, empty dir, missing path, regular file) yields an identical accept/refuse verdict on both surfaces for every row, in the **existing** parity file — no second parity test; the four existing parity tests (`test_story_trace_cli_equals_mcp`, `test_impact_cli_equals_mcp`, `test_get_node_cli_equals_mcp`, `test_find_nodes_empty_query_cli_equals_mcp`) and `test_ac_5_2_query_before_build_is_a_clear_message` pass unchanged; with `repo="."` in the checkout every query's output is unchanged from v0.5.0; no query name, argument name or existing success-response key changed — files: tests/test_cli_mcp_parity.py |
| T6 | **Guard tests: no bypass, no adapter logic, no file reads.** Introspection tests for AC-1.10/NFR-7/NFR-1. | US-1 | AC-1.10, NFR-1, NFR-7, NFR-9 | T4 | `done` | Tests prove: `confinement`'s public surface exposes no bypass/allow/skip/disable hook and its source reads no environment variable; `ensure_repo` takes exactly one parameter; no CLI flag and no MCP tool parameter matches those names; `cli.py`/`server.py` source contains none of `".git"`, `".spark"`, `"graph.json"`, `MAX_ENTRIES`, `MAX_FILE_BYTES` (NFR-7); with `Path.read_bytes`/`read_text`/`open` patched to raise, `ensure_repo` still accepts a graph-marker dir (NFR-1 "reads no file contents"); 1000 verdicts complete in <100 ms each — files: tests/test_confinement_guards.py |
| T7 | **(User-owned — not code.) Enable GitHub private vulnerability reporting.** Repo Settings → Security → "Private vulnerability reporting" → Enable. Only the maintainer can do this; it must land **before** T10 ships a `SECURITY.md` naming the channel. | US-2 | AC-2.8 | – | `done` | The repository's Security tab shows a reachable "Report a vulnerability" advisory form; the maintainer confirms it in this plan's status before T10 is marked done |
| T8 | **Entry-count bound (measured constant).** `_iter_source_files` becomes a bounded collector: iterate `rglob("*")` lazily into a list, raise `RepoTooLargeError` as soon as the list exceeds `MAX_ENTRIES = 200_000`, then sort exactly as today. Runs before any parsing, so no partial graph can exist. Message names the limit and that the walk was stopped past it (reporting the *true* total would require completing the walk the bound exists to avoid). | US-3 | AC-3.1, AC-3.4, NFR-2, NFR-3 | T3 | `done` | A synthetic tree over the bound: CLI exits 1 with one stderr line naming limit + observed count, MCP returns `{"found": false, "reason": "too_large", …}`, and **no** `graph.json` and no partial graph are written; `sample_repo` and this repo build byte-identically to a pre-change `graph.json` (double-build test still green); the constant and its basis are in the module docstring — files: src/aspark_graph/build.py, src/aspark_graph/confinement.py, tests/test_build_bounds.py |
| T9 | **5 MB per-file cap + symlink-cycle characterisation.** Before `read_bytes()`, `stat().st_size > MAX_FILE_BYTES` → a `File` node with `unparsed=True`, `unparsed_reason="size"`, `size_bytes=<n>` and **no** `hash` (contents never read; `graph.add_node` already drops `None`, so no `graph.py` change). Counted in `BuildReport` and reported by `summary()`. `queries.staleness` skips nodes with no `hash` (inert today — every existing `File` node has one). Test that an ancestor-directory symlink terminates. | US-3 | AC-3.2, AC-3.3, AC-3.4, NFR-2, NFR-6 | T8 | `done` | A >5 MB source file yields an unparsed `File` node with the stated reason, build exits 0, summary reports the size-skipped count, and the file's bytes are never read (patched `read_bytes` proves it); `staleness` on that repo reports it neither changed nor missing; a repo containing a symlink to its own ancestor builds to completion and returns a report; graphs for repos with no oversized file are byte-identical to a pre-change build — files: src/aspark_graph/build.py, src/aspark_graph/queries.py, tests/test_build_bounds.py |
| T10 | **`SECURITY.md` + doc harness.** Write the document: trust boundary (AC-2.2), *Non-guarantees* with exactly six numbered entries (AC-2.3), *Output is data, not instruction* (AC-2.5), reporting via GitHub private advisories + 5 working days + scope (AC-2.6), and the limits with their **asymmetric** basis (AC-2.9). Doc test in the v0.3.1 introspection style. No graph coverage for this task (§2) — scoped by reading. | US-2 | AC-2.1, AC-2.2, AC-2.3, AC-2.5, AC-2.6, AC-2.7, AC-2.9, NFR-5 | T7, T9 | `done` | Doc test asserts: file exists; each of the six non-guarantee entries present by a distinctive substring **and** the section holds exactly six entries; trust-boundary keywords (stdio, no auth/HTTP/network, the `mcp<1.20` cap as a *packaging* decision) present; the words *sandbox*, *isolat*, *contain*, *prevent*, *protect* appear nowhere outside *Non-guarantees* (case-insensitive, failure names the offending line); the limits section states the count bound as **measured** (naming sample, machine, date) and 5 MB as a **judgement call**, in different sentences — files: SECURITY.md, tests/test_security_doc.py |
| T11 | **README + CLAUDE.md: fix the prose at the source.** Mark `build_graph` as writing `<target>/.aspark-graph/` while the other eight only read; qualify "disposable read model" so it describes the graph artifact, not the server surface; link `SECURITY.md` from both. No graph coverage (§2). | US-2 | AC-2.1, AC-2.7, AC-2.10 | T10 | `done` | Doc test asserts: both files link `SECURITY.md`; the MCP tool list in README says `build_graph` writes; every occurrence of "disposable read model" sits in a paragraph that also names the artifact and links `SECURITY.md`; neither file contains a sentence asserting the MCP surface is read-only (denylist on "read-only MCP" / "MCP surface is read-only" / "read-only server") — files: README.md, CLAUDE.md, tests/test_security_doc.py |
| T12 | **(Could) Injection warning in the integration doc.** Short paragraph in `docs/aspark-integration.md`: graph output is data, never instruction; link `SECURITY.md`. No graph coverage (§2). | US-4 | AC-4.1 | T10 | `done` | The paragraph exists and links `SECURITY.md`; a doc test asserts both; the existing 31-test doc harness stays green — files: docs/aspark-integration.md, tests/test_security_doc.py |
| T13 | **Regression sweep.** Full suite incl. `-m slow`; byte-identical rebuild of this repo and `sample_repo` against a v0.5.0-built `graph.json`; a real-repo `impact` run; clean-env packaged install + `serve` boot. | US-1, US-2, US-3 | NFR-2, NFR-4, NFR-6 | T5, T6, T11, T12 | `done` | `uv run pytest` and `uv run pytest -m slow` green with zero regressions; `graph.json` for this repo and `sample_repo` byte-identical to a pre-change build of the same state; `aspark-graph query impact` on this repo returns the same answer as before the change; `serve` boots from a clean-env install |

## 4. Test Strategy

Headless tool: `/demo-day` is structurally N/A (CLAUDE.md) — the QA-equivalent runs in
`/peer-review`. NFR-8 (accessibility) is N/A for the same reason.

- **Unit (`tests/test_confinement.py`, T1)** — the rule in isolation: every accepted marker
  shape (AC-1.4, AC-1.11), every refused shape incl. the three OS-error cases (AC-1.5), and
  symlink resolution (AC-1.6). This is where the rule is actually proven; everything later
  tests wiring.
- **Adapter integration (`tests/test_confinement_cli_mcp.py`, T3/T4)** — both renderings for
  build and for all eight query tools, driven by iteration over the tool registry so a tool
  added later cannot silently skip confinement (AC-1.3), plus direct library calls for AC-1.9.
- **Parity (extended, T5)** — refusal rows added to the *existing* `test_cli_mcp_parity.py`
  table via its `_cli_json`/`_mcp_data` helpers (AC-1.7), plus the `repo="."` no-change
  regression (AC-1.8).
- **Introspection guards (T6)** — AC-1.10 (no bypass reachable, and none existing), NFR-7
  (no rule text in the adapters), NFR-1 (no file contents read; timed verdict). These are the
  cheapest defence against the design silently eroding later.
- **Build bounds (T8/T9)** — synthetic over-limit tree, oversized-file skip with a patched
  `read_bytes` proving the bytes are never read, ancestor-symlink termination, and
  byte-identical graphs for accepted repos (AC-3.4/NFR-2).
- **Doc introspection (T10–T12)** — extends the v0.3.1 harness technique (section extraction +
  keyword assertions), not a new harness. NFR-5 is honest about the limit: these catch
  regression, not adversarial rephrasing, so `/peer-review` must still read every guarantee
  sentence against the code. The graph indexes no Markdown, so these three tasks carry no
  blast-radius coverage at all (§2) — the doc tests are the only automated net under them.
- **Deliberately manual, in `/peer-review`:** clean-env packaged install, `serve` boot, the
  real-repo `impact` sanity run, and the human reading of `SECURITY.md` (NFR-5). AC-2.8 is
  verified by the maintainer in the GitHub UI — there is no API-free way to assert it from a
  test, and faking one would be worse than naming it.

## 5. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| **R1 — Marking the fixtures reverses a user-resolved question (Q3/A11).** The spec resolved for an internal test-only bypass; this plan ships none. | If the user wants the bypass, T2 and T6 change shape (a module-private context manager + a `bypassed == non-bypassed` equivalence test) — roughly one task's rework, no change to T1/T3/T4. | Raised explicitly at the plan gate as a veto point. The spec *accepts* a bypass, it does not require one; AC-1.10 and NFR-9 are satisfied more strongly by its absence. Recorded as the first rejected alternative in §1 so a later reader sees a decision, not an oversight. |
| **R2 — The autouse marker hides a refusal bug, and `conftest.py` is a high-radius file.** Every `tmp_path` becomes acceptable, and `impact` links `conftest.py` to all six `close-the-loop` US-1 ACs. | A legitimate repo shape refused in the field; or a fixture change that quietly moves another feature's assertions. | T1 tests every marker shape directly rather than through fixtures; T5's parity table carries accepted rows; T2's DoD forbids any moved count, assertion or graph byte; T13 builds this repo and `sample_repo` (real `.git` + real `.spark/`) end-to-end. |
| **R3 — The pinned entry bound rests on a thin sample.** Seven local repos, one machine (macOS Darwin 22.6.0, 2026-07-26), largest 23,688 `rglob` entries; ~10,000 entries/s. `MAX_ENTRIES = 200_000` is ×8.4 headroom over the largest measured repo. Big monorepos were **not** measured. | A legitimate very large repo is refused; or a pathological target still takes ~20 s (200k entries at the measured throughput) before refusing. | The number, its sample, its machine, its date and the headroom factor go in the module docstring **and** in `SECURITY.md` (AC-2.9), stated as a measurement over 7 repos — never as a survey. The trade is recorded deliberately: never refuse a real repo first, terminate in tens of seconds second. Raising the constant is a one-line change with a doc test that follows. |
| **R4 — `SECURITY.md` (Must) depends on US-3 (Should).** AC-2.9 requires the document to state the build limits and their basis. | If US-3 is cut, AC-2.9 describes limits that do not exist. | T10 depends on T9 and the table is ordered so US-3 lands before the document. If the user cuts US-3 at the gate, AC-2.9 must be re-scoped in the spec (the doc would then state that no bounds are enforced) — a question back to the Product Owner, not a silent edit. |
| **R5 — AC-2.4's denylist collides with legitimate prose.** *contain* matches "contains"; *prevent*/*protect* are natural in security writing. | A red doc test on honest prose, or a weakened check. | The denylist runs on the document with *Non-guarantees* removed, is case-insensitive on stems, and its failure message names the offending line. `SECURITY.md` is authored around it ("holds", "includes", "refuses"). Accepted: the check is regression cover, not adversarial cover (NFR-5). |
| **R6 — Refusal changes the response shape for paths that previously answered.** An unmarked directory queried today returns `{"found": false, "error": "No graph found…"}`; after this change it returns `{"found": false, "reason": "outside_confinement", "message": …}`. | A consumer keying on `error` for that case sees `message`. | Spec-mandated (AC-1.2), and `found: false` is unchanged, which is what A13 says Core branches on. `load_graph` keeps building its message from the *original* argument so the marked-but-unbuilt case stays byte-identical (T4 DoD). NFR-4 asserted by T5/T13. |
| **R7 — The blast radius is `inferred`-only and incomplete.** All 27 affected ACs come from git history, from just two past features; `go-rust-support`, `incremental-builds` and `robustness` returned nothing, and the three doc files plus `test_build.py` returned nothing at all. | Over-trusting the result would make three doc tasks and the byte-identity tests look risk-free when they are simply unindexed. | §2 states the tier and the gaps explicitly; the affected code was read directly (the four modules and the two test files are cited by definition in §2). T13's byte-identity and full-suite sweep is the actual net under `test_build.py`; the doc tests are the net under T10–T12. |
| **R8 — Inherited spec assumptions.** A7 (first build of a monorepo subdir stops working), A8 (marker-less source export refused), A12 (pre-confinement graphs stay queryable), A13 (Core branches on `found`, unverified from this repo). | Real behaviour changes for users on those paths. | All four are user-accepted spec decisions; the plan inherits them unchanged and does not widen them. A12/A13 are recorded in `SECURITY.md` (T10) so the next cycle finds the assumption instead of re-deriving it. |

## 6. Increment Notes (T13 regression sweep — for /peer-review's head start)

- **Full suite:** 275 passed (`uv run pytest`), 2 passed (`uv run pytest -m slow`). Zero failures at any point once the walking skeleton (T3) landed.
- **`sample_repo` byte-identity — verified against actual pre-change code, not just double-build.** `git stash push -u` reverted the working tree to HEAD (no confinement/bounds code, no new tests); built `sample_repo`, captured `graph.json`; `git stash pop` restored the increment; rebuilt `sample_repo`. The two are **byte-identical** (`json.dumps(..., sort_keys=True)` equality). This is the strongest form of AC-3.4/NFR-2 evidence available — a fixed fixture, old code vs. new code.
- **This repo's own graph, same before/after comparison:** 139 nodes added (the files this increment added: `confinement.py` + 5 new test files), 0 nodes removed, 72 pre-existing nodes changed **only** in `hash`/`line` (expected — their source files were legitimately edited). One non-obvious finding: **4 `inferred` `implements` edges from `task:close-the-loop:T9` disappeared.** Traced to `inference.py`'s pre-existing F1 disambiguation rule: this plan's own task table also defines a `T9` (§3), so a historical commit whose message says only "T9" now id-matches **two** features instead of one and correctly contributes no edge (honest absence over a wrong cross-feature link — the exact behaviour `close-the-loop`'s F1 non-negotiable in `CLAUDE.md` specifies). Not a code regression; a pre-existing mechanism reacting correctly to ordinary per-feature task-number reuse. Worth `/peer-review` knowing so it isn't re-derived.
- **`aspark-graph query impact`** on this repo (`confinement.py`, `build.py`, `queries.py`) returns `found: true` with all three files resolved — sane on the live, rebuilt graph.
- **Clean-env packaged install:** `uv build` → fresh `uv venv` (Python 3.13) → `uv pip install` the wheel only. Verified: `cryptography`/`joserfc` absent; `build`/`query` work against `sample_repo`; **confinement refusal works from the packaged install** (`aspark-graph build /tmp` → exit 1, clean message); `serve` boots, completes the JSON-RPC `initialize` handshake, and registers exactly the 9 expected tools (`tools/list`). Matches the `distributable-install` precedent's verification method.

---

## ✅ PLAN GATE

*All boxes checked → `/increment` may start. Any box open → back to `/sprint-plan`.*

- [x] Spec status is `approved` (never plan against a draft) — 2026-07-26
- [x] Architecture decision includes rejected alternatives (a decision without alternatives is a guess) — five, incl. the bypass
- [x] Architecture respects the constitution's technical constraints — no constitution exists; CLAUDE.md non-negotiables honoured: thin adapters (NFR-7, T6 guard), determinism (AC-3.4/NFR-2, T8/T9/T13), fail loudly / clean errors (NFR-3), `mcp` cap and dependency set untouched
- [x] Every task maps to a user story — no orphan tasks, no story without tasks
- [x] Every Must AC and every applicable NFR is covered by at least one task — NFR-8 N/A (headless)
- [x] Every task has a checkable definition of done
- [x] Task order respects dependencies — T7 (user-owned) precedes T10 by construction
- [x] Test strategy covers every Must story
- [x] Status set to `approved` by the user — 2026-07-27, explicit approval at the `/spark` plan gate; R1 accepted as designed (no bypass, fixtures marked)
