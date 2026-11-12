# QA Report: qa-multi-table

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Review (hands-on) |
| **Owner** | QA Tester (`/demo-day`) |
| **Input** | Headless CLI/MCP tool, `.spark/qa-multi-table/spec.md` |
| **Status** | `passed` |
| **Round** | 1 |
| **Date** | 2026-11-12 |

## 1. Test Environment

Headless tool, no UI: browser QA is N/A (CLAUDE.md). QA-equivalent done hands-on: full suite (411 passed), slow suite (4 passed), and builds of fixtures and the live repo. No override of a gate; the reviewer additionally re-checked against a Core copy (see review.md).

## 2. Acceptance Criteria Verification

| Spec ID | Steps performed | Expected | Observed | Result |
|---|---|---|---|---|
| AC-1.1 | Built a 3-table fixture (`tests/test_qa_multi_table.py`) | A QA check per AC row of every table | 3 checks, one per row | ✅ pass |
| AC-1.2 | `gate_health` / `story_trace` on the fixture | Later-table ACs show their result | Result shown, not unverified | ✅ pass |
| AC-1.3 | Built `current_names_repo` under old and new code, `cmp` of graph.json | Byte-identical | Identical (reviewer also checked live repo clone) | ✅ pass |
| AC-1.4 | First table without AC / Result column; later bug table | Drift error; later table skipped | As expected | ✅ pass |
| AC-1.5 | Same AC in two tables | Both kept, later is latest | Later result wins | ✅ pass |
| NFR-1 | Double build of the multi-table fixture | Byte-identical | Identical | ✅ pass |

## 3. Bugs

None.

## 4. Verdict

Passed. All ACs verified; demo-day browser testing is structurally N/A.
