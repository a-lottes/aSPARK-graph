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
- **Summary:** One new never-raising helper `git.history_state()` makes one `git rev-parse --is-inside-work-tree --is-shallow-repository` call and returns `full`/`shallow`/`none`. `build.build_graph` calls it only when the graph has ≥1 Task node and stores the result on `BuildReport` (build output, never graph content). The CLI prints the one matching notice and MCP returns two booleans derived from that single field. `inference.py` and graph.json stay untouched.
- **Open:** `none`. All 9 tasks done; increment record and deviations at the end of this plan.
- **Binding ruling:** §3 Task Breakdown for current task status; a plan revision after review/QA findings updates §1/§3 in place, never a new section
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Architecture Decision

- **Context:** `inference.infer_implements` silently returns 0 edges when
  `git.is_git_repo` is false, and reads less history on a shallow clone (`git.py`
  docstring: "return less, never raise"). Nothing records *why*. The spec wants that
  condition in the build output only. It must be decided once in the shared layer
  (NFR-6), shown only when ≥1 plan task exists (C5), and add at most one local git
  call (NFR-1). Exit code, stdout and graph.json bytes must not change (C1, C4, NFR-4).
  The precedent is `BuildReport.shadowed`: a field filled during the build, printed
  by `cli._cmd_build` on stderr, and returned by `server.build_graph` as
  `ignored_legacy_files`. There is no `.spark/constitution.md`. The CLAUDE.md
  non-negotiables apply instead: determinism, thin adapters, clean errors, the
  `git stash` round-trip proof, and fixtures that are marked and never bypass
  confinement.
- **Decision:**
  1. `git.history_state(root) -> "full" | "shallow" | "none"` makes exactly one
     `_run(root, ["rev-parse", "--is-inside-work-tree", "--is-shallow-repository"])`
     call. A non-zero exit or a first line that is not `true` gives `none`. That
     covers a missing binary (A8), a non-repo, a ZIP and a corrupt `.git` (A7), and
     it is the same test `is_git_repo` uses, so `none` ⇔ inference was skipped. A
     second line of `true` gives `shallow`. Anything else gives `full`, including a
     subdirectory of a full clone (A7), a detached HEAD or a `--single-branch` clone
     (A5), and a zero-commit repo (§6, no notice). The helper never raises.
  2. `BuildReport.git_history: str | None = None`. `None` means "not checked, no Task
     node". Two read-only properties derive from it: `shallow_history` and
     `no_git_history`. Because both come from one field, they can never both be true
     (AC-2.4), and each is true exactly when its notice prints (A9).
  3. `BuildReport.history_notice() -> str | None` returns the AC-1.1 or the AC-4.1
     text, which are kept as module constants in `build.py`, or `None`.
  4. `build_graph` sets `git_history` after `infer_implements`, and only
     `if graph.nodes(NodeType.TASK)`. It runs on every build, full or incremental
     (AC-1.4).
  5. The adapters only render. `cli._cmd_build` prints the notice to stderr as its
     last stderr line, after the `Ignored …` lines, and leaves `summary()` and stdout
     untouched. `server.build_graph` adds `"shallow_history"` and `"no_git_history"`
     next to the six v0.7.1 keys.
- **Alternatives considered:**
  | Alternative | Why rejected |
  |---|---|
  | Have `infer_implements` report the state (change its return type, or detect inside it) | Couples an output signal to inference internals and puts F1 logic at risk. Inference returns early on "no ids", which is not the C5 gate (≥1 Task). `inferred_edges: int` is asserted by existing tests. |
  | Check for a `.git/shallow` file via `pathlib` | Wrong for a subdirectory build (A7). Wrong when `.git` is a file (worktree or submodule) and when `GIT_DIR` is set. |
  | `git rev-parse --git-path shallow` plus a Python `exists()` | Still one call and works on older git, but it depends on git's internal file layout. The documented porcelain flag `--is-shallow-repository` (git ≥ 2.15, 2017) states the fact directly. |
  | Two calls: reuse `is_git_repo` and add `rev-parse --is-shallow-repository` | Two git calls, which breaks NFR-1. |
  | Notice text in `cli.py`, as the `Ignored …` line is | Moves the boolean→text mapping (a small decision) into an adapter and gives the text two possible homes. A constant plus `history_notice()` in the shared layer keeps the CLI to one `print`. |
  | Persist a flag in graph.json, or add it to `impact`/`story_trace` | Ruled out by the spec (C4, §6). It would also break NFR-4. |
  | GitPython / dulwich | A new dependency for one `rev-parse`. The repo's pattern is offline `subprocess` git with no dependency. |
