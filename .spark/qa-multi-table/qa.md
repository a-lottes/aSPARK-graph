# QA Report: qa-multi-table

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Review (hands-on) |
| **Owner** | QA Tester (`/demo-day`, condensed, run by the orchestrator) |
| **Input** | Branch `factory/issue-38`, `.spark/qa-multi-table/spec.md` |
| **Status** | `in-review` |
| **Round** | 1 |
| **Date** | 2026-11-11 |

**Handoff**
- **Status:** mirrors the header table above.
- **Verdict:** Yes. Every AC passes hands-on over the CLI.
- **Open:** `none`.

## 1. Test Environment

No browser: headless CLI/MCP tool, no UI (CLAUDE.md: QA-equivalent is hands-on CLI). Scratch copy of `tests/fixtures/current_names_repo` with a split-table `qa.md` (`### US-1`, `### US-2`), built with `uv run aspark-graph build`. Reviewer separately proved byte-identity against HEAD~1 (review.md, AC-3.1).

## 2. Acceptance Criteria Verification

| Spec ID | Steps performed | Expected | Observed | Result |
|---|---|---|---|---|
| AC-1.1 | Built a repo whose qa.md has two sub-tables | Checks of both tables in the graph | Build succeeded; AC-1.1, AC-1.2, AC-2.1 all have checks | ✅ pass |
| AC-1.2 | `query gate_health demo` and `story_trace US-1` on that repo | No AC from a later table unverified | `unverified_acs` empty for the split report; trace shows pass | ✅ pass |
| AC-1.3 | Table in a later `## 6` section plus the suite test | Not read | No checks from it; test passes | ✅ pass |
| AC-2.1 | Replaced the US-2 sub-table header by `Spec ID \| Notes` | Drift error naming file and column | `template drift in …/qa.md: QA table missing a 'Result' column`, one line, no traceback | ✅ pass |
| AC-3.1 | Reviewer: `build --full` of this repo under HEAD~1 vs HEAD, `cmp` | Identical | Identical, same sha256 (review.md) | ✅ pass |
| AC-4.1 | grep docs for "first QA" / "first table" | No remaining limit statement | None left (CLAUDE.md, constitution, BACKLOG G6 updated) | ✅ pass |

## 3. Bugs
None.

## 4. Exploratory
Same AC in two tables keeps two distinct checks (test added); a pipe block without a separator row is skipped, not drift (C3).

## 5. Verdict
Passed. 393 tests green.
