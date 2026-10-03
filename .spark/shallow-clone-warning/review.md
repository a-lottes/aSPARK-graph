# Review Report: shallow-clone-warning

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | `git diff b215790..c83517a` (round 2 delta `19a5bef..c83517a`), `.spark/shallow-clone-warning/plan.md` |
| **Status** | `passed` |
| **Round** | 2 |
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
- **Verdict:** Passed. F1 is fixed. A shallow build now only loses inferred links. That holds on this repo (2/8 ⊆ 4/17 at `c83517a`) and in 9/9 non-shallow byte-identity checks against v0.7.1.
- **Open:** `none`. F6 and F7 (artifact sync) fixed by `/increment` after round 2: plan Deviations line, spec §1 and plan §1/R11 wording.
- **Binding ruling:** §6 Verdict and the gate checklist below — the only binding location; there is no other round to point to
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Scope

- Reviewed: round-2 delta `19a5bef..c83517a`: `src/aspark_graph/{git,inference,build}.py`, `README.md`, `tests/{conftest,test_git,test_shallow_boundary,test_history_notice,test_cli_mcp_parity,test_readme}.py`, and the plan's Deviations and Increment record. I re-checked the round-1 code only where round 2 touches it (`build_graph` order, the T3 spy).
- aspark-graph tool: the graph is still stale, so it was treated as absent and no graph result is cited. Scoped by hand from the diff.
- Re-derived rather than cited: T16 sweep, AC-5.6, NFR-1 timing (condition (a): verifying the F1/F2 fixes; (b): AC-5.6 is a Must). NFR-2 was re-run on the US-5 clones, as the plan assigns.
- Not reviewed: spec wording beyond F7 (approved, not changed).

## 2. Plan Conformance

| Task | Implemented as planned? | Note |
|---|---|---|
| T1, T2, T4–T9 | ✅ | Round 1, unchanged. T2's matrix is unedited and green through the `history_state` wrapper (`git.py:92-98`). T8's shallow leg is superseded by T16, as planned. |
| T3 | ✅ | Spy retargeted to `read_history`. New `_run` budget test (`test_history_notice.py:114`): Task build ≤ 3 calls, no-Task build 0. |
| T10 | ⚠️ | §1 Decisions 1–4 match the code (`git.py:46-89,101-135`, `inference.py:53-59,76`, `build.py:184-187`). The fixture shape differs from §3's description: F6. |
| T11 | ✅ | `test_git.py:199-277`. The R8 subdir assertion was vacuous (F5, fixed). |
| T12 | ✅ | AC-5.3 pinned as an exact set. AC-5.5 root commit. Depth 1 and 3 deterministic. |
| T13 | ✅ | (a) stubbed `None`, (b) real corrupt marker, R9 asserted as observed. |
| T14 | ✅ | 13 shapes; `boundary-corrupt-marker` asserts only ⇔ and never-both. |
| T15 | ✅ | `README.md:247-253`; the stale phrase is gone, guarded by a test. |
| T16 | ✅ | Documented deviation: v0.7.1 baseline from the `git archive` export. Accepted, same code. Re-run by the reviewer (§5). |

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Major | `git.py:62-89,131-132`, `inference.py:56-59,76`, `build.py:184-187` | A non-merge shallow tip used to inflate `impact` (40/181 vs 4/17) while the notice said "may be missing". The user chose (b). Verified: the boundary comes from `--git-path shallow` in the same single `rev-parse` call, and `log_records(skip=)` drops those commits. This repo at `c83517a`, `--depth 1`: v0.7.1 1470 inferred / 19 stories / 101 ACs; new 0 / 2 / 8; full clone 187 / 4 / 17. | fixed r2 |
| F2 | Minor | `plan.md` Increment record, "NFR-1 timing" | The record understated the round-1 cost. It now carries the interleaved +3.2% and the 26.9 ms per call. | fixed r2 |
| F3 | Nit | `git.py:5` | Over-long docstring line, re-wrapped by the reviewer in round 1. | fixed r2 |
| F4 | Minor | this report, Handoff block (as left by fix-mode) | The Handoff `Open` said `0 open`, but the gate checkbox still said "F1 open", and the Handoff `Verdict` was still round 1's. Its vocabulary was also not the template's (`none` / `<n> open`). Overwritten in this round. | fixed r2 |
| F5 | Minor | `tests/test_git.py:229-232` | The R8 test compared subdir vs root boundary only, so `None == None` passed. A mutation that resolves `--git-path` against the process cwd left it green. Reviewer fix: also assert `== {HEAD~2}`. That mutation now fails the test. | fixed r2 |
| F6 | Minor | `tests/conftest.py:158-177` vs `plan.md` §3 fixture | Undocumented deviation. The plan's c1 adds `a/b/c.py` and its c2 touches `a.py`. The fixture's c1 adds only the trail, c2 adds `b.py`, c4 adds `c.py` and c5 adds `a.py`. It still meets every spec condition (≥5 commits, ≥3 files, single-file non-merge T1 tip; c3 alone gives T2→b.py), so the reviewer accepts it. Why it matters: the plan describes a fixture that doesn't exist. Fix: one Deviations line in `plan.md` (`/increment`). | fixed |
| F7 | Nit | `spec.md` §1 Problem, `plan.md` §1 alternative 1 | Both say the 2026-09-29 merge tip was safe because `--no-merges` skips it. Observed: a grafted merge (`b215790`, `--depth 1`) shows no parents. `--no-merges` keeps it, with all 132 files. `log_records` 1 record → 0 with `skip`, so the fix covers it. The 2/8 then was probably due to its message ("Merge pull request #6") naming no task id. Fix: the PO/EM correct the sentence at their next edit. No code change. | fixed |
| F8 | Nit | `build.py:66` | The comment still named `git.history_state()`, which `build_graph` no longer calls. Reviewer fix: `git.read_history().state`. | fixed r2 |

