# Plan: shallow-clone-warning

| | |
|---|---|
| **Phase** | Plan |
| **Owner** | Engineering Manager (`/sprint-plan`) |
| **Input** | `.spark/shallow-clone-warning/spec.md` (must be `approved`) |
| **Status** | `approved` |
| **Date** | 2026-10-03 |

<!-- Handoff: read this block first, the numbered sections below by exception. Whoever
     writes to this plan updates it in the same edit that changes a task's status or
     the plan's own status: overwrite in place, never append. The block holds one
     current state, never a per-round log; a stale block is a defect, not a cosmetic
     issue. -->

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Summary:** One never-raising `git.read_history()` makes one `git rev-parse --is-inside-work-tree --is-shallow-repository --git-path shallow` call. It returns the state (`full`/`shallow`/`none`) and, when shallow, the grafted boundary SHAs read from the shallow file. `build_graph` calls it once, before inference and only when ≥1 Task exists. The state goes to `BuildReport` (notice and MCP keys, unchanged). The boundary set goes to `infer_implements`, which drops those commits by `%H` inside `git.log_records`. If a shallow repo's boundary cannot be read, inference adds no edges (C12). Non-shallow builds: zero diff from v0.7.1.
- **Open:** `none`. All 16 tasks done (T3 reopened and closed, T10–T16 new in round 2); increment record and deviations at the end of this plan.
- **Binding ruling:** §3 Task Breakdown for current task status; a plan revision after review/QA findings updates §1/§3 in place, never a new section
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Architecture Decision

- **Context:** Round 1 (T1–T9) added the notice and the MCP keys and left inference
  alone. Review F1 found that in a shallow clone the grafted boundary commit has no
  parent, so `git log --no-merges --name-only` (`git.py::log_records`) lists every
  tracked file for it, and inference links all of them. That is why this repo at
  `19a5bef` showed 40/181 against 4/17. Spec round 2 (C11, US-5) requires that
  boundary commits contribute no inferred edges. C12 adds two constraints: detection
  and the fix share one local git call per build (median rise < 5%), and an
  undeterminable boundary means no inferred edges, never an exception. NFR-4 now
  demands zero diff on every non-shallow build. On shallow builds the only change
  allowed is the loss of the boundary commits' inferred edges. Precedents still
  apply: `BuildReport.shadowed`, thin adapters, `git.py`'s "return less, never
  raise", and the CLAUDE.md non-negotiables (determinism, old-code round-trip,
  marked fixtures). There is no constitution.
- **Decision:**
  1. **`git.read_history(root) -> GitHistory`**, a frozen dataclass with
     `state: str` and `boundary: frozenset[str] | None`. It makes exactly one
     `_run(root, ["rev-parse", "--is-inside-work-tree", "--is-shallow-repository",
     "--git-path", "shallow"])` call. The state rules are the round-1 ones,
     unchanged: line 1 decides `none`, line 2 decides `shallow`. On `full` or `none`,
     `boundary = frozenset()` and no file is read. On `shallow` the helper reads
     `Path(root) / line3`, which handles both relative and absolute
     `--git-path` output. Every non-empty line must be 40 or 64 lowercase hex.
     A missing or unreadable file, an empty file or any malformed line gives
     `boundary = None`, meaning undeterminable (C12). `history_state(root)` stays
     as a one-line wrapper (`read_history(root).state`), so T2's matrix and its
     callers are untouched.
  2. **`git.log_records(root, *, skip=frozenset())`** adds `%H` to its format and
     drops a record whose hash is in `skip`. The record shape stays
     `{"message", "files"}`. The hash never leaves `git.py` and never reaches the
     graph. It is content-derived, not a date, so determinism holds. With an empty
     `skip` the output is the same as today's.
  3. **`inference.infer_implements(graph, root, history=None)`:**
     - return 0 when there is no Task node (the output is the same as before, with
       0 git calls);
     - if `history` is None, call `read_history` itself, so no entry point can
       invent links;
     - `state == "none"` → 0, replacing its own `is_git_repo` call (the same test,
       one call fewer);
     - `state == "shallow"` with `boundary is None` → 0 (C12);
     - otherwise pass `skip=boundary` to `log_records`. The F1 feature-resolution
       logic stays untouched.
  4. **`build_graph`** moves the gated call ahead of inference:
     `history = git.read_history(root) if graph.nodes(TASK) else None`, then
     `report.git_history = history.state`, then
     `infer_implements(graph, root, history)`. A Task build makes 3 git calls,
     the same as v0.7.1 (`is_git_repo` ×2 + `log`) and one fewer than round 1. A
     no-Task build now makes 0.
  5. The adapters, the notice constants, the `BuildReport` properties and the
     two MCP keys stay as they are (NFR-6: the decision lives in
     `git.py`/`inference.py`/`build.py`).
