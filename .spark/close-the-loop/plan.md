# Plan: close-the-loop

| | |
|---|---|
| **Phase** | Plan |
| **Owner** | Engineering Manager (`/sprint-plan`) |
| **Input** | `.spark/close-the-loop/spec.md` (`approved`) |
| **Status** | `approved` |
| **Date** | 2026-07-14 |

## 1. Architecture Decision

<!-- Mini-ADR. The EM decides — but shows the alternatives that were rejected and why. -->

- **Context:** v0.1.0 shipped a correct, byte-deterministic read model (`model.py`
  → `graph.py` → `build.py` → `queries.py`, with `cli.py`/`server.py` as thin
  adapters). The `implements` (task→code) edge — the one bridge from a *changed
  file* to the *stories QA must re-verify* — exists **only** where a plan task
  carries an inline `files:` note (`artifacts._files_note` / `_FILES_NOTE_RE`),
  and real aSPARK plans never write those. On the aspark-graph repo itself the
  built graph therefore has **zero** `implements` edges and `impact` on a real
  source file returns empty. This cycle must derive `implements` edges from data
  that is *already present in a normal repo* — repository history (Q2-confirmed) —
  while never breaking the two contracts the whole tool rests on: it stays
  **deterministic and offline** (A5 / AC-1.5 / v0.1.0 AC-1.2), and it is **honest
  about confidence** (A4 — inferred is a distinct, weaker tier). This is a second
  cycle on a codebase with an established culture: I extend the existing modules
  and conventions (thin adapters, canonical sorted `graph.json`, fail-loud parser,
  `Confidence.rank()` weakest-edge tagging) rather than reinvent them.

- **Decision:** Add a new, self-contained **`inference.py`** module that derives
  `implements` edges from **git commit history read via `git` as a subprocess with
  a pinned, offline, plumbing-only invocation** — no new dependency, no network.
  The determinism problem (task status transitions are *not* timestamped in the
  plan artifact, so we cannot bound a time window) is solved by **not using time
  at all**. Instead we key inference on data that is a pure function of the
  committed repo state:

  > **For each Task node that maps to a Story, find the commits reachable from
  > `HEAD` whose commit *message* references that task's id (`T<n>`) or its
  > mapped story's id (`US-<n>`); take the set of tracked source files those
  > commits touched (`git log --format=... --name-only`, no dates, no merges via
  > `--no-merges`, walked in git's default topological-then-reverse-chronological
  > order which is fixed for a fixed commit graph); for every such file that is a
  > `File` node in the graph, add a `Task --implements--> File` edge tagged
  > `Confidence.INFERRED`.**

  This is deterministic because the input is the immutable commit DAG reachable
  from a fixed `HEAD` plus the (already-in-graph) task/story ids — the same repo
  state always yields the same commit set and therefore the same edges (AC-1.5).
  It is offline because `git log` reads only the local object store. A third
  confidence tier `Confidence.INFERRED` (rank 0, below `EXTRACTED`=1 /
  `DECLARED`=2) is threaded through `model.py`, and — because `_RANK_CONF` and
  `_reach` in `queries.py` are already **data-driven off `Confidence.rank()`** —
  the weakest-edge tagging picks it up with *no* change to the impact algorithm
  (only its output gains a new possible tag value). Two convenience surfaces ride
  the same engine: **staleness** (US-4) is a query-layer check comparing each
  `File` node's stored `hash` against the file on disk (data already present per
  A6), and **`impact --diff <range>`** (US-3) resolves a git range to a file list
  via the same subprocess helper and feeds the *existing* `impact(files)`
  unchanged. If git is unavailable (not a repo, shallow/empty clone, `git`
  missing) inference returns **zero edges** and the build proceeds exactly as
  v0.1.0 (AC-1.6).

  **Self-fulfilling commit convention (user decision, 2026-07-14).** Because the
  chosen signal is the commit-message id-reference, it only fires on repos whose
  commits reference task/story ids — and the dogfood repo today has a single
  release commit that references **none**, so inference would find zero edges and
  the AC-1.1 headline (measured, per spec, on *this* repo) would fail. The user
  therefore adopts the id-referencing commit convention as an **aspark-graph-internal
  working rule for this cycle**: `/increment` makes one commit per task whose
  message references the task id **and** the mapped story id. This makes the repo
  self-hosting for its own inference by the end of the cycle. It is **not** a change
  to aSPARK itself (A7 stays intact — no aSPARK template/agent edit ships here);
  the *general recommendation* that aSPARK commits reference ids is documentation
  only, in US-5. **No `files:` notes are retrofitted** — the convention + inference
  carry the proof on their own (the user chose the convention, not a belt-and-braces
  declared-note pass).