## 4. Requirements Traceability

| Spec ID | Implemented at | Verdict |
|---|---|---|
| AC-1.1 | `build.py:38-41,79-86`, `cli.py:178-180`; test `test_history_notice.py:29` | ✅ met (exact line, once; also hands-on) |
| AC-1.2 | `cli.py:181-184` unchanged; T16 stdout equal except the inferred count | ✅ met (amended AC; 4/4 shallow inputs) r2 |
| AC-1.3 | gate in `git.py:62-89` → `full`; `test_history_notice.py` | ✅ met (stderr 0 bytes, v0.7.1 and new) |
| AC-1.4 | `build.py:184` runs on every build path | ✅ met (hands-on: full then incremental both print it) |
| AC-1.5 | `test_history_notice.py` + hands-on §5 | ✅ met (re-derived: Must AC verification) |
| AC-1.6 | `git.py:62-89`; `test_git.py` detached/single-branch | ✅ met |
| AC-1.7 | `build.py:184` gate; `test_history_notice.py` | ✅ met |
| AC-2.1–2.3 | `server.py:37-38`, `build.py:184-186` | ✅ met |
| AC-2.4 | `test_cli_mcp_parity.py:265-298` (13 shapes) | ✅ met (US-5 shapes added) r2 |
| AC-3.1 | `README.md:236-253`; `test_readme.py:112` | ✅ met (wording now accurate) r2 |
| AC-4.1–4.4 | `git.py:62-89`, `build.py:184` | ✅ met |
| AC-5.1 | `git.py:131-132`, `inference.py:76`; `test_shallow_boundary.py:25` | ✅ met (mutation M1: 4 tests fail) r2 |
| AC-5.2 | `test_shallow_boundary.py:65` | ✅ met r2 |
| AC-5.3 | `test_shallow_boundary.py:75` (exact set) | ✅ met r2 |
| AC-5.4 | empty `skip` = old records; T16 9/9 byte-equal | ✅ met (reviewer re-run) r2 |
| AC-5.5 | `test_shallow_boundary.py:86`; T16 root-commit input | ✅ met r2 |
| AC-5.6 | hands-on §5 | ✅ met (`c83517a`, 2/8 ⊆ 4/17) r2 |
| NFR-1 | 3 git calls per Task build (= v0.7.1), 0 without Task | ✅ met (+0.7%, read_history 26.7 ms) r2 |
| NFR-2 | `rev-parse` + local file read; constants without path/URL | ✅ met (sandbox, US-5 depth 1/3) r2 |
| NFR-3 | plain constants, no ANSI | ✅ met |
| NFR-4 | non-shallow byte-equal; shallow loses inferred only; C12 → 0 edges | ✅ met (amended NFR) r2 |
| NFR-5 | stderr only, at most one notice by construction | ✅ met |
| NFR-6 | decision in `git.py`/`inference.py`/`build.py`; adapters unchanged | ✅ met |

## 5. What Was Checked