- **Alternatives considered:**
  | Alternative | Why rejected |
  |---|---|
  | Treat a parentless commit (`%P` empty) in a shallow repo as the boundary, with no file read | It also drops a genuine root inside a shallow repo (multi-root history, `--shallow-since`), and git's rendering of a grafted *merge* is unverified: the round-1 evidence shows a grafted merge tip still skipped by `--no-merges`, so git may report its real parents. The shallow file is git's own list of grafts. |
  | A second git call (`cat-file`/`rev-list --boundary`, or a separate `rev-parse --git-path`) | Breaks C12/NFR-1 (one shared call). |
  | Drop *all* inferred edges whenever the repo is shallow | Violates AC-5.3 (the newer kept commits must keep their edges). It is used only as the C12 fallback. |
  | Drop commits touching more than N files | A heuristic that also changes full repos, which violates AC-5.5/NFR-4 (§6 keeps bulk commits as v0.7.1). |
  | Expose the hash in `log_records` records and filter in `inference.py` | Leaks a hash into a record shape that `commits_touching` and the F1 logic consume. Filtering at the source keeps the hash private to `git.py`. |
  | Read `.git/shallow` via `pathlib` | Wrong for a subdirectory build, a worktree (`.git` is a file) and `GIT_DIR` (A7). `--git-path` resolves all three. |
  | Keep round 1's `--is-shallow-repository`-only call, which rejected `--git-path` for depending on file layout | Round 1 needed only the fact. US-5 needs the SHAs, and the shallow file is a documented repository-layout file (`gitrepository-layout`: one object name per line). Reversed on purpose. |
  | Fetch the boundary's real parent to diff it | Network access, out of scope (§6, NFR-2). |
  | GitPython / dulwich | A new dependency for one `rev-parse` and one file read. |
- **Consequences:**
  - *Easier:*
    - A shallow `impact` answer is at worst incomplete, so the approved notice
      ("may be missing") becomes accurate (A4).
    - The NFR-1 margin widens: a Task build is back to v0.7.1's 3 git calls, and a
      no-Task build drops to 0.
  - *Harder:*
    - `inference.py` is no longer untouched, so the F1 logic must be shown to be
      unperturbed (T12, T16).
    - `log_records` now parses a hash field.
    - The shallow graph.json differs from v0.7.1 by design, so the round-1
      "6/6 byte-equal" claim is superseded for the shallow input.
    - `build_graph`'s order changed (history before inference). The round-1
      `history_state` spy no longer sees the build, so T3 reopens.
  - *Unchanged:*
    - On git < 2.15 a shallow clone still reads `full` and keeps v0.7.1's
      inflation (R1).
    - When the suite runs from a shallow checkout, `tests/fixtures/sample_repo`
      reads as shallow, and inference on it now skips this repo's boundary
      commits. That is expected, and no existing test asserts inferred counts on
      that fixture under a shallow host (T16 checks it).

## 2. Affected Components