- **Alternatives considered:**

  *For the inference mechanism (the crux):*

  | Alternative | Why rejected |
  |---|---|
  | **Time-window: commits between a task going `doing` and `done`** | The plan artifact records task `status` but **no timestamp** for any transition, and commit author/committer dates are wall-clock and rewritable — using them would make the graph depend on when commits happened, not on repo *state*, breaking AC-1.5 the moment a repo is rebased or re-cloned. There is no deterministic, offline clock to anchor a window to. Rejected outright by A5. |
  | **`git blame` per line → map lines to defs → tasks** | Blame output depends on merge/rename detection heuristics and diff algorithm settings that are not guaranteed stable across git versions, and it links files to *commits*, not to *tasks* — we would still need a commit→task bridge (the message reference), so blame adds nondeterminism risk without removing the hard step. Far heavier per-file cost for no gain over `--name-only`. |
  | **File mtime / filesystem timestamps** | Not committed state at all; changes on every checkout/clone. Flatly violates A5. Explicitly out of scope per spec §5 ("any non-deterministic inference source"). |
  | **LLM / embedding-assisted "which file implements this story"** | Non-deterministic and requires network/model access — violates both halves of A5 and the tool's founding no-LLM contract. Out of scope per spec §5. |
  | **Pure path-heuristic (task title/story keywords → filename match)** | Deterministic and offline, but fabricates links from coincidental name overlap with no evidence a human ever connected them — high false-positive rate would poison `impact` at exactly the tier (`inferred`) consumers are told to trust least-but-still-act-on, undermining AC-1.4. Kept in reserve as a *documented* future signal, not shipped. |

  *For the commit→task binding within the chosen mechanism:*

  | Alternative | Why rejected |
  |---|---|
  | **Bind commits to tasks by touched-file overlap with the `.spark/` plan edits** | Every task's commits also touch the plan file, collapsing all tasks to the same commit set — no discrimination between tasks. |
  | **Only match story ids (`US-n`), never task ids** | Coarser: loses the finer task-level attribution when commit messages name a `T<n>`; matching both id shapes strictly widens recall without hurting determinism. Adopted **both** id shapes instead. |

  *For structural choices:*

  | Alternative | Why rejected |
  |---|---|
  | **A new dependency (`pygit2`/`GitPython`) to read history** | A liability that must beat "we call `git log` in ~30 lines ourselves." It does not: a single pinned `subprocess.run(["git", "log", ...])` with `--no-merges --name-only -z` is boring, offline, and needs no wheel. Rejected on the every-dependency-is-a-liability rule, consistent with v0.1.0's `argparse`-over-`click` decision. |
  | **Compute staleness inside `build`/CLI only** | Would duplicate the check and let CLI and MCP drift. Placed in `queries.py` (a `staleness(graph, repo_root)` helper the existing thin adapters call) so both surfaces get it identically — the v0.1.0 thin-adapter convention (AC-5.1) applied to a new capability. |
  | **`impact --diff` as a new query function** | Unnecessary: a diff is just a way of *producing the file list* the existing `impact(files)` already consumes. Resolve the range to files at the adapter/entry edge and reuse `impact` untouched — AC-3.1's "same result as passing the files explicitly" is then true by construction. |

- **Consequences:**
  - *Easier:* `impact`/`story_trace` become non-empty on real repos with zero
    artifact-authoring effort (the core mandate). Because `_reach`/`_RANK_CONF`
    are already keyed on `Confidence.rank()`, adding the `inferred` tier is a
    model change that the impact engine inherits for free. Staleness and `--diff`
    are thin additions that reuse the existing engine and adapter pattern, so
    CLI≡MCP parity holds by construction. The dogfood fixture (this very repo)
    becomes the headline test once the cycle's own task-commits exist.
  - *Harder:* We now shell out to `git`, so the build's determinism depends on
    git's *documented* stable ordering (`--no-merges`, reverse-topo default) and
    on message-reference discipline — carried as the top risk in §5 and pinned by
    a determinism test (double-build byte-equality) and an explicit invocation.
    Inferred edges can be wrong (name-collision in a commit message) — mitigated
    by the weaker tier and the AC-1.4 human-confirmation `/demo-day` step; we must
    never emit an inferred edge at `declared`/`extracted` strength. Every
    v0.1.0 confidence-tagging test now runs against a three-tier enum, so a
    dedicated **no-regression task (T8)** re-runs the whole v0.1.0 suite. The
    commit convention adds process discipline on `/increment` (one id-referencing
    commit per task) — cheap, but load-bearing for the dogfood AC-1.1 proof.