- [x] Correctness: boundary read via `--git-path shallow`. Probed hands-on: root `.git/shallow`, subdir `../.git/shallow` (resolved against `root`, as `git -C` does), linked worktree (absolute path), and a worktree subdir. All give the right set.
- [x] Non-functional: NFR-1–6 hold. CLAUDE.md non-negotiables respected: determinism (`%H` is read for filtering only and never emitted), thin adapters, old-code round-trip, marked fixtures.
- [x] Error handling, C12 against real git 2.39. An empty file or an uppercase file gives `None` and 0 edges. A well-formed but wrong SHA reads as shallow, `git log` fails (rc 128) and the build adds 0 edges. A non-hex line makes `rev-parse` fail, so the build reads `none` and adds 0 edges. CRLF parses correctly. Never raises.
- [x] Security: fixed argv, no shell. Only a git-owned file is read, never written.
- [x] Tests: 387 passed and `-m slow` 3 passed, before and after the reviewer fixes. Mutations: M1 (skip filter off) 4 tests fail; M2 (C12 return off in inference) 1 fails; M3 (path not joined to root) 3 fail, 4 after F5; M4 (malformed graft list accepted) 3 fail. Everything was restored and `git diff` is clean apart from F5 and F8.
- [x] Readability: small, commented, and the record shape is unchanged.

**R9 ruling, no finding.** A non-hex graft line makes git's own `rev-parse` fail with "fatal: bad shallow line", and `git log` dies the same way. Inference therefore really has no readable history. The no-git notice is true in substance ("inferred links are missing"), and its remedy, a full clone, works. A7/C10 already class a corrupt `.git` as no git, and this state only arises from hand-editing `.git`. It is acceptable.

Hands-on evidence (scratch dirs under `…/scratchpad/r2/`, branch `.venv`):
- **T16 re-run** (`t16.py`, v0.7.1 = `v071/src`):
  - Non-shallow, 9 inputs: rc 0/0, bytes, stdout and stderr-minus-notice all equal 9/9.
  - Shallow: nodes equal and 0 edges gained. Every lost edge is inferred: US-1 shallow 1, US-5 depth 1 3, depth 3 1, this repo 1470.
- **AC-5.6 / AC-1.5:**
  - HEAD `c83517a61a074b7acf1cb3ed40ffcc5f0f7bccd0`, one parent (`19a5bef`), so a non-merge tip.
  - `--depth 1`: the notice is printed and `impact src/aspark_graph/queries.py` gives 2 stories / 8 ACs. That is a subset of the full clone's 4 / 17 (set check, both levels).
  - v0.7.1 on the same clone: 19 / 101.
  - `git fetch --unshallow`, then an incremental rebuild: no notice, 4 / 17, and graph.json byte-equal to the full clone's.
- **NFR-2:** `sandbox-exec '(deny network*)'`. Control: curl gives 200 outside the sandbox and rc 6 inside it. The US-5 depth-1 and depth-3 clones, with origin set to an https URL, build with rc 0 and the notice on both full and incremental builds (inferred 0 and 2). `test_shallow_boundary.py` + `test_git.py` inside the sandbox: 40 passed.
- **NFR-1:** 2 warm-ups, interleaved, median of 5 `build --full` runs on a full clone: v0.7.1 0.684 s, new 0.689 s (+0.7%). One `read_history`: 26.7 ms. Consistent with the record (−2.4%): both are noise around zero, as expected with 3 git calls before and after.

## 6. Verdict

F1 is genuinely fixed, not papered over. Inference now drops exactly the commits that git itself lists as grafts, and it reads them in the same single `rev-parse` call the notice already made. A Task build therefore makes v0.7.1's 3 git calls, and the timing is within noise. I re-ran the evidence myself. Every non-shallow input stays byte-identical to v0.7.1 (9/9). Shallow builds only lose `inferred` edges. On this repo at a non-merge tip, `impact` went from v0.7.1's inflated 19/101 to 2/8, a subset of the full clone's 4/17, and unshallowing restores the full answer byte for byte. The C12 paths hold against real git, never raise and never invent links. The R9 no-git notice for a hand-corrupted graft list is accurate enough under A7 and needs no change. Mutating the skip filter, the C12 return, the path join or the SHA validation each turns tests red. I fixed the one vacuous assertion (F5) and a stale comment (F8). Two artifact-sync items stay open and do not block: an undocumented fixture-shape deviation (F6), which I accept, and a disproven sentence about merge tips in spec and plan (F7). No Blocker or Major is open, so the status is `passed`.

---

## ✅ REVIEW GATE

*All boxes checked → `/demo-day` may start. Any box open → back to `/increment`. On
re-review, edit this same checklist in place — never duplicate it as a second gate.*

- [x] No open Blocker findings
- [x] No open Major findings (or explicitly waived by the user, with reason recorded here): F1 fixed r2
- [x] Every Must AC traces to implementing code; no constitution non-negotiable violated (no constitution; CLAUDE.md non-negotiables checked)
- [x] All plan deviations documented and accepted (T7 fixture, T8/T16 baseline in plan; T10 fixture shape recorded as F6 here and accepted by the reviewer)
- [x] Test suite runs green (387 passed, slow 3 passed, after reviewer fixes F5/F8)
- [x] Line budget respected: Ist ~120 / Soll ~150 (excluding HTML comments)
- [x] Status set to `passed`