Scoped by hand. The graph was stale on 2026-10-03 (review §1: `staleness` 10 changed
files), so it was treated as absent and no blast-radius result is cited. Read for
this revision: `git.py`, `inference.py`, `build.py`, `tests/conftest.py`,
`tests/test_git.py`, `tests/test_history_notice.py`, `tests/test_cli_mcp_parity.py`,
`tests/test_readme.py`, `README.md:236-251`. `infer_implements` has one caller
(`build.py:180`) and no direct test caller (grep).

| Component | Change |
|---|---|
| `src/aspark_graph/git.py` | + `GitHistory`, `read_history()`; `history_state()` becomes a wrapper; `log_records(skip=)` reads `%H`; docstrings drop "no hash" and say "hash read, never emitted" |
| `src/aspark_graph/inference.py` | `history` parameter, no-Task early return, `none`/C12 early returns, `skip=boundary` |
| `src/aspark_graph/build.py` | gated `read_history` moved before inference and passed in; comment updated |
| `src/aspark_graph/cli.py`, `server.py`, `graph.py`, `artifacts.py` | **unchanged** |
| `README.md` | lines 247-251 reworded (T15) |
| `tests/` | new `test_shallow_boundary.py`; extend `conftest.py`, `test_git.py`, `test_history_notice.py`, `test_cli_mcp_parity.py`, `test_readme.py` |

New dependencies, services and patterns: **none**. Reading a git-owned file is new
to `git.py`. It is justified above, it stays local, and it is never written.

## 3. Task Breakdown

T1–T9 are round 1. T3 is **reopened**: its spy targets `git.history_state`, which
`build_graph` no longer calls. T10–T16 are round 2 (US-5, C11, C12, the amended
AC-1.2/AC-2.4/NFR-1/2/4/6, review F2). Order: T10 → T3 → T11–T15 → T16.

US-5 fixture (`conftest.make_boundary_origin`, built in T10). Tasks T1 and T2 both
map to US-1. Five commits:
- c1 "docs: scaffold" adds the trail plus `src/a.py`, `src/b.py` and `src/c.py`;
- c2 "chore: tweak a" touches `a.py`;
- c3 "T2: work on b" touches `b.py`;
- c4 "T2: work on c" touches `c.py`;
- c5, the tip, "T1: implement a", touches `a.py` and is a non-merge commit.

`make_trail` gains `tasks=("T1",)` (the default is unchanged).

