# Review Report: shallow-clone-warning

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | `git diff b215790..19a5bef`, `.spark/shallow-clone-warning/plan.md` |
| **Status** | `changes-requested` |
| **Round** | 1 |
| **Date** | 2026-10-03 |

<!-- Handoff: read this block first, the numbered sections below by exception. Whoever
     writes to this report — including `/increment` in fix-mode, which is not this
     report's owner — updates it in the same edit that closes or re-rules a finding:
     overwrite in place, never append. The block holds one current state, never a
     per-round log; a stale block is a defect, not a cosmetic issue.

     Re-review: bump `Round` yourself (only the owner bumps it, never `/increment`) at
     the start of the pass, then overwrite every section below in place — §1 Scope, §2
     Plan Conformance, §3 Findings, §4 Traceability, §6 Verdict and the gate checklist
     all hold exactly one current state, never a `## Round N` heading or a second gate.
     History lives in git, not in this file. -->

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Verdict:** Code is correct against every AC and NFR; one Major (F1) needs a user decision because the approved notice wording is wrong for a common shallow-clone shape.
- **Open:** `0 open` — F1 fixed in round 2 via spec US-5/C11/C12 and plan T10–T16; F2 fixed in the plan's Increment record; F3 fixed by the reviewer. Ready for re-review.
- **Binding ruling:** §6 Verdict and the gate checklist below — the only binding location; there is no other round to point to
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Scope

- Reviewed: `b215790..19a5bef` (one commit, 12 files): `src/aspark_graph/{git,build,cli,server}.py`, `README.md`, `tests/{conftest,test_git,test_history_notice,test_cli_mcp_parity,test_readme}.py`, plus `inference.py`/`git.py::log_records` for context (F1).
- aspark-graph tool: CLI runner present, `graph.json` present, `query staleness` returned `stale: true` (10 changed files). Per the tool file's stale rule the graph was treated as absent; no graph result is cited. Scoped by hand from the diff.
- Not reviewed: `.spark/` spec/plan wording beyond conformance (spec is approved; not changed).

## 2. Plan Conformance

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 | ✅ | `git.history_state` (git.py:42), `BuildReport.git_history` + properties + `history_notice()` (build.py:69-86), gated call (build.py:183-184), CLI print (cli.py:178-180), MCP keys (server.py:37-38), conftest helpers. |
| T2 | ✅ | 11 tests in `test_git.py` cover all ten shapes plus the 1-call spy. |
| T3 | ✅ | Gate tests incl. spy = 0 / = 1 calls. Mutation probe (gate removed) fails 4 tests. |
| T4 | ✅ | |
| T5 | ✅ | NFR-3 check asserts on the constants rather than captured stderr; equivalent because the CLI prints the constant. |
| T6 | ✅ | Real-repo leg done hands-on here (§5). |
| T7 | ✅ | Documented deviation: monorepo-shaped subdir fixture (confinement refuses a bare `src/`). Accepted: still AC-4.4's case. |
| T8 | ✅ | Documented deviation: v0.7.1 baseline from a detached worktree instead of `git stash`. Accepted: same old-vs-new comparison, safer. Reviewer re-ran 3 inputs independently (§5). |
| T9 | ✅ | Placed under "Linking code to stories"; PR #7 not on `origin/main` (R7). |

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Major | `build.py:38-41`, `README.md:238-239` (root cause `git.py:77`, unchanged) | On a shallow clone whose tip is a **non-merge** commit, the grafted root commit lists every tracked file as touched, so inference *adds* spurious links rather than losing them. This repo at `19a5bef`, `--depth 1`: 4716 inferred edges vs 132 on a full clone; `impact src/aspark_graph/queries.py` = **40 stories / 181 ACs** vs 4 / 17 (v0.7.1 code gives the same 40/181, so it is pre-existing). The approved notice ("inferred links may be missing") and README ("has only part of it") tell the user the answer is too small when it is ~10x too large. The spec's evidence (2/8) only holds when the tip is a merge commit (`--no-merges` drops it). Why it matters: the feature exists to make a degraded answer honest, and squash-merge or direct-push tips are common. The remedy in the notice is correct and works. Fix needs the user, because it touches C9 (frozen wording) or NFR-4 (byte-identical shallow graph): (a) amend the wording, e.g. "inferred links may be missing or wrong", or (b) make inference skip shallow boundary commits (changes the shallow graph.json vs v0.7.1), or (c) waive and BACKLOG it. | fixed |
| F2 | Minor | `plan.md` Increment record, "NFR-1 timing" | The record says "no measurable rise; within noise" (1.010 s → 0.937 s). Reviewer, interleaved runs on the same full clone: 0.715 s → 0.738 s median (+3.2%). `history_state` alone takes 26.9 ms median (21 runs), about 3.8% of a build. NFR-1 still holds (< 5%), but the margin is thin and the record understates it. Fix: replace the line with the measured per-call cost. Artifact wording only, so capped at Minor. | fixed |
| F3 | Nit | `git.py:5` | The module docstring line ran to about 105 columns after the edit, out of step with the rest of the file. Re-wrapped by the reviewer, a docstring-only change; suite re-run green. | fixed |