- **Consequences:** Easier: an agent can explain a thin `impact` answer from the
  `build_graph` response alone. The two keys cannot contradict each other by
  construction. A future history notice (zero commits, missing binary, both in the
  BACKLOG) is one more enum value. Harder: a build with ≥1 Task runs one more local
  subprocess. Both notice texts are now a frozen, user-approved contract (NFR-5), so
  any wording change needs a spec change. On git < 2.15 the flag is echoed rather
  than answered, so the build reads `full` and shows no shallow notice (R1).
  `tests/fixtures/sample_repo` sits inside this repo's work tree. When the suite runs
  from a shallow checkout or an sdist, building that fixture now prints a notice.
  No existing test asserts empty stderr (checked with grep), so this is expected
  behaviour, not a failure.

## 2. Affected Components

Scoped by hand from reading the code: `git.py`, `inference.py`, `build.py`, `cli.py`,
`server.py`, `confinement.py`, `tests/conftest.py`, `tests/test_git.py`,
`tests/test_cli_mcp_parity.py`, `tests/test_readme.py`, `README.md`.

aspark-graph blast radius: the graph was stale on 2026-10-03 (`staleness`: 7 changed files), so it was treated as absent and the scope above was set by hand; no graph result is cited.

| Component | Change |
|---|---|
| `src/aspark_graph/git.py` | + `history_state()`; docstring names it among the never-raise helpers |
| `src/aspark_graph/build.py` | + two notice constants, `BuildReport.git_history` + 2 properties + `history_notice()`, one gated call in `build_graph` |
| `src/aspark_graph/cli.py` | + one stderr `print` in `_cmd_build` |
| `src/aspark_graph/server.py` | + two keys in `build_graph`'s dict |
| `src/aspark_graph/inference.py`, `graph.py`, `artifacts.py` | **unchanged, deliberately** (NFR-4) |
| `README.md` | + short subsection under "Linking code to stories" (US-3) |
| `tests/` | new `test_history_notice.py`; extend `conftest.py`, `test_git.py`, `test_cli_mcp_parity.py`, `test_readme.py` |

New dependencies, services and patterns: **none**. `history_state` follows the
existing `git.py` `_run` pattern, and the report fields follow `BuildReport.shadowed`.

## 3. Task Breakdown

