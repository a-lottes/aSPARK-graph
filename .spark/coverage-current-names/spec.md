# Spec: coverage-current-names

| | |
|---|---|
| **Phase** | Specify |
| **Owner** | Orchestrator with the user (`/story-time`, condensed: a merge-conflict repair, no new product idea) |
| **Status** | `approved` |
| **Date** | 2026-09-26 |
| **Target** | v0.7.1 (not yet uploaded; main already carries the 0.7.1 bump) |

## 1. Problem

Two PRs merged into `main` without ever meeting: `current-artifact-names` (PR #3, reads `qa.md`/`review.md`/`release.md`, `_resolve` returns `None` when an artifact is missing) and `coverage statement` (PR #2 by a contributor, records per-feature `coverage` = recognized / skipped / near_misses). Merged `1b62da0`: `_parse_feature` calls `.exists()` on a `None` path, so `build` crashes on any feature without all three artifacts (26 tests fail). Even without the crash, PR #2's fixed list of expected names knows only the legacy names, so on a current-name trail `qa.md` would count as a near-miss and `qa-report.md` as skipped.

## 2. User Stories

### US-1 (Must): The build works again on merged main
- [ ] AC-1.1: Given the merged main, when `uv run pytest` runs, then all tests pass, including PR #2's `tests/test_coverage_statement.py`, unedited.
- [ ] AC-1.2: Given a feature folder that lacks review, QA or release (either name), when the graph is built, then no exception is raised and the missing kinds appear in `coverage.skipped`.

### US-2 (Must): Coverage speaks the names the trail actually uses
- [ ] AC-2.1: Given a feature with `spec.md`, `plan.md`, `review.md`, `qa.md`, `release.md`, when built, then `coverage.recognized` lists all five kinds (in their legacy spelling, C4), `skipped` and `near_misses` are empty, and `gate_health` has `coverage_note: null`.
- [ ] AC-2.2: Given a feature with only current-name `qa.md` (no review, no release), when built, then `recognized` names the QA kind (`qa-report.md`, C4), and `skipped` names the missing kinds (`review-report.md`, `release-notes.md`, the legacy spelling, as today).
- [ ] AC-2.3: Given both `qa.md` and `qa-report.md`, when built, then `recognized` names the QA kind once (`qa-report.md`, C4) and the shadowed `qa-report.md` is not reported as a near-miss.
- [ ] AC-2.4: Given a file such as `reviews.md` that is neither name, when built, then it is still a near-miss (PR #2 behaviour unchanged).

### US-3 (Must): Legacy trails see no change from this repair
- [ ] AC-3.1: Given a repo that uses only legacy names, when built by the repaired code and by `ad83eae` (PR #2 without PR #3), then `graph.json` is byte-identical.
- [ ] AC-3.2: Given this repo's own trail, the same holds (this feature's trail uses legacy names on purpose).

## 3. Non-functional
- NFR-1: Deterministic output; sorted lists; no new dependency.
- NFR-2: Existing tests are not edited, only added (PR #2's and PR #3's suites stay as they are).
- NFR-3: `coverage` values come from `_ARTIFACT_NAMES` (single source for names), not from a second hand-kept list.

## 4. Clarifications
| # | Question | Decision |
|---|---|---|
| C1 | AC-5.1 of `current-artifact-names` said "byte-identical to v0.7.0". PR #2 adds `coverage` to every Feature node, so v0.7.0 can no longer be the baseline. | The baseline is `ad83eae` (PR #2 alone); AC-3.1 replaces it. The claim in the v0.7.1 release notes changes to "…to the previous main". |
| C2 | Which name does `skipped` use for a missing kind? | The legacy spelling, as PR #2 pinned it in its tests. A later cleanup can switch to current names (BACKLOG G10). |
| C4 | (Raised in /increment T1, 2026-09-26) Reporting actual file names in `recognized` breaks v0.7.1's AC-5.3 (a rename leaves the graph byte-identical). | User ruling: `recognized` names each kind by its legacy spelling, like `skipped` (C2). AC-2.1–2.3 reworded accordingly; which file was read stays visible via the `Ignored …` notice. |
| C3 | Process | Repair on branch `fix/coverage-current-names` from `origin/main`; own trail here under legacy names; Review and QA again before the tag. |

## ✅ SPEC GATE
- [x] Status `approved` by the user (2026-09-26)