## 2. Affected Components

<!-- Files, modules, services, external dependencies. New dependencies need a justification. -->

Existing standalone repo `aspark-graph` (v0.1.0 → v0.2.0). Changes are additive and
respect the v0.1.0 layout; **one new module** (`inference.py`) plus focused edits.

| Component | Change | For |
|---|---|---|
| `src/aspark_graph/model.py` | Add `Confidence.INFERRED = "inferred"` (rank **0**); update `.rank()` map to `{INFERRED:0, EXTRACTED:1, DECLARED:2}`. No id-scheme or edge-type change (`EdgeType.IMPLEMENTS` already exists). | US-1, US-2 (A4) |
| `src/aspark_graph/git.py` *(new, tiny)* | One offline helper module wrapping `git` via `subprocess`: `is_git_repo(root)`, `commits_touching(root, ids) -> {file: matched}`, `diff_files(root, range) -> (files, unknown/err)`. Pinned invocation (`--no-merges`, `-z`, `--name-only`, no dates). Returns empty/typed error, never raises to the caller, on missing-git/not-a-repo/shallow (AC-1.6, AC-3.3). | US-1, US-3 |
| `src/aspark_graph/inference.py` *(new)* | `infer_implements(graph, repo_root)`: for each Task node with a `maps_to` story, gather commit-touched files whose commit message references the task id (`T<n>`) or mapped story id (`US-<n>`); add `Task --implements--> File` edges at `Confidence.INFERRED`, only when the `File` node exists (no dangling/fabricated edges — mirrors the `_files_note` guard). Deterministic ordering; no network. | US-1, US-2 |
| `src/aspark_graph/build.py` | After `artifacts.extract_features(...)`, call `inference.infer_implements(graph, repo_root)` (declared `implements` from `files:` notes already added, so they win / are not overwritten). Extend `BuildReport` with `inferred_edges: int`. Degrade silently to 0 when git absent (AC-1.6). | US-1, US-2 |
| `src/aspark_graph/queries.py` | (a) `_IMPACT_STEPS` already has `IMPLEMENTS` "in" from File/Class/Function — **no algorithm change**; `_RANK_CONF`/`_reach` inherit the new tier via `Confidence.rank()`. (b) New `staleness(graph, repo_root) -> {stale, changed:[...], missing:[...]}` comparing File-node `hash` to on-disk sha256 (A6). (c) `impact_diff(graph, repo_root, range)` — resolve range via `git.diff_files`, then call existing `impact(graph, files)`; surface unknown paths (AC-3.2) and empty/invalid range message (AC-3.3). (d) `story_trace`/`impact` results already carry per-link `confidence`; verify inferred surfaces as `"inferred"` (AC-1.3/AC-2.2). | US-1..US-4 |
| `src/aspark_graph/cli.py` | Add `query staleness`; add `--diff <range>` to `impact` (mutually exclusive with positional `files`); optionally attach a staleness banner to query output (US-4). Thin: delegates to `queries.py` only. | US-3, US-4 |
| `src/aspark_graph/server.py` | Add `staleness` tool; add optional `diff` param to the `impact` tool (delegates to `queries.impact_diff`). Thin. | US-3, US-4 |
| `README.md` | (a) Document **both** declarative link paths the tool recognises (US-5), stating which yields which confidence: the inline **`files:` note → `declared`**, and the **commit-message id-reference (`T<n>`/`US-<n>`) → the signal inference reads → `inferred`**; include a reproducible example of each. (b) Document that inferred `implements` edges exist and are weaker (US-1/A4). (c) Remove the fictional `uvx`/PyPI install path; document only from-source `uv`/`uv run` and (optionally) a local wheel (US-6). |
| `tests/` | New fixtures + tests (see §4), incl. a **git-backed fixture repo** (real, id-referencing history) built in a `tmp_path` for the hard automated proof, and a determinism (double-build) test for inference. |