## 4. Requirements Traceability

| Spec ID | Implemented at | Verdict |
|---|---|---|
| AC-1.1 | `build.py:38-41,79-86`, `cli.py:178-180`; test `test_history_notice.py:29` | ✅ met (exact line, once; also hands-on) |
| AC-1.2 | `cli.py:181-184` unchanged; `test_history_notice.py:121` | ✅ met (stdout equal to v0.7.1 on shallow clone of this repo, hands-on) |
| AC-1.3 | gate in `git.py:42-59` → `full`; `test_history_notice.py:131` | ✅ met (stderr 0 bytes, v0.7.1 and new) |
| AC-1.4 | `build.py:183` runs on every build path; `test_history_notice.py:138` | ✅ met (hands-on: full then incremental both print it) |
| AC-1.5 | `test_history_notice.py:155` + hands-on §5 | ✅ met (re-derived: Must AC verification) |
| AC-1.6 | `git.py:42-59`; `test_git.py` detached/single-branch; `test_history_notice.py:174` | ✅ met |
| AC-1.7 | `build.py:183` gate; `test_history_notice.py:75` | ✅ met |
| AC-2.1 | `server.py:37-38`; `test_history_notice.py:39-41` | ✅ met |
| AC-2.2 | `server.py:31-38`; parity key-set assert | ✅ met |
| AC-2.3 | `build.py:183`, `test_history_notice.py:88-90` | ✅ met |
| AC-2.4 | single field → two properties `build.py:69-77`; 9-shape parity test | ✅ met |
| AC-3.1 | `README.md:236-252`; `test_readme.py` vs real stderr | ✅ met (content wording: see F1) |
| AC-4.1–4.4 | `git.py:42-59`, `build.py:183`; `test_history_notice.py:103`, parity subdir shapes | ✅ met |
| NFR-1 | one `rev-parse` call, `git.py:53`; spy tests | ✅ met (+3.2%, see F2) |
| NFR-2 | constants contain no path/URL; booleans only; `rev-parse` is local | ✅ met (no-network sandbox, §5) |
| NFR-3 | plain constants, no ANSI | ✅ met |
| NFR-4 | nothing written to `graph`; `summary()` untouched | ✅ met (v0.7.1 vs new byte-equal on shallow, full, no-git, hands-on) |
| NFR-5 | stderr only, at most one notice by construction | ✅ met |
| NFR-6 | decision in `build.py`/`git.py`; adapters render only | ✅ met |

## 5. What Was Checked

- [x] Correctness: logic does what the acceptance criteria demand, except the notice's accuracy on non-merge shallow tips (F1)
- [x] Non-functional: NFR-1–6 hold; CLAUDE.md non-negotiables (determinism, thin adapters, no confinement bypass, old-code round-trip) respected
- [x] Error handling: `history_state` never raises (`_run` catches OSError/ValueError; non-zero → `none`)
- [x] Security: no input reaches a shell; fixed argv; no URL/path in output
- [x] Tests: 361 passed, `-m slow` 3 passed (before and after F3). A mutation probe that removes the task gate fails 4 tests.
- [x] Readability: small, commented, follows the `shadowed` precedent

