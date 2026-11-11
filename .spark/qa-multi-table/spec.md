# Spec: qa-multi-table

| | |
|---|---|
| **Phase** | Specify |
| **Owner** | Orchestrator (`/story-time`, condensed: seeded from issue #38 / BACKLOG G6, autonomous line) |
| **Ticket** | #38 |
| **Status** | `approved` |
| **Date** | 2026-11-11 |

## 1. Problem

`_parse_qa` reads only the first table under `## … Acceptance Criteria Verification`. Several aSPARK Core `qa.md` files split that section into per-story `### US-n` sub-tables, so every AC after the first table reads as unverified: no drift error, silent under-counting (BACKLOG G6). Seeded from issue #38.

## 2. User Stories

### US-1 (Must): Every table of the QA verification section is read
- [ ] AC-1.1: Given a `qa.md` whose verification section has several tables (including `### …` sub-tables), when built, then QA checks of every table reach the graph.
- [ ] AC-1.2: Given such a report, when `story_trace` and `gate_health` run, then they see the QA checks of every table (no AC verified in a later table is reported unverified).
- [ ] AC-1.3: Given tables in other sections of `qa.md`, when built, then they are still not read.

### US-2 (Must): Every verification table is checked for drift
- [ ] AC-2.1: Given a table in the verification section without an `AC`/`Spec ID` column, or without a `Result` column, when built, then `TemplateDriftError` names the file and the missing column, as for the first table today.

### US-3 (Must): Single-table reports are unchanged
- [ ] AC-3.1: Given a `qa.md` with a single table, when built, then the graph is byte-identical to the one the previous code builds.

### US-4 (Should): The old limit is no longer documented
- [ ] AC-4.1: Given the repo docs, when read, then none still states that only the first QA table is read.

## 3. Non-functional
- NFR-1: Deterministic output; no new dependency.
- NFR-2: QACheck ids use a running row index across tables, so they are unique and equal to today's for one table.

## 4. Clarifications
| # | Question | Decision |
|---|---|---|
| C1 | Index across tables (BACKLOG G6 open point)? | One running index over all data rows of all tables in order. |
| C2 | Sub-table with a deviating header? | Template drift (AC-2.1). |
| C3 | Pipe-block without a separator row? | Not a table; skipped, as the first-table logic did. |

## 5. Out of Scope
Other sections' tables; review.md findings tables; new template markers.

## 6. Design Review
N/A: headless tool, no UI.

## SPEC GATE
- [x] Stories and ACs testable
- [x] Design review N/A recorded
- [x] Approved (autonomous line, recommended option)