**New dependency:** **none.** Git history is read through the stdlib `subprocess`
against the already-present `git` binary — the same "beat writing ~30 lines
ourselves" bar v0.1.0 used to reject a CLI framework. No `pygit2`/`GitPython`.
**No new service** (still stdio MCP + CLI). **New pattern justified:** shelling out
to an external tool (`git`) is new for this codebase; it is confined to the single
`git.py` module with a pinned, offline invocation and total-failure-returns-empty
contract, so the determinism/offline guarantees are auditable in one place.

## 3. Task Breakdown

<!-- Ordered. Every task maps to a story from the spec and has its own definition of done.
     /increment works through this table top to bottom — nothing else — and keeps Status current. -->

Ordering: the **walking skeleton (T1–T3)** delivers the *smallest end-to-end
non-empty result* first — a third confidence tier plus a git-backed `implements`
edge that makes `impact` on a real file return ≥1 story — killing the central
integration risk (deterministic git inference) before the convenience features.
The two Musts (US-1, US-2) land by T5; the no-regression gate is T8; Shoulds
(US-3/US-4/US-5/US-6) follow.

**Load-bearing working convention for this cycle (like v0.1.0's thin-adapter rule).**
Because the inference signal is the commit-message id-reference, `/increment` MUST
make **one commit per task** whose message references **both** the task id and the
mapped story id — subject line `T<n>: <summary> (US-<m>)` **or** a `Refs: T<n>,
US-<m>` trailer. This is what makes the dogfood repo self-hosting so the AC-1.1
headline can be verified hands-on on the real repo (self-fulfilling). It is an
aspark-graph-internal work rule only — **no aSPARK template/agent change ships here**
(A7). No `files:` notes are retrofitted; the convention + inference carry the proof.

| # | Task | Story | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|
| T1 | Add `Confidence.INFERRED` (value `"inferred"`, rank 0) to `model.py`; update `.rank()` map. | US-1 | – | `done` | Unit test: `Confidence.INFERRED.rank() == 0 < EXTRACTED(1) < DECLARED(2)`; `_RANK_CONF` in `queries.py` now has three entries with `inferred` weakest. Existing v0.1.0 model tests still pass. Committed as `T1: … (US-1)`. |
| T2 | New `git.py`: offline `subprocess` helpers `is_git_repo`, `commits_touching(root, ids)`, `diff_files(root, range)`; pinned invocation (`--no-merges -z --name-only`, no dates); every failure mode (no git binary, not a repo, shallow, bad range) returns empty/typed result, never raises. | US-1 | – | `doing` | Unit tests: in a `tmp_path` git repo with two commits, `commits_touching` returns exactly the files whose commit message referenced the queried id; in a non-git dir all helpers return empty/false with no exception (AC-1.6 seed). Committed as `T2: … (US-1)`. |
| T3 | **Walking skeleton**: `inference.infer_implements(graph, repo_root)` adds `Task --implements--> File` at `INFERRED` for graphed files touched by id-referencing commits; wire into `build.py` (after artifacts) + `BuildReport.inferred_edges`. | US-1 | T1, T2 | `todo` | Against a git-backed fixture repo (task `T1`/`US-1` referenced in a commit that touched `app.py`), `build` produces ≥1 `implements` edge tagged `inferred`, and `impact(["app.py"])` returns ≥1 affected story tagged `inferred`. Runs end-to-end via `build_graph`. Non-git repo → 0 inferred edges, build succeeds. Committed as `T3: … (US-1)`. |
| T4 | Determinism of inference (AC-1.5): guarantee two builds of the same repo state yield identical inferred edges + tags. | US-1 | T3 | `todo` | Test: build the git-backed fixture twice; `graph.to_dict()` is byte-identical across both (extends the v0.1.0 double-build determinism test to include inferred edges). Ordering in `inference.py` is fully sorted/derived, never insertion- or clock-dependent. Committed as `T4: … (US-1)`. |
| T5 | Confirm read-direction (US-2) and graceful absence (AC-1.6, AC-2.3): `story_trace` code section non-empty for a story with inferred code; inferred links tagged distinctly; a story/file with no inferable link still returns cleanly. | US-2 | T3 | `todo` | Tests: `story_trace(US-1)` on the git-backed fixture has a non-empty `code` list with `confidence == "inferred"` (AC-2.1/AC-2.2); a story with no code link returns full declared trail + empty code, no error (AC-2.3); `impact` on a file with no inferable link returns explicit "no affected" (AC-1.6). Declared `files:` note still wins at `declared` (AC-5.2 preserved). Committed as `T5: … (US-2)`. |
| T6 | Headline AC-1.1/AC-1.2 — two-track proof. **(a) Automated (hard proof):** git-backed fixture with realistic id-referencing history in `tmp_path` — deterministic, independent of the real repo's state. **(b) `/demo-day` (self-fulfilling):** once the v0.2.0 task-commits exist, verify on **this** aspark-graph repo. | US-1 | T3 | `todo` | (a) An automated test builds the git-backed fixture and asserts `impact(<file>)` returns non-empty `affected_stories` + `affected_acs` and `len([e for e in graph.edges() if e.type=="implements"]) >= 1` (AC-1.1/AC-1.2), fully in CI. (b) A documented `/demo-day` step builds the real repo (after this cycle's task-commits land) and confirms `impact(<a real src file implementing a close-the-loop story>)` is non-empty — the exact query empty today. Any real-repo assertion is `/demo-day`, not CI (keeps CI hermetic). Committed as `T6: … (US-1)`. |
| T7 | Staleness (US-4): `queries.staleness(graph, repo_root)` compares File-node `hash` to on-disk sha256; CLI `query staleness` + optional banner; MCP `staleness` tool. | US-4 | T3 | `todo` | Tests: unchanged repo → `stale=false`, no warning (AC-4.2); mutate a tracked file → `stale=true` naming the changed file (AC-4.1); rebuild → `stale=false` again (AC-4.3). CLI and MCP return the same staleness dict (parity). Committed as `T7: … (US-4)`. |
| T8 | **No-regression gate**: re-run the entire v0.1.0 test suite unchanged against the three-tier enum + new build step; fix only genuine regressions in confidence-tagging output shape. | US-1 | T1, T3 | `todo` | `uv run pytest` is fully green including all v0.1.0 tests (`test_impact.py`, `test_story_trace.py`, `test_cli_mcp_parity.py`, `test_gate_health.py`, `test_navigation.py`, `test_build.py`, `test_graph.py`, `test_artifacts.py`). Any v0.1.0 AC assertion that changed value is documented in §6, not silently edited. Committed as `T8: … (US-1)`. |
| T9 | `impact --diff <range>` (US-3): `queries.impact_diff` resolves range via `git.diff_files` then calls existing `impact`; CLI `--diff` flag; MCP `diff` param. | US-3 | T2 | `todo` | Tests: `impact_diff(range)` == `impact(files_in_range)` (AC-3.1); range touching an ungraphed path names it as unknown while still answering known files (AC-3.2); empty/invalid range → clear message, no traceback, no silent-empty (AC-3.3). Committed as `T9: … (US-3)`. |
| T10 | US-5 docs+robustness: README documents **both** declarative link paths and their confidence tiers — the `files:` note (→ `declared`) **and** the commit-message id-reference (→ `inferred`), each with a reproducible example; dangling `files:` reference still handled (no crash, no fabricated edge). | US-5 | T3 | `todo` | Test: a fixture task with `files: does/not/exist.py` yields no edge and no error (AC-5.3); a fixture task following the `files:` convention yields a `declared` edge distinct from inferred (AC-5.2); README section documents both paths precisely enough to reproduce, stating which yields `declared` vs `inferred` (AC-5.1). Committed as `T10: … (US-5)`. |
| T11 | US-6 README honesty: remove fictional `uvx`/PyPI claims; document only working install paths (from-source `uv`, optional local wheel) and the `uv run` MCP entry. | US-6 | – | `todo` | README install section contains no `uvx`/PyPI/package-index command (AC-6.1); following it from a clean env reaches a working install and a `build`+`query` run end-to-end (AC-6.2, `/demo-day`); MCP-add instructions use a working non-published entry point (AC-6.3). Committed as `T11: … (US-6)`. |