Hands-on evidence (scratch dirs under `/private/tmp/claude-501/…/scratchpad/`, code from this branch's `.venv`):
- **AC-1.5:** HEAD `19a5befe4f93fec4b6abea89d888841a63d7791b`. `--depth 1` file:// clone: 1 commit, the shallow notice printed, rc 0. `impact src/aspark_graph/queries.py` gave 40 stories / 181 ACs (F1). Then `git fetch --unshallow` (51 commits) and a rebuild: no notice, and 4 stories / 17 ACs. The full clone at the same HEAD also gives 4 / 17. The stories, ACs and tiers are equal, the impact JSON is identical and graph.json is byte-identical to the full clone's.
- **A5:** `--filter=blob:none` clone (uploadpack.allowFilter on), 51 commits, 128 blobs missing. The remote URL was then pointed at a non-existent path. Build: rc 0, no notice, graph.json byte-identical to the full clone, and still 128 blobs missing afterwards (nothing was lazily fetched).
- **NFR-2:** real isolation via `sandbox-exec -p '(version 1)(allow default)(deny network*)'`. Control: curl works outside the sandbox (200) and fails inside it (rc 6 by name, rc 7 by IP). Inside the sandbox, a shallow clone of this repo (origin set to the GitHub https URL) built with rc 0 and the notice on both the full and the incremental build. `test_history_notice.py` + `test_git.py` also ran inside it: 32 passed.
- **NFR-1:** median of 5 measured runs (after 2 warm-up rounds, interleaved), `build . --full` on a full clone: v0.7.1 0.715 s, new 0.738 s (+3.2%). One `history_state` call: 26.9 ms.
- **NFR-4 re-check** (old code from `git archive b215790`): graph.json is byte-equal on the shallow clone, the full clone and `tests/fixtures/sample_repo` copied outside git. On the full clone stdout and stderr are equal too. On no-git, stdout is equal and the only stderr difference is the new no-git line.

## 6. Verdict

The increment does what the plan says, with two deviations that are documented and sound. Every Must AC and every NFR traces to code and a test that fails when the gate is broken, and the suite is green. I reproduced the hands-on checks the plan assigned to this review: AC-1.5 on this repo, the A5 blob-filter case, NFR-2 under a real network-deny sandbox and NFR-1 timing. One honest problem remains. On a shallow clone whose tip is not a merge commit, which is exactly this repo at `19a5bef`, the build inflates `impact` tenfold (40/181 vs 4/17), yet the approved notice says links "may be missing". The tool now speaks up, but it misnames the direction of the error. That is F1, a Major. It cannot be fixed in code without breaking frozen spec decisions (C9 wording, NFR-4 bytes), so it goes to the user: amend the wording, change inference, or waive with a BACKLOG item and a recorded reason. Until then the status is `changes-requested`. Nothing else stands between this increment and `passed`. F2 (Minor) is a one-line correction to the increment record.

---

## ✅ REVIEW GATE

*All boxes checked → `/demo-day` may start. Any box open → back to `/increment`. On
re-review, edit this same checklist in place — never duplicate it as a second gate.*

- [x] No open Blocker findings
- [ ] No open Major findings (or explicitly waived by the user, with reason recorded here): F1 open, needs a user decision
- [x] Every Must AC traces to implementing code; no constitution non-negotiable violated (no constitution; CLAUDE.md non-negotiables checked)
- [x] All plan deviations documented and accepted (T7 fixture shape, T8 worktree baseline)
- [x] Test suite runs green (361 passed, slow 3 passed, after reviewer fix F3)
- [x] Line budget respected: Ist ~105 / Soll ~150 (excluding HTML comments)
- [ ] Status set to `passed`