| # | Task | Story | Covers (AC / NFR) | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|---|
| T1 | **Walking skeleton.** Add `git.history_state`, the `BuildReport` field, properties, `history_notice()` and constants, the gated call in `build_graph`, the CLI `print` and the two MCP keys. Add conftest helpers `make_trail(root)` (spec + plan with ≥1 task) and `shallow_clone(src, dst)` (`git clone --depth 1 <src.as_uri()>`; a plain path would silently ignore `--depth`). | US-1, US-2 | AC-1.1, AC-2.1, NFR-6 | – | `done` | A test builds a ≥2-commit source repo whose task id is in a commit message, clones it with `--depth 1`, and runs `cli.main(["build", clone])`: rc is 0 and stderr contains the AC-1.1 line exactly once (`err.splitlines().count(...) == 1`). `server.build_graph(path=clone)` returns `shallow_history is True` and `no_git_history is False`. Full suite green — files: src/aspark_graph/git.py, src/aspark_graph/build.py, src/aspark_graph/cli.py, src/aspark_graph/server.py, tests/conftest.py, tests/test_history_notice.py |
| T2 | `history_state` unit matrix and call budget | US-1, US-4 | AC-1.6, AC-4.4, NFR-1, NFR-2, NFR-4 | T1 | `done` | Tests assert: full repo→`full`; shallow clone→`shallow`; subdir of full→`full`; subdir of shallow→`shallow`; plain dir→`none`; corrupt `.git`→`none`; `PATH=""` (no git binary)→`none`, no exception; detached HEAD→`full`; `--single-branch` full-depth→`full`; zero-commit repo→`full`. Non-git cases set `GIT_CEILING_DIRECTORIES` to `tmp_path` and assert the non-git precondition first. A `_run` spy proves exactly 1 call per `history_state` and that its argv has no remote or URL-related command — files: tests/test_git.py |
| T3 | **Reopened (round 2).** Task gate (C5/A9): no Task node → no check, no notice, keys false. The spy is retargeted to `git.read_history` | US-1, US-2, US-4 | AC-1.7, AC-2.3, AC-4.3, NFR-1 | T10 | `done` | `history_spy` wraps `git.read_history`. On a shallow clone and on a no-git dir, each with a spec but no plan task: `report.git_history is None`, the spy shows 0 calls, CLI stderr contains neither notice, and MCP returns both keys `False`. With a task, the spy shows exactly 1 call per `build_graph`. A `_run` spy shows ≤ 3 git calls per Task build (v0.7.1's count) and 0 per no-Task build — files: tests/test_history_notice.py |
| T4 | No-git notice end-to-end (US-4) | US-4 | AC-4.1, AC-4.2 | T1 | `done` | No-git fixture (`.spark/`-marked, ≥1 task, ceiling env set, precondition asserted): CLI rc is 0 and stderr contains the AC-4.1 line exactly once and no shallow line. MCP on an identical copy returns `no_git_history is True` and `shallow_history is False`. Both graph.json files are byte-equal — files: tests/test_history_notice.py |
| T5 | CLI output contract: stdout, full-clone stderr, `--full` and incremental | US-1 | AC-1.2, AC-1.3, AC-1.4, NFR-3, NFR-5 | T1 | `done` | Shallow fixture: stdout is exactly 2 lines (`Built graph: …`, `Saved to …`) and contains no notice text. A full clone of the same source gives empty stderr. On the shallow clone, a first build, then a `--full` build, then an incremental build (graph present) each print the notice exactly once. Each notice contains no `\x1b` and no path separator — files: tests/test_history_notice.py |
| T6 | Remedy round-trip and no-notice clone shapes, at build level | US-1 | AC-1.5, AC-1.6 | T1 | `done` | Test: shallow clone → notice. `git fetch --unshallow` from the `file://` origin (offline) → rebuild → no notice, and `queries.impact(graph, [<task file>])` equals the full clone's result at the same HEAD (stories, ACs, confidences). A detached-HEAD build and a `--single-branch` full-depth build print no notice. The real-repo evidence (this repo, `--depth 1` → unshallow; HEAD SHA plus story and AC counts for `impact src/aspark_graph/queries.py`) is produced hands-on in `/peer-review` and recorded there — files: tests/test_history_notice.py |
| T7 | CLI≡MCP parity across every US-1/US-4 fixture | US-2 | AC-2.2, AC-2.4, AC-4.4, NFR-6 | T2, T3, T4 | `done` | Parametrised test over {shallow, full, shallow-no-task, no-git, no-git-no-task, subdir-of-full, subdir-of-shallow, detached, single-branch}, with CLI on copy a and MCP on copy b. Asserts: shallow line printed ⇔ `shallow_history`, no-git line printed ⇔ `no_git_history`, never both true, graph.json bytes equal. The MCP key set equals the six v0.7.1 keys plus the two new ones, and on the full clone both new keys are `False` — files: tests/test_cli_mcp_parity.py |
| T8 | v0.7.1 regression sweep: `git stash` round-trip and timing (no code change) | US-1, US-2 | AC-1.2, AC-1.3, NFR-1, NFR-4 | T5, T6, T7 | `done` | Build the shallow, full, no-git, subdir-of-full, `tests/fixtures/sample_repo` and this-repo inputs once under stashed (v0.7.1) code and once under the new code. Result: 0 graph.json byte diffs, identical stdout, and identical stderr except the expected notice lines. Median of 5 builds of this repo, before vs after, shows a rise of < 5%. The commands, SHAs and numbers are recorded in the `/increment` hand-off for `/peer-review`. Round 2: the shallow leg is superseded by T16 |
| T9 | README documents both notices (US-3) | US-3 | AC-3.1 | T1 | `done` | README gains a short subsection under "Linking code to stories" (or next to the full-clone advice, if PR #7 has landed on this branch) that quotes both notices verbatim and names `shallow_history`, `no_git_history` and `git fetch --unshallow`. A test runs the CLI on the shallow and no-git fixtures and asserts each captured notice line is a substring of README.md — files: README.md, tests/test_readme.py |
| T10 | **Walking skeleton (US-5).** Implement §1 Decision 1–4: `GitHistory` + `read_history`, `history_state` wrapper, `log_records(skip=)`, the `infer_implements(history=)` early returns, and `build_graph` reorder. Add `make_boundary_origin` and `make_trail(tasks=)` | US-5 | AC-5.1, NFR-6 | – | `done` | New test: a `--depth 1` clone of the US-5 fixture, built with `--full` and then incrementally, has no `inferred` edge from T1 in graph.json either time. On a full clone of the same origin, T1→`src/a.py` *is* inferred, so the check is not vacuous. The suite is green except `test_t3_with_a_plan_task_exactly_one_check_per_build` (T3 retargets it) — files: src/aspark_graph/git.py, src/aspark_graph/inference.py, src/aspark_graph/build.py, tests/conftest.py, tests/test_shallow_boundary.py |
| T11 | `read_history` and `log_records(skip=)` unit matrix | US-5 | AC-5.1, AC-5.3, NFR-1, NFR-2, NFR-4 | T10 | `done` | Tests assert: full → `boundary == frozenset()`; `--depth 1` → `{rev-parse HEAD}`; `--depth 3` → `{rev-parse HEAD~2}`; subdir of a shallow clone → the same set as its root (R8); `none` shapes → `frozenset()`. With `_run` stubbed to report shallow, a missing file, an empty file or a non-hex line each give `boundary is None` and raise nothing, and a 64-hex line is accepted. A `_run` spy shows exactly 1 call per `read_history`, `rev-parse`, with no remote or URL word. `log_records(r, skip={sha})` equals `log_records(r)` minus exactly that commit's record, with an unchanged `{message, files}` shape. T2's 10-shape `history_state` tests stay green unedited — files: tests/test_git.py |
| T12 | US-5 subset, kept-commit and root-commit behaviour | US-5 | AC-5.2, AC-5.3, AC-5.5, NFR-4 | T10 | `done` | AC-5.2: on `--depth 1` and full clones at the same HEAD, the shallow inferred (task, file) set is a subset of the full set, and the non-`inferred` edge lists are equal. AC-5.3: the `--depth 3` inferred set is exactly {T1→`src/a.py`, T2→`src/c.py`}, the same edges c4 and c5 give on the full clone, and it has no T2→`src/b.py`. AC-5.5: a full repo whose root commit "T1: initial" adds files keeps T1's inferred edges to them. Two builds of the depth-1 and depth-3 clones each give byte-identical graph.json — files: tests/test_shallow_boundary.py |
| T13 | C12: an undeterminable boundary drops all inferred edges and never raises | US-5 | AC-5.2, NFR-4 | T10 | `done` | (a) With `git.read_history` monkeypatched to `GitHistory("shallow", None)` on the depth-3 clone: `report.inferred_edges == 0`, no `inferred` edge in graph.json, the shallow notice printed once, rc 0. (b) A depth-3 clone whose shallow file is overwritten with a non-hex line: CLI rc 0, `Traceback` not in stderr, 0 inferred edges, at most one notice, and the printed notice ⇔ MCP key on a twin copy. The observed state is asserted as found, not presumed (R9) — files: tests/test_shallow_boundary.py |
| T14 | Extend AC-2.4 parity to the US-5 fixtures | US-2, US-5 | AC-2.4, NFR-6 | T3, T10 | `done` | `_SHAPES` gains `boundary-depth1` (True, False), `boundary-depth3` (True, False) and `boundary-full` (False, False), plus `boundary-corrupt-marker` with expectation `None`, which asserts only the ⇔ and never-both rules. All 13 shapes pass: notice ⇔ key, never both true, CLI and MCP graph.json byte-equal — files: tests/test_cli_mcp_parity.py |
| T15 | README: drop the "graph.json stays the same" claim for shallow clones | US-3 | AC-3.1 | T10 | `done` | README:247-251 no longer says graph.json stays the same in general. It says three things: on a shallow clone the build drops the inferred links of the clone's oldest (boundary) commits, so `impact` can show fewer links but never extra ones; exit code and stdout format are unchanged; a non-shallow `graph.json` is unchanged. A test asserts that the old phrase "and `graph.json` stay the same" (whitespace-normalised) is gone. The AC-3.1 real-stderr test stays green — files: README.md, tests/test_readme.py |
| T16 | v0.7.1 regression sweep 2 + timing + this-repo evidence (no code change) | US-1, US-5 | AC-1.2, AC-5.4, AC-5.6, NFR-1, NFR-4 | T11–T15 | `done` | v0.7.1 code from a detached worktree at `b215790` (Deviation 1) vs the new code. Non-shallow inputs: full, no-git, subdir-of-full, detached, single-branch, `sample_repo` copied outside git, a full clone of this repo, the US-5 full clone and the AC-5.5 root-commit repo. Result: 0 graph.json byte diffs, stdout equal, stderr equal apart from the expected notice. Shallow inputs: US-1 shallow, US-5 depth 1 and depth 3, and this repo at `--depth 1` on a non-merge tip. Result: the new edge list equals v0.7.1's minus `inferred` edges only, and stdout differs only in the inferred-link count. AC-5.6: `impact src/aspark_graph/queries.py` on the depth-1 clone gives stories and ACs that are a subset of the full clone's at the same HEAD. NFR-1: 2 warm-ups, interleaved, median of 5 `build --full` runs, < 5%, plus the median cost of one `read_history`. All SHAs, counts and timings go into the Increment record, replacing round-1 numbers |

## 4. Test Strategy

- **Unit (`test_git.py`, T2/T11):**
  - The round-1 `history_state` matrix runs unedited.
  - `read_history` covers boundary parsing for depth 1, depth 3 and a subdirectory,
    plus every undeterminable shape (missing, empty or malformed file) and SHA-256
    lines.
  - `log_records(skip=)` is checked for exact removal and an unchanged shape.
  - A `_run` spy proves one call per `read_history`. No shape may raise.
- **Integration (`test_shallow_boundary.py`, T10/T12/T13; `test_history_notice.py`,
  T1/T3–T6):**
  - Real `git` runs in `tmp_path`, with `file://` clones (R4) and fixed dates
    (`git_commit`).
  - The US-5 fixture has expected edge sets computed by hand. AC-5.3 is pinned as
    an *exact* set, not a subset.
  - C12 is driven twice: once by a stub (deterministic branch) and once by a real
    corrupt marker (git's own behaviour).
  - The build-level `_run` count (T3) is the NFR-1 call-budget proof.
  - Fixtures stay marked, with no confinement bypass.
- **Parity (`test_cli_mcp_parity.py`, T7/T14):** 13 shapes, every fixture AC-2.4
  names.
- **Doc (`test_readme.py`, T9/T15):** both notices are checked against real stderr,
  and the stale "stay the same" claim must be gone.
- **Regression (T16):** an old-code round-trip, not a double build (CLAUDE.md
  non-negotiable).
  - The non-shallow inputs must be byte-equal (AC-5.4).
  - The shallow inputs may only lose `inferred` edges (NFR-4).
  - The existing byte-identical double-build test stays.
- **Hands-on in `/peer-review` (no `/demo-day`; headless tool, see CLAUDE.md):**
  - Re-derive AC-5.6 and AC-1.5 on this repo (record SHA and counts).
  - NFR-2 under `sandbox-exec` network-deny, for the US-5 depth-1 and depth-3
    clones.
  - NFR-1 interleaved re-timing.
  - `uv run pytest` and `-m slow` both green.

  These steps stay manual because they need a real clone of this repo or OS-level
  network control.

## 5. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| R1: git < 2.15 echoes `--is-shallow-repository`, so a shallow clone reads `full`: no notice, no boundary exclusion (v0.7.1 inflation) | Low (2017 git; macOS ships 2.39) | Strict `== "true"` parse, documented in the docstring. Same as v0.7.1, never a crash |
| R2: a no-git test tmp dir inside an enclosing work tree reads `full` | False green/red | `GIT_CEILING_DIRECTORIES` plus an asserted precondition (T2–T4, T7, T14) |
| R3: the `build.py` reorder or the `log_records` hash field perturbs a non-shallow graph or the F1 logic | Breaks NFR-4/AC-5.4 | Empty `skip` returns today's records (T11). T12 exact sets. T16 old-code round-trip on 9 non-shallow inputs |
| R4: `git clone --depth N <plain path>` silently makes a full clone | Vacuous US-5 tests | `as_uri()`. T11 asserts the boundary set before any edge assertion |
| R5 (inherited A5/A6): blob-filter verified in round 1; `--filter=tree:0` may fetch during `git log` | Network access | `rev-parse` and the file read fetch nothing. tree:0 stays in the BACKLOG (§6) |
| R6 (inherited A3/A4): CI use assumed; any depth warns | Noise for deep clones | Accepted. With US-5 "may be missing" is now accurate |
| R7: PR #7 full-clone advice not on this branch | AC-3.1 placement | Unchanged: the subsection lives under "Linking code to stories". Tests check content |
| R8: `--git-path` prints a relative path for some layouts (subdir, worktree) | Shallow file not found → C12 drops *all* inferred edges, losing too much | `Path(root) / out` handles relative and absolute output. T11 asserts the subdir-of-shallow boundary equals the root's |
| R9: git's reaction to a corrupt shallow file is unverified: `rev-parse` may fail (→ `none`, no-git notice) or `log` may fail (→ 0 edges) | Notice may name "no git" for a corrupt shallow repo | C12 holds on every path (no edges, no raise). T13(b) asserts what git does rather than guessing. A7 already classes a corrupt `.git` as no git |
| R10: NFR-1 margin was thin (+3.2%, F2) | NFR-1 fail | The redundant `is_git_repo` in inference is removed (3 calls = v0.7.1). The file is read only when shallow. T16 re-times |
| R11: AC-5.6 needs a non-merge tip on this repo | A merge tip passes vacuously (`--no-merges`) | T16 records the tip SHA and checks `git rev-list --parents -n1` shows one parent |

---

## ✅ PLAN GATE

*All boxes checked → `/increment` may start. Any box open → back to `/sprint-plan`.*

- [x] Spec status is `approved` (never plan against a draft): re-approved 2026-10-03
- [x] Architecture decision includes rejected alternatives (a decision without alternatives is a guess)
- [x] Architecture respects the constitution's technical constraints (or a conflict is recorded): no constitution; CLAUDE.md non-negotiables applied
- [x] Every task maps to a user story — no orphan tasks, no story without tasks
- [x] Every Must AC and every applicable NFR is covered by at least one task
- [x] Every task has a checkable definition of done
- [x] Task order respects dependencies
- [x] Test strategy covers every Must story
- [x] Line budget respected: Ist ~260 / Soll ~300 (excluding HTML comments)
- [x] Status set to `approved` by the user (2026-10-03, revision after review F1/F2)

## Deviations

- **T8, v0.7.1 baseline taken from a detached worktree at `HEAD`, not `git stash`.**
  `HEAD` (`b215790`) is v0.7.1 code. The old code ran from that worktree via
  `PYTHONPATH`, the new code from the working tree, with no risk to uncommitted work.
  The comparison is the same one CLAUDE.md asks for. T16 reuses this method.
- **T7 and the T8 subdirectory input use a monorepo-shaped fixture.** The project
  lives in `proj/` with its own `.spark/`, because confinement refuses a bare `src/`
  subdirectory, which has no marker. This is still AC-4.4's case: the build path is
  a subdirectory of a full clone.

- **T16, v0.7.1 baseline from review round 1's `git archive` export of `b215790`,**
  not a new detached worktree. It is the same code.

## Increment record (for `/peer-review`)

- **T8 regression (round 1, 2026-10-03):** six inputs (shallow, full, no-git,
  subdir-of-full, `tests/fixtures/sample_repo` copied outside git, and a full clone of
  this repo) were each built once with v0.7.1 code and once with round-1 code.
  - Results: rc 0/0 every time, graph.json byte-equal 6/6, stdout equal 6/6, and
    stderr minus the notice equal 6/6.
  - The notice appeared exactly on shallow (shallow line), no-git and the copied
    sample_repo (no-git line).
  - Round 2 changes the shallow graph on purpose (US-5), so the shallow leg is
    superseded by T16.
- **NFR-1 timing (round 1, corrected per review F2):** the first record said "no
  measurable rise" (1.010 s → 0.937 s, runs not interleaved). That understated the
  cost.
  - The reviewer's interleaved re-measure (2 warm-ups, median of 5, `build . --full`
    on a full clone) gave v0.7.1 0.715 s against round 1 0.738 s, a rise of +3.2%.
  - One `history_state` call took 26.9 ms median over 21 runs.
  - NFR-1 holds, with a thin margin. T16 re-measures round 2.
- **Suite (round 1):** `pytest` 361 passed, `pytest -m slow` 3 passed. No linter is
  configured in this repo.
- **T16 regression (round 2, 2026-10-03):** v0.7.1 code was the `git archive` export
  of `b215790` that review round 1 left in the scratchpad (`v071/src`). New code was
  the working tree.
  - **Non-shallow, 9 inputs** (full, no-git, subdir-of-full, detached, single-branch,
    `sample_repo` outside git, full clone of this repo, US-5 full clone, AC-5.5
    root-commit repo): rc 0/0, graph.json byte-equal 9/9, stdout equal 9/9, stderr
    minus the notice equal 9/9 (AC-5.4, NFR-4).
  - **Shallow, 4 inputs:** nodes equal 4/4, no edge gained, and every lost edge is
    `inferred`. Lost: US-1 shallow 1, US-5 depth 1 3, US-5 depth 3 1, this repo at
    `--depth 1` 4716. stdout equal apart from the inferred-link count (AC-1.2).
  - **AC-5.6:** HEAD `19a5befe4f93fec4b6abea89d888841a63d7791b`, a non-merge commit (one
    parent, `b215790`). `impact src/aspark_graph/queries.py` gave 2 stories / 8 ACs
    on the depth-1 clone against 4 / 17 on the full clone, a subset. v0.7.1 gave
    40 / 181 on the same depth-1 clone (review F1).
- **NFR-1 timing (round 2):** 2 warm-ups, interleaved, median of 5 `build --full` on a
  full clone of this repo: v0.7.1 0.845 s, round 2 0.824 s (−2.4%). One `read_history`
  call took 33.5 ms median over 9 runs. A Task build makes 3 git calls, as v0.7.1 does
  (T3 asserts ≤ 3).
- **R9, observed:** with a non-hex line in `.git/shallow`, git 2.39's `rev-parse`
  fails, so the build reads `none`, prints the no-git notice, adds 0 inferred edges
  and exits 0 (T13, parity shape `boundary-corrupt-marker`).
- **Suite (round 2):** `pytest` 387 passed, `pytest -m slow` 3 passed.