| # | Task | Story | Covers (AC / NFR) | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|---|
| T1 | **Walking skeleton.** Add `git.history_state`, the `BuildReport` field, properties, `history_notice()` and constants, the gated call in `build_graph`, the CLI `print` and the two MCP keys. Add conftest helpers `make_trail(root)` (spec + plan with ≥1 task) and `shallow_clone(src, dst)` (`git clone --depth 1 <src.as_uri()>`; a plain path would silently ignore `--depth`). | US-1, US-2 | AC-1.1, AC-2.1, NFR-6 | – | `done` | A test builds a ≥2-commit source repo whose task id is in a commit message, clones it with `--depth 1`, and runs `cli.main(["build", clone])`: rc is 0 and stderr contains the AC-1.1 line exactly once (`err.splitlines().count(...) == 1`). `server.build_graph(path=clone)` returns `shallow_history is True` and `no_git_history is False`. Full suite green — files: src/aspark_graph/git.py, src/aspark_graph/build.py, src/aspark_graph/cli.py, src/aspark_graph/server.py, tests/conftest.py, tests/test_history_notice.py |
| T2 | `history_state` unit matrix and call budget | US-1, US-4 | AC-1.6, AC-4.4, NFR-1, NFR-2, NFR-4 | T1 | `done` | Tests assert: full repo→`full`; shallow clone→`shallow`; subdir of full→`full`; subdir of shallow→`shallow`; plain dir→`none`; corrupt `.git`→`none`; `PATH=""` (no git binary)→`none`, no exception; detached HEAD→`full`; `--single-branch` full-depth→`full`; zero-commit repo→`full`. Non-git cases set `GIT_CEILING_DIRECTORIES` to `tmp_path` and assert the non-git precondition first. A `_run` spy proves exactly 1 call per `history_state` and that its argv has no remote or URL-related command — files: tests/test_git.py |
| T3 | Task gate (C5/A9): no Task node → no check, no notice, keys false | US-1, US-2, US-4 | AC-1.7, AC-2.3, AC-4.3, NFR-1 | T1 | `done` | On a shallow clone and on a no-git dir, each with a spec but no plan task: `report.git_history is None`, the `history_state` spy shows 0 calls, CLI stderr contains neither notice, and MCP returns both keys `False`. With a task, the spy shows exactly 1 call per `build_graph` — files: tests/test_history_notice.py |
| T4 | No-git notice end-to-end (US-4) | US-4 | AC-4.1, AC-4.2 | T1 | `done` | No-git fixture (`.spark/`-marked, ≥1 task, ceiling env set, precondition asserted): CLI rc is 0 and stderr contains the AC-4.1 line exactly once and no shallow line. MCP on an identical copy returns `no_git_history is True` and `shallow_history is False`. Both graph.json files are byte-equal — files: tests/test_history_notice.py |
| T5 | CLI output contract: stdout, full-clone stderr, `--full` and incremental | US-1 | AC-1.2, AC-1.3, AC-1.4, NFR-3, NFR-5 | T1 | `done` | Shallow fixture: stdout is exactly 2 lines (`Built graph: …`, `Saved to …`) and contains no notice text. A full clone of the same source gives empty stderr. On the shallow clone, a first build, then a `--full` build, then an incremental build (graph present) each print the notice exactly once. Each notice contains no `\x1b` and no path separator — files: tests/test_history_notice.py |
| T6 | Remedy round-trip and no-notice clone shapes, at build level | US-1 | AC-1.5, AC-1.6 | T1 | `done` | Test: shallow clone → notice. `git fetch --unshallow` from the `file://` origin (offline) → rebuild → no notice, and `queries.impact(graph, [<task file>])` equals the full clone's result at the same HEAD (stories, ACs, confidences). A detached-HEAD build and a `--single-branch` full-depth build print no notice. The real-repo evidence (this repo, `--depth 1` → unshallow; HEAD SHA plus story and AC counts for `impact src/aspark_graph/queries.py`) is produced hands-on in `/peer-review` and recorded there — files: tests/test_history_notice.py |
| T7 | CLI≡MCP parity across every US-1/US-4 fixture | US-2 | AC-2.2, AC-2.4, AC-4.4, NFR-6 | T2, T3, T4 | `done` | Parametrised test over {shallow, full, shallow-no-task, no-git, no-git-no-task, subdir-of-full, subdir-of-shallow, detached, single-branch}, with CLI on copy a and MCP on copy b. Asserts: shallow line printed ⇔ `shallow_history`, no-git line printed ⇔ `no_git_history`, never both true, graph.json bytes equal. The MCP key set equals the six v0.7.1 keys plus the two new ones, and on the full clone both new keys are `False` — files: tests/test_cli_mcp_parity.py |
| T8 | v0.7.1 regression sweep: `git stash` round-trip and timing (no code change) | US-1, US-2 | AC-1.2, AC-1.3, NFR-1, NFR-4 | T5, T6, T7 | `done` | Build the shallow, full, no-git, subdir-of-full, `tests/fixtures/sample_repo` and this-repo inputs once under stashed (v0.7.1) code and once under the new code. Result: 0 graph.json byte diffs, identical stdout, and identical stderr except the expected notice lines. Median of 5 builds of this repo, before vs after, shows a rise of < 5%. The commands, SHAs and numbers are recorded in the `/increment` hand-off for `/peer-review` |
| T9 | README documents both notices (US-3) | US-3 | AC-3.1 | T1 | `done` | README gains a short subsection under "Linking code to stories" (or next to the full-clone advice, if PR #7 has landed on this branch) that quotes both notices verbatim and names `shallow_history`, `no_git_history` and `git fetch --unshallow`. A test runs the CLI on the shallow and no-git fixtures and asserts each captured notice line is a substring of README.md — files: README.md, tests/test_readme.py |

## 4. Test Strategy

- **Unit (`test_git.py`, T2):** `history_state` across all ten repo shapes, including
  a missing binary and a corrupt `.git`. A `_run` spy proves the one-call budget. The
  module stays in the "never raises" tradition: no shape may raise.
- **Integration (`test_history_notice.py`, T1/T3–T6):** real `git` in `tmp_path`.
  Shallow clones use `file://` URIs. Fixed dates come from the `conftest.git_commit`
  helper. No-git fixtures set `GIT_CEILING_DIRECTORIES` and assert the precondition,
  so a host `tmp` inside a work tree cannot fake a pass. Fixtures stay `.spark/` or
  `.git` marked, with no confinement bypass (`test_confinement_guards.py` stays green).
  No new test depends on the host checkout's own git state.
- **Parity (`test_cli_mcp_parity.py`, T7):** one parametrised table, following the
  confinement and `ignored_legacy_files` precedent, over every fixture named in AC-2.4.
- **Doc (`test_readme.py`, T9):** the README is checked against *real* stderr, not
  against the constants, as AC-3.1 asks.
- **Regression (T8):** a `git stash` round-trip against v0.7.1 code (CLAUDE.md
  non-negotiable), not just a double build. The existing byte-identical double-build
  test stays.
- **Hands-on in `/peer-review` (no `/demo-day`; headless tool, see CLAUDE.md):**
  - AC-1.5 on this repo (success signal 2; record SHA and counts).
  - A5 blob-filter clone gives no notice.
  - NFR-2: the shallow fixture builds with the network disabled.
  - NFR-1 timing re-run.
  - `uv run pytest` and `-m slow` both green.

  These steps stay manual because they need a real remote-shaped clone of this repo
  or OS-level network control, which the unit suite should not script.

## 5. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| R1: git < 2.15 echoes `--is-shallow-repository` instead of answering, so a shallow clone reads `full` and shows no notice | Low (git 2.15 is from 2017; macOS ships 2.39) | Parse strictly (`== "true"`). Document in `history_state`'s docstring. The silent failure is the same as v0.7.1, never a crash |
| R2: a test tmp dir inside an enclosing work tree makes a "no-git" fixture read `full` | False green or red in CI | `GIT_CEILING_DIRECTORIES` plus an asserted precondition in every no-git test (T2–T4, T7) |
| R3: graph.json or stdout drift from the edit to `build.py` | Breaks C4 / NFR-4 / AC-1.2 | Nothing is written to `graph`, and `summary()` is untouched. T8 stash round-trip on 6 inputs |
| R4: `git clone --depth 1 <plain path>` silently makes a full clone | Shallow tests pass vacuously | The helper uses `Path.as_uri()`. T2 asserts the clone reads `shallow` before any notice assertion |
| R5 (inherited A5/A6): blob-filter clone unverified; `--filter=tree:0` may fetch over the network during inference | Wrong notice / network access | `rev-parse` itself fetches nothing. Blob-filter check is hands-on in `/peer-review`. tree:0 stays in the BACKLOG (§6) |
| R6 (inherited A3/A4): CI use is assumed; any shallow depth warns | Possible noise for deep clones | Accepted in the spec. The wording says "may be missing" |
| R7: US-3 says "next to the full-clone advice (PR #7)", but this branch's README has no such passage | AC-3.1 placement ambiguous | T9 places the subsection under "Linking code to stories". If PR #7 lands first, move it next to that advice. The AC-3.1 test checks content, not position |

---

## ✅ PLAN GATE

*All boxes checked → `/increment` may start. Any box open → back to `/sprint-plan`.*

- [x] Spec status is `approved` (never plan against a draft)
- [x] Architecture decision includes rejected alternatives (a decision without alternatives is a guess)
- [x] Architecture respects the constitution's technical constraints (or a conflict is recorded): no constitution; CLAUDE.md non-negotiables applied
- [x] Every task maps to a user story — no orphan tasks, no story without tasks
- [x] Every Must AC and every applicable NFR is covered by at least one task
- [x] Every task has a checkable definition of done
- [x] Task order respects dependencies
- [x] Test strategy covers every Must story
- [x] Line budget respected: Ist ~175 / Soll ~300 (excluding HTML comments)
- [x] Status set to `approved` by the user (2026-10-03)

## Deviations

- **T8, v0.7.1 baseline taken from a detached worktree at `HEAD`, not `git stash`.**
  `HEAD` (`b215790`) is v0.7.1 code. The old code ran from that worktree via
  `PYTHONPATH`, the new code from the working tree, with no risk to uncommitted work.
  The comparison is the same one CLAUDE.md asks for.
- **T7 and the T8 subdirectory input use a monorepo-shaped fixture.** The project
  lives in `proj/` with its own `.spark/`, because confinement refuses a bare `src/`
  subdirectory, which has no marker. This is still AC-4.4's case: the build path is
  a subdirectory of a full clone.

## Increment record (for `/peer-review`)

- **T8 regression, 2026-10-03:** six inputs (shallow, full, no-git, subdir-of-full,
  `tests/fixtures/sample_repo` copied outside git, and a full clone of this repo) were
  each built once with v0.7.1 code and once with the new code.
  - Results: rc 0/0 every time, graph.json byte-equal 6/6, stdout equal 6/6, and
    stderr minus the notice equal 6/6.
  - The notice appeared exactly on shallow (shallow line), no-git and the copied
    sample_repo (no-git line).
- **NFR-1 timing:** median of 5 `build --full` runs of a full clone of this repo.
  - v0.7.1 measured 1.010 s (0.838–1.072) and the new code 0.937 s (0.892–1.025).
  - No measurable rise; the difference is within noise.
- **Suite:** `pytest` 361 passed, `pytest -m slow` 3 passed. No linter is configured
  in this repo.
- **Still hands-on in `/peer-review`, per §4:**
  - AC-1.5 on this repo (`--depth 1` → unshallow; HEAD SHA plus story and AC counts)
  - A5 blob-filter clone
  - NFR-2 with the network off