Story coverage check: US-1 → T1,T2,T3,T4,T6,T8 · US-2 → T5 · US-3 → T9 ·
US-4 → T7 · US-5 → T10 · US-6 → T11 · US-7 (Won't) → no tasks (correct). No
orphan tasks; every in-scope story has ≥1 task. Both Musts (US-1, US-2) land by
T6/T5; the no-regression gate (T8) protects the v0.1.0 contract.

## 4. Test Strategy

<!-- What gets unit tests, what gets integration tests, what is left to /demo-day. -->

Determinism + offline keeps this suite almost entirely automatable. **This is a
CLI/MCP tool, not a browser app: `/demo-day` here is CLI/MCP-driven, not
browser-driven** — the QA template's browser/viewport sections are N/A (matching
the spec's Design Review N/A).

- **Unit tests (pure logic):**
  - `model.py` three-tier `Confidence` and `.rank()` ordering (T1).
  - `git.py` helpers against a `tmp_path` git repo *and* against a non-git dir —
    the graceful-degradation path (AC-1.6) is unit-tested, not just hoped for (T2).
  - `inference.py` commit→task matching and File-node guard (no dangling edge) in
    isolation (T3).

- **Integration / fixture tests (git-backed fixture repo, built in `tmp_path`):**
  - **AC-1.1/AC-1.2 headline — hard automated proof:** a git-backed fixture with
    **realistic, id-referencing history** (commits whose messages carry `T<n>`/`US-<n>`)
    is built → assert ≥1 `implements` edge exists (AC-1.2) and `impact(<file>)`
    returns ≥1 story + ≥1 AC (AC-1.1). This is deterministic and independent of the
    real repo's state, so it is the load-bearing automated evidence (T3, T6). The
    read-direction counterpart `story_trace(US-n)` code section non-empty (AC-2.1) (T5).
  - **The determinism test (AC-1.5):** build the same fixture state twice and
    assert byte-identical `graph.to_dict()` including inferred edges + tags (T4).
  - **Confidence honesty (AC-1.3/AC-2.2):** inferred links carry `"inferred"`,
    strictly weaker than a declared `files:`-note link on the same fixture (T5).
  - **Graceful absence (AC-1.6/AC-2.3/AC-3.3):** non-git repo and no-inferable-link
    cases return clean empty results, never errors (T2, T5, T9).
  - **Staleness (AC-4.1..4.3):** unchanged→current, mutate→stale-naming-file,
    rebuild→current; CLI≡MCP parity on the staleness dict (T7).
  - **`--diff` (AC-3.1..3.3):** diff-derived impact equals explicit-file impact;
    unknown-path and empty/invalid-range handling (T9).
  - **`files:` convention (AC-5.1..5.3):** declared beats inferred; dangling ref
    is safe (T10).
  - **No-regression (T8):** the *entire* v0.1.0 suite runs unchanged and green —
    the load-bearing guard for "we did not regress confidence tagging."

- **Left to `/demo-day` (CLI/MCP, deliberately not automated):**
  - **AC-1.1 on the real dogfood repo (self-fulfilling):** once this cycle's
    id-referencing task-commits exist (the working convention above), build the
    real aspark-graph repo and confirm `impact(<a real src file>)` returns ≥1 story
    + ≥1 AC — the exact query empty today. This complements the hermetic fixture
    test (which is the hard proof); the real-repo run is the observable success
    signal the spec pins to this repo.
  - **AC-1.4 human confirmation:** a reviewer confirms the story returned for a
    real file is genuinely one that file helps implement — a judgement call the
    spec assigns to a human, not an assertion. Run in a live Claude Code session.
  - **US-6 clean-environment install (AC-6.2):** following the corrected README
    from a fresh env reaches a working install + `build`+`query` — verified
    hands-on, not in CI.
  - **MCP tools answering inside a live Claude Code session** (new `staleness`
    tool + `impact --diff`) — protocol/tool-visibility can't be fully asserted
    in-process.

Every Must is covered by automated tests (US-1: T1/T2/T3/T4/T6(a) + regression T8;
US-2: T5), with the real-repo AC-1.1 confirmed additionally at `/demo-day`. No Must
relies on "manual testing only".

## 5. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| **Determinism of git inference (A5/AC-1.5) — the headline risk.** Commit ordering, merge handling, or a rebased/re-cloned history could make the same *logical* repo yield different inferred edges. | High — breaks the founding contract and the whole reason the tier is trusted. | Key inference on repo *state* only (commit set reachable from `HEAD` matched by message id-reference), never on time/mtime/author-date. Pin the `git log` invocation (`--no-merges -z --name-only`, no date fields) in the single `git.py` module. Enforce with a **double-build byte-equality test (T4)** and fully sorted/derived ordering in `inference.py`. If any residual nondeterminism is found, the fallback is to drop the offending signal rather than ship it (spec §5 makes non-deterministic inference out of scope). |
| **Dogfood repo has no id-referencing commits today.** The single release commit references no task/story id, so inference on the real repo finds zero edges → the spec's AC-1.1 headline (measured on this repo) would fail as-is. | High — the headline Must would read as unmet on its own witness. | **Self-fulfilling commit convention (user decision):** `/increment` commits one id-referencing commit per task (§3 working rule), so the repo hosts task-referencing commits by cycle end and inference fires on it. The **hard automated proof** does not depend on this — it runs against a purpose-built git fixture (T6a). The real-repo run is the `/demo-day` confirmation (T6b). If `/increment` forgets the convention, T6a still passes but T6b (and the spec's on-repo success signal) would not — so the convention is called out as load-bearing. |
| **Regression to v0.1.0 confidence tagging.** Adding a third tier touches `Confidence.rank()`, which `_RANK_CONF`/`_reach` and every confidence-tagging test depend on. | High — could silently change existing `impact`/`story_trace` tags. | The impact algorithm is already data-driven off `.rank()`, so the change is additive; but **T8 re-runs the entire v0.1.0 suite unchanged** as a gate, and any changed AC value is recorded in §6 rather than edited quietly. Inferred is rank 0 (weakest), so it can only *lower* a path's tag when a strictly weaker link is on it — never raise an existing declared/extracted result. |
| **Inference false positives (AC-1.4).** A commit message that mentions `US-1` while touching an unrelated file creates a wrong `implements` edge. | Medium. | Emit only at `Confidence.INFERRED` (distinct, weakest tier) so no consumer mistakes it for declared; guard every edge on the `File` node existing (no fabricated targets); the AC-1.4 human-confirmation `/demo-day` step catches obviously wrong links; declared `files:` notes always win at their stronger tier. |
| **git unavailable / shallow / not a repo (AC-1.6).** The tool must degrade, not crash. | Medium. | `git.py` returns empty/typed results on every failure mode and never raises to `build`; unit-tested against a non-git dir (T2). Inference absence yields the v0.1.0 empty-but-clean behaviour, not an error. |
| **`--diff` range resolution edge cases (AC-3.2/3.3).** Bad ranges, paths outside the graph, deletions. | Low–Medium. | Resolve range only to a file list at the edge and reuse the *existing* `impact` (which already handles unknown paths, AC-3.4→AC-3.2); empty/invalid range returns an explicit message via `git.diff_files`'s typed error, tested in T9. |
| **README honesty vs. reality (US-6).** Any lingering `uvx`/PyPI claim is a live dead end. | Low. | T11 removes all package-index claims; AC-6.2 install is a `/demo-day` walkthrough from a clean env. |

Inherited spec assumptions this plan accepts as-is: A6 (file hashes already on
File nodes — staleness needs no new data), A7 (no aSPARK-side template/agent
change ships here; the commit convention is an aspark-graph-internal work rule and
the general recommendation is US-5 doc only; US-1 does not depend on an aSPARK PR),
A1 (mechanism was the EM's call — made above). A4 and A5 are treated as **binding
guardrails**, not soft goals.

## 6. Deviations (recorded during `/increment`)

<!-- Filled during /increment. Any AC output value that changes vs. v0.1.0 is recorded here, not edited silently. -->

_None yet — plan is `draft`._

---

## ✅ PLAN GATE

*All boxes checked → `/increment` may start. Any box open → back to `/sprint-plan`.*

- [x] Spec status is `approved` (never plan against a draft)
- [x] Architecture decision includes rejected alternatives (a decision without alternatives is a guess)
- [x] Every task maps to a user story — no orphan tasks, no story without tasks
- [x] Every task has a checkable definition of done
- [x] Task order respects dependencies
- [x] Test strategy covers every Must story
- [x] Status set to `approved` by the user
