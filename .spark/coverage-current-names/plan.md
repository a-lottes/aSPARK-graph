# Plan: coverage-current-names

| | |
|---|---|
| **Phase** | Plan |
| **Owner** | Orchestrator (`/sprint-plan`, condensed) |
| **Input** | `spec.md` (`approved`, 2026-09-26) |
| **Status** | `approved` |
| **Date** | 2026-09-26 |

## 1. Architecture Decision

`_parse_feature` builds `coverage` from what `_resolve` returned, not from a second hand-kept name list.
- `recognized` = for each kind whose file was found (`spec.md`, `plan.md`, and the three resolved paths not `None`), the kind's **legacy** spelling (C4), so a rename leaves the graph byte-identical.
- `known` = `{spec.md, plan.md}` plus every current and legacy name from `_ARTIFACT_NAMES`.
- `skipped` = for each kind whose resolved path is `None`, the legacy name (C2), plus `spec.md`/`plan.md` when absent, sorted.
- `near_misses` = other `*.md` whose stem contains spec/plan/review/qa/release, excluding every name in `known`.

Rejected: (a) only guarding `None` — crash fixed but current-name trails would report false skips and near-misses (AC-2.1 fails); (b) reporting current names in `skipped` — changes PR #2's pinned output for legacy trails (C2); (c) reverting PR #3 — loses the feature.

## 2. Affected Components
`src/aspark_graph/artifacts.py` (`_parse_feature` coverage block) and tests. `queries.py`, `build.py`, `cli.py`, `server.py` unchanged.

## 3. Task Breakdown

| # | Task | Story | Covers | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|---|
| T1 | Rebuild the coverage block from `_resolve` results and `_ARTIFACT_NAMES` (no `None.exists()`, no second name list) | US-1, US-2 | AC-1.1, AC-1.2, NFR-3 | — | `done` | `uv run pytest` fully green, PR #2 and PR #3 tests unedited — files: src/aspark_graph/artifacts.py |
| T2 | Tests: full current-name trail (fixture `current_names_repo`): recognized five names, skipped `[]`, note null; only `qa.md`: skipped names the two legacy spellings; both names: shadowed legacy not a near-miss; `reviews.md` still a near-miss | US-2 | AC-2.1–2.4 | T1 | `done` | New tests fail on `origin/main`, pass now — files: tests/test_coverage_current_names.py |
| T3 | Baseline check: fresh clone of `ad83eae` vs the fix on a legacy-only repo and on this repo's trail: `cmp graph.json`. Rebuild Core and steamcore scratch clones: no crash, counts as in v0.7.1 QA | US-3 | AC-3.1, AC-3.2 | T2 | `done` | `cmp` empty; counts recorded in the notes |
| T4 | Release: update the v0.7.1 release notes (baseline claim, coverage fields), release commit; new PR; tag on the merge commit after the upload | — | — | T3 | `done` | Review and QA `passed` again first. Pre-flight re-run on the repair commit (tests, slow suite, `uv build` sdist list, `cmp` vs `ad83eae` on a fresh clone, Core/steamcore) and written into the v0.7.1 release notes §1; KEEP GATE pre-flight box ticked only then (review F1) |

### Task notes
- **T1 (2026-09-26):** coverage built from `_resolve` results; names from `_ARTIFACT_NAMES`. First version reported actual names in `recognized` and broke v0.7.1's AC-5.3 test; user ruling C4 → legacy spelling per kind.
- **T2:** `tests/test_coverage_current_names.py`, 5 tests; all 5 fail on `origin/main` (`1b62da0`) and pass with the fix. Suite 328 passed, `-m slow` 3 passed.
- **T3:** `ad83eae` vs fix, `cmp` empty on (a) this repo's trail incl. this folder, (b) the current-name fixture renamed to legacy names with an `AC` header. Core `e1a0005`: rc 0, QACheck pass 143 / unknown 11 / fail 11, Finding 170, 14 features, 1 with skipped kinds, near-miss `PATCH-PLAN.md`. steamcore `bf1b3e0`: rc 0, pass 251 / unknown 10, Finding 138, no skipped, no near-misses.
- **Review r1 (2026-09-26):** `changes-requested` for F1 (stale release evidence). User ruling: fix F1–F5 now (artifact text), F6–F9 (PR #2 code) → BACKLOG G10; version stays 0.7.1; `coverage_note` on in-progress features stays as PR #2 intends.
- **T4 (part 1):** v0.7.1 release notes: coverage added to the changelog, the "byte-identical to v0.7.0" claim replaced (C1), the repair named. BACKLOG G9 (`version-surface`) carried over from the release branch.
- **T4 (part 2, 2026-09-26):** release commit `8b7a1b3`; pre-flight re-run on a fresh clone of it, all green, written into the v0.7.1 release notes §1. Publish steps pending.

## 4. Test Strategy
Unit and graph-level tests as above, plus the two scratch-clone checks in T3. No browser.

## 5. Risks
- R1: the contributor's tests pin the legacy spelling in `skipped`; C2 keeps them green.
- R2: v0.7.1 release notes still say "byte-identical to v0.7.0"; corrected in T4.

## ✅ PLAN GATE
- [x] Spec `approved`; every task maps to a story; DoD checkable
- [x] Status `approved` by the user (2026-09-26)
