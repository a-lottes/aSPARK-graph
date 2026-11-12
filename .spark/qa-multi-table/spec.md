# Spec: qa-multi-table

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Specify |
| **Owner** | Product Owner (`/story-time`), Designer (`/look-and-feel`) |
| **Status** | `approved` |
| **Date** | 2026-11-12 |
| **Ticket** | #70 |
| **Gate comment** | none |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Summary:** `qa.md` files that split "Acceptance Criteria Verification" into per-story tables (`### US-n`) only have their first table read, so later ACs show as unverified. Read every table in the section. Closes BACKLOG G6.
- **Open:** `none`
- **Binding ruling:** §4 User Stories
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Problem & Goal

- **Problem:** `_parse_qa` (`artifacts.py`) uses `_first_table`. 4 of 13 Core `qa.md` files (BACKLOG G6) have 4–7 per-story tables; every AC after the first table reads `unverified` in `gate_health` and `story_trace`. Silent undercounting.
- **Goal:** every verification table under the section contributes its QA checks.
- **Success signal:** a multi-table fixture yields a QA result for every AC; single-table `qa.md` files produce a byte-identical graph.json.
- **Why now:** reported as issue #70; gate output is wrong for affected repos.

## 2. Target Users

Agents and developers using `gate_health` / `story_trace` on repos whose `qa.md` splits verification per story.

## 3. Assumptions & Open Questions

| # | Assumption / Question | Resolution |
|---|---|---|
| A1 | Tables are the pipe-tables inside the section, including under `###` sub-headings (`_section` already ends only at `#`/`##`). | Accepted |
| A2 | A later table without an AC/Spec ID column or Result column (e.g. a summary or bug table) is not a verification table: skipped silently. The first table keeps today's strict drift error. | Accepted (drift stays loud where today's behaviour was loud) |
| A3 | QA check ids stay `qa:<feature>:<ac>#<index>`; the index runs continuously across tables in file order, so single-table output is unchanged and ids never collide. | Accepted |

## 4. User Stories

### US-1 (Must): Read all QA verification tables

> As a user of `gate_health`/`story_trace`, I want results from every verification table in `qa.md`, so that ACs verified in later per-story tables are not reported as unverified.

**Acceptance criteria:**

- [ ] AC-1.1: Given a `qa.md` whose verification section holds several tables, when the graph is built, then each AC row from every table yields a QA check with its result.
- [ ] AC-1.2: Given such a `qa.md`, when `gate_health` and `story_trace` run, then ACs from the second and later tables show their recorded result, not `unverified`.
- [ ] AC-1.3: Given a `qa.md` with a single table, when the graph is built, then graph.json is byte-identical to the previous release's (proved by building a fixed fixture under pre-change code and new code and diffing).
- [ ] AC-1.4: Given a first table missing its AC or Result column, then `TemplateDriftError` is raised as today; given a later table lacking those columns, it is skipped without error.
- [ ] AC-1.5: Given the same AC verified in two tables, then both checks are kept in file order and the later one is the latest result, as for repeated rows today.

## 5. Non-Functional Requirements

| # | Category | Requirement (measurable) | How it's verified |
|---|---|---|---|
| NFR-1 | Determinism | Double build of a multi-table fixture is byte-identical. | tests |
| NFR-2 | Reliability | No new traceback paths; errors stay one-line domain errors. | /peer-review |

## 6. Out of Scope

- Tables outside the Acceptance Criteria Verification section.
- Reading a QA table's non-AC rows (NFR rows etc.).
- Changing result normalisation or the `implements` model.

## 7. Clarifications

| # | Date | Question | Resolution |
|---|---|---|---|
| C1 | 2026-11-12 | Strict or lenient on later tables with other columns? | Lenient (A2); autonomous decision following the issue's "read all of them". |

## 8. Design Review

N/A — headless tool, no UI.

---

## ✅ SPEC GATE

- [x] Problem, goal and success signal are concrete
- [x] Every story has testable Given/When/Then acceptance criteria
- [x] Stories are prioritized and at least one is a Must
- [x] Non-functional requirements are stated and measurable
- [x] Clarify pass done
- [x] Open questions are resolved
- [x] Out-of-scope section is filled
